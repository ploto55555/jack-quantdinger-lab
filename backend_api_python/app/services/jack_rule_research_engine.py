"""Rule research engine v1 for Jack OS.

This module only reads stored candles and returns historical simulation metrics.
It does not connect to any broker or place orders.
"""
from __future__ import annotations

from typing import Any

from app.services.jack_candle_storage import load_candles


def run_rule_research_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = _text(payload.get("symbol"), "GBPJPY").upper()
    timeframe = _text(payload.get("timeframe"), "H4").upper()
    initial_capital = _float(payload.get("initial_capital"), 10000.0)
    risk_percent = max(0.1, min(_float(payload.get("risk_percent"), 1.0), 5.0))
    fast = max(2, _int(payload.get("ema_fast"), 20))
    slow = max(fast + 1, _int(payload.get("ema_slow"), 50))
    breakout_lookback = max(2, _int(payload.get("breakout_lookback"), 20))
    stop_lookback = max(2, _int(payload.get("stop_lookback"), 10))
    target_r = max(0.5, _float(payload.get("target_r"), 2.0))
    limit = _int(payload.get("limit"), 20000)

    stored = load_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    candles = [_clean_candle(row) for row in stored.get("candles", [])]
    candles = [row for row in candles if row is not None]

    min_needed = max(slow, breakout_lookback, stop_lookback) + 2
    if len(candles) < min_needed:
        return {
            "status": "not_enough_candles",
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_available": len(candles),
            "candles_required": min_needed,
            "storage": {k: stored.get(k) for k in ["rows_total", "rows_returned", "first_timestamp", "last_timestamp", "path"]},
        }

    closes = [row["close"] for row in candles]
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    equity = initial_capital
    peak = initial_capital
    max_drawdown = 0.0
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    position: dict[str, Any] | None = None

    start_index = max(slow, breakout_lookback, stop_lookback)
    for i in range(start_index, len(candles)):
        row = candles[i]

        if position is not None:
            exit_reason = None
            exit_price = None
            if row["low"] <= position["stop"]:
                exit_reason = "stop_loss"
                exit_price = position["stop"]
            elif row["high"] >= position["target"]:
                exit_reason = "target_r"
                exit_price = position["target"]

            if exit_reason:
                r_multiple = (exit_price - position["entry"]) / position["risk_per_unit"]
                pnl = position["risk_amount"] * r_multiple
                equity = round(equity + pnl, 2)
                trade = {
                    "entry_time": position["entry_time"],
                    "exit_time": row["timestamp"],
                    "side": "long",
                    "entry": round(position["entry"], 5),
                    "stop": round(position["stop"], 5),
                    "target": round(position["target"], 5),
                    "exit": round(exit_price, 5),
                    "exit_reason": exit_reason,
                    "r_multiple": round(r_multiple, 3),
                    "pnl": round(pnl, 2),
                    "equity_after": equity,
                }
                trades.append(trade)
                position = None

        if position is None:
            trend_ok = ema_fast[i - 1] is not None and ema_slow[i - 1] is not None and ema_fast[i - 1] > ema_slow[i - 1]
            recent_high = max(candles[j]["high"] for j in range(i - breakout_lookback, i))
            recent_low = min(candles[j]["low"] for j in range(i - stop_lookback, i))
            breakout_ok = row["close"] > recent_high
            stop_ok = recent_low < row["close"]
            if trend_ok and breakout_ok and stop_ok:
                entry = row["close"]
                stop = recent_low
                risk_per_unit = entry - stop
                if risk_per_unit > 0:
                    risk_amount = equity * risk_percent / 100
                    position = {
                        "entry_time": row["timestamp"],
                        "entry": entry,
                        "stop": stop,
                        "target": entry + risk_per_unit * target_r,
                        "risk_per_unit": risk_per_unit,
                        "risk_amount": risk_amount,
                    }

        peak = max(peak, equity)
        drawdown = ((equity - peak) / peak * 100) if peak else 0.0
        max_drawdown = min(max_drawdown, drawdown)
        equity_curve.append({"timestamp": row["timestamp"], "equity": round(equity, 2), "drawdown_percent": round(drawdown, 4)})

    if position is not None:
        last = candles[-1]
        r_multiple = (last["close"] - position["entry"]) / position["risk_per_unit"]
        pnl = position["risk_amount"] * r_multiple
        equity = round(equity + pnl, 2)
        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": last["timestamp"],
            "side": "long",
            "entry": round(position["entry"], 5),
            "stop": round(position["stop"], 5),
            "target": round(position["target"], 5),
            "exit": round(last["close"], 5),
            "exit_reason": "end_of_data",
            "r_multiple": round(r_multiple, 3),
            "pnl": round(pnl, 2),
            "equity_after": equity,
        })

    wins = [t for t in trades if t["r_multiple"] > 0]
    losses = [t for t in trades if t["r_multiple"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = round(gross_win / gross_loss, 3) if gross_loss > 0 else None

    summary = {
        "engine": "Rule Research Engine v1",
        "rule": "EMA trend + breakout + fixed R target",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": candles[0]["timestamp"],
        "end_date": candles[-1]["timestamp"],
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(equity, 2),
        "total_return_percent": round((equity / initial_capital - 1) * 100, 4),
        "max_drawdown_percent": round(max_drawdown, 4),
        "candles_used": len(candles),
        "number_of_trades": len(trades),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": profit_factor,
        "risk_percent": risk_percent,
        "ema_fast": fast,
        "ema_slow": slow,
        "breakout_lookback": breakout_lookback,
        "stop_lookback": stop_lookback,
        "target_r": target_r,
        "status": "computed_from_stored_candles",
    }
    return {
        "summary": summary,
        "trades": trades[:500],
        "trades_total": len(trades),
        "equity_curve": equity_curve[-500:],
        "notes": [
            "Historical research only. No broker connection and no live orders.",
            "This is v1 logic for system validation. It is not a final trading method.",
        ],
        "storage": {k: stored.get(k) for k in ["rows_total", "rows_returned", "first_timestamp", "last_timestamp", "path"]},
    }


def _ema(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return output
    sma = sum(values[:period]) / period
    output[period - 1] = sma
    alpha = 2 / (period + 1)
    previous = sma
    for i in range(period, len(values)):
        previous = values[i] * alpha + previous * (1 - alpha)
        output[i] = previous
    return output


def _clean_candle(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    try:
        return {
            "timestamp": str(row["timestamp"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _text(value: Any, default: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
