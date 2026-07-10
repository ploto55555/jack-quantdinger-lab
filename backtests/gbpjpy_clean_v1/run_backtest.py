from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Config:
    strategy_id: str = "CLEAN_V1_M5_EMA20_PULLBACK"
    symbol: str = "GBPJPY"
    pip_size: float = 0.01
    starting_equity: float = 500.0
    risk_pct: float = 0.05
    sl_pips: float = 30.0
    tp1_pips: float = 20.0
    tp2_pips: float = 80.0
    tp1_close_pct: float = 0.30
    tp2_close_pct: float = 0.20
    runner_pct: float = 0.50
    trailing_gap_before_80: float = 30.0
    trailing_gap_after_80: float = 80.0
    cost_pips: float = 1.5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_m1(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[required].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    invalid = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    )
    if invalid.any():
        raise ValueError(f"Invalid OHLC rows found: {int(invalid.sum())}")
    return df.set_index("timestamp")


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    bars = df.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    return bars.dropna(subset=["open", "high", "low", "close"])


def make_signals(m1: pd.DataFrame) -> pd.DataFrame:
    h1 = resample_ohlcv(m1, "1h")
    h1["ema50"] = h1["close"].ewm(span=50, adjust=False).mean()
    h1["ema200"] = h1["close"].ewm(span=200, adjust=False).mean()
    h1["direction"] = np.select(
        [
            (h1["close"] > h1["ema50"]) & (h1["ema50"] > h1["ema200"]),
            (h1["close"] < h1["ema50"]) & (h1["ema50"] < h1["ema200"]),
        ],
        [1, -1],
        default=0,
    )
    # H1 direction becomes available only after the candle has completed.
    h1_direction = h1[["direction"]].copy()
    h1_direction.index = h1_direction.index + pd.Timedelta(hours=1)

    m5 = resample_ohlcv(m1, "5min")
    m5["ema20"] = m5["close"].ewm(span=20, adjust=False).mean()
    m5["ema50"] = m5["close"].ewm(span=50, adjust=False).mean()
    m5["prev_high"] = m5["high"].shift(1)
    m5["prev_low"] = m5["low"].shift(1)

    available_time = m5.index + pd.Timedelta(minutes=5)
    signal_frame = m5.reset_index().rename(columns={"timestamp": "bar_start"})
    signal_frame["signal_time"] = available_time.to_numpy()
    signal_frame = pd.merge_asof(
        signal_frame.sort_values("signal_time"),
        h1_direction.reset_index().rename(columns={"timestamp": "signal_time"}).sort_values("signal_time"),
        on="signal_time",
        direction="backward",
    )

    long_signal = (
        (signal_frame["direction"] == 1)
        & (signal_frame["ema20"] > signal_frame["ema50"])
        & (signal_frame["low"] <= signal_frame["ema20"])
        & (signal_frame["close"] > signal_frame["ema20"])
        & (signal_frame["close"] > signal_frame["prev_high"])
    )
    short_signal = (
        (signal_frame["direction"] == -1)
        & (signal_frame["ema20"] < signal_frame["ema50"])
        & (signal_frame["high"] >= signal_frame["ema20"])
        & (signal_frame["close"] < signal_frame["ema20"])
        & (signal_frame["close"] < signal_frame["prev_low"])
    )
    signal_frame["side"] = np.select([long_signal, short_signal], [1, -1], default=0)
    return signal_frame.loc[signal_frame["side"] != 0, ["signal_time", "bar_start", "side"]]


