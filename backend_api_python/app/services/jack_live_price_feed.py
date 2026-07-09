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


def _age_seconds_from_path(path: Path) -> Optional[float]:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return round((datetime.now(timezone.utc) - modified).total_seconds(), 2)
    except Exception:
        return None


def _pip_size(symbol: str) -> float:
    symbol = _clean_symbol(symbol)
    return 0.01 if symbol.endswith("JPY") else 0.0001


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
    symbol_clean = _clean_symbol(symbol)
    for path in _tick_candidates(symbol_clean):
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
        price = _safe_float(raw.get("price")) or mid or last or close
        if price is None and bid is not None and ask is not None:
            price = (bid + ask) / 2
        if price is None:
            continue
        spread = _safe_float(raw.get("spread_pips"))
        if spread is None and bid is not None and ask is not None:
            spread = abs(ask - bid) / _pip_size(symbol_clean)
        written_at = raw.get("written_at") or raw.get("timestamp") or raw.get("time")
        return {
            "ok": True,
            "source": raw.get("source") or "local_tick_file",
            "symbol": _clean_symbol(raw.get("symbol") or symbol_clean),
            "mt5_symbol": raw.get("mt5_symbol"),
            "timestamp": raw.get("timestamp") or raw.get("time") or datetime.now(timezone.utc).isoformat(),
            "written_at": written_at,
            "age_seconds": _age_seconds_from_path(path),
            "price": round(price, 5),
            "bid": round(bid, 5) if bid is not None else None,
            "ask": round(ask, 5) if ask is not None else None,
            "mid": round(mid, 5) if mid is not None else round(price, 5),
            "last": round(last, 5) if last is not None else None,
            "spread_pips": round(spread, 2) if spread is not None else None,
            "file_name": path.name,
            "file_path": str(path),
            "note": raw.get("note") or "Read-only tick file. No broker order action is used.",
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
        "mt5_symbol": None,
        "timeframe": timeframe,
        "timestamp": latest.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "written_at": None,
        "age_seconds": None,
        "price": round(close, 5) if close is not None else None,
        "bid": None,
        "ask": None,
        "mid": round(close, 5) if close is not None else None,
        "spread_pips": None,
        "file_name": tf_data.get("file_name"),
        "note": "No local tick file found yet. Using latest candle close as a reference line only.",
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
