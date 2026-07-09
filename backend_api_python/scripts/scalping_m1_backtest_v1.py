"""Jack Scalping M1 Research Backtest v1.

Purpose: local historical-data research only.
This script reads local M1 OHLC CSV data, builds M5/M15/H1 context, and writes
CSV research outputs. It has no broker API code and no execution integration.

Example:
    python scripts/scalping_m1_backtest_v1.py --pair gbpjpy --input-csv data/processed/fx_1min/gbpjpy_M1_merged.csv
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd

PIP_SIZE = {"gbpjpy": 0.01, "xauusd": 0.1, "gbpusd": 0.0001, "eurusd": 0.0001}
DEFAULT_OUTPUT_DIR = Path("data/research/scalping_m1")


@dataclass
class ResearchConfig:
    pair: str
    start_equity: float = 500.0
    risk_pct: float = 0.05
    daily_target_pips: float = 50.0
    daily_loss_cap_pips: float = 30.0
    max_setups_per_day: int = 5
    sl_pips: float = 8.0
    tp_pips: float = 12.0
    session_start_hour: int = 7
    session_end_hour: int = 17


def load_m1_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    if "time" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"time": "timestamp"})
    required = ["timestamp", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 0
    return df.dropna(subset=required).sort_values("timestamp").drop_duplicates("timestamp")


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df.set_index("timestamp").resample(rule).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    return out.dropna().reset_index()


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean()
    return out


def build_context(m1: pd.DataFrame) -> pd.DataFrame:
    m5 = add_emas(resample_ohlc(m1, "5min"))
    m15 = add_emas(resample_ohlc(m1, "15min"))
    h1 = add_emas(resample_ohlc(m1, "1h"))

    def ctx(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
        cols = ["timestamp", "close", "ema20", "ema50", "ema200"]
        out = frame[cols].copy()
        for c in cols[1:]:
            out[c] = out[c].shift(1)
        return out.rename(columns={c: f"{prefix}_{c}" for c in cols[1:]})

    data = pd.merge_asof(m1, ctx(m5, "m5"), on="timestamp", direction="backward")
    data = pd.merge_asof(data, ctx(m15, "m15"), on="timestamp", direction="backward")
    data = pd.merge_asof(data, ctx(h1, "h1"), on="timestamp", direction="backward")
    return data.dropna()


def setup_label(row: pd.Series) -> str | None:
    bull = row.h1_ema20 > row.h1_ema50 > row.h1_ema200 and row.m15_ema20 > row.m15_ema50 and row.m5_ema20 > row.m5_ema50 and row.close > row.m5_ema20
    bear = row.h1_ema20 < row.h1_ema50 < row.h1_ema200 and row.m15_ema20 < row.m15_ema50 and row.m5_ema20 < row.m5_ema50 and row.close < row.m5_ema20
    if bull:
        return "trend_pullback_bullish"
    if bear:
        return "trend_pullback_bearish"
    return None


def evaluate_candidate(day_df: pd.DataFrame, idx: int, label: str, pip: float, sl_pips: float, tp_pips: float) -> float | None:
    row = day_df.iloc[idx]
    ref = float(row.close)
    future = day_df.iloc[idx + 1 : idx + 31]
    if future.empty:
        return None
    if label.endswith("bullish"):
        down_level = ref - sl_pips * pip
        up_level = ref + tp_pips * pip
        for _, item in future.iterrows():
            if float(item.low) <= down_level:
                return -sl_pips
            if float(item.high) >= up_level:
                return tp_pips
    else:
        up_level = ref + sl_pips * pip
        down_level = ref - tp_pips * pip
        for _, item in future.iterrows():
            if float(item.high) >= up_level:
                return -sl_pips
            if float(item.low) <= down_level:
                return tp_pips
    return None


def run_research(data: pd.DataFrame, config: ResearchConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    pip = PIP_SIZE.get(config.pair, 0.01)
    data = data.copy()
    data["date"] = data.timestamp.dt.date
    data["hour"] = data.timestamp.dt.hour
    data = data[(data.hour >= config.session_start_hour) & (data.hour < config.session_end_hour)]

    equity = config.start_equity
    risk_base = equity
    daily_rows = []
    candidate_rows = []

    for day, day_df in data.groupby("date"):
        day_df = day_df.reset_index(drop=True)
        day_pips = 0.0
        used = 0
        start_equity = equity
        for i, row in day_df.iterrows():
            if used >= config.max_setups_per_day or day_pips >= config.daily_target_pips or day_pips <= -abs(config.daily_loss_cap_pips):
                break
            label = setup_label(row)
            if label is None:
                continue
            result_pips = evaluate_candidate(day_df, i, label, pip, config.sl_pips, config.tp_pips)
            if result_pips is None:
                continue
            pnl = risk_base * config.risk_pct * (result_pips / config.sl_pips)
            equity += pnl
            day_pips += result_pips
            used += 1
            candidate_rows.append({
                "date": str(day),
                "timestamp": row.timestamp,
                "pair": config.pair,
                "setup_label": label,
                "result_pips": result_pips,
                "equity_after": equity,
                "risk_base": risk_base,
            })
        hit_target = day_pips >= config.daily_target_pips
        if hit_target:
            risk_base = equity
        daily_rows.append({
            "date": str(day),
            "start_equity": start_equity,
            "end_equity": equity,
            "daily_pips": day_pips,
            "setups_used": used,
            "hit_daily_target": hit_target,
            "next_day_risk_base": risk_base,
        })
    return pd.DataFrame(candidate_rows), pd.DataFrame(daily_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Jack Scalping M1 research backtest v1")
    parser.add_argument("--pair", default="gbpjpy")
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sl-pips", type=float, default=8.0)
    parser.add_argument("--tp-pips", type=float, default=12.0)
    parser.add_argument("--max-setups-per-day", type=int, default=5)
    args = parser.parse_args()

    config = ResearchConfig(pair=args.pair.lower().replace("/", ""), sl_pips=args.sl_pips, tp_pips=args.tp_pips, max_setups_per_day=args.max_setups_per_day)
    print("Jack Scalping M1 Research Backtest v1")
    print("Mode: personal_research_support_only")
    print("Broker connection: false")
    print("Execution integration: false")
    print(asdict(config))

    m1 = load_m1_csv(args.input_csv)
    context = build_context(m1)
    candidates, daily = run_research(context, config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = args.output_dir / f"{config.pair}_m1_candidates.csv"
    daily_path = args.output_dir / f"{config.pair}_m1_daily.csv"
    candidates.to_csv(candidates_path, index=False)
    daily.to_csv(daily_path, index=False)
    print(f"Wrote: {candidates_path}")
    print(f"Wrote: {daily_path}")
    if not candidates.empty:
        print({
            "candidates": int(len(candidates)),
            "win_rate": float((candidates.result_pips > 0).mean()),
            "final_equity": float(daily.end_equity.iloc[-1]) if not daily.empty else config.start_equity,
            "target_days": int(daily.hit_daily_target.sum()) if not daily.empty else 0,
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
