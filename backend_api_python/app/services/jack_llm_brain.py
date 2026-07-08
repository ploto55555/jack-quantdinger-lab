import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_brain_context(
    symbol: str = "GBPJPY",
    profile_id: str = "GBPJPY_H4_UP_V1",
    setup_quality: str = "A+",
    equity: float = 500,
    peak_equity: float = 500,
    target_equity: float = 1000000,
    user_question: str = "",
) -> Dict[str, Any]:
    required_multiple = round(target_equity / equity, 2) if equity else None

    return {
        "system": "Jack QuantDinger Lab / Jack Personal AI Capital OS",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "created_at": _now_iso(),
        "input": {
            "symbol": symbol,
            "profile_id": profile_id,
            "setup_quality": setup_quality,
            "equity": equity,
            "peak_equity": peak_equity,
            "target_equity": target_equity,
            "required_multiple": required_multiple,
            "user_question": user_question,
        },
        "backend_brain_modules": {
            "backtest_engine": "available",
            "goal_based_backtest_engine": "available",
            "research_dashboard_api": "available",
            "mem0_memory_layer": "planned_or_available",
            "chroma_vector_memory": "planned_or_available",
            "journal_decision_trace": "planned_or_available",
            "snowball_learning": "planned_or_available",
        },
        "brain_rules": [
            "Personal research support only.",
            "No broker connection.",
            "No auto trading.",
            "Do not provide trade execution instructions.",
            "Explain backtest, risk, memory, journal, and next research step.",
            "Use simple beginner-friendly language.",
        ],
    }


def fallback_brain_explanation(context: Dict[str, Any]) -> Dict[str, Any]:
    user_input = context.get("input", {})
    equity = user_input.get("equity")
    target_equity = user_input.get("target_equity")
    required_multiple = user_input.get("required_multiple")
    profile_id = user_input.get("profile_id")
    setup_quality = user_input.get("setup_quality")

    summary = (
        f"Backend Brain fallback is active. "
        f"Profile {profile_id} with setup quality {setup_quality} is being reviewed. "
        f"Current equity is {equity}, target equity is {target_equity}, "
        f"required multiple is {required_multiple}x. "
        f"Next step is to connect real backtest result, goal result, memory context, "
        f"and journal trace into this brain layer."
    )

    return {
        "llm_enabled": False,
        "provider": "fallback_local",
        "command": "NORMAL_REVIEW",
        "risk_mode": "RESEARCH_ONLY",
        "summary": summary,
        "memory_used": False,
        "journal_ready": True,
        "next_action": "Connect backend backtest result + memory + journal before frontend UI.",
        "context": context,
    }


def call_openai_responses_api(prompt: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key:
        return None

    payload = {
        "model": model,
        "input": prompt,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))

        if isinstance(data, dict):
            if data.get("output_text"):
                return data["output_text"]

            output = data.get("output", [])
            texts = []
            for item in output:
                for content in item.get("content", []):
                    if content.get("type") in ("output_text", "text"):
                        texts.append(content.get("text", ""))
            if texts:
                return "\n".join(texts)

        return json.dumps(data, ensure_ascii=False, indent=2)

    except Exception as exc:
        return f"LLM API error: {exc}"


def explain_backend_brain(context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
You are the backend brain of Jack QuantDinger Lab.

This system is personal research support only.
No broker connection.
No auto trading.
Do not tell the user to buy or sell.
Explain results in simple beginner language.

Backend context:
{json.dumps(context, ensure_ascii=False, indent=2)}

Return:
1. short summary
2. risk meaning
3. memory meaning
4. journal draft
5. next research action
"""

    llm_text = call_openai_responses_api(prompt)

    if not llm_text:
        return fallback_brain_explanation(context)

    return {
        "llm_enabled": True,
        "provider": "openai_responses_api",
        "command": "NORMAL_REVIEW",
        "risk_mode": "RESEARCH_ONLY",
        "summary": llm_text,
        "memory_used": "pending_backend_memory_connection",
        "journal_ready": True,
        "next_action": "Connect this brain result to frontend chat panel.",
        "context": context,
    }


def create_decision_journal_draft(
    context: Dict[str, Any],
    brain_result: Dict[str, Any],
) -> Dict[str, Any]:
    user_input = context.get("input", {})
    decision_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-"
        f"{user_input.get('symbol', 'UNKNOWN')}-"
        f"{user_input.get('profile_id', 'PROFILE')}"
    )

    return {
        "decision_id": decision_id,
        "created_at": _now_iso(),
        "type": "backend_brain_decision_journal_v1",
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "inputs": user_input,
        "brain_command": brain_result.get("command"),
        "risk_mode": brain_result.get("risk_mode"),
        "memory_used": brain_result.get("memory_used"),
        "summary": brain_result.get("summary"),
        "next_action": brain_result.get("next_action"),
        "save_status": "draft_only_not_persisted_yet",
    }