def simulate_trade(
    m1: pd.DataFrame,
    entry_pos: int,
    side: int,
    cfg: Config,
) -> dict:
    entry_time = m1.index[entry_pos]
    entry_price = float(m1.iloc[entry_pos]["open"])
    pip = cfg.pip_size
    sl_price = entry_price - side * cfg.sl_pips * pip
    tp1_price = entry_price + side * cfg.tp1_pips * pip
    tp2_price = entry_price + side * cfg.tp2_pips * pip

    tp1_hit = False
    tp2_hit = False
    tp1_time = pd.NaT
    tp2_time = pd.NaT
    highest = entry_price
    lowest = entry_price
    mfe_pips = 0.0
    mae_pips = 0.0
    realized_weighted_pips = 0.0
    remaining = 1.0
    runner_stop = np.nan
    exit_time = entry_time
    exit_price = entry_price
    exit_reason = "end_of_data"

    for pos in range(entry_pos, len(m1)):
        row = m1.iloc[pos]
        ts = m1.index[pos]
        high = float(row["high"])
        low = float(row["low"])
        highest = max(highest, high)
        lowest = min(lowest, low)

        if side == 1:
            mfe_pips = max(mfe_pips, (highest - entry_price) / pip)
            mae_pips = max(mae_pips, (entry_price - lowest) / pip)
        else:
            mfe_pips = max(mfe_pips, (entry_price - lowest) / pip)
            mae_pips = max(mae_pips, (highest - entry_price) / pip)

        adverse_touch = low <= sl_price if side == 1 else high >= sl_price
        tp1_touch = high >= tp1_price if side == 1 else low <= tp1_price
        tp2_touch = high >= tp2_price if side == 1 else low <= tp2_price

        # Before TP1, initial stop is always processed first for conservative ambiguity handling.
        if not tp1_hit:
            if adverse_touch:
                realized_weighted_pips += -cfg.sl_pips * remaining
                exit_time, exit_price, exit_reason = ts, sl_price, "initial_sl"
                remaining = 0.0
                break
            if tp1_touch:
                tp1_hit = True
                tp1_time = ts
                realized_weighted_pips += cfg.tp1_pips * cfg.tp1_close_pct
                remaining -= cfg.tp1_close_pct
                gap = (
                    cfg.trailing_gap_after_80
                    if mfe_pips >= 80.0
                    else cfg.trailing_gap_before_80
                )
                runner_stop = (
                    highest - gap * pip if side == 1 else lowest + gap * pip
                )

        if tp1_hit and remaining > 0:
            gap = (
                cfg.trailing_gap_after_80
                if mfe_pips >= 80.0
                else cfg.trailing_gap_before_80
            )
            candidate = highest - gap * pip if side == 1 else lowest + gap * pip
            if np.isnan(runner_stop):
                runner_stop = candidate
            elif side == 1:
                runner_stop = max(runner_stop, candidate)
            else:
                runner_stop = min(runner_stop, candidate)

            trailing_touch = low <= runner_stop if side == 1 else high >= runner_stop

            # After TP1, trailing stop is processed before TP2 when both occur in one M1 bar.
            if trailing_touch:
                runner_pips = side * (runner_stop - entry_price) / pip
                realized_weighted_pips += runner_pips * remaining
                exit_time, exit_price, exit_reason = ts, runner_stop, "trailing_stop"
                remaining = 0.0
                break

            if (not tp2_hit) and tp2_touch:
                tp2_hit = True
                tp2_time = ts
                realized_weighted_pips += cfg.tp2_pips * cfg.tp2_close_pct
                remaining -= cfg.tp2_close_pct

        exit_time, exit_price = ts, float(row["close"])

    if remaining > 0:
        end_pips = side * (exit_price - entry_price) / pip
        realized_weighted_pips += end_pips * remaining

    gross_pips = realized_weighted_pips
    net_pips = gross_pips - cfg.cost_pips
    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "direction": "LONG" if side == 1 else "SHORT",
        "entry_price": entry_price,
        "initial_sl": sl_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "tp1_hit": bool(tp1_hit),
        "tp1_time": tp1_time,
        "tp2_hit": bool(tp2_hit),
        "tp2_time": tp2_time,
        "mfe_pips": mfe_pips,
        "mae_pips": mae_pips,
        "runner_exit_price": exit_price,
        "runner_exit_reason": exit_reason,
        "gross_pips": gross_pips,
        "cost_pips": cfg.cost_pips,
        "net_pips": net_pips,
        "exit_pos": int(m1.index.get_loc(exit_time)),
    }


