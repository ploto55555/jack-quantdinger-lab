# Jack Strategy Deployment Pipeline

This document defines the professional path from backtest to automated trading.

## Core principle

A strategy must never jump directly from backtest to live trading.

Correct path:

```text
Draft
→ Backtested
→ Validated
→ Paper Trading
→ Small Live
→ Live Approved
→ Paused / Retired
```

## Stage rules

### 1. Draft

Strategy idea exists, but it has not passed any test.

Allowed:

```text
Edit prompt
Edit code
Run sample backtest
Run historical backtest
```

Forbidden:

```text
Paper trading
Live trading
Broker execution
```

### 2. Backtested

Strategy has historical backtest result.

Minimum required metrics:

```text
10-year data if available
Total return
CAGR
Max drawdown
Win rate
Profit factor
Number of trades
Average R
Trade list
Equity curve
Drawdown curve
```

Promotion rule:

```text
Can move to Validated only after manual approval by Jack.
```

### 3. Validated

Strategy has passed extra review such as walk-forward / out-of-sample check.

Minimum checks:

```text
Not only profitable because of one lucky trade
No lookahead bias
No future data
Reasonable trade count
Drawdown acceptable
Works outside original optimisation period
```

Promotion rule:

```text
Can move to Paper Trading only after manual approval by Jack.
```

### 4. Paper Trading

Strategy runs on real-time market data but does not use real money.

Minimum monitoring:

```text
Signal timestamp
Expected entry price
Actual simulated entry
Spread / slippage estimate
Missed signal log
Rejected signal log
Daily PnL simulation
```

Promotion rule:

```text
Paper trading must run for a meaningful period before small live.
```

### 5. Small Live

Strategy uses real money with very small risk.

Hard limits:

```text
Max risk per trade: 0.10% - 0.25%
Daily loss limit required
Strategy loss limit required
Kill switch required
Broker error handling required
```

Promotion rule:

```text
Can move to Live Approved only after manual approval by Jack.
```

### 6. Live Approved

Strategy is allowed to run automatically under portfolio risk control.

Required controls:

```text
Portfolio Risk Manager
Daily max loss
Weekly max loss
Total open exposure limit
Same-symbol duplicate check
Correlation / same-direction check
News pause rule
Drawdown auto downgrade
Kill switch
Audit log
```

### 7. Paused / Retired

Strategy is stopped.

Reasons:

```text
Drawdown breach
System error
Market regime changed
Manual pause
Strategy replaced by better version
```

## Portfolio Risk Manager

When multiple strategies are running, the system must check account-level risk before allowing any order.

Example:

```text
Strategy A: GBPJPY Trend Breakout
Strategy B: XAUUSD Pullback
Strategy C: EURUSD Range
```

Before execution, the manager checks:

```text
1. Is total account daily risk still below limit?
2. Is this symbol already exposed?
3. Is this direction already crowded?
4. Are multiple strategies taking the same macro bet?
5. Is account drawdown in Attack / Normal / Defense / Pause mode?
6. Is news pause active?
7. Is broker/API healthy?
8. Is kill switch off?
```

## API namespace

Suggested backend namespace:

```text
/api/jack-deployment
```

First skeleton endpoints:

```text
GET  /api/jack-deployment/health
GET  /api/jack-deployment/stages
GET  /api/jack-deployment/sample-strategies
POST /api/jack-deployment/evaluate-promotion
POST /api/jack-deployment/portfolio-risk-check
```

These endpoints are non-trading skeletons first. They must not connect to brokers.

## v1 safety

In v1, this pipeline is only a control framework.

```text
No live order placement
No broker connection
No autonomous execution
No strategy can self-promote
Manual approval required at every major step
```
