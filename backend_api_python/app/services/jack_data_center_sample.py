"""Sample-only Jack Data Center service.

This module defines the candle data contract before real 10+ year imports
are connected. It uses deterministic in-memory sample data only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class JackSymbol:
    symbol: str
    asset_class: str
    base: str
    quote: str
    priority: int
    data_status: str
    preferred_sources: list[str]


@dataclass(frozen=True)
class JackCandle:
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


SYMBOLS = [
    JackSymbol("EURUSD", "forex", "EUR", "USD", 1, "planned", ["Twelve Data", "OANDA", "Dukascopy"]),
    JackSymbol("GBPUSD", "forex", "GBP", "USD", 1, "planned", ["Twelve Data", "OANDA", "Dukascopy"]),
    JackSymbol("USDJPY", "forex", "USD", "JPY", 1, "planned", ["Twelve Data", "OANDA", "Dukascopy"]),
    JackSymbol("GBPJPY", "forex", "GBP", "JPY", 1, "sample_ready", ["Twelve Data", "OANDA", "Dukascopy"]),
    JackSymbol("XAUUSD", "metal", "XAU", "USD", 1, "planned", ["Twelve Data", "OANDA", "Polygon"]),
    JackSymbol("SPY", "etf", "SPY", "USD", 2, "planned", ["Yahoo-style", "Polygon", "FMP"]),
    JackSymbol("QQQ", "etf", "QQQ", "USD", 2, "planned", ["Yahoo-style", "Polygon", "FMP"]),
    JackSymbol("TSLA", "stock", "TSLA", "USD", 3, "planned", ["Yahoo-style", "Polygon", "FMP"]),
    JackSymbol("NVDA", "stock", "NVDA", "USD", 3, "planned", ["Yahoo-style", "Polygon", "FMP"]),
]


TIMEFRAMES = ["1D", "H4", "H1", "M15", "M5"]


def list_symbols() -> list[dict[str, Any]]:
    return [asdict(symbol) for symbol in SYMBOLS]


def get_import_plan() -> dict[str, Any]:
    return {
        "goal": "Prepare local 10+ year OHLCV storage for fast backtests.",
        "rule": "Backtest should read local candles only; external APIs are for import/update jobs.",
        "phase_1": {
            "timeframes": ["1D", "H4", "H1"],
            "symbols": ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "XAUUSD", "SPY", "QQQ"],
            "storage": "PostgreSQL candles table later; sample API uses in-memory data now.",
        },
        "phase_2": {
            "timeframes": ["M15", "M5"],
            "symbols": ["GBPJPY", "USDJPY", "XAUUSD", "GBPUSD", "EURUSD"],
            "note": "Small timeframe 10-year data is large; import only priority symbols first.",
        },
        "candle_schema": {
            "symbol": "string",
            "timeframe": "string",
            "timestamp": "ISO-8601 UTC string",
            "open": "float",
            "high": "float",
            "low": "float",
            "close": "float",
            "volume": "float",
            "source": "string",
        },
    }


def sample_candles(symbol: str = "GBPJPY", timeframe: str = "H4", limit: int = 50) -> list[dict[str, Any]]:
    symbol = (symbol or "GBPJPY").upper()
    timeframe = (timeframe or "H4").upper()
    limit = max(1, min(int(limit or 50), 500))

    step_hours = {"1D": 24, "D1": 24, "H4": 4, "H1": 1, "M15": 0.25, "M5": 1 / 12}.get(timeframe, 4)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    base_price = 180.0 if symbol.endswith("JPY") else 1.25
    candles: list[JackCandle] = []

    for idx in range(limit):
        ts = start + timedelta(hours=step_hours * idx)
        drift = idx * 0.035
        wave = ((idx % 7) - 3) * 0.08
        open_price = base_price + drift + wave
        close_price = open_price + ((idx % 5) - 2) * 0.055
        high_price = max(open_price, close_price) + 0.18
        low_price = min(open_price, close_price) - 0.16
        candles.append(
            JackCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts.isoformat().replace("+00:00", "Z"),
                open=round(open_price, 5),
                high=round(high_price, 5),
                low=round(low_price, 5),
                close=round(close_price, 5),
                volume=0.0,
                source="sample",
            )
        )

    return [asdict(candle) for candle in candles]


def data_quality_report(symbol: str = "GBPJPY", timeframe: str = "H4") -> dict[str, Any]:
    candles = sample_candles(symbol=symbol, timeframe=timeframe, limit=50)
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "source": "sample",
        "rows": len(candles),
        "first_timestamp": candles[0]["timestamp"] if candles else None,
        "last_timestamp": candles[-1]["timestamp"] if candles else None,
        "missing_rows": 0,
        "status": "sample_ready",
        "next_step": "Replace sample candles with local 10+ year imported candles.",
    }
