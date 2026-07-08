from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.jack_market_context import get_market_context_v1
from app.services.jack_memory_store import add_memory_v1


VERSION = "strategy_research_agent_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _goal_text(payload: dict[str, Any]) -> str:
    return str(
        payload.get("goal_text")
        or payload.get("user_goal")
        or "Find a day trading strategy that targets around 20 pips per day."
    ).strip()


def _extract_target_pips(goal_text: str, payload: dict[str, Any]) -> float:
    manual = payload.get("target_pips_per_day")
    if manual is not None:
        return _to_float(manual, 20.0)

    lower = goal_text.lower()
    for token in lower.replace(",", " ").split():
        clean = token.replace("pips", "").replace("pip", "").strip()
        try:
            value = float(clean)
            if 1 <= value <= 500:
                return value
        except ValueError:
            pass

    return 20.0


def _pick_symbols(target_pips: float, preferred_symbol: str = "") -> list[str]:
    preferred_symbol = preferred_symbol.upper().strip()
    if preferred_symbol and preferred_symbol != "AUTO":
        return [preferred_symbol]

    if target_pips >= 50:
        return ["XAUUSD", "GBPJPY", "USDJPY"]
    if target_pips >= 20:
        return ["GBPJPY", "XAUUSD", "USDJPY", "GBPUSD"]
    return ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY"]


def _build_strategy_candidates(symbols: list[str], target_pips: float) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for symbol in symbols:
        if symbol in ["GBPJPY", "USDJPY", "EURJPY", "AUDJPY"]:
            candidates.append({
                "candidate_id": f"CAND_{uuid4().hex[:8].upper()}",
                "symbol": symbol,
                "strategy_name": "London Trend Pullback",
                "strategy_type": "trend_pullback",
                "session": "London / London-New York overlap",
                "timeframes": ["H4 context", "H1 setup", "M15 entry"],
                "target_pips_per_day": target_pips,
                "core_idea": "Use higher timeframe direction, wait for pullback, then enter only when momentum resumes.",
                "entry_logic_draft": [
                    "H4 trend filter using EMA or structure.",
                    "H1 pullback into key zone.",
                    "M15 breakout or rejection confirmation.",
                    "Avoid entry directly before high-impact GBP/JPY/USD events."
                ],
                "risk_filters": [
                    "No trade during unclear range.",
                    "No trade if stop loss is too large for target R.",
                    "Avoid revenge trade after losing streak."
                ],
                "backtest_needed": True,
                "backtest_plan": "Run 5-10 year test by session, spread, stop size, target pips, and news-window exclusion."
            })

            candidates.append({
                "candidate_id": f"CAND_{uuid4().hex[:8].upper()}",
                "symbol": symbol,
                "strategy_name": "Asian Range Breakout",
                "strategy_type": "range_breakout",
                "session": "London open",
                "timeframes": ["M30 range", "M15 breakout", "M5 confirmation"],
                "target_pips_per_day": target_pips,
                "core_idea": "Mark Asian session range, trade only clean breakout with enough space.",
                "entry_logic_draft": [
                    "Build Asian high/low range.",
                    "Trade London breakout only if volatility expands.",
                    "Skip if price is already too far or fake breakout risk is high."
                ],
                "risk_filters": [
                    "No trade if range is too wide.",
                    "No trade if breakout candle is too large.",
                    "Stop after one or two failed attempts."
                ],
                "backtest_needed": True,
                "backtest_plan": "Test Asian range size, breakout time, retest rule, stop loss, and fixed target."
            })

        if symbol == "XAUUSD":
            candidates.append({
                "candidate_id": f"CAND_{uuid4().hex[:8].upper()}",
                "symbol": symbol,
                "strategy_name": "NY Gold Momentum",
                "strategy_type": "momentum_breakout",
                "session": "New York",
                "timeframes": ["H1 context", "M15 setup", "M5 trigger"],
                "target_pips_per_day": target_pips,
                "core_idea": "Use New York momentum expansion on gold, but avoid CPI/FOMC/NFP spike conditions.",
                "entry_logic_draft": [
                    "Use H1 directional bias.",
                    "Wait for NY liquidity expansion.",
                    "M5/M15 momentum trigger after consolidation."
                ],
                "risk_filters": [
                    "Avoid major USD news windows.",
                    "Use strict slippage assumptions.",
                    "Reject if drawdown or losing streak is too high."
                ],
                "backtest_needed": True,
                "backtest_plan": "Backtest NY session only, include slippage, high-impact USD event filters, and max loss streak."
            })

        if symbol in ["EURUSD", "GBPUSD"]:
            candidates.append({
                "candidate_id": f"CAND_{uuid4().hex[:8].upper()}",
                "symbol": symbol,
                "strategy_name": "Clean London Continuation",
                "strategy_type": "session_continuation",
                "session": "London",
                "timeframes": ["H1 context", "M15 setup"],
                "target_pips_per_day": target_pips,
                "core_idea": "Lower volatility pair strategy. More stable but may not always reach 20 pips daily.",
                "entry_logic_draft": [
                    "Trade only with clear London direction.",
                    "Avoid middle of range.",
                    "Use fixed stop and realistic spread assumption."
                ],
                "risk_filters": [
                    "Reject if average daily opportunity is too low.",
                    "Reject if target pips forces poor R:R."
                ],
                "backtest_needed": True,
                "backtest_plan": "Compare 10, 15, 20 pips targets and check if 20 pips is realistic after costs."
            })

    return candidates


