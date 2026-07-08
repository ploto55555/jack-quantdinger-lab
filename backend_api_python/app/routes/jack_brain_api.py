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
    return jsonify({"ok": True, "service": "jack_brain_api", "mode": "personal_research_support_only", "broker_connection": False, "auto_trading": False})


@jack_brain_api.get("/context-v1")
def jack_brain_context_v1():
    context = build_brain_context(
        symbol=request.args.get("symbol", "GBPJPY"),
        profile_id=request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        setup_quality=request.args.get("setup_quality", "A+"),
        equity=_get_float_arg("equity", 500),
        peak_equity=_get_float_arg("peak_equity", 500),
        target_equity=_get_float_arg("target_equity", 1000000),
        user_question=request.args.get("user_question", "Explain current backend brain context."),
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
        user_question=request.args.get("user_question", "Explain this backtest result in simple language."),
    )
    return jsonify(explain_backend_brain(context))


@jack_brain_api.get("/decision-journal-draft-v1")
def jack_brain_decision_journal_draft_v1():
    context = build_brain_context(
        symbol=request.args.get("symbol", "GBPJPY"),
        profile_id=request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        setup_quality=request.args.get("setup_quality", "A+"),
        equity=_get_float_arg("equity", 500),
        peak_equity=_get_float_arg("peak_equity", 500),
        target_equity=_get_float_arg("target_equity", 1000000),
        user_question=request.args.get("user_question", "Create decision journal draft."),
    )
    brain_result = explain_backend_brain(context)
    return jsonify(create_decision_journal_draft(context, brain_result))


from app.services.jack_brain_front_ui import get_jack_brain_front_ui_html


@jack_brain_api.get("/front-ui-v1")
def jack_brain_front_ui_v1():
    return get_jack_brain_front_ui_html()


from app.services.jack_trade_journal import add_trade_journal_v1, list_trade_journal_v1, trade_journal_summary_v1
from app.services.jack_memory_store import add_memory_v1, list_memory_v1, search_memory_v1


@jack_brain_api.post("/save-journal-v1")
def jack_brain_save_journal_v1():
    return jsonify(add_trade_journal_v1(request.get_json(silent=True) or {}))


@jack_brain_api.get("/list-journal-v1")
def jack_brain_list_journal_v1():
    return jsonify(list_trade_journal_v1({"symbol": request.args.get("symbol", ""), "status": request.args.get("status", ""), "limit": request.args.get("limit", 50)}))


@jack_brain_api.get("/journal-summary-v1")
def jack_brain_journal_summary_v1():
    return jsonify(trade_journal_summary_v1({"symbol": request.args.get("symbol", "")}))


@jack_brain_api.post("/save-memory-v1")
def jack_brain_save_memory_v1():
    return jsonify(add_memory_v1(request.get_json(silent=True) or {}))


@jack_brain_api.get("/list-memory-v1")
def jack_brain_list_memory_v1():
    return jsonify(list_memory_v1({"symbol": request.args.get("symbol", ""), "memory_type": request.args.get("memory_type", ""), "limit": request.args.get("limit", 50)}))


@jack_brain_api.get("/search-memory-v1")
def jack_brain_search_memory_v1():
    return jsonify(search_memory_v1({"query": request.args.get("query", ""), "symbol": request.args.get("symbol", ""), "limit": request.args.get("limit", 10)}))


from app.services.jack_capital_compounding import simulate_capital_path_v1, compare_compounding_plans_v1


@jack_brain_api.get("/capital-compounding-v1")
def jack_brain_capital_compounding_v1():
    return jsonify(simulate_capital_path_v1({"start_equity": request.args.get("start_equity", 500), "daily_growth_percent": request.args.get("daily_growth_percent", 5), "days": request.args.get("days", 90), "target_equity": request.args.get("target_equity", 1000000)}))


