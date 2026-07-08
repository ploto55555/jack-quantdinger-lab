from __future__ import annotations

from typing import Any


VERSION = "idea_generator_v1"

CORE_SYMBOLS = ["GBPJPY", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
EMA_SETS = [(20, 100), (30, 150), (50, 200)]
OBJECTIVES = [1.5, 2.0, 3.0]


def generate_ideas_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbols = _symbols(payload.get("symbols"))
    max_items = max(1, min(_to_int(payload.get("limit"), 30), 120))
    include_mtf = _bool(payload.get("include_mtf"), True)
    include_lower_profile = _bool(payload.get("include_lower_profile"), True)

    ideas: list[dict[str, Any]] = []

    for symbol in symbols:
        for ema_fast, ema_slow in EMA_SETS:
            for objective in OBJECTIVES:
                ideas.append(_idea(symbol, "H4", "bullish", ema_fast, ema_slow, objective, False))

                if include_mtf:
                    ideas.append(_idea(symbol, "H4", "bullish", ema_fast, ema_slow, objective, True))

                if include_lower_profile and symbol in ["GBPUSD", "EURUSD", "USDJPY"]:
                    ideas.append(_idea(symbol, "H4", "bearish", ema_fast, ema_slow, objective, False))

    ideas = ideas[:max_items]

    return {
        "version": VERSION,
        "ok": True,
        "total_generated": len(ideas),
        "symbols": symbols,
        "ideas": ideas,
        "idea_texts": [item["text"] for item in ideas],
        "next_step": "Send idea_texts to /api/jack-backtest/run-multi-idea-test-v1 for batch testing.",
    }


def _idea(symbol: str, timeframe: str, direction_word: str, ema_fast: int, ema_slow: int, objective: float, mtf: bool) -> dict[str, Any]:
    if mtf:
        text = f"{symbol} D1 bullish {timeframe} breakout EMA{ema_fast}/{ema_slow} target {objective:g}R risk 1%"
        profile_type = "mtf_h4_up_previous_closed_d1"
        direction = "up"
    else:
        text = f"{symbol} {timeframe} {direction_word} breakout EMA{ema_fast}/{ema_slow} target {objective:g}R risk 1%"
        direction = "down" if direction_word == "bearish" else "up"
        profile_type = f"{timeframe.lower()}_{direction}"

    return {
        "text": text,
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "profile_type": profile_type,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "objective_r": objective,
        "d1_filter": mtf,
    }


def _symbols(value: Any) -> list[str]:
    allowed = CORE_SYMBOLS

    if isinstance(value, str) and value.strip():
        value = [value]

    if isinstance(value, list) and value:
        output = []
        for item in value:
            text = str(item).strip().upper()
            if text in allowed and text not in output:
                output.append(text)
        return output or allowed

    return allowed


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "y", "on"]

    return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
