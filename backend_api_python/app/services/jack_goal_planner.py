from __future__ import annotations

import math
from typing import Any, Dict, List


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


def build_goal_path_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build a target equity path for the personal capital OS.

    This is a planning and risk-control tool only. It does not place trades and
    it does not guarantee that the target can be reached.
    """
    payload = payload or {}
    start_equity = max(_safe_float(payload.get("start_equity", 500), 500), 1)
    target_equity = max(_safe_float(payload.get("target_equity", 100000), 100000), start_equity)
    current_equity = max(_safe_float(payload.get("current_equity", start_equity), start_equity), 0)
    elapsed_days = max(_safe_int(payload.get("elapsed_days", 0), 0), 0)
    total_days = max(_safe_int(payload.get("total_days", 365), 365), 1)

    required_multiple = target_equity / start_equity
    required_daily_growth = (required_multiple ** (1 / total_days)) - 1
    required_monthly_growth = (required_multiple ** (1 / 12)) - 1

    expected_equity_today = start_equity * ((1 + required_daily_growth) ** min(elapsed_days, total_days))
    progress_percent = (current_equity / target_equity) * 100 if target_equity else 0
    path_ratio = current_equity / expected_equity_today if expected_equity_today else 0

    checkpoints: List[Dict[str, Any]] = []
    for month in range(1, 13):
        day = round(total_days * month / 12)
        target_for_month = start_equity * ((1 + required_daily_growth) ** day)
        checkpoints.append(
            {
                "month": month,
                "day": day,
                "target_equity": _round(target_for_month, 2),
                "multiple_from_start": _round(target_for_month / start_equity, 2),
            }
        )

    return {
        "version": "goal_path_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "inputs": {
            "start_equity": start_equity,
            "target_equity": target_equity,
            "current_equity": current_equity,
            "elapsed_days": elapsed_days,
            "total_days": total_days,
        },
        "target_math": {
            "required_multiple": _round(required_multiple, 2),
            "required_daily_growth_percent": _round(required_daily_growth * 100, 3),
            "required_monthly_growth_percent": _round(required_monthly_growth * 100, 2),
            "expected_equity_today": _round(expected_equity_today, 2),
            "progress_percent": _round(progress_percent, 2),
            "path_ratio": _round(path_ratio, 3),
        },
        "checkpoints": checkpoints,
        "warning": "This is target-path math for research and planning. It is not a promise of future performance.",
    }


def get_goal_mode_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Decide Attack/Main/A+/Defense based on goal path and account state."""
    payload = payload or {}
    start_equity = _safe_float(payload.get("start_equity", 500), 500)
    target_equity = _safe_float(payload.get("target_equity", 100000), 100000)
    current_equity = _safe_float(payload.get("current_equity", start_equity), start_equity)
    peak_equity = max(_safe_float(payload.get("peak_equity", current_equity), current_equity), current_equity)
    elapsed_days = _safe_int(payload.get("elapsed_days", 0), 0)
    total_days = _safe_int(payload.get("total_days", 365), 365)
    consecutive_losses = _safe_int(payload.get("consecutive_losses", 0), 0)
    news_risk = str(payload.get("news_risk", "unknown")).lower().strip()
    market_quality = str(payload.get("market_quality", "normal")).lower().strip()

    path = build_goal_path_v1(
        {
            "start_equity": start_equity,
            "target_equity": target_equity,
            "current_equity": current_equity,
            "elapsed_days": elapsed_days,
            "total_days": total_days,
        }
    )
    path_ratio = _safe_float(path.get("target_math", {}).get("path_ratio", 1), 1)
    drawdown_percent = ((current_equity - peak_equity) / peak_equity) * 100 if peak_equity else 0

    mode = "MAIN"
    command = "MAIN_ONLY"
    risk_level = "aggressive_but_controlled"
    reason = "Account is close enough to target path and can use the main forward-test setup."
    allowed_setup_modes = ["main"]
    blocked_setup_modes = ["attack_research_only"]

    if news_risk in {"high", "very_high"}:
        mode = "NO_TRADE"
        command = "WAIT_NEWS_RISK"
        risk_level = "blocked"
        reason = "High news risk blocks new trades even if the goal path is behind."
        allowed_setup_modes = []
        blocked_setup_modes = ["a_plus_safe", "main", "attack_research", "attack_research_only"]
    elif drawdown_percent <= -15:
        mode = "DEFENSE_PAUSE"
        command = "STOP_AND_REVIEW"
        risk_level = "defense"
        reason = "Drawdown is worse than -15%; protect account and pause for review."
        allowed_setup_modes = []
        blocked_setup_modes = ["a_plus_safe", "main", "attack_research", "attack_research_only"]
    elif drawdown_percent <= -10 or consecutive_losses >= 2:
        mode = "A_PLUS_ONLY"
        command = "STRICT_ONLY"
        risk_level = "recovery"
        reason = "Drawdown or loss streak requires A+ strict setup only."
        allowed_setup_modes = ["a_plus_safe"]
        blocked_setup_modes = ["main", "attack_research", "attack_research_only"]
    elif current_equity >= target_equity * 0.8:
        mode = "PROTECT_TARGET"
        command = "A_PLUS_ONLY"
        risk_level = "protect_target"
        reason = "Close to target; protect progress instead of attacking."
        allowed_setup_modes = ["a_plus_safe"]
        blocked_setup_modes = ["main", "attack_research", "attack_research_only"]
    elif path_ratio >= 1.25:
        mode = "AHEAD_OF_PLAN"
        command = "A_PLUS_OR_MAIN_LIGHT"
        risk_level = "protect_lead"
        reason = "Equity is ahead of path. Use A+ or lighter main mode to protect lead."
        allowed_setup_modes = ["a_plus_safe", "main"]
        blocked_setup_modes = ["attack_research", "attack_research_only"]
    elif path_ratio < 0.75 and market_quality in {"very_strong", "a_plus"}:
        mode = "CONTROLLED_ATTACK_RESEARCH"
        command = "MAIN_ALLOWED_ATTACK_RESEARCH_ONLY"
        risk_level = "behind_path_but_no_forced_trade"
        reason = "Equity is behind path, but attack can only be considered as research when market quality is very strong."
        allowed_setup_modes = ["main", "a_plus_safe"]
        blocked_setup_modes = ["attack_research_only"]
    elif path_ratio < 0.75:
        mode = "BEHIND_PLAN"
        command = "MAIN_ONLY_NO_FORCE"
        risk_level = "behind_path"
        reason = "Equity is behind path, but market is not strong enough for attack. Use main only if setup is valid."
        allowed_setup_modes = ["main", "a_plus_safe"]
        blocked_setup_modes = ["attack_research", "attack_research_only"]
    elif market_quality in {"unclear", "range", "messy"}:
        mode = "NO_TRADE"
        command = "WAIT_MARKET_UNCLEAR"
        risk_level = "blocked"
        reason = "Market is unclear/range. The goal does not justify forcing a trade."
        allowed_setup_modes = []
        blocked_setup_modes = ["a_plus_safe", "main", "attack_research", "attack_research_only"]

    return {
        "version": "goal_mode_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "goal_path": path,
        "account_state": {
            "current_equity": _round(current_equity, 2),
            "peak_equity": _round(peak_equity, 2),
            "drawdown_percent": _round(drawdown_percent, 2),
            "consecutive_losses": consecutive_losses,
            "news_risk": news_risk,
            "market_quality": market_quality,
        },
        "decision": {
            "goal_mode": mode,
            "command": command,
            "risk_level": risk_level,
            "reason": reason,
            "allowed_setup_modes": allowed_setup_modes,
            "blocked_setup_modes": blocked_setup_modes,
        },
    }


