"""Read-only Jack Personal OS helper routes."""
from __future__ import annotations

from flask import jsonify, request

from app.openapi.blueprint import HumanBlueprint as Blueprint
from app.services.jack_personal_os_registry import JACK_PERSONAL_OS_TOOLS
from app.services.jack_personal_os_rules import decide_risk_percent, grade_setup
from app.utils.auth import login_required


jack_personal_os_blp = Blueprint("jack_personal_os", __name__)


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


@jack_personal_os_blp.route("/tools", methods=["GET"])
@login_required
def list_jack_tools():
    """List Jack Personal OS draft tools."""
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "enabled": False,
            "tools": [_tool_to_dict(tool) for tool in JACK_PERSONAL_OS_TOOLS],
        },
    })


@jack_personal_os_blp.route("/grade-setup", methods=["POST"])
@login_required
def grade_setup_route():
    """Map a 0-20 score into a Jack setup grade."""
    data = request.get_json() or {}
    score = data.get("score", 0)
    result = grade_setup(score)
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "score": result.score,
            "grade": result.grade.value,
            "note": result.note,
        },
    })


@jack_personal_os_blp.route("/risk-decision", methods=["POST"])
@login_required
def risk_decision_route():
    """Calculate a Jack risk-mode decision from simple inputs."""
    data = request.get_json() or {}
    decision = decide_risk_percent(
        equity=float(data.get("equity") or 0),
        drawdown_percent=float(data.get("drawdown_percent") or 0),
        setup_score=int(data.get("setup_score") or 0),
        losing_streak=int(data.get("losing_streak") or 0),
    )
    return jsonify({
        "code": 1,
        "msg": "ok",
        "data": {
            "allowed": decision.allowed,
            "mode": decision.mode.value,
            "risk_percent": decision.risk_percent,
            "note": decision.note,
        },
    })
