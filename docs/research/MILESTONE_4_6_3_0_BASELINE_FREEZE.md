# NEPTUNE — Milestone 4.6.3.0
# Technical-Only Strategy Baseline Freeze Specification

**Milestone:** 4.6.3.0  
**Status:** FROZEN  
**Date:** 2026-11-06  
**Document Type:** Technical Baseline Specification & Discrepancy Audit  
**Configuration Fingerprint (SHA-256):** `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`  

---

## 1. Baseline Strategy Overview

NEPTUNE's deterministic technical baseline strategy combines multi-timeframe regime detection, moving average stack alignment, momentum acceleration/divergence analysis, and volume participation into an explainable, rule-based setup generator.

- **Primary Strategy Identifier:** `trend_continuation_v1` (in `strategy_analyst.py`)
- **Simulation Strategy Identifier:** `trend_momentum_pullback_v1` (in `models.py`)
- **Operational Principle:** Consumes strictly confirmed, closed candles (Rule A-09). Never evaluates in-progress bars. Defaults strictly to `NO_SIGNAL` when conflicting indicators exist.

---

## 2. Implementation Discrepancy Reconciliation

Prior to freezing the baseline, every parameter specified in the research protocol was reconciled against the live Python implementation across `backend/app/config/settings.py`, `backend/app/risk/risk_manager.py`, `backend/app/simulation/models.py`, `backend/app/simulation/execution.py`, and `backend/app/simulation/engine.py`.

| Parameter | Specification | Live Implementation Value | Implementation Location | Discrepancy Status |
|:---|:---:|:---:|:---|:---:|
| **Starting Virtual Capital** | 1,000 USDT | `Decimal("1000.00")` / `1000.0` | `models.BacktestConfig.initial_capital`<br>`settings.paper_starting_equity` | **EXACT MATCH** |
| **Leverage** | Disabled (1.0x spot cap) | Cap at available cash equity / no margin | `risk_manager.RiskManager.evaluate_signal` | **EXACT MATCH** |
| **Max Concurrent Positions** | 2 | `2` | `models.BacktestConfig.max_concurrent_positions`<br>`risk_manager.max_concurrent_positions` | **EXACT MATCH** |
| **Max Risk Per Trade** | 0.5% | `Decimal("0.005")` | `models.BacktestConfig.risk_per_trade_pct`<br>`risk_manager.risk_per_trade_pct` | **EXACT MATCH** |
| **Daily Simulated Loss Limit**| 2.0% | `Decimal("0.02")` | `models.BacktestConfig.daily_loss_limit_pct`<br>`risk_manager.daily_loss_limit_pct` | **EXACT MATCH** |
| **Max Drawdown Circuit Breaker**| 5.0% | `Decimal("0.05")` | `models.BacktestConfig.max_drawdown_pct`<br>`risk_manager.max_drawdown_pct` | **EXACT MATCH** |
| **Minimum Reward/Risk Ratio** | 1.5:1 | `Decimal("1.5")` / `1.5` | `models.BacktestConfig.min_reward_risk_ratio`<br>`strategy_analyst.RawCandidateSignal` | **EXACT MATCH** |
| **Taker Fee Per Side** | 0.10% (10 bps) | `Decimal("0.001")` | `execution.PaperExecutionSimulator.taker_fee_pct` | **EXACT MATCH** |
| **Maker Fee Per Side** | 0.10% (10 bps) | `Decimal("0.001")` | `execution.PaperExecutionSimulator.maker_fee_pct` | **EXACT MATCH** |
| **Adverse Slippage Per Side** | 0.05% (5 bps) | `Decimal("0.0005")` | `execution.PaperExecutionSimulator.slippage_pct` | **EXACT MATCH** |
| **Bid-Ask Half-Spread** | 0.01% (1 bp) | `Decimal("0.0001")` (`spread_bps = 2.0`) | `execution.PaperExecutionSimulator.spread_fraction` | **EXACT MATCH** |
| **Total Round-Trip Friction** | 0.32% (32 bps) | `0.16% entry + 0.16% exit = 0.32%` | `execution.PaperExecutionSimulator._finalize_trade` | **EXACT MATCH** |
| **Default Execution Policy** | `NEXT_ELIGIBLE_PRICE`| `NEXT_ELIGIBLE_PRICE` (for experiments)| `models.ExecutionPolicy.NEXT_ELIGIBLE_PRICE` | **EXACT MATCH** |
| **15m Max Execution Gap** | 1 bar (30 min delay) | `1` bar configured in protocol | `scheduling.PointInTimeExecutionScheduler` | **EXACT MATCH** |
| **HTF Max Execution Gap** | 3 bars (4h / 16h / 4d)| `3` bars configured in protocol | `scheduling.PointInTimeExecutionScheduler` | **EXACT MATCH** |

> **Audit Finding:** Zero parameter discrepancies exist between the research protocol and the codebase implementation.

---

## 3. Detailed Component Specifications

