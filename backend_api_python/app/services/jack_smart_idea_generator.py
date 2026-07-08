from __future__ import annotations

from typing import Any

from app.services.jack_idea_generator import generate_ideas_v1
from app.services.jack_avoid_list import should_skip_idea_v1
from app.services.jack_memory_report import build_memory_report_v1


VERSION = "smart_idea_generator_v2"


def generate_smart_ideas_v2(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}

    final_limit = max(1, min(_to_int(payload.get("limit"), 20), 80))
    raw_limit = max(final_limit * 4, _to_int(payload.get("raw_limit"), final_limit * 4))
    raw_limit = min(raw_limit, 120)

    memory_report = build_memory_report_v1({
        "limit": payload.get("memory_limit", 300),
        "save_report": False,
    })

    base = generate_ideas_v1({
        "symbols": payload.get("symbols"),
        "limit": raw_limit,
        "include_mtf": payload.get("include_mtf", True),
        "include_lower_profile": payload.get("include_lower_profile", True),
    })

    selected = []
    skipped = []

    for idea in base.get("ideas") or []:
        text = idea.get("text")
        check = should_skip_idea_v1({
            "idea": text,
            "limit": payload.get("memory_limit", 300),
            "min_count": payload.get("min_count", 2),
        })

        enriched = dict(idea)
        enriched["smart_score"] = _smart_score(idea, memory_report)
        enriched["skip_check"] = check

        if check.get("skip"):
            skipped.append(enriched)
        else:
            selected.append(enriched)

    selected = sorted(selected, key=lambda x: x.get("smart_score", 0), reverse=True)
    selected = selected[:final_limit]

    return {
        "version": VERSION,
        "ok": True,
        "raw_generated": len(base.get("ideas") or []),
        "selected_count": len(selected),
        "skipped_count": len(skipped),
        "ideas": selected,
        "idea_texts": [x.get("text") for x in selected],
        "skipped_preview": skipped[:20],
        "memory_summary": (memory_report.get("summary") or {}).get("human_summary"),
        "next_step": "Send idea_texts to /api/jack-backtest/run-multi-idea-test-v1 or run-research-loop-v1.",
    }


def _smart_score(idea: dict[str, Any], memory_report: dict[str, Any]) -> float:
    text = str(idea.get("text") or "")
    symbol = str(idea.get("symbol") or "")
    profile_type = str(idea.get("profile_type") or "")

    score = 10.0

    # Prefer known strong area, but do not blindly overfit.
    if symbol == "GBPJPY" and profile_type == "h4_up":
        score += 8.0
    if symbol == "XAUUSD" and profile_type == "h4_up":
        score += 7.0

    # Give extra research attention to symbols with no accepted candidate yet.
    report = memory_report.get("summary") or {}
    for row in report.get("symbol_status") or []:
        if row.get("symbol") == symbol and int(row.get("accepted") or 0) == 0:
            score += 5.0

    # Current evidence prefers EMA30/150 and 1.5R.
    if "EMA30/150" in text:
        score += 5.0
    if "target 1.5R" in text:
        score += 4.0

    # Current memory says these are weaker.
    if "EMA20/100" in text:
        score -= 4.0
    if "EMA50/200" in text:
        score -= 5.0
    if "target 2R" in text:
        score -= 3.0
    if "target 3R" in text:
        score -= 5.0
    if " D1 " in text:
        score -= 4.0

    return round(score, 4)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
