"""Parameter scan for stored-candle rule research."""
from __future__ import annotations

from typing import Any

from app.services.jack_rule_research_engine import run_rule_research_v1


def scan_rule_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper()
    timeframe = str(payload.get("timeframe") or "H4").upper()
    initial_capital = float(payload.get("initial_capital") or 10000)
    risk_percent = float(payload.get("risk_percent") or 1)
    top_n = max(1, min(int(payload.get("top_n") or 20), 50))

    ema_fast_values = [10, 20, 30]
    ema_slow_values = [50, 100, 150]
    breakout_values = [10, 20, 30, 40]
    stop_values = [5, 10, 15, 20]
    target_values = [1.5, 2.0, 2.5, 3.0]

    rows: list[dict[str, Any]] = []
    tested = 0
    skipped = 0

    for fast in ema_fast_values:
        for slow in ema_slow_values:
            if slow <= fast:
                skipped += 1
                continue
            for breakout in breakout_values:
                for stop in stop_values:
                    for target_r in target_values:
                        tested += 1
                        result = run_rule_research_v1({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "initial_capital": initial_capital,
                            "risk_percent": risk_percent,
                            "ema_fast": fast,
                            "ema_slow": slow,
                            "breakout_lookback": breakout,
                            "stop_lookback": stop,
                            "target_r": target_r,
                            "limit": 20000,
                        })
                        summary = result.get("summary") if isinstance(result, dict) else None
                        if not summary:
                            skipped += 1
                            continue
                        trades = int(summary.get("number_of_trades") or 0)
                        pf = summary.get("profit_factor")
                        if trades < 10 or pf is None:
                            skipped += 1
                            continue
                        max_dd = abs(float(summary.get("max_drawdown_percent") or 0))
                        total_return = float(summary.get("total_return_percent") or 0)
                        score = round((float(pf) * 100) + total_return - (max_dd * 2), 4)
                        rows.append({
                            "rank_score": score,
                            "profit_factor": pf,
                            "total_return_percent": summary.get("total_return_percent"),
                            "max_drawdown_percent": summary.get("max_drawdown_percent"),
                            "final_equity": summary.get("final_equity"),
                            "number_of_trades": trades,
                            "win_rate_percent": summary.get("win_rate_percent"),
                            "ema_fast": fast,
                            "ema_slow": slow,
                            "breakout_lookback": breakout,
                            "stop_lookback": stop,
                            "target_r": target_r,
                        })

    rows.sort(key=lambda item: (item["rank_score"], item["profit_factor"], item["total_return_percent"]), reverse=True)
    return {
        "summary": {
            "engine": "Rule Parameter Scan v1",
            "symbol": symbol,
            "timeframe": timeframe,
            "combinations_tested": tested,
            "valid_results": len(rows),
            "skipped": skipped,
            "top_n": top_n,
            "status": "scan_complete" if rows else "no_valid_results",
        },
        "best": rows[0] if rows else None,
        "top_results": rows[:top_n],
        "notes": [
            "Historical research only.",
            "Use scan results as candidates, then validate on other periods and symbols.",
        ],
    }
