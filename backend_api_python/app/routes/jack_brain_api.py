from flask import Blueprint, jsonify, request

from app.services.jack_llm_brain import (
    build_brain_context,
    explain_backend_brain,
    create_decision_journal_draft,
)

jack_brain_api = Blueprint(
    "jack_brain_api",
    __name__,
    url_prefix="/api/jack-brain",
)


def _get_float_arg(name: str, default: float) -> float:
    raw_value = request.args.get(name, default)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


@jack_brain_api.get("/health")
def jack_brain_health_v1():
    return jsonify(
        {
            "ok": True,
            "service": "jack_brain_api",
            "mode": "personal_research_support_only",
            "broker_connection": False,
            "auto_trading": False,
        }
    )


@jack_brain_api.get("/context-v1")
def jack_brain_context_v1():
    context = build_brain_context(
        symbol=request.args.get("symbol", "GBPJPY"),
        profile_id=request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        setup_quality=request.args.get("setup_quality", "A+"),
        equity=_get_float_arg("equity", 500),
        peak_equity=_get_float_arg("peak_equity", 500),
        target_equity=_get_float_arg("target_equity", 1000000),
        user_question=request.args.get(
            "user_question",
            "Explain current backend brain context.",
        ),
    )
    return jsonify(context)


@jack_brain_api.get("/explain-backtest-v1")
def jack_brain_explain_backtest_v1():
    context = build_brain_context(
        symbol=request.args.get("symbol", "GBPJPY"),
        profile_id=request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        setup_quality=request.args.get("setup_quality", "A+"),
        equity=_get_float_arg("equity", 500),
        peak_equity=_get_float_arg("peak_equity", 500),
        target_equity=_get_float_arg("target_equity", 1000000),
        user_question=request.args.get(
            "user_question",
            "Explain this backtest result in simple language.",
        ),
    )
    result = explain_backend_brain(context)
    return jsonify(result)


@jack_brain_api.get("/decision-journal-draft-v1")
def jack_brain_decision_journal_draft_v1():
    context = build_brain_context(
        symbol=request.args.get("symbol", "GBPJPY"),
        profile_id=request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        setup_quality=request.args.get("setup_quality", "A+"),
        equity=_get_float_arg("equity", 500),
        peak_equity=_get_float_arg("peak_equity", 500),
        target_equity=_get_float_arg("target_equity", 1000000),
        user_question=request.args.get(
            "user_question",
            "Create decision journal draft.",
        ),
    )
    brain_result = explain_backend_brain(context)
    journal = create_decision_journal_draft(context, brain_result)
    return jsonify(journal)

from app.services.jack_brain_front_ui import get_jack_brain_front_ui_html


@jack_brain_api.get("/front-ui-v1")
def jack_brain_front_ui_v1():
    return get_jack_brain_front_ui_html()
