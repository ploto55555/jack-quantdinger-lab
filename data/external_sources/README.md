# External Data Sources

Mode: `personal_research_support_only`

This folder documents external historical market-data sources used by Jack Personal AI Capital OS / QuantDinger Lab.

Large raw datasets should stay local and should not be committed by default. Suggested local folders:

```text
backend_api_python/data/external/fx_1min_raw/
backend_api_python/data/processed/fx_1min/
```

## Rules

External data is only for research:

- backtesting
- candle conversion
- data inspection
- setup research
- SL / TP optimization
- daily setup reports

No script in this area should connect to broker order endpoints or place trades. Scripts may download historical files and write local CSV/JSON research outputs only.

## Current external sources

| Source | Purpose | Notes |
|---|---|---|
| `philipperemy/FX-1-Minute-Data` | Long-history M1 FX data research | HistData-based 1-minute OHLC bid quote data; requires spread/slippage caution |
