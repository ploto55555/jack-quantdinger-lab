from __future__ import annotations

from typing import Any


VERSION = "research_profiles_v1"


ITEMS: list[dict[str, Any]] = [
    {
        "symbol": "GBPJPY",
        "profile_id": "GBPJPY_H4_UP_V1",
        "status": "active_candidate",
        "profile_type": "h4_up",
        "note": "Best current simple H4 upward profile. Higher timeframe filter was not helpful in the latest comparison.",
        "settings": {"timeframe": "H4", "unit_percent": 1, "ema_fast": 30, "ema_slow": 150, "range_lookback": 20, "guard_lookback": 20, "objective_r": 1.5},
        "result": {"return_percent": 10.3764, "max_drop_percent": -3.9405, "sample_count": 55, "win_rate_percent": 47.27, "positive_negative_ratio": 1.342, "source_step": "step_9"},
    },
    {
        "symbol": "XAUUSD",
        "profile_id": "XAUUSD_H4_UP_V1",
        "status": "active_candidate",
        "profile_type": "h4_up",
        "note": "Simple H4 upward profile stayed positive. Higher timeframe filter reduced the result.",
        "settings": {"timeframe": "H4", "unit_percent": 1, "ema_fast": 30, "ema_slow": 150, "range_lookback": 20, "guard_lookback": 20, "objective_r": 1.5},
        "result": {"return_percent": 8.9993, "max_drop_percent": -6.8283, "sample_count": 67, "win_rate_percent": 46.27, "positive_negative_ratio": 1.237, "source_step": "step_9"},
    },
    {
        "symbol": "GBPUSD",
        "profile_id": "GBPUSD_H4_DOWN_V1",
        "status": "active_candidate",
        "profile_type": "h4_down",
        "note": "Downward H4 profile was stronger than upward-only for this symbol in the current research set.",
        "settings": {"timeframe": "H4", "unit_percent": 1, "ema_fast": 30, "ema_slow": 150, "range_lookback": 20, "guard_lookback": 20, "objective_r": 1.5},
        "result": {"return_percent": 4.8395, "max_drop_percent": -7.2781, "sample_count": 35, "win_rate_percent": 45.71, "positive_negative_ratio": 1.248, "source_step": "step_12"},
    },
    {
        "symbol": "EURUSD",
        "profile_id": "EURUSD_MTF_UP_V1",
        "status": "active_candidate",
        "profile_type": "mtf_h4_up_previous_closed_d1",
        "note": "Previous-closed-D1 filter improved this symbol versus H4-only in the latest comparison.",
        "settings": {"unit_percent": 1, "h4_ema_fast": 30, "h4_ema_slow": 150, "d1_ema_fast": 30, "d1_ema_slow": 150, "range_lookback": 20, "guard_lookback": 20, "objective_r": 1.5},
        "result": {"return_percent": 5.4666, "max_drop_percent": -4.9009, "sample_count": 22, "win_rate_percent": 50.0, "positive_negative_ratio": 1.49, "filter_timing": "previous_closed_d1", "source_step": "step_11_1"},
    },
    {
        "symbol": "USDJPY",
        "profile_id": "USDJPY_SKIP_V1",
        "status": "rejected_for_now",
        "profile_type": "none",
        "note": "Current upward, multi-timeframe, and downward research versions were weak or negative.",
        "settings": {},
        "result": {"h4_up_return_percent": 2.5412, "mtf_return_percent": -5.7132, "h4_down_return_percent": -12.51, "source_step": "steps_9_11_12"},
    },
]


def get_research_profiles_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "").upper().strip()
    status = str(payload.get("status") or "").strip()
    rows = ITEMS
    if symbol:
        rows = [x for x in rows if x.get("symbol") == symbol]
    if status:
        rows = [x for x in rows if x.get("status") == status]
    return {
        "version": VERSION,
        "summary": {
            "total": len(rows),
            "active_candidates": len([x for x in rows if x.get("status") == "active_candidate"]),
            "rejected_for_now": len([x for x in rows if x.get("status") == "rejected_for_now"]),
            "purpose": "Keep one current research profile per symbol instead of treating all symbols the same.",
        },
        "profiles": rows,
    }
