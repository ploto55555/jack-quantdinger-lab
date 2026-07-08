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


from app.services.jack_trade_journal import (
    add_trade_journal_v1,
    list_trade_journal_v1,
    trade_journal_summary_v1,
)

from app.services.jack_memory_store import (
    add_memory_v1,
    list_memory_v1,
    search_memory_v1,
)


@jack_brain_api.post("/save-journal-v1")
def jack_brain_save_journal_v1():
    payload = request.get_json(silent=True) or {}
    result = add_trade_journal_v1(payload)
    return jsonify(result)


@jack_brain_api.get("/list-journal-v1")
def jack_brain_list_journal_v1():
    payload = {
        "symbol": request.args.get("symbol", ""),
        "status": request.args.get("status", ""),
        "limit": request.args.get("limit", 50),
    }
    result = list_trade_journal_v1(payload)
    return jsonify(result)


@jack_brain_api.get("/journal-summary-v1")
def jack_brain_journal_summary_v1():
    payload = {
        "symbol": request.args.get("symbol", ""),
    }
    result = trade_journal_summary_v1(payload)
    return jsonify(result)


@jack_brain_api.post("/save-memory-v1")
def jack_brain_save_memory_v1():
    payload = request.get_json(silent=True) or {}
    result = add_memory_v1(payload)
    return jsonify(result)


@jack_brain_api.get("/list-memory-v1")
def jack_brain_list_memory_v1():
    payload = {
        "symbol": request.args.get("symbol", ""),
        "memory_type": request.args.get("memory_type", ""),
        "limit": request.args.get("limit", 50),
    }
    result = list_memory_v1(payload)
    return jsonify(result)


@jack_brain_api.get("/search-memory-v1")
def jack_brain_search_memory_v1():
    payload = {
        "query": request.args.get("query", ""),
        "symbol": request.args.get("symbol", ""),
        "limit": request.args.get("limit", 10),
    }
    result = search_memory_v1(payload)
    return jsonify(result)


from app.services.jack_capital_compounding import (
    simulate_capital_path_v1,
    compare_compounding_plans_v1,
)


@jack_brain_api.get("/capital-compounding-v1")
def jack_brain_capital_compounding_v1():
    payload = {
        "start_equity": request.args.get("start_equity", 500),
        "daily_growth_percent": request.args.get("daily_growth_percent", 5),
        "days": request.args.get("days", 90),
        "target_equity": request.args.get("target_equity", 1000000),
    }
    result = simulate_capital_path_v1(payload)
    return jsonify(result)


@jack_brain_api.get("/capital-compounding-compare-v1")
def jack_brain_capital_compounding_compare_v1():
    payload = {
        "start_equity": request.args.get("start_equity", 500),
        "days": request.args.get("days", 90),
        "target_equity": request.args.get("target_equity", 1000000),
        "daily_growth_percents": [1, 2, 3, 5, 10],
    }
    result = compare_compounding_plans_v1(payload)
    return jsonify(result)
