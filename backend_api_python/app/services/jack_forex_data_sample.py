"""Jack Forex Data Center sample service.

This module defines the Forex-first data contract and CSV format before a
real 10+ year import pipeline is connected.
"""
from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


CSV_COLUMNS = ["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume", "source"]
PRIORITY_FOREX_SYMBOLS = ["GBPJPY", "USDJPY", "XAUUSD", "GBPUSD", "EURUSD"]
PRIORITY_TIMEFRAMES = ["1D", "H4", "H1"]
SECOND_PHASE_TIMEFRAMES = ["M15", "M5"]


@dataclass(frozen=True)
class ForexImportRequirement:
    symbol: str
    priority: int
    asset_class: str
    phase_1_timeframes: list[str]
    phase_2_timeframes: list[str]
    preferred_sources: list[str]
    notes: str


REQUIREMENTS = [
    ForexImportRequirement("GBPJPY", 1, "forex", PRIORITY_TIMEFRAMES, SECOND_PHASE_TIMEFRAMES, ["Dukascopy", "OANDA", "Twelve Data"], "Primary Abu system pair."),
    ForexImportRequirement("USDJPY", 1, "forex", PRIORITY_TIMEFRAMES, SECOND_PHASE_TIMEFRAMES, ["Dukascopy", "OANDA", "Twelve Data"], "Important JPY and USD direction pair."),
    ForexImportRequirement("XAUUSD", 1, "metal", PRIORITY_TIMEFRAMES, SECOND_PHASE_TIMEFRAMES, ["Dukascopy", "OANDA", "Twelve Data", "Polygon"], "Gold priority market."),
    ForexImportRequirement("GBPUSD", 1, "forex", PRIORITY_TIMEFRAMES, SECOND_PHASE_TIMEFRAMES, ["Dukascopy", "OANDA", "Twelve Data"], "Major pair for GBP direction."),
    ForexImportRequirement("EURUSD", 1, "forex", PRIORITY_TIMEFRAMES, SECOND_PHASE_TIMEFRAMES, ["Dukascopy", "OANDA", "Twelve Data"], "Major pair for USD direction."),
]


def forex_requirements() -> dict[str, Any]:
    return {
        "goal": "Import Forex / Gold candles first for 10+ year backtests.",
        "priority_symbols": PRIORITY_FOREX_SYMBOLS,
        "phase_1_timeframes": PRIORITY_TIMEFRAMES,
        "phase_2_timeframes": SECOND_PHASE_TIMEFRAMES,
        "storage_rule": "Backtest reads local stored candles only. External APIs or CSV files are used for import/update jobs.",
        "csv_columns": CSV_COLUMNS,
        "requirements": [asdict(item) for item in REQUIREMENTS],
        "quality_checks": [
            "timestamp is valid ISO-8601 UTC",
            "OHLC values are numeric",
            "high >= max(open, close)",
            "low <= min(open, close)",
            "candles are sorted oldest to newest",
            "duplicate symbol/timeframe/timestamp rows are rejected later",
        ],
    }


def csv_template() -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in sample_forex_candles(symbol="GBPJPY", timeframe="H4", limit=5):
        writer.writerow(row)
    return output.getvalue()


def csv_template_json() -> dict[str, Any]:
    return {
        "filename": "jack_forex_candles_template.csv",
        "columns": CSV_COLUMNS,
        "example_rows": sample_forex_candles(symbol="GBPJPY", timeframe="H4", limit=5),
        "csv_text": csv_template(),
    }


def sample_forex_candles(symbol: str = "GBPJPY", timeframe: str = "H4", limit: int = 50) -> list[dict[str, Any]]:
    symbol = (symbol or "GBPJPY").upper()
    timeframe = (timeframe or "H4").upper()
    limit = max(1, min(int(limit or 50), 500))

    step_hours = {"1D": 24, "D1": 24, "H4": 4, "H1": 1, "M15": 0.25, "M5": 1 / 12}.get(timeframe, 4)
    base_price = _base_price(symbol)
    start = datetime(2015, 1, 1, tzinfo=timezone.utc)
    candles = []

    for idx in range(limit):
        ts = start + timedelta(hours=step_hours * idx)
        trend = idx * _trend_unit(symbol)
        wave = ((idx % 11) - 5) * _wave_unit(symbol)
        open_price = base_price + trend + wave
        close_price = open_price + ((idx % 5) - 2) * _close_unit(symbol)
        high_price = max(open_price, close_price) + _range_unit(symbol)
        low_price = min(open_price, close_price) - _range_unit(symbol) * 0.88
        candles.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": ts.isoformat().replace("+00:00", "Z"),
            "open": round(open_price, _price_digits(symbol)),
            "high": round(high_price, _price_digits(symbol)),
            "low": round(low_price, _price_digits(symbol)),
            "close": round(close_price, _price_digits(symbol)),
            "volume": 0.0,
            "source": "forex_sample",
        })
    return candles


def validate_csv_text(csv_text: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text or ""))
    rows = list(reader)
    errors: list[str] = []

    if reader.fieldnames != CSV_COLUMNS:
        errors.append(f"CSV columns must be exactly: {','.join(CSV_COLUMNS)}")

    for idx, row in enumerate(rows[:1000], start=2):
        try:
            open_price = float(row.get("open", ""))
            high_price = float(row.get("high", ""))
            low_price = float(row.get("low", ""))
            close_price = float(row.get("close", ""))
            datetime.fromisoformat((row.get("timestamp") or "").replace("Z", "+00:00"))
        except Exception as exc:  # noqa: BLE001 - validation endpoint should report all simple issues.
            errors.append(f"line {idx}: invalid value: {exc}")
            continue
        if high_price < max(open_price, close_price):
            errors.append(f"line {idx}: high is below open/close")
        if low_price > min(open_price, close_price):
            errors.append(f"line {idx}: low is above open/close")

    return {
        "valid": not errors,
        "rows_checked": len(rows),
        "errors": errors[:20],
        "note": "Validation only. It does not store candles yet.",
    }


def _base_price(symbol: str) -> float:
    return {
        "GBPJPY": 186.0,
        "USDJPY": 120.0,
        "XAUUSD": 1200.0,
        "GBPUSD": 1.55,
        "EURUSD": 1.18,
    }.get(symbol, 100.0)


def _trend_unit(symbol: str) -> float:
    return 0.035 if symbol.endswith("JPY") else 0.00018 if symbol.endswith("USD") and symbol != "XAUUSD" else 0.42


def _wave_unit(symbol: str) -> float:
    return 0.08 if symbol.endswith("JPY") else 0.00045 if symbol.endswith("USD") and symbol != "XAUUSD" else 1.6


def _close_unit(symbol: str) -> float:
    return 0.055 if symbol.endswith("JPY") else 0.00028 if symbol.endswith("USD") and symbol != "XAUUSD" else 0.9


def _range_unit(symbol: str) -> float:
    return 0.22 if symbol.endswith("JPY") else 0.0011 if symbol.endswith("USD") and symbol != "XAUUSD" else 3.8


def _price_digits(symbol: str) -> int:
    return 3 if symbol.endswith("JPY") else 2 if symbol == "XAUUSD" else 5
