"""Jack Backtest API skeleton."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.services.jack_backtest_sample import (
    build_candle_buy_hold_backtest,
    build_sample_backtest,
    build_stored_forex_buy_hold_backtest,
)
from app.services.jack_rule_research_engine import run_rule_research_v1
from app.services.jack_rule_scan import scan_rule_v1
from app.services.jack_walk_forward import walk_forward_v1
from app.services.jack_stability_report import stability_report_v1
from app.services.jack_mtf_research import run_mtf_research_v1
from app.services.jack_research_profiles import get_research_profiles_v1
from app.services.jack_idea_parser import parse_idea_v1
from app.services.jack_idea_runner import run_idea_v1
from app.services.jack_decision_engine import make_decision_v1
from app.services.jack_batch_import_helper import batch_import_forex_v1, batch_storage_status_v1
from app.services.jack_multi_idea_tester import run_multi_idea_test_v1
from app.services.jack_idea_generator import generate_ideas_v1
from app.services.jack_research_loop import run_research_loop_v1
from app.services.jack_memory_report import build_memory_report_v1
from app.services.jack_avoid_list import build_avoid_list_v1, should_skip_idea_v1
from app.services.jack_smart_idea_generator import generate_smart_ideas_v2
from app.services.jack_validation_engine import validate_profile_v1, validate_top_candidates_v1
from app.services.jack_profile_promotion import build_profile_promotion_v1
from app.services.jack_risk_mode_v2 import calculate_risk_mode_v2
from app.services.jack_capital_stage_engine import build_capital_stage_v1, build_capital_path_v1
from app.services.jack_trade_journal import add_trade_journal_v1, list_trade_journal_v1, update_trade_journal_v1, trade_journal_summary_v1
from app.services.jack_learning_engine import build_learning_report_v1
from app.services.jack_daily_command_center import build_daily_command_center_v1
from app.services.jack_goal_backtest_engine import run_goal_backtest_v1
from app.services.jack_research_dashboard_api import build_research_dashboard_v1
from app.services.jack_simple_ui_dashboard import build_simple_ui_dashboard_html_v1
from app.services.jack_memory_store import add_memory_v1, list_memory_v1, search_memory_v1, seed_from_research_notes_v1
from app.services.jack_dashboard_preview_html import build_dashboard_preview_html_v1
from app.services.jack_dashboard_summary import build_dashboard_summary_v1
from app.services.jack_research_notes import build_research_notes_v1

jack_backtest_api = Blueprint("jack_backtest_api", __name__, url_prefix="/api/jack-backtest")


def _json_payload() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


@jack_backtest_api.get("/health")
def health():
    return jsonify({"code": 1, "msg": "ok", "data": {"service": "jack-backtest", "status": "ready", "auth_required": False, "ai_token_required": False, "stage": "research_profiles_v1"}})


@jack_backtest_api.get("/sample-result")
def sample_result():
    return jsonify({"code": 1, "msg": "ok", "data": build_sample_backtest()})


@jack_backtest_api.post("/run-sample")
def run_sample():
    return jsonify({"code": 1, "msg": "ok", "data": build_sample_backtest(_json_payload())})


@jack_backtest_api.get("/run-candles-sample")
def run_candles_sample_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "limit": request.args.get("limit", 120), "initial_capital": request.args.get("initial_capital", 10000)}
    return jsonify({"code": 1, "msg": "ok", "data": build_candle_buy_hold_backtest(payload)})


@jack_backtest_api.post("/run-candles-sample")
def run_candles_sample_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_candle_buy_hold_backtest(_json_payload())})


@jack_backtest_api.get("/run-forex-stored")
def run_forex_stored_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "limit": request.args.get("limit", 0), "initial_capital": request.args.get("initial_capital", 10000)}
    return jsonify({"code": 1, "msg": "ok", "data": build_stored_forex_buy_hold_backtest(payload)})


@jack_backtest_api.post("/run-forex-stored")
def run_forex_stored_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_stored_forex_buy_hold_backtest(_json_payload())})


@jack_backtest_api.get("/run-rule-v1")
def run_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "limit": request.args.get("limit", 20000), "initial_capital": request.args.get("initial_capital", 10000), "risk_percent": request.args.get("risk_percent", 1), "ema_fast": request.args.get("ema_fast", 20), "ema_slow": request.args.get("ema_slow", 50), "breakout_lookback": request.args.get("breakout_lookback", 20), "stop_lookback": request.args.get("stop_lookback", 10), "target_r": request.args.get("target_r", 2)}
    return jsonify({"code": 1, "msg": "ok", "data": run_rule_research_v1(payload)})


@jack_backtest_api.post("/run-rule-v1")
def run_rule_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_rule_research_v1(_json_payload())})


@jack_backtest_api.get("/scan-rule-v1")
def scan_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "initial_capital": request.args.get("initial_capital", 10000), "top_n": request.args.get("top_n", 20)}
    return jsonify({"code": 1, "msg": "ok", "data": scan_rule_v1(payload)})


@jack_backtest_api.get("/validate-rule-v1")
def validate_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "initial_capital": request.args.get("initial_capital", 10000), "train_end": request.args.get("train_end", "2017-12-31T23:59:59Z"), "validate_start": request.args.get("validate_start", "2018-01-01T00:00:00Z")}
    return jsonify({"code": 1, "msg": "ok", "data": walk_forward_v1(payload)})


@jack_backtest_api.get("/stability-rule-v1")
def stability_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "timeframe": request.args.get("timeframe", "H4"), "initial_capital": request.args.get("initial_capital", 10000), "top_n": request.args.get("top_n", 20), "train_end": request.args.get("train_end", "2017-12-31T23:59:59Z"), "validate_start": request.args.get("validate_start", "2018-01-01T00:00:00Z")}
    return jsonify({"code": 1, "msg": "ok", "data": stability_report_v1(payload)})


@jack_backtest_api.get("/run-mtf-rule-v1")
def run_mtf_rule_v1_get():
    payload = {"symbol": request.args.get("symbol", "GBPJPY"), "initial_capital": request.args.get("initial_capital", 10000), "risk_percent": request.args.get("risk_percent", 1), "h4_ema_fast": request.args.get("h4_ema_fast", 30), "h4_ema_slow": request.args.get("h4_ema_slow", 150), "d1_ema_fast": request.args.get("d1_ema_fast", 30), "d1_ema_slow": request.args.get("d1_ema_slow", 150), "breakout_lookback": request.args.get("breakout_lookback", 20), "stop_lookback": request.args.get("stop_lookback", 20), "target_r": request.args.get("target_r", 1.5)}
    return jsonify({"code": 1, "msg": "ok", "data": run_mtf_research_v1(payload)})


@jack_backtest_api.get("/research-profiles-v1")
def research_profiles_v1_get():
    payload = {"symbol": request.args.get("symbol", ""), "status": request.args.get("status", "")}
    return jsonify({"code": 1, "msg": "ok", "data": get_research_profiles_v1(payload)})

@jack_backtest_api.get("/research-notes-v1")
def research_notes_v1_get():
    payload = {
        "symbol": request.args.get("symbol", ""),
    }
    return jsonify({"code": 1, "msg": "ok", "data": build_research_notes_v1(payload)})

@jack_backtest_api.get("/dashboard-summary-v1")
def dashboard_summary_v1_get():
    return jsonify({"code": 1, "msg": "ok", "data": build_dashboard_summary_v1({})})

@jack_backtest_api.get("/dashboard-preview-v1")
def dashboard_preview_v1_get():
    return Response(build_dashboard_preview_html_v1(), mimetype="text/html")

@jack_backtest_api.post("/jack-memory/add")
def jack_memory_add_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": add_memory_v1(_json_payload())})

@jack_backtest_api.get("/jack-memory/list")
def jack_memory_list_v1_get():
    payload = {
        "symbol": request.args.get("symbol", ""),
        "memory_type": request.args.get("memory_type", ""),
        "limit": request.args.get("limit", 50),
    }
    return jsonify({"code": 1, "msg": "ok", "data": list_memory_v1(payload)})

@jack_backtest_api.get("/jack-memory/search")
def jack_memory_search_v1_get():
    payload = {
        "query": request.args.get("query", ""),
        "symbol": request.args.get("symbol", ""),
        "limit": request.args.get("limit", 10),
    }
    return jsonify({"code": 1, "msg": "ok", "data": search_memory_v1(payload)})

@jack_backtest_api.post("/jack-memory/seed-research-notes")
def jack_memory_seed_research_notes_v1_post():
    notes = build_research_notes_v1({}).get("notes", [])
    return jsonify({"code": 1, "msg": "ok", "data": seed_from_research_notes_v1(notes)})

@jack_backtest_api.post("/parse-idea-v1")
def parse_idea_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": parse_idea_v1(_json_payload())})

@jack_backtest_api.post("/run-idea-v1")
def run_idea_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_idea_v1(_json_payload())})

@jack_backtest_api.post("/make-decision-v1")
def make_decision_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": make_decision_v1(_json_payload())})

@jack_backtest_api.post("/batch-import-forex-v1")
def batch_import_forex_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": batch_import_forex_v1(_json_payload())})

@jack_backtest_api.get("/batch-storage-status-v1")
def batch_storage_status_v1_get():
    payload = {
        "symbols": request.args.get("symbols", ""),
        "timeframes": request.args.get("timeframes", ""),
    }
    return jsonify({"code": 1, "msg": "ok", "data": batch_storage_status_v1(payload)})

@jack_backtest_api.post("/run-multi-idea-test-v1")
def run_multi_idea_test_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_multi_idea_test_v1(_json_payload())})

@jack_backtest_api.post("/generate-ideas-v1")
def generate_ideas_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": generate_ideas_v1(_json_payload())})

@jack_backtest_api.post("/run-research-loop-v1")
def run_research_loop_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_research_loop_v1(_json_payload())})

@jack_backtest_api.post("/memory-report-v1")
def memory_report_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_memory_report_v1(_json_payload())})

@jack_backtest_api.post("/avoid-list-v1")
def avoid_list_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_avoid_list_v1(_json_payload())})

@jack_backtest_api.post("/should-skip-idea-v1")
def should_skip_idea_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": should_skip_idea_v1(_json_payload())})


@jack_backtest_api.post("/generate-smart-ideas-v2")
def generate_smart_ideas_v2_post():
    return jsonify({"code": 1, "msg": "ok", "data": generate_smart_ideas_v2(_json_payload())})

@jack_backtest_api.post("/validate-profile-v1")
def validate_profile_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": validate_profile_v1(_json_payload())})

@jack_backtest_api.post("/validate-top-candidates-v1")
def validate_top_candidates_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": validate_top_candidates_v1(_json_payload())})

@jack_backtest_api.post("/profile-promotion-v1")
def profile_promotion_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_profile_promotion_v1(_json_payload())})

@jack_backtest_api.post("/risk-mode-v2")
def risk_mode_v2_post():
    return jsonify({"code": 1, "msg": "ok", "data": calculate_risk_mode_v2(_json_payload())})

@jack_backtest_api.post("/capital-stage-v1")
def capital_stage_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_capital_stage_v1(_json_payload())})

@jack_backtest_api.post("/capital-path-v1")
def capital_path_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_capital_path_v1(_json_payload())})

@jack_backtest_api.post("/trade-journal/add-v1")
def trade_journal_add_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": add_trade_journal_v1(_json_payload())})

@jack_backtest_api.post("/trade-journal/list-v1")
def trade_journal_list_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": list_trade_journal_v1(_json_payload())})

@jack_backtest_api.post("/trade-journal/update-v1")
def trade_journal_update_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": update_trade_journal_v1(_json_payload())})

@jack_backtest_api.post("/trade-journal/summary-v1")
def trade_journal_summary_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": trade_journal_summary_v1(_json_payload())})

@jack_backtest_api.post("/learning-report-v1")
def learning_report_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_learning_report_v1(_json_payload())})

@jack_backtest_api.post("/daily-command-center-v1")
def daily_command_center_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_daily_command_center_v1(_json_payload())})

@jack_backtest_api.post("/goal-backtest-v1")
def goal_backtest_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": run_goal_backtest_v1(_json_payload())})

@jack_backtest_api.post("/research-dashboard-v1")
def research_dashboard_v1_post():
    return jsonify({"code": 1, "msg": "ok", "data": build_research_dashboard_v1(_json_payload())})

@jack_backtest_api.get("/simple-ui-dashboard-v1")
def simple_ui_dashboard_v1_get():
    payload = {
        "equity": request.args.get("equity", 500),
        "peak_equity": request.args.get("peak_equity", 500),
        "profile_id": request.args.get("profile_id", "GBPJPY_H4_UP_V1"),
        "setup_quality": request.args.get("setup_quality", "A+"),
        "target_equity": request.args.get("target_equity", 1000000),
    }
    html = build_simple_ui_dashboard_html_v1(payload)
    return Response(html, mimetype="text/html")
