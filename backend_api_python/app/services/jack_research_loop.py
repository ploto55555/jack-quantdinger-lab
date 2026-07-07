from __future__ import annotations

from typing import Any

from app.services.jack_idea_generator import generate_ideas_v1
from app.services.jack_multi_idea_tester import run_multi_idea_test_v1
from app.services.jack_memory_store import add_memory_v1


VERSION = "research_loop_v1"


def run_research_loop_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = max(1, min(_to_int(payload.get("limit"), 30), 120))
    top_n = max(1, min(_to_int(payload.get("top_n"), 5), 20))

    generated = generate_ideas_v1({
        "symbols": payload.get("symbols"),
        "limit": limit,
        "include_mtf": payload.get("include_mtf", True),
        "include_lower_profile": payload.get("include_lower_profile", True),
    })
    idea_texts = generated.get("idea_texts") or []
    tested = run_multi_idea_test_v1({"ideas": idea_texts, "limit": limit})
    ranked = tested.get("ranked") or []
    top = ranked[:top_n]
    rejected_patterns = _rejected_patterns(ranked)
    accepted_patterns = _accepted_patterns(ranked)

    summary = {
        "version": VERSION,
        "generated_count": generated.get("total_generated", 0),
        "tested_count": tested.get("total_tested", 0),
        "top_n": top_n,
        "best_idea": top[0].get("idea") if top else None,
        "best_score": top[0].get("rank_score") if top else None,
        "accepted_patterns": accepted_patterns,
        "rejected_patterns": rejected_patterns,
        "human_summary": _human_summary(top, accepted_patterns, rejected_patterns),
    }

    memory = add_memory_v1({
        "memory_type": "research_loop",
        "symbol": "MULTI",
        "title": f"Research Loop {summary.get('generated_count')} ideas",
        "content": summary.get("human_summary"),
        "tags": [VERSION, "research_loop", "snowball"],
        "source": VERSION,
        "metadata": {"summary": summary, "top": top, "rejected_patterns": rejected_patterns},
    })

    return {
        "version": VERSION,
        "ok": bool(tested.get("ok", True)),
        "summary": summary,
        "top": top,
        "ranked": ranked,
        "generated": generated,
        "tested_summary": tested.get("summary"),
        "memory": {"research_loop_memory_id": (memory.get("memory") or {}).get("memory_id")},
    }


def _accepted_patterns(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in ranked:
        if row.get("action") == "keep_as_research_candidate":
            output.append({
                "idea": row.get("idea"),
                "symbol": row.get("symbol"),
                "profile_type": row.get("profile_type"),
                "return_percent": row.get("return_percent"),
                "max_drop_percent": row.get("max_drop_percent"),
                "ratio": row.get("ratio"),
                "sample_count": row.get("sample_count"),
            })
    return output[:10]


def _rejected_patterns(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in ranked:
        if row.get("action") != "reject_or_rework":
            continue
        flags = row.get("flags") or []
        key = "+".join(sorted(str(x) for x in flags if x not in ["memory_context_available", "symbol_has_active_profile"])) or "reject"
        if key not in buckets:
            buckets[key] = {"pattern": key, "count": 0, "examples": []}
        buckets[key]["count"] += 1
        if len(buckets[key]["examples"]) < 3:
            buckets[key]["examples"].append(row.get("idea"))
    return sorted(buckets.values(), key=lambda x: x.get("count", 0), reverse=True)


def _human_summary(top: list[dict[str, Any]], accepted: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> str:
    best = top[0] if top else {}
    return (
        f"Research loop completed. Best idea: {best.get('idea')} "
        f"score={best.get('rank_score')} action={best.get('action')}. "
        f"Accepted candidates={len(accepted)}. Rejected pattern buckets={len(rejected)}."
    )


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
