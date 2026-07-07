from __future__ import annotations

from typing import Any

from app.services.jack_memory_store import add_memory_v1
from app.services.jack_profile_promotion import build_profile_promotion_v1


VERSION = "risk_mode_engine_v2"


def calculate_risk_mode_v2(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    equity = _to_float(payload.get("equity"), 500.0)
    peak_equity = _to_float(payload.get("peak_equity"), equity)
    profile_id = str(payload.get("profile_id") or "GBPJPY_H4_UP_V1").strip()
    setup_quality = str(payload.get("setup_quality") or "A").upper().strip()
    save = _bool(payload.get("save_memory"), True)

    drawdown_percent = _drawdown(equity, peak_equity)
    capital_stage = _capital_stage(equity)
    promotion_report = build_profile_promotion_v1({"save_memory": False})
    profile = _find_profile(promotion_report, profile_id)
    profile_status = str(profile.get("promoted_status") or "unknown")

    base_mode = _mode_from_drawdown(drawdown_percent)
    profile_gate = _profile_gate(profile_status)
    setup_gate = _setup_gate(setup_quality)
    final_mode = _combine_mode(base_mode, profile_gate, setup_gate)
    max_risk_percent = _risk_percent(capital_stage, final_mode, profile_status, setup_quality)

    decision = {
        "version": VERSION,
        "ok": True,
        "equity": equity,
        "peak_equity": peak_equity,
        "drawdown_percent": drawdown_percent,
        "capital_stage": capital_stage,
        "profile_id": profile_id,
        "profile_status": profile_status,
        "setup_quality": setup_quality,
        "base_mode": base_mode,
        "profile_gate": profile_gate,
        "setup_gate": setup_gate,
        "final_mode": final_mode,
        "max_research_risk_percent": max_risk_percent,
        "allowed_for_research_watch": final_mode not in ["PAUSE", "BLOCK"],
        "profile_summary": profile.get("recommendation"),
        "reason_flags": _reason_flags(drawdown_percent, capital_stage, profile_status, setup_quality, final_mode),
        "human_summary": "",
        "notes": [
            "Research support only.",
            "This endpoint does not connect to a broker and does not create live instructions.",
            "The output is a risk framework for review, not an automatic action.",
        ],
    }
    decision["human_summary"] = _human_summary(decision)

    if save:
        saved = add_memory_v1({
            "memory_type": "risk_mode_report",
            "symbol": str(profile.get("symbol") or "MULTI"),
            "title": f"Risk Mode {profile_id}",
            "content": decision["human_summary"],
            "tags": [VERSION, final_mode, capital_stage, profile_status],
            "source": VERSION,
            "metadata": decision,
        })
        decision["memory_id"] = (saved.get("memory") or {}).get("memory_id")

    return decision


def _capital_stage(equity: float) -> str:
    if equity < 2000:
        return "STAGE_1_500_TO_2K"
    if equity < 10000:
        return "STAGE_2_2K_TO_10K"
    if equity < 100000:
        return "STAGE_3_10K_TO_100K"
    if equity < 1000000:
        return "STAGE_4_100K_TO_1M"
    return "STAGE_5_1M_PLUS"


def _mode_from_drawdown(drawdown: float) -> str:
    if drawdown <= -25:
        return "PAUSE"
    if drawdown <= -20:
        return "DEFENSE"
    if drawdown <= -10:
        return "REDUCED"
    if drawdown <= -5:
        return "CAUTION"
    return "NORMAL"


def _profile_gate(status: str) -> str:
    if status in ["active_core_candidate", "validated_candidate"]:
        return "ALLOW_REVIEW"
    if status in ["research_candidate", "active_candidate", "watch_only"]:
        return "WATCH_ONLY"
    if status in ["rejected_for_now", "retired", "avoid"]:
        return "BLOCK"
    return "WATCH_ONLY"


def _setup_gate(quality: str) -> str:
    if quality in ["S", "A+", "A"]:
        return "QUALITY_OK"
    if quality in ["B", "C"]:
        return "LOW_PRIORITY"
    return "UNKNOWN_QUALITY"


def _combine_mode(base: str, profile_gate: str, setup_gate: str) -> str:
    if profile_gate == "BLOCK":
        return "BLOCK"
    if base == "PAUSE":
        return "PAUSE"
    if setup_gate in ["LOW_PRIORITY", "UNKNOWN_QUALITY"]:
        return "WAIT"
    if profile_gate == "WATCH_ONLY":
        return "WATCH"
    return base


def _risk_percent(stage: str, mode: str, profile_status: str, quality: str) -> float:
    if mode in ["BLOCK", "PAUSE", "WAIT"]:
        return 0.0

    table = {
        "STAGE_1_500_TO_2K": {"A": 3.0, "A+": 4.0, "S": 5.0},
        "STAGE_2_2K_TO_10K": {"A": 3.0, "A+": 4.0, "S": 5.0},
        "STAGE_3_10K_TO_100K": {"A": 1.5, "A+": 3.0, "S": 4.0},
        "STAGE_4_100K_TO_1M": {"A": 1.0, "A+": 2.0, "S": 3.0},
        "STAGE_5_1M_PLUS": {"A": 0.5, "A+": 1.0, "S": 1.5},
    }
    q = quality if quality in ["A", "A+", "S"] else "A"
    risk = table.get(stage, table["STAGE_1_500_TO_2K"]).get(q, 1.0)

    if profile_status == "watch_only":
        risk *= 0.25
    elif profile_status in ["research_candidate", "active_candidate"]:
        risk *= 0.5
    elif profile_status == "validated_candidate":
        risk *= 0.75
    elif profile_status == "active_core_candidate":
        risk *= 1.0

    if mode == "WATCH":
        risk *= 0.5
    elif mode == "CAUTION":
        risk *= 0.5
    elif mode == "REDUCED":
        risk *= 0.35
    elif mode == "DEFENSE":
        risk *= 0.2

    return round(max(0.0, min(risk, 5.0)), 3)


def _find_profile(report: dict[str, Any], profile_id: str) -> dict[str, Any]:
    promotions = ((report.get("summary") or {}).get("promotions") or [])
    for row in promotions:
        if row.get("profile_id") == profile_id:
            return row
    return {}


def _drawdown(equity: float, peak: float) -> float:
    if peak <= 0:
        return 0.0
    if equity > peak:
        peak = equity
    return round((equity - peak) / peak * 100, 4)


def _reason_flags(drawdown: float, stage: str, profile_status: str, quality: str, mode: str) -> list[str]:
    flags = [stage, f"profile_{profile_status}", f"quality_{quality}", f"mode_{mode}"]
    if drawdown <= -25:
        flags.append("drawdown_pause_zone")
    elif drawdown <= -20:
        flags.append("drawdown_defense_zone")
    elif drawdown <= -10:
        flags.append("drawdown_reduced_zone")
    elif drawdown <= -5:
        flags.append("drawdown_caution_zone")
    else:
        flags.append("drawdown_normal_zone")
    return flags


def _human_summary(d: dict[str, Any]) -> str:
    return (
        f"Risk mode result: profile={d.get('profile_id')} status={d.get('profile_status')} "
        f"equity={d.get('equity')} peak={d.get('peak_equity')} drawdown={d.get('drawdown_percent')}% "
        f"stage={d.get('capital_stage')} setup={d.get('setup_quality')} final_mode={d.get('final_mode')} "
        f"max_research_risk={d.get('max_research_risk_percent')}%. Research support only."
    )


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
