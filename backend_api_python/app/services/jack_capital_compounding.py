from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


VERSION = "capital_compounding_simulator_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def simulate_capital_path_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}

    start_equity = max(_to_float(payload.get("start_equity"), 500.0), 0.01)
    daily_growth_percent = _to_float(payload.get("daily_growth_percent"), 5.0)
    days = max(_to_int(payload.get("days"), 90), 1)
    target_equity = max(_to_float(payload.get("target_equity"), 1000000.0), 0.01)

    daily_rate = daily_growth_percent / 100.0
    final_equity = start_equity * ((1 + daily_rate) ** days)

    required_multiple = target_equity / start_equity
    achieved_multiple = final_equity / start_equity

    days_to_target = None
    if daily_rate > 0:
        current = start_equity
        d = 0
        while current < target_equity and d < 3650:
            current = current * (1 + daily_rate)
            d += 1
        days_to_target = d if current >= target_equity else None

    checkpoints = []
    current = start_equity
    for day in range(1, days + 1):
        current = current * (1 + daily_rate)

        if day in [7, 14, 30, 60, 90, 120, 180, 240, 365] or day == days:
            checkpoints.append(
                {
                    "day": day,
                    "equity": round(current, 2),
                    "multiple": round(current / start_equity, 4),
                }
            )

    drawdown_scenarios = []
    for dd in [10, 20, 30, 50]:
        after_dd = final_equity * (1 - dd / 100)
        drawdown_scenarios.append(
            {
                "drawdown_percent": dd,
                "equity_after_drawdown": round(after_dd, 2),
                "remaining_multiple": round(after_dd / start_equity, 4),
            }
        )

    if daily_growth_percent >= 10:
        risk_label = "extreme"
        risk_note = "Daily 10% or higher is extremely aggressive and should be treated as math simulation only."
    elif daily_growth_percent >= 5:
        risk_label = "very_aggressive"
        risk_note = "Daily 5% is very aggressive. Backtest and forward test must be very strict."
    elif daily_growth_percent >= 2:
        risk_label = "aggressive"
        risk_note = "Daily 2%+ is still aggressive and requires strong edge and risk control."
    elif daily_growth_percent > 0:
        risk_label = "researchable"
        risk_note = "This target may be researched, but still needs backtest, costs, drawdown, and forward testing."
    else:
        risk_label = "invalid_or_negative"
        risk_note = "Growth percent is zero or negative. Target cannot be reached by positive compounding."

    return {
        "version": VERSION,
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now(),
        "inputs": {
            "start_equity": start_equity,
            "daily_growth_percent": daily_growth_percent,
            "days": days,
            "target_equity": target_equity,
        },
        "result": {
            "final_equity": round(final_equity, 2),
            "profit": round(final_equity - start_equity, 2),
            "achieved_multiple": round(achieved_multiple, 4),
            "required_multiple_to_target": round(required_multiple, 4),
            "days_to_target_at_same_daily_growth": days_to_target,
            "target_reached_within_period": final_equity >= target_equity,
        },
        "checkpoints": checkpoints,
        "drawdown_scenarios": drawdown_scenarios,
        "risk_assessment": {
            "risk_label": risk_label,
            "risk_note": risk_note,
            "warning": "This is a compounding calculator for research only. It is not a guarantee or trade instruction.",
        },
        "next_action": "Compare this capital path with real backtest result, max drawdown, losing streak, transaction cost, and journal memory.",
    }


def compare_compounding_plans_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}

    start_equity = max(_to_float(payload.get("start_equity"), 500.0), 0.01)
    days = max(_to_int(payload.get("days"), 90), 1)
    target_equity = max(_to_float(payload.get("target_equity"), 1000000.0), 0.01)

    growth_rates = payload.get("daily_growth_percents")
    if not isinstance(growth_rates, list) or not growth_rates:
        growth_rates = [1, 2, 3, 5, 10]

    plans = []
    for rate in growth_rates:
        result = simulate_capital_path_v1(
            {
                "start_equity": start_equity,
                "daily_growth_percent": rate,
                "days": days,
                "target_equity": target_equity,
            }
        )
        plans.append(
            {
                "daily_growth_percent": rate,
                "final_equity": result["result"]["final_equity"],
                "achieved_multiple": result["result"]["achieved_multiple"],
                "days_to_target": result["result"]["days_to_target_at_same_daily_growth"],
                "risk_label": result["risk_assessment"]["risk_label"],
            }
        )

    return {
        "version": "capital_compounding_plan_compare_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "inputs": {
            "start_equity": start_equity,
            "days": days,
            "target_equity": target_equity,
        },
        "plans": plans,
        "warning": "This compares math paths only. Real strategy evaluation still needs backtest, spread, slippage, drawdown, and forward testing.",
    }
