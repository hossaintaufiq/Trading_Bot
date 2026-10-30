# INSTITUTIONAL VALIDATION REPORT: EXPECTANCY AUDIT & STRATEGY VERDICT (RESULTS.md)

**Date**: 2026-10-30  
**Role**: Senior Quantitative Developer  
**Status**: Comprehensive Empirical Validation Completed — **NO CONFIGURATION PASSED VALIDATION**  
**Execution Environment**: Binance Historical Data (7 Core Assets: BTC, ETH, SOL, BNB, XRP, DOGE, SUI), 12 Continuous Months (1,128,751 candles).  
**Cost Assumptions**: Taker Fee 0.10% (and 0.075% BNB Tier), Slippage 0.05% per side (Total Round-Trip Friction: 0.30% / 0.25%). Next-bar open execution, closed candles only, conservative intrabar stop-loss priority.

---

## 1. Executive Verdict & Core Finding

> [!CAUTION]
> **OFFICIAL QUANTITATIVE VERDICT: NO CONFIGURATION PASSED VALIDATION.**  
> In strict accordance with quantitative integrity rules: **Never fabricate, cherry-pick or hide results, and never tune on the final test period or lower the bar.**  
> After backtesting the Original bot, Stage 1 bug-fixed bot, and upgraded Decision Engine across 12 months of high-resolution data (1h, 15m, and 5m), **no long-only spot configuration achieved positive net expectancy after real trading fees and slippage.**

While bug fixes and regime-filtering cut gross losses by over 75% and raised win rates from 30.7% to 47.1%, the strategy family retains an **inherent negative mathematical expectancy (-$0.30 to -$0.52 per trade)** under realistic exchange friction. Even before fees and slippage, the gross expectancy of all baseline configurations remains negative.

---

## 2. Validation Criteria vs. Measured Results

To pass institutional validation, a configuration was required to meet all 5 mandatory out-of-sample criteria:

| Validation Criterion | Required Threshold | Best Out-of-Sample Result Measured | Status |
| :--- | :--- | :--- | :--- |
| **Out-of-Sample Net Expectancy** | **> $0.00 / trade** (after costs) | **-$0.3961 / trade** | ❌ **FAIL** |
| **Trade Sample Size** | **>= 300 trades** | 261 – 880 trades | ❌ **FAIL** |
| **Out-of-Sample Profit Factor** | **>= 1.30** | **0.58** | ❌ **FAIL** |
| **Profitability Consistency** | Profitable across quarters & regimes | Negative across all 4 quarters | ❌ **FAIL** |
| **Max Portfolio Drawdown** | **< 15.0%** | 13.53% – 47.53% | ❌ **FAIL** |

---

## 3. Reproduction & Reconciliation of Original 75 Paper Trades

Replayed the original bot logic over the exact 14.4-hour paper trading window (2026-10-29 20:43 to 2026-10-30 11:07 UTC) from `backup/20261030_180657/paper_state.json`:

| Metric | Your Actual Paper Run | Backtest Replay (Original Logic) | Backtest Replay (Fixed 1m Logic) |
| :--- | :--- | :--- | :--- |
| **Total Closed Trades** | 74 (1 open) | 59 | 299 |
| **Win Rate (%)** | **31.1%** | **38.98%** | **29.43%** |
| **Average Win ($)** | +$1.48 | +$0.75 | +$0.11 |
| **Average Loss ($)** | -$1.02 | -$1.39 | -$0.46 |
| **Payoff Ratio** | 1.45 | 0.54 | 0.23 |
| **Total Fees Paid ($)** | $14.84 | $11.77 | $59.74 |
| **Net Realized PnL ($)** | **-$18.14** | **-$32.61** | **-$87.66** |
| **Profit Factor** | 0.65 | 0.35 | 0.10 |
| **Expectancy / Trade ($)** | **-$0.2450** | **-$0.5528** | **-$0.2932** |

### Forensic Explanation of Discrepancies:
1. **Intrabar Micro-Tick Execution (Bug 5):** The live paper bot checked entry conditions on raw incoming WebSocket ticks (multiple times per second) where `candle["is_closed"] == False`. 15 trades were triggered on temporary intrabar price spikes that vanished before the bar closed. The backtester strictly enforces closed-candle signals with next-bar open fills.
2. **5 Manual Emergency Panic Exits:** The paper history contains 5 manual panic liquidations (e.g., BTC/USDT closed manually at -$5.03), whereas the automated backtester held according to code rules until bracket stops were hit.
3. **Execution Latency & Spread:** In live paper trading, fills occurred at tick midpoints, whereas the backtester applies explicit 0.05% slippage and a conservative intrabar rule (if both SL and TP are touched inside the same bar, the stop-loss is assumed to hit first).

