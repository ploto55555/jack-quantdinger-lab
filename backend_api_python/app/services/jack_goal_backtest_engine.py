from __future__ import annotations

import math
from typing import Any

from app.services.jack_memory_store import add_memory_v1
from app.services.jack_profile_promotion import build_profile_promotion_v1
from app.services.jack_research_profiles import get_research_profiles_v1
from app.services.jack_validation_engine import validate_top_candidates_v1


VERSION = "goal_backtest_engine_v1"

GOAL_STAGES = [
    {"stage": "STAGE_1_500_TO_2K", "start": 500.0, "target": 2000.0, "stage_label": "500_to_2k"},
    {"stage": "STAGE_2_2K_TO_10K", "start": 2000.0, "target": 10000.0, "stage_label": "2k_to_10k"},
    {"stage": "STAGE_3_10K_TO_100K", "start": 10000.0, "target": 100000.0, "stage_label": "10k_to_100k"},
    {"stage": "STAGE_4_100K_TO_1M", "start": 100000.0, "target": 1000000.0, "stage_label": "100k_to_1m"},
]

RISK_BY_STAGE = {
    "STAGE_1_500_TO_2K": {"normal": 0.03, "strong": 0.04, "max": 0.05},
    "STAGE_2_2K_TO_10K": {"normal": 0.03, "strong": 0.04, "max": 0.05},
    "STAGE_3_10K_TO_100K": {"normal": 0.015, "strong": 0.03, "max": 0.04},
    "STAGE_4_100K_TO_1M": {"normal": 0.01, "strong": 0.02, "max": 0.03},
}


def run_goal_backtest_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    start_equity = _to_float(payload.get("start_equity"), 500.0)
    target_equity = _to_float(payload.get("target_equity"), 1000000.0)
    save = _bool(payload.get("save_memory"), True)

    profiles = get_research_profiles_v1({}).get("profiles") or []
    promotion = build_profile_promotion_v1({"save_memory": False})
    validation = validate_top_candidates_v1({"save_memory": False})

    promo_by_id = {p.get("profile_id"): p for p in (promotion.get("summary") or {}).get("promotions") or []}
    validation_by_symbol = _validation_by_symbol(validation)

    rows = []
    for profile in profiles:
        profile_id = str(profile.get("profile_id") or "")
        stats = profile.get("result") or {}
        promo = promo_by_id.get(profile_id, {})
        validation_row = validation_by_symbol.get(str(profile.get("symbol") or ""), {})
        rows.append(_score_profile(profile, stats, promo, validation_row, start_equity, target_equity))

    rows = sorted(rows, key=lambda x: x.get("goal_fit_score", 0), reverse=True)
    stage_map = _best_by_stage(rows)

    report = {
        "version": VERSION,
        "ok": True,
        "start_equity": start_equity,
        "target_equity": target_equity,
        "summary": {
            "best_profile_id": rows[0].get("profile_id") if rows else None,
            "best_goal_fit_score": rows[0].get("goal_fit_score") if rows else None,
            "stage_recommendations": stage_map,
            "human_summary": "",
        },
        "ranked_profiles": rows,
        "capital_path": GOAL_STAGES,
        "notes": [
            "Goal backtest compares existing research profiles against the capital path.",
            "It is not a guarantee and does not create live instructions.",
            "Journal data is still small, so confidence should remain conservative.",
        ],
    }
    report["summary"]["human_summary"] = _human_summary(report)

    if save:
        saved = add_memory_v1({
            "memory_type": "goal_backtest_report",
            "symbol": "MULTI",
            "title": "Goal Backtest 500 to 1M",
            "content": report["summary"]["human_summary"],
            "tags": [VERSION, "goal_path", "capital_path", "research_only"],
            "source": VERSION,
            "metadata": report,
        })
        report["memory_id"] = (saved.get("memory") or {}).get("memory_id")

    return report


