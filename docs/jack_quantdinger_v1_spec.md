# Jack QuantDinger v1 — Personal Backtest OS Spec

## 1. Product direction

Jack QuantDinger is not a SaaS trading platform. It is a personal backtest and strategy review system for Jack.

Core workflow:

```text
Strategy discussion with ChatGPT
→ copy a clean strategy prompt into Jack QuantDinger
→ generate or paste Python strategy code
→ run 10+ years of backtest
→ get result immediately
→ review result with ChatGPT
→ create v2 / v3 / v4 strategy versions
→ build Snowball System memory over time
```

Primary goal:

```text
Make strategy testing fast, repeatable, and reviewable.
```

Not v1 goals:

```text
No live trading
No broker execution
No SaaS billing
No multi-user permissions
No public customer product
No autonomous AI trading
```

---

## 2. What to copy from QuantDinger

Use QuantDinger as reference for the useful workflow, not as a full product to clone.

Keep / rebuild:

```text
Strategy Lab
Backtest Engine
Backtest Result Dashboard
Trade List
Equity Curve
Strategy Version History
Historical Data Store
```

Remove / avoid in v1:

```text
Top Up / Credits
SaaS billing
Public user accounts
Live execution
Broker connection
Complex admin
AI token dependency from QuantDinger
```

AI should use Jack's own API key later, for example environment variables such as:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

Backtest itself must not require AI.

---

## 3. v1 core modules

### 3.1 Data Center

Purpose: store at least 10 years of OHLCV candles locally so backtests are fast and do not depend on external API calls every run.

Tables / storage concepts:

```text
symbols
candles
import_jobs
data_quality_reports
```

Minimum symbols:

```text
Forex / Gold:
EURUSD
GBPUSD
USDJPY
GBPJPY
XAUUSD

ETF / Stocks:
SPY
QQQ
TSLA
NVDA
AAPL
MSFT

Macro later:
DXY
US10Y
VIX
```

Minimum timeframes:

```text
Daily
H4
H1
```

Later:

```text
M15
M5
```

Data source plan:

```text
Phase 1 stocks / ETF: Yahoo-style source for quick testing
Phase 1 FX / Gold: Twelve Data / OANDA / Dukascopy-style source
Phase 2 professional: Polygon / FMP / broker data
```

Data rule:

```text
Backtest reads local database only.
External API is used for import/update, not every backtest run.
```

---

### 3.2 Strategy Prompt Lab

Purpose: Jack copies a prompt from ChatGPT or writes his own strategy idea.

Fields:

```text
Strategy name
Market
Symbol
Timeframe
Data range
Core idea
Entry rules
Exit rules
Stop loss
Take profit
Risk model
Filters
Backtest requirements
Output requirements
```

v1 can support two modes:

```text
Mode A: Paste Python strategy code manually
Mode B: Paste strategy prompt, then use Jack's own AI API key to generate code
```

Mode A comes first because it is simpler and no token is needed.

---

### 3.3 Code Editor

Purpose: display and edit generated Python strategy code.

Minimum features:

```text
Syntax-highlighted Python editor
Save strategy version
Check code
Run backtest
```

Safety rules:

```text
No network calls from strategy code
No broker calls from strategy code
No file deletion
No OS command execution
Backtest sandbox only
```

---

### 3.4 Backtest Engine

Purpose: run deterministic 10+ year backtest.

Input:

```text
strategy_code
symbol
timeframe
start_date
end_date
initial_capital
risk_mode
commission
slippage
```

Output:

```text
total_return
CAGR
max_drawdown
win_rate
profit_factor
number_of_trades
average_R
best_trade
worst_trade
average_holding_time
long_performance
short_performance
yearly_performance
monthly_performance
equity_curve
trade_list
```

Important requirements:

```text
No lookahead bias
No repainting
No future data
Clear transaction cost assumptions
Reproducible result
```

---

### 3.5 Result Review Dashboard

Purpose: show result immediately after backtest.

Layout:

```text
Top metrics:
- Total Return
- Max Drawdown
- Win Rate
- Profit Factor
- Trades
- Average R

Middle:
- Equity Curve
- Drawdown Curve
- Monthly heatmap

Bottom:
- Trade List
- Yearly Performance
- Long vs Short stats
```

Every backtest result should be saved so Jack can compare versions.

---

### 3.6 Strategy Version / Snowball Memory

Purpose: every backtest becomes future data.

Save:

```text
strategy_name
version
prompt
code
symbol
timeframe
data_range
parameters
result_summary
trade_list
notes
mistakes
next_version_idea
created_at
```

Version examples:

```text
GBPJPY Trend Breakout v1
GBPJPY Trend Breakout v2
XAUUSD Abu Compression v1
EURUSD Pullback v1
```

Review loop:

```text
Backtest result
→ identify weakness
→ edit prompt / code
→ run again
→ compare v1 vs v2 vs v3
```

---

## 4. First build milestone

### Milestone 1: No-AI Backtest Core

Build first:

```text
1. Local data schema for candles
2. Sample 10-year daily data import
3. Simple Python backtest runner
4. One test strategy
5. Result JSON
6. Basic result page
```

First test strategy:

```text
GBPJPY Trend Breakout v1
Daily EMA200 trend filter
H4 breakout entry
ATR stop loss
3R take profit
1% risk
10-year backtest
```

Pass condition:

```text
Jack can click Run Backtest and see result without AI token.
```

---

## 5. Second build milestone

### Milestone 2: AI Strategy Prompt using Jack API key

Add:

```text
Strategy prompt input
Use OPENAI_API_KEY from Jack's environment
Generate Python strategy code
Insert code into editor
Run backtest
Save prompt + code + result
```

AI safety:

```text
AI can generate code only
AI cannot execute live trades
AI cannot connect broker
AI cannot change approved rules without Jack approval
```

---

## 6. Long-term direction

After v1 is stable:

```text
Multi-timeframe Abu setup engine
Forex strength panel
XAUUSD special model
Market regime detection
Trade journal connection
Mistake memory
Portfolio / capital stage tracker
```

Final direction:

```text
Jack talks strategy with ChatGPT
Jack QuantDinger runs research and backtests
Every result becomes Snowball System memory
Jack decides execution manually
```

---

## 7. Implementation note

Current QuantDinger fork can remain as reference. New Jack modules should be isolated and not break original QuantDinger startup.

Suggested new backend namespace:

```text
/api/jack-backtest
```

Suggested new docs:

```text
docs/jack_quantdinger_v1_spec.md
docs/jack_backtest_data_plan.md
docs/jack_backtest_api_plan.md
```

Suggested next implementation task:

```text
Create Jack Backtest no-AI backend skeleton:
GET  /api/jack-backtest/health
GET  /api/jack-backtest/sample-result
POST /api/jack-backtest/run-sample
```

The first endpoint should return mock/sample results before connecting real historical data.
