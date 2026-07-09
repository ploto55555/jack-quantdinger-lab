from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.jack_live_price_feed import _tick_candidates


def _clean_symbol(symbol: str) -> str:
    return str(symbol or "GBPJPY").upper().replace("/", "").replace("_", "")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _age_seconds(path: Path) -> Optional[float]:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return round((datetime.now(timezone.utc) - modified).total_seconds(), 2)
    except Exception:
        return None


def get_tick_bridge_status_v1(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    symbol = _clean_symbol(payload.get("symbol", "GBPJPY"))
    candidates = _tick_candidates(symbol)
    found_path: Optional[Path] = None
    data: Optional[Dict[str, Any]] = None

    for path in candidates:
        if path.exists() and path.is_file():
            found_path = path
            data = _read_json(path)
            break

    if not found_path:
        return {
            "version": "tick_bridge_status_v1",
            "ok": False,
            "mode": "personal_research_support_only",
            "broker_connection": False,
            "auto_trading": False,
            "symbol": symbol,
            "status": "tick_file_not_found",
            "file_path": None,
            "age_seconds": None,
            "latest": None,
            "expected_files": [str(p) for p in candidates[:8]],
            "how_to_start": "Run: python scripts/mt5_tick_bridge_writer.py --symbol GBPJPY --interval 2",
        }

    return {
        "version": "tick_bridge_status_v1",
        "ok": bool(data and data.get("price") is not None or data and data.get("mid") is not None),
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "symbol": symbol,
        "status": "tick_file_found",
        "file_path": str(found_path),
        "file_name": found_path.name,
        "age_seconds": _age_seconds(found_path),
        "latest": data,
        "expected_files": [str(p) for p in candidates[:8]],
    }
