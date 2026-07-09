from __future__ import annotations

"""
Step 55B - MT5 Tick Bridge Writer v1

Purpose:
- Read live quote information from the local MetaTrader 5 terminal via the MetaTrader5 Python package.
- Write a small JSON tick file that the Jack AI Capital OS dashboard can read.

Safety:
- This script does NOT place orders.
- This script does NOT modify positions.
- This script only reads symbol info and writes a local JSON file.

Run examples from backend_api_python folder:
    python scripts/mt5_tick_bridge_writer.py --symbol GBPJPY --interval 2
    python scripts/mt5_tick_bridge_writer.py --mt5-symbol "GBPJPYm#" --output-symbol GBPJPY --interval 2

Output file:
    data/market/live_ticks/GBPJPY_tick.json
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = BACKEND_ROOT / "data" / "market" / "live_ticks"


def _clean_output_symbol(symbol: str) -> str:
    """Normalize the dashboard/output symbol only. Do not use this for broker MT5 names."""
    return str(symbol or "GBPJPY").upper().replace("/", "").replace("_", "")


def _clean_mt5_symbol(symbol: str) -> str:
    """Preserve broker symbol case and suffixes such as GBPJPYm# or EURUSDmicro."""
    return str(symbol or "GBPJPY").strip().replace("/", "").replace("_", "")


def _spread_pips(output_symbol: str, bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    symbol = _clean_output_symbol(output_symbol)
    # JPY pairs are usually quoted to 3 decimals. One pip is commonly 0.01.
    pip_size = 0.01 if symbol.endswith("JPY") else 0.0001
    return round(abs(ask - bid) / pip_size, 2)


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def build_payload(mt5_symbol: str, output_symbol: str, tick: Any, source: str = "mt5_python_tick") -> Dict[str, Any]:
    bid = float(tick.bid) if getattr(tick, "bid", None) is not None else None
    ask = float(tick.ask) if getattr(tick, "ask", None) is not None else None
    last = float(tick.last) if getattr(tick, "last", None) is not None else None
    mid = (bid + ask) / 2 if bid is not None and ask is not None else last
    tick_time = getattr(tick, "time", None)
    if tick_time:
        timestamp = datetime.fromtimestamp(int(tick_time), tz=timezone.utc).isoformat()
    else:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "version": "mt5_tick_bridge_writer_v1",
        "ok": mid is not None,
        "mode": "personal_research_support_only",
        "broker_connection": False,
        "auto_trading": False,
        "source": source,
        "symbol": _clean_output_symbol(output_symbol),
        "mt5_symbol": _clean_mt5_symbol(mt5_symbol),
        "timestamp": timestamp,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "bid": round(bid, 5) if bid is not None else None,
        "ask": round(ask, 5) if ask is not None else None,
        "last": round(last, 5) if last is not None else None,
        "mid": round(mid, 5) if mid is not None else None,
        "price": round(mid, 5) if mid is not None else None,
        "spread_pips": _spread_pips(output_symbol, bid, ask),
        "note": "Read-only MT5 tick bridge. This file is for dashboard live reference only.",
    }


def run_bridge(
    symbol: str,
    interval: float,
    output_dir: Path,
    once: bool = False,
    mt5_symbol: str | None = None,
    output_symbol: str | None = None,
) -> int:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        print("MetaTrader5 Python package is not installed or cannot be imported.", file=sys.stderr)
        print("Install locally with: pip install MetaTrader5", file=sys.stderr)
        print(f"Import error: {exc}", file=sys.stderr)
        return 2

    mt5_symbol_clean = _clean_mt5_symbol(mt5_symbol or symbol)
    output_symbol_clean = _clean_output_symbol(output_symbol or symbol)
    output_path = output_dir / f"{output_symbol_clean}_tick.json"

    if not mt5.initialize():
        print(f"MT5 initialize failed: {mt5.last_error()}", file=sys.stderr)
        return 3

    try:
        if not mt5.symbol_select(mt5_symbol_clean, True):
            print(f"MT5 symbol_select failed for {mt5_symbol_clean}: {mt5.last_error()}", file=sys.stderr)
            print("Tip: Check the exact symbol name in MT5 Market Watch, including suffix/case like GBPJPYm#.", file=sys.stderr)
            return 4

        print(f"MT5 tick bridge started for MT5 symbol: {mt5_symbol_clean}")
        print(f"Dashboard/output symbol: {output_symbol_clean}")
        print(f"Writing to: {output_path}")
        print("Read-only mode. No order actions are used.")

        while True:
            tick = mt5.symbol_info_tick(mt5_symbol_clean)
            if tick is None:
                print(f"No tick returned for {mt5_symbol_clean}: {mt5.last_error()}", file=sys.stderr)
            else:
                payload = build_payload(mt5_symbol_clean, output_symbol_clean, tick)
                _write_json_atomic(output_path, payload)
                print(
                    f"{payload['written_at']} {output_symbol_clean} "
                    f"mt5={mt5_symbol_clean} bid={payload['bid']} ask={payload['ask']} spread={payload['spread_pips']}"
                )

            if once:
                break
            time.sleep(max(interval, 0.5))
    finally:
        mt5.shutdown()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read MT5 tick data and write a local JSON tick file for Jack AI Capital OS.")
    parser.add_argument("--symbol", default="GBPJPY", help="Standard dashboard symbol, for example GBPJPY")
    parser.add_argument("--mt5-symbol", default=None, help="Exact broker symbol in MT5 Market Watch, for example GBPJPYm#")
    parser.add_argument("--output-symbol", default=None, help="Dashboard/output symbol for the tick file, for example GBPJPY")
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output folder for tick JSON files")
    parser.add_argument("--once", action="store_true", help="Write one tick and exit")
    args = parser.parse_args()
    return run_bridge(
        args.symbol,
        args.interval,
        Path(args.output_dir),
        once=args.once,
        mt5_symbol=args.mt5_symbol,
        output_symbol=args.output_symbol,
    )


if __name__ == "__main__":
    raise SystemExit(main())
