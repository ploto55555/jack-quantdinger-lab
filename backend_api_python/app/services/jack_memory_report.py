from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.services.jack_memory_store import list_memory_v1, add_memory_v1


VERSION = "memory_report_v1"


def build_memory_report_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = max(10, min(_to_int(payload.get("limit"), 200), 1000))
    symbol_filter = str(payload.get("symbol") or "").upper().strip()

    memory = list_memory_v1({"limit": limit, "symbol": symbol_filter})
    items = memory.get("items") or []

    type_counts = Counter(str(item.get("memory_type") or "unknown") for item in items)
    symbol_counts = Counter(str(item.get("symbol") or "UNKNOWN") for item in items)

    top_candidates = _top_candidates(items)
    weak_patterns = _weak_patterns(items)
    symbol_status = _symbol_status(items)
    next_research = _next_research(top_candidates, weak_patterns, symbol_status)

    summary = {
        "version": VERSION,
        "memory_items_scanned": len(items),
        "memory_type_counts": dict(type_counts),
        "symbol_counts": dict(symbol_counts),
        "top_candidates": top_candidates,
        "weak_patterns": weak_patterns,
        "symbol_status": symbol_status,
        "next_research": next_research,
        "human_summary": _human_summary(top_candidates, weak_patterns, next_research),
    }

    saved = None
    if _bool(payload.get("save_report"), True):
        saved = add_memory_v1({
            "memory_type": "memory_report",
            "symbol": symbol_filter or "MULTI",
            "title": "Research Memory Report v1",
            "content": summary["human_summary"],
            "tags": [VERSION, "report", "snowball"],
            "source": VERSION,
            "metadata": summary,
        })

    return {
        "version": VERSION,
        "ok": True,
        "summary": summary,
        "report_memory_id": ((saved or {}).get("memory") or {}).get("memory_id"),
    }


def _top_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in items:
        meta = item.get("metadata") or {}
        blocks = []
        if isinstance(meta.get("top"), list):
            blocks.extend(meta.get("top") or [])
        if isinstance(meta.get("ranked"), list):
            blocks.extend(meta.get("ranked") or [])
        summary = meta.get("summary") or {}
        if isinstance(summary.get("accepted_patterns"), list):
            blocks.extend(summary.get("accepted_patterns") or [])
        for row in blocks:
            if not isinstance(row, dict):
                continue
            action = str(row.get("action") or "")
            if action and action != "keep_as_research_candidate":
                continue
            idea = row.get("idea")
            if not idea:
                continue
            candidates.append({
                "idea": idea,
                "symbol": row.get("symbol"),
                "profile_type": row.get("profile_type"),
                "rank_score": row.get("rank_score"),
                "return_percent": row.get("return_percent"),
                "max_drop_percent": row.get("max_drop_percent"),
                "ratio": row.get("ratio"),
                "sample_count": row.get("sample_count"),
            })
    unique: dict[str, dict[str, Any]] = {}
    for row in candidates:
        key = str(row.get("idea"))
        if key not in unique or _score(row) > _score(unique[key]):
            unique[key] = row
    return sorted(unique.values(), key=_score, reverse=True)[:10]


def _weak_patterns(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        meta = item.get("metadata") or {}
        sources = []
        if isinstance(meta.get("rejected_patterns"), list):
            sources.extend(meta.get("rejected_patterns") or [])
        summary = meta.get("summary") or {}
        if isinstance(summary.get("rejected_patterns"), list):
            sources.extend(summary.get("rejected_patterns") or [])
        for row in sources:
            if not isinstance(row, dict):
                continue
            pattern = str(row.get("pattern") or "unknown")
            if pattern not in buckets:
                buckets[pattern] = {"pattern": pattern, "count": 0, "examples": []}
            buckets[pattern]["count"] += int(row.get("count") or 1)
            for example in row.get("examples") or []:
                if len(buckets[pattern]["examples"]) < 5:
                    buckets[pattern]["examples"].append(example)
    return sorted(buckets.values(), key=lambda x: x.get("count", 0), reverse=True)[:10]


def _symbol_status(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data: dict[str, dict[str, Any]] = defaultdict(lambda: {"symbol": "", "tested": 0, "accepted": 0, "watch": 0, "rework": 0, "best_score": None, "best_idea": None})
    for item in items:
        meta = item.get("metadata") or {}
        rows = []
        if isinstance(meta.get("top"), list):
            rows.extend(meta.get("top") or [])
        if isinstance(meta.get("ranked"), list):
            rows.extend(meta.get("ranked") or [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "UNKNOWN")
            d = data[symbol]
            d["symbol"] = symbol
            d["tested"] += 1
            action = str(row.get("action") or "")
            if action == "keep_as_research_candidate":
                d["accepted"] += 1
            elif action == "watch_only_more_validation_needed":
                d["watch"] += 1
            elif action == "reject_or_rework":
                d["rework"] += 1
            score = row.get("rank_score")
            if isinstance(score, (int, float)) and (d["best_score"] is None or score > d["best_score"]):
                d["best_score"] = score
                d["best_idea"] = row.get("idea")
    return sorted(data.values(), key=lambda x: (x.get("accepted", 0), x.get("best_score") or -999), reverse=True)


def _next_research(top: list[dict[str, Any]], weak: list[dict[str, Any]], symbols: list[dict[str, Any]]) -> list[str]:
    ideas = []
    if top:
        best = top[0]
        ideas.append(f"Focus validation on {best.get('symbol')} {best.get('profile_type')} because it is the current strongest candidate.")
    if weak:
        ideas.append(f"Avoid repeating the most common weak pattern for now: {weak[0].get('pattern')}.")
    for row in symbols[:5]:
        if row.get("accepted", 0) == 0:
            ideas.append(f"Find new variations for {row.get('symbol')} because no accepted candidate is recorded yet.")
    return ideas[:8]


def _human_summary(top: list[dict[str, Any]], weak: list[dict[str, Any]], next_research: list[str]) -> str:
    best = top[0] if top else {}
    return (
        f"Memory report completed. Current best candidate: {best.get('idea')} "
        f"score={best.get('rank_score')} return={best.get('return_percent')} max_drop={best.get('max_drop_percent')}. "
        f"Top weak pattern: {(weak[0] if weak else {}).get('pattern')}. "
        f"Next research items: {' | '.join(next_research)}"
    )


def _score(row: dict[str, Any]) -> float:
    value = row.get("rank_score")
    if isinstance(value, (int, float)):
        return float(value)
    ret = _float(row.get("return_percent"), 0.0)
    ratio = _float(row.get("ratio"), 0.0)
    drop = abs(_float(row.get("max_drop_percent"), 99.0))
    return ret * 2 + ratio * 5 - drop


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
