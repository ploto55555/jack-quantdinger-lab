from __future__ import annotations

from typing import Any

from app.services.jack_decision_engine import make_decision_v1
from app.services.jack_memory_store import add_memory_v1


VERSION = "multi_idea_tester_v1"


def run_multi_idea_test_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ideas = _ideas(payload)
    limit = max(1, min(_to_int(payload.get("limit"), 20), 50))
    selected = ideas[:limit]

    results = []
    failures = []
    for index, text in enumerate(selected, start=1):
        try:
            report = make_decision_v1({"text": text})
            results.append({
                "index": index,
                "idea": text,
                "ok": bool(report.get("ok")),
                "symbol": report.get("symbol"),
                "profile_type": report.get("profile_type"),
                "final_decision": report.get("final_decision"),
                "idea_result_decision": report.get("idea_result_decision"),
                "explanation": report.get("explanation"),
                "memory": report.get("memory"),
            })
        except Exception as exc:  # pragma: no cover
            failures.append({"index": index, "idea": text, "ok": False, "error": str(exc)})

    ranked = _rank(results)
    summary = _summary(results, failures, ranked)
    batch_memory = add_memory_v1({
        "memory_type": "batch_idea_test",
        "symbol": "MULTI",
        "title": f"Batch Idea Test {len(selected)} ideas",
        "content": summary.get("human_summary"),
        "tags": [VERSION, "batch", summary.get("best_action")],
        "source": VERSION,
        "metadata": {"summary": summary, "ranked": ranked[:10]},
    })

    return {
        "version": VERSION,
        "ok": not failures,
        "total_input": len(ideas),
        "total_tested": len(selected),
        "total_failed": len(failures),
        "summary": summary,
        "ranked": ranked,
        "results": results,
        "failures": failures,
        "memory": {"batch_memory_id": (batch_memory.get("memory") or {}).get("memory_id")},
    }


def _ideas(payload: dict[str, Any]) -> list[str]:
    value = payload.get("ideas")
    if isinstance(value, list):
        out = [str(x).strip() for x in value if str(x).strip()]
        if out:
            return out
    text = str(payload.get("text") or "").strip()
    if text:
        lines = [x.strip(" -\t") for x in text.splitlines()]
        return [x for x in lines if x]
    return []


def _rank(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for item in results:
        decision = item.get("idea_result_decision") or {}
        final = item.get("final_decision") or {}
        score = _score(decision, final)
        ranked.append({
            "rank_score": score,
            "idea": item.get("idea"),
            "symbol": item.get("symbol"),
            "profile_type": item.get("profile_type"),
            "mode": final.get("mode"),
            "action": final.get("action"),
            "return_percent": decision.get("return_percent"),
            "max_drop_percent": decision.get("max_drop_percent"),
            "ratio": decision.get("ratio"),
            "sample_count": decision.get("sample_count"),
            "flags": final.get("flags"),
            "explanation": item.get("explanation"),
        })
    return sorted(ranked, key=lambda row: row.get("rank_score", -999), reverse=True)


def _score(decision: dict[str, Any], final: dict[str, Any]) -> float:
    ret = _float(decision.get("return_percent"), 0.0)
    drop = abs(_float(decision.get("max_drop_percent"), 99.0))
    ratio = _float(decision.get("ratio"), 0.0)
    samples = _float(decision.get("sample_count"), 0.0)
    action = str(final.get("action") or "")
    score = ret * 2.0 + ratio * 5.0 - drop * 0.8 + min(samples, 80.0) * 0.08
    if action == "keep_as_research_candidate":
        score += 10.0
    if action == "watch_only_more_validation_needed":
        score -= 3.0
    if action == "reject_or_rework":
        score -= 10.0
    return round(score, 4)


def _summary(results: list[dict[str, Any]], failures: list[dict[str, Any]], ranked: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in results:
        action = ((item.get("final_decision") or {}).get("action") or "unknown")
        counts[action] = counts.get(action, 0) + 1
    best = ranked[0] if ranked else {}
    human = (
        f"Batch tested {len(results)} ideas with {len(failures)} failures. "
        f"Best idea: {best.get('idea')} action={best.get('action')} score={best.get('rank_score')}. "
        f"Action counts: {counts}."
    )
    return {
        "action_counts": counts,
        "best_action": best.get("action"),
        "best_idea": best.get("idea"),
        "best_score": best.get("rank_score"),
        "human_summary": human,
    }


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