@jack_brain_api.get("/capital-compounding-compare-v1")
def jack_brain_capital_compounding_compare_v1():
    return jsonify(compare_compounding_plans_v1({"start_equity": request.args.get("start_equity", 500), "days": request.args.get("days", 90), "target_equity": request.args.get("target_equity", 1000000), "daily_growth_percents": [1, 2, 3, 5, 10]}))


from app.services.jack_market_context import get_calendar_context_v1, get_news_context_v1, get_market_context_v1


@jack_brain_api.get("/calendar-context-v1")
def jack_brain_calendar_context_v1():
    return jsonify(get_calendar_context_v1({"symbol": request.args.get("symbol", "GBPJPY")}))


@jack_brain_api.get("/news-context-v1")
def jack_brain_news_context_v1():
    return jsonify(get_news_context_v1({"symbol": request.args.get("symbol", "GBPJPY")}))


@jack_brain_api.get("/market-context-v1")
def jack_brain_market_context_v1():
    return jsonify(get_market_context_v1({"symbol": request.args.get("symbol", "GBPJPY")}))


from app.services.jack_strategy_research_agent import research_strategy_goal_v1, save_strategy_research_to_memory_v1


@jack_brain_api.get("/strategy-research-v1")
def jack_brain_strategy_research_v1():
    return jsonify(research_strategy_goal_v1({"goal_text": request.args.get("goal_text", "Find a day trading system that targets around 20 pips per day."), "symbol": request.args.get("symbol", "AUTO"), "target_pips_per_day": request.args.get("target_pips_per_day", 20), "start_equity": request.args.get("start_equity", 500), "backtest_years": request.args.get("backtest_years", 10)}))


@jack_brain_api.post("/strategy-research-save-v1")
def jack_brain_strategy_research_save_v1():
    return jsonify(save_strategy_research_to_memory_v1(request.get_json(silent=True) or {}))


from app.services.jack_beta_terminal_ui import get_jack_beta_terminal_ui_html


@jack_brain_api.get("/beta-terminal-v1")
def jack_brain_beta_terminal_v1():
    return get_jack_beta_terminal_ui_html()


from app.services.jack_strategy_library import load_strategy_library_v1, list_strategy_candidates_v1, get_strategy_candidate_v1, choose_strategy_for_goal_v1


@jack_brain_api.get("/strategy-library-v1")
def jack_brain_strategy_library_v1():
    return jsonify(load_strategy_library_v1())


@jack_brain_api.get("/strategy-candidates-v1")
def jack_brain_strategy_candidates_v1():
    return jsonify(list_strategy_candidates_v1({"role": request.args.get("role", ""), "mode": request.args.get("mode", ""), "symbol": request.args.get("symbol", ""), "limit": request.args.get("limit", 50)}))


@jack_brain_api.get("/strategy-candidate-v1")
def jack_brain_strategy_candidate_v1():
    return jsonify(get_strategy_candidate_v1({"strategy_id": request.args.get("strategy_id", "")}))


@jack_brain_api.get("/strategy-selector-v1")
def jack_brain_strategy_selector_v1():
    return jsonify(choose_strategy_for_goal_v1({"equity": request.args.get("equity", 500), "peak_equity": request.args.get("peak_equity", request.args.get("equity", 500)), "target_equity": request.args.get("target_equity", 100000), "consecutive_losses": request.args.get("consecutive_losses", 0), "news_risk": request.args.get("news_risk", "unknown"), "market_quality": request.args.get("market_quality", "normal")}))


from app.services.jack_goal_planner import build_goal_path_v1, get_goal_mode_v1, build_goal_brief_v1


@jack_brain_api.get("/goal-path-v1")
def jack_brain_goal_path_v1():
    return jsonify(build_goal_path_v1({"start_equity": request.args.get("start_equity", 500), "target_equity": request.args.get("target_equity", 100000), "current_equity": request.args.get("current_equity", request.args.get("start_equity", 500)), "elapsed_days": request.args.get("elapsed_days", 0), "total_days": request.args.get("total_days", 365)}))


