from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.services.jack_candle_storage import load_candles


def run_mtf_research_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper()
    initial_capital = float(payload.get("initial_capital") or 10000)
    risk_percent = float(payload.get("risk_percent") or 1)
    h4_fast = int(payload.get("h4_ema_fast") or 30)
    h4_slow = int(payload.get("h4_ema_slow") or 150)
    d1_fast = int(payload.get("d1_ema_fast") or 30)
    d1_slow = int(payload.get("d1_ema_slow") or 150)
    breakout = int(payload.get("breakout_lookback") or 20)
    stop_n = int(payload.get("stop_lookback") or 20)
    target_r = float(payload.get("target_r") or 1.5)

    h4_store = load_candles(symbol=symbol, timeframe="H4", limit=20000)
    d1_store = load_candles(symbol=symbol, timeframe="D1", limit=5000)
    h4 = [_row(x) for x in h4_store.get("candles", [])]
    d1 = [_row(x) for x in d1_store.get("candles", [])]
    h4 = [x for x in h4 if x is not None]
    d1 = [x for x in d1 if x is not None]

    needed = max(h4_slow, breakout, stop_n) + 2
    if len(h4) < needed or len(d1) < d1_slow + 2:
        return {"status": "not_enough_data", "symbol": symbol, "h4_rows": len(h4), "d1_rows": len(d1)}

    h4_close = [x["close"] for x in h4]
    d1_close = [x["close"] for x in d1]
    h4_ef = _ema(h4_close, h4_fast)
    h4_es = _ema(h4_close, h4_slow)
    d1_ef = _ema(d1_close, d1_fast)
    d1_es = _ema(d1_close, d1_slow)
    d1_map = _d1_trend_map(d1, d1_ef, d1_es)

    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    trades = []
    pos = None
    skipped_by_d1 = 0
    start = max(h4_slow, breakout, stop_n)

    for i in range(start, len(h4)):
        bar = h4[i]
        if pos is not None:
            out = None
            reason = None
            if bar["low"] <= pos["stop"]:
                out = pos["stop"]
                reason = "stop"
            elif bar["high"] >= pos["target"]:
                out = pos["target"]
                reason = "target"
            if out is not None:
                r = (out - pos["entry"]) / pos["risk_unit"]
                pnl = pos["risk_amount"] * r
                equity = round(equity + pnl, 2)
                trades.append({"entry_time": pos["time"], "exit_time": bar["timestamp"], "exit_reason": reason, "r_multiple": round(r, 3), "pnl": round(pnl, 2), "equity_after": equity})
                pos = None
        if pos is None:
            h4_trend = h4_ef[i - 1] is not None and h4_es[i - 1] is not None and h4_ef[i - 1] > h4_es[i - 1]
            d1_ok = _d1_allows_long_using_previous_day(bar["timestamp"], d1_map)
            recent_high = max(h4[j]["high"] for j in range(i - breakout, i))
            recent_low = min(h4[j]["low"] for j in range(i - stop_n, i))
            breakout_ok = bar["close"] > recent_high
            if h4_trend and breakout_ok and not d1_ok:
                skipped_by_d1 += 1
            if h4_trend and d1_ok and breakout_ok and recent_low < bar["close"]:
                risk_unit = bar["close"] - recent_low
                if risk_unit > 0:
                    pos = {"time": bar["timestamp"], "entry": bar["close"], "stop": recent_low, "target": bar["close"] + risk_unit * target_r, "risk_unit": risk_unit, "risk_amount": equity * risk_percent / 100}
        peak = max(peak, equity)
        dd = (equity - peak) / peak * 100 if peak else 0.0
        max_dd = min(max_dd, dd)

    wins = [x for x in trades if x["r_multiple"] > 0]
    losses = [x for x in trades if x["r_multiple"] <= 0]
    gw = sum(x["pnl"] for x in wins)
    gl = abs(sum(x["pnl"] for x in losses))
    pf = round(gw / gl, 3) if gl > 0 else None
    summary = {
        "engine": "MTF Research v1",
        "rule": "Previous closed D1 trend filter + H4 breakout research",
        "symbol": symbol,
        "h4_rows": len(h4),
        "d1_rows": len(d1),
        "start_date": h4[0]["timestamp"],
        "end_date": h4[-1]["timestamp"],
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(equity, 2),
        "total_return_percent": round((equity / initial_capital - 1) * 100, 4),
        "max_drawdown_percent": round(max_dd, 4),
        "number_of_trades": len(trades),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": pf,
        "skipped_by_d1_filter": skipped_by_d1,
        "daily_filter_timing": "uses_previous_closed_d1_candle",
        "h4_ema_fast": h4_fast,
        "h4_ema_slow": h4_slow,
        "d1_ema_fast": d1_fast,
        "d1_ema_slow": d1_slow,
        "breakout_lookback": breakout,
        "stop_lookback": stop_n,
        "target_r": target_r,
        "status": "computed_from_h4_d1_storage",
    }
    return {"summary": summary, "trades": trades[:300], "trades_total": len(trades), "storage": {"h4": {k: h4_store.get(k) for k in ["rows_total", "first_timestamp", "last_timestamp", "path"]}, "d1": {k: d1_store.get(k) for k in ["rows_total", "first_timestamp", "last_timestamp", "path"]}}}


def _d1_trend_map(d1: list[dict[str, Any]], ef: list[float | None], es: list[float | None]) -> dict[str, bool]:
    out = {}
    for i, row in enumerate(d1):
        day = row["timestamp"][:10]
        out[day] = ef[i] is not None and es[i] is not None and ef[i] > es[i]
    return out


def _d1_allows_long_using_previous_day(timestamp: str, trend_map: dict[str, bool]) -> bool:
    previous_day = _previous_calendar_day(str(timestamp)[:10])
    return bool(trend_map.get(previous_day))


def _previous_calendar_day(day: str) -> str:
    try:
        return (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        return ""


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
