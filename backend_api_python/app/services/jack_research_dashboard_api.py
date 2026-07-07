from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.jack_daily_command_center import build_daily_command_center_v1
from app.services.jack_goal_backtest_engine import run_goal_backtest_v1
from app.services.jack_learning_engine import build_learning_report_v1
from app.services.jack_memory_report import build_memory_report_v1
from app.services.jack_profile_promotion import build_profile_promotion_v1
from app.services.jack_trade_journal import trade_journal_summary_v1, list_trade_journal_v1


VERSION = "research_dashboard_api_v1"


def build_research_dashboard_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    equity = _to_float(payload.get("equity"), 500.0)
    peak_equity = _to_float(payload.get("peak_equity"), equity)
    profile_id = str(payload.get("profile_id") or "GBPJPY_H4_UP_V1").strip()
    setup_quality = str(payload.get("setup_quality") or "A+").upper().strip()

    command = build_daily_command_center_v1({
        "equity": equity,
        "peak_equity": peak_equity,
        "profile_id": profile_id,
        "setup_quality": setup_quality,
    })
    goal = run_goal_backtest_v1({
        "start_equity": equity,
        "target_equity": _to_float(payload.get("target_equity"), 1000000.0),
        "save_memory": False,
    })
    promotion = build_profile_promotion_v1({"save_memory": False})
    learning = build_learning_report_v1({"limit": 300, "save_memory": False})
    memory = build_memory_report_v1({"limit": 300, "save_report": False})
    journal_summary = trade_journal_summary_v1({})
    recent_journal = list_trade_journal_v1({"limit": 5})

    cards = {
        "command_card": _command_card(command),
        "capital_card": _capital_card(command),
        "risk_card": _risk_card(command),
        "goal_card": _goal_card(goal),
        "profile_card": _profile_card(promotion, goal),
        "journal_card": _journal_card(journal_summary, recent_journal),
        "learning_card": _learning_card(learning),
        "memory_card": _memory_card(memory),
        "system_health_card": _system_health_card(command, goal, journal_summary),
    }

    report = {
        "version": VERSION,
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cards": cards,
        "raw": {
            "daily_command_center": command,
            "goal_backtest": goal,
            "profile_promotion": promotion,
            "learning_report": learning,
            "memory_report": memory,
            "journal_summary": journal_summary,
            "recent_journal": recent_journal,
        },
        "ui_order": [
            "command_card",
            "capital_card",
            "risk_card",
            "goal_card",
            "profile_card",
            "journal_card",
            "learning_card",
            "memory_card",
            "system_health_card",
        ],
        "human_summary": "",
        "notes": [
            "Dashboard API prepares UI-ready personal research data.",
            "It does not connect to a broker and does not create live instructions.",
        ],
    }
    report["human_summary"] = _human_summary(report)
    return report


def _command_card(command: dict[str, Any]) -> dict[str, Any]:
    status = command.get("command_status") or {}
    return {
        "title": "Daily Command",
        "status": status.get("level"),
        "primary_value": status.get("risk_mode"),
        "secondary_value": f"max research risk {status.get('max_research_risk_percent')}%",
        "items": command.get("today_focus") or [],
    }


def _capital_card(command: dict[str, Any]) -> dict[str, Any]:
    stage = command.get("capital_stage") or {}
    progress = command.get("capital_progress") or {}
    return {
        "title": "Capital Stage",
        "status": stage.get("stage"),
        "primary_value": f"progress {progress.get('percent')}%",
        "secondary_value": f"remaining {progress.get('remaining_to_next_stage')}",
        "items": [
            f"Target: {stage.get('target_equity')}",
            f"Purpose: {stage.get('purpose')}",
        ],
    }


def _risk_card(command: dict[str, Any]) -> dict[str, Any]:
    risk = command.get("risk_mode") or {}
    return {
        "title": "Risk Mode",
        "status": risk.get("final_mode"),
        "primary_value": f"{risk.get('max_research_risk_percent')}%",
        "secondary_value": risk.get("capital_stage"),
        "items": risk.get("reason_flags") or [],
    }


def _goal_card(goal: dict[str, Any]) -> dict[str, Any]:
    summary = goal.get("summary") or {}
    ranked = goal.get("ranked_profiles") or []
    best = ranked[0] if ranked else {}
    return {
        "title": "Goal Backtest",
        "status": best.get("target_possible"),
        "primary_value": f"score {best.get('goal_fit_score')}",
        "secondary_value": best.get("profile_id"),
        "items": [
            summary.get("human_summary"),
            f"Best stage: {best.get('best_stage')}",
            f"Use: {best.get('recommended_use')}",
        ],
        "top_profiles": ranked[:5],
        "stage_recommendations": summary.get("stage_recommendations") or {},
    }


def _profile_card(promotion: dict[str, Any], goal: dict[str, Any]) -> dict[str, Any]:
    summary = promotion.get("summary") or {}
    ranked = goal.get("ranked_profiles") or []
    return {
        "title": "Profiles",
        "status": "ready",
        "primary_value": summary.get("status_counts"),
        "secondary_value": f"goal ranked {len(ranked)}",
        "items": summary.get("promotions") or [],
    }


def _journal_card(summary: dict[str, Any], recent: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Journal",
        "status": "low_data" if (summary.get("closed_items") or 0) == 0 else "learning",
        "primary_value": f"total {summary.get('total_items')}",
        "secondary_value": f"closed {summary.get('closed_items')}",
        "items": [summary.get("human_summary")],
        "recent": recent.get("items") or [],
    }


def _learning_card(learning: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "Learning",
        "status": "low_data" if learning.get("journal_items_scanned") == 0 else "active",
        "primary_value": f"scanned {learning.get('journal_items_scanned')}",
        "secondary_value": None,
        "items": learning.get("next_actions") or [],
        "behavior_notes": learning.get("behavior_notes") or [],
    }


def _memory_card(memory: dict[str, Any]) -> dict[str, Any]:
    summary = memory.get("summary") or {}
    return {
        "title": "Memory",
        "status": "active",
        "primary_value": f"items {summary.get('total_items')}",
        "secondary_value": f"top candidates {len(summary.get('top_candidates') or [])}",
        "items": summary.get("next_research") or [],
    }


def _system_health_card(command: dict[str, Any], goal: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    issues = []
    if (journal.get("closed_items") or 0) == 0:
        issues.append("journal_has_no_closed_records")
    if not (goal.get("ranked_profiles") or []):
        issues.append("goal_backtest_no_ranked_profiles")
    if not command.get("ok"):
        issues.append("daily_command_center_not_ok")
    return {
        "title": "System Health",
        "status": "ok" if not issues else "needs_data",
        "primary_value": "v1 API ready" if not issues else "needs more journal data",
        "secondary_value": VERSION,
        "items": issues or ["dashboard_data_ready"],
    }


def _human_summary(report: dict[str, Any]) -> str:
    cards = report.get("cards") or {}
    command = cards.get("command_card") or {}
    goal = cards.get("goal_card") or {}
    health = cards.get("system_health_card") or {}
    return (
        f"Research Dashboard ready. Command={command.get('status')} risk={command.get('primary_value')} "
        f"goal={goal.get('secondary_value')} {goal.get('primary_value')} health={health.get('status')}."
    )


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
