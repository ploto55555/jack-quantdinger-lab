from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any


VERSION = "memory_layer_v1"
MEMORY_PATH = os.getenv("JACK_MEMORY_PATH", "/app/data/memory/jack_memory_v1.json")
ALLOWED_TYPES = {"idea", "research_result", "mistake", "rule", "profile", "journal", "system_note"}


def memory_status_v1() -> dict[str, Any]:
    items = _load_items()
    type_counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("memory_type") or "unknown")
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
    return {
        "version": VERSION,
        "path": MEMORY_PATH,
        "total_items": len(items),
        "type_counts": type_counts,
        "purpose": "Persistent local memory for ideas, research notes, mistakes, rules, and profile observations.",
    }


def add_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    now = datetime.now(timezone.utc).isoformat()
    memory_type = str(payload.get("memory_type") or "system_note").strip()
    if memory_type not in ALLOWED_TYPES:
        memory_type = "system_note"
    text = str(payload.get("text") or "").strip()
    if not text:
        text = str(payload.get("note") or "").strip()
    if not text:
        return {"ok": False, "error": "text is required", "allowed_types": sorted(ALLOWED_TYPES)}

    item = {
        "id": str(payload.get("id") or f"mem_{uuid.uuid4().hex[:12]}"),
        "created_at": now,
        "updated_at": now,
        "memory_type": memory_type,
        "symbol": str(payload.get("symbol") or "").upper().strip(),
        "profile_id": str(payload.get("profile_id") or "").strip(),
        "tags": _tags(payload.get("tags")),
        "text": text,
        "source": str(payload.get("source") or "manual").strip(),
        "importance": _to_int(payload.get("importance"), default=3),
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }
    items = _load_items()
    items.append(item)
    _save_items(items)
    return {"ok": True, "item": item, "status": memory_status_v1()}


def list_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = _to_int(payload.get("limit"), default=50)
    memory_type = str(payload.get("memory_type") or "").strip()
    symbol = str(payload.get("symbol") or "").upper().strip()
    items = _load_items()
    if memory_type:
        items = [x for x in items if x.get("memory_type") == memory_type]
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]
    items = sorted(items, key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"version": VERSION, "total": len(items), "items": items[:limit]}


def search_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    query = str(payload.get("query") or "").strip().lower()
    limit = _to_int(payload.get("limit"), default=20)
    symbol = str(payload.get("symbol") or "").upper().strip()
    memory_type = str(payload.get("memory_type") or "").strip()
    words = [w for w in query.replace("/", " ").replace("_", " ").split() if w]
    items = _load_items()
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]
    if memory_type:
        items = [x for x in items if x.get("memory_type") == memory_type]
    scored = []
    for item in items:
        score = _score(item, words, query)
        if score > 0 or not query:
            scored.append((score, item))
    scored.sort(key=lambda pair: (pair[0], str(pair[1].get("created_at") or "")), reverse=True)
    return {
        "version": VERSION,
        "query": query,
        "total_matches": len(scored),
        "items": [{"score": score, **item} for score, item in scored[:limit]],
    }


def seed_research_notes_to_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    from app.services.jack_research_notes import build_research_notes_v1

    payload = payload or {}
    notes = build_research_notes_v1({"symbol": payload.get("symbol", "")}).get("notes", [])
    existing = _load_items()
    existing_keys = {x.get("metadata", {}).get("note_id") for x in existing if isinstance(x.get("metadata"), dict)}
    added = []
    for note in notes:
        note_id = note.get("note_id")
        if note_id in existing_keys:
            continue
        text = _note_text(note)
        item_payload = {
            "memory_type": "research_result",
            "symbol": note.get("symbol"),
            "profile_id": note.get("profile_id"),
            "tags": [note.get("profile_type"), note.get("decision"), *(note.get("quality_flags") or [])],
            "text": text,
            "source": "research_notes_v1",
            "importance": 4,
            "metadata": {"note_id": note_id, "test_type": note.get("test_type")},
        }
        result = add_memory_v1(item_payload)
        if result.get("ok"):
            added.append(result.get("item"))
    return {"version": VERSION, "added_count": len(added), "added": added, "status": memory_status_v1()}


def _note_text(note: dict[str, Any]) -> str:
    summary = note.get("result_summary") or {}
    flags = ", ".join(note.get("quality_flags") or [])
    return (
        f"{note.get('symbol')} {note.get('profile_id')} {note.get('profile_type')} decision={note.get('decision')}. "
        f"Reason: {note.get('reason')} "
        f"Result: return={summary.get('return_percent')} max_drop={summary.get('max_drop_percent')} "
        f"samples={summary.get('sample_count')} ratio={summary.get('positive_negative_ratio')}. "
        f"Flags: {flags}. Next: {note.get('next_action')}"
    )


def _score(item: dict[str, Any], words: list[str], query: str) -> int:
    if not words and not query:
        return 1
    hay = " ".join([
        str(item.get("symbol") or ""),
        str(item.get("profile_id") or ""),
        str(item.get("memory_type") or ""),
        " ".join([str(t) for t in item.get("tags") or []]),
        str(item.get("text") or ""),
    ]).lower()
    score = 0
    if query and query in hay:
        score += 10
    for word in words:
        if word in hay:
            score += 2
    score += min(_to_int(item.get("importance"), default=3), 5)
    return score if score > min(_to_int(item.get("importance"), default=3), 5) else 0


def _load_items() -> list[dict[str, Any]]:
    if not os.path.exists(MEMORY_PATH):
        return []
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return [x for x in data.get("items", []) if isinstance(x, dict)]
    except Exception:
        return []
    return []


def _save_items(items: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return []


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default
