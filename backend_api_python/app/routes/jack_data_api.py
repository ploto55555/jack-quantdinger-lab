"""Jack Data Center API skeleton."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_data_center_sample import (
    data_quality_report,
    get_import_plan,
    list_symbols,
    sample_candles,
)


jack_data_api = Blueprint("jack_data_api", __name__, url_prefix="/api/jack-data")


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


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
            "stage": "sample_skeleton",
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
