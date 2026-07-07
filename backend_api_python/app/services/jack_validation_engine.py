from __future__ import annotations

from typing import Any

from app.services.jack_candle_storage import load_candles
from app.services.jack_memory_store import add_memory_v1


VERSION = "validation_engine_v1"

DEFAULT_PERIODS = [
    {"name": "P1_2012_2016", "start": "2012-01-01", "end": "2016-12-31"},
    {"name": "P2_2017_2019", "start": "2017-01-01", "end": "2019-12-31"},
    {"name": "P3_2020_2022", "start": "2020-01-01", "end": "2022-12-31"},
]


def validate_profile_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper().strip()
    timeframe = str(payload.get("timeframe") or "H4").upper().strip()
    fast = _to_int(payload.get("ema_fast"), 30)
    slow = _to_int(payload.get("ema_slow"), 150)
    breakout = _to_int(payload.get("breakout_lookback"), 20)
    guard = _to_int(payload.get("guard_lookback"), 20)
    objective_r = _to_float(payload.get("target_r"), 1.5)
    capital = _to_float(payload.get("initial_capital"), 10000.0)
    risk_pct = _to_float(payload.get("risk_percent"), 1.0)
    periods = payload.get("periods") if isinstance(payload.get("periods"), list) else DEFAULT_PERIODS

    stored = load_candles(symbol=symbol, timeframe=timeframe, limit=50000)
    candles = [_clean(row) for row in stored.get("candles", [])]
    candles = [row for row in candles if row is not None]

    period_results = []
    for period in periods:
        rows = _slice(candles, str(period.get("start")), str(period.get("end")))
        result = _run_segment(rows, symbol, timeframe, fast, slow, breakout, guard, objective_r, capital, risk_pct)
        result["period"] = period
        period_results.append(result)

    grade = _grade(period_results)
    report = {
        "version": VERSION,
        "ok": True,
        "symbol": symbol,
        "timeframe": timeframe,
        "params": {
            "ema_fast": fast,
            "ema_slow": slow,
            "breakout_lookback": breakout,
            "guard_lookback": guard,
            "target_r": objective_r,
            "risk_percent": risk_pct,
        },
        "grade": grade,
        "period_results": period_results,
        "human_summary": _human_summary(symbol, timeframe, grade, period_results),
        "notes": [
            "Historical validation only.",
            "This endpoint does not connect to any broker and does not create live instructions.",
        ],
    }

    if _bool(payload.get("save_memory"), True):
        saved = add_memory_v1({
            "memory_type": "validation_report",
            "symbol": symbol,
            "title": f"Validation {symbol} {timeframe} EMA{fast}/{slow} {objective_r:g}R",
            "content": report["human_summary"],
            "tags": [VERSION, symbol, timeframe, grade.get("status")],
            "source": VERSION,
            "metadata": report,
        })
        report["memory_id"] = (saved.get("memory") or {}).get("memory_id")

    return report


def validate_top_candidates_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else [
        {"symbol": "GBPJPY", "timeframe": "H4", "ema_fast": 30, "ema_slow": 150, "target_r": 1.5},
        {"symbol": "XAUUSD", "timeframe": "H4", "ema_fast": 30, "ema_slow": 150, "target_r": 1.5},
    ]
    results = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        request = dict(item)
        request["save_memory"] = payload.get("save_memory", True)
        results.append(validate_profile_v1(request))
    ranked = sorted(results, key=lambda x: x.get("grade", {}).get("score", -999), reverse=True)
    return {
        "version": VERSION,
        "ok": True,
        "total": len(results),
        "ranked": ranked,
        "summary": {
            "best": ranked[0].get("human_summary") if ranked else None,
            "validated_count": sum(1 for row in ranked if row.get("grade", {}).get("status") == "validated_candidate"),
        },
    }


