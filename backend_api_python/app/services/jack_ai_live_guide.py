from __future__ import annotations

from typing import Any, Dict, List

from app.services.jack_trade_readiness_engine import build_trade_readiness_v2


def _fmt_price(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pips(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.1f} pips"
    except (TypeError, ValueError):
        return str(value)


def _clean_line(text: str) -> str:
    replacements = {
        "Direction input is non-standard; treated as unknown.": "No valid direction yet because M15 has not produced a setup.",
        "H1 trend conditions are mixed.": "H1 trend is mixed, so the system cannot confirm trend direction yet.",
        "D1 and H1 do not agree; M15 setup blocked.": "M15 is blocked because D1 and H1 are not aligned.",
        "M15 has no valid entry direction, so M5 cannot confirm.": "M5 cannot confirm because M15 has no valid setup yet.",
        "H1 regime is range/unclear; SRDC runner should wait.": "H1 is unclear/range, so SRDC runner should wait.",
        "Market quality is not suitable for SRDC runner.": "Market quality is not clean enough for SRDC runner.",
        "Goal planner does not allow setup selection.": "Goal planner blocks trading because market quality is unclear.",
    }
    return replacements.get(text, text)


def _unique_clean(items: List[str]) -> List[str]:
    result: List[str] = []
    for item in items or []:
        clean = _clean_line(str(item))
        if clean and clean not in result:
            result.append(clean)
    return result


def _stage_tone(stage: str) -> str:
    if stage == "READY":
        return "READY — setup is close enough to prepare a manual trade plan."
    if stage == "PREPARE":
        return "PREPARE — setup is near trigger, but final confirmation is still required."
    if stage == "WATCH":
        return "WATCH — conditions are improving, but not ready yet."
    if stage == "NO_TRADE":
        return "NO TRADE — do not force a trade."
    if stage == "DEFENSE":
        return "DEFENSE — protect account first, no new trade."
    return "WAIT — no clean setup yet."


def _build_plain_english(readiness: Dict[str, Any]) -> Dict[str, Any]:
    stage = readiness.get("readiness_stage", "WAIT")
    command = readiness.get("final_command", "WAIT")
    summary = readiness.get("four_timeframe_summary", {}) or {}
    entry = readiness.get("entry_context", {}) or {}
    blockers = _unique_clean(readiness.get("blockers", []) or [])
    reasons = _unique_clean(readiness.get("reasons", []) or [])

    d1 = summary.get("D1", "unknown")
    h1 = summary.get("H1", "unknown")
    m15 = summary.get("M15", "unknown")
    m5 = summary.get("M5", "unknown")

    headline = _stage_tone(stage)
    if command:
        headline = f"{headline} Current command: {command}."

    current_read = (
        f"D1 is {d1}, H1 is {h1}, M15 is {m15}, and M5 is {m5}. "
        f"The system score is {readiness.get('readiness_score', '—')}."
    )

    why_now = []
    if d1 == "long_only" and h1 in {"unclear", "range"}:
        why_now.append("Daily bias is bullish, but H1 is not clean enough to confirm trend. This blocks the trade.")
    elif d1 == "short_only" and h1 in {"unclear", "range"}:
        why_now.append("Daily bias is bearish, but H1 is not clean enough to confirm trend. This blocks the trade.")
    elif h1 == "trend" and m15 == "wait":
        why_now.append("Higher timeframe is acceptable, but M15 has not reached a valid SRDC trigger area yet.")
    elif m15 in {"setup_forming", "triggered"} and m5 == "wait":
        why_now.append("M15 is getting closer, but M5 has not confirmed yet.")

    if not why_now and blockers:
        why_now.append(blockers[0])
    if not why_now:
        why_now.append(readiness.get("reason", "Conditions are not aligned enough yet."))

    next_watch = []
    y_high = entry.get("yesterday_high")
    y_low = entry.get("yesterday_low")
    entry_price = entry.get("entry_price")
    distance = entry.get("distance_to_entry_pips")

    if d1 == "long_only":
        if y_high is not None:
            next_watch.append(f"For a long setup, watch yesterday high area around {_fmt_price(y_high)} plus the SRDC buffer.")
        next_watch.append("H1 needs to turn from unclear into trend-long before M15/M5 can matter.")
    elif d1 == "short_only":
        if y_low is not None:
            next_watch.append(f"For a short setup, watch yesterday low area around {_fmt_price(y_low)} minus the SRDC buffer.")
        next_watch.append("H1 needs to turn from unclear into trend-short before M15/M5 can matter.")
    else:
        next_watch.append("Wait for D1 to give a clearer direction first.")

    if entry_price is not None:
        next_watch.append(f"Current trigger area is {_fmt_price(entry_price)}; distance is {_fmt_pips(distance)}.")
    else:
        next_watch.append("No valid entry price yet because H1/M15 are not aligned.")

    conditions_to_upgrade = [
        "D1 remains directional and not neutral.",
        "H1 changes from unclear/range into a clean trend in the same direction as D1.",
        "M15 moves near or through the SRDC trigger instead of staying in wait mode.",
        "M5 changes from wait into prepare or confirm.",
        "News risk remains low and account mode does not enter defense.",
    ]

    do_now = []
    if stage in {"NO_TRADE", "WAIT"}:
        do_now = [
            "Do not open a new trade now.",
            "Keep watching H1 first; it is the main blocker.",
            "Only check M15/M5 after H1 becomes clean.",
        ]
    elif stage == "WATCH":
        do_now = [
            "Watch only. Do not pre-click or chase.",
            "Prepare levels mentally, but wait for M15/M5 improvement.",
        ]
    elif stage == "PREPARE":
        do_now = [
            "Prepare the trade plan, risk, SL, TP, and invalidation.",
            "Still require final manual chart confirmation before any execution.",
        ]
    elif stage == "READY":
        do_now = [
            "Generate a trade plan next.",
            "Manually confirm chart, spread, and news before any execution.",
        ]
    elif stage == "DEFENSE":
        do_now = [
            "No new trades.",
            "Review drawdown, loss streak, and rule discipline first.",
        ]

    return {
        "headline": headline,
        "current_read": current_read,
        "why_now": why_now,
        "next_watch": next_watch,
        "conditions_to_upgrade": conditions_to_upgrade,
        "do_now": do_now,
        "clean_blockers": blockers,
        "clean_reasons": reasons,
    }


def build_ai_live_guide_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()
    readiness = build_trade_readiness_v2(payload | {"symbol": symbol})
    guide = _build_plain_english(readiness)

    return {
        "version": "ai_live_guide_v1",
        "ok": readiness.get("ok", False),
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "final_command": readiness.get("final_command"),
        "readiness_stage": readiness.get("readiness_stage"),
        "readiness_score": readiness.get("readiness_score"),
        "guide": guide,
        "readiness": readiness,
        "note": "This guide is rule-based AI support for manual review only. It is not financial advice and it does not place trades.",
    }