### 3.1 Market Scanner Agent (`market_scanner.py`)
- **Purpose:** Classifies market structure into one of five deterministic regimes.
- **Warmup:** Requires minimum 30 closed candles; defaults to `UNCERTAIN` (confidence = 0.0) if $< 30$.
- **Indicators:**
  - ATR 14: Rolling mean over last 50 bars. $\text{ATR ratio} = \text{ATR}_{14} / \text{mean}(\text{ATR}_{50})$.
  - Bollinger Bands: Period 20, 2.0 standard deviations.
  - Keltner Channels: EMA 20, ATR 10. Squeeze detected when Upper BB $<$ Upper KC and Lower BB $>$ Lower KC.
  - ADX 14: Directional Movement Index with Wilder's smoothing continuity.
  - EMA 50: Baseline trend reference.
- **Regime Rules:**
  1. `VOLATILE`: $\text{ATR ratio} > 1.80$. Confidence = $\min(1.0, 0.60 + (\text{ratio} - 1.80) \times 0.20)$.
  2. `RANGING` (Squeeze): Bollinger Bands compressed within Keltner Channels. Confidence = 0.85.
  3. `TRENDING_BULL`: $\text{ADX}_{14} \ge 25.0$, $\text{Price} > \text{EMA}_{50}$, $+\text{DI} > -\text{DI}$. Confidence = $\min(0.95, \text{ADX} / 50.0)$.
  4. `TRENDING_BEAR`: $\text{ADX}_{14} \ge 25.0$, $\text{Price} < \text{EMA}_{50}$, $-\text{DI} > +\text{DI}$. Confidence = $\min(0.95, \text{ADX} / 50.0)$.
  5. `RANGING` (Weak): $\text{ADX}_{14} < 20.0$. Confidence = $\max(0.50, 1.0 - \text{ADX} / 20.0)$.
  6. `UNCERTAIN`: Mixed DI/Price alignment or transitional ADX ($20.0 \le \text{ADX} < 25.0$).

### 3.2 Trend Analyst Agent (`trend_analyst.py`)
- **Purpose:** Measures multi-moving-average stack alignment and directional slope.
- **Warmup:** Minimum 20 closed candles required. Full EMA 200 stability requires 200 bars. If $N < 200$, a 50% confidence discount is applied.
- **Stack Alignment:**
  - Bullish Stack: $\text{EMA}_{20} > \text{EMA}_{50} > \text{EMA}_{200}$ (or $\text{EMA}_{20} > \text{EMA}_{50}$ and $\text{Price} > \text{EMA}_{50}$ if $N < 200$).
  - Bearish Stack: $\text{EMA}_{20} < \text{EMA}_{50} < \text{EMA}_{200}$ (or $\text{EMA}_{20} < \text{EMA}_{50}$ and $\text{Price} < \text{EMA}_{50}$ if $N < 200$).
- **Composite Bias & Strength:**
  - $\text{Strength} = (\text{Stack contribution [0.3-0.5]}) + (\text{ADX contribution [0.0-0.5]}) \times (1.0 - \text{Discount})$.
  - Minimum trend strength required for signal generation: $\text{Strength} \ge 0.40$.

### 3.3 Momentum Analyst Agent (`momentum_analyst.py`)
- **Purpose:** Analyzes momentum velocity, MACD acceleration, and exhaustion divergence.
- **Warmup:** Minimum 35 closed candles ($\text{MACD slow } 26 + \text{signal } 9$).
- **Indicators:**
  - RSI 14: Normalized between $-1.0$ and $+1.0$ around midpoint 50.0.
  - MACD (12, 26, 9): Histogram slope over last 2 bars.
- **Divergence & Exhaustion Detection:**
  - Bearish Divergence: New 15-bar price high while RSI fails to form higher high ($> 3.0$ pt drop).
  - Bullish Divergence: New 15-bar price low while RSI forms higher low ($> 3.0$ pt gain).
  - Deceleration: RSI $\ge 70.0$ with negative histogram slope, or RSI $\le 30.0$ with positive histogram slope.
- **Confluence Range:**
  - LONG: Momentum score $\ge +0.15$, $40.0 \le \text{RSI} \le 68.0$, no exhaustion risk.
  - SHORT: Momentum score $\le -0.15$, $32.0 \le \text{RSI} \le 60.0$, no exhaustion risk.

### 3.4 Volume Analyst Agent (`volume_analyst.py`)
- **Purpose:** Evaluates liquidity participation, VWAP deviation, and On-Balance Volume.
- **Warmup:** Minimum 20 closed candles ($\text{SMA}_{20}$ baseline).
- **Indicators:**
  - Relative Volume: $\text{RVOL} = \text{Volume} / \text{SMA}_{20}(\text{Volume})$.
  - Participation Categories: $\text{STRONG } (\text{RVOL} \ge 1.50)$, $\text{NORMAL } (\text{RVOL} \ge 0.80)$, $\text{WEAK } (\text{RVOL} < 0.80)$.
  - Anomaly Surge: Volume $> 2.50$ standard deviations above 50-bar rolling mean.
  - On-Balance Volume: 10-bar slope determines `ACCUMULATION` ($>0$) vs `DISTRIBUTION` ($<0$).
