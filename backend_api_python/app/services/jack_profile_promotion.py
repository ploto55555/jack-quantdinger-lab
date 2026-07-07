from __future__ import annotations

from typing import Any

from app.services.jack_memory_store import list_memory_v1, add_memory_v1
from app.services.jack_research_profiles import get_research_profiles_v1


VERSION = "profile_promotion_v1"

PROMOTION_ORDER = [
    "avoid",
    "retired",
    "rejected_for_now",
    "watch_only",
    "research_candidate",
    "validated_candidate",
    "active_core_candidate",
]


def build_profile_promotion_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    save = _bool(payload.get("save_memory"), True)
    memory_limit = max(20, min(_to_int(payload.get("memory_limit"), 500), 1000))

    base_profiles = get_research_profiles_v1({}).get("profiles") or []
    validation_items = _validation_items(memory_limit)
    promotions = []

    for profile in base_profiles:
        row = _promote_one(profile, validation_items)
        promotions.append(row)

    summary = {
        "version": VERSION,
        "total_profiles": len(promotions),
        "status_counts": _status_counts(promotions),
        "promotions": promotions,
        "human_summary": _human_summary(promotions),
    }

    saved = None
    if save:
        saved = add_memory_v1({
            "memory_type": "profile_promotion_report",
            "symbol": "MULTI",
            "title": "Profile Promotion Report v1",
            "content": summary["human_summary"],
            "tags": [VERSION, "profile", "promotion", "snowball"],
            "source": VERSION,
            "metadata": summary,
        })

    return {
        "version": VERSION,
        "ok": True,
        "summary": summary,
        "promotion_memory_id": ((saved or {}).get("memory") or {}).get("memory_id"),
    }


def _promote_one(profile: dict[str, Any], validation_items: list[dict[str, Any]]) -> dict[str, Any]:
    symbol = str(profile.get("symbol") or "").upper()
    profile_id = str(profile.get("profile_id") or "")
    current_status = str(profile.get("status") or "research_candidate")
    settings = profile.get("settings") or {}
    timeframe = str(settings.get("timeframe") or "H4").upper()
    ema_fast = settings.get("ema_fast") or settings.get("h4_ema_fast")
    ema_slow = settings.get("ema_slow") or settings.get("h4_ema_slow")
    target_r = settings.get("objective_r")

    matched = _match_validation(validation_items, symbol, timeframe, ema_fast, ema_slow, target_r)
    validation_grade = (matched.get("metadata") or {}).get("grade") if matched else None
    validation_report = matched.get("metadata") if matched else None

    new_status = _status_from_validation(current_status, validation_grade)
    recommendation = _recommendation(current_status, new_status, validation_grade)

    return {
        "symbol": symbol,
        "profile_id": profile_id,
        "profile_type": profile.get("profile_type"),
        "previous_status": current_status,
        "promoted_status": new_status,
        "settings": settings,
        "base_result": profile.get("result"),
        "validation_grade": validation_grade,
        "validation_summary": validation_report.get("human_summary") if isinstance(validation_report, dict) else None,
        "recommendation": recommendation,
        "status_changed": new_status != current_status,
    }


def _validation_items(limit: int) -> list[dict[str, Any]]:
    data = list_memory_v1({"limit": limit, "memory_type": "validation_report"})
    return data.get("items") or []


def _match_validation(items: list[dict[str, Any]], symbol: str, timeframe: str, ema_fast: Any, ema_slow: Any, target_r: Any) -> dict[str, Any]:
    best = {}
    for item in items:
        meta = item.get("metadata") or {}
        if str(meta.get("symbol") or "").upper() != symbol:
            continue
        if str(meta.get("timeframe") or "").upper() != timeframe:
            continue
        params = meta.get("params") or {}
        if ema_fast is not None and _to_float(params.get("ema_fast"), -1) != _to_float(ema_fast, -2):
            continue
        if ema_slow is not None and _to_float(params.get("ema_slow"), -1) != _to_float(ema_slow, -2):
            continue
        if target_r is not None and abs(_to_float(params.get("target_r"), -1) - _to_float(target_r, -2)) > 0.0001:
            continue
        if not best or str(item.get("created_at") or "") > str(best.get("created_at") or ""):
            best = item
    return best


def _status_from_validation(current: str, grade: dict[str, Any] | None) -> str:
    if current in ["rejected_for_now", "avoid", "retired"]:
        return current
    if not grade:
        return current if current else "research_candidate"
    status = str(grade.get("status") or "")
    positive = _to_int(grade.get("positive_periods"), 0)
    weak = _to_int(grade.get("weak_periods"), 0)
    deep = _to_int(grade.get("deep_drop_periods"), 0)
    score = _to_float(grade.get("score"), 0)

    if status == "validated_candidate" and positive >= 3 and weak == 0 and deep == 0:
        if score >= 15:
            return "active_core_candidate"
        return "validated_candidate"
    if status == "needs_more_validation":
        return "watch_only"
    if status == "not_validated":
        return "rejected_for_now"
    return current


def _recommendation(previous: str, new: str, grade: dict[str, Any] | None) -> str:
    if new == "active_core_candidate":
        return "Eligible for next risk-mode review, but still research support only."
    if new == "validated_candidate":
        return "Promote from research candidate to validated candidate. Continue validation before active core."
    if new == "watch_only":
        return "Keep on watch list; needs more validation before promotion."
    if new == "rejected_for_now":
        return "Do not prioritize until rule or market filter changes."
    if new == previous:
        return "No promotion change."
    return "Review manually."


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("promoted_status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _human_summary(rows: list[dict[str, Any]]) -> str:
    changed = [x for x in rows if x.get("status_changed")]
    best = [x for x in rows if x.get("promoted_status") in ["validated_candidate", "active_core_candidate"]]
    parts = [f"{x.get('profile_id')} {x.get('previous_status')} -> {x.get('promoted_status')}" for x in changed]
    return (
        f"Profile promotion completed. Changed={len(changed)}. "
        f"Validated-or-better={len(best)}. "
        f"Changes: {' | '.join(parts) if parts else 'none'}."
    )


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "y", "on"]
    return default
