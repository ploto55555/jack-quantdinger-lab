"""Jack Backtest API skeleton."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_backtest_sample import (
    build_candle_buy_hold_backtest,
    build_sample_backtest,
    build_stored_forex_buy_hold_backtest,
)
from app.services.jack_rule_research_engine import run_rule_research_v1
from app.services.jack_rule_scan import scan_rule_v1

jack_backtest_api = Blueprint("jack_backtest_api", __name__, url_prefix="/api/jack-backtest")


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


@jack_backtest_api.get("/health")
def health():
    return jsonify({"code": 1, "msg": "ok", "data": {"service": "jack-backtest", "status": "ready", "auth_required": False, "ai_token_required": False, "stage": "rule_scan_v1"}})


@jack_backtest_api.get("/sample-result")
def sample_result():
    return jsonify({"code": 1, "msg": "ok", "data": build_sample_backtest()})


@jack_backtest_api.post("/run-sample")
def run_sample():
    return jsonify({"code": 1, "msg": "ok", "data": build_sample_backtest(_json_payload())})


@jack_backtest_api.get("/run-candles-sample")
def run_candles_sample_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "limit": request.args.get("limit", 120), "initial_capital": request.args.get("initial_capital", 10000)}
    return jsonify({"code": 1, "msg": "ok", "data": build_candle_buy_hold_backtest(payload)})


@jack_backtest_api.post("/run-candles-sample")
def run_candles_sample_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_candle_buy_hold_backtest(_json_payload())})


@jack_backtest_api.get("/run-forex-stored")
def run_forex_stored_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "limit": request.args.get("limit", 0), "initial_capital": request.args.get("initial_capital", 10000)}
    return jsonify({"code": 1, "msg": "ok", "data": build_stored_forex_buy_hold_backtest(payload)})


@jack_backtest_api.post("/run-forex-stored")
def run_forex_stored_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_stored_forex_buy_hold_backtest(_json_payload())})


@jack_backtest_api.get("/run-rule-v1")
def run_rule_v1_get():
    payload = {
        "symbol": request.args.get("symbol", "GBPJPY"),
        "timeframe": request.args.get("timeframe", "H4"),
        "limit": request.args.get("limit", 20000),
        "initial_capital": request.args.get("initial_capital", 10000),
        "risk_percent": request.args.get("risk_percent", 1),
        "ema_fast": request.args.get("ema_fast", 20),
        "ema_slow": request.args.get("ema_slow", 50),
        "breakout_lookback": request.args.get("breakout_lookback", 20),
        "stop_lookback": request.args.get("stop_lookback", 10),
        "target_r": request.args.get("target_r", 2),
    }
    return jsonify({"code": 1, "msg": "ok", "data": run_rule_research_v1(payload)})


@jack_backtest_api.post("/run-rule-v1")
def run_rule_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_rule_research_v1(_json_payload())})


@jack_backtest_api.get("/scan-rule-v1")
def scan_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "initial_capital": request.args.get("initial_capital", 10000), "top_n": request.args.get("top_n", 20)}
    return jsonify({"code": 1, "msg": "ok", "data": scan_rule_v1(payload)})
