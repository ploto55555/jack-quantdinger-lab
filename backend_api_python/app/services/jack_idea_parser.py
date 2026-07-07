from __future__ import annotations

import re
from typing import Any


VERSION = "idea_parser_v1"
SUPPORTED_SYMBOLS = [
    "GBPJPY", "XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "EURJPY", "AUDJPY",
    "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "DXY", "SPY", "QQQ",
]


def parse_idea_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text = str(payload.get("text") or payload.get("idea") or "").strip()
    upper = text.upper()
    symbol = _find_symbol(upper)
    timeframe = _find_timeframe(upper)
    direction = _find_direction(text, upper)
    ema_fast, ema_slow = _find_ema_pair(upper)
    lookback = _find_lookback(upper)
    objective_r = _find_objective_r(upper)
    unit_percent = _find_unit_percent(upper)
    d1_filter = _has_d1_filter(text, upper)

    profile_type = _profile_type(direction, timeframe, d1_filter)
    test_type = _test_type(profile_type)

    parsed = {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "profile_type": profile_type,
        "test_type": test_type,
        "unit_percent": unit_percent,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "range_lookback": lookback,
        "guard_lookback": lookback,
        "objective_r": objective_r,
        "d1_filter": d1_filter,
        "raw_text": text,
    }
    return {
        "version": VERSION,
        "ok": bool(text),
        "parsed": parsed,
        "confidence": _confidence(parsed),
        "missing_fields": _missing_fields(parsed),
        "router_hint": _router_hint(parsed),
    }


def _find_symbol(upper: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", upper)
    for symbol in SUPPORTED_SYMBOLS:
        if symbol in compact:
            return symbol
    return "GBPJPY"


def _find_timeframe(upper: str) -> str:
    for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]:
        if re.search(rf"\b{tf}\b", upper):
            return tf
    if "4H" in upper:
        return "H4"
    if "DAILY" in upper or "日线" in upper or "日綫" in upper:
        return "D1"
    return "H4"


def _find_direction(text: str, upper: str) -> str:
    low_words = ["DOWN", "SHORT", "SELL", "BEAR", "BEARISH", "跌", "空", "下跌", "做空"]
    up_words = ["UP", "LONG", "BUY", "BULL", "BULLISH", "涨", "多", "上涨", "做多", "多头"]
    if any(w in upper or w in text for w in low_words):
        return "down"
    if any(w in upper or w in text for w in up_words):
        return "up"
    return "up"


def _find_ema_pair(upper: str) -> tuple[int, int]:
    m = re.search(r"EMA\s*(\d{1,3})\s*[/,\- ]\s*(\d{1,3})", upper)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)
    nums = [int(x) for x in re.findall(r"EMA\s*(\d{1,3})", upper)]
    if len(nums) >= 2:
        return min(nums[0], nums[1]), max(nums[0], nums[1])
    return 30, 150


def _find_lookback(upper: str) -> int:
    patterns = [r"BREAKOUT\s*(\d{1,3})", r"LOOKBACK\s*(\d{1,3})", r"RANGE\s*(\d{1,3})"]
    for p in patterns:
        m = re.search(p, upper)
        if m:
            return int(m.group(1))
    return 20


def _find_objective_r(upper: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*R", upper)
    if m:
        return float(m.group(1))
    m = re.search(r"TARGET\s*(\d+(?:\.\d+)?)", upper)
    if m:
        return float(m.group(1))
    return 1.5


def _find_unit_percent(upper: str) -> float:
    m = re.search(r"RISK\s*(\d+(?:\.\d+)?)\s*%", upper)
    if m:
        return float(m.group(1))
    return 1.0


def _has_d1_filter(text: str, upper: str) -> bool:
    return "D1" in upper or "DAILY" in upper or "日线" in text or "日綫" in text


def _profile_type(direction: str, timeframe: str, d1_filter: bool) -> str:
    if d1_filter and timeframe == "H4" and direction == "up":
        return "mtf_h4_up_previous_closed_d1"
    if direction == "down":
        return f"{timeframe.lower()}_down"
    return f"{timeframe.lower()}_up"


def _test_type(profile_type: str) -> str:
    if profile_type == "mtf_h4_up_previous_closed_d1":
        return "run_mtf_rule_v1"
    if profile_type.endswith("_down"):
        return "run_inverse_rule_v1"
    return "run_rule_v1"


def _missing_fields(parsed: dict[str, Any]) -> list[str]:
    missing = []
    if not parsed.get("symbol"):
        missing.append("symbol")
    if not parsed.get("timeframe"):
        missing.append("timeframe")
    if not parsed.get("direction"):
        missing.append("direction")
    return missing


def _confidence(parsed: dict[str, Any]) -> float:
    score = 0.55
    if parsed.get("symbol"):
        score += 0.15
    if parsed.get("timeframe"):
        score += 0.1
    if parsed.get("ema_fast") and parsed.get("ema_slow"):
        score += 0.1
    if parsed.get("objective_r"):
        score += 0.1
    return round(min(score, 0.95), 2)


def _router_hint(parsed: dict[str, Any]) -> dict[str, Any]:
    test_type = parsed.get("test_type")
    if test_type == "run_mtf_rule_v1":
        endpoint = "/api/jack-backtest/run-mtf-rule-v1"
        query = {
            "symbol": parsed.get("symbol"),
            "risk_percent": parsed.get("unit_percent"),
            "h4_ema_fast": parsed.get("ema_fast"),
            "h4_ema_slow": parsed.get("ema_slow"),
            "d1_ema_fast": parsed.get("ema_fast"),
            "d1_ema_slow": parsed.get("ema_slow"),
            "breakout_lookback": parsed.get("range_lookback"),
            "stop_lookback": parsed.get("guard_lookback"),
            "target_r": parsed.get("objective_r"),
        }
    elif test_type == "run_inverse_rule_v1":
        endpoint = "/api/jack-backtest/run-inverse-rule-v1"
        query = {
            "symbol": parsed.get("symbol"),
            "timeframe": parsed.get("timeframe"),
            "risk_percent": parsed.get("unit_percent"),
            "ema_fast": parsed.get("ema_fast"),
            "ema_slow": parsed.get("ema_slow"),
            "breakout_lookback": parsed.get("range_lookback"),
            "stop_lookback": parsed.get("guard_lookback"),
            "target_r": parsed.get("objective_r"),
        }
    else:
        endpoint = "/api/jack-backtest/run-rule-v1"
        query = {
            "symbol": parsed.get("symbol"),
            "timeframe": parsed.get("timeframe"),
            "risk_percent": parsed.get("unit_percent"),
            "ema_fast": parsed.get("ema_fast"),
            "ema_slow": parsed.get("ema_slow"),
            "breakout_lookback": parsed.get("range_lookback"),
            "stop_lookback": parsed.get("guard_lookback"),
            "target_r": parsed.get("objective_r"),
        }
    return {"endpoint": endpoint, "query": query}