@jack_brain_api.get("/goal-mode-v1")
def jack_brain_goal_mode_v1():
    return jsonify(get_goal_mode_v1({"start_equity": request.args.get("start_equity", 500), "target_equity": request.args.get("target_equity", 100000), "current_equity": request.args.get("current_equity", request.args.get("start_equity", 500)), "peak_equity": request.args.get("peak_equity", request.args.get("current_equity", request.args.get("start_equity", 500))), "elapsed_days": request.args.get("elapsed_days", 0), "total_days": request.args.get("total_days", 365), "consecutive_losses": request.args.get("consecutive_losses", 0), "news_risk": request.args.get("news_risk", "unknown"), "market_quality": request.args.get("market_quality", "normal")}))


@jack_brain_api.get("/goal-brief-v1")
def jack_brain_goal_brief_v1():
    return jsonify(build_goal_brief_v1({"start_equity": request.args.get("start_equity", 500), "target_equity": request.args.get("target_equity", 100000), "current_equity": request.args.get("current_equity", request.args.get("start_equity", 500)), "peak_equity": request.args.get("peak_equity", request.args.get("current_equity", request.args.get("start_equity", 500))), "elapsed_days": request.args.get("elapsed_days", 0), "total_days": request.args.get("total_days", 365), "consecutive_losses": request.args.get("consecutive_losses", 0), "news_risk": request.args.get("news_risk", "unknown"), "market_quality": request.args.get("market_quality", "normal")}))


from app.services.jack_strategy_selector_v2 import select_strategy_v2


@jack_brain_api.get("/strategy-selector-v2")
def jack_brain_strategy_selector_v2():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "direction": request.args.get("direction", "auto"), "start_equity": request.args.get("start_equity", 500), "target_equity": request.args.get("target_equity", 100000), "current_equity": request.args.get("current_equity", request.args.get("equity", 500)), "peak_equity": request.args.get("peak_equity", request.args.get("current_equity", request.args.get("equity", 500))), "elapsed_days": request.args.get("elapsed_days", 0), "total_days": request.args.get("total_days", 365), "consecutive_losses": request.args.get("consecutive_losses", 0), "news_risk": request.args.get("news_risk", "unknown"), "market_quality": request.args.get("market_quality", "normal"), "d1_signal": request.args.get("d1_signal", "unknown"), "h1_regime": request.args.get("h1_regime", "unknown"), "m15_signal": request.args.get("m15_signal", "unknown"), "m5_signal": request.args.get("m5_signal", "unknown")}
    return jsonify(select_strategy_v2(payload))


from app.services.jack_backtest_dashboard import get_backtest_dashboard_data_v1, get_backtest_dashboard_html_v1


@jack_brain_api.get("/backtest-dashboard-data-v1")
def jack_brain_backtest_dashboard_data_v1():
    return jsonify(get_backtest_dashboard_data_v1())


@jack_brain_api.get("/backtest-dashboard-v1")
def jack_brain_backtest_dashboard_v1():
    return get_backtest_dashboard_html_v1()


from app.services.jack_market_data_feed import get_market_data_status_v1, get_latest_candles_v1


@jack_brain_api.get("/market-data-status-v1")
def jack_brain_market_data_status_v1():
    return jsonify(get_market_data_status_v1({"symbol": request.args.get("symbol", "GBPJPY")}))


@jack_brain_api.get("/latest-candles-v1")
def jack_brain_latest_candles_v1():
    raw_timeframes = request.args.get("timeframes", "D1,H1,M15,M5")
    return jsonify(get_latest_candles_v1({"symbol": request.args.get("symbol", "GBPJPY"), "timeframes": [part.strip().upper() for part in raw_timeframes.split(",") if part.strip()], "limit": request.args.get("limit", 300)}))


from app.services.jack_timeframe_signal_engine import build_four_timeframe_signals_v1


@jack_brain_api.get("/four-timeframe-signals-v1")
def jack_brain_four_timeframe_signals_v1():
    return jsonify(build_four_timeframe_signals_v1({"symbol": request.args.get("symbol", "GBPJPY")}))