def _score_profile(profile: dict[str, Any], stats: dict[str, Any], promo: dict[str, Any], validation: dict[str, Any], start_equity: float, target_equity: float) -> dict[str, Any]:
    profile_id = str(profile.get("profile_id") or "")
    symbol = str(profile.get("symbol") or "")
    status = str(promo.get("promoted_status") or profile.get("status") or "unknown")
    total_return = _to_float(stats.get("total_return_percent"), _to_float(stats.get("return_percent"), 0.0))
    max_drop = _to_float(stats.get("max_drawdown_percent"), _to_float(stats.get("max_drop_percent"), 0.0))
    sample_count = _to_float(stats.get("sample_count"), _to_float(stats.get("trades"), 0.0))
    ratio = _to_float(stats.get("profit_factor"), _to_float(stats.get("ratio"), 1.0))
    validation_grade = str(validation.get("grade") or "not_checked")
    positive_periods = _to_float((validation.get("summary") or {}).get("positive_periods"), 0.0)

    stage_results = []
    for stage in GOAL_STAGES:
        stage_results.append(_stage_fit(stage, status, total_return, max_drop, sample_count, ratio, validation_grade, positive_periods))

    score = _goal_fit_score(status, total_return, max_drop, sample_count, ratio, validation_grade, positive_periods, stage_results)
    best_stage = sorted(stage_results, key=lambda x: x.get("stage_fit_score", 0), reverse=True)[0] if stage_results else {}
    worst_stage = sorted(stage_results, key=lambda x: x.get("stage_fit_score", 0))[0] if stage_results else {}

    return {
        "profile_id": profile_id,
        "symbol": symbol,
        "profile_status": status,
        "validation_grade": validation_grade,
        "positive_periods": positive_periods,
        "backtest_stats": {
            "total_return_percent": round(total_return, 4),
            "max_drop_percent": round(max_drop, 4),
            "sample_count": sample_count,
            "ratio": round(ratio, 4),
        },
        "goal_fit_score": score,
        "target_possible": _target_possible(score),
        "best_stage": best_stage.get("stage"),
        "worst_stage": worst_stage.get("stage"),
        "stage_results": stage_results,
        "recommended_use": _recommended_use(score, status, validation_grade),
        "warnings": _warnings(status, total_return, max_drop, sample_count, ratio, validation_grade),
    }


def _stage_fit(stage: dict[str, Any], status: str, total_return: float, max_drop: float, sample_count: float, ratio: float, validation_grade: str, positive_periods: float) -> dict[str, Any]:
    stage_id = str(stage.get("stage"))
    start = _to_float(stage.get("start"), 0.0)
    target = _to_float(stage.get("target"), start)
    multiple = target / start if start > 0 else 1.0
    risk = RISK_BY_STAGE.get(stage_id, {}).get("normal", 0.01)

    estimated_edge_r = max(0.05, min(1.2, (total_return / 100.0) * 4.0 + (ratio - 1.0) * 1.2))
    required_net_r = math.log(multiple) / math.log(1.0 + risk) if risk > 0 else None
    estimated_steps = math.ceil(required_net_r / estimated_edge_r) if required_net_r and estimated_edge_r > 0 else None

    score = 50.0
    score += min(20.0, max(0.0, total_return * 1.2))
    score += min(15.0, max(0.0, (ratio - 1.0) * 40.0))
    score += min(10.0, sample_count / 8.0)
    if validation_grade == "validated_candidate":
        score += 12.0
    if positive_periods >= 3:
        score += 8.0
    if status in ["validated_candidate", "active_core_candidate"]:
        score += 8.0
    elif status == "watch_only":
        score -= 10.0
    elif status in ["rejected_for_now", "avoid", "retired"]:
        score -= 35.0
    if max_drop <= -10:
        score -= 15.0
    elif max_drop <= -7:
        score -= 8.0
    if sample_count < 20:
        score -= 10.0
    if stage_id in ["STAGE_3_10K_TO_100K", "STAGE_4_100K_TO_1M"] and status != "active_core_candidate":
        score -= 8.0

    score = round(max(0.0, min(100.0, score)), 2)

    return {
        "stage": stage_id,
        "start": start,
        "target": target,
        "required_multiple": round(multiple, 3),
        "normal_risk_percent": round(risk * 100, 3),
        "required_net_r_units": round(required_net_r, 2) if required_net_r else None,
        "estimated_edge_r_per_event": round(estimated_edge_r, 3),
        "estimated_event_count": estimated_steps,
        "stage_fit_score": score,
        "stage_use": _stage_use(score),
    }


