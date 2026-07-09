from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.jack_market_data_feed import get_latest_candles_v1


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT.parent
LIVE_DIRS = [
    BACKEND_ROOT / "data" / "market" / "live_ticks",
    BACKEND_ROOT / "data" / "live_ticks",
    APP_ROOT / "data" / "market" / "live_ticks",
    APP_ROOT / "data" / "live_ticks",
]
DEFAULT_TIMEFRAMES = ["D1", "H1", "M15", "M5"]


def _clean_symbol(symbol: str) -> str:
    return str(symbol or "GBPJPY").upper().replace("/", "").replace("_", "")


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _tick_candidates(symbol: str) -> list[Path]:
    symbol = _clean_symbol(symbol)
    names = [
        f"{symbol}_tick.json",
        f"{symbol}_live_tick.json",
        f"{symbol}_live.json",
        f"{symbol.lower()}_tick.json",
        f"{symbol.lower()}_live_tick.json",
        f"{symbol.lower()}_live.json",
    ]
    return [directory / name for directory in LIVE_DIRS for name in names]


def _read_tick_file(symbol: str) -> Optional[Dict[str, Any]]:
    for path in _tick_candidates(symbol):
        if not path.exists() or not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        bid = _safe_float(raw.get("bid"))
        ask = _safe_float(raw.get("ask"))
        mid = _safe_float(raw.get("mid"))
        last = _safe_float(raw.get("last"))
        close = _safe_float(raw.get("close"))
        price = mid or last or close
        if price is None and bid is not None and ask is not None:
            price = (bid + ask) / 2
        if price is None:
            continue
        spread = _safe_float(raw.get("spread_pips"))
        if spread is None and bid is not None and ask is not None:
            spread = abs(ask - bid) * 100
        return {
            "ok": True,
            "source": "local_tick_file",
            "symbol": _clean_symbol(symbol),
            "timestamp": raw.get("timestamp") or raw.get("time") or datetime.now(timezone.utc).isoformat(),
            "price": round(price, 5),
            "bid": round(bid, 5) if bid is not None else None,
            "ask": round(ask, 5) if ask is not None else None,
            "spread_pips": round(spread, 2) if spread is not None else None,
            "file_name": path.name,
            "file_path": str(path),
        }
    return None


def _fallback_from_latest_candle(symbol: str, timeframe: str) -> Dict[str, Any]:
    symbol = _clean_symbol(symbol)
    timeframe = str(timeframe or "M5").upper()
    candle_pack = get_latest_candles_v1({"symbol": symbol, "timeframes": [timeframe], "limit": 2})
    tf_data = (candle_pack.get("timeframes") or {}).get(timeframe, {})
    latest = tf_data.get("latest_candle") or {}
    close = _safe_float(latest.get("close"))
    return {
        "ok": close is not None,
        "source": "latest_candle_close_fallback",
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": latest.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "price": round(close, 5) if close is not None else None,
        "bid": None,
        "ask": None,
        "spread_pips": None,
        "file_name": tf_data.get("file_name"),
        "note": "No local tick file found yet. Using the latest candle close as a live reference line until MT5 tick bridge is added.",
    }


def get_live_price_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = _clean_symbol(payload.get("symbol", "GBPJPY"))
    timeframe = str(payload.get("timeframe", "M5") or "M5").upper()
    tick = _read_tick_file(symbol)
    if tick:
        tick.update({
            "version": "live_price_v1",
            "mode": "personal_research_support_only",
            "broker_connection": False,
            "auto_trading": False,
        })
        return tick
    fallback = _fallback_from_latest_candle(symbol, timeframe)
    fallback.update({
        "version": "live_price_v1",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
    })
    return fallback


def get_live_price_all_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = _clean_symbol(payload.get("symbol", "GBPJPY"))
    raw_timeframes = payload.get("timeframes") or DEFAULT_TIMEFRAMES
    if isinstance(raw_timeframes, str):
        timeframes = [part.strip().upper() for part in raw_timeframes.split(",") if part.strip()]
    else:
        timeframes = [str(tf).upper() for tf in raw_timeframes]
    result = {
        "version": "live_price_all_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "timeframes": {},
        "tick_file_candidates": [str(p) for p in _tick_candidates(symbol)[:8]],
    }
    for tf in timeframes:
        result["timeframes"][tf] = get_live_price_v1({"symbol": symbol, "timeframe": tf})
    result["ok"] = any(v.get("ok") for v in result["timeframes"].values())
    return result
