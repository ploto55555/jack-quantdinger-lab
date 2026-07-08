from flask import Blueprint, jsonify, request

from app.services.jack_setup_study_draft import build_setup_study_draft_v1

jack_setup_study_api = Blueprint(
    "jack_setup_study_api",
    __name__,
    url_prefix="/api/jack-brain",
)


def _payload():
    return {
        "symbol": request.args.get("symbol", "GBPJPY"),
        "start_equity": request.args.get("start_equity", 500),
        "target_equity": request.args.get("target_equity", 100000),
        "current_equity": request.args.get("current_equity", request.args.get("equity", 500)),
        "peak_equity": request.args.get("peak_equity", request.args.get("current_equity", request.args.get("equity", 500))),
        "elapsed_days": request.args.get("elapsed_days", 0),
        "total_days": request.args.get("total_days", 365),
        "consecutive_losses": request.args.get("consecutive_losses", 0),
        "news_risk": request.args.get("news_risk", "unknown"),
        "study_gap_pips": request.args.get("study_gap_pips", 15),
        "study_zone_1_units": request.args.get("study_zone_1_units", 1),
        "study_zone_2_units": request.args.get("study_zone_2_units", 3),
        "runner_units": request.args.get("runner_units", 8),
    }


@jack_setup_study_api.get("/setup-study-draft-v1")
def jack_brain_setup_study_draft_v1():
    return jsonify(build_setup_study_draft_v1(_payload()))
