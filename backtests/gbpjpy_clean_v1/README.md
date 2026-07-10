# GBPJPY Backtest Clean V1

Personal research support only. This engine does not place orders.

## Frozen rules

- Symbol: GBPJPY
- Source data: M1 OHLCV
- Direction: previous completed H1 candle, close > EMA50 > EMA200 for long; close < EMA50 < EMA200 for short
- Entry: M5 EMA20 pullback and reclaim/break confirmation
- Entry fill: next available M1 open after the completed M5 signal candle
- Initial stop: 30 pips
- TP1: +20 pips, close 30%
- TP2: +80 pips, close another 20%
- Runner: final 50%
- Runner trailing after TP1: 30-pip gap; once MFE >= 80 pips, gap becomes 80 pips
- Cost: 1.5 pips per complete trade
- If a completed trade never hits TP1, no more entries on that calendar date
- Risk: 5% of equity per trade
- One open trade at a time
- Intrabar ambiguity: adverse outcome is processed first

## Expected input columns

`timestamp, open, high, low, close, volume`

The timestamp must be parseable by pandas. Data is sorted and duplicate timestamps are removed by the engine.

## Run 2024 first

From the repository root:

```powershell
cd backtests\gbpjpy_clean_v1
python -m pip install -r requirements.txt
python run_backtest.py --input "C:\PATH\GBPJPY_M1_2024_normalized.csv.gz" --output outputs\2024
```

## Output files

- `trades.csv`
- `daily.csv`
- `monthly.csv`
- `summary.csv`
- `compound_5pct.csv`

The script also writes `run_manifest.json`, containing the settings and SHA-256 hash of the input file for reproducibility.

## Stability check

Run the same command twice into two different output folders. The five CSV files should have identical SHA-256 hashes. Do not run 2002-2024 until the 2024 output passes logical and reconciliation checks.
