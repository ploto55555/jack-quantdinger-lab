from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.jack_memory_store import list_memory_v1, add_memory_v1


VERSION = "avoid_list_v1"


def build_avoid_list_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = max(10, min(_to_int(payload.get("limit"), 300), 1000))
    min_count = max(1, min(_to_int(payload.get("min_count"), 2), 20))
    save = _bool(payload.get("save"), True)

    memory = list_memory_v1({"limit": limit})
    items = memory.get("items") or []

    weak_patterns = Counter()
    weak_examples: dict[str, list[str]] = {}
    idea_counter = Counter()

    for item in items:
        meta = item.get("metadata") or {}
        for pattern_row in _pattern_rows(meta):
            pattern = str(pattern_row.get("pattern") or "unknown")
            count = int(pattern_row.get("count") or 1)
            weak_patterns[pattern] += count
            weak_examples.setdefault(pattern, [])
            for example in pattern_row.get("examples") or []:
                if len(weak_examples[pattern]) < 5:
                    weak_examples[pattern].append(str(example))
        for row in _rank_rows(meta):
            if not isinstance(row, dict):
                continue
            if row.get("action") == "reject_or_rework":
                text = str(row.get("idea") or "").strip()
                if text:
                    idea_counter[text] += 1

    patterns = [
        {
            "pattern": pattern,
            "count": count,
            "level": _level(count),
            "rule": _rule_text(pattern),
            "examples": weak_examples.get(pattern, []),
        }
        for pattern, count in weak_patterns.most_common()
        if count >= min_count
    ]

    ideas = [
        {
            "idea": idea,
            "count": count,
            "level": _level(count),
            "rule": "Do not repeat this exact idea unless new data or new rule version is added.",
        }
        for idea, count in idea_counter.most_common()
        if count >= min_count
    ][:30]

    summary = {
        "version": VERSION,
        "memory_items_scanned": len(items),
        "min_count": min_count,
        "pattern_rules": patterns,
        "exact_idea_rules": ideas,
        "human_summary": _human_summary(patterns, ideas),
    }

    saved = None
    if save:
        saved = add_memory_v1({
            "memory_type": "avoid_list",
            "symbol": "MULTI",
            "title": "Research Avoid List v1",
            "content": summary["human_summary"],
            "tags": [VERSION, "avoid_list", "snowball"],
            "source": VERSION,
            "metadata": summary,
        })

    return {
        "version": VERSION,
        "ok": True,
        "summary": summary,
        "avoid_list_memory_id": ((saved or {}).get("memory") or {}).get("memory_id"),
    }


def should_skip_idea_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text = str(payload.get("idea") or payload.get("text") or "").strip()
    avoid = build_avoid_list_v1({"save": False, "limit": payload.get("limit", 300), "min_count": payload.get("min_count", 2)})
    reasons = []

    for row in avoid["summary"].get("exact_idea_rules", []):
        if text and text == row.get("idea"):
            reasons.append({"type": "exact_idea", "rule": row})

    tokens = _tokens(text)
    for row in avoid["summary"].get("pattern_rules", []):
        pattern = str(row.get("pattern") or "")
        if _pattern_matches(pattern, tokens):
            reasons.append({"type": "pattern", "rule": row})

    return {
        "version": VERSION,
        "idea": text,
        "skip": bool(reasons),
        "reasons": reasons,
    }


def _pattern_rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if isinstance(meta.get("rejected_patterns"), list):
        rows.extend(meta.get("rejected_patterns") or [])
    summary = meta.get("summary") or {}
    if isinstance(summary, dict) and isinstance(summary.get("rejected_patterns"), list):
        rows.extend(summary.get("rejected_patterns") or [])
    return [x for x in rows if isinstance(x, dict)]


def _rank_rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if isinstance(meta.get("ranked"), list):
        rows.extend(meta.get("ranked") or [])
    if isinstance(meta.get("top"), list):
        rows.extend(meta.get("top") or [])
    summary = meta.get("summary") or {}
    if isinstance(summary, dict) and isinstance(summary.get("ranked"), list):
        rows.extend(summary.get("ranked") or [])
    return [x for x in rows if isinstance(x, dict)]


def _level(count: int) -> str:
    if count >= 10:
        return "strong_avoid"
    if count >= 4:
        return "reduce_priority"
    return "watch_carefully"


def _rule_text(pattern: str) -> str:
    if "deep_drop" in pattern and "weak_ratio" in pattern:
        return "Avoid or reduce priority when this variation previously caused deep drawdown with weak positive/negative ratio."
    if "negative_result" in pattern:
        return "Do not repeat unless parameters or market regime filter are materially changed."
    if "low_return" in pattern and "weak_ratio" in pattern:
        return "Reduce priority because reward quality was weak."
    if "low_sample_count" in pattern:
        return "Needs more data before promotion; do not treat as strong evidence."
    return "Reduce priority until new evidence appears."


def _pattern_matches(pattern: str, tokens: set[str]) -> bool:
    if not pattern:
        return False
    if "deep_drop" in pattern and {"d1", "3r"}.intersection(tokens):
        return True
    if "negative_result" in pattern and {"3r", "50", "200"}.intersection(tokens):
        return True
    if "low_return" in pattern and {"2r", "20", "100"}.intersection(tokens):
        return True
    return False


def _tokens(text: str) -> set[str]:
    cleaned = text.upper().replace("/", " ").replace("EMA", " EMA ").replace("TARGET", " TARGET ")
    raw = cleaned.split()
    tokens = {x.lower() for x in raw}
    compact = text.upper().replace(" ", "")
    for key in ["1.5R", "2R", "3R", "EMA20", "EMA30", "EMA50", "100", "150", "200", "D1", "H4"]:
        if key in compact:
            tokens.add(key.lower())
    return tokens


def _human_summary(patterns: list[dict[str, Any]], ideas: list[dict[str, Any]]) -> str:
    top_pattern = patterns[0] if patterns else {}
    top_idea = ideas[0] if ideas else {}
    return (
        f"Avoid list completed. Top weak pattern={top_pattern.get('pattern')} count={top_pattern.get('count')}. "
        f"Exact repeated weak idea={top_idea.get('idea')} count={top_idea.get('count')}. "
        f"Pattern rules={len(patterns)}, exact idea rules={len(ideas)}."
    )


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "y", "on"]
    return default