def run_engine(m1: pd.DataFrame, signals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    records: list[dict] = []
    equity = cfg.starting_equity
    blocked_dates: set = set()
    next_free_pos = 0

    for signal in signals.itertuples(index=False):
        signal_time = pd.Timestamp(signal.signal_time)
        entry_pos = int(m1.index.searchsorted(signal_time, side="left"))
        if entry_pos >= len(m1) or entry_pos < next_free_pos:
            continue

        entry_date = m1.index[entry_pos].date()
        if entry_date in blocked_dates:
            continue

        trade = simulate_trade(m1, entry_pos, int(signal.side), cfg)
        trade_id = len(records) + 1
        equity_before = equity
        risk_amount = equity_before * cfg.risk_pct
        net_r = trade["net_pips"] / cfg.sl_pips
        pnl_amount = risk_amount * net_r
        equity = equity_before + pnl_amount
        stop_for_day = not trade["tp1_hit"]
        if stop_for_day:
            blocked_dates.add(entry_date)

        trade.update(
            {
                "trade_id": trade_id,
                "signal_time": signal_time,
                "risk_pct": cfg.risk_pct,
                "risk_amount": risk_amount,
                "equity_before": equity_before,
                "net_r_multiple": net_r,
                "pnl_amount": pnl_amount,
                "equity_after": equity,
                "stop_for_day_triggered": stop_for_day,
            }
        )
        next_free_pos = trade.pop("exit_pos") + 1
        records.append(trade)

    return pd.DataFrame(records)


def max_drawdown(equity: pd.Series) -> tuple[float, float]:
    if equity.empty:
        return 0.0, 0.0
    peaks = equity.cummax()
    dd_amount = equity - peaks
    dd_pct = dd_amount / peaks.replace(0, np.nan)
    return float(dd_pct.min() * 100), float(dd_amount.min())


def build_outputs(trades: pd.DataFrame, cfg: Config) -> dict[str, pd.DataFrame]:
    if trades.empty:
        empty = pd.DataFrame()
        summary = pd.DataFrame(
            [{
                "strategy_id": cfg.strategy_id,
                "symbol": cfg.symbol,
                "starting_equity": cfg.starting_equity,
                "final_equity": cfg.starting_equity,
                "total_trades": 0,
            }]
        )
        return {
            "trades.csv": empty,
            "daily.csv": empty,
            "monthly.csv": empty,
            "summary.csv": summary,
            "compound_5pct.csv": empty,
        }

    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades["year_month"] = pd.to_datetime(trades["entry_time"]).dt.to_period("M").astype(str)
    trades["is_win"] = trades["pnl_amount"] > 0

    daily = trades.groupby("date", sort=True).agg(
        starting_equity=("equity_before", "first"),
        ending_equity=("equity_after", "last"),
        trade_count=("trade_id", "count"),
        winning_trades=("is_win", "sum"),
        gross_pips=("gross_pips", "sum"),
        cost_pips=("cost_pips", "sum"),
        net_pips=("net_pips", "sum"),
        pnl_amount=("pnl_amount", "sum"),
        tp1_failure_stop=("stop_for_day_triggered", "max"),
    ).reset_index()
    daily["losing_trades"] = daily["trade_count"] - daily["winning_trades"]
    daily["return_pct"] = daily["pnl_amount"] / daily["starting_equity"] * 100

    monthly_rows = []
    for month, group in trades.groupby("year_month", sort=True):
        dd_pct, _ = max_drawdown(group["equity_after"])
        wins = int(group["is_win"].sum())
        monthly_rows.append(
            {
                "year_month": month,
                "starting_equity": group.iloc[0]["equity_before"],
                "ending_equity": group.iloc[-1]["equity_after"],
                "trade_count": len(group),
                "winning_trades": wins,
                "losing_trades": len(group) - wins,
                "win_rate": wins / len(group) * 100,
                "net_pips": group["net_pips"].sum(),
                "pnl_amount": group["pnl_amount"].sum(),
                "return_pct": group["pnl_amount"].sum() / group.iloc[0]["equity_before"] * 100,
                "max_drawdown_pct": dd_pct,
            }
        )
    monthly = pd.DataFrame(monthly_rows)

    wins = trades.loc[trades["pnl_amount"] > 0, "pnl_amount"]
    losses = trades.loc[trades["pnl_amount"] < 0, "pnl_amount"]
    profit_factor = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.inf
    dd_pct, dd_amount = max_drawdown(trades["equity_after"])
    summary = pd.DataFrame(
        [{
            "strategy_id": cfg.strategy_id,
            "symbol": cfg.symbol,
            "start_date": trades["entry_time"].min(),
            "end_date": trades["exit_time"].max(),
            "starting_equity": cfg.starting_equity,
            "final_equity": trades.iloc[-1]["equity_after"],
            "total_return_pct": (trades.iloc[-1]["equity_after"] / cfg.starting_equity - 1) * 100,
            "total_trades": len(trades),
            "wins": int((trades["pnl_amount"] > 0).sum()),
            "losses": int((trades["pnl_amount"] <= 0).sum()),
            "win_rate": float((trades["pnl_amount"] > 0).mean() * 100),
            "tp1_hit_rate": float(trades["tp1_hit"].mean() * 100),
            "net_pips": trades["net_pips"].sum(),
            "profit_factor": profit_factor,
            "average_trade_pips": trades["net_pips"].mean(),
            "average_win_pips": trades.loc[trades["net_pips"] > 0, "net_pips"].mean(),
            "average_loss_pips": trades.loc[trades["net_pips"] <= 0, "net_pips"].mean(),
            "max_drawdown_pct": dd_pct,
            "max_drawdown_amount": dd_amount,
            "best_trade_pips": trades["net_pips"].max(),
            "worst_trade_pips": trades["net_pips"].min(),
            "best_day_pct": daily["return_pct"].max(),
            "worst_day_pct": daily["return_pct"].min(),
        }]
    )

    compound = trades[
        [
            "trade_id", "entry_time", "risk_pct", "equity_before", "risk_amount",
            "net_r_multiple", "pnl_amount", "equity_after",
        ]
    ].copy()
    compound["equity_peak"] = compound["equity_after"].cummax()
    compound["drawdown_pct"] = (
        compound["equity_after"] / compound["equity_peak"] - 1
    ) * 100

    trades_export = trades.drop(columns=["date", "year_month", "is_win"])
    return {
        "trades.csv": trades_export,
        "daily.csv": daily,
        "monthly.csv": monthly,
        "summary.csv": summary,
        "compound_5pct.csv": compound,
    }


def validate_outputs(outputs: dict[str, pd.DataFrame]) -> None:
    trades = outputs["trades.csv"]
    if trades.empty:
        return
    if not np.allclose(trades["gross_pips"] - trades["cost_pips"], trades["net_pips"]):
        raise AssertionError("gross_pips - cost_pips does not reconcile to net_pips")
    if not np.allclose(trades["equity_before"] + trades["pnl_amount"], trades["equity_after"]):
        raise AssertionError("Trade equity does not reconcile")
    daily = outputs["daily.csv"]
    if not np.isclose(daily["pnl_amount"].sum(), trades["pnl_amount"].sum()):
        raise AssertionError("Daily PnL does not reconcile to trades")
    monthly = outputs["monthly.csv"]
    if not np.isclose(monthly["pnl_amount"].sum(), trades["pnl_amount"].sum()):
        raise AssertionError("Monthly PnL does not reconcile to trades")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GBPJPY Clean V1 backtest")
    parser.add_argument("--input", required=True, type=Path, help="M1 CSV or CSV.GZ path")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--starting-equity", type=float, default=500.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(starting_equity=args.starting_equity)
    args.output.mkdir(parents=True, exist_ok=True)

    m1 = load_m1(args.input)
    signals = make_signals(m1)
    trades = run_engine(m1, signals, cfg)
    outputs = build_outputs(trades, cfg)
    validate_outputs(outputs)

    hashes = {}
    for filename, frame in outputs.items():
        path = args.output / filename
        frame.to_csv(path, index=False, float_format="%.10f", date_format="%Y-%m-%d %H:%M:%S")
        hashes[filename] = sha256_file(path)

    manifest = {
        "config": asdict(cfg),
        "input_path": str(args.input.resolve()),
        "input_sha256": sha256_file(args.input),
        "input_rows": int(len(m1)),
        "input_start": str(m1.index.min()),
        "input_end": str(m1.index.max()),
        "signal_count": int(len(signals)),
        "trade_count": int(len(trades)),
        "output_sha256": hashes,
    }
    with (args.output / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
