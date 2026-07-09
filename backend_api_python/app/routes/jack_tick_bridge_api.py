from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_tick_bridge_status import get_tick_bridge_status_v1


jack_tick_bridge_api = Blueprint(
    "jack_tick_bridge_api",
    __name__,
    url_prefix="/api/jack-brain",
)


@jack_tick_bridge_api.get("/tick-bridge-status-v1")
def jack_tick_bridge_status_v1():
    return jsonify(get_tick_bridge_status_v1({"symbol": request.args.get("symbol", "GBPJPY")}))
