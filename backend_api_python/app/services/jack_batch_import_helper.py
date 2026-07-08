from __future__ import annotations

from typing import Any

from app.services.jack_csv_loader import load_csv_to_storage
from app.services.jack_candle_storage import storage_status


VERSION = "batch_import_helper_v1"

DEFAULT_IMPORTS = [
    {"symbol": "GBPJPY", "timeframe": "H4", "file_path": "data/forex/GBPJPY_H4_ejtrader_10y_normalized.csv"},
    {"symbol": "GBPJPY", "timeframe": "D1", "file_path": "data/forex/GBPJPY_D1_ejtrader_10y_normalized.csv"},
    {"symbol": "USDJPY", "timeframe": "H4", "file_path": "data/forex/USDJPY_H4_ejtrader_10y_normalized.csv"},
    {"symbol": "USDJPY", "timeframe": "D1", "file_path": "data/forex/USDJPY_D1_ejtrader_10y_normalized.csv"},
    {"symbol": "GBPUSD", "timeframe": "H4", "file_path": "data/forex/GBPUSD_H4_ejtrader_10y_normalized.csv"},
    {"symbol": "GBPUSD", "timeframe": "D1", "file_path": "data/forex/GBPUSD_D1_ejtrader_10y_normalized.csv"},
    {"symbol": "EURUSD", "timeframe": "H4", "file_path": "data/forex/EURUSD_H4_ejtrader_10y_normalized.csv"},
    {"symbol": "EURUSD", "timeframe": "D1", "file_path": "data/forex/EURUSD_D1_ejtrader_10y_normalized.csv"},
    {"symbol": "XAUUSD", "timeframe": "H4", "file_path": "data/forex/XAUUSD_H4_ejtrader_10y_normalized.csv"},
    {"symbol": "XAUUSD", "timeframe": "D1", "file_path": "data/forex/XAUUSD_D1_ejtrader_10y_normalized.csv"},
]


def batch_import_forex_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbols = _symbols(payload.get("symbols"))
    timeframes = _timeframes(payload.get("timeframes"))
    selected = [
        item for item in DEFAULT_IMPORTS
        if item["symbol"] in symbols and item["timeframe"] in timeframes
    ]

    results = []
    failures = []
    for item in selected:
        try:
            result = load_csv_to_storage(item)
            results.append({"request": item, "result": result, "ok": True})
        except Exception as exc:  # pragma: no cover
            failures.append({"request": item, "ok": False, "error": str(exc)})

    return {
        "version": VERSION,
        "ok": not failures,
        "requested_symbols": symbols,
        "requested_timeframes": timeframes,
        "total_requested": len(selected),
        "total_imported": len(results),
        "total_failed": len(failures),
        "results": results,
        "failures": failures,
        "status_after_import": batch_storage_status_v1({"symbols": symbols, "timeframes": timeframes}),
    }


def batch_storage_status_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbols = _symbols(payload.get("symbols"))
    timeframes = _timeframes(payload.get("timeframes"))
    items = []
    for symbol in symbols:
        for timeframe in timeframes:
            items.append(storage_status(symbol, timeframe))
    return {
        "version": VERSION,
        "symbols": symbols,
        "timeframes": timeframes,
        "items": items,
        "ready": all(bool(item.get("stored")) for item in items),
    }


def _symbols(value: Any) -> list[str]:
    allowed = ["GBPJPY", "USDJPY", "GBPUSD", "EURUSD", "XAUUSD"]
    if isinstance(value, str) and value.strip():
        value = [value]
    if isinstance(value, list) and value:
        output = []
        for item in value:
            text = str(item).strip().upper()
            if text in allowed and text not in output:
                output.append(text)
        return output or allowed
    return allowed


def _timeframes(value: Any) -> list[str]:
    allowed = ["H4", "D1"]
    if isinstance(value, str) and value.strip():
        value = [value]
    if isinstance(value, list) and value:
        output = []
        for item in value:
            text = str(item).strip().upper()
            if text in allowed and text not in output:
                output.append(text)
        return output or allowed
    return allowed

