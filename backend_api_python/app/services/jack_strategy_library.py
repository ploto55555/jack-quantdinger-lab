from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


APP_ROOT = Path(__file__).resolve().parents[1]
STRATEGY_LIBRARY_PATH = APP_ROOT / "knowledge" / "strategies" / "srdc_strategy_candidates_v1.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_strategy_library_v1() -> Dict[str, Any]:
    """Load the personal strategy candidate library.

    This library stores research candidates only. It must not be used as an
    auto-trading instruction source without a separate execution approval layer.
    """
    if not STRATEGY_LIBRARY_PATH.exists():
        return {
            "version": "srdc_strategy_candidates_v1",
            "ok": False,
            "error": "strategy_library_file_not_found",
            "path": str(STRATEGY_LIBRARY_PATH),
            "candidates": [],
        }

    try:
        data = json.loads(STRATEGY_LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive for malformed local data
        return {
            "version": "srdc_strategy_candidates_v1",
            "ok": False,
            "error": "strategy_library_file_read_failed",
            "message": str(exc),
            "candidates": [],
        }

    data["ok"] = True
    data["candidate_count"] = len(data.get("candidates", []))
    return data


def list_strategy_candidates_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    library = load_strategy_library_v1()
    candidates: List[Dict[str, Any]] = list(library.get("candidates", []))

    role_filter = str(payload.get("role", "")).strip()
    mode_filter = str(payload.get("mode", "")).strip()
    symbol_filter = str(payload.get("symbol", "")).strip().upper()
    limit = _safe_int(payload.get("limit", len(candidates) or 50), len(candidates) or 50)

    if role_filter:
        candidates = [c for c in candidates if c.get("role") == role_filter]

    if mode_filter:
        candidates = [c for c in candidates if c.get("goal_use", {}).get("mode") == mode_filter]

    if symbol_filter:
        candidates = [c for c in candidates if str(c.get("pair", "")).upper() == symbol_filter]

    candidates = sorted(candidates, key=lambda c: c.get("rank", 999))[:limit]

    return {
        "version": "strategy_library_list_v1",
        "ok": library.get("ok", False),
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def get_strategy_candidate_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    strategy_id = str(payload.get("strategy_id", "")).strip()
    library = load_strategy_library_v1()

    for candidate in library.get("candidates", []):
        if candidate.get("id") == strategy_id:
            return {
                "version": "strategy_candidate_detail_v1",
                "ok": True,
                "mode": "personal_research_support_only",
                "broker_connection": False,
                "auto_trading": False,
                "candidate": candidate,
            }

    return {
        "version": "strategy_candidate_detail_v1",
        "ok": False,
        "error": "strategy_candidate_not_found",
        "strategy_id": strategy_id,
    }


def choose_strategy_for_goal_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Choose a candidate for the current capital/discipline state.

    This is a simple rules-first selector for Step 37. Step 38 will add a full
    goal-path planner. For now, it maps account state to A+/Main/Attack/Wait.
    """
    payload = payload or {}
    equity = _safe_float(payload.get("equity", 500), 500)
    peak_equity = max(_safe_float(payload.get("peak_equity", equity), equity), equity)
    target_equity = _safe_float(payload.get("target_equity", 100000), 100000)
    consecutive_losses = _safe_int(payload.get("consecutive_losses", 0), 0)
    news_risk = str(payload.get("news_risk", "unknown")).strip().lower()
    market_quality = str(payload.get("market_quality", "normal")).strip().lower()

    drawdown_percent = 0.0
    if peak_equity > 0:
        drawdown_percent = round(((equity - peak_equity) / peak_equity) * 100, 2)

    selected_mode = "main"
    command = "MAIN_RESEARCH"
    reason = "Account state is healthy enough for the main forward-test candidate."
    strategy_id = "SRDC_GBPJPY_KETTY_H1_TREND_MOD_RUNNER_V1"

    if news_risk in {"high", "very_high"}:
        selected_mode = "no_trade"
        command = "WAIT"
        reason = "High news risk blocks new trades."
        strategy_id = None
    elif drawdown_percent <= -15:
        selected_mode = "no_trade"
        command = "DEFENSE_PAUSE"
        reason = "Drawdown is beyond -15%; pause and review."
        strategy_id = None
    elif drawdown_percent <= -10 or consecutive_losses >= 2:
        selected_mode = "a_plus_safe"
        command = "A_PLUS_ONLY"
        reason = "Drawdown or loss streak requires strict A+ mode only."
        strategy_id = "SRDC_GBPJPY_KETTY_H1_STRICT_RUNNER_V1"
    elif equity >= target_equity * 0.5:
        selected_mode = "a_plus_safe"
        command = "PROTECT_GAINS"
        reason = "Equity is past 50% of the target; protect progress with A+ mode."
        strategy_id = "SRDC_GBPJPY_KETTY_H1_STRICT_RUNNER_V1"
    elif market_quality in {"very_strong", "a_plus"} and drawdown_percent >= -3 and consecutive_losses == 0:
        selected_mode = "main_or_attack_research"
        command = "MAIN_WITH_ATTACK_RESEARCH_OPTION"
        reason = "Market quality is strong and account state is healthy; main mode is allowed, attack remains research-only."
        strategy_id = "SRDC_GBPJPY_KETTY_H1_TREND_MOD_RUNNER_V1"
    elif market_quality in {"unclear", "range", "messy"}:
        selected_mode = "no_trade"
        command = "WAIT"
        reason = "Market quality is unclear/range; block SRDC runner setup."
        strategy_id = None

    candidate_detail = None
    if strategy_id:
        detail = get_strategy_candidate_v1({"strategy_id": strategy_id})
        candidate_detail = detail.get("candidate") if detail.get("ok") else None

    return {
        "version": "strategy_selector_v1",
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "inputs": {
            "equity": equity,
            "peak_equity": peak_equity,
            "target_equity": target_equity,
            "consecutive_losses": consecutive_losses,
            "news_risk": news_risk,
            "market_quality": market_quality,
        },
        "account_state": {
            "drawdown_percent": drawdown_percent,
            "target_progress_percent": round((equity / target_equity) * 100, 2) if target_equity else 0,
        },
        "selection": {
            "selected_mode": selected_mode,
            "command": command,
            "strategy_id": strategy_id,
            "reason": reason,
        },
        "candidate": candidate_detail,
    }
