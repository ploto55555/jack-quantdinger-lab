from __future__ import annotations

from typing import Any

from app.services.jack_memory_store import add_memory_v1
from app.services.jack_risk_mode_v2 import calculate_risk_mode_v2


VERSION = "capital_stage_engine_v1"

STAGE_PLAN = [
    {
        "stage": "STAGE_1_500_TO_2K",
        "min_equity": 500,
        "max_equity": 2000,
        "target_equity": 2000,
        "purpose": "Survival plus early compounding. Only strongest validated research setups should be reviewed.",
        "focus": ["protect account", "use only A/A+/S quality", "avoid frequent low-quality ideas"],
    },
    {
        "stage": "STAGE_2_2K_TO_10K",
        "min_equity": 2000,
        "max_equity": 10000,
        "target_equity": 10000,
        "purpose": "Small-account compounding. Still strict, but can review more validated candidates.",
        "focus": ["keep risk controlled", "expand validated candidates", "continue memory learning"],
    },
    {
        "stage": "STAGE_3_10K_TO_100K",
        "min_equity": 10000,
        "max_equity": 100000,
        "target_equity": 100000,
        "purpose": "Professional discipline stage. Reduce base risk and focus on consistency.",
        "focus": ["reduce ordinary risk", "track drawdown", "separate research and execution review"],
    },
    {
        "stage": "STAGE_4_100K_TO_1M",
        "min_equity": 100000,
        "max_equity": 1000000,
        "target_equity": 1000000,
        "purpose": "Capital protection plus selective growth. Avoid emotional acceleration.",
        "focus": ["protect capital", "only validated/core profiles", "defense rules matter more"],
    },
    {
        "stage": "STAGE_5_1M_PLUS",
        "min_equity": 1000000,
        "max_equity": None,
        "target_equity": None,
        "purpose": "Wealth management phase. Capital allocation and survival dominate.",
        "focus": ["allocation", "low risk", "separate defensive capital", "avoid over-concentration"],
    },
]


def build_capital_stage_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    equity = _to_float(payload.get("equity"), 500.0)
    peak_equity = _to_float(payload.get("peak_equity"), equity)
    profile_id = str(payload.get("profile_id") or "GBPJPY_H4_UP_V1").strip()
    setup_quality = str(payload.get("setup_quality") or "A+").upper().strip()
    save = _bool(payload.get("save_memory"), True)

    stage = _get_stage(equity)
    progress = _stage_progress(equity, stage)
    risk = calculate_risk_mode_v2({
        "equity": equity,
        "peak_equity": peak_equity,
        "profile_id": profile_id,
        "setup_quality": setup_quality,
        "save_memory": False,
    })
    rules = _stage_rules(stage, risk)

    report = {
        "version": VERSION,
        "ok": True,
        "equity": equity,
        "peak_equity": peak_equity,
        "stage": stage,
        "progress": progress,
        "risk_mode": risk,
        "stage_rules": rules,
        "human_summary": "",
        "notes": [
            "Research support only.",
            "This endpoint does not connect to a broker and does not create live instructions.",
            "Capital stage rules are a framework for review and discipline.",
        ],
    }
    report["human_summary"] = _human_summary(report)

    if save:
        saved = add_memory_v1({
            "memory_type": "capital_stage_report",
            "symbol": "MULTI",
            "title": f"Capital Stage {stage.get('stage')}",
            "content": report["human_summary"],
            "tags": [VERSION, stage.get("stage"), risk.get("final_mode")],
            "source": VERSION,
            "metadata": report,
        })
        report["memory_id"] = (saved.get("memory") or {}).get("memory_id")

    return report


def build_capital_path_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    equity = _to_float(payload.get("equity"), 500.0)
    rows = []
    for stage in STAGE_PLAN:
        rows.append({
            "stage": stage.get("stage"),
            "target_equity": stage.get("target_equity"),
            "current_stage": stage.get("stage") == _get_stage(equity).get("stage"),
            "purpose": stage.get("purpose"),
            "focus": stage.get("focus"),
        })
    return {
        "version": VERSION,
        "ok": True,
        "current_equity": equity,
        "current_stage": _get_stage(equity),
        "path": rows,
    }


def _get_stage(equity: float) -> dict[str, Any]:
    for stage in STAGE_PLAN:
        low = _to_float(stage.get("min_equity"), 0)
        high = stage.get("max_equity")
        if high is None and equity >= low:
            return dict(stage)
        if high is not None and equity >= low and equity < _to_float(high, 0):
            return dict(stage)
    return dict(STAGE_PLAN[0])


def _stage_progress(equity: float, stage: dict[str, Any]) -> dict[str, Any]:
    low = _to_float(stage.get("min_equity"), 0)
    high_value = stage.get("max_equity")
    target = stage.get("target_equity")
    if high_value is None or target is None:
        return {"percent": None, "remaining_to_next_stage": None, "next_target": None}
    high = _to_float(high_value, low)
    percent = ((equity - low) / (high - low) * 100) if high > low else 0
    percent = max(0, min(percent, 100))
    return {
        "percent": round(percent, 2),
        "remaining_to_next_stage": round(max(0, high - equity), 2),
        "next_target": high,
    }


def _stage_rules(stage: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    stage_id = str(stage.get("stage") or "")
    mode = str(risk.get("final_mode") or "")
    rules = {
        "can_accelerate": False,
        "can_review_validated_candidate": mode in ["NORMAL", "CAUTION", "REDUCED", "WATCH", "DEFENSE"],
        "must_pause": mode in ["PAUSE", "BLOCK"],
        "max_research_risk_percent": risk.get("max_research_risk_percent"),
        "stage_warning": None,
    }

    if stage_id in ["STAGE_1_500_TO_2K", "STAGE_2_2K_TO_10K"]:
        rules["can_accelerate"] = mode == "NORMAL" and risk.get("profile_status") in ["validated_candidate", "active_core_candidate"]
        rules["stage_warning"] = "Small account stage: avoid random research ideas; only review strong validated profiles."
    elif stage_id == "STAGE_3_10K_TO_100K":
        rules["can_accelerate"] = mode == "NORMAL" and risk.get("profile_status") == "active_core_candidate"
        rules["stage_warning"] = "Discipline stage: reduce ordinary risk and protect compounding progress."
    elif stage_id == "STAGE_4_100K_TO_1M":
        rules["can_accelerate"] = False
        rules["stage_warning"] = "Protection stage: selective review only; drawdown control dominates."
    else:
        rules["can_accelerate"] = False
        rules["stage_warning"] = "Wealth stage: allocation and capital defense dominate growth speed."

    return rules


def _human_summary(report: dict[str, Any]) -> str:
    stage = report.get("stage") or {}
    progress = report.get("progress") or {}
    risk = report.get("risk_mode") or {}
    return (
        f"Capital stage result: equity={report.get('equity')} stage={stage.get('stage')} "
        f"progress={progress.get('percent')}% remaining={progress.get('remaining_to_next_stage')} "
        f"risk_mode={risk.get('final_mode')} max_research_risk={risk.get('max_research_risk_percent')}%. "
        f"Purpose: {stage.get('purpose')}"
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
