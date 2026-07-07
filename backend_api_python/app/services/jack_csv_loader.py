"""CSV loader for Jack Data Center."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.services.jack_candle_storage import save_candles


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").exists() or (parent / "docker-compose.yml").exists():
            return parent
    return Path.cwd()


ROOT = _find_project_root()
DATA_DIR = ROOT / "data"


def csv_loader_health() -> dict:
    return {"status": "ready", "root": str(ROOT), "data_dir": str(DATA_DIR)}


def load_csv_to_storage(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").strip().upper()
    timeframe = str(payload.get("timeframe") or "H4").strip().upper()
    rel_path = str(payload.get("file_path") or "").strip()
    path = _safe_path(rel_path)

    if path is None:
        return {"status": "invalid_file_path", "message": "Use data/forex/your_file.csv", "root": str(ROOT), "data_dir": str(DATA_DIR), "symbol": symbol, "timeframe": timeframe}
    if not path.exists():
        return {"status": "file_not_found", "file_path": str(path), "root": str(ROOT), "data_dir": str(DATA_DIR), "symbol": symbol, "timeframe": timeframe}

    candles: list[dict[str, Any]] = []
    rows_read = 0
    rows_skipped = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return {"status": "bad_csv", "message": "CSV needs a header row."}
        columns = _columns(reader.fieldnames)
        missing = _missing(columns)
        if missing:
            return {"status": "bad_csv", "message": "Missing columns: " + ", ".join(missing), "found": reader.fieldnames}
        for row in reader:
            rows_read += 1
            candle = _row(row, columns, symbol, timeframe)
            if candle is None:
                rows_skipped += 1
                continue
            candles.append(candle)

    if not candles:
        return {"status": "no_valid_candles", "rows_read": rows_read, "rows_skipped": rows_skipped}

    result = save_candles({"symbol": symbol, "timeframe": timeframe, "source": "csv", "candles": candles})
    return {
        "status": "imported",
        "symbol": symbol,
        "timeframe": timeframe,
        "file_path": str(path),
        "rows_read": rows_read,
        "rows_imported": len(candles),
        "rows_skipped": rows_skipped,
        "first_timestamp": candles[0]["timestamp"],
        "last_timestamp": candles[-1]["timestamp"],
        "storage_result": result,
    }


def _row(raw: dict[str, Any], columns: dict[str, str], symbol: str, timeframe: str) -> dict[str, Any] | None:
    try:
        timestamp = _timestamp(raw, columns)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": _normalise_ts(timestamp),
            "open": float(raw[columns["open"]]),
            "high": float(raw[columns["high"]]),
            "low": float(raw[columns["low"]]),
            "close": float(raw[columns["close"]]),
            "volume": float(raw.get(columns.get("volume", ""), 0) or 0),
            "source": "csv",
        }
    except (KeyError, TypeError, ValueError):
        return None


def _timestamp(raw: dict[str, Any], columns: dict[str, str]) -> str:
    if "timestamp" in columns:
        return str(raw[columns["timestamp"]])
    if "date" in columns and "time" in columns:
        return f"{raw[columns['date']]}T{raw[columns['time']]}"
    return str(raw[columns["date"]])


def _columns(names: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        key = name.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        alias = {
            "timestamp": "timestamp", "datetime": "timestamp", "date_time": "timestamp", "gmt_time": "timestamp",
            "date": "date", "time": "time",
            "open": "open", "o": "open",
            "high": "high", "h": "high",
            "low": "low", "l": "low",
            "close": "close", "c": "close", "last": "close",
            "volume": "volume", "vol": "volume", "tick_volume": "volume",
        }.get(key)
        if alias and alias not in out:
            out[alias] = name
    return out


def _missing(columns: dict[str, str]) -> list[str]:
    missing = [x for x in ["open", "high", "low", "close"] if x not in columns]
    if "timestamp" not in columns and "date" not in columns:
        missing.insert(0, "timestamp_or_date")
    return missing


def _normalise_ts(value: str) -> str:
    text = str(value).strip().replace(" ", "T")
    if "T" not in text:
        text = f"{text}T00:00:00"
    return text if text.endswith("Z") else text.replace("+00:00", "Z") + ("" if text.endswith("+00:00") else "Z")


def _safe_path(value: str) -> Path | None:
    if not value or Path(value).is_absolute() or not value.lower().endswith(".csv"):
        return None
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(DATA_DIR.resolve())
    except ValueError:
        return None
    return resolved
