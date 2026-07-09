from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.jack_market_data_feed import get_latest_candles_v1


DEFAULT_TIMEFRAMES = ["D1", "H1", "M15", "M5"]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float], digits: int = 5) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _point(timestamp: str, value: Optional[float]) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    return {"timestamp": timestamp, "value": _round(value)}


def _sma(candles: List[Dict[str, Any]], period: int) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    window: List[float] = []
    for row in candles:
        close = _safe_float(row.get("close"))
        if close is None:
            continue
        window.append(close)
        if len(window) > period:
            window.pop(0)
        if len(window) == period:
            pt = _point(str(row.get("timestamp", "")), sum(window) / period)
            if pt:
                output.append(pt)
    return output


def _ema(candles: List[Dict[str, Any]], period: int) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    closes: List[float] = []
    multiplier = 2 / (period + 1)
    ema_value: Optional[float] = None
    for row in candles:
        close = _safe_float(row.get("close"))
        if close is None:
            continue
        closes.append(close)
        timestamp = str(row.get("timestamp", ""))
        if len(closes) < period:
            continue
        if ema_value is None:
            ema_value = sum(closes[-period:]) / period
        else:
            ema_value = (close - ema_value) * multiplier + ema_value
        pt = _point(timestamp, ema_value)
        if pt:
            output.append(pt)
    return output


def _bollinger(candles: List[Dict[str, Any]], period: int = 20, multiplier: float = 2.0) -> Dict[str, List[Dict[str, Any]]]:
    upper: List[Dict[str, Any]] = []
    middle: List[Dict[str, Any]] = []
    lower: List[Dict[str, Any]] = []
    width: List[Dict[str, Any]] = []
    window: List[float] = []
    for row in candles:
        close = _safe_float(row.get("close"))
        if close is None:
            continue
        window.append(close)
        if len(window) > period:
            window.pop(0)
        if len(window) != period:
            continue
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        sd = variance ** 0.5
        timestamp = str(row.get("timestamp", ""))
        upper_pt = _point(timestamp, mean + multiplier * sd)
        mid_pt = _point(timestamp, mean)
        lower_pt = _point(timestamp, mean - multiplier * sd)
        width_pt = _point(timestamp, (multiplier * sd * 2))
        if upper_pt:
            upper.append(upper_pt)
        if mid_pt:
            middle.append(mid_pt)
        if lower_pt:
            lower.append(lower_pt)
        if width_pt:
            width.append(width_pt)
    return {"upper": upper, "middle": middle, "lower": lower, "width": width}


def _true_ranges(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    previous_close: Optional[float] = None
    for row in candles:
        high = _safe_float(row.get("high"))
        low = _safe_float(row.get("low"))
        close = _safe_float(row.get("close"))
        timestamp = str(row.get("timestamp", ""))
        if high is None or low is None or close is None:
            continue
        if previous_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - previous_close), abs(low - previous_close))
        output.append({"timestamp": timestamp, "value": _round(tr)})
        previous_close = close
    return output


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> List[Dict[str, Any]]:
    tr = _true_ranges(candles)
    output: List[Dict[str, Any]] = []
    value: Optional[float] = None
    for index, row in enumerate(tr):
        raw = _safe_float(row.get("value"))
        if raw is None:
            continue
        if index < period - 1:
            continue
        if value is None:
            seed_values = [_safe_float(x.get("value")) or 0 for x in tr[index - period + 1 : index + 1]]
            value = sum(seed_values) / period
        else:
            value = ((value * (period - 1)) + raw) / period
        output.append({"timestamp": row.get("timestamp"), "value": _round(value)})
    return output


def _rsi(candles: List[Dict[str, Any]], period: int = 14) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    gains: List[float] = []
    losses: List[float] = []
    previous_close: Optional[float] = None
    avg_gain: Optional[float] = None
    avg_loss: Optional[float] = None
    for row in candles:
        close = _safe_float(row.get("close"))
        timestamp = str(row.get("timestamp", ""))
        if close is None:
            continue
        if previous_close is None:
            previous_close = close
            continue
        change = close - previous_close
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        gains.append(gain)
        losses.append(loss)
        if len(gains) < period:
            previous_close = close
            continue
        if avg_gain is None or avg_loss is None:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period
        if avg_loss == 0:
            rsi_value = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
        output.append({"timestamp": timestamp, "value": _round(rsi_value, 2)})
        previous_close = close
    return output


def build_indicator_overlay_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY") or "GBPJPY").upper()
    timeframe = str(payload.get("timeframe", "H1") or "H1").upper()
    limit = int(payload.get("limit", 320) or 320)
    candle_pack = get_latest_candles_v1({"symbol": symbol, "timeframes": [timeframe], "limit": limit})
    tf_data = (candle_pack.get("timeframes") or {}).get(timeframe, {})
    candles = tf_data.get("candles") or []
    bb = _bollinger(candles, 20, 2.0)
    latest = candles[-1] if candles else None
    indicators = {
        "ema20": _ema(candles, 20),
        "ema50": _ema(candles, 50),
        "sma14": _sma(candles, 14),
        "sma20": _sma(candles, 20),
        "bb_upper": bb["upper"],
        "bb_middle": bb["middle"],
        "bb_lower": bb["lower"],
        "bb_width": bb["width"],
        "atr14": _atr(candles, 14),
        "rsi14": _rsi(candles, 14),
    }
    latest_values = {name: (series[-1] if series else None) for name, series in indicators.items()}
    return {
        "version": "indicator_overlay_v1",
        "ok": bool(candles),
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "timeframe": timeframe,
        "source": "local_csv_candles",
        "latest_candle": latest,
        "counts": {name: len(series) for name, series in indicators.items()},
        "latest_values": latest_values,
        "indicators": indicators,
        "note": "Indicators are calculated from the same local candle feed used by the dashboard. This is research support only.",
    }


def build_indicator_overlay_all_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY") or "GBPJPY").upper()
    raw_timeframes = payload.get("timeframes") or DEFAULT_TIMEFRAMES
    if isinstance(raw_timeframes, str):
        timeframes = [part.strip().upper() for part in raw_timeframes.split(",") if part.strip()]
    else:
        timeframes = [str(x).upper() for x in raw_timeframes]
    result = {
        "version": "indicator_overlay_all_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "timeframes": {},
    }
    for tf in timeframes:
        result["timeframes"][tf] = build_indicator_overlay_v1({"symbol": symbol, "timeframe": tf, "limit": payload.get("limit", 320)})
    result["ok"] = any(v.get("ok") for v in result["timeframes"].values())
    return result
