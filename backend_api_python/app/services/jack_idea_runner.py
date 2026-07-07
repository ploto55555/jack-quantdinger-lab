from __future__ import annotations

from typing import Any

from app.services.jack_idea_parser import parse_idea_v1
from app.services.jack_memory_store import add_memory_v1
from app.services.jack_mtf_research import run_mtf_research_v1
from app.services.jack_rule_research_engine import run_rule_research_v1

try:
    from app.services.jack_inverse_research import run_inverse_research_v1
except Exception:  # pragma: no cover
    run_inverse_research_v1 = None


VERSION = "idea_runner_v1"


def run_idea_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text = str(payload.get("text") or payload.get("idea") or "").strip()
    parsed_result = parse_idea_v1({"text": text})
    parsed = parsed_result.get("parsed") or {}
    test_type = parsed.get("test_type")
    query = (parsed_result.get("router_hint") or {}).get("query") or {}

    idea_memory = add_memory_v1({
        "memory_type": "idea",
        "symbol": parsed.get("symbol"),
        "title": f"Idea {parsed.get('symbol')} {parsed.get('profile_type')}",
        "content": text,
        "tags": [parsed.get("profile_type"), test_type],
        "source": "idea_runner_v1",
        "metadata": {"parsed": parsed},
    })

    if test_type == "run_mtf_rule_v1":
        result = run_mtf_research_v1(query)
    elif test_type == "run_inverse_rule_v1":
        if run_inverse_research_v1 is None:
            return {
                "version": VERSION,
                "ok": False,
                "error": "inverse_research_engine_unavailable",
                "parser": parsed_result,
                "idea_memory": idea_memory,
            }
        result = run_inverse_research_v1(query)
    else:
        result = run_rule_research_v1(query)

    decision = _decision_from_result(result)
    result_memory = add_memory_v1({
        "memory_type": "idea_result",
        "symbol": parsed.get("symbol"),
        "title": f"Result {parsed.get('symbol')} {parsed.get('profile_type')}",
        "content": _result_content(text, parsed, result, decision),
        "tags": [parsed.get("profile_type"), test_type, decision.get("status")],
        "source": "idea_runner_v1",
        "metadata": {"parsed": parsed, "result": _compact_result(result), "decision": decision},
    })

    return {
        "version": VERSION,
        "ok": True,
        "parser": parsed_result,
        "result": result,
        "decision": decision,
        "memory": {
            "idea_memory_id": (idea_memory.get("memory") or {}).get("memory_id"),
            "result_memory_id": (result_memory.get("memory") or {}).get("memory_id"),
        },
    }


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "symbol", "timeframe", "total_return_percent", "return_percent",
        "max_drawdown_percent", "max_drop_percent", "number_of_trades",
        "number_of_cases", "win_rate_percent", "profit_factor",
        "positive_negative_ratio", "daily_filter_timing",
    ]
    compact = {k: result.get(k) for k in keys if k in result}
    if "summary" in result and isinstance(result.get("summary"), dict):
        compact["summary"] = result.get("summary")
    return compact


def _num(result: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = result.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    for key in keys:
        value = summary.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _decision_from_result(result: dict[str, Any]) -> dict[str, Any]:
    ret = _num(result, "total_return_percent", "return_percent")
    max_drop = _num(result, "max_drawdown_percent", "max_drop_percent")
    ratio = _num(result, "profit_factor", "positive_negative_ratio")
    count = _num(result, "number_of_trades", "number_of_cases", "sample_count")

    flags: list[str] = []
    if ret is None:
        flags.append("return_unknown")
    elif ret <= 0:
        flags.append("negative_result")
    elif ret < 5:
        flags.append("low_return")

    if max_drop is not None and max_drop < -8:
        flags.append("deep_drop")
    if ratio is not None and ratio < 1.2:
        flags.append("weak_ratio")
    if count is not None and count < 30:
        flags.append("low_sample_count")

    if "negative_result" in flags or "weak_ratio" in flags:
        status = "reject_or_rework"
    elif flags:
        status = "watch_only"
    else:
        status = "research_candidate"

    return {
        "status": status,
        "flags": flags or ["clean_candidate"],
        "return_percent": ret,
        "max_drop_percent": max_drop,
        "ratio": ratio,
        "sample_count": count,
        "next_action": _next_action(status),
    }


def _next_action(status: str) -> str:
    if status == "research_candidate":
        return "Keep in research list and compare with chart review."
    if status == "watch_only":
        return "Do not promote yet. More validation or more data is needed."
    return "Do not use as current profile. Rework idea or skip."


def _result_content(text: str, parsed: dict[str, Any], result: dict[str, Any], decision: dict[str, Any]) -> str:
    c = _compact_result(result)
    return (
        f"Idea: {text}. Parsed as {parsed.get('symbol')} {parsed.get('profile_type')} "
        f"using {parsed.get('test_type')}. Result summary: {c}. "
        f"Decision: {decision.get('status')} flags={decision.get('flags')} next={decision.get('next_action')}"
    )
