"""Jack market data provider adapter.

Phase 1 Data Center adapter.

This file creates one stable interface for market data providers. Backtests
should read local stored candles; provider calls are for import/update jobs.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.jack_dukascopy_provider import fetch_dukascopy_candles


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    label: str
    asset_classes: list[str]
    requires_api_key: bool
    env_key_name: str | None
    status: str
    note: str


@dataclass(frozen=True)
class ProviderCandle:
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    provider: str


PROVIDERS = [
    ProviderSpec(
        provider="sample",
        label="Sample deterministic data",
        asset_classes=["forex", "metal", "stock", "etf"],
        requires_api_key=False,
        env_key_name=None,
        status="ready",
        note="Local deterministic candles for testing the Data Center flow.",
    ),
    ProviderSpec(
        provider="dukascopy",
        label="Dukascopy historical data",
        asset_classes=["forex", "metal"],
        requires_api_key=False,
        env_key_name=None,
        status="http_fetch_ready_limited_window",
        note="Primary route for long-history Forex/Gold backtest data. Start with small test windows, then store locally.",
    ),
    ProviderSpec(
        provider="twelve_data",
        label="Twelve Data",
        asset_classes=["forex", "metal", "stock", "etf", "index"],
        requires_api_key=True,
        env_key_name="TWELVE_DATA_API_KEY",
        status="http_fetch_ready",
        note="Simple API route, but free plans may hit 429 rate limits. Use as backup/validation route.",
    ),
    ProviderSpec(
        provider="oanda",
        label="OANDA",
        asset_classes=["forex", "metal"],
        requires_api_key=True,
        env_key_name="OANDA_API_KEY",
        status="adapter_stub",
        note="Use later for Forex data and paper/broker research flow.",
    ),
    ProviderSpec(
        provider="yahoo",
        label="Yahoo-style market data",
        asset_classes=["stock", "etf", "index"],
        requires_api_key=False,
        env_key_name=None,
        status="adapter_stub",
        note="Use later for quick stock and ETF daily data testing.",
    ),
    ProviderSpec(
        provider="stooq",
        label="Stooq-style free daily data",
        asset_classes=["stock", "etf", "index", "forex"],
        requires_api_key=False,
        env_key_name=None,
        status="adapter_stub",
        note="Backup no-key daily data route for MVP tests after formatter is connected.",
    ),
    ProviderSpec(
        provider="polygon",
        label="Polygon",
        asset_classes=["forex", "metal", "stock", "etf", "index"],
        requires_api_key=True,
        env_key_name="POLYGON_API_KEY",
        status="adapter_stub",
        note="Use later for professional market data.",
    ),
]


SUPPORTED_TIMEFRAMES = ["1D", "D1", "H4", "H1", "M15", "M5"]
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"


def list_providers() -> list[dict[str, Any]]:
    return [asdict(provider) | {"api_key_configured": _has_api_key(provider)} for provider in PROVIDERS]


def provider_status(provider_name: str | None = None) -> dict[str, Any]:
    providers = PROVIDERS if not provider_name else [p for p in PROVIDERS if p.provider == provider_name]
    if provider_name and not providers:
        return {
            "provider": provider_name,
            "status": "unknown_provider",
            "available_providers": [p.provider for p in PROVIDERS],
        }
    return {
        "providers": [asdict(provider) | {"api_key_configured": _has_api_key(provider)} for provider in providers],
        "rule": "External providers are for import/update jobs. Backtests should read local stored candles.",
        "recommended_routes": {
            "forex_gold_primary": "dukascopy",
            "forex_gold_backup": "twelve_data",
            "forex_broker_research_later": "oanda",
            "stocks_etf_mvp": "yahoo_or_stooq",
            "stocks_etf_professional_later": "polygon",
        },
    }


def fetch_candles(payload: dict[str, Any] | None) -> dict[str, Any]:
    request_data = _normalise_request(payload)
    provider = request_data["provider"]

    if provider == "sample":
        candles = _sample_provider_candles(request_data)
        return {
            "provider": provider,
            "symbol": request_data["symbol"],
            "timeframe": request_data["timeframe"],
            "start_date": request_data["start_date"],
            "end_date": request_data["end_date"],
            "candles_returned": len(candles),
            "stored_local": False,
            "status": "sample_ready",
            "candles": candles,
            "next_step": "Connect this output to local candle storage, then make backtest read stored candles only.",
        }

    spec = _get_provider(provider)
    if spec is None:
        return {
            "provider": provider,
            "status": "unknown_provider",
            "available_providers": [p.provider for p in PROVIDERS],
            "candles": [],
        }

    if spec.requires_api_key and not _has_api_key(spec):
        return {
            "provider": provider,
            "symbol": request_data["symbol"],
            "timeframe": request_data["timeframe"],
            "status": "missing_api_key",
            "env_key_name": spec.env_key_name,
            "candles": [],
            "message": f"Set {spec.env_key_name} in backend_api_python/.env before real import.",
        }

    if provider == "twelve_data":
        return _fetch_twelve_data(request_data)

    if provider == "dukascopy":
        return fetch_dukascopy_candles(request_data)

    return {
        "provider": provider,
        "symbol": request_data["symbol"],
        "timeframe": request_data["timeframe"],
        "status": "adapter_stub",
        "candles": [],
        "message": "Provider contract is ready. Real HTTP client/import logic for this provider will be implemented later.",
        "request": request_data,
    }


def build_import_job_preview(payload: dict[str, Any] | None) -> dict[str, Any]:
    request_data = _normalise_request(payload)
    spec = _get_provider(request_data["provider"])
    provider_ok = spec is not None
    api_key_ok = True if (not spec or not spec.requires_api_key) else _has_api_key(spec)
    return {
        "job_type": "market_data_api_import",
        "provider": request_data["provider"],
        "symbol": request_data["symbol"],
        "timeframe": request_data["timeframe"],
        "start_date": request_data["start_date"],
        "end_date": request_data["end_date"],
        "provider_supported": provider_ok,
        "api_key_configured": api_key_ok,
        "storage_target": "local_candles_table",
        "backtest_rule": "After import, backtest reads local storage and should not call provider directly.",
        "ready_to_run_real_import": provider_ok and api_key_ok and request_data["provider"] not in {"sample"},
        "next_endpoint": "/api/jack-data/fetch-provider-candles",
        "route_note": _route_note(request_data["provider"]),
    }


def _fetch_twelve_data(request_data: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return {
            "provider": "twelve_data",
            "status": "missing_api_key",
            "env_key_name": "TWELVE_DATA_API_KEY",
            "candles": [],
        }

    params = {
        "symbol": _to_twelve_data_symbol(request_data["symbol"]),
        "interval": _to_twelve_data_interval(request_data["timeframe"]),
        "start_date": request_data["start_date"],
        "end_date": request_data["end_date"],
        "outputsize": request_data["limit"],
        "apikey": api_key,
        "format": "JSON",
    }
    url = f"{TWELVE_DATA_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return _provider_error("twelve_data", request_data, f"http_error_{exc.code}", exc.read().decode("utf-8", errors="ignore"))
    except urllib.error.URLError as exc:
        return _provider_error("twelve_data", request_data, "url_error", str(exc.reason))
    except TimeoutError:
        return _provider_error("twelve_data", request_data, "timeout", "Provider request timed out.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _provider_error("twelve_data", request_data, "bad_json", raw[:500])

    if payload.get("status") == "error" or "values" not in payload:
        return {
            "provider": "twelve_data",
            "symbol": request_data["symbol"],
            "provider_symbol": params["symbol"],
            "timeframe": request_data["timeframe"],
            "provider_interval": params["interval"],
            "status": "provider_error",
            "candles": [],
            "provider_response": {k: v for k, v in payload.items() if k != "values"},
        }

    candles = _normalise_twelve_data_values(request_data, payload.get("values", []))
    return {
        "provider": "twelve_data",
        "symbol": request_data["symbol"],
        "provider_symbol": params["symbol"],
        "timeframe": request_data["timeframe"],
        "provider_interval": params["interval"],
        "start_date": request_data["start_date"],
        "end_date": request_data["end_date"],
        "candles_returned": len(candles),
        "stored_local": False,
        "status": "fetched_not_stored",
        "candles": candles,
        "next_step": "Persist these candles to local storage, then make backtest read stored candles only.",
    }


def _normalise_twelve_data_values(request_data: dict[str, Any], values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[ProviderCandle] = []
    for item in reversed(values):
        dt_value = item.get("datetime") or item.get("date")
        if not dt_value:
            continue
        try:
            candle = ProviderCandle(
                symbol=request_data["symbol"],
                timeframe=request_data["timeframe"],
                timestamp=_normalise_timestamp(str(dt_value)),
                open=float(item.get("open")),
                high=float(item.get("high")),
                low=float(item.get("low")),
                close=float(item.get("close")),
                volume=float(item.get("volume") or 0.0),
                provider="twelve_data",
            )
        except (TypeError, ValueError):
            continue
        candles.append(asdict(candle))
    return candles


def _normalise_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "provider": _clean(payload.get("provider"), "sample").lower(),
        "symbol": _clean(payload.get("symbol"), "GBPJPY").upper(),
        "timeframe": _clean(payload.get("timeframe"), "H4").upper(),
        "start_date": _clean(payload.get("start_date"), "2015-01-01"),
        "end_date": _clean(payload.get("end_date"), "2025-01-01"),
        "limit": max(1, min(_to_int(payload.get("limit"), 200), 5000)),
    }


def _sample_provider_candles(request_data: dict[str, Any]) -> list[dict[str, Any]]:
    symbol = request_data["symbol"]
    timeframe = request_data["timeframe"]
    limit = request_data["limit"]
    step_hours = {"1D": 24, "D1": 24, "H4": 4, "H1": 1, "M15": 0.25, "M5": 1 / 12}.get(timeframe, 4)
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    base_price = 180.0 if symbol.endswith("JPY") else 2300.0 if symbol.startswith("XAU") else 1.25
    candles: list[ProviderCandle] = []

    for idx in range(limit):
        ts = start + timedelta(hours=step_hours * idx)
        drift = idx * (0.025 if symbol.endswith("JPY") else 0.00012)
        wave = ((idx % 9) - 4) * (0.06 if symbol.endswith("JPY") else 0.0004)
        open_price = base_price + drift + wave
        close_price = open_price + ((idx % 5) - 2) * (0.04 if symbol.endswith("JPY") else 0.00025)
        high_price = max(open_price, close_price) + (0.16 if symbol.endswith("JPY") else 0.0008)
        low_price = min(open_price, close_price) - (0.14 if symbol.endswith("JPY") else 0.0007)
        candles.append(
            ProviderCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts.isoformat().replace("+00:00", "Z"),
                open=round(open_price, 5),
                high=round(high_price, 5),
                low=round(low_price, 5),
                close=round(close_price, 5),
                volume=0.0,
                provider="sample",
            )
        )

    return [asdict(candle) for candle in candles]


def _route_note(provider: str) -> str:
    if provider == "dukascopy":
        return "Primary route for long-history Forex/Gold. Small window downloader is connected; store results locally before backtesting."
    if provider == "twelve_data":
        return "Backup/validation route. May hit 429 on free plan."
    if provider in {"yahoo", "stooq"}:
        return "Useful for no-key daily stock/ETF MVP data after formatter is connected."
    return "Provider route exists in architecture; implementation can be added without changing backtest contracts."


def _to_twelve_data_symbol(symbol: str) -> str:
    symbol = symbol.upper().replace("/", "")
    if len(symbol) == 6 and symbol.isalpha():
        return f"{symbol[:3]}/{symbol[3:]}"
    if symbol == "XAUUSD":
        return "XAU/USD"
    return symbol


def _to_twelve_data_interval(timeframe: str) -> str:
    mapping = {
        "1D": "1day",
        "D1": "1day",
        "H4": "4h",
        "H1": "1h",
        "M15": "15min",
        "M5": "5min",
    }
    return mapping.get(timeframe.upper(), "4h")


def _normalise_timestamp(value: str) -> str:
    text = value.strip().replace(" ", "T")
    if "T" not in text:
        text = f"{text}T00:00:00"
    if text.endswith("Z"):
        return text
    return f"{text}Z"


def _provider_error(provider: str, request_data: dict[str, Any], status: str, message: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "symbol": request_data["symbol"],
        "timeframe": request_data["timeframe"],
        "status": status,
        "message": message[:1000],
        "candles": [],
    }


def _get_provider(provider_name: str) -> ProviderSpec | None:
    for provider in PROVIDERS:
        if provider.provider == provider_name:
            return provider
    return None


def _has_api_key(provider: ProviderSpec) -> bool:
    return bool(provider.env_key_name and os.getenv(provider.env_key_name)) if provider.requires_api_key else True


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
