"""Local candle storage for Jack Data Center.

Phase 1 storage uses JSON files so the backtest pipeline can be proven before
PostgreSQL migrations are finalized. The public contract is intentionally close
to a future candles table: symbol + timeframe + timestamp + OHLCV + source.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STORAGE_ROOT = Path(os.getenv("JACK_CANDLE_STORAGE_DIR", "/tmp/jack_candles"))


@dataclass(frozen=True)
class StorageResult:
    symbol: str
    timeframe: str
    source: str
    rows_written: int
    rows_total: int
    first_timestamp: str | None
    last_timestamp: str | None
    path: str


def save_candles(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    symbol = _clean(payload.get("symbol"), "GBPJPY").upper()
    timeframe = _clean(payload.get("timeframe"), "H4").upper()
    source = _clean(payload.get("source") or payload.get("provider"), "manual")
    candles = payload.get("candles") if isinstance(payload.get("candles"), list) else []
    normalised = _normalise_candles(symbol, timeframe, source, candles)

    existing = _read_raw(symbol, timeframe)
    merged = _merge_by_timestamp(existing, normalised)
    _write_raw(symbol, timeframe, merged)

    return _storage_summary(symbol, timeframe, source, len(normalised), merged)


def load_candles(symbol: str = "GBPJPY", timeframe: str = "H4", limit: int = 500) -> dict[str, Any]:
    symbol = _clean(symbol, "GBPJPY").upper()
    timeframe = _clean(timeframe, "H4").upper()
    limit = max(1, min(_to_int(limit, 500), 20000))
    candles = _read_raw(symbol, timeframe)
    selected = candles[-limit:] if limit else candles
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "rows_total": len(candles),
        "rows_returned": len(selected),
        "first_timestamp": candles[0]["timestamp"] if candles else None,
        "last_timestamp": candles[-1]["timestamp"] if candles else None,
        "candles": selected,
        "storage": "json_file_phase1",
        "path": str(_path(symbol, timeframe)),
    }


def storage_status(symbol: str = "GBPJPY", timeframe: str = "H4") -> dict[str, Any]:
    symbol = _clean(symbol, "GBPJPY").upper()
    timeframe = _clean(timeframe, "H4").upper()
    candles = _read_raw(symbol, timeframe)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "stored": bool(candles),
        "rows_total": len(candles),
        "first_timestamp": candles[0]["timestamp"] if candles else None,
        "last_timestamp": candles[-1]["timestamp"] if candles else None,
        "storage": "json_file_phase1",
        "path": str(_path(symbol, timeframe)),
        "next_step": "Backtest engine should read this storage instead of calling the provider.",
    }


def save_provider_result(provider_result: dict[str, Any] | None) -> dict[str, Any]:
    provider_result = provider_result or {}
    candles = provider_result.get("candles") if isinstance(provider_result.get("candles"), list) else []
    return save_candles({
        "symbol": provider_result.get("symbol", "GBPJPY"),
        "timeframe": provider_result.get("timeframe", "H4"),
        "source": provider_result.get("provider", "provider"),
        "candles": candles,
    })


def _normalise_candles(symbol: str, timeframe: str, source: str, candles: list[Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in candles:
        if not isinstance(item, dict):
            continue
        timestamp = item.get("timestamp") or item.get("datetime") or item.get("date")
        if not timestamp:
            continue
        try:
            output.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": str(timestamp),
                "open": float(item.get("open")),
                "high": float(item.get("high")),
                "low": float(item.get("low")),
                "close": float(item.get("close")),
                "volume": float(item.get("volume") or 0.0),
                "source": str(item.get("source") or item.get("provider") or source),
            })
        except (TypeError, ValueError):
            continue
    return sorted(output, key=lambda row: row["timestamp"])


def _merge_by_timestamp(existing: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {row["timestamp"]: row for row in existing if isinstance(row, dict) and row.get("timestamp")}
    for row in new_rows:
        merged[row["timestamp"]] = row
    return [merged[key] for key in sorted(merged)]


def _storage_summary(symbol: str, timeframe: str, source: str, rows_written: int, merged: list[dict[str, Any]]) -> dict[str, Any]:
    result = StorageResult(
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        rows_written=rows_written,
        rows_total=len(merged),
        first_timestamp=merged[0]["timestamp"] if merged else None,
        last_timestamp=merged[-1]["timestamp"] if merged else None,
        path=str(_path(symbol, timeframe)),
    )
    return result.__dict__ | {"storage": "json_file_phase1"}


def _read_raw(symbol: str, timeframe: str) -> list[dict[str, Any]]:
    path = _path(symbol, timeframe)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _write_raw(symbol: str, timeframe: str, rows: list[dict[str, Any]]) -> None:
    path = _path(symbol, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _path(symbol: str, timeframe: str) -> Path:
    safe_symbol = symbol.upper().replace("/", "")
    safe_timeframe = timeframe.upper().replace("/", "")
    return STORAGE_ROOT / f"{safe_symbol}_{safe_timeframe}.json"


def _clean(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
