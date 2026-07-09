from flask import Blueprint, jsonify, request

from app.services.jack_live_health import build_live_health_v1


jack_stability_api = Blueprint(
    "jack_stability_api",
    __name__,
    url_prefix="/api/jack-brain",
)


@jack_stability_api.get("/live-health-v1")
def jack_brain_live_health_v1():
    raw_timeframes = request.args.get("timeframes", "D1,H1,M15,M5")
    return jsonify(build_live_health_v1({
        "symbol": request.args.get("symbol", "GBPJPY"),
        "timeframes": [part.strip().upper() for part in raw_timeframes.split(",") if part.strip()],
        "stale_after_seconds": request.args.get("stale_after_seconds", 15),
    }))
