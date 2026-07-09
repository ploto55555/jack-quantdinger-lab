# Jack Personal AI Capital OS — v9.5 Safer 100k Model

This document freezes the current research setup so future testing does not silently change the rules.

Personal research support only. This is not auto-trading and does not place orders.

---

## Saved Setup Name

**GBPJPY v9.5 Base-Attack-Defense**

---

## Backtest Base

- Pair: GBPJPY
- Data source: HistData Generic ASCII M1
- Cost assumption: 1.5 pips
- Compounding: trade-by-trade percentage of current equity
- Starting capital: 500 USD

---

## Entry Logic

### v8.1 Core

Use:

- Fib + support/resistance location
- Red / Blue trend regime only
- Green range regime is skipped for now

Meaning:

- Red = uptrend pullback long
- Blue = downtrend pullback short
- Green = range, do not trade for this saved setup

---

## Exit Logic

### v9.2 Runner Capture

- Initial SL: 30 pips
- TP1: +20 pips, close 30%
- TP2: +80 pips, close 20%
- Runner: remaining 50%
- Trailing starts after +20 pips
- Normal trailing gap: 30 pips
- If MFE reaches +80 pips, widen runner trailing gap to 80 pips
- Max hold: 12 hours

---

## Loss Control

### v9.3 Rule

If any trade does **not** hit TP1 +20 pips, stop trading for that day.

Purpose:

- Avoid low-momentum days
- Avoid repeated entries in bad conditions
- Reduce oversized daily losses

Saved benchmark improvement:

- v9.2: about +2,445.8 pips, max daily loss about -54.0 pips
- v9.3: about +2,652.3 pips, max daily loss about -31.5 pips

---

## Risk Model

### v9.5 Safer 100k Model

Base mode:

- Risk 5%

Attack mode:

- Risk 11%
- Conditions:
  1. Current equity is close to peak equity
  2. Equity >= 95% of peak equity
  3. Previous trade was profitable
  4. System is not in drawdown mode

Defense mode 1:

- Risk 4%
- Conditions:
  1. Drawdown is worse than -10%, or
  2. Previous trade was a loss

Defense mode 2:

- Risk 2.5%
- Conditions:
  1. Drawdown is worse than -20%, or
  2. There are two consecutive losses

---

## Saved 2024 Benchmark

Using GBPJPY 2024 M1 historical data:

- Starting capital: 500 USD
- Final capital: about 103,651 USD
- Multiple: about 207x
- Maximum drawdown: about -27.9%
- Worst month: about -14.7%
- Average risk: about 5.72%
- Maximum risk: 11%

Comparison:

| Model | Final Equity | Multiple | Max Drawdown | Worst Month |
|---|---:|---:|---:|---:|
| Fixed 5% | about 21,080 USD | 42x | -30.4% | -19.8% |
| Fixed 7.4% | about 99,969 USD | 200x | -42.0% | -28.3% |
| v9.5 Safer Model | about 103,651 USD | 207x | -27.9% | -14.7% |

---

## Validation Flow

Do not trust multi-year results until the script can reproduce the 2024 benchmark closely.

Required sequence:

1. Run `scripts/research/v9_5_gbpjpy_backtest.py` on 2024 data.
2. Compare output with the saved 2024 benchmark.
3. If 2024 is close enough, freeze the code version.
4. Run the same frozen script on 2021, 2022, and 2023 without changing parameters.
5. Only then summarize multi-year pass/fail.

---

## CLI Example

```bash
python scripts/research/v9_5_gbpjpy_backtest.py \
  --input DAT_ASCII_GBPJPY_M1_2024.zip \
  --outdir research_outputs/v9_5_2024
```

For multiple years:

```bash
python scripts/research/v9_5_gbpjpy_backtest.py \
  --input DAT_ASCII_GBPJPY_M1_2021.zip DAT_ASCII_GBPJPY_M1_2022.zip DAT_ASCII_GBPJPY_M1_2023.zip \
  --outdir research_outputs/v9_5_2021_2023
```

---

## One-Line Summary

v9.5 combines v8.1 Fib/SR trend entries, v9.2 runner exits, v9.3 loss control, and adaptive 5% / 11% / 4% / 2.5% risk management to research a possible 500 USD to 100k USD path while avoiding fixed high-risk compounding.