def _run_segment(candles: list[dict[str, Any]], symbol: str, timeframe: str, fast: int, slow: int, breakout: int, guard: int, objective_r: float, capital: float, risk_pct: float) -> dict[str, Any]:
    min_needed = max(slow, breakout, guard) + 2
    if len(candles) < min_needed:
        return {"status": "not_enough_data", "symbol": symbol, "timeframe": timeframe, "candles": len(candles), "trades": 0, "return_percent": 0.0, "max_drop_percent": 0.0, "ratio": 0.0}

    closes = [x["close"] for x in candles]
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    equity = capital
    peak = capital
    max_drop = 0.0
    events = []
    active = None

    for i in range(max(slow, breakout, guard), len(candles)):
        row = candles[i]
        if active is not None:
            done = False
            out_price = None
            if row["low"] <= active["guard"]:
                done = True
                out_price = active["guard"]
            elif row["high"] >= active["objective"]:
                done = True
                out_price = active["objective"]
            if done:
                r_value = (out_price - active["entry"]) / active["unit_risk"]
                gain = active["risk_amount"] * r_value
                equity = round(equity + gain, 2)
                events.append({"start": active["start"], "end": row["timestamp"], "r": round(r_value, 3), "equity": equity})
                active = None

        if active is None:
            trend_ok = ema_fast[i - 1] is not None and ema_slow[i - 1] is not None and ema_fast[i - 1] > ema_slow[i - 1]
            recent_high = max(candles[j]["high"] for j in range(i - breakout, i))
            recent_low = min(candles[j]["low"] for j in range(i - guard, i))
            trigger_ok = row["close"] > recent_high and recent_low < row["close"]
            if trend_ok and trigger_ok:
                entry = row["close"]
                unit_risk = entry - recent_low
                if unit_risk > 0:
                    active = {"start": row["timestamp"], "entry": entry, "guard": recent_low, "objective": entry + unit_risk * objective_r, "unit_risk": unit_risk, "risk_amount": equity * risk_pct / 100}

        peak = max(peak, equity)
        drop = ((equity - peak) / peak * 100) if peak else 0.0
        max_drop = min(max_drop, drop)

    wins = [x for x in events if x.get("r", 0) > 0]
    others = [x for x in events if x.get("r", 0) <= 0]
    gross_win = sum(x.get("r", 0) for x in wins)
    gross_other = abs(sum(x.get("r", 0) for x in others))
    ratio = round(gross_win / gross_other, 3) if gross_other > 0 else (999.0 if gross_win > 0 else 0.0)
    return_percent = round((equity / capital - 1) * 100, 4)

    return {
        "status": "computed",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": candles[0]["timestamp"],
        "end_date": candles[-1]["timestamp"],
        "candles": len(candles),
        "trades": len(events),
        "return_percent": return_percent,
        "max_drop_percent": round(max_drop, 4),
        "ratio": ratio,
        "win_rate_percent": round(len(wins) / len(events) * 100, 2) if events else 0.0,
    }


def _grade(results: list[dict[str, Any]]) -> dict[str, Any]:
    computed = [x for x in results if x.get("status") == "computed"]
    positives = [x for x in computed if _to_float(x.get("return_percent"), 0) > 0]
    weak = [x for x in computed if _to_float(x.get("ratio"), 0) < 1.1 or _to_float(x.get("return_percent"), 0) <= 0]
    deep = [x for x in computed if _to_float(x.get("max_drop_percent"), 0) <= -10]
    score = 0.0
    for row in computed:
        score += _to_float(row.get("return_percent"), 0) * 2
        score += _to_float(row.get("ratio"), 0) * 5
        score -= abs(_to_float(row.get("max_drop_percent"), 0))
        score += min(_to_float(row.get("trades"), 0), 40) * 0.1
    if computed:
        score = round(score / len(computed), 4)
    if len(computed) >= 3 and len(positives) >= 2 and not deep and len(weak) <= 1:
        status = "validated_candidate"
    elif len(positives) >= 1:
        status = "needs_more_validation"
    else:
        status = "not_validated"
    return {"status": status, "score": score, "periods_computed": len(computed), "positive_periods": len(positives), "weak_periods": len(weak), "deep_drop_periods": len(deep)}


def _slice(candles: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    return [row for row in candles if str(row.get("timestamp", ""))[:10] >= start and str(row.get("timestamp", ""))[:10] <= end]


def _clean(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    try:
        return {"timestamp": str(row["timestamp"]), "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"])}
    except (KeyError, TypeError, ValueError):
        return None


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


def _human_summary(symbol: str, timeframe: str, grade: dict[str, Any], results: list[dict[str, Any]]) -> str:
    parts = [f"{row.get('period', {}).get('name')} return={row.get('return_percent')} drop={row.get('max_drop_percent')} ratio={row.get('ratio')} trades={row.get('trades')}" for row in results]
    return f"Validation {symbol} {timeframe}: status={grade.get('status')} score={grade.get('score')} positive_periods={grade.get('positive_periods')}/{grade.get('periods_computed')}. " + " | ".join(parts)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "y", "on"]
    return default
