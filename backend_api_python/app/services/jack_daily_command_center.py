from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.jack_capital_stage_engine import build_capital_stage_v1
from app.services.jack_learning_engine import build_learning_report_v1
from app.services.jack_memory_report import build_memory_report_v1
from app.services.jack_profile_promotion import build_profile_promotion_v1
from app.services.jack_trade_journal import trade_journal_summary_v1, list_trade_journal_v1


VERSION = "daily_command_center_v1"


def build_daily_command_center_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    equity = _to_float(payload.get("equity"), 500.0)
    peak_equity = _to_float(payload.get("peak_equity"), equity)
    profile_id = str(payload.get("profile_id") or "GBPJPY_H4_UP_V1").strip()
    setup_quality = str(payload.get("setup_quality") or "A+").upper().strip()

    capital = build_capital_stage_v1({
        "equity": equity,
        "peak_equity": peak_equity,
        "profile_id": profile_id,
        "setup_quality": setup_quality,
        "save_memory": False,
    })

    promotion = build_profile_promotion_v1({"save_memory": False})
    memory = build_memory_report_v1({"limit": 300, "save_report": False})
    learning = build_learning_report_v1({"limit": 300, "save_memory": False})
    journal_summary = trade_journal_summary_v1({})
    recent_journal = list_trade_journal_v1({"limit": 5})

    command = _command_status(capital)
    today_focus = _today_focus(command, capital, promotion, learning, journal_summary)

    report = {
        "version": VERSION,
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command_status": command,
        "equity": equity,
        "peak_equity": peak_equity,
        "profile_id": profile_id,
        "setup_quality": setup_quality,
        "capital_stage": capital.get("stage"),
        "capital_progress": capital.get("progress"),
        "risk_mode": capital.get("risk_mode"),
        "stage_rules": capital.get("stage_rules"),
        "profile_promotion_summary": promotion.get("summary") or {},
        "memory_summary": memory.get("summary") or {},
        "learning_summary": {
            "human_summary": learning.get("human_summary"),
            "behavior_notes": learning.get("behavior_notes"),
            "next_actions": learning.get("next_actions"),
        },
        "journal_summary": journal_summary,
        "recent_journal": recent_journal.get("items") or [],
        "today_focus": today_focus,
        "human_summary": "",
        "notes": [
            "Daily Command Center is a personal research and review dashboard.",
            "No broker connection and no live automation.",
        ],
    }
    report["human_summary"] = _human_summary(report)
    return report


def _command_status(capital: dict[str, Any]) -> dict[str, Any]:
    risk = capital.get("risk_mode") or {}
    mode = str(risk.get("final_mode") or "UNKNOWN")

    if mode in ["PAUSE", "BLOCK"]:
        level = "STOP_REVIEW"
    elif mode == "DEFENSE":
        level = "DEFENSE_REVIEW_ONLY"
    elif mode in ["REDUCED", "CAUTION", "WATCH"]:
        level = "CAUTION_REVIEW_ONLY"
    elif mode == "NORMAL":
        level = "NORMAL_REVIEW"
    else:
        level = "WAIT"

    return {
        "level": level,
        "risk_mode": mode,
        "max_research_risk_percent": risk.get("max_research_risk_percent"),
        "allowed_for_research_watch": risk.get("allowed_for_research_watch"),
        "reason_flags": risk.get("reason_flags") or [],
    }


def _today_focus(
    command: dict[str, Any],
    capital: dict[str, Any],
    promotion: dict[str, Any],
    learning: dict[str, Any],
    journal: dict[str, Any],
) -> list[str]:
    focus = []
    level = command.get("level")

    if level == "NORMAL_REVIEW":
        focus.append("Review only validated or better profiles; avoid random ideas.")
    elif level == "DEFENSE_REVIEW_ONLY":
        focus.append("Defense day: reduce activity, review journal, and protect capital path.")
    elif level in ["STOP_REVIEW", "WAIT"]:
        focus.append("No new priority review; use the day for learning and journal cleanup.")
    else:
        focus.append("Caution day: only review strongest prepared profiles.")

    stage = capital.get("stage") or {}
    focus.append(f"Current stage: {stage.get('stage')} target={stage.get('target_equity')}.")

    promo_summary = promotion.get("summary") or {}
    counts = promo_summary.get("status_counts") or {}
    validated_count = (
        (counts.get("validated_candidate") or 0)
        + (counts.get("active_core_candidate") or 0)
    )
    focus.append(f"Validated-or-better profiles: {validated_count}.")

    if (journal.get("closed_items") or 0) == 0:
        focus.append("Close or review at least one journal record with result_r and mistakes.")

    for action in learning.get("next_actions") or []:
        focus.append(str(action))

    return focus[:8]


def _human_summary(report: dict[str, Any]) -> str:
    command = report.get("command_status") or {}
    stage = report.get("capital_stage") or {}
    progress = report.get("capital_progress") or {}
    journal = report.get("journal_summary") or {}

    return (
        f"Daily Command Center: status={command.get('level')} "
        f"risk_mode={command.get('risk_mode')} "
        f"max_research_risk={command.get('max_research_risk_percent')}%. "
        f"stage={stage.get('stage')} progress={progress.get('percent')}% "
        f"remaining={progress.get('remaining_to_next_stage')}. "
        f"journal_total={journal.get('total_items')} closed={journal.get('closed_items')}. "
        f"Focus: {' | '.join(report.get('today_focus') or [])}"
    )


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



