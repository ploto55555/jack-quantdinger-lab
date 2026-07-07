"""Jack Forex Data Center API skeleton."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.services.jack_forex_csv_store import (
    import_csv_text,
    list_stored_datasets,
    load_stored_candles,
    stored_quality_report,
)
from app.services.jack_forex_data_sample import (
    csv_template,
    csv_template_json,
    forex_requirements,
    sample_forex_candles,
    validate_csv_text,
)


jack_forex_data_api = Blueprint("jack_forex_data_api", __name__, url_prefix="/api/jack-forex-data")


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


@jack_forex_data_api.get("/health")
def health():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "service": "jack-forex-data-center",
            "status": "ready",
            "auth_required": False,
            "external_api_required": False,
            "stage": "csv_import_skeleton",
        },
    })


@jack_forex_data_api.get("/requirements")
def requirements():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": forex_requirements(),
    })


@jack_forex_data_api.get("/csv-template")
def template_json():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": csv_template_json(),
    })


@jack_forex_data_api.get("/csv-template.csv")
def template_csv():
    return Response(
        csv_template(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=jack_forex_candles_template.csv"},
    )


@jack_forex_data_api.get("/sample-forex-candles")
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
            "candles": sample_forex_candles(symbol=symbol, timeframe=timeframe, limit=limit),
        },
    })


@jack_forex_data_api.post("/validate-csv")
def validate_csv():
    payload = _json_payload()
    csv_text = str(payload.get("csv_text", ""))
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": validate_csv_text(csv_text),
    })


@jack_forex_data_api.post("/import-csv")
def import_csv():
    payload = _json_payload()
    csv_text = str(payload.get("csv_text", ""))
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": import_csv_text(csv_text),
    })


@jack_forex_data_api.get("/stored-datasets")
def stored_datasets():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": list_stored_datasets(),
    })


@jack_forex_data_api.get("/stored-candles")
def stored_candles():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    limit = _int_arg("limit", 0)
    candles = load_stored_candles(symbol=symbol, timeframe=timeframe, limit=limit or None)
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "rows": len(candles),
            "candles": candles,
        },
    })


@jack_forex_data_api.get("/stored-quality-report")
def stored_quality():
    symbol = request.args.get("symbol", "GBPJPY")
    timeframe = request.args.get("timeframe", "H4")
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": stored_quality_report(symbol=symbol, timeframe=timeframe),
    })
