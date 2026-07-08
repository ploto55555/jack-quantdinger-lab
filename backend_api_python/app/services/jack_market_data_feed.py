from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT.parent
DEFAULT_DATA_DIRS = [
    BACKEND_ROOT / "data" / "market",
    BACKEND_ROOT / "data",
    APP_ROOT / "data" / "market",
    APP_ROOT / "data",
]

TIMEFRAME_ALIASES = {
    "D1": ["D1", "1440", "DAY", "DAILY"],
    "H1": ["H1", "60", "1H", "HOURLY"],
    "M15": ["M15", "15", "15M"],
    "M5": ["M5", "5", "5M"],
}

TIMEFRAME_MINUTES = {
    "D1": 1440,
    "H1": 60,
    "M15": 15,
    "M5": 5,
}


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _normalise_symbol(symbol: str) -> str:
    return str(symbol or "GBPJPY").upper().replace("/", "").replace("_", "")


def _market_data_dirs() -> List[Path]:
    raw = os.environ.get("JACK_MARKET_DATA_DIR", "").strip()
    dirs: List[Path] = []
    if raw:
        dirs.append(Path(raw))
    dirs.extend(DEFAULT_DATA_DIRS)
    # Keep order while removing duplicates.
    seen = set()
    unique = []
    for d in dirs:
        resolved = str(d)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(d)
    return unique


def _timeframe_file_candidates(symbol: str, timeframe: str) -> List[Path]:
    symbol_clean = _normalise_symbol(symbol)
    aliases = TIMEFRAME_ALIASES.get(timeframe, [timeframe])
    names = []
    for alias in aliases:
        names.extend(
            [
                f"{symbol_clean}_{alias}.csv",
                f"{symbol_clean}{alias}.csv",
                f"{symbol_clean}{alias} (1).csv",
                f"{symbol_clean}_{alias.lower()}.csv",
                f"{symbol_clean.lower()}_{alias.lower()}.csv",
                f"{symbol_clean.lower()}{alias.lower()}.csv",
            ]
        )

    candidates: List[Path] = []
    for directory in _market_data_dirs():
        for name in names:
            candidates.append(directory / name)
    return candidates


def _find_timeframe_file(symbol: str, timeframe: str) -> Optional[Path]:
    candidates = _timeframe_file_candidates(symbol, timeframe)
    for path in candidates:
        if path.exists() and path.is_file():
            return path

    # Flexible fallback scan, useful for manually dropped MT5 files.
    symbol_clean = _normalise_symbol(symbol).lower()
    aliases = [a.lower() for a in TIMEFRAME_ALIASES.get(timeframe, [timeframe])]
    for directory in _market_data_dirs():
        if not directory.exists() or not directory.is_dir():
            continue
        for path in directory.glob("*.csv"):
            name = path.name.lower().replace(" ", "")
            if symbol_clean in name and any(alias.lower() in name for alias in aliases):
                return path
    return None


def _parse_datetime(date_value: str, time_value: str = "") -> Optional[str]:
    date_value = str(date_value or "").strip()
    time_value = str(time_value or "").strip()
    if not date_value:
        return None

    raw_values = []
    if time_value:
        raw_values.append(f"{date_value} {time_value}")
    raw_values.append(date_value)

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y/%m/%d",
    ]

    for raw in raw_values:
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt).isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
        except ValueError:
            continue
    return None