def _risk_label_for_goal(target_pips: float, candidate_count: int) -> dict[str, Any]:
    if target_pips >= 50:
        return {
            "label": "extreme",
            "note": "Target is very aggressive for day trading. Needs strict backtest and forward test."
        }
    if target_pips >= 20:
        return {
            "label": "aggressive_but_researchable",
            "note": "20 pips per day is aggressive. System should research it, not assume it is stable."
        }
    if candidate_count == 0:
        return {
            "label": "not_enough_candidates",
            "note": "No suitable candidate generated yet."
        }
    return {
        "label": "researchable",
        "note": "Target can be researched, but still needs historical test, cost model, and forward test."
    }


def research_strategy_goal_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}

    goal_text = _goal_text(payload)
    preferred_symbol = str(payload.get("symbol") or "AUTO").upper().strip()
    target_pips = _extract_target_pips(goal_text, payload)
    start_equity = _to_float(payload.get("start_equity"), 500.0)
    backtest_years = _to_int(payload.get("backtest_years"), 10)

    symbols = _pick_symbols(target_pips, preferred_symbol)
    candidates = _build_strategy_candidates(symbols, target_pips)
    risk = _risk_label_for_goal(target_pips, len(candidates))

    market_context = {}
    if symbols:
        market_context = get_market_context_v1({"symbol": symbols[0]})

    return {
        "version": VERSION,
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now(),
        "research_id": f"SR_{uuid4().hex[:12].upper()}",
        "input": {
            "goal_text": goal_text,
            "preferred_symbol": preferred_symbol,
            "target_pips_per_day": target_pips,
            "start_equity": start_equity,
            "backtest_years_requested": backtest_years
        },
        "selected_symbols": symbols,
        "candidate_count": len(candidates),
        "strategy_candidates": candidates,
        "goal_risk_assessment": risk,
        "market_context_sample": market_context,
        "backtest_status": "candidate_generation_only_backtest_not_run_yet",
        "what_ai_should_do_next": [
            "Run each candidate through real historical backtest.",
            "Compare win rate, average pips per day, profit factor, max drawdown, and losing streak.",
            "Reject candidates that only look good before spread/slippage.",
            "Tag trades around high-impact news and calendar windows.",
            "Save best and rejected candidates into memory for Snowball learning."
        ],
        "safety_note": "This is research support only. It is not a live trading signal or automatic trading instruction."
    }


def save_strategy_research_to_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    research = research_strategy_goal_v1(payload)

    summary = (
        f"Strategy research {research['research_id']}: goal={research['input']['goal_text']} "
        f"target_pips={research['input']['target_pips_per_day']} symbols={research['selected_symbols']} "
        f"candidates={research['candidate_count']} risk={research['goal_risk_assessment']['label']}. "
        f"Backtest status={research['backtest_status']}. Research support only."
    )

    memory = add_memory_v1({
        "memory_type": "strategy_research",
        "symbol": research["selected_symbols"][0] if research["selected_symbols"] else "MULTI",
        "title": f"Strategy Research {research['research_id']}",
        "content": summary,
        "tags": [VERSION, research["goal_risk_assessment"]["label"]],
        "source": VERSION,
        "metadata": research
    })

    return {
        "version": "strategy_research_memory_save_v1",
        "ok": bool(memory.get("ok")),
        "research": research,
        "memory": memory
    }
