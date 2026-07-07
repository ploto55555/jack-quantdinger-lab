from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.services.jack_memory_store import add_memory_v1
from app.services.jack_trade_journal import list_trade_journal_v1, trade_journal_summary_v1


VERSION = "learning_engine_v1"


def build_learning_report_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = max(10, min(_to_int(payload.get("limit"), 300), 1000))
    save = _bool(payload.get("save_memory"), True)

    journal = list_trade_journal_v1({"limit": limit})
    items = journal.get("items") or []
    summary = trade_journal_summary_v1({})

    profile_stats = _profile_stats(items)
    symbol_stats = _symbol_stats(items)
    mistake_stats = _mistake_stats(items)
    behavior_notes = _behavior_notes(items, mistake_stats, profile_stats)
    next_actions = _next_actions(items, profile_stats, mistake_stats)

    report = {
        "version": VERSION,
        "ok": True,
        "journal_items_scanned": len(items),
        "journal_summary": summary,
        "profile_stats": profile_stats,
        "symbol_stats": symbol_stats,
        "mistake_stats": mistake_stats,
        "behavior_notes": behavior_notes,
        "next_actions": next_actions,
        "human_summary": "",
        "notes": [
            "Learning report is based on journal records only.",
            "More closed/reviewed records are required before conclusions become strong.",
            "Research support only; no broker connection and no live automation.",
        ],
    }
    report["human_summary"] = _human_summary(report)

    if save:
        saved = add_memory_v1({
            "memory_type": "learning_report",
            "symbol": "MULTI",
            "title": "Learning Report v1",
            "content": report["human_summary"],
            "tags": [VERSION, "journal", "learning", "snowball"],
            "source": VERSION,
            "metadata": report,
        })
        report["memory_id"] = (saved.get("memory") or {}).get("memory_id")

    return report


def _profile_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        key = str(item.get("profile_id") or "UNKNOWN")
        grouped[key].append(item)
    rows = []
    for profile_id, rows_items in grouped.items():
        closed = [x for x in rows_items if x.get("status") in ["closed", "reviewed"]]
        r_values = [_to_float(x.get("result_r"), 0.0) for x in closed if x.get("result_r") is not None]
        rows.append({
            "profile_id": profile_id,
            "total": len(rows_items),
            "planned": len([x for x in rows_items if x.get("status") == "planned"]),
            "closed": len(closed),
            "total_r": round(sum(r_values), 3) if r_values else 0.0,
            "average_r": round(sum(r_values) / len(r_values), 3) if r_values else None,
            "quality_counts": dict(Counter(str(x.get("setup_quality") or "UNKNOWN") for x in rows_items)),
        })
    return sorted(rows, key=lambda x: (x.get("total_r") or 0, x.get("closed") or 0, x.get("total") or 0), reverse=True)


def _symbol_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        key = str(item.get("symbol") or "UNKNOWN")
        grouped[key].append(item)
    rows = []
    for symbol, rows_items in grouped.items():
        closed = [x for x in rows_items if x.get("status") in ["closed", "reviewed"]]
        r_values = [_to_float(x.get("result_r"), 0.0) for x in closed if x.get("result_r") is not None]
        rows.append({
            "symbol": symbol,
            "total": len(rows_items),
            "closed": len(closed),
            "total_r": round(sum(r_values), 3) if r_values else 0.0,
            "average_r": round(sum(r_values) / len(r_values), 3) if r_values else None,
        })
    return sorted(rows, key=lambda x: (x.get("total_r") or 0, x.get("closed") or 0, x.get("total") or 0), reverse=True)


def _mistake_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter()
    by_symbol: dict[str, Counter] = defaultdict(Counter)
    by_profile: dict[str, Counter] = defaultdict(Counter)
    for item in items:
        if item.get("status") not in ["closed", "reviewed"]:
            continue
        symbol = str(item.get("symbol") or "UNKNOWN")
        profile_id = str(item.get("profile_id") or "UNKNOWN")
        for mistake in item.get("mistakes") or []:
            key = str(mistake)
            counter[key] += 1
            by_symbol[symbol][key] += 1
            by_profile[profile_id][key] += 1
    return [
        {
            "mistake": mistake,
            "count": count,
            "symbols": {k: v.get(mistake, 0) for k, v in by_symbol.items() if v.get(mistake, 0)},
            "profiles": {k: v.get(mistake, 0) for k, v in by_profile.items() if v.get(mistake, 0)},
        }
        for mistake, count in counter.most_common()
    ]


def _behavior_notes(items: list[dict[str, Any]], mistakes: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> list[str]:
    notes = []
    total = len(items)
    closed = len([x for x in items if x.get("status") in ["closed", "reviewed"]])
    planned = len([x for x in items if x.get("status") == "planned"])
    if total == 0:
        notes.append("No journal records yet. Start by recording planned and reviewed items.")
    elif closed == 0:
        notes.append("Journal has planned records but no closed/reviewed records yet; learning strength is low.")
    if planned > closed * 3 and total >= 5:
        notes.append("Many planned records are not reviewed yet; review completion should improve.")
    if mistakes:
        notes.append(f"Most common mistake so far: {mistakes[0].get('mistake')} count={mistakes[0].get('count')}.")
    if profiles:
        best = profiles[0]
        notes.append(f"Most recorded profile: {best.get('profile_id')} total={best.get('total')} closed={best.get('closed')}.")
    return notes


def _next_actions(items: list[dict[str, Any]], profiles: list[dict[str, Any]], mistakes: list[dict[str, Any]]) -> list[str]:
    actions = []
    if not items:
        actions.append("Record at least 20 planned/reviewed journal items before trusting behavior statistics.")
    else:
        actions.append("After every planned item, update it to closed or reviewed with result_r and mistakes.")
    if mistakes:
        actions.append(f"Create a simple checklist to reduce: {mistakes[0].get('mistake')}.")
    else:
        actions.append("Start tagging mistakes consistently, for example: chasing, late_entry, ignored_plan, poor_timing.")
    if profiles:
        actions.append(f"Keep separating results by profile_id; current top recorded profile is {profiles[0].get('profile_id')}.")
    return actions[:8]


def _human_summary(report: dict[str, Any]) -> str:
    js = report.get("journal_summary") or {}
    profile = (report.get("profile_stats") or [{}])[0]
    mistake = (report.get("mistake_stats") or [{}])[0]
    return (
        f"Learning report completed. Journal total={js.get('total_items')} closed={js.get('closed_items')} "
        f"total_R={js.get('total_r')} average_R={js.get('average_r')}. "
        f"Top profile={profile.get('profile_id')} total={profile.get('total')} closed={profile.get('closed')}. "
        f"Top mistake={mistake.get('mistake')} count={mistake.get('count')}. "
        f"Next: {' | '.join(report.get('next_actions') or [])}"
    )


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
