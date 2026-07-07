from __future__ import annotations

from typing import Any

from app.services.jack_candle_storage import load_candles


def run_inverse_research_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper()
    timeframe = str(payload.get("timeframe") or "H4").upper()
    start_value = float(payload.get("initial_capital") or payload.get("start_value") or 10000)
    unit_percent = float(payload.get("risk_percent") or payload.get("unit_percent") or 1)
    ema_fast = int(payload.get("ema_fast") or 30)
    ema_slow = int(payload.get("ema_slow") or 150)
    lookback = int(payload.get("lookback") or payload.get("breakout_lookback") or 20)
    guard_n = int(payload.get("stop_lookback") or payload.get("guard_lookback") or 20)
    objective_r = float(payload.get("target_r") or payload.get("objective_r") or 1.5)

    store = load_candles(symbol=symbol, timeframe=timeframe, limit=20000)
    candles = [_row(x) for x in store.get("candles", [])]
    candles = [x for x in candles if x is not None]
    needed = max(ema_slow, lookback, guard_n) + 2
    if len(candles) < needed:
        return {"status": "not_enough_data", "symbol": symbol, "timeframe": timeframe, "rows": len(candles)}

    closes = [x["close"] for x in candles]
    ef = _ema(closes, ema_fast)
    es = _ema(closes, ema_slow)

    value = start_value
    high_water = start_value
    max_drop = 0.0
    cases = []
    active = None
    start = max(ema_slow, lookback, guard_n)

    for i in range(start, len(candles)):
        bar = candles[i]
        if active is not None:
            finish = None
            reason = None
            if bar["high"] >= active["guard"]:
                finish = active["guard"]
                reason = "guard"
            elif bar["low"] <= active["objective"]:
                finish = active["objective"]
                reason = "objective"
            if finish is not None:
                r_value = (active["start"] - finish) / active["unit"]
                change = active["sized_value"] * r_value
                value = round(value + change, 2)
                cases.append({"start_time": active["time"], "finish_time": bar["timestamp"], "reason": reason, "r_multiple": round(r_value, 3), "change": round(change, 2), "value_after": value})
                active = None
        if active is None:
            trend_ok = ef[i - 1] is not None and es[i - 1] is not None and ef[i - 1] < es[i - 1]
            recent_floor = min(candles[j]["low"] for j in range(i - lookback, i))
            recent_ceiling = max(candles[j]["high"] for j in range(i - guard_n, i))
            signal_ok = bar["close"] < recent_floor
            if trend_ok and signal_ok and recent_ceiling > bar["close"]:
                unit = recent_ceiling - bar["close"]
                if unit > 0:
                    active = {"time": bar["timestamp"], "start": bar["close"], "guard": recent_ceiling, "objective": bar["close"] - unit * objective_r, "unit": unit, "sized_value": value * unit_percent / 100}
        high_water = max(high_water, value)
        drop = (value - high_water) / high_water * 100 if high_water else 0.0
        max_drop = min(max_drop, drop)

    positive = [x for x in cases if x["r_multiple"] > 0]
    negative = [x for x in cases if x["r_multiple"] <= 0]
    pos_sum = sum(x["change"] for x in positive)
    neg_sum = abs(sum(x["change"] for x in negative))
    ratio = round(pos_sum / neg_sum, 3) if neg_sum > 0 else None
    summary = {
        "engine": "Inverse Research v1",
        "rule": "EMA down state + lower range break + fixed R objective",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": candles[0]["timestamp"],
        "end_date": candles[-1]["timestamp"],
        "initial_capital": round(start_value, 2),
        "final_equity": round(value, 2),
        "total_return_percent": round((value / start_value - 1) * 100, 4),
        "max_drawdown_percent": round(max_drop, 4),
        "candles_used": len(candles),
        "number_of_cases": len(cases),
        "win_rate_percent": round(len(positive) / len(cases) * 100, 2) if cases else 0.0,
        "profit_factor": ratio,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "lookback": lookback,
        "guard_lookback": guard_n,
        "objective_r": objective_r,
        "status": "computed_from_stored_candles",
    }
    return {"summary": summary, "cases": cases[:300], "cases_total": len(cases), "storage": {k: store.get(k) for k in ["rows_total", "first_timestamp", "last_timestamp", "path"]}}


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


def _row(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    try:
        return {"timestamp": str(v["timestamp"]), "open": float(v["open"]), "high": float(v["high"]), "low": float(v["low"]), "close": float(v["close"])}
    except Exception:
        return None