def _goal_fit_score(status: str, total_return: float, max_drop: float, sample_count: float, ratio: float, validation_grade: str, positive_periods: float, stage_results: list[dict[str, Any]]) -> float:
    if not stage_results:
        return 0.0
    avg_stage = sum(_to_float(x.get("stage_fit_score"), 0.0) for x in stage_results) / len(stage_results)
    score = avg_stage
    if status in ["validated_candidate", "active_core_candidate"]:
        score += 6
    if validation_grade == "validated_candidate":
        score += 6
    if sample_count >= 50:
        score += 5
    if max_drop <= -10:
        score -= 8
    if ratio < 1.1:
        score -= 8
    return round(max(0.0, min(100.0, score)), 2)


def _best_by_stage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for stage in GOAL_STAGES:
        stage_id = str(stage.get("stage"))
        candidates = []
        for row in rows:
            for sr in row.get("stage_results") or []:
                if sr.get("stage") == stage_id:
                    candidates.append({
                        "profile_id": row.get("profile_id"),
                        "symbol": row.get("symbol"),
                        "profile_status": row.get("profile_status"),
                        "stage_fit_score": sr.get("stage_fit_score"),
                        "estimated_event_count": sr.get("estimated_event_count"),
                        "stage_use": sr.get("stage_use"),
                    })
        candidates = sorted(candidates, key=lambda x: x.get("stage_fit_score") or 0, reverse=True)
        out[stage_id] = candidates[:3]
    return out


def _validation_by_symbol(validation: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in validation.get("ranked") or []:
        symbol = str(row.get("symbol") or "")
        if symbol:
            out[symbol] = row
    return out


def _target_possible(score: float) -> str:
    if score >= 75:
        return "strong_research_candidate"
    if score >= 60:
        return "possible_but_needs_more_validation"
    if score >= 45:
        return "weak_or_stage_limited"
    return "not_suitable_now"


def _stage_use(score: float) -> str:
    if score >= 75:
        return "main_candidate_for_stage_research"
    if score >= 60:
        return "secondary_candidate"
    if score >= 45:
        return "watch_only"
    return "not_priority"


def _recommended_use(score: float, status: str, validation_grade: str) -> str:
    if status in ["rejected_for_now", "avoid", "retired"]:
        return "do_not_use_for_goal_path"
    if score >= 75 and validation_grade == "validated_candidate":
        return "primary_goal_path_research_candidate"
    if score >= 60:
        return "secondary_goal_path_candidate_needs_journal_confirmation"
    if score >= 45:
        return "watch_only_more_data_needed"
    return "not_suitable_for_goal_path_now"


def _warnings(status: str, total_return: float, max_drop: float, sample_count: float, ratio: float, validation_grade: str) -> list[str]:
    warnings = []
    if sample_count < 50:
        warnings.append("sample_count_not_enough_for_strong_confidence")
    if validation_grade != "validated_candidate":
        warnings.append("not_fully_validated_across_periods")
    if status == "watch_only":
        warnings.append("profile_is_watch_only")
    if status in ["rejected_for_now", "avoid", "retired"]:
        warnings.append("profile_not_allowed_for_goal_path")
    if max_drop <= -10:
        warnings.append("drawdown_too_deep_for_compounding_path")
    if ratio < 1.15:
        warnings.append("edge_ratio_too_weak")
    if total_return <= 0:
        warnings.append("historical_result_not_positive")
    return warnings


def _human_summary(report: dict[str, Any]) -> str:
    ranked = report.get("ranked_profiles") or []
    if not ranked:
        return "Goal backtest completed but no profiles were available."
    best = ranked[0]
    return (
        f"Goal backtest completed. Best profile={best.get('profile_id')} score={best.get('goal_fit_score')} "
        f"target_possible={best.get('target_possible')} recommended_use={best.get('recommended_use')}. "
        f"Best stage={best.get('best_stage')}. This is research support only, not a guarantee."
    )


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "y", "on"]
    return default