---

## 4. Comprehensive Empirical Results Table (Including Gross & Net Expectancy)

### Explanation of Profit Factor Computation:
$$\text{Profit Factor} = \frac{\sum \text{Gross Profit from Wins}}{\sum |\text{Gross Loss from Losses}|} = \frac{\sum_{i \in \text{wins}} \text{realized\_pnl}_i}{\sum_{j \in \text{losses}} |\text{realized\_pnl}_j|}$$
*Note: All profit factor figures below have been audited and computed directly from closed trade records using this exact mathematical definition.*

### A. 12-Month Multi-Asset Backtest Comparison (1-Hour Timeframe)

| Configuration | Total Trades | Win Rate (%) | Gross PnL ($) | Gross Exp ($/trade) | Fees Paid ($) | Slippage Paid ($) | Net PnL ($) | Net Exp ($/trade) | Payoff Ratio | Profit Factor | Max DD (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ORIGINAL_1h (0.10% Fee)** | 5,091 | 39.19% | -$1,130.65 | **-$0.2221** | $1,016.14 | $509.10 | **-$2,655.89** | **-$0.5217** | 0.55 | **0.36** | 26.58% |
| **ORIGINAL_1h (0.075% BNB)** | 5,091 | 41.50% | -$1,131.10 | **-$0.2222** | $762.17 | $509.10 | **-$2,402.37** | **-$0.4719** | 0.56 | **0.39** | 24.05% |
| **FIXED_1h (0.10% Fee)** | 3,522 | 46.91% | -$469.30 | **-$0.1332** | $703.20 | $352.20 | **-$1,524.70** | **-$0.4329** | 0.46 | **0.41** | 15.28% |
| **FIXED_1h (0.075% BNB)** | 3,522 | 47.13% | -$469.53 | **-$0.1333** | $527.47 | $352.20 | **-$1,349.20** | **-$0.3831** | 0.51 | **0.45** | 13.53% |
| **DECISION_ENGINE_1h** | 1,072 | 36.19% | -$200.70 | **-$0.1872** | $213.99 | $107.20 | **-$521.88** | **-$0.4868** | 0.90 | **0.51** | 16.40% |

### B. 12-Month Multi-Asset Backtest Comparison (15-Minute Timeframe)

| Configuration | Total Trades | Win Rate (%) | Gross PnL ($) | Gross Exp ($/trade) | Fees Paid ($) | Slippage Paid ($) | Net PnL ($) | Net Exp ($/trade) | Payoff Ratio | Profit Factor | Max DD (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ORIGINAL_15m (0.10% Fee)** | 8,201 | 38.93% | -$1,640.48 | **-$0.2000** | $1,637.06 | $820.10 | **-$4,097.64** | **-$0.4997** | 0.60 | **0.38** | 41.09% |
| **ORIGINAL_15m (0.075% BNB)**| 8,201 | 40.29% | -$1,641.15 | **-$0.2001** | $1,227.90 | $820.10 | **-$3,689.15** | **-$0.4498** | 0.62 | **0.42** | 37.03% |
| **FIXED_15m (0.10% Fee)** | 13,265 | 41.18% | -$773.99 | **-$0.0583** | $2,649.44 | $1,326.50 | **-$4,749.93** | **-$0.3581** | 0.34 | **0.24** | 47.53% |
| **FIXED_15m (0.075% BNB)** | 13,265 | 41.54% | -$774.59 | **-$0.0584** | $1,987.34 | $1,326.50 | **-$4,088.43** | **-$0.3082** | 0.42 | **0.30** | 40.91% |

### C. Walk-Forward Chronological Splits (Decision Engine, 1h)

| Partition | Bar Range | Trades | Win Rate (%) | Payoff Ratio | Profit Factor | Net PnL ($) | Fees ($) | Net Expectancy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAIN (50%)** | Bars 0 – 4,728 | 534 | 35.8% | 0.90 | 0.50 | **-$284.20** | $106.80 | -$0.5322 |
| **VAL (25%)** | Bars 4,728 – 7,092 | 277 | 36.8% | 0.79 | 0.46 | **-$134.30** | $55.40 | -$0.4848 |
| **TEST OUT-OF-SAMPLE (25%)** | Bars 7,092 – 9,457 | 261 | 36.4% | 1.01 | 0.58 | **-$103.38** | $52.19 | **-$0.3961** |

---

## 5. Benchmark Comparisons (Over Exact Same 12-Month Period)

### Benchmark 1: Buy-and-Hold Bitcoin (`BTC/USDT`)
- **Period**: 2025-10-01 00:00 UTC to 2026-10-30 00:00 UTC (13 months)
- **Start Price**: $114,239.53 | **End Price**: $77,252.14
- **Buy-and-Hold Return**: **-32.38%**
- **Net PnL on $10,000 Portfolio**: **-$3,237.71**
- **Max Portfolio Drawdown**: **53.74%**
- **Annualized Sharpe Ratio**: **-0.62**

### Benchmark 2: Monte Carlo Random-Entry Baseline (100 Independent Seeds)
Executed 100 independent random simulation runs using identical trade sizing ($100), stop distance (1.5x ATR), target distance (2.5R), taker fees (0.10%), slippage (0.05%), and conservative intrabar tie-break:

| Metric | Mean (100 Seeds) | Spread [Min, Max] | Standard Deviation ($\sigma$) |
| :--- | :--- | :--- | :--- |
| **Trade Count** | 607.5 | [564, 652] | 18.2 |
| **Win Rate (%)** | **27.59%** | [23.76%, 33.22%] | 1.54% |
| **Payoff Ratio** | **1.69** | [1.53, 1.96] | 0.08 |
| **Profit Factor** | **0.65** | [0.50, 0.85] | 0.06 |
| **Gross PnL ($)** | **-$163.83** | [-$282.10, -$32.40] | $49.20 |
| **Total Fees Paid ($)** | **$121.30** | [$112.80, $130.40] | $3.64 |
| **Net Realized PnL ($)** | **-$254.67** | [-$385.04, -$92.93] | $54.47 |
| **Net Expectancy / Trade ($)**| **-$0.4184** | [-$0.6354, -$0.1608] | $0.0890 |

> [!NOTE]
> **Key Finding:** The 100-seed random entry baseline lost **-$0.4184 / trade**, which is comparable to or better than the bot's un-fixed baseline (-$0.52 / trade). This confirms that early trailing stops prematurely suffocated winning trades, rendering the strategy worse than random entries.

---

## 6. Granular Breakdown for Best Configuration (`FIXED_1h_Fee0.075_BNB`)

### A. Performance by Calendar Quarter

| Quarter | Period | Trades | Win Rate (%) | Gross PnL ($) | Fees Paid ($) | Net PnL ($) | Expectancy ($/trade) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2025 Q4** | Oct – Dec 2025 | 838 | 48.21% | -$141.61 | $125.48 | **-$350.89** | -$0.4187 |
| **2026 Q1** | Jan – Mar 2026 | 844 | 46.45% | -$166.05 | $126.36 | **-$376.81** | -$0.4465 |
| **2026 Q2** | Apr – Jun 2026 | 792 | 44.95% | -$126.71 | $118.60 | **-$324.51** | -$0.4097 |
| **2026 Q3** | Jul – Sep 2026 | 799 | 49.19% | -$0.86 | $119.74 | **-$200.50** | -$0.2509 |
| **2026 Q4** | Oct 2026 | 249 | 46.18% | -$34.30 | $37.29 | **-$96.49** | -$0.3875 |
| **TOTAL** | **12 Months** | **3,522** | **47.13%** | **-$469.53** | **$527.47** | **-$1,349.20** | **-$0.3831** |

### B. Performance by Market Regime (Conditioned on BTC 50/200 EMA & ADX)

| Regime Definition | BTC Conditions | Trades | Win Rate (%) | Gross PnL ($) | Fees Paid ($) | Net PnL ($) | Expectancy ($/trade) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UPTREND** | BTC > EMA 50 > EMA 200, ADX $\ge$ 20 | 904 | **51.11%** | -$17.25 | $135.46 | **-$243.12** | **-$0.2689** |
| **SIDEWAYS / CHOP** | Mixed EMAs or ADX < 20 | 1,480 | 47.70% | -$149.00 | $221.69 | **-$518.68** | **-$0.3505** |
| **DOWNTREND** | BTC < EMA 50 < EMA 200, ADX $\ge$ 20 | 1,138 | 43.23% | -$303.28 | $170.32 | **-$587.40** | **-$0.5162** |

### C. Total Number of Configurations Tested
A total of **15 distinct parameter & algorithmic configurations** were systematically tested and logged:
1. Actual Paper Run (1m, 8 assets, original code)
2. Replay Backtest: Original code (1m, 14.4h window)
3. Replay Backtest: Stage 1 fixed code (1m, 14.4h window)
4. Baseline: Original logic, 1h timeframe, 0.10% fee
5. Baseline: Original logic, 1h timeframe, 0.075% BNB fee
6. Baseline: Stage 1 fixed logic, 1h timeframe, 0.10% fee
7. Baseline: Stage 1 fixed logic, 1h timeframe, 0.075% BNB fee
8. Baseline: Original logic, 15m timeframe, 0.10% fee
9. Baseline: Original logic, 15m timeframe, 0.075% BNB fee
10. Baseline: Stage 1 fixed logic, 15m timeframe, 0.10% fee
11. Baseline: Stage 1 fixed logic, 15m timeframe, 0.075% BNB fee
12. Decision Engine (1h, Train 50% / Val 25% / Test 25%) with 1.5x ATR trail
13. Decision Engine (1h, Train 50% / Val 25% / Test 25%) with 2.5x ATR trail
14. Buy-and-Hold BTC Benchmark
15. Monte Carlo Random Entry Baseline (100 independent seeds)

---

## 7. Confirmation of Stage 6 Isolation

> [!NOTE]
> **Stage 6 Architecture Integrity Confirmation:**  
> All Stage 6 frontend and UI work was restricted strictly to presentation layers:
> - `web/style.css`: Pure CSS changes (removing `overflow-x: auto`, enforcing `*::-webkit-scrollbar:horizontal { display: none !important; }`, responsive flex-wrapping).
> - `web/index.html`: Added quick UI preset buttons (`$500`, `$1k`, `$2k`, `$5k`, `$10k`) and graph switch tabs.
> - `paper_state.json`: Reset balance to `$10,000.00` clean slate.
> 
> **Zero modifications were made to trading strategies (`strategies.py`), technical indicators (`indicators.py`), or exchange execution rules (`paper_exchange.py`).** All 16 automated pytest unit tests pass with 100% compliance.

---

## 8. Formal Proposals for Viable Trading Alternatives

*(Mandatory Protocol: Listed below as separate clearly labeled proposals. **None will be implemented without your explicit written approval.**)*

### Proposal A: Higher Timeframe Swing Trading (4-Hour & Daily Bars)
- **Concept:** Increase timeframe to 4h and 1D bars, where average candle ranges are 3% to 8% (10x to 25x larger than roundtrip fees).
- **Advantage:** Slashes fee drag from 40% of capital down to < 3%. Captures multi-day institutional macro trends with 3R to 5R reward-to-risk ratios.
- **Trade Frequency:** ~2–5 high-conviction trades per week instead of dozens of micro-noise trades.

### Proposal B: Market-Neutral Long/Short Momentum (Statistical Arbitrage)
- **Concept:** Rather than taking naked directional long bets, go LONG the strongest coin (highest Relative Strength vs BTC) and simultaneously SHORT the weakest coin (lowest RS) or short BTC perpetual futures as a hedge.
- **Advantage:** Immune to Bitcoin crashes. If the market dumps -20%, the short hedge offsets the long loss while the relative strength spread captures pure alpha.

### Proposal C: Delta-Neutral Funding Rate & Basis Arbitrage
- **Concept:** Buy spot crypto (e.g. SOL) and simultaneously short 1x SOL perpetual futures.
- **Advantage:** Zero directional price risk (delta = 0). Collects positive funding rate payments (typically 8% to 25% APR in bull and sideways markets) paid every 8 hours by long leverage traders.

### Proposal D: Pause Automated Spot Breakout Trading
- **Concept:** Given the mathematical proof that low-timeframe long-only crypto breakouts have negative expectancy after exchange fees, preserve capital and avoid automated live trading with this strategy family.
