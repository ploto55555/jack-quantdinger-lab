"""Ketty Regime Classifier and trend-breakout research backtest v0.1.

Research only. Reads local GBPJPY H1/H4 OHLC CSV files exported from MT5.
No broker connection and no trade execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

PIP_SIZE = 0.01
MAX_HOLD = 96


def load_mt5(path: Path) -> pd.DataFrame:
    """Load the seven-field MT5 export whose header exposes only six names."""
    df = pd.read_csv(
        path,
        sep="\t",
        header=0,
        names=["timestamp", "open", "high", "low", "close", "tick_volume", "spread_points"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    numeric = ["open", "high", "low", "close", "tick_volume", "spread_points"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return (
        df.dropna(subset=["timestamp", "open", "high", "low", "close"])
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = tr.rolling(14).mean()
    out["sma14"] = out["close"].rolling(14).mean()
    out["sma20"] = out["close"].rolling(20).mean()
    out["std20"] = out["close"].rolling(20).std(ddof=0)
    out["bb_upper"] = out["sma20"] + 2 * out["std20"]
    out["bb_lower"] = out["sma20"] - 2 * out["std20"]
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["sma20"]
    out["bb_width_median50"] = out["bb_width"].rolling(50).median()
    out["slope_norm"] = (out["sma14"] - out["sma14"].shift(3)) / (out["atr14"] * 3)
    out["range20_atr"] = (
        out["high"].rolling(20).max() - out["low"].rolling(20).min()
    ) / out["atr14"]

    tenkan = (out["high"].rolling(9).max() + out["low"].rolling(9).min()) / 2
    kijun = (out["high"].rolling(26).max() + out["low"].rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = (
        (out["high"].rolling(52).max() + out["low"].rolling(52).min()) / 2
    ).shift(26)
    out["cloud_top"] = pd.concat([span_a, span_b], axis=1).max(axis=1)
    out["cloud_bottom"] = pd.concat([span_a, span_b], axis=1).min(axis=1)
    return out


def classify_simple_cloud(h4: pd.DataFrame) -> pd.Series:
    """Source-inspired Ketty V0.1 regime classifier without future data."""
    up = (
        (h4["close"] > h4["sma20"])
        & (h4["slope_norm"] > 0.03)
        & (h4["close"] > h4["cloud_top"])
    )
    down = (
        (h4["close"] < h4["sma20"])
        & (h4["slope_norm"] < -0.03)
        & (h4["close"] < h4["cloud_bottom"])
    )
    range_regime = (
        (~up)
        & (~down)
        & (h4["slope_norm"].abs() < 0.04)
        & (h4["bb_width"] <= h4["bb_width_median50"])
        & (h4["range20_atr"] <= 5.5)
    )
    result = pd.Series("UNCLEAR", index=h4.index)
    result[up] = "UPTREND"
    result[down] = "DOWNTREND"
    result[range_regime] = "RANGE"
    return result


def build_context(h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    h1i = add_indicators(h1)
    h4i = add_indicators(h4)
    h4i["regime"] = classify_simple_cloud(h4i)
    context = h4i[["timestamp", "regime"]].copy()
    context["regime"] = context["regime"].shift(1)
    merged = pd.merge_asof(
        h1i.sort_values("timestamp"),
        context.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    )
    return merged.dropna(subset=["atr14", "regime"]).reset_index(drop=True)


def run_selected_candidate(data: pd.DataFrame) -> pd.DataFrame:
    lookback = 40
    prev_high = data["high"].rolling(lookback).max().shift(1)
    prev_low = data["low"].rolling(lookback).min().shift(1)
    body_atr = (data["close"] - data["open"]).abs() / data["atr14"]
    long_signal = (
        (data["regime"] == "UPTREND")
        & (data["close"] > prev_high)
        & (body_atr >= 0.3)
    ).fillna(False)
    short_signal = (
        (data["regime"] == "DOWNTREND")
        & (data["close"] < prev_low)
        & (body_atr >= 0.3)
    ).fillna(False)

    ts = data["timestamp"].to_numpy()
    op = data["open"].to_numpy(float)
    hi = data["high"].to_numpy(float)
    lo = data["low"].to_numpy(float)
    cl = data["close"].to_numpy(float)
    atr = data["atr14"].to_numpy(float)
    spread = data["spread_points"].to_numpy(float) * 0.001

    hi_pad = np.concatenate([hi, np.full(MAX_HOLD, np.nan)])
    lo_pad = np.concatenate([lo, np.full(MAX_HOLD, np.nan)])
    cl_pad = np.concatenate([cl, np.full(MAX_HOLD, np.nan)])
    hi_win = sliding_window_view(hi_pad, MAX_HOLD + 1)[: len(data)]
    lo_win = sliding_window_view(lo_pad, MAX_HOLD + 1)[: len(data)]
    cl_win = sliding_window_view(cl_pad, MAX_HOLD + 1)[: len(data)]

    direction = np.where(long_signal, 1, np.where(short_signal, -1, 0))
    signal_idx = np.flatnonzero(direction != 0)
    signal_idx = signal_idx[signal_idx + 1 + MAX_HOLD < len(data)]
    direction = direction[signal_idx]
    entry_idx = signal_idx + 1

    entry_spread = spread[entry_idx]
    entry = np.where(direction == 1, op[entry_idx] + entry_spread, op[entry_idx])
    risk_distance = atr[signal_idx] * 1.5
    reward_distance = risk_distance * 5.0
    long_mask = direction == 1

    stop = np.empty(len(signal_idx))
    target = np.empty(len(signal_idx))
    stop[long_mask] = entry[long_mask] - risk_distance[long_mask]
    target[long_mask] = entry[long_mask] + reward_distance[long_mask]
    stop[~long_mask] = entry[~long_mask] + risk_distance[~long_mask] - entry_spread[~long_mask]
    target[~long_mask] = entry[~long_mask] - reward_distance[~long_mask] - entry_spread[~long_mask]

    highs = hi_win[entry_idx]
    lows = lo_win[entry_idx]
    hit_stop = np.where(long_mask[:, None], lows <= stop[:, None], highs >= stop[:, None])
    hit_target = np.where(long_mask[:, None], highs >= target[:, None], lows <= target[:, None])
    has_stop = hit_stop.any(axis=1)
    has_target = hit_target.any(axis=1)
    first_stop = np.where(has_stop, hit_stop.argmax(axis=1), MAX_HOLD + 1)
    first_target = np.where(has_target, hit_target.argmax(axis=1), MAX_HOLD + 1)
    offset = np.minimum(np.minimum(first_stop, first_target), MAX_HOLD)
    outcome = np.where(
        (first_stop <= first_target) & (first_stop <= MAX_HOLD),
        -1,
        np.where((first_target < first_stop) & (first_target <= MAX_HOLD), 1, 0),
    )
    exit_idx = entry_idx + offset
    r_value = np.empty(len(signal_idx))
    r_value[outcome == -1] = -1.0
    r_value[outcome == 1] = 5.0
    timed = outcome == 0
    if timed.any():
        timed_exit = exit_idx[timed]
        pnl = np.where(
            direction[timed] == 1,
            cl[timed_exit] - entry[timed],
            entry[timed] - (cl[timed_exit] + entry_spread[timed]),
        )
        r_value[timed] = pnl / risk_distance[timed]

    chosen: list[int] = []
    previous_exit = -1
    for idx in range(len(signal_idx)):
        if entry_idx[idx] > previous_exit:
            chosen.append(idx)
            previous_exit = int(exit_idx[idx])
    selected = np.asarray(chosen, dtype=int)
    reason = np.where(outcome[selected] == -1, "SL", np.where(outcome[selected] == 1, "TP", "TIME"))
    return pd.DataFrame(
        {
            "signal_time": ts[signal_idx[selected]],
            "entry_time": ts[entry_idx[selected]],
            "exit_time": ts[exit_idx[selected]],
            "direction": np.where(direction[selected] == 1, "LONG", "SHORT"),
            "r": r_value[selected],
            "reason": reason,
            "risk_pips": risk_distance[selected] / PIP_SIZE,
            "target_pips": reward_distance[selected] / PIP_SIZE,
            "spread_pips": entry_spread[selected] / PIP_SIZE,
        }
    )


def metrics(trades: pd.DataFrame) -> dict[str, float | int]:
    r = trades["r"].to_numpy(float)
    if len(r) == 0:
        return {"trades": 0}
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    equity_r = np.cumsum(r)
    drawdown_r = equity_r - np.maximum.accumulate(np.r_[0.0, equity_r])[1:]
    return {
        "trades": int(len(r)),
        "win_rate": float((r > 0).mean()),
        "profit_factor": float(wins / losses) if losses > 0 else float("inf"),
        "expectancy_r": float(r.mean()),
        "sum_r": float(r.sum()),
        "max_drawdown_r": float(-drawdown_r.min()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h1", type=Path, required=True)
    parser.add_argument("--h4", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = build_context(load_mt5(args.h1), load_mt5(args.h4))
    trades = run_selected_candidate(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(args.output_dir / "ketty_best_candidate_trades.csv", index=False)

    splits = {
        "IS_2010_2018": trades[trades["entry_time"] < "2019-01-01"],
        "VAL_2019_2022": trades[(trades["entry_time"] >= "2019-01-01") & (trades["entry_time"] < "2023-01-01")],
        "OOS_2023_2026": trades[trades["entry_time"] >= "2023-01-01"],
        "ALL": trades,
    }
    report = {name: metrics(frame) for name, frame in splits.items()}
    (args.output_dir / "ketty_best_candidate_metrics.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
