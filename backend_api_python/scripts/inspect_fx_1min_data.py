"""Inspect HistData-style 1-minute FX files for scalping research.

Mode: personal_research_support_only

This script reads HistData Generic ASCII 1-minute files from either:
    - extracted CSV files
    - HistData ZIP files containing CSV/TXT data

Expected row format:
    YYYYMMDD HHMMSS;open;high;low;close;volume

It reports:
    - file count
    - row count
    - date range
    - missing/duplicate timestamps
    - basic OHLC sanity checks
    - estimated gap count by pair

It does not connect to a broker and it does not place trades.
"""

from __future__ import annotations

import argparse
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_INPUT_DIR = Path("data/external/fx_1min_raw")
DEFAULT_REPORT_DIR = Path("data/processed/fx_1min/reports")


@dataclass
class InspectionSummary:
    pair: str
    file_count: int
    row_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    duplicate_timestamps: int
    missing_minutes_estimate: int
    bad_ohlc_rows: int
    zero_volume_rows: int


def _normalize_histdata_frame(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y%m%d %H%M%S", errors="coerce")
    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    return df.dropna(subset=["timestamp", "open", "high", "low", "close"])


def _read_histdata_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep=";",
        header=None,
        names=["timestamp", "open", "high", "low", "close", "volume"],
    )
    return _normalize_histdata_frame(df)


def _read_histdata_zip(path: Path) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            lower = member.lower()
            if not (lower.endswith(".csv") or lower.endswith(".txt")):
                continue
            with archive.open(member) as handle:
                df = pd.read_csv(
                    handle,
                    sep=";",
                    header=None,
                    names=["timestamp", "open", "high", "low", "close", "volume"],
                )
            df = _normalize_histdata_frame(df)
            if not df.empty:
                df["source_file"] = f"{path}!{member}"
                frames.append(df)
    return frames


def _iter_data_files(pair_dir: Path) -> Iterable[Path]:
    patterns = ["*.csv", "*.txt", "*.zip"]
    for pattern in patterns:
        yield from pair_dir.rglob(pattern)


def inspect_pair(pair: str, input_dir: Path) -> tuple[InspectionSummary, pd.DataFrame]:
    pair = pair.lower().replace("/", "")
    pair_dir = input_dir / pair
    files = sorted(set(_iter_data_files(pair_dir)))

    frames: list[pd.DataFrame] = []
    for file_path in files:
        try:
            if file_path.suffix.lower() == ".zip":
                frames.extend(_read_histdata_zip(file_path))
            else:
                frame = _read_histdata_csv(file_path)
                frame["source_file"] = str(file_path)
                frames.append(frame)
        except Exception as exc:
            print(f"WARNING: failed to read {file_path}: {exc}")

    if not frames:
        summary = InspectionSummary(
            pair=pair,
            file_count=len(files),
            row_count=0,
            first_timestamp=None,
            last_timestamp=None,
            duplicate_timestamps=0,
            missing_minutes_estimate=0,
            bad_ohlc_rows=0,
            zero_volume_rows=0,
        )
        return summary, pd.DataFrame()

    df = pd.concat(frames, ignore_index=True).sort_values("timestamp")
    duplicate_timestamps = int(df.duplicated(subset=["timestamp"]).sum())
    df = df.drop_duplicates(subset=["timestamp"], keep="last")

    bad_ohlc = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    bad_ohlc_rows = int(bad_ohlc.sum())

    minute_diffs = df["timestamp"].diff().dropna().dt.total_seconds().div(60)
    missing_minutes_estimate = int(minute_diffs[minute_diffs > 1].sub(1).sum()) if not minute_diffs.empty else 0

    summary = InspectionSummary(
        pair=pair,
        file_count=len(files),
        row_count=len(df),
        first_timestamp=df["timestamp"].min().isoformat() if len(df) else None,
        last_timestamp=df["timestamp"].max().isoformat() if len(df) else None,
        duplicate_timestamps=duplicate_timestamps,
        missing_minutes_estimate=missing_minutes_estimate,
        bad_ohlc_rows=bad_ohlc_rows,
        zero_volume_rows=int((df["volume"] == 0).sum()),
    )
    return summary, df


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect downloaded FX M1 data quality.")
    parser.add_argument("--pairs", required=True, help="Comma-separated pair codes, e.g. gbpjpy,xauusd")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--write-merged", action="store_true", help="Write merged normalized M1 CSV files.")
    args = parser.parse_args()

    args.report_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []

    print("Jack FX M1 Data Inspector")
    print("Mode: personal_research_support_only")
    print("Broker connection: false")
    print("Order actions: false")

    for pair in [item.strip().lower().replace("/", "") for item in args.pairs.split(",") if item.strip()]:
        summary, df = inspect_pair(pair, args.input_dir)
        summaries.append(asdict(summary))
        print(asdict(summary))

        if args.write_merged and not df.empty:
            out_path = args.report_dir.parent / f"{pair}_M1_merged.csv"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(out_path, index=False)
            print(f"Wrote merged file: {out_path}")

    summary_df = pd.DataFrame(summaries)
    summary_path = args.report_dir / "fx_1min_inspection_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"Wrote report: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
