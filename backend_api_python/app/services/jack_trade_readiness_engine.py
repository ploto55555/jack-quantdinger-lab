from __future__ import annotations

from typing import Any, Dict, List

from app.services.jack_goal_planner import get_goal_mode_v1
from app.services.jack_strategy_selector_v2 import select_strategy_v2
from app.services.jack_timeframe_signal_engine import build_four_timeframe_signals_v1


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round(value: float, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _flatten_signal_blockers(signals: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    for tf in ["D1", "H1", "M15", "M5"]:
        tf_data = signals.get("signals", {}).get(tf, {})
        blockers.extend(tf_data.get("blockers", []) or [])
    blockers.extend(signals.get("blockers", []) or [])
    # de-duplicate while keeping order
    result = []
    for item in blockers:
        if item and item not in result:
            result.append(item)
    return result


def _flatten_signal_reasons(signals: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    for tf in ["D1", "H1", "M15", "M5"]:
        tf_data = signals.get("signals", {}).get(tf, {})
        reasons.extend(tf_data.get("reasons", []) or [])
    reasons.extend(signals.get("reasons", []) or [])
    result = []
    for item in reasons:
        if item and item not in result:
            result.append(item)
    return result


def _command_to_stage(command: str) -> str:
    if command in {"MAIN_READY", "A_PLUS_READY"}:
        return "READY"
    if command in {"A_PLUS_WATCH", "A_PLUS_ONLY_WATCH", "WATCH"}:
        return "WATCH"
    if command in {"WAIT", "MAIN_ONLY_NO_FORCE"}:
        return "WAIT"
    if command in {"NO_TRADE", "WAIT_NEWS_RISK", "WAIT_MARKET_UNCLEAR"}:
        return "NO_TRADE"
    if command in {"STOP_AND_REVIEW", "DEFENSE_PAUSE"}:
        return "DEFENSE"
    return "WAIT"


def build_trade_readiness_v2(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Combine goal, strategy selection, and 4-timeframe signals.

    This is the final readiness brain before a trade plan generator. It gives
    WAIT/WATCH/READY/PREPARE/NO_TRADE/DEFENSE, but never places orders.
    """
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()

    signals = build_four_timeframe_signals_v1({"symbol": symbol})

    base_goal_payload = {
        "start_equity": payload.get("start_equity", 500),
        "target_equity": payload.get("target_equity", 100000),
        "current_equity": payload.get("current_equity", payload.get("equity", 500)),
        "peak_equity": payload.get("peak_equity", payload.get("current_equity", payload.get("equity", 500))),
        "elapsed_days": payload.get("elapsed_days", 0),
        "total_days": payload.get("total_days", 365),
        "consecutive_losses": payload.get("consecutive_losses", 0),
        "news_risk": payload.get("news_risk", "unknown"),
        "market_quality": payload.get("market_quality", "normal"),
    }

    if not signals.get("ok"):
        goal_mode = get_goal_mode_v1(base_goal_payload)
        return {
            "version": "trade_readiness_v2",
            "ok": False,
            "mode": "personal_research_support_only",
            "broker_connection": False,
            "auto_trading": False,
            "symbol": symbol,
            "final_command": "NO_DATA",
            "readiness_stage": "NO_TRADE",
            "readiness_score": 0,
            "reason": "Missing market data. Cannot calculate 4-timeframe signals.",
            "goal_mode": goal_mode,
            "four_timeframe_signals": signals,
            "strategy_selector": None,
            "blockers": signals.get("missing_timeframes", []),
            "next_action": "Fix data feed before evaluating any setup.",
        }

    selector_inputs = dict(signals.get("strategy_selector_inputs", {}))
    selector_payload = {
        **base_goal_payload,
        "symbol": symbol,
        "direction": selector_inputs.get("direction", "auto"),
        "d1_signal": selector_inputs.get("d1_signal", "unknown"),
        "h1_regime": selector_inputs.get("h1_regime", "unknown"),
        "m15_signal": selector_inputs.get("m15_signal", "unknown"),
        "m5_signal": selector_inputs.get("m5_signal", "unknown"),
        "market_quality": selector_inputs.get("market_quality", base_goal_payload.get("market_quality", "normal")),
    }

    goal_mode = get_goal_mode_v1(selector_payload)
    selector = select_strategy_v2(selector_payload)

    signal_final = signals.get("final_signal", "WAIT")
    selector_command = selector.get("selection", {}).get("final_command", "WAIT")
    selector_stage = _command_to_stage(selector_command)
    signal_blockers = _flatten_signal_blockers(signals)
    signal_reasons = _flatten_signal_reasons(signals)
    selector_blockers = selector.get("selection", {}).get("blockers", []) or []
    selector_reasons = selector.get("selection", {}).get("reasons", []) or []

    final_command = "WAIT"
    readiness_stage = "WAIT"
    readiness_score = _safe_float(selector.get("selection", {}).get("readiness_score", 0), 0)
    reason = "Default wait."

    if goal_mode.get("decision", {}).get("command") in {"STOP_AND_REVIEW", "WAIT_NEWS_RISK", "WAIT_MARKET_UNCLEAR"}:
        final_command = goal_mode.get("decision", {}).get("command")
        readiness_stage = _command_to_stage(final_command)
        reason = goal_mode.get("decision", {}).get("reason", "Goal mode blocks trading.")
    elif signal_blockers:
        final_command = "WAIT_SIGNAL_BLOCKED"
        readiness_stage = "WAIT"
        readiness_score = min(readiness_score, 49)
        reason = "4-timeframe signal has blockers. Wait until D1/H1/M15/M5 align."
    elif signal_final == "ENTRY_CONFIRMATION" and selector_stage == "READY":
        final_command = selector_command
        readiness_stage = "READY"
        readiness_score = max(readiness_score, 90)
        reason = "Goal, selected setup, and 4-timeframe confirmation are aligned. Prepare trade plan for manual confirmation."
    elif signal_final in {"PREPARE", "READY"} and selector_stage == "READY":
        final_command = selector_command
        readiness_stage = "PREPARE"
        readiness_score = max(readiness_score, 80)
        reason = "Setup is close or triggered. Prepare plan, but wait for final manual chart confirmation."
    elif signal_final == "WATCH" and selector_stage in {"READY", "WATCH"}:
        final_command = "WATCH"
        readiness_stage = "WATCH"
        readiness_score = max(min(readiness_score, 75), 55)
        reason = "Setup is forming but not ready. Watch only."
    elif selector_stage == "NO_TRADE":
        final_command = selector_command
        readiness_stage = "NO_TRADE"
        readiness_score = min(readiness_score, 30)
        reason = "Strategy selector blocks trading."
    elif selector_stage == "DEFENSE":
        final_command = selector_command
        readiness_stage = "DEFENSE"
        readiness_score = 0
        reason = "Account is in defense/pause mode."
    else:
        final_command = "WAIT"
        readiness_stage = "WAIT"
        reason = "Conditions are not aligned enough for preparation."

    combined_blockers = []
    for item in signal_blockers + selector_blockers:
        if item and item not in combined_blockers:
            combined_blockers.append(item)

    combined_reasons = []
    for item in signal_reasons + selector_reasons:
        if item and item not in combined_reasons:
            combined_reasons.append(item)

    return {
        "version": "trade_readiness_v2",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "final_command": final_command,
        "readiness_stage": readiness_stage,
        "readiness_score": _round(readiness_score),
        "reason": reason,
        "selected_strategy_id": selector.get("selection", {}).get("selected_strategy_id"),
        "selected_mode": selector.get("selection", {}).get("selected_mode"),
        "direction": signals.get("signals", {}).get("M15", {}).get("direction", "none"),
        "entry_context": {
            "entry_price": signals.get("signals", {}).get("M15", {}).get("entry_price"),
            "distance_to_entry_pips": signals.get("signals", {}).get("M15", {}).get("distance_to_entry_pips"),
            "yesterday_high": signals.get("signals", {}).get("M15", {}).get("yesterday_high"),
            "yesterday_low": signals.get("signals", {}).get("M15", {}).get("yesterday_low"),
        },
        "goal_summary": {
            "goal_mode": goal_mode.get("decision", {}).get("goal_mode"),
            "goal_command": goal_mode.get("decision", {}).get("command"),
            "path_ratio": goal_mode.get("goal_path", {}).get("target_math", {}).get("path_ratio"),
            "progress_percent": goal_mode.get("goal_path", {}).get("target_math", {}).get("progress_percent"),
            "drawdown_percent": goal_mode.get("account_state", {}).get("drawdown_percent"),
        },
        "four_timeframe_summary": {
            "final_signal": signal_final,
            "D1": signals.get("signals", {}).get("D1", {}).get("signal"),
            "H1": signals.get("signals", {}).get("H1", {}).get("regime"),
            "M15": signals.get("signals", {}).get("M15", {}).get("signal"),
            "M5": signals.get("signals", {}).get("M5", {}).get("signal"),
        },
        "reasons": combined_reasons,
        "blockers": combined_blockers,
        "next_action": _next_action(readiness_stage),
        "goal_mode": goal_mode,
        "four_timeframe_signals": signals,
        "strategy_selector": selector,
    }


def _next_action(stage: str) -> str:
    if stage == "READY":
        return "Generate a trade plan next. Final execution remains manual."
    if stage == "PREPARE":
        return "Prepare the trade plan and wait for final M5/manual confirmation."
    if stage == "WATCH":
        return "Watch the setup. Do not prepare order until M15/M5 improves."
    if stage == "DEFENSE":
        return "Stop new trades and review drawdown/rules."
    if stage == "NO_TRADE":
        return "No new trade. Wait for cleaner conditions."
    return "Wait. Do not force a trade."
