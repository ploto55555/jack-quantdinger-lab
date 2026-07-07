from __future__ import annotations

from typing import Any

from app.services.jack_candle_storage import load_candles
from app.services.jack_walk_forward import _simulate

A = [10, 20, 30]
B = [50, 100, 150]
C = [10, 20, 30, 40]
D = [5, 10, 15, 20]
E = [1.5, 2.0, 2.5, 3.0]


def stability_report_v1(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    symbol = str(payload.get("symbol") or "GBPJPY").upper()
    timeframe = str(payload.get("timeframe") or "H4").upper()
    capital = float(payload.get("initial_capital") or 10000)
    top_n = max(1, min(int(payload.get("top_n") or 20), 50))
    split_a = str(payload.get("train_end") or "2017-12-31T23:59:59Z")
    split_b = str(payload.get("validate_start") or "2018-01-01T00:00:00Z")

    stored = load_candles(symbol=symbol, timeframe=timeframe, limit=20000)
    rows = [_row(x) for x in stored.get("candles", [])]
    rows = [x for x in rows if x is not None]
    left = [x for x in rows if x["timestamp"] <= split_a]
    right = [x for x in rows if x["timestamp"] >= split_b]

    out = []
    tested = 0
    for a in A:
        for b in B:
            if b <= a:
                continue
            for c in C:
                for d in D:
                    for e in E:
                        tested += 1
                        x = _simulate(left, capital, 1.0, a, b, c, d, e)
                        y = _simulate(right, capital, 1.0, a, b, c, d, e)
                        if not _ok(x, 8) or not _ok(y, 10):
                            continue
                        score = _score(x, y)
                        out.append({
                            "stability_score": score,
                            "ema_fast": a,
                            "ema_slow": b,
                            "breakout_lookback": c,
                            "stop_lookback": d,
                            "target_r": e,
                            "train_return_percent": x.get("total_return_percent"),
                            "train_max_drawdown_percent": x.get("max_drawdown_percent"),
                            "train_trades": x.get("number_of_trades"),
                            "train_profit_factor": x.get("profit_factor"),
                            "validation_return_percent": y.get("total_return_percent"),
                            "validation_max_drawdown_percent": y.get("max_drawdown_percent"),
                            "validation_trades": y.get("number_of_trades"),
                            "validation_profit_factor": y.get("profit_factor"),
                        })
    out.sort(key=lambda x: x["stability_score"], reverse=True)
    return {
        "summary": {
            "engine": "Stability Report v1",
            "symbol": symbol,
            "timeframe": timeframe,
            "total_candles": len(rows),
            "train_candles": len(left),
            "validation_candles": len(right),
            "combinations_tested": tested,
            "passed_filters": len(out),
            "top_n": top_n,
            "status": "stability_report_complete" if out else "no_stable_candidates",
        },
        "best": out[0] if out else None,
        "top_results": out[:top_n],
        "storage": {k: stored.get(k) for k in ["rows_total", "rows_returned", "first_timestamp", "last_timestamp", "path"]},
    }


def _ok(r: dict[str, Any], n: int) -> bool:
    return r.get("status") == "ok" and int(r.get("number_of_trades") or 0) >= n and r.get("profit_factor") is not None and float(r.get("profit_factor") or 0) >= 1.05 and float(r.get("total_return_percent") or 0) > 0


def _score(x: dict[str, Any], y: dict[str, Any]) -> float:
    xr = float(x.get("total_return_percent") or 0)
    yr = float(y.get("total_return_percent") or 0)
    xp = float(x.get("profit_factor") or 0)
    yp = float(y.get("profit_factor") or 0)
    xd = abs(float(x.get("max_drawdown_percent") or 0))
    yd = abs(float(y.get("max_drawdown_percent") or 0))
    gap = abs(xr - yr) * 0.6 + abs(xp - yp) * 20
    return round(yp * 100 + yr + xp * 25 - yd * 2 - xd - gap, 4)


def _row(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    try:
        return {"timestamp": str(v["timestamp"]), "open": float(v["open"]), "high": float(v["high"]), "low": float(v["low"]), "close": float(v["close"])}
    except Exception:
        return None
