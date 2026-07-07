"""Walk-forward report for stored-candle rule research."""
from __future__ import annotations

from typing import Any

from app.services.jack_candle_storage import load_candles

FAST_VALUES = [10, 20, 30]
SLOW_VALUES = [50, 100, 150]
BREAKOUT_VALUES = [10, 20, 30, 40]
STOP_VALUES = [5, 10, 15, 20]
TARGET_VALUES = [1.5, 2.0, 2.5, 3.0]


def walk_forward_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper()
    timeframe = str(payload.get("timeframe") or "H4").upper()
    initial_capital = float(payload.get("initial_capital") or 10000)
    risk_percent = float(payload.get("risk_percent") or 1)
    train_end = str(payload.get("train_end") or "2017-12-31T23:59:59Z")
    validate_start = str(payload.get("validate_start") or "2018-01-01T00:00:00Z")

    stored = load_candles(symbol=symbol, timeframe=timeframe, limit=20000)
    rows = [_clean(x) for x in stored.get("candles", [])]
    candles = [x for x in rows if x is not None]
    train = [x for x in candles if x["timestamp"] <= train_end]
    valid = [x for x in candles if x["timestamp"] >= validate_start]

    candidates = []
    tested = 0
    for fast in FAST_VALUES:
        for slow in SLOW_VALUES:
            if slow <= fast:
                continue
            for breakout in BREAKOUT_VALUES:
                for stop in STOP_VALUES:
                    for target in TARGET_VALUES:
                        tested += 1
                        result = _simulate(train, initial_capital, risk_percent, fast, slow, breakout, stop, target)
                        if result.get("status") != "ok" or result.get("number_of_trades", 0) < 8 or result.get("profit_factor") is None:
                            continue
                        candidates.append({
                            "score": _score(result),
                            "ema_fast": fast,
                            "ema_slow": slow,
                            "breakout_lookback": breakout,
                            "stop_lookback": stop,
                            "target_r": target,
                            "train": result,
                        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0] if candidates else None
    validation = None
    decision = "no_candidate"
    if best:
        validation = _simulate(valid, initial_capital, risk_percent, best["ema_fast"], best["ema_slow"], best["breakout_lookback"], best["stop_lookback"], best["target_r"])
        decision = _decision(validation)

    return {
        "summary": {
            "engine": "Walk Forward v1",
            "symbol": symbol,
            "timeframe": timeframe,
            "total_candles": len(candles),
            "train_candles": len(train),
            "validation_candles": len(valid),
            "train_end": train_end,
            "validate_start": validate_start,
            "combinations_tested": tested,
            "valid_candidates": len(candidates),
            "decision": decision,
            "status": "walk_forward_complete" if best else "no_valid_candidate",
        },
        "best_params": {k: best[k] for k in ["ema_fast", "ema_slow", "breakout_lookback", "stop_lookback", "target_r"]} if best else None,
        "train_result": best["train"] if best else None,
        "validation_result": validation,
        "top_train_candidates": candidates[:10],
        "storage": {k: stored.get(k) for k in ["rows_total", "rows_returned", "first_timestamp", "last_timestamp", "path"]},
    }


def _simulate(candles: list[dict[str, Any]], initial_capital: float, risk_percent: float, fast: int, slow: int, breakout: int, stop_n: int, target_r: float) -> dict[str, Any]:
    if len(candles) < max(slow, breakout, stop_n) + 2:
        return {"status": "not_enough_data", "number_of_trades": 0}
    closes = [x["close"] for x in candles]
    ef = _ema(closes, fast)
    es = _ema(closes, slow)
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    trades = []
    pos = None
    start = max(slow, breakout, stop_n)
    for i in range(start, len(candles)):
        row = candles[i]
        if pos is not None:
            out = None
            if row["low"] <= pos["stop"]:
                out = pos["stop"]
            elif row["high"] >= pos["target"]:
                out = pos["target"]
            if out is not None:
                r = (out - pos["entry"]) / pos["risk_unit"]
                pnl = pos["risk_amount"] * r
                equity = round(equity + pnl, 2)
                trades.append({"r": round(r, 3), "pnl": round(pnl, 2)})
                pos = None
        if pos is None:
            trend = ef[i - 1] is not None and es[i - 1] is not None and ef[i - 1] > es[i - 1]
            recent_high = max(candles[j]["high"] for j in range(i - breakout, i))
            recent_low = min(candles[j]["low"] for j in range(i - stop_n, i))
            if trend and row["close"] > recent_high and recent_low < row["close"]:
                risk_unit = row["close"] - recent_low
                if risk_unit > 0:
                    pos = {"entry": row["close"], "stop": recent_low, "target": row["close"] + risk_unit * target_r, "risk_unit": risk_unit, "risk_amount": equity * risk_percent / 100}
        peak = max(peak, equity)
        dd = (equity - peak) / peak * 100 if peak else 0.0
        max_dd = min(max_dd, dd)
    wins = [t for t in trades if t["r"] > 0]
    losses = [t for t in trades if t["r"] <= 0]
    gw = sum(t["pnl"] for t in wins)
    gl = abs(sum(t["pnl"] for t in losses))
    pf = round(gw / gl, 3) if gl > 0 else None
    return {"status": "ok", "start_date": candles[0]["timestamp"], "end_date": candles[-1]["timestamp"], "initial_capital": round(initial_capital, 2), "final_equity": round(equity, 2), "total_return_percent": round((equity / initial_capital - 1) * 100, 4), "max_drawdown_percent": round(max_dd, 4), "number_of_trades": len(trades), "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0, "profit_factor": pf}


def _decision(result: dict[str, Any] | None) -> str:
    result = result or {}
    if result.get("status") != "ok" or result.get("number_of_trades", 0) < 5:
        return "insufficient_validation"
    if (result.get("profit_factor") or 0) >= 1.15 and result.get("total_return_percent", 0) > 0:
        return "passed_first_validation"
    if result.get("total_return_percent", 0) > 0:
        return "weak_validation"
    return "failed_validation_possible_overfit"


def _score(result: dict[str, Any]) -> float:
    return round(float(result.get("profit_factor") or 0) * 100 + float(result.get("total_return_percent") or 0) - abs(float(result.get("max_drawdown_percent") or 0)) * 2, 4)


def _ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        prev = values[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out


def _clean(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    try:
        return {"timestamp": str(row["timestamp"]), "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"])}
    except (KeyError, TypeError, ValueError):
        return None
