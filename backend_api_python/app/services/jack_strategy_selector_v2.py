from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.jack_goal_planner import get_goal_mode_v1
from app.services.jack_strategy_library import (
    get_strategy_candidate_v1,
    list_strategy_candidates_v1,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
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


def _find_candidate_by_mode(mode: str) -> Optional[Dict[str, Any]]:
    result = list_strategy_candidates_v1({"mode": mode, "symbol": "GBPJPY", "limit": 10})
    candidates = result.get("candidates", [])
    if not candidates:
        return None
    return candidates[0]


def _find_candidate_by_id(strategy_id: str) -> Optional[Dict[str, Any]]:
    result = get_strategy_candidate_v1({"strategy_id": strategy_id})
    if result.get("ok"):
        return result.get("candidate")
    return None


def _score_market_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    d1_signal = str(payload.get("d1_signal", "unknown")).lower().strip()
    h1_regime = str(payload.get("h1_regime", "unknown")).lower().strip()
    m15_signal = str(payload.get("m15_signal", "unknown")).lower().strip()
    m5_signal = str(payload.get("m5_signal", "unknown")).lower().strip()
    direction = str(payload.get("direction", "unknown")).lower().strip()
    news_risk = str(payload.get("news_risk", "unknown")).lower().strip()
    market_quality = str(payload.get("market_quality", "normal")).lower().strip()

    score = 0
    reasons: List[str] = []
    blockers: List[str] = []

    if news_risk in {"high", "very_high"}:
        blockers.append("High news risk blocks new setup selection.")
    elif news_risk in {"low", "medium", "unknown"}:
        score += 5

    if h1_regime in {"trend", "clear_trend", "uptrend", "downtrend"}:
        score += 25
        reasons.append("H1 regime supports trend/breakout logic.")
    elif h1_regime in {"range", "unclear", "messy"}:
        blockers.append("H1 regime is range/unclear; SRDC runner should wait.")
    else:
        reasons.append("H1 regime is unknown; selector keeps confidence lower.")

    if d1_signal in {"long_only", "short_only", "trend_ok", "approved"}:
        score += 20
        reasons.append("D1 direction filter is supportive.")
    elif d1_signal in {"neutral", "unclear", "blocked"}:
        blockers.append("D1 direction is not supportive.")

    if m15_signal in {"setup_forming", "ready", "triggered"}:
        score += 20
        reasons.append("M15 setup is forming or ready.")
    elif m15_signal in {"invalid", "too_late", "fake_breakout_risk"}:
        blockers.append("M15 setup is invalid/too late/fake breakout risk.")

    if m5_signal in {"confirm", "entry_zone", "prepare"}:
        score += 10
        reasons.append("M5 supports execution confirmation.")
    elif m5_signal in {"invalid", "wait"}:
        reasons.append("M5 does not confirm yet; entry should wait.")

    if market_quality in {"very_strong", "a_plus"}:
        score += 20
        reasons.append("Market quality is very strong.")
    elif market_quality in {"normal", "good"}:
        score += 10
    elif market_quality in {"range", "unclear", "messy"}:
        blockers.append("Market quality is not suitable for SRDC runner.")

    if direction not in {"long", "short", "unknown", "auto"}:
        reasons.append("Direction input is non-standard; treated as unknown.")

    score = max(0, min(100, score))
    if blockers:
        score = min(score, 49)

    if score >= 85:
        label = "A_PLUS_READY"
    elif score >= 70:
        label = "MAIN_READY"
    elif score >= 55:
        label = "WATCH"
    elif score >= 40:
        label = "WAIT"
    else:
        label = "NO_TRADE"

    return {
        "score": score,
        "label": label,
        "reasons": reasons,
        "blockers": blockers,
        "inputs": {
            "d1_signal": d1_signal,
            "h1_regime": h1_regime,
            "m15_signal": m15_signal,
            "m5_signal": m5_signal,
            "direction": direction,
            "news_risk": news_risk,
            "market_quality": market_quality,
        },
    }


def select_strategy_v2(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Step 39 strategy selector.

    Combines the goal planner, account state, and four-timeframe market state to
    choose A+ / Main / Research / No Trade. It does not place orders.
    """
    payload = payload or {}

    goal_payload = {
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
    goal_mode = get_goal_mode_v1(goal_payload)
    market = _score_market_inputs(payload)

    goal_decision = goal_mode.get("decision", {})
    allowed_modes = set(goal_decision.get("allowed_setup_modes", []))
    goal_command = goal_decision.get("command", "MAIN_ONLY")

    final_command = "WAIT"
    selected_mode: Optional[str] = None
    selected_candidate: Optional[Dict[str, Any]] = None
    decision_reasons: List[str] = []
    decision_blockers: List[str] = []

    decision_reasons.append(goal_decision.get("reason", "Goal planner completed."))
    decision_reasons.extend(market.get("reasons", []))
    decision_blockers.extend(market.get("blockers", []))

    if not allowed_modes or goal_command in {"WAIT_NEWS_RISK", "WAIT_MARKET_UNCLEAR", "STOP_AND_REVIEW"}:
        final_command = goal_command if goal_command else "WAIT"
        decision_blockers.append("Goal planner does not allow setup selection.")
    elif market["label"] == "NO_TRADE":
        final_command = "NO_TRADE"
        decision_blockers.append("Market score is too low for setup selection.")
    elif market["label"] == "WAIT":
        final_command = "WAIT"
        decision_reasons.append("Market is not ready; continue watching only.")
    elif "a_plus_safe" in allowed_modes and (market["label"] == "A_PLUS_READY" or goal_command in {"STRICT_ONLY", "A_PLUS_ONLY"}):
        selected_mode = "a_plus_safe"
        selected_candidate = _find_candidate_by_mode("a_plus_safe")
        final_command = "A_PLUS_READY" if market["label"] == "A_PLUS_READY" else "A_PLUS_ONLY_WATCH"
    elif "main" in allowed_modes and market["label"] in {"MAIN_READY", "A_PLUS_READY"}:
        selected_mode = "main"
        selected_candidate = _find_candidate_by_mode("main")
        final_command = "MAIN_READY"
    elif "a_plus_safe" in allowed_modes and market["label"] in {"MAIN_READY", "WATCH"}:
        selected_mode = "a_plus_safe"
        selected_candidate = _find_candidate_by_mode("a_plus_safe")
        final_command = "A_PLUS_WATCH"
    elif market["label"] == "WATCH":
        final_command = "WATCH"
        decision_reasons.append("Setup is forming, but not ready enough for preparation.")
    else:
        final_command = "WAIT"
        decision_reasons.append("No allowed candidate matches the current goal and market state.")

    if selected_candidate is None and selected_mode:
        decision_blockers.append(f"No candidate found for selected mode: {selected_mode}")

    return {
        "version": "strategy_selector_v2",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "inputs": {
            "symbol": payload.get("symbol", "GBPJPY"),
            "direction": payload.get("direction", "auto"),
            "start_equity": _safe_float(goal_payload["start_equity"], 500),
            "target_equity": _safe_float(goal_payload["target_equity"], 100000),
            "current_equity": _safe_float(goal_payload["current_equity"], 500),
            "peak_equity": _safe_float(goal_payload["peak_equity"], 500),
            "elapsed_days": _safe_int(goal_payload["elapsed_days"], 0),
            "total_days": _safe_int(goal_payload["total_days"], 365),
        },
        "goal_mode": goal_mode,
        "market_score": market,
        "selection": {
            "final_command": final_command,
            "selected_mode": selected_mode,
            "selected_strategy_id": selected_candidate.get("id") if selected_candidate else None,
            "selected_role": selected_candidate.get("role") if selected_candidate else None,
            "readiness_score": market.get("score"),
            "readiness_label": market.get("label"),
            "reasons": decision_reasons,
            "blockers": decision_blockers,
        },
        "candidate": selected_candidate,
        "next_action": _next_action(final_command),
    }


def _next_action(command: str) -> str:
    if command in {"A_PLUS_READY", "MAIN_READY"}:
        return "Prepare the trade plan, but require final chart confirmation before any manual execution."
    if command in {"A_PLUS_WATCH", "A_PLUS_ONLY_WATCH", "WATCH"}:
        return "Watch only. Wait for the missing timeframe confirmation before preparing a plan."
    if command in {"NO_TRADE", "WAIT_NEWS_RISK", "WAIT_MARKET_UNCLEAR", "STOP_AND_REVIEW"}:
        return "No new trade. Review blockers and wait for a cleaner setup."
    return "Wait. Do not force a trade."
