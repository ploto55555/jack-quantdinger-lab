from __future__ import annotations

from typing import Any

from app.services.jack_idea_runner import run_idea_v1
from app.services.jack_memory_store import add_memory_v1, search_memory_v1
from app.services.jack_research_profiles import get_research_profiles_v1


VERSION = "decision_engine_v1"


def make_decision_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text = str(payload.get("text") or payload.get("idea") or "").strip()
    run = run_idea_v1({"text": text})
    parsed = ((run.get("parser") or {}).get("parsed") or {})
    symbol = parsed.get("symbol")
    profile_type = parsed.get("profile_type")
    run_decision = run.get("decision") or {}

    profiles = get_research_profiles_v1({"symbol": symbol}).get("profiles", [])
    current_profile = profiles[0] if profiles else {}
    memory_hits = search_memory_v1({"query": text, "symbol": symbol, "limit": 5}).get("items", [])

    final = _final_decision(run_decision, current_profile, memory_hits)
    report = {
        "version": VERSION,
        "ok": bool(run.get("ok")),
        "input_text": text,
        "symbol": symbol,
        "profile_type": profile_type,
        "current_profile": _profile_summary(current_profile),
        "idea_result_decision": run_decision,
        "similar_memory": [_memory_summary(x) for x in memory_hits],
        "final_decision": final,
        "explanation": _explain(symbol, profile_type, run_decision, current_profile, memory_hits, final),
    }

    memory = add_memory_v1({
        "memory_type": "decision",
        "symbol": symbol,
        "title": f"Decision {symbol} {profile_type}",
        "content": report["explanation"],
        "tags": [profile_type, final.get("mode"), final.get("action")],
        "source": "decision_engine_v1",
        "metadata": report,
    })
    report["memory"] = {"decision_memory_id": (memory.get("memory") or {}).get("memory_id")}
    return report


def _profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile:
        return {"status": "none"}
    result = profile.get("result") or {}
    return {
        "profile_id": profile.get("profile_id"),
        "status": profile.get("status"),
        "profile_type": profile.get("profile_type"),
        "return_percent": result.get("return_percent"),
        "max_drop_percent": result.get("max_drop_percent"),
        "sample_count": result.get("sample_count"),
        "ratio": result.get("positive_negative_ratio"),
    }


def _memory_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": item.get("memory_id"),
        "memory_type": item.get("memory_type"),
        "title": item.get("title"),
        "match_score": item.get("match_score"),
        "content": str(item.get("content") or "")[:320],
    }


def _final_decision(run_decision: dict[str, Any], profile: dict[str, Any], memory_hits: list[dict[str, Any]]) -> dict[str, Any]:
    flags = list(run_decision.get("flags") or [])
    profile_status = profile.get("status")
    profile_type = profile.get("profile_type")
    run_status = run_decision.get("status")

    if profile_status == "rejected_for_now":
        flags.append("symbol_rejected_in_current_profile_registry")
    if profile and profile_status == "active_candidate" and profile_type != "none":
        flags.append("symbol_has_active_profile")
    if len(memory_hits) >= 3:
        flags.append("memory_context_available")

    if "negative_result" in flags or "weak_ratio" in flags or profile_status == "rejected_for_now":
        action = "reject_or_rework"
        mode = "WAIT"
    elif run_status == "research_candidate" and profile_status == "active_candidate":
        action = "keep_as_research_candidate"
        mode = "WATCH"
    elif run_status == "watch_only":
        action = "watch_only_more_validation_needed"
        mode = "WAIT"
    else:
        action = "research_only"
        mode = "WAIT"

    return {
        "mode": mode,
        "action": action,
        "flags": sorted(set(flags)),
        "can_promote_to_profile": action == "keep_as_research_candidate" and "low_sample_count" not in flags,
        "can_use_for_live_decision": False,
        "safety_note": "Research support only. No automatic execution.",
    }


def _explain(symbol: str, profile_type: str, run_decision: dict[str, Any], profile: dict[str, Any], memory_hits: list[dict[str, Any]], final: dict[str, Any]) -> str:
    profile_id = profile.get("profile_id") if profile else "none"
    profile_status = profile.get("status") if profile else "none"
    flags = ", ".join(final.get("flags") or [])
    return (
        f"Decision for {symbol} {profile_type}: mode={final.get('mode')}, action={final.get('action')}. "
        f"Current registry profile={profile_id} status={profile_status}. "
        f"Idea test status={run_decision.get('status')} return={run_decision.get('return_percent')} "
        f"max_drop={run_decision.get('max_drop_percent')} ratio={run_decision.get('ratio')} samples={run_decision.get('sample_count')}. "
        f"Similar memory count={len(memory_hits)}. Flags={flags}. "
        f"This is research support only and should not be treated as an automatic live decision."
    )
