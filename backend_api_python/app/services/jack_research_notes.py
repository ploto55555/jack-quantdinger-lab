from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.jack_research_profiles import get_research_profiles_v1


VERSION = "research_notes_v1"


def build_research_notes_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "").upper().strip()
    profiles = get_research_profiles_v1({"symbol": symbol}).get("profiles", [])
    notes = [_note_from_profile(p) for p in profiles]
    status_counts: dict[str, int] = {}
    for n in notes:
        status = str(n.get("decision") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "notes_total": len(notes),
            "status_counts": status_counts,
            "purpose": "Convert current research profiles into a consistent note format for review and future memory.",
            "next_step": "Attach live/manual observations to these notes later.",
        },
        "notes": notes,
    }


def _note_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    symbol = profile.get("symbol")
    profile_id = profile.get("profile_id")
    status = profile.get("status")
    result = profile.get("result") or {}
    settings = profile.get("settings") or {}
    decision = "keep_research_candidate" if status == "active_candidate" else "skip_for_now"
    return {
        "note_id": f"NOTE_{profile_id}",
        "symbol": symbol,
        "profile_id": profile_id,
        "profile_type": profile.get("profile_type"),
        "test_type": profile.get("result", {}).get("source_step", "profile_review"),
        "decision": decision,
        "reason": profile.get("note"),
        "result_summary": {
            "return_percent": result.get("return_percent"),
            "max_drop_percent": result.get("max_drop_percent"),
            "sample_count": result.get("sample_count"),
            "win_rate_percent": result.get("win_rate_percent"),
            "positive_negative_ratio": result.get("positive_negative_ratio"),
        },
        "settings_snapshot": settings,
        "quality_flags": _quality_flags(profile),
        "next_action": _next_action(profile),
    }


def _quality_flags(profile: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    result = profile.get("result") or {}
    ratio = result.get("positive_negative_ratio")
    samples = result.get("sample_count")
    max_drop = result.get("max_drop_percent")
    if profile.get("status") != "active_candidate":
        flags.append("not_active")
    if isinstance(ratio, (int, float)) and ratio < 1.2:
        flags.append("weak_edge")
    if isinstance(samples, (int, float)) and samples < 30:
        flags.append("low_sample_count")
    if isinstance(max_drop, (int, float)) and max_drop < -8:
        flags.append("deep_drawdown")
    if not flags:
        flags.append("clean_candidate")
    return flags


def _next_action(profile: dict[str, Any]) -> str:
    if profile.get("status") != "active_candidate":
        return "Do not focus on this symbol until a different idea is tested."
    symbol = profile.get("symbol")
    if symbol == "EURUSD":
        return "Keep as MTF candidate and later compare with journal observations."
    if symbol == "GBPUSD":
        return "Keep downside profile and later test if profile remains useful with newer data."
    if symbol in {"GBPJPY", "XAUUSD"}:
        return "Keep H4 upward profile and later compare with manual chart review."
    return "Keep for review."