- **Confluence Requirement:**
  - LONG: Participation $\in \{\text{STRONG}, \text{NORMAL}\}$, $\text{OBV} \ne \text{DISTRIBUTION}$.
  - SHORT: Participation $\in \{\text{STRONG}, \text{NORMAL}\}$, $\text{OBV} \ne \text{ACCUMULATION}$.

### 3.5 Strategy Analyst Agent (`strategy_analyst.py`)
- **Conflicting Indicators (Strict Default to `NO_SIGNAL`):**
  1. Market regime is `VOLATILE` or `UNCERTAIN`.
  2. Trend bias conflicts with Momentum direction (e.g. Bullish trend + Bearish momentum).
  3. Momentum exhaustion warning active.
  4. Volume divergence active (Bullish price + Institutional distribution, or vice versa).
- **Setup Generation (Monetary Calculation via `Decimal`):**
  - $\text{Entry Price} = \text{Candle Close}$.
  - $\text{Risk Amount} = 2.0 \times \text{ATR}_{14}$.
  - $\text{Reward Amount} = \text{Risk Amount} \times 1.50$.
  - Long: $\text{Stop} = \text{Entry} - \text{Risk}$, $\text{Target} = \text{Entry} + \text{Reward}$.
  - Short: $\text{Stop} = \text{Entry} + \text{Risk}$, $\text{Target} = \text{Entry} - \text{Reward}$.
  - Invariant: Stops and targets $\le 0$ immediately rejected.

### 3.6 Risk Manager Authorization & Sizing (`risk_manager.py`)
- **Five Invariant Checks:**
  1. Daily Loss Limit: $(\text{Daily Realized} + \text{Unrealized}) / \text{Daily Starting Equity} > -2.0\%$.
  2. Drawdown Circuit Breaker: $(\text{Peak} - \text{Current}) / \text{Peak} < 5.0\%$.
  3. Concurrent Positions: $\text{Active Positions} + \text{Pending Scheduled} < 2$.
  4. Correlation Exposure: Max 1 position per symbol across active portfolio.
  5. Minimum Reward/Risk: $\text{Reward Distance} / \text{Risk Distance} \ge 1.50$.
- **Position Sizing Formula:**
  $$\text{Risk Budget} = \text{Total Equity} \times 0.005$$
  $$\text{Raw Units} = \frac{\text{Risk Budget}}{|\text{Entry Price} - \text{Stop Loss}|}$$
  $$\text{Max Spot Units} = \frac{\text{Available Cash}}{\text{Entry Price}}$$
  $$\text{Final Sized Units} = \min(\text{Raw Units}, \text{Max Spot Units})$$
- **Cryptographic Token Binding:** Issues HMAC-SHA256 token binding `run_id`, `signal_id`, `symbol`, `direction`, `quantity`, `entry_price`, `stop_loss`, and `timestamp`.

### 3.7 Execution & Protective Mechanics (`execution.py`, `scheduling.py`)
- **Execution Policy:** `NEXT_ELIGIBLE_PRICE`. Orders fill at the open of Bar $T+1$.
- **Execution Frictions Applied:**
  $$\text{Executed Entry Price}_{\text{LONG}} = \text{Open} \times (1 + \text{slippage } 0.0005 + \text{half-spread } 0.0001)$$
  $$\text{Executed Entry Price}_{\text{SHORT}} = \text{Open} \times (1 - \text{slippage } 0.0005 - \text{half-spread } 0.0001)$$
  $$\text{Entry Fee} = \text{Executed Notional} \times \text{taker fee } 0.0010$$
- **BALANCED Protective Ratchet Mode:**
  - Fixed take profit is **not** automatically enforced; positions run with the trend.
  - When favorable excursion reaches $+1.0\text{ R}$, the trailing stop activates.
  - Trailing stop ratchets to $\text{Peak} - (2.0 \times \text{ATR}_{14})$ for longs (or $\text{Trough} + (2.0 \times \text{ATR}_{14})$ for shorts).
  - One-way ratchet: stops can only move in the direction of profit, never widen.
  - Ambiguous bar resolution: If both stop and target are touched within a bar, the stop loss is conservatively assumed hit.
  - Reversal exits: If multi-factor reversal is detected at Bar $T$ close, position exits at Bar $T+1$ open (superseded by stop loss if stop is breached at open).

---

## 4. Frozen Baseline Configuration Fingerprint

The complete baseline configuration has been exported to:  
`storage/exports/milestone_4_6_3_0/frozen_baseline_configuration.json`

**Cryptographic Hash (SHA-256):**  
$$\mathbf{33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278}$$

This hash certifies the technical baseline is frozen and verifiable across all subsequent experimental milestones.
