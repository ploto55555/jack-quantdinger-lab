"""Jack Data Center API skeleton."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_candle_storage import (
    load_candles,
    save_candles,
    save_provider_result,
    storage_status,
)
from app.services.jack_csv_loader import load_csv_to_storage
from app.services.jack_data_center_sample import (
    data_quality_report,
    get_import_plan,
    list_symbols,
    sample_candles,
)
from app.services.jack_market_data_provider import (
    build_import_job_preview,
    fetch_candles,
    list_providers,
    provider_status,
)


jack_data_api = Blueprint("jack_data_api", __name__, url_prefix="/api/jack-data")


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


@jack_data_api.get("/health")
def health():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "service": "jack-data-center",
            "status": "ready",
            "auth_required": False,
            "external_api_required": False,
            "stage": "provider_local_storage_csv_import",
        },
    })


@jack_data_api.get("/symbols")
def symbols():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "symbols": list_symbols(),
        },
    })


@jack_data_api.get("/import-plan")
def import_plan():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": get_import_plan(),
    })


@jack_data_api.get("/sample-candles")
def candles():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    limit = _int_arg("limit", 50)
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "candles": sample_candles(symbol=symbol, timeframe=timeframe, limit=limit),
        },
    })


@jack_data_api.get("/quality-report")
def quality_report():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": data_quality_report(symbol=symbol, timeframe=timeframe),
    })


@jack_data_api.get("/providers")
def providers():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "providers": list_providers(),
        },
    })


@jack_data_api.get("/provider-status")
def market_provider_status():
    provider = request.args.get("provider")
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": provider_status(provider),
    })


@jack_data_api.post("/fetch-provider-candles")
def fetch_provider_candles():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": fetch_candles(_json_payload()),
    })


@jack_data_api.post("/import-api-preview")
def import_api_preview():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_import_job_preview(_json_payload()),
    })


@jack_data_api.post("/store-candles")
def store_candles():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": save_candles(_json_payload()),
    })


@jack_data_api.post("/fetch-and-store")
def fetch_and_store():
    provider_result = fetch_candles(_json_payload())
    if provider_result.get("status") not in {"sample_ready", "fetched_not_stored"}:
        return jsonify({
            "code": 1,
            "msg": "provider_result_not_stored",
            "data": {
                "provider_result": provider_result,
                "storage_result": None,
            },
        })
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "provider_result": {
                "provider": provider_result.get("provider"),
                "symbol": provider_result.get("symbol"),
                "timeframe": provider_result.get("timeframe"),
                "status": provider_result.get("status"),
                "candles_returned": provider_result.get("candles_returned"),
            },
            "storage_result": save_provider_result(provider_result),
        },
    })


@jack_data_api.post("/import-csv-file")
def import_csv_file():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": load_csv_to_storage(_json_payload()),
    })


@jack_data_api.get("/stored-candles")
def stored_candles():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    limit = _int_arg("limit", 500)
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": load_candles(symbol=symbol, timeframe=timeframe, limit=limit),
    })


@jack_data_api.get("/storage-status")
def local_storage_status():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": storage_status(symbol=symbol, timeframe=timeframe),
    })
