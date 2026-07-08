from __future__ import annotations

from typing import Any, Dict

from app.services.jack_trade_readiness_engine import build_trade_readiness_v2

PIP_SIZE = 0.01


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _price(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _blocked(readiness: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "status": "NO_VALID_PLAN_YET",
        "can_generate_plan": False,
        "reason": reason,
        "direction": readiness.get("direction", "none"),
        "draft_levels": None,
        "study_checklist": [
            "Do not act on a plan while the system is NO_TRADE or WAIT.",
            "Wait for D1, H1, M15, and M5 to align.",
            "Use this tool for research review only; it does not send orders.",
        ],
    }


def _draft_levels(readiness: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    stage = readiness.get("readiness_stage", "WAIT")
    direction = readiness.get("direction", "none")
    entry_context = readiness.get("entry_context", {}) or {}
    entry = _safe_float(entry_context.get("entry_price"), 0)

    if stage not in {"WATCH", "PREPARE", "READY"}:
        return _blocked(readiness, f"Current stage is {stage}. Plan draft is blocked until WATCH, PREPARE, or READY.")
    if direction not in {"long", "short"} or entry <= 0:
        return _blocked(readiness, "No valid direction or trigger level yet. Wait for H1 trend and M15 setup.")

    sl_pips = _safe_float(payload.get("study_sl_pips", 15), 15)
    r1 = _safe_float(payload.get("study_target_1r", 1), 1)
    r3 = _safe_float(payload.get("study_target_3r", 3), 3)
    r8 = _safe_float(payload.get("study_target_8r", 8), 8)

    if direction == "long":
        stop = entry - sl_pips * PIP_SIZE
        t1 = entry + sl_pips * r1 * PIP_SIZE
        t3 = entry + sl_pips * r3 * PIP_SIZE
        t8 = entry + sl_pips * r8 * PIP_SIZE
        source = "yesterday high plus SRDC buffer"
        invalid = "Study plan becomes invalid if higher-timeframe trend turns unclear before confirmation."
    else:
        stop = entry + sl_pips * PIP_SIZE
        t1 = entry - sl_pips * r1 * PIP_SIZE
        t3 = entry - sl_pips * r3 * PIP_SIZE
        t8 = entry - sl_pips * r8 * PIP_SIZE
        source = "yesterday low minus SRDC buffer"
        invalid = "Study plan becomes invalid if higher-timeframe trend turns unclear before confirmation."

    return {
        "status": "STUDY_PLAN_DRAFT",
        "can_generate_plan": True,
        "warning": "Research draft only. Manual review required. No broker action is performed.",
        "direction": direction,
        "trigger": {"price": _price(entry), "source": source},
        "study_stop_reference": {"price": _price(stop), "distance_pips": sl_pips},
        "study_targets": [
            {"label": "1R reference", "price": _price(t1), "r": r1},
            {"label": "3R reference", "price": _price(t3), "r": r3},
            {"label": "8R runner reference", "price": _price(t8), "r": r8},
        ],
        "invalidation": invalid,
        "risk_note": "Lot size and real risk are intentionally not calculated in v1. Connect broker contract/pip value later before using real sizing.",
        "study_checklist": [
            "Final command is WATCH, PREPARE, or READY.",
            "D1 still supports the same direction.",
            "H1 is clean trend in the same direction.",
            "M15 is near or through the SRDC trigger area.",
            "M5 is prepare or confirm, not wait.",
            "News risk and spread must be reviewed manually.",
            "If anything feels unclear, do not use the draft.",
        ],
    }


def build_trade_plan_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()
    readiness = build_trade_readiness_v2(payload | {"symbol": symbol})
    plan = _draft_levels(readiness, payload) if readiness.get("ok") else _blocked(readiness, "Readiness engine failed or data is missing.")

    return {
        "version": "trade_plan_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "final_command": readiness.get("final_command"),
        "readiness_stage": readiness.get("readiness_stage"),
        "readiness_score": readiness.get("readiness_score"),
        "selected_strategy_id": readiness.get("selected_strategy_id"),
        "plan": plan,
        "readiness": readiness,
        "note": "Research draft only. This is not financial advice and it does not place trades.",
    }
