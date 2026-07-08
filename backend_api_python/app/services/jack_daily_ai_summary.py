from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.jack_memory_store import list_memory_v1

VERSION = "daily_ai_summary_v1"


def _today_prefix() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _pick_today(items: List[Dict[str, Any]], day_prefix: str) -> List[Dict[str, Any]]:
    return [x for x in items if str(x.get("created_at", "")).startswith(day_prefix)]


def _counter(items: List[Dict[str, Any]], key: str) -> Counter:
    c: Counter = Counter()
    for item in items:
        value = item.get("metadata", {}).get(key)
        if value is not None:
            c[str(value)] += 1
    return c


def _collect_text_counts(items: List[Dict[str, Any]], metadata_key: str) -> Counter:
    c: Counter = Counter()
    for item in items:
        for text in _as_list(item.get("metadata", {}).get(metadata_key)):
            clean = str(text).strip()
            if clean:
                c[clean] += 1
    return c


def _collect_tf(items: List[Dict[str, Any]]) -> Dict[str, Counter]:
    result = {"D1": Counter(), "H1": Counter(), "M15": Counter(), "M5": Counter()}
    for item in items:
        summary = item.get("metadata", {}).get("summary", {}) or {}
        for tf in result:
            value = summary.get(tf)
            if value is not None:
                result[tf][str(value)] += 1
    return result


def build_daily_ai_summary_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol", "GBPJPY")).upper()
    day = str(payload.get("date") or _today_prefix())
    limit = int(payload.get("limit") or 500)

    memory = list_memory_v1({
        "symbol": symbol,
        "memory_type": "dashboard_auto_snapshot",
        "limit": limit,
    })
    items = _pick_today(memory.get("items", []), day)

    command_counts = Counter(str(x.get("tags", [None, None])[1]) for x in items if len(x.get("tags", [])) > 1)
    stage_counts = Counter(str(x.get("tags", [None, None, None])[2]) for x in items if len(x.get("tags", [])) > 2)
    score_counts = _counter(items, "score")
    blocker_counts = _collect_text_counts(items, "blockers")
    reason_counts = _collect_text_counts(items, "reasons")
    tf_counts = _collect_tf(items)

    latest = items[0] if items else None
    latest_meta = latest.get("metadata", {}) if latest else {}
    latest_summary = latest_meta.get("summary", {}) if latest else {}

    top_blockers = blocker_counts.most_common(8)
    top_reasons = reason_counts.most_common(8)

    if not items:
        human_summary = f"No {symbol} dashboard snapshots found for {day}. Keep dashboard open to collect memory."
        next_focus = ["Open the 4 Chart Dashboard so auto snapshot memory can be collected."]
    else:
        human_summary = (
            f"{symbol} daily summary for {day}: {len(items)} snapshot(s) saved. "
            f"Latest command={latest.get('tags', ['', '', ''])[1] if latest else 'unknown'}, "
            f"latest stage={latest.get('tags', ['', '', ''])[2] if latest else 'unknown'}. "
            f"Latest D1={latest_summary.get('D1')}, H1={latest_summary.get('H1')}, "
            f"M15={latest_summary.get('M15')}, M5={latest_summary.get('M5')}."
        )
        next_focus = []
        if top_blockers:
            next_focus.append(f"Main blocker to watch: {top_blockers[0][0]}")
        h1_top = tf_counts["H1"].most_common(1)
        if h1_top:
            next_focus.append(f"H1 repeated state: {h1_top[0][0]}")
        m15_top = tf_counts["M15"].most_common(1)
        if m15_top:
            next_focus.append(f"M15 repeated state: {m15_top[0][0]}")
        next_focus.append("Keep collecting snapshots only as research memory; final decision remains manual.")

    return {
        "version": VERSION,
        "ok": True,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "date": day,
        "snapshot_count": len(items),
        "latest_snapshot": latest,
        "command_counts": dict(command_counts),
        "stage_counts": dict(stage_counts),
        "score_counts": dict(score_counts),
        "timeframe_counts": {tf: dict(counter) for tf, counter in tf_counts.items()},
        "top_blockers": [{"text": k, "count": v} for k, v in top_blockers],
        "top_reasons": [{"text": k, "count": v} for k, v in top_reasons],
        "human_summary": human_summary,
        "next_focus": next_focus,
        "note": "Daily summary is based on saved dashboard memory only. It does not place orders.",
    }
