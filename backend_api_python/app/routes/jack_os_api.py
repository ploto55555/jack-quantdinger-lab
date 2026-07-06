"""Jack OS helper API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.jack_personal_os_registry import JACK_PERSONAL_OS_TOOLS
from app.services.jack_personal_os_rules import decide_risk_percent, grade_setup
from app.utils.auth import login_required


jack_os_api = Blueprint("jack_os_api", __name__, url_prefix="/api/jack-os")


def _tool_to_dict(tool):
    return {
        "id": tool.id,
        "category": tool.category,
        "label": tool.label,
        "description": tool.description,
        "risk_level": tool.risk_level,
        "read_only": tool.read_only,
        "enabled": tool.enabled,
        "safety": tool.safety,
    }


@jack_os_api.get("/tools")
@login_required
def tools():
    return jsonify({"code": 1, "msg": "ok", "data": {"tools": [_tool_to_dict(t) for t in JACK_PERSONAL_OS_TOOLS]}})


@jack_os_api.post("/grade-setup")
@login_required
def setup_grade():
    payload = request.get_json() or {}
    result = grade_setup(payload.get("score", 0))
    return jsonify({"code": 1, "msg": "ok", "data": {"score": result.score, "grade": result.grade.value, "note": result.note}})


@jack_os_api.post("/risk-decision")
@login_required
def risk_decision():
    payload = request.get_json() or {}
    result = decide_risk_percent(
        equity=float(payload.get("equity") or 0),
        drawdown_percent=float(payload.get("drawdown_percent") or 0),
        setup_score=int(payload.get("setup_score") or 0),
        losing_streak=int(payload.get("losing_streak") or 0),
    )
    return jsonify({"code": 1, "msg": "ok", "data": {"allowed": result.allowed, "mode": result.mode.value, "risk_percent": result.risk_percent, "note": result.note}})