def _row_from_values(values: List[str], headers: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    if headers:
        record = {h.strip().lower(): values[i].strip() if i < len(values) else "" for i, h in enumerate(headers)}
        date_value = record.get("date") or record.get("time") or record.get("datetime") or record.get("timestamp")
        time_value = record.get("hour") or record.get("time_only") or ""
        if record.get("date") and record.get("time"):
            date_value = record.get("date")
            time_value = record.get("time")
        dt = _parse_datetime(date_value or "", time_value)
        open_value = record.get("open") or record.get("o")
        high_value = record.get("high") or record.get("h")
        low_value = record.get("low") or record.get("l")
        close_value = record.get("close") or record.get("c")
        volume_value = record.get("volume") or record.get("tickvol") or record.get("tick_volume") or record.get("vol")
        spread_value = record.get("spread")
    else:
        # MT5 common export: Date, Time, Open, High, Low, Close, TickVol, Vol, Spread
        if len(values) >= 6:
            dt = _parse_datetime(values[0], values[1])
            open_value, high_value, low_value, close_value = values[2], values[3], values[4], values[5]
            volume_value = values[6] if len(values) > 6 else None
            spread_value = values[8] if len(values) > 8 else (values[6] if len(values) == 7 else None)
        else:
            return None

    if not dt:
        return None

    open_price = _safe_float(open_value)
    high_price = _safe_float(high_value)
    low_price = _safe_float(low_value)
    close_price = _safe_float(close_value)
    if None in {open_price, high_price, low_price, close_price}:
        return None

    return {
        "timestamp": dt,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": _safe_float(volume_value, 0),
        "spread": _safe_float(spread_value, None),
    }


def _read_latest_rows(path: Path, limit: int = 300) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not path.exists():
        return [], {"ok": False, "error": "file_not_found", "path": str(path)}

    rows: List[Dict[str, Any]] = []
    total_rows = 0
    header: Optional[List[str]] = None

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
        reader = csv.reader(f, dialect)
        for idx, values in enumerate(reader):
            if not values or all(str(v).strip() == "" for v in values):
                continue
            cleaned = [str(v).strip() for v in values]
            lower = [v.lower() for v in cleaned]
            if idx == 0 and any(v in {"date", "time", "datetime", "timestamp", "open"} for v in lower):
                header = cleaned
                continue
            row = _row_from_values(cleaned, header)
            if row:
                rows.append(row)
                total_rows += 1
                if len(rows) > limit:
                    rows = rows[-limit:]

    return rows, {
        "ok": True,
        "path": str(path),
        "file_name": path.name,
        "row_count": total_rows,
        "returned_rows": len(rows),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
    }


def get_latest_candles_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = _normalise_symbol(payload.get("symbol", "GBPJPY"))
    timeframes = payload.get("timeframes") or ["D1", "H1", "M15", "M5"]
    limit = int(payload.get("limit", 300) or 300)

    result: Dict[str, Any] = {
        "version": "latest_candles_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "timeframes": {},
        "data_dirs_checked": [str(p) for p in _market_data_dirs()],
        "note": "Step 41 reads local/MT5-exported CSV candles. It is not a broker connection yet.",
    }

    for tf in timeframes:
        tf = str(tf).upper()
        path = _find_timeframe_file(symbol, tf)
        if not path:
            result["timeframes"][tf] = {
                "ok": False,
                "error": "csv_file_not_found",
                "expected_examples": [str(p) for p in _timeframe_file_candidates(symbol, tf)[:6]],
                "latest_candle": None,
                "candles": [],
            }
            continue
        rows, meta = _read_latest_rows(path, limit=limit)
        result["timeframes"][tf] = {
            **meta,
            "timeframe": tf,
            "minutes": TIMEFRAME_MINUTES.get(tf),
            "latest_candle": rows[-1] if rows else None,
            "candles": rows,
        }

    result["ok"] = any(tf_data.get("ok") for tf_data in result["timeframes"].values())
    return result


def get_market_data_status_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = _normalise_symbol(payload.get("symbol", "GBPJPY"))
    candles = get_latest_candles_v1({"symbol": symbol, "limit": 5})

    status_rows = []
    for tf, tf_data in candles.get("timeframes", {}).items():
        latest = tf_data.get("latest_candle") or {}
        status_rows.append(
            {
                "timeframe": tf,
                "ok": tf_data.get("ok", False),
                "file_name": tf_data.get("file_name"),
                "row_count": tf_data.get("row_count", 0),
                "last_timestamp": latest.get("timestamp"),
                "last_close": latest.get("close"),
                "error": tf_data.get("error"),
            }
        )

    return {
        "version": "market_data_status_v1",
        "ok": candles.get("ok", False),
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "status": status_rows,
        "data_dirs_checked": candles.get("data_dirs_checked", []),
        "next_step": "Step 42 will calculate D1/H1/M15/M5 signals from these candles.",
    }
