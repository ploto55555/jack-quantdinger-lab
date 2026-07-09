"""
Jack Personal AI Capital OS — GBPJPY v9.5 research backtest harness.

Purpose
-------
Personal research support only. This script is not auto-trading and does not place orders.

What this file does
-------------------
1. Reads HistData GBPJPY M1 Generic ASCII zip/csv files.
2. Runs a deterministic reconstructed v9.5 research engine:
   - v8.1-style Fib/S/R + red/blue trend entries
   - v9.2-style runner exit
   - v9.3 loss control: stop for the day after any trade that does not hit TP1
   - v9.5 base/attack/defense equity-compounding risk model
3. Exports trades, daily, monthly, and compound-equity CSVs.

Important
---------
This is a code-frozen research harness. Before treating multi-year results as official,
validate that this script reproduces the saved 2024 benchmark closely.
Saved 2024 benchmark from research notes:
- v9.3 pips: about +2,652.3
- v9.5 compounding: $500 -> about $103,651
- max drawdown: about -27.9%

Usage example
-------------
python scripts/research/v9_5_gbpjpy_backtest.py \
  --input DAT_ASCII_GBPJPY_M1_2021.zip DAT_ASCII_GBPJPY_M1_2022.zip DAT_ASCII_GBPJPY_M1_2023.zip \
  --outdir research_outputs/v9_5_multiyear
"""

from __future__ import annotations

import argparse
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

PIP = 0.01  # GBPJPY pip size


@dataclass
class Config:
    cost_pips: float = 1.5
    sr_tolerance_pips: float = 8.0
    fib_tolerance_pips: float = 12.0
    ema_width_min_pips: float = 15.0
    score_min: int = 5
    initial_sl_pips: float = 30.0
    tp1_pips: float = 20.0
    tp2_pips: float = 80.0
    tp1_close: float = 0.30
    tp2_close: float = 0.20
    runner_close: float = 0.50
    trail_start_pips: float = 20.0
    trail_gap_pips: float = 30.0
    strong_mfe_pips: float = 80.0
    strong_trail_gap_pips: float = 80.0
    max_hold_hours: int = 12
    max_trades_per_day: int = 4
    session_start_hour: int = 6
    session_end_hour: int = 10
    starting_equity: float = 500.0


def read_histdata_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            if not names:
                raise ValueError(f"No file found inside {path}")
            with zf.open(names[0]) as fh:
                df = pd.read_csv(
                    fh,
                    sep=";",
                    header=None,
                    names=["timestamp", "open", "high", "low", "close", "volume"],
                )
    else:
        df = pd.read_csv(path, sep=";", header=None)
        if df.shape[1] >= 6:
            df = df.iloc[:, :6]
            df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        else:
            df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y%m%d %H%M%S", errors="coerce")
    if df["timestamp"].isna().any():
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"]).copy()
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("timestamp")
    df = df.drop_duplicates("timestamp").set_index("timestamp")
    return df


def load_many(paths: Iterable[Path]) -> pd.DataFrame:
    frames = [read_histdata_file(p) for p in paths]
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    return out.dropna()


