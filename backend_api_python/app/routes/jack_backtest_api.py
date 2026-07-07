"""Jack Backtest API skeleton."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_backtest_sample import build_sample_backtest


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
            "stage": "sample_skeleton",
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