def build_goal_brief_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compact daily brief for UI/AI guide."""
    result = get_goal_mode_v1(payload)
    path_math = result.get("goal_path", {}).get("target_math", {})
    decision = result.get("decision", {})
    account = result.get("account_state", {})

    return {
        "version": "goal_brief_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "headline": decision.get("command", "MAIN_ONLY"),
        "summary": {
            "current_equity": account.get("current_equity"),
            "target_progress_percent": path_math.get("progress_percent"),
            "expected_equity_today": path_math.get("expected_equity_today"),
            "path_ratio": path_math.get("path_ratio"),
            "drawdown_percent": account.get("drawdown_percent"),
            "goal_mode": decision.get("goal_mode"),
            "risk_level": decision.get("risk_level"),
        },
        "guide": {
            "reason": decision.get("reason"),
            "allowed_setup_modes": decision.get("allowed_setup_modes", []),
            "blocked_setup_modes": decision.get("blocked_setup_modes", []),
            "next_action": _next_action_from_decision(decision.get("command", "")),
        },
        "raw": result,
    }


def _next_action_from_decision(command: str) -> str:
    if command in {"WAIT_NEWS_RISK", "WAIT_MARKET_UNCLEAR", "STOP_AND_REVIEW"}:
        return "Do not prepare a new trade. Review market or account state first."
    if command == "STRICT_ONLY":
        return "Only prepare A+ strict setup. Skip main and attack versions."
    if command in {"A_PLUS_ONLY", "A_PLUS_OR_MAIN_LIGHT"}:
        return "Prefer A+ strict setup. Use main only if signal quality is exceptional."
    if command == "MAIN_ALLOWED_ATTACK_RESEARCH_ONLY":
        return "Use main setup if valid. Attack remains research-only, not execution mode."
    return "Use the main setup only if all strategy filters pass. Do not force trades."
