from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.jack_memory_store import add_memory_v1
from app.services.jack_risk_mode_v2 import calculate_risk_mode_v2


VERSION = "trade_journal_v1"
DEFAULT_PATH = "/app/data/journal/jack_trade_journal_v1.json"


def _path() -> str:
    return os.getenv("JACK_TRADE_JOURNAL_FILE", DEFAULT_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict[str, Any]]:
    path = _path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def add_trade_journal_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "").upper().strip()
    profile_id = str(payload.get("profile_id") or "").strip()
    setup_quality = str(payload.get("setup_quality") or "A").upper().strip()
    equity = _to_float(payload.get("equity"), 500.0)
    peak_equity = _to_float(payload.get("peak_equity"), equity)

    risk = calculate_risk_mode_v2({
        "equity": equity,
        "peak_equity": peak_equity,
        "profile_id": profile_id or "GBPJPY_H4_UP_V1",
        "setup_quality": setup_quality,
        "save_memory": False,
    })

    item = {
        "journal_id": str(payload.get("journal_id") or f"TJ_{uuid4().hex[:12].upper()}"),
        "created_at": _now(),
        "updated_at": _now(),
        "status": str(payload.get("status") or "planned").strip(),
        "symbol": symbol,
        "timeframe": str(payload.get("timeframe") or "").upper().strip(),
        "profile_id": profile_id,
        "setup_quality": setup_quality,
        "idea_text": str(payload.get("idea_text") or payload.get("text") or "").strip(),
        "entry_plan": str(payload.get("entry_plan") or "").strip(),
        "invalid_reason": str(payload.get("invalid_reason") or "").strip(),
        "risk_percent_planned": _optional_float(payload.get("risk_percent_planned")),
        "result_r": _optional_float(payload.get("result_r")),
        "result_note": str(payload.get("result_note") or "").strip(),
        "mistakes": payload.get("mistakes") if isinstance(payload.get("mistakes"), list) else [],
        "screenshots": payload.get("screenshots") if isinstance(payload.get("screenshots"), list) else [],
        "tags": payload.get("tags") if isinstance(payload.get("tags"), list) else [],
        "risk_mode_snapshot": risk,
        "ai_review": "",
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }
    item["ai_review"] = _review_text(item, risk)

    items = _load()
    items.append(item)
    _save(items)

    add_memory_v1({
        "memory_type": "trade_journal",
        "symbol": symbol or "MULTI",
        "title": f"Trade Journal {item['journal_id']} {symbol}",
        "content": item["ai_review"],
        "tags": [VERSION, item["status"], setup_quality, risk.get("final_mode")],
        "source": VERSION,
        "metadata": item,
    })

    return {"version": VERSION, "ok": True, "journal": item, "total": len(items)}


def list_trade_journal_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "").upper().strip()
    status = str(payload.get("status") or "").strip()
    limit = max(1, min(_to_int(payload.get("limit"), 50), 300))
    items = _load()
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]
    if status:
        items = [x for x in items if x.get("status") == status]
    items = sorted(items, key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"version": VERSION, "ok": True, "total": len(items), "items": items[:limit]}


def update_trade_journal_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    journal_id = str(payload.get("journal_id") or "").strip()
    if not journal_id:
        return {"version": VERSION, "ok": False, "error": "journal_id_required"}

    items = _load()
    found = None
    for item in items:
        if item.get("journal_id") == journal_id:
            found = item
            break

    if not found:
        return {"version": VERSION, "ok": False, "error": "journal_not_found"}

    allowed = [
        "status", "risk_percent_planned", "result_r", "result_note",
        "mistakes", "screenshots", "tags", "metadata",
        "entry_plan", "invalid_reason", "setup_quality",
    ]
    for key in allowed:
        if key in payload:
            found[key] = payload[key]

    found["updated_at"] = _now()
    found["ai_review"] = _review_text(found, found.get("risk_mode_snapshot") or {})
    _save(items)

    add_memory_v1({
        "memory_type": "trade_journal_update",
        "symbol": str(found.get("symbol") or "MULTI"),
        "title": f"Trade Journal Update {journal_id}",
        "content": found["ai_review"],
        "tags": [VERSION, str(found.get("status") or "updated")],
        "source": VERSION,
        "metadata": found,
    })

    return {"version": VERSION, "ok": True, "journal": found}


def trade_journal_summary_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    items = _load()
    symbol = str(payload.get("symbol") or "").upper().strip()
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]

    closed = [x for x in items if x.get("status") in ["closed", "reviewed"]]
    r_values = [_to_float(x.get("result_r"), 0.0) for x in closed if x.get("result_r") is not None]

    mistakes: dict[str, int] = {}
    for item in closed:
        for mistake in item.get("mistakes") or []:
            key = str(mistake)
            mistakes[key] = mistakes.get(key, 0) + 1

    summary = {
        "version": VERSION,
        "ok": True,
        "total_items": len(items),
        "closed_items": len(closed),
        "planned_items": len([x for x in items if x.get("status") == "planned"]),
        "average_r": round(sum(r_values) / len(r_values), 3) if r_values else None,
        "total_r": round(sum(r_values), 3) if r_values else 0.0,
        "mistake_counts": dict(sorted(mistakes.items(), key=lambda x: x[1], reverse=True)),
        "human_summary": "",
    }
    summary["human_summary"] = _summary_text(summary)
    return summary


def _review_text(payload: dict[str, Any], risk: dict[str, Any]) -> str:
    symbol = str(payload.get("symbol") or "")
    quality = str(payload.get("setup_quality") or "")
    status = str(payload.get("status") or "planned")
    result_r = payload.get("result_r")
    mistakes = payload.get("mistakes") if isinstance(payload.get("mistakes"), list) else []
    mode = risk.get("final_mode")
    max_risk = risk.get("max_research_risk_percent")

    text = f"Journal review: {symbol} status={status} quality={quality} risk_mode={mode} max_research_risk={max_risk}%."
    if result_r is not None:
        text += f" Result R={result_r}."
    if mistakes:
        text += f" Mistakes recorded: {', '.join(str(x) for x in mistakes)}."
    if mode in ["PAUSE", "BLOCK", "WAIT"]:
        text += " Framework says this should not be prioritized for review now."
    return text + " Research support only."


def _summary_text(summary: dict[str, Any]) -> str:
    return (
        f"Trade journal summary: total={summary.get('total_items')} closed={summary.get('closed_items')} "
        f"total_R={summary.get('total_r')} average_R={summary.get('average_r')} "
        f"top_mistakes={summary.get('mistake_counts')}."
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


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
