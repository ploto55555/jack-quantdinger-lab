from flask import Blueprint, jsonify, request

from app.services.jack_daily_ai_summary import build_daily_ai_summary_v1

jack_daily_summary_api = Blueprint(
    "jack_daily_summary_api",
    __name__,
    url_prefix="/api/jack-brain",
)


@jack_daily_summary_api.get("/daily-ai-summary-v1")
def jack_brain_daily_ai_summary_v1():
    return jsonify(build_daily_ai_summary_v1({
        "symbol": request.args.get("symbol", "GBPJPY"),
        "date": request.args.get("date", ""),
        "limit": request.args.get("limit", 500),
    }))