def add_context(m5: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1 = h1.copy()
    h1["ema20"] = h1["close"].ewm(span=20, adjust=False).mean()
    h1["ema50"] = h1["close"].ewm(span=50, adjust=False).mean()
    h1["ema_width_pips"] = (h1["ema20"] - h1["ema50"]).abs() / PIP
    h1["swing_high_24"] = h1["high"].rolling(24, min_periods=12).max()
    h1["swing_low_24"] = h1["low"].rolling(24, min_periods=12).min()
    h1["prev_day_high"] = h1["high"].resample("1D").max().shift(1).reindex(h1.index, method="ffill")
    h1["prev_day_low"] = h1["low"].resample("1D").min().shift(1).reindex(h1.index, method="ffill")

    m5 = m5.copy()
    m5["ema25"] = m5["close"].ewm(span=25, adjust=False).mean()
    m5["body"] = (m5["close"] - m5["open"]).abs()
    m5["upper_wick"] = m5["high"] - m5[["open", "close"]].max(axis=1)
    m5["lower_wick"] = m5[["open", "close"]].min(axis=1) - m5["low"]

    cols = [
        "ema20", "ema50", "ema_width_pips", "swing_high_24", "swing_low_24",
        "prev_day_high", "prev_day_low",
    ]
    ctx = h1[cols].reindex(m5.index, method="ffill")
    return pd.concat([m5, ctx], axis=1).dropna()


def near_level(price: float, levels: list[float], tolerance_pips: float) -> bool:
    tolerance = tolerance_pips * PIP
    return any(math.isfinite(x) and abs(price - x) <= tolerance for x in levels)


def build_candidates(m5ctx: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    rows = []
    for ts, r in m5ctx.iterrows():
        if not (cfg.session_start_hour <= ts.hour < cfg.session_end_hour):
            continue
        if r.ema_width_pips < cfg.ema_width_min_pips:
            continue
        trend = None
        if r.ema20 > r.ema50 and r.close > r.ema50:
            trend = "long"
        elif r.ema20 < r.ema50 and r.close < r.ema50:
            trend = "short"
        if trend is None:
            continue

        swing_high = r.swing_high_24
        swing_low = r.swing_low_24
        rng = swing_high - swing_low
        if rng <= 0:
            continue
        fibs = [swing_high - rng * x for x in (0.382, 0.5, 0.618)]
        sr_levels = [r.prev_day_high, r.prev_day_low, swing_high, swing_low, r.ema25]
        price = r.close

        loc_ok = near_level(price, fibs, cfg.fib_tolerance_pips) or near_level(price, sr_levels, cfg.sr_tolerance_pips)
        if not loc_ok:
            continue

        rejection = False
        if trend == "long" and r.close > r.open and r.lower_wick >= r.body * 0.5:
            rejection = True
        if trend == "short" and r.close < r.open and r.upper_wick >= r.body * 0.5:
            rejection = True
        if not rejection:
            continue

        score = 0
        score += 2 if loc_ok else 0
        score += 1 if rejection else 0
        score += 1 if r.ema_width_pips >= cfg.ema_width_min_pips else 0
        score += 1 if abs(price - r.ema25) / PIP <= 20 else 0
        if score < cfg.score_min:
            continue

        rows.append({"entry_time": ts, "side": trend, "entry": price, "score": score})
    return pd.DataFrame(rows)


def simulate_trade(m1: pd.DataFrame, entry_time: pd.Timestamp, side: str, entry: float, cfg: Config) -> dict:
    start = entry_time + pd.Timedelta(minutes=1)
    end = entry_time + pd.Timedelta(hours=cfg.max_hold_hours)
    bars = m1.loc[(m1.index >= start) & (m1.index <= end)]
    if bars.empty:
        return {}

    direction = 1 if side == "long" else -1
    sl = entry - direction * cfg.initial_sl_pips * PIP
    tp1 = entry + direction * cfg.tp1_pips * PIP
    tp2 = entry + direction * cfg.tp2_pips * PIP
    hit_tp1 = False
    hit_tp2 = False
    remaining = 1.0
    gross_pips = 0.0
    mfe = 0.0
    trail_stop: Optional[float] = None
    exit_time = bars.index[-1]
    exit_price = bars.iloc[-1].close
    reason = "max_hold"

    for ts, b in bars.iterrows():
        high = b.high
        low = b.low
        favourable_price = high if side == "long" else low
        adverse_price = low if side == "long" else high
        mfe = max(mfe, direction * (favourable_price - entry) / PIP)

        if not hit_tp1:
            if direction * (adverse_price - sl) <= 0:
                gross_pips += remaining * (-cfg.initial_sl_pips)
                exit_time, exit_price, reason = ts, sl, "sl_before_tp1"
                remaining = 0.0
                break
            if direction * (favourable_price - tp1) >= 0:
                hit_tp1 = True
                gross_pips += cfg.tp1_close * cfg.tp1_pips
                remaining -= cfg.tp1_close
                trail_stop = entry + direction * (cfg.tp1_pips - cfg.trail_gap_pips) * PIP

        if hit_tp1 and not hit_tp2:
            if direction * (favourable_price - tp2) >= 0:
                hit_tp2 = True
                gross_pips += cfg.tp2_close * cfg.tp2_pips
                remaining -= cfg.tp2_close

        if hit_tp1 and remaining > 0:
            gap = cfg.strong_trail_gap_pips if mfe >= cfg.strong_mfe_pips else cfg.trail_gap_pips
            candidate = favourable_price - direction * gap * PIP
            if trail_stop is None:
                trail_stop = candidate
            else:
                trail_stop = max(trail_stop, candidate) if side == "long" else min(trail_stop, candidate)
            if direction * (adverse_price - trail_stop) <= 0:
                runner_pips = direction * (trail_stop - entry) / PIP
                gross_pips += remaining * runner_pips
                exit_time, exit_price, reason = ts, trail_stop, "trail"
                remaining = 0.0
                break

    if remaining > 0:
        close_pips = direction * (exit_price - entry) / PIP
        gross_pips += remaining * close_pips

    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "side": side,
        "entry": entry,
        "exit": exit_price,
        "gross_pips": gross_pips,
        "net_pips": gross_pips - cfg.cost_pips,
        "mfe_pips": mfe,
        "hit_tp1": bool(hit_tp1),
        "hit_tp2": bool(hit_tp2),
        "reason": reason,
    }


def run_backtest(m1: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    m5 = resample_ohlc(m1, "5min")
    h1 = resample_ohlc(m1, "1h")
    m5ctx = add_context(m5, h1)
    candidates = build_candidates(m5ctx, cfg)
    trades = []
    stopped_days = set()
    day_counts = {}
    last_exit_by_day = {}

    for row in candidates.itertuples(index=False):
        day = row.entry_time.date()
        if day in stopped_days:
            continue
        if day_counts.get(day, 0) >= cfg.max_trades_per_day:
            continue
        if day in last_exit_by_day and row.entry_time <= last_exit_by_day[day]:
            continue
        t = simulate_trade(m1, row.entry_time, row.side, row.entry, cfg)
        if not t:
            continue
        trades.append(t)
        day_counts[day] = day_counts.get(day, 0) + 1
        last_exit_by_day[day] = t["exit_time"]
        if not t["hit_tp1"]:
            stopped_days.add(day)

    return pd.DataFrame(trades)


def apply_v95_compounding(trades: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    equity = cfg.starting_equity
    peak = equity
    consec_losses = 0
    prev_profit = False
    rows = []
    for i, r in trades.reset_index(drop=True).iterrows():
        dd = (equity / peak) - 1.0
        if dd <= -0.20 or consec_losses >= 2:
            risk = 0.025
            mode = "deep_defense"
        elif dd <= -0.10 or consec_losses >= 1:
            risk = 0.04
            mode = "defense"
        elif equity >= peak * 0.95 and prev_profit:
            risk = 0.11
            mode = "attack"
        else:
            risk = 0.05
            mode = "base"
        start_equity = equity
        return_pct = (r.net_pips / cfg.initial_sl_pips) * risk
        pnl = start_equity * return_pct
        equity = max(0.0, start_equity + pnl)
        peak = max(peak, equity)
        if pnl < 0:
            consec_losses += 1
            prev_profit = False
        else:
            consec_losses = 0
            prev_profit = True
        rows.append({**r.to_dict(), "trade_no": i + 1, "mode": mode, "risk_pct": risk, "start_equity": start_equity, "pnl_usd": pnl, "end_equity": equity, "drawdown_pct": equity / peak - 1.0})
    return pd.DataFrame(rows)


def summarize(compound: pd.DataFrame) -> dict:
    if compound.empty:
        return {}
    final_equity = compound.end_equity.iloc[-1]
    return {
        "trades": len(compound),
        "net_pips": compound.net_pips.sum(),
        "final_equity": final_equity,
        "multiple": final_equity / compound.start_equity.iloc[0],
        "max_drawdown_pct": compound.drawdown_pct.min(),
        "win_rate": (compound.net_pips > 0).mean(),
        "avg_risk_pct": compound.risk_pct.mean(),
        "max_risk_pct": compound.risk_pct.max(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True, help="HistData GBPJPY M1 zip/csv files")
    parser.add_argument("--outdir", default="research_outputs/v9_5")
    args = parser.parse_args()

    cfg = Config()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    m1 = load_many(Path(p) for p in args.input)
    trades = run_backtest(m1, cfg)
    if trades.empty:
        raise SystemExit("No trades generated. Check data and parameters.")
    compound = apply_v95_compounding(trades, cfg)
    compound["day"] = pd.to_datetime(compound.entry_time).dt.date
    compound["month"] = pd.to_datetime(compound.entry_time).dt.to_period("M").astype(str)
    daily = compound.groupby("day", as_index=False).agg(net_pips=("net_pips", "sum"), trades=("net_pips", "size"), end_equity=("end_equity", "last"))
    monthly = compound.groupby("month", as_index=False).agg(net_pips=("net_pips", "sum"), trades=("net_pips", "size"), end_equity=("end_equity", "last"))
    summary = pd.DataFrame([summarize(compound)])

    compound.to_csv(outdir / "v9_5_trades_compound.csv", index=False)
    trades.to_csv(outdir / "v9_5_trades_raw.csv", index=False)
    daily.to_csv(outdir / "v9_5_daily.csv", index=False)
    monthly.to_csv(outdir / "v9_5_monthly.csv", index=False)
    summary.to_csv(outdir / "v9_5_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(f"Saved outputs to {outdir}")


if __name__ == "__main__":
    main()
