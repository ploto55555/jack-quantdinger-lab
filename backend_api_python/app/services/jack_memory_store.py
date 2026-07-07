from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


VERSION = "memory_store_v1"
DEFAULT_PATH = "/app/data/memory/jack_memory_v1.json"


def _path() -> str:
    return os.getenv("JACK_MEMORY_FILE", DEFAULT_PATH)


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


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z0-9_]+", text or "") if len(t) >= 2}


def _score(query: str, item: dict[str, Any]) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    body = " ".join([
        str(item.get("title") or ""),
        str(item.get("content") or ""),
        str(item.get("symbol") or ""),
        str(item.get("memory_type") or ""),
        " ".join([str(x) for x in item.get("tags", [])]),
    ])
    b = _tokens(body)
    overlap = len(q.intersection(b))
    return round(overlap / max(len(q), 1), 4)


def add_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    content = str(payload.get("content") or "").strip()
    if not content:
        return {"version": VERSION, "ok": False, "error": "content_required"}
    item = {
        "memory_id": str(payload.get("memory_id") or f"MEM_{uuid4().hex[:12].upper()}"),
        "created_at": _now(),
        "updated_at": _now(),
        "memory_type": str(payload.get("memory_type") or "idea").strip() or "idea",
        "symbol": str(payload.get("symbol") or "").upper().strip(),
        "title": str(payload.get("title") or "").strip(),
        "content": content,
        "tags": payload.get("tags") if isinstance(payload.get("tags"), list) else [],
        "source": str(payload.get("source") or "manual").strip() or "manual",
        "status": str(payload.get("status") or "active").strip() or "active",
        "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    }
    items = _load()
    items.append(item)
    _save(items)
    return {"version": VERSION, "ok": True, "memory": item, "total": len(items)}


def list_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "").upper().strip()
    memory_type = str(payload.get("memory_type") or "").strip()
    limit = int(payload.get("limit") or 50)
    items = _load()
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]
    if memory_type:
        items = [x for x in items if x.get("memory_type") == memory_type]
    items = sorted(items, key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"version": VERSION, "total": len(items), "items": items[:limit]}


def search_memory_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    query = str(payload.get("query") or "").strip()
    symbol = str(payload.get("symbol") or "").upper().strip()
    limit = int(payload.get("limit") or 10)
    items = _load()
    if symbol:
        items = [x for x in items if x.get("symbol") == symbol]
    ranked = []
    for item in items:
        score = _score(query, item)
        if score > 0:
            row = dict(item)
            row["match_score"] = score
            ranked.append(row)
    ranked.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return {"version": VERSION, "query": query, "total_matches": len(ranked), "items": ranked[:limit]}


def seed_from_research_notes_v1(notes: list[dict[str, Any]]) -> dict[str, Any]:
    items = _load()
    existing_ids = {x.get("memory_id") for x in items}
    added = []
    for note in notes:
        memory_id = f"MEM_{note.get('note_id')}"
        if memory_id in existing_ids:
            continue
        result = note.get("result_summary") or {}
        content = (
            f"{note.get('symbol')} {note.get('profile_id')} decision={note.get('decision')}. "
            f"Reason: {note.get('reason')}. "
            f"Return={result.get('return_percent')} max_drop={result.get('max_drop_percent')} "
            f"samples={result.get('sample_count')} ratio={result.get('positive_negative_ratio')}. "
            f"Next: {note.get('next_action')}"
        )
        item = {
            "memory_id": memory_id,
            "created_at": _now(),
            "updated_at": _now(),
            "memory_type": "research_note",
            "symbol": str(note.get("symbol") or "").upper(),
            "title": str(note.get("profile_id") or ""),
            "content": content,
            "tags": [note.get("profile_type"), note.get("decision")],
            "source": "research_notes_v1",
            "status": "active",
            "metadata": note,
        }
        items.append(item)
        existing_ids.add(memory_id)
        added.append(item)
    _save(items)
    return {"version": VERSION, "ok": True, "added": len(added), "total": len(items), "items": added}
