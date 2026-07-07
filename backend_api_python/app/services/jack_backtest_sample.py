"""Sample-only Jack Backtest service.

This module is deliberately deterministic and does not touch broker APIs,
AI APIs, external data sources, or live execution. It exists to prove the
Jack Backtest API contract before connecting real 10+ year historical data.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Any

from app.services.jack_data_center_sample import sample_candles


@dataclass(frozen=True)
class BacktestSummary:
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return_percent: float
    cagr_percent: float
    max_drawdown_percent: float
    win_rate_percent: float
    profit_factor: float
    number_of_trades: int
    average_r: float
    best_trade_r: float
    worst_trade_r: float
    status: str = "sample_only"


DEFAULT_SAMPLE_INPUT = {
    "strategy_name": "GBPJPY Trend Breakout v1",
    "symbol": "GBPJPY",
    "timeframe": "H4",
    "start_date": "2015-01-01",
    "end_date": "2025-01-01",
    "initial_capital": 10000.0,
}


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def normalise_sample_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "strategy_name": _to_str(payload.get("strategy_name"), DEFAULT_SAMPLE_INPUT["strategy_name"]),
        "symbol": _to_str(payload.get("symbol"), DEFAULT_SAMPLE_INPUT["symbol"]).upper(),
        "timeframe": _to_str(payload.get("timeframe"), DEFAULT_SAMPLE_INPUT["timeframe"]).upper(),
        "start_date": _to_str(payload.get("start_date"), DEFAULT_SAMPLE_INPUT["start_date"]),
        "end_date": _to_str(payload.get("end_date"), DEFAULT_SAMPLE_INPUT["end_date"]),
        "initial_capital": _to_float(payload.get("initial_capital"), DEFAULT_SAMPLE_INPUT["initial_capital"]),
    }


def build_sample_backtest(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    request_data = normalise_sample_request(payload)
    initial_capital = max(request_data["initial_capital"], 1.0)

    # Deterministic placeholder result. These are not real backtest numbers.
    final_equity = round(initial_capital * 1.846, 2)
    summary = BacktestSummary(
        strategy_name=request_data["strategy_name"],
        symbol=request_data["symbol"],
        timeframe=request_data["timeframe"],
        start_date=request_data["start_date"],
        end_date=request_data["end_date"],
        initial_capital=initial_capital,
        final_equity=final_equity,
        total_return_percent=84.6,
        cagr_percent=6.32,
        max_drawdown_percent=-18.4,
        win_rate_percent=41.8,
        profit_factor=1.42,
        number_of_trades=287,
        average_r=0.21,
        best_trade_r=5.7,
        worst_trade_r=-1.0,
    )

    equity_curve = _sample_equity_curve(initial_capital)
    trades = _sample_trades()

    return {
        "summary": asdict(summary),
        "equity_curve": equity_curve,
        "trades": trades,
        "notes": [
            "Sample-only deterministic result.",
            "No AI token used.",
            "No broker connection used.",
            "Next step: connect local 10+ year historical candles and real backtest engine.",
        ],
    }


def build_candle_buy_hold_backtest(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a simple buy-and-hold calculation from sample candles.

    This proves the data -> backtest -> result chain. It is not yet a real
    trading strategy engine.
    """
    payload = payload or {}
    symbol = _to_str(payload.get("symbol"), "GBPJPY").upper()
    timeframe = _to_str(payload.get("timeframe"), "H4").upper()
    limit = max(2, min(_to_int(payload.get("limit"), 120), 500))
    initial_capital = max(_to_float(payload.get("initial_capital"), 10000.0), 1.0)

    candles = sample_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    start_close = float(candles[0]["close"])
    end_close = float(candles[-1]["close"])
    total_return_percent = ((end_close / start_close) - 1.0) * 100.0
    final_equity = round(initial_capital * (end_close / start_close), 2)
    equity_curve = _equity_curve_from_candles(candles, initial_capital, start_close)
    max_drawdown_percent = _max_drawdown_percent([point["equity"] for point in equity_curve])

    summary = {
        "strategy_name": "Buy & Hold Candle Chain Test",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": candles[0]["timestamp"],
        "end_date": candles[-1]["timestamp"],
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "start_close": start_close,
        "end_close": end_close,
        "total_return_percent": round(total_return_percent, 4),
        "max_drawdown_percent": round(max_drawdown_percent, 4),
        "number_of_candles": len(candles),
        "number_of_trades": 1,
        "status": "computed_from_sample_candles",
    }

    trade = {
        "id": 1,
        "symbol": symbol,
        "side": "long",
        "entry_date": candles[0]["timestamp"],
        "entry_price": start_close,
        "exit_date": candles[-1]["timestamp"],
        "exit_price": end_close,
        "return_percent": round(total_return_percent, 4),
        "reason": "buy first sample candle close, sell last sample candle close",
    }

    return {
        "summary": summary,
        "equity_curve": equity_curve,
        "trades": [trade],
        "candles_used_preview": candles[:5],
        "notes": [
            "Computed from Jack Data Center sample candles.",
            "No AI token used.",
            "No external market data API used.",
            "No broker connection used.",
            "Next step: replace sample candles with imported 10+ year historical candles.",
        ],
    }


def _equity_curve_from_candles(candles: list[dict[str, Any]], initial_capital: float, start_close: float) -> list[dict[str, Any]]:
    return [
        {
            "date": candle["timestamp"],
            "equity": round(initial_capital * (float(candle["close"]) / start_close), 2),
            "close": float(candle["close"]),
        }
        for candle in candles
    ]


def _max_drawdown_percent(equity_values: list[float]) -> float:
    peak = equity_values[0] if equity_values else 0.0
    max_drawdown = 0.0
    for equity in equity_values:
        peak = max(peak, equity)
        if peak > 0:
            drawdown = ((equity / peak) - 1.0) * 100.0
            max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def _sample_equity_curve(initial_capital: float) -> list[dict[str, Any]]:
    start = date(2015, 1, 1)
    multipliers = [1.0, 1.08, 1.02, 1.21, 1.34, 1.29, 1.48, 1.61, 1.52, 1.72, 1.846]
    return [
        {
            "date": (start + timedelta(days=365 * idx)).isoformat(),
            "equity": round(initial_capital * multiplier, 2),
        }
        for idx, multiplier in enumerate(multipliers)
    ]


def _sample_trades() -> list[dict[str, Any]]:
    return [
        {"id": 1, "symbol": "GBPJPY", "side": "long", "entry_date": "2015-03-18", "exit_date": "2015-04-02", "r": 2.4, "reason": "H4 breakout with daily trend"},
        {"id": 2, "symbol": "GBPJPY", "side": "short", "entry_date": "2015-06-10", "exit_date": "2015-06-14", "r": -1.0, "reason": "stop loss"},
        {"id": 3, "symbol": "GBPJPY", "side": "long", "entry_date": "2016-02-03", "exit_date": "2016-03-08", "r": 5.7, "reason": "trend continuation"},
        {"id": 4, "symbol": "GBPJPY", "side": "short", "entry_date": "2018-08-22", "exit_date": "2018-09-03", "r": 1.8, "reason": "breakdown follow-through"},
        {"id": 5, "symbol": "GBPJPY", "side": "long", "entry_date": "2020-11-09", "exit_date": "2020-11-21", "r": -0.6, "reason": "time exit"},
    ]
