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


def _no_draft(readiness: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "status": "NO_STUDY_DRAFT_YET",
        "can_build_study": False,
        "reason": reason,
        "direction_context": readiness.get("direction", "none"),
        "reference_levels": None,
        "manual_review_notes": [
            "No action should be taken while readiness is NO_TRADE or WAIT.",
            "Wait for D1, H1, M15, and M5 to align first.",
            "This module is only a study draft. It does not connect to any broker.",
        ],
    }


def _build_references(readiness: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    stage = readiness.get("readiness_stage", "WAIT")
    direction = readiness.get("direction", "none")
    context = readiness.get("entry_context", {}) or {}
    trigger = _safe_float(context.get("entry_price"), 0)

    if stage not in {"WATCH", "PREPARE", "READY"}:
        return _no_draft(readiness, f"Current stage is {stage}. Study draft waits until WATCH, PREPARE, or READY.")
    if direction not in {"long", "short"} or trigger <= 0:
        return _no_draft(readiness, "No valid direction or trigger reference yet. Wait for H1 trend and M15 setup.")

    study_gap_pips = _safe_float(payload.get("study_gap_pips", 15), 15)
    zone_1_units = _safe_float(payload.get("study_zone_1_units", 1), 1)
    zone_2_units = _safe_float(payload.get("study_zone_2_units", 3), 3)
    runner_units = _safe_float(payload.get("runner_units", 8), 8)

    if direction == "long":
        invalid = trigger - study_gap_pips * PIP_SIZE
        zone1 = trigger + study_gap_pips * zone_1_units * PIP_SIZE
        zone2 = trigger + study_gap_pips * zone_2_units * PIP_SIZE
        runner = trigger + study_gap_pips * runner_units * PIP_SIZE
        source = "yesterday high area plus SRDC buffer"
    else:
        invalid = trigger + study_gap_pips * PIP_SIZE
        zone1 = trigger - study_gap_pips * zone_1_units * PIP_SIZE
        zone2 = trigger - study_gap_pips * zone_2_units * PIP_SIZE
        runner = trigger - study_gap_pips * runner_units * PIP_SIZE
        source = "yesterday low area minus SRDC buffer"

    return {
        "status": "STUDY_DRAFT_READY",
        "can_build_study": True,
        "warning": "Study reference only. Manual review required. No broker action is performed.",
        "direction_context": direction,
        "trigger_reference": {
            "price": _price(trigger),
            "source": source,
        },
        "invalid_reference": {
            "price": _price(invalid),
            "study_gap_pips": study_gap_pips,
            "note": "Reference only. Do not treat as automatic execution instruction.",
        },
        "study_zones": [
            {"label": "study_zone_1", "price": _price(zone1), "unit": zone_1_units},
            {"label": "study_zone_2", "price": _price(zone2), "unit": zone_2_units},
        ],
        "runner_reference": {
            "price": _price(runner),
            "unit": runner_units,
            "note": "Only meaningful if market expansion remains clean.",
        },
        "size_note": "Real position sizing is not calculated here. This system remains research support only.",
        "manual_review_notes": [
            "Readiness must remain WATCH, PREPARE, or READY.",
            "D1 should still support the same direction context.",
            "H1 should be a clean trend in the same direction context.",
            "M15 should be near or through the SRDC reference area.",
            "M5 should be prepare or confirm, not wait.",
            "News and spread must be reviewed manually.",
            "If chart context feels unclear, ignore the study draft.",
        ],
    }


def build_setup_study_draft_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()
    readiness = build_trade_readiness_v2(payload | {"symbol": symbol})
    study = _build_references(readiness, payload) if readiness.get("ok") else _no_draft(readiness, "Readiness data is missing.")

    return {
        "version": "setup_study_draft_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "final_command": readiness.get("final_command"),
        "readiness_stage": readiness.get("readiness_stage"),
        "readiness_score": readiness.get("readiness_score"),
        "study": study,
        "readiness": readiness,
        "note": "This is a research study draft only. It is not financial advice and it does not place orders.",
    }
