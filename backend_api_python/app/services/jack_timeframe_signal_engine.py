from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from app.services.jack_market_data_feed import get_latest_candles_v1


PIP_SIZE = 0.01  # GBPJPY pip size


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _round(value: float, digits: int = 3) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return mean(values[-period:])


def _ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_value = mean(values[:period])
    for value in values[period:]:
        ema_value = value * k + ema_value * (1 - k)
    return ema_value


def _bb(values: List[float], period: int = 20, mult: float = 2.0) -> Optional[Dict[str, float]]:
    if len(values) < period:
        return None
    window = values[-period:]
    mid = mean(window)
    sd = pstdev(window)
    return {
        "middle": mid,
        "upper": mid + mult * sd,
        "lower": mid - mult * sd,
        "width": (mult * sd * 2),
    }


def _bb_prev(values: List[float], period: int = 20, mult: float = 2.0) -> Optional[Dict[str, float]]:
    if len(values) < period + 1:
        return None
    return _bb(values[:-1], period, mult)


def _pips(distance: float) -> float:
    return distance / PIP_SIZE


def _latest(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    return candles[-1] if candles else {}


def _closes(candles: List[Dict[str, Any]]) -> List[float]:
    return [_safe_float(c.get("close")) for c in candles if c.get("close") is not None]


def _analyse_d1(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    latest = _latest(candles)
    closes = _closes(candles)
    close = _safe_float(latest.get("close"))
    ema50 = _ema(closes, 50)
    bb_now = _bb(closes, 20)
    bb_prev = _bb_prev(closes, 20)

    signal = "neutral"
    bias = "none"
    reasons: List[str] = []
    blockers: List[str] = []

    if ema50 is None or bb_now is None or bb_prev is None:
        signal = "insufficient_data"
        blockers.append("D1 needs at least 51 candles for EMA50 and Bollinger expansion.")
    else:
        bb_expanding = bb_now["width"] > bb_prev["width"]
        if close > ema50 and bb_expanding:
            signal = "long_only"
            bias = "long"
            reasons.append("D1 close is above EMA50 and Bollinger width is expanding.")
        elif close < ema50 and bb_expanding:
            signal = "short_only"
            bias = "short"
            reasons.append("D1 close is below EMA50 and Bollinger width is expanding.")
        elif close > ema50:
            signal = "long_bias_no_bbexp"
            bias = "long"
            blockers.append("D1 trend is long but Bollinger width is not expanding.")
        elif close < ema50:
            signal = "short_bias_no_bbexp"
            bias = "short"
            blockers.append("D1 trend is short but Bollinger width is not expanding.")
        else:
            signal = "neutral"
            blockers.append("D1 close is near EMA50; direction is not clear.")

    previous_day = candles[-2] if len(candles) >= 2 else {}

    return {
        "timeframe": "D1",
        "signal": signal,
        "bias": bias,
        "latest_close": close,
        "latest_timestamp": latest.get("timestamp"),
        "yesterday_high": previous_day.get("high"),
        "yesterday_low": previous_day.get("low"),
        "ema50": _round(ema50) if ema50 is not None else None,
        "bb_width": _round(bb_now["width"]) if bb_now else None,
        "bb_width_prev": _round(bb_prev["width"]) if bb_prev else None,
        "bb_expanding": bool(bb_now and bb_prev and bb_now["width"] > bb_prev["width"]),
        "reasons": reasons,
        "blockers": blockers,
    }


def _analyse_h1(candles: List[Dict[str, Any]], d1_bias: str) -> Dict[str, Any]:
    latest = _latest(candles)
    closes = _closes(candles)
    close = _safe_float(latest.get("close"))
    sma14 = _sma(closes, 14)
    sma20 = _sma(closes, 20)
    bb_now = _bb(closes, 20)
    sma14_prev = _sma(closes[:-5], 14) if len(closes) >= 25 else None
    sma20_prev = _sma(closes[:-5], 20) if len(closes) >= 25 else None

    regime = "unclear"
    trend_direction = "none"
    reasons: List[str] = []
    blockers: List[str] = []
    slope14 = None
    slope20 = None

    if sma14 is None or sma20 is None or bb_now is None or sma14_prev is None or sma20_prev is None:
        blockers.append("H1 needs more data for Ketty trend regime.")
    else:
        slope14 = _pips(sma14 - sma14_prev)
        slope20 = _pips(sma20 - sma20_prev)
        above_middle = close > bb_now["middle"]
        below_middle = close < bb_now["middle"]

        if close > sma14 and above_middle and slope14 > 3 and slope20 > -2:
            regime = "trend"
            trend_direction = "long"
            reasons.append("H1 Ketty trend mod supports long: price above SMA14/BB middle and MA slope is positive.")
        elif close < sma14 and below_middle and slope14 < -3 and slope20 < 2:
            regime = "trend"
            trend_direction = "short"
            reasons.append("H1 Ketty trend mod supports short: price below SMA14/BB middle and MA slope is negative.")
        elif abs(slope14) < 2 and abs(slope20) < 2:
            regime = "range"
            blockers.append("H1 MA slopes are flat; range/unclear market.")
        else:
            regime = "unclear"
            blockers.append("H1 trend conditions are mixed.")

        if d1_bias in {"long", "short"} and trend_direction not in {"none", d1_bias}:
            blockers.append("H1 trend direction conflicts with D1 bias.")

    return {
        "timeframe": "H1",
        "regime": regime,
        "trend_direction": trend_direction,
        "latest_close": close,
        "latest_timestamp": latest.get("timestamp"),
        "sma14": _round(sma14) if sma14 is not None else None,
        "sma20": _round(sma20) if sma20 is not None else None,
        "bb_middle": _round(bb_now["middle"]) if bb_now else None,
        "slope14_pips_5bars": _round(slope14) if slope14 is not None else None,
        "slope20_pips_5bars": _round(slope20) if slope20 is not None else None,
        "reasons": reasons,
        "blockers": blockers,
    }


def _analyse_m15(candles: List[Dict[str, Any]], d1: Dict[str, Any], h1: Dict[str, Any]) -> Dict[str, Any]:
    latest = _latest(candles)
    close = _safe_float(latest.get("close"))
    high = _safe_float(latest.get("high"))
    low = _safe_float(latest.get("low"))
    y_high = _safe_float(d1.get("yesterday_high"))
    y_low = _safe_float(d1.get("yesterday_low"))
    d1_bias = d1.get("bias", "none")
    h1_direction = h1.get("trend_direction", "none")

    signal = "wait"
    direction = "none"
    entry_price = None
    distance_to_entry_pips = None
    reasons: List[str] = []
    blockers: List[str] = []

    if not y_high or not y_low:
        blockers.append("Yesterday high/low is missing.")
    elif d1_bias == "long" and h1_direction == "long":
        direction = "long"
        entry_price = y_high + 2 * PIP_SIZE
        distance_to_entry_pips = _pips(entry_price - close)
        if high >= entry_price:
            signal = "triggered"
            reasons.append("M15 traded through SRDC long entry level.")
        elif 0 <= distance_to_entry_pips <= 20:
            signal = "setup_forming"
            reasons.append("M15 is within 20 pips of SRDC long trigger.")
        elif distance_to_entry_pips < 0:
            signal = "too_late_or_pullback"
            blockers.append("Price is already above long entry; avoid chasing without plan.")
        else:
            signal = "wait"
            reasons.append("M15 is not close enough to SRDC long trigger.")
    elif d1_bias == "short" and h1_direction == "short":
        direction = "short"
        entry_price = y_low - 2 * PIP_SIZE
        distance_to_entry_pips = _pips(close - entry_price)
        if low <= entry_price:
            signal = "triggered"
            reasons.append("M15 traded through SRDC short entry level.")
        elif 0 <= distance_to_entry_pips <= 20:
            signal = "setup_forming"
            reasons.append("M15 is within 20 pips of SRDC short trigger.")
        elif distance_to_entry_pips < 0:
            signal = "too_late_or_pullback"
            blockers.append("Price is already below short entry; avoid chasing without plan.")
        else:
            signal = "wait"
            reasons.append("M15 is not close enough to SRDC short trigger.")
    else:
        blockers.append("D1 and H1 do not agree; M15 setup blocked.")

    return {
        "timeframe": "M15",
        "signal": signal,
        "direction": direction,
        "latest_close": close,
        "latest_timestamp": latest.get("timestamp"),
        "entry_price": _round(entry_price) if entry_price is not None else None,
        "distance_to_entry_pips": _round(distance_to_entry_pips) if distance_to_entry_pips is not None else None,
        "yesterday_high": y_high,
        "yesterday_low": y_low,
        "reasons": reasons,
        "blockers": blockers,
    }


def _analyse_m5(candles: List[Dict[str, Any]], m15: Dict[str, Any]) -> Dict[str, Any]:
    latest = _latest(candles)
    close = _safe_float(latest.get("close"))
    high = _safe_float(latest.get("high"))
    low = _safe_float(latest.get("low"))
    entry_price = m15.get("entry_price")
    direction = m15.get("direction", "none")
    m15_signal = m15.get("signal", "wait")

    signal = "wait"
    reasons: List[str] = []
    blockers: List[str] = []
    distance_to_entry_pips = None

    if not entry_price or direction == "none":
        blockers.append("M15 has no valid entry direction, so M5 cannot confirm.")
    elif m15_signal not in {"setup_forming", "triggered"}:
        signal = "wait"
        blockers.append("M15 setup is not ready; M5 remains wait.")
    elif direction == "long":
        distance_to_entry_pips = _pips(entry_price - close)
        if high >= entry_price:
            signal = "confirm"
            reasons.append("M5 touched or broke the long entry level.")
        elif 0 <= distance_to_entry_pips <= 8:
            signal = "prepare"
            reasons.append("M5 is close to long entry. Prepare but do not chase.")
        else:
            signal = "wait"
            reasons.append("M5 is not close enough to entry.")
    elif direction == "short":
        distance_to_entry_pips = _pips(close - entry_price)
        if low <= entry_price:
            signal = "confirm"
            reasons.append("M5 touched or broke the short entry level.")
        elif 0 <= distance_to_entry_pips <= 8:
            signal = "prepare"
            reasons.append("M5 is close to short entry. Prepare but do not chase.")
        else:
            signal = "wait"
            reasons.append("M5 is not close enough to entry.")

    return {
        "timeframe": "M5",
        "signal": signal,
        "direction": direction,
        "latest_close": close,
        "latest_timestamp": latest.get("timestamp"),
        "entry_price": _round(entry_price) if entry_price else None,
        "distance_to_entry_pips": _round(distance_to_entry_pips) if distance_to_entry_pips is not None else None,
        "reasons": reasons,
        "blockers": blockers,
    }


def build_four_timeframe_signals_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()
    candles_result = get_latest_candles_v1({"symbol": symbol, "timeframes": ["D1", "H1", "M15", "M5"], "limit": 300})
    tfs = candles_result.get("timeframes", {})

    missing = [tf for tf in ["D1", "H1", "M15", "M5"] if not tfs.get(tf, {}).get("ok")]
    if missing:
        return {
            "version": "four_timeframe_signals_v1",
            "ok": False,
            "mode": "personal_research_support_only",
            "broker_connection": False,
            "auto_trading": False,
            "symbol": symbol,
            "error": "missing_market_data",
            "missing_timeframes": missing,
            "market_data": candles_result,
        }

    d1 = _analyse_d1(tfs["D1"].get("candles", []))
    h1 = _analyse_h1(tfs["H1"].get("candles", []), d1.get("bias", "none"))
    m15 = _analyse_m15(tfs["M15"].get("candles", []), d1, h1)
    m5 = _analyse_m5(tfs["M5"].get("candles", []), m15)

    blockers = d1.get("blockers", []) + h1.get("blockers", []) + m15.get("blockers", []) + m5.get("blockers", [])
    reasons = d1.get("reasons", []) + h1.get("reasons", []) + m15.get("reasons", []) + m5.get("reasons", [])

    final_signal = "WAIT"
    if blockers:
        final_signal = "WAIT"
    if d1.get("signal") in {"long_only", "short_only"} and h1.get("regime") == "trend" and m15.get("signal") == "setup_forming":
        final_signal = "WATCH"
    if d1.get("signal") in {"long_only", "short_only"} and h1.get("regime") == "trend" and m15.get("signal") == "triggered":
        final_signal = "READY"
    if final_signal == "READY" and m5.get("signal") == "confirm":
        final_signal = "ENTRY_CONFIRMATION"
    elif final_signal in {"READY", "WATCH"} and m5.get("signal") == "prepare":
        final_signal = "PREPARE"

    strategy_selector_inputs = {
        "symbol": symbol,
        "direction": m15.get("direction", "auto"),
        "d1_signal": d1.get("signal", "unknown"),
        "h1_regime": h1.get("regime", "unknown"),
        "m15_signal": m15.get("signal", "unknown"),
        "m5_signal": m5.get("signal", "unknown"),
        "market_quality": "a_plus" if final_signal in {"ENTRY_CONFIRMATION", "PREPARE"} else ("normal" if final_signal in {"READY", "WATCH"} else "unclear"),
    }

    return {
        "version": "four_timeframe_signals_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "final_signal": final_signal,
        "signals": {
            "D1": d1,
            "H1": h1,
            "M15": m15,
            "M5": m5,
        },
        "strategy_selector_inputs": strategy_selector_inputs,
        "reasons": reasons,
        "blockers": blockers,
        "note": "Signals are for research and manual confirmation only. This engine does not place orders.",
    }
