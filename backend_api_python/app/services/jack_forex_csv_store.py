"""Local file-based Forex CSV candle store.

This is a development-first storage layer. It stores imported CSV candles as
JSON files under JACK_FOREX_STORE_DIR, defaulting to /tmp/jack_forex_data.
Later this can be replaced by PostgreSQL without changing the API contract.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.jack_forex_data_sample import CSV_COLUMNS, validate_csv_text


DEFAULT_STORE_DIR = Path(os.getenv("JACK_FOREX_STORE_DIR", "/tmp/jack_forex_data"))


def import_csv_text(csv_text: str, store_dir: Path | None = None) -> dict[str, Any]:
    validation = validate_csv_text(csv_text)
    if not validation["valid"]:
        return {
            "imported": False,
            "validation": validation,
            "stored_files": [],
            "rows_imported": 0,
        }

    rows = _parse_rows(csv_text)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["symbol"], row["timeframe"])
        grouped.setdefault(key, []).append(row)

    base_dir = _store_dir(store_dir)
    stored_files = []
    rows_imported = 0
    for (symbol, timeframe), candles in grouped.items():
        candles = _dedupe_and_sort(candles)
        path = _store_path(symbol, timeframe, base_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(candles, indent=2, ensure_ascii=False), encoding="utf-8")
        stored_files.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "path": str(path),
            "rows": len(candles),
            "first_timestamp": candles[0]["timestamp"] if candles else None,
            "last_timestamp": candles[-1]["timestamp"] if candles else None,
        })
        rows_imported += len(candles)

    return {
        "imported": True,
        "validation": validation,
        "store_dir": str(base_dir),
        "stored_files": stored_files,
        "rows_imported": rows_imported,
        "note": "Stored to local JSON files. This is a development store before PostgreSQL.",
    }


def list_stored_datasets(store_dir: Path | None = None) -> dict[str, Any]:
    base_dir = _store_dir(store_dir)
    datasets = []
    if base_dir.exists():
        for path in sorted(base_dir.glob("*.json")):
            try:
                candles = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not candles:
                continue
            datasets.append({
                "symbol": candles[0].get("symbol"),
                "timeframe": candles[0].get("timeframe"),
                "rows": len(candles),
                "first_timestamp": candles[0].get("timestamp"),
                "last_timestamp": candles[-1].get("timestamp"),
                "path": str(path),
            })
    return {
        "store_dir": str(base_dir),
        "datasets": datasets,
        "count": len(datasets),
    }


def load_stored_candles(symbol: str, timeframe: str, limit: int | None = None, store_dir: Path | None = None) -> list[dict[str, Any]]:
    path = _store_path(symbol, timeframe, _store_dir(store_dir))
    if not path.exists():
        return []
    candles = json.loads(path.read_text(encoding="utf-8"))
    if limit is not None and limit > 0:
        return candles[:limit]
    return candles


def stored_quality_report(symbol: str, timeframe: str, store_dir: Path | None = None) -> dict[str, Any]:
    candles = load_stored_candles(symbol, timeframe, store_dir=store_dir)
    return {
        "symbol": (symbol or "").upper(),
        "timeframe": (timeframe or "").upper(),
        "status": "stored_ready" if candles else "missing",
        "rows": len(candles),
        "first_timestamp": candles[0]["timestamp"] if candles else None,
        "last_timestamp": candles[-1]["timestamp"] if candles else None,
        "source": candles[0].get("source") if candles else None,
    }


def _parse_rows(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text or ""))
    rows = []
    for row in reader:
        normalised = {
            "symbol": str(row["symbol"]).strip().upper(),
            "timeframe": str(row["timeframe"]).strip().upper(),
            "timestamp": _normalise_timestamp(str(row["timestamp"]).strip()),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row.get("volume") or 0.0),
            "source": str(row.get("source") or "csv").strip() or "csv",
        }
        rows.append(normalised)
    return rows


def _dedupe_and_sort(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_timestamp: dict[str, dict[str, Any]] = {}
    for candle in candles:
        by_timestamp[candle["timestamp"]] = candle
    return [by_timestamp[key] for key in sorted(by_timestamp)]


def _normalise_timestamp(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _store_dir(store_dir: Path | None = None) -> Path:
    return store_dir or DEFAULT_STORE_DIR


def _store_path(symbol: str, timeframe: str, store_dir: Path) -> Path:
    safe_symbol = (symbol or "").upper().replace("/", "")
    safe_timeframe = (timeframe or "").upper().replace("/", "")
    return store_dir / f"{safe_symbol}_{safe_timeframe}.json"
