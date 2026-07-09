"""Download historical FX 1-minute data for scalping research.

Mode: personal_research_support_only

This script uses the public `histdata` Python package referenced by
philipperemy/FX-1-Minute-Data. It downloads historical 1-minute OHLC files
for research/backtesting only. It does not connect to a broker and it does
not place trades.

Install dependency locally if needed:
    pip install histdata

Examples:
    python scripts/download_fx_1min_data.py --pairs gbpjpy --start-year 2020 --end-year 2024
    python scripts/download_fx_1min_data.py --pairs gbpjpy,xauusd,gbpusd,eurusd --start-year 2022 --end-year 2024

Notes:
    - HistData files are typically monthly ZIP files.
    - Download behavior is handled by the histdata package.
    - The default output folder is local and should not be committed.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ALLOWED_PAIRS = {
    "gbpjpy",
    "xauusd",
    "gbpusd",
    "eurusd",
}

DEFAULT_OUTPUT_DIR = Path("data/external/fx_1min_raw")


@dataclass(frozen=True)
class DownloadJob:
    pair: str
    year: int
    month: int


def _parse_pairs(value: str) -> list[str]:
    pairs = [item.strip().lower().replace("/", "") for item in value.split(",") if item.strip()]
    unknown = sorted(set(pairs) - ALLOWED_PAIRS)
    if unknown:
        raise ValueError(f"Unsupported pair(s): {unknown}. Allowed: {sorted(ALLOWED_PAIRS)}")
    return pairs


def _iter_jobs(pairs: Iterable[str], start_year: int, end_year: int, start_month: int, end_month: int) -> Iterable[DownloadJob]:
    for pair in pairs:
        for year in range(start_year, end_year + 1):
            first_month = start_month if year == start_year else 1
            last_month = end_month if year == end_year else 12
            for month in range(first_month, last_month + 1):
                yield DownloadJob(pair=pair, year=year, month=month)


def download_job(job: DownloadJob, output_dir: Path) -> None:
    try:
        from histdata import download_hist_data as dl  # type: ignore
        from histdata.api import Platform as P, TimeFrame as TF  # type: ignore
    except Exception as exc:  # pragma: no cover - user environment dependent
        raise RuntimeError(
            "Missing dependency `histdata`. Install it with: pip install histdata"
        ) from exc

    pair_dir = output_dir / job.pair
    pair_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {job.pair} {job.year}-{job.month:02d} M1 data...")
    # The histdata package manages the remote download and extraction behavior.
    # We keep the call simple and explicit for reproducibility.
    dl(
        year=str(job.year),
        month=str(job.month),
        pair=job.pair,
        platform=P.GENERIC_ASCII,
        time_frame=TF.ONE_MINUTE,
        output_directory=str(pair_dir),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download FX 1-minute data for Jack scalping research.")
    parser.add_argument("--pairs", required=True, help="Comma-separated pair codes, e.g. gbpjpy,xauusd")
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--end-month", type=int, default=12)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Print jobs without downloading.")
    args = parser.parse_args()

    if args.start_year > args.end_year:
        raise ValueError("start-year must be <= end-year")
    if not (1 <= args.start_month <= 12 and 1 <= args.end_month <= 12):
        raise ValueError("Months must be between 1 and 12")

    pairs = _parse_pairs(args.pairs)
    jobs = list(_iter_jobs(pairs, args.start_year, args.end_year, args.start_month, args.end_month))

    print("Jack FX M1 Data Downloader")
    print("Mode: personal_research_support_only")
    print("Broker connection: false")
    print("Order actions: false")
    print(f"Output directory: {args.output_dir}")
    print(f"Jobs: {len(jobs)}")

    if args.dry_run:
        for job in jobs:
            print(f"DRY RUN {job.pair} {job.year}-{job.month:02d}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for job in jobs:
        try:
            download_job(job, args.output_dir)
        except Exception as exc:  # pragma: no cover - network/user environment dependent
            msg = f"FAILED {job.pair} {job.year}-{job.month:02d}: {exc}"
            failures.append(msg)
            print(msg, file=sys.stderr)

    if failures:
        print("Some downloads failed:")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
