from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.jack_market_data_feed import get_latest_candles_v1
from app.services.jack_tick_bridge_status import get_tick_bridge_status_v1


DEFAULT_TIMEFRAMES = ["D1", "H1", "M15", "M5"]


def _clean_symbol(symbol: str) -> str:
    return str(symbol or "GBPJPY").upper().replace("/", "").replace("_", "")


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_age_seconds(timestamp: Any) -> Optional[float]:
    if not timestamp:
        return None
    try:
        text = str(timestamp).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds(), 2)
    except Exception:
        return None


def _session_from_utc(now: datetime) -> str:
    hour = now.hour + now.minute / 60
    if 13 <= hour < 16:
        return "London-NewYork Overlap"
    if 0 <= hour < 7:
        return "Asia"
    if 7 <= hour < 13:
        return "London"
    if 16 <= hour < 21:
        return "New York"
    return "Off-session / Thin Liquidity"


def _forex_market_status(now: datetime) -> str:
    # Simple FX week model in UTC: roughly opens Sunday 22:00 and closes Friday 22:00.
    weekday = now.weekday()  # Monday=0, Sunday=6
    if weekday == 5:
        return "WEEKEND_CLOSED"
    if weekday == 6 and now.hour < 22:
        return "WEEKEND_CLOSED"
    if weekday == 4 and now.hour >= 22:
        return "WEEKEND_CLOSED"
    return "OPEN"


def _spread_status(symbol: str, spread_pips: Optional[float]) -> Dict[str, Any]:
    symbol = _clean_symbol(symbol)
    threshold = 4.0 if symbol.endswith("JPY") else 2.0
    if spread_pips is None:
        return {"status": "UNKNOWN", "threshold_pips": threshold, "warning": "NO_SPREAD_DATA"}
    if spread_pips > threshold:
        return {"status": "HIGH", "threshold_pips": threshold, "warning": "HIGH_SPREAD_WARNING"}
    return {"status": "OK", "threshold_pips": threshold, "warning": None}


def _tf_candle_health(symbol: str, timeframe: str, tf_data: Dict[str, Any]) -> Dict[str, Any]:
    latest = tf_data.get("latest_candle") or {}
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "ok": bool(tf_data.get("ok") and latest),
        "status": "OK" if tf_data.get("ok") and latest else "CANDLE_DATA_MISSING",
        "file_name": tf_data.get("file_name"),
        "row_count": tf_data.get("row_count"),
        "returned_rows": tf_data.get("returned_rows"),
        "latest_timestamp": latest.get("timestamp"),
        "latest_close": latest.get("close"),
        "error": tf_data.get("error"),
    }


def build_live_health_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Step 55C: stable frontend/backend health contract for Jack dashboard.

    This is data-health only. It never connects to a broker order endpoint and never
    returns an execution instruction.
    """
    payload = payload or {}
    symbol = _clean_symbol(payload.get("symbol", "GBPJPY"))
    raw_timeframes = payload.get("timeframes") or DEFAULT_TIMEFRAMES
    if isinstance(raw_timeframes, str):
        timeframes = [part.strip().upper() for part in raw_timeframes.split(",") if part.strip()]
    else:
        timeframes = [str(tf).upper() for tf in raw_timeframes]
    stale_after_seconds = int(payload.get("stale_after_seconds", 15) or 15)

    now = datetime.now(timezone.utc)
    tick = get_tick_bridge_status_v1({"symbol": symbol})
    latest_tick = tick.get("latest") or {}
    tick_age = _safe_float(tick.get("age_seconds"))
    if tick_age is None:
        tick_age = _safe_age_seconds(latest_tick.get("written_at") or latest_tick.get("timestamp"))

    tick_found = tick.get("status") == "tick_file_found"
    tick_has_price = bool(latest_tick.get("price") is not None or latest_tick.get("mid") is not None)
    tick_stale = bool(tick_found and tick_age is not None and tick_age > stale_after_seconds)
    if not tick_found:
        tick_state = "OFF"
    elif tick_stale:
        tick_state = "STALE"
    elif tick_has_price:
        tick_state = "LIVE"
    else:
        tick_state = "BAD_TICK_FILE"

    candles = get_latest_candles_v1({"symbol": symbol, "timeframes": timeframes, "limit": 5})
    candle_health = {
        tf: _tf_candle_health(symbol, tf, (candles.get("timeframes") or {}).get(tf, {}))
        for tf in timeframes
    }
    candle_ok_count = sum(1 for row in candle_health.values() if row.get("ok"))
    if candle_ok_count == len(timeframes) and timeframes:
        candle_state = "OK"
    elif candle_ok_count > 0:
        candle_state = "PARTIAL"
    else:
        candle_state = "FAILED"

    spread_pips = _safe_float(latest_tick.get("spread_pips"))
    spread = _spread_status(symbol, spread_pips)
    market_status = _forex_market_status(now)
    session = _session_from_utc(now)

    warnings = []
    if tick_state == "OFF":
        warnings.append("LIVE_OFF_CHECK_MT5_BRIDGE")
    if tick_state == "STALE":
        warnings.append("STALE_TICK")
    if spread.get("warning"):
        warnings.append(spread["warning"])
    if candle_state != "OK":
        warnings.append(f"CANDLES_{candle_state}")
    if market_status != "OPEN":
        warnings.append(market_status)

    if tick_state == "LIVE" and candle_state == "OK" and not spread.get("warning") and market_status == "OPEN":
        system_status = "SYSTEM_OK"
    elif candle_ok_count > 0 or tick_found:
        system_status = "PARTIAL_OK"
    else:
        system_status = "DATA_OFF"

    return {
        "version": "live_health_v1_step_55c",
        "ok": system_status in {"SYSTEM_OK", "PARTIAL_OK"},
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "mt5_symbol": latest_tick.get("mt5_symbol"),
        "system_status": system_status,
        "backend_status": "OK",
        "tick_status": tick_state,
        "tick_age_seconds": tick_age,
        "tick_stale_after_seconds": stale_after_seconds,
        "tick_source": latest_tick.get("source") or tick.get("status"),
        "last_tick_time": latest_tick.get("written_at") or latest_tick.get("timestamp"),
        "price": latest_tick.get("price") or latest_tick.get("mid") or latest_tick.get("last"),
        "bid": latest_tick.get("bid"),
        "ask": latest_tick.get("ask"),
        "mid": latest_tick.get("mid") or latest_tick.get("price"),
        "spread_pips": spread_pips,
        "spread_status": spread.get("status"),
        "spread_threshold_pips": spread.get("threshold_pips"),
        "session": session,
        "market_status": market_status,
        "candle_status": candle_state,
        "candle_ok_count": candle_ok_count,
        "timeframes": candle_health,
        "warnings": warnings,
        "safe_to_research": system_status in {"SYSTEM_OK", "PARTIAL_OK"} and market_status == "OPEN",
        "final_command": "RESEARCH_ONLY_NO_AUTO_TRADING",
        "how_to_start_bridge": 'python scripts\\mt5_tick_bridge_writer.py --mt5-symbol "GBPJPYm#" --output-symbol GBPJPY --interval 2',
        "note": "Step 55C health contract. This reports data reliability only; it is not a buy/sell signal.",
    }
