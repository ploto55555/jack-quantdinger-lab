"""Jack Backtest API skeleton."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_backtest_sample import (
    build_candle_buy_hold_backtest,
    build_sample_backtest,
    build_stored_forex_buy_hold_backtest,
)


jack_backtest_api = Blueprint("jack_backtest_api", __name__, url_prefix="/api/jack-backtest")


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


@jack_backtest_api.get("/health")
def health():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "service": "jack-backtest",
            "status": "ready",
            "auth_required": False,
            "ai_token_required": False,
            "stage": "csv_import_chain_skeleton",
        },
    })


@jack_backtest_api.get("/sample-result")
def sample_result():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_sample_backtest(),
    })


@jack_backtest_api.post("/run-sample")
def run_sample():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_sample_backtest(_json_payload()),
    })


@jack_backtest_api.get("/run-candles-sample")
def run_candles_sample_get():
    payload = {
        "symbol": request.args.get("symbol", "GBPJPY"),
        "timeframe": request.args.get("timeframe", "H4"),
        "limit": request.args.get("limit", 120),
        "initial_capital": request.args.get("initial_capital", 10000),
    }
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_candle_buy_hold_backtest(payload),
    })


@jack_backtest_api.post("/run-candles-sample")
def run_candles_sample_post():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_candle_buy_hold_backtest(_json_payload()),
    })


@jack_backtest_api.get("/run-forex-stored")
def run_forex_stored_get():
    payload = {
        "symbol": request.args.get("symbol", "GBPJPY"),
        "timeframe": request.args.get("timeframe", "H4"),
        "limit": request.args.get("limit", 0),
        "initial_capital": request.args.get("initial_capital", 10000),
    }
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_stored_forex_buy_hold_backtest(payload),
    })


@jack_backtest_api.post("/run-forex-stored")
def run_forex_stored_post():
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": build_stored_forex_buy_hold_backtest(_json_payload()),
    })
