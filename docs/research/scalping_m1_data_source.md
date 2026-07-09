# Scalping M1 External Data Source Research

Project: Jack Personal AI Capital OS / QuantDinger Lab

Mode: `personal_research_support_only`

This document records an external historical 1-minute FX data source for scalping research. It is for research, backtesting, data inspection, and strategy analysis only.

## Source

- Repository: `philipperemy/FX-1-Minute-Data`
- Pair list: `pairs.csv`
- README notes that the dataset/API is based on HistData and supports 1-minute FX data.
- README notes the Generic ASCII 1-minute format has no header and uses semicolon-separated columns:
  - `DateTime Stamp`
  - `Bar OPEN Bid Quote`
  - `Bar HIGH Bid Quote`
  - `Bar LOW Bid Quote`
  - `Bar CLOSE Bid Quote`
  - `Volume`
- README notes timezone is EST without daylight-saving adjustment.

## Pairs relevant to Jack's current scalping research

From `pairs.csv`:

| Display pair | Code | First history month |
|---|---:|---:|
| GBP/JPY | `gbpjpy` | 200205 |
| GBP/USD | `gbpusd` | 200005 |
| EUR/USD | `eurusd` | 200005 |
| XAU/USD | `xauusd` | 200903 |

## Why this matters

The current Jack scalping research needs longer M1/M5 coverage because the uploaded GBPJPY M1 data only covered a short recent window. H1 or M5-only testing is too rough for scalping. M1 is needed to research:

- London / New York open scalping
- M1 entry precision
- M5 setup confirmation
- M15/H1 direction filter
- SL tests: 5 / 8 / 10 / 12 / 15 pips
- TP tests: 8 / 12 / 15 / 20 / 30 / 50 pips
- Daily target: +50 pips
- Runner logic after +50 pips
- 5% risk research model

## Important limitations

This dataset is useful, but it is not the same as live broker execution.

Known limitations to track before trusting any scalping result:

1. The 1-minute OHLC data is bid quote based, not full bid/ask execution.
2. Real spread is not guaranteed to be present.
3. Slippage is not included unless the backtest adds a conservative buffer.
4. Scalping backtests can look too good if spread and slippage are ignored.
5. Timezone is EST without daylight-saving adjustment; session mapping must be handled carefully.
6. Historical data quality must be inspected for missing minutes and gaps.

## Safety boundary

This work must never add broker-order actions.

Allowed:

- download historical data
- inspect data quality
- convert files into local research format
- run backtests
- generate daily setup reports
- generate risk / SL / TP research tables

Not allowed:

- auto trading
- broker order placement
- live execution
- signal-to-order automation
- hidden order routing

## Next research steps

1. Download M1 data for GBPJPY first.
2. Inspect data range, gaps, timezone, and OHLC format.
3. Convert raw HistData CSV into Jack standard candles.
4. Build M5 / M15 / H1 from M1 locally.
5. Run `Scalping M1 Backtest v1`:
   - pair: GBPJPY
   - primary setup: M5 trend pullback + M1 entry trigger
   - secondary setup: London sweep / breakout retest
   - risk model: 5% per S setup only
   - daily target: +50 pips
   - if daily target hit, next day compounding lot size increases
   - if losing day, next day maintains previous lot size

## Current research naming

Use this naming for future docs and APIs:

`Jack Scalping 50 Pips M1 Research v1`
