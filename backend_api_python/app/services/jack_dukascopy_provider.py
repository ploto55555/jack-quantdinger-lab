"""Dukascopy historical data adapter for Jack Data Center.

This adapter downloads small test windows from Dukascopy's public historical
feed, normalises ticks into Jack candle schema, and returns candles that can be
stored by jack_candle_storage.

Phase 1 safety limits:
- Designed for small verification windows first.
- Caps each request to a limited number of hourly chunks.
- Backtests should read local stored candles after import, not call this every run.
"""
from __future__ import annotations

import lzma
import struct
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


DUKASCOPY_BASE_URL = "https://datafeed.dukascopy.com/datafeed"
MAX_HOURLY_CHUNKS_PER_REQUEST = 72


@dataclass(frozen=True)
class DukascopyCandle:
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    provider: str = "dukascopy"


@dataclass(frozen=True)
class Tick:
    timestamp: datetime
    price: float
    volume: float


def fetch_dukascopy_candles(request_data: dict[str, Any]) -> dict[str, Any]:
    symbol = _clean(request_data.get("symbol"), "GBPJPY").upper().replace("/", "")
    timeframe = _clean(request_data.get("timeframe"), "H1").upper()
    start = _parse_date(_clean(request_data.get("start_date"), "2024-01-01"))
    end = _parse_date(_clean(request_data.get("end_date"), "2024-01-03"))

    if end <= start:
        end = start + timedelta(days=1)

    hours = _hour_range(start, end)
    capped = False
    if len(hours) > MAX_HOURLY_CHUNKS_PER_REQUEST:
        hours = hours[:MAX_HOURLY_CHUNKS_PER_REQUEST]
        capped = True

    ticks: list[Tick] = []
    downloaded_chunks = 0
    missing_chunks = 0
    failed_chunks: list[str] = []

    for hour_start in hours:
        result = _download_hour_ticks(symbol, hour_start)
        if result["status"] == "ok":
            downloaded_chunks += 1
            ticks.extend(result["ticks"])
        elif result["status"] == "missing":
            missing_chunks += 1
        else:
            failed_chunks.append(result.get("message", "unknown_error"))

    candles = _aggregate_ticks(symbol=symbol, timeframe=timeframe, ticks=ticks)
    return {
        "provider": "dukascopy",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "status": "fetched_not_stored" if candles else "no_candles_returned",
        "candles_returned": len(candles),
        "stored_local": False,
        "candles": candles,
        "download_report": {
            "hourly_chunks_requested": len(hours),
            "hourly_chunks_downloaded": downloaded_chunks,
            "hourly_chunks_missing": missing_chunks,
            "request_was_capped": capped,
            "max_hourly_chunks_per_request": MAX_HOURLY_CHUNKS_PER_REQUEST,
            "failed_chunks_sample": failed_chunks[:5],
        },
        "next_step": "Use /api/jack-data/fetch-and-store with provider=dukascopy to persist candles locally.",
    }


def _download_hour_ticks(symbol: str, hour_start: datetime) -> dict[str, Any]:
    url = _dukascopy_url(symbol, hour_start)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"status": "missing", "ticks": [], "url": url}
        return {"status": "error", "ticks": [], "url": url, "message": f"http_error_{exc.code}"}
    except urllib.error.URLError as exc:
        return {"status": "error", "ticks": [], "url": url, "message": f"url_error_{exc.reason}"}
    except TimeoutError:
        return {"status": "error", "ticks": [], "url": url, "message": "timeout"}

    try:
        decompressed = lzma.decompress(raw)
    except lzma.LZMAError as exc:
        return {"status": "error", "ticks": [], "url": url, "message": f"lzma_error_{exc}"}

    ticks = _parse_ticks(symbol, hour_start, decompressed)
    return {"status": "ok", "ticks": ticks, "url": url}


def _parse_ticks(symbol: str, hour_start: datetime, data: bytes) -> list[Tick]:
    ticks: list[Tick] = []
    record_size = 20
    if len(data) < record_size:
        return ticks

    price_divisor = _price_divisor(symbol)
    for offset in range(0, len(data) - record_size + 1, record_size):
        chunk = data[offset : offset + record_size]
        try:
            ms, ask_raw, bid_raw, ask_volume, bid_volume = struct.unpack(">IIIff", chunk)
        except struct.error:
            continue
        ask = ask_raw / price_divisor
        bid = bid_raw / price_divisor
        mid = (ask + bid) / 2
        ts = hour_start + timedelta(milliseconds=ms)
        ticks.append(Tick(timestamp=ts, price=mid, volume=float(ask_volume or 0.0) + float(bid_volume or 0.0)))
    return ticks


def _aggregate_ticks(symbol: str, timeframe: str, ticks: list[Tick]) -> list[dict[str, Any]]:
    if not ticks:
        return []
    bucket_minutes = _timeframe_minutes(timeframe)
    buckets: dict[datetime, list[Tick]] = {}
    for tick in sorted(ticks, key=lambda item: item.timestamp):
        key = _bucket_start(tick.timestamp, bucket_minutes)
        buckets.setdefault(key, []).append(tick)

    candles: list[DukascopyCandle] = []
    for ts in sorted(buckets):
        bucket_ticks = buckets[ts]
        prices = [tick.price for tick in bucket_ticks]
        volume = sum(tick.volume for tick in bucket_ticks)
        candles.append(
            DukascopyCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts.isoformat().replace("+00:00", "Z"),
                open=round(prices[0], 6),
                high=round(max(prices), 6),
                low=round(min(prices), 6),
                close=round(prices[-1], 6),
                volume=round(volume, 4),
            )
        )
    return [asdict(candle) for candle in candles]


def _bucket_start(timestamp: datetime, bucket_minutes: int) -> datetime:
    timestamp = timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0)
    total_minutes = timestamp.hour * 60 + timestamp.minute
    bucket_index = total_minutes // bucket_minutes
    bucket_total_minutes = bucket_index * bucket_minutes
    hour = bucket_total_minutes // 60
    minute = bucket_total_minutes % 60
    return timestamp.replace(hour=hour, minute=minute)


def _dukascopy_url(symbol: str, hour_start: datetime) -> str:
    # Dukascopy month folders are zero-based: January = 00.
    year = hour_start.year
    month_zero_based = hour_start.month - 1
    day = hour_start.day
    hour = hour_start.hour
    return f"{DUKASCOPY_BASE_URL}/{symbol}/{year}/{month_zero_based:02d}/{day:02d}/{hour:02d}h_ticks.bi5"


def _hour_range(start: datetime, end: datetime) -> list[datetime]:
    current = start.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    final = end.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    hours: list[datetime] = []
    while current < final:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


def _parse_date(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    if "T" not in text:
        text = f"{text}T00:00:00+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _timeframe_minutes(timeframe: str) -> int:
    mapping = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
        "1D": 1440,
    }
    return mapping.get(timeframe.upper(), 60)


def _price_divisor(symbol: str) -> float:
    symbol = symbol.upper()
    if symbol.endswith("JPY") or symbol.startswith("XAU") or symbol.startswith("XAG"):
        return 1000.0
    return 100000.0


def _clean(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default
