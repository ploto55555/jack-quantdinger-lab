from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.jack_research_notes import build_research_notes_v1
from app.services.jack_research_profiles import get_research_profiles_v1


VERSION = "dashboard_summary_v1"


def build_dashboard_summary_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    profile_data = get_research_profiles_v1({})
    note_data = build_research_notes_v1({})
    profiles = profile_data.get("profiles", [])
    notes = note_data.get("notes", [])

    active = [p for p in profiles if p.get("status") == "active_candidate"]
    skipped = [p for p in profiles if p.get("status") == "rejected_for_now"]
    ranked = sorted(active, key=lambda p: _score_profile(p), reverse=True)

    return {
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "active_candidates": len(active),
            "rejected_for_now": len(skipped),
            "notes_total": len(notes),
            "best_current_profile": ranked[0].get("profile_id") if ranked else None,
            "weakest_active_profile": ranked[-1].get("profile_id") if ranked else None,
            "dashboard_stage": "research_profile_dashboard",
        },
        "cards": _cards(profiles, notes),
        "ranked_candidates": [_candidate_row(p) for p in ranked],
        "attention_items": _attention_items(notes),
        "next_focus": [
            "Keep current profiles as research candidates, not final live rules.",
            "Use journal notes to compare manual chart observations against profile results.",
            "Later connect dashboard cards to the frontend so the system can be reviewed on one screen.",
        ],
    }


def _score_profile(profile: dict[str, Any]) -> float:
    result = profile.get("result") or {}
    ret = float(result.get("return_percent") or 0)
    ratio = float(result.get("positive_negative_ratio") or 0)
    max_drop = abs(float(result.get("max_drop_percent") or 0))
    samples = float(result.get("sample_count") or 0)
    sample_bonus = min(samples, 60) / 60
    return round(ret + ratio * 10 + sample_bonus * 2 - max_drop * 0.35, 4)


def _candidate_row(profile: dict[str, Any]) -> dict[str, Any]:
    result = profile.get("result") or {}
    return {
        "symbol": profile.get("symbol"),
        "profile_id": profile.get("profile_id"),
        "profile_type": profile.get("profile_type"),
        "score": _score_profile(profile),
        "return_percent": result.get("return_percent"),
        "max_drop_percent": result.get("max_drop_percent"),
        "sample_count": result.get("sample_count"),
        "positive_negative_ratio": result.get("positive_negative_ratio"),
        "status": profile.get("status"),
    }


def _cards(profiles: list[dict[str, Any]], notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    note_map = {n.get("profile_id"): n for n in notes}
    cards = []
    for p in profiles:
        n = note_map.get(p.get("profile_id"), {})
        cards.append({
            "symbol": p.get("symbol"),
            "title": p.get("profile_id"),
            "status": p.get("status"),
            "profile_type": p.get("profile_type"),
            "decision": n.get("decision"),
            "quality_flags": n.get("quality_flags", []),
            "next_action": n.get("next_action"),
            "result": p.get("result"),
        })
    return cards


def _attention_items(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for note in notes:
        flags = note.get("quality_flags") or []
        if "clean_candidate" in flags:
            continue
        items.append({
            "symbol": note.get("symbol"),
            "profile_id": note.get("profile_id"),
            "flags": flags,
            "next_action": note.get("next_action"),
        })
    return items
