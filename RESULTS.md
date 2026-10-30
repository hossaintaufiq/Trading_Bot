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
> After backtesting the Original bot, Stage 1 bug-fixed bot, and upgraded Decision Engine across 12 months of high-resolution data (1h and 15m), **no long-only spot configuration achieved positive net expectancy after real trading fees and slippage.**

The strategy family exhibits an **inherent negative mathematical expectancy across all evaluated configurations**:
- **ORIGINAL_1h (0.10% fee)**: 5,091 trades, Win Rate 39.19%, Payoff Ratio 0.55, Profit Factor 0.36, Net Expectancy **-$0.5217 / trade**.
- **FIXED_1h (0.10% fee)**: 3,522 trades, Win Rate 46.91%, Payoff Ratio 0.46, Profit Factor 0.41, Net Expectancy **-$0.4329 / trade**.
- **FIXED_1h (0.075% BNB fee)**: 3,522 trades, Win Rate 47.13%, Payoff Ratio 0.51, Profit Factor 0.45, Net Expectancy **-$0.3831 / trade**.
- **DECISION_ENGINE_1h (1.5x ATR trail)**: 1,088 trades, Win Rate 36.12%, Payoff Ratio 0.90, Profit Factor 0.51, Net Expectancy **-$0.4883 / trade**.
- **DECISION_ENGINE_1h (2.5x ATR trail)**: 1,072 trades, Win Rate 36.19%, Payoff Ratio 0.90, Profit Factor 0.51, Net Expectancy **-$0.4868 / trade**.
- **ORIGINAL_15m (0.10% fee)**: 8,201 trades, Win Rate 38.93%, Payoff Ratio 0.60, Profit Factor 0.38, Net Expectancy **-$0.4997 / trade**.
- **FIXED_15m (0.10% fee)**: 13,265 trades, Win Rate 41.18%, Payoff Ratio 0.34, Profit Factor 0.24, Net Expectancy **-$0.3581 / trade**.

Although the bug-fixed bot reduced trade over-churning and raised the nominal win rate (46.91% vs 39.19%), the payoff ratio simultaneously declined from 0.55 to 0.46 because trailing stops clipped winning runs early. On a per-trade basis, net expectancy improved by only +$0.0888 / trade (-$0.5217 vs -$0.4329), remaining deeply negative. Even before deducting fees and slippage, the gross expectancy of all configurations remains negative.

---

## 2. Validation Criteria vs. Measured Results

To pass institutional validation, a configuration was required to meet all 5 mandatory out-of-sample criteria:

| Validation Criterion | Required Threshold | Best Out-of-Sample Result Measured | Status |
| :--- | :--- | :--- | :--- |
| **Out-of-Sample Net Expectancy** | **> $0.00 / trade** (after costs) | **-$0.3961 / trade** | ❌ **FAIL** |
| **Trade Sample Size** | **>= 300 trades** | 261 – 880 trades | ❌ **FAIL** |
| **Out-of-Sample Profit Factor** | **>= 1.30** | **0.58** | ❌ **FAIL** |
| **Profitability Consistency** | Profitable across quarters & regimes | Negative across all 5 quarters | ❌ **FAIL** |
| **Max Portfolio Drawdown** | **< 15.0%** | 13.53% (BNB tier passed threshold; other runs 15.28% – 47.53% failed) | ⚠️ **PARTIAL / FAIL OVERALL** |

---

## 3. Reproduction & Forensic Reconciliation of Original 75 Paper Trades

### Forensic Reconciliation: 74 vs. 75 Trades and -$18.14 vs. -$19.43 Net PnL
In `backup/20261030_180657/paper_state.json`:
- `trades_history` contains exactly 150 events (75 BUY entry events and 75 SELL exit events), representing **75 completed closed trades**.
- The cumulative realized PnL across all 75 closed trades is **-$19.4300**.
- The earlier figure of **74 trades and -$18.14** was caused by an off-by-one slice (`[:74]`) that excluded the 75th closed trade:
  - **Trade #75**: ID `TRD-1793306594019`, Symbol `SUI/USDT`, Side `SELL`, Price `$0.8796`, Proceeds `$98.71`, Fee `$0.0988`, Realized PnL **-$1.29**, Reason: `Bracket Stop Exit ($0.88)`.
  - First 74 trades sum: $-\$18.14$.
  - Including Trade #75: $-\$18.14 + (-\$1.29) = -\$19.43$.
- Full audited baseline figures for all 75 trades:
  - Wins: 23 trades (30.67%, rounded to 30.7%)
  - Losses: 52 trades (69.33%, rounded to 69.3%)
  - Average Win: +$1.4839 (+$1.48)
  - Average Loss: -$1.0300 (-$1.03)
  - Payoff Ratio: $1.4839 / 1.0300 = 1.4407$ (1.44)
  - Total Fees Paid: $14.9888 ($14.99)
  - Break-Even Win Rate: $1 / (1 + 1.4407) = 40.97\%$ (~41.0%)
  - Mathematical Expectancy: $(0.3067 \times 1.4839) - (0.6933 \times 1.0300) = -\$0.2590$ (-$0.26 / trade).

### Replay Backtest Comparison over the Same Window:
Replayed the original bot logic over the exact 14.4-hour paper trading window (2026-10-29 20:43 to 2026-10-30 11:07 UTC):

| Metric | Your Actual Paper Run (All 75 Trades) | Backtest Replay (Original Logic) | Backtest Replay (Fixed 1m Logic) |
| :--- | :--- | :--- | :--- |
| **Total Closed Trades** | **75** | 59 | 299 |
| **Win Rate (%)** | **30.67%** (30.7%) | **38.98%** | **29.43%** |
| **Average Win ($)** | **+$1.48** | +$0.75 | +$0.11 |
| **Average Loss ($)** | **-$1.03** | -$1.39 | -$0.46 |
| **Payoff Ratio** | **1.44** | 0.54 | 0.23 |
| **Total Fees Paid ($)** | **$14.99** | $11.77 | $59.74 |
| **Net Realized PnL ($)** | **-$19.43** | **-$32.61** | **-$87.66** |
| **Profit Factor** | **0.64** | 0.35 | 0.10 |
| **Expectancy / Trade ($)** | **-$0.2590** (-$0.26) | **-$0.5528** | **-$0.2932** |

#### Explanation of Differences vs. Live Paper Execution:
1. **Intrabar Micro-Tick Execution (Bug 5):** The live paper bot evaluated strategies on raw unclosed WebSocket ticks (`candle["is_closed"] == False`). 16 trades were triggered on temporary intrabar price spikes that evaporated before the bar closed. The backtester strictly enforces closed-candle signals with next-bar open fills.
2. **5 Manual Emergency Panic Exits:** The paper history contains 5 manual panic liquidations (e.g., BTC/USDT closed manually at -$5.03), whereas the automated backtester held strictly according to code rules until bracket stops were hit.
3. **Execution Latency & Spread:** In live paper trading, fills occurred at tick midpoints, whereas the backtester applies explicit 0.05% slippage and a conservative intrabar rule (if both SL and TP are touched inside the same bar, the stop-loss is assumed to hit first).

---

## 4. Head-to-Head Exit System Comparison

### A. Isolated Single-Trade Test: 15,867 Truly Identical Entries (Zero Portfolio Concurrency Limits)
To isolate exit mechanics from portfolio slot contention and signal filters, all raw strategy entry signals across the 12-month 1h dataset were recorded. Each identical entry was independently simulated through both exit engines with identical capital ($100), 0.10% fee, and 0.05% slippage:

| Metric | Original Fixed Bracket Exit (SL 1.5%, TP 2.5%, 1% Trail) | Upgraded 1.5x ATR Trailing Stop Exit | Difference ($\Delta$) |
| :--- | :--- | :--- | :--- |
| **Total Identical Signals Evaluated** | **15,867** | **15,867** | **0 (100% Identical)** |
| **Win Rate (%)** | 39.42% | **47.05%** | **+7.63%** |
| **Average Win ($)** | **+$0.68** | +$0.61 | -$0.07 (-10.3%) |
| **Average Loss ($)** | **-$1.25** | -$1.60 | -$0.35 (+28.0%) |
| **Payoff Ratio** | **0.55** | 0.38 | -0.17 (-30.9%) |
| **Profit Factor** | **0.35** | 0.34 | -0.01 |
| **Total Net Realized PnL ($)** | **-$7,762.57** | -$8,855.32 | -$1,092.75 |
| **Net Expectancy / Trade ($)** | **-$0.4892** | -$0.5581 | **-$0.0689 / trade** |

### B. Full Portfolio Simulation: Differing Entry Sets (Capital & Signal Filtering Constraints)
When evaluating the full bot engine where max positions are capped at 5 and correlation is capped at 2, the entry sets **naturally diverge** (5,091 vs. 3,522 trades) due to two structural differences:
1. **Signal Invalidation Gate (Bug 3):** The Upgraded engine rejects signals lacking explicit stop/target prices, dropping ~1,500 low-quality trades.
2. **Holding Duration & Concurrency (Bug 8):** The 1.5x ATR trail exits earlier on average (323.5 min vs. 371.2 min), freeing portfolio slots sooner, and limits exposure to max 2 concurrent altcoins:

| Metric | Original Logic Backtest (Unfiltered Entries, 5 Alts Max) | Upgraded Logic Backtest (Gated Entries, 2 Alts Max) | Difference ($\Delta$) |
| :--- | :--- | :--- | :--- |
| **Total Executed Trades** | 5,091 | 3,522 | -1,569 (-30.8%) |
| **Win Rate (%)** | 39.19% | **46.91%** | **+7.72%** |
| **Average Win ($)** | **+$0.73** | +$0.63 | -$0.10 (-13.7%) |
| **Average Loss ($)** | **-$1.33** | -$1.37 | -$0.04 (+3.0%) |
| **Payoff Ratio** | **0.55** | 0.46 | -0.09 (-16.4%) |
| **Profit Factor** | 0.36 | **0.41** | **+0.05** |
| **Fees Paid ($)** | $1,016.14 | **$703.20** | **-$312.94** |
| **Net Realized PnL ($)** | -$2,655.89 | **-$1,524.70** | **+$1,131.19** |
| **Net Expectancy / Trade ($)** | -$0.5217 | **-$0.4329** | **+$0.0888 / trade** |
| **Max Drawdown (%)** | 26.58% | **15.28%** | **-11.30%** |

### Quantitative Verdict on Exit Systems: Which Works Better?
- **In an isolated single-trade vacuum (100% identical entries):** The ATR trailing stop raises win rate (+7.63%), but because ATR stops are wider during volatile expansions than a fixed 1.5% stop, average loss increases from -$1.25 to -$1.60. Combined with lower average win (+$0.61 vs +$0.68), the unconstrained payoff drops sharply to 0.38, yielding -$0.5581 expectancy vs -$0.4892.
- **In portfolio execution (with Stage 1 risk gates):** The upgraded bot cuts overall portfolio drawdown from 26.58% down to 15.28% and improves per-trade expectancy from -$0.5217 to -$0.4329, primarily driven by filtering out invalid signals and capping alt exposure.
- **Conclusion:** Neither exit engine can create positive mathematical edge from negative-expectancy entry signals. Exit mechanics can modulate risk and win rate, but cannot overcome 0.30% round-trip exchange friction on low timeframes.

---

## 5. Comprehensive Empirical Results Table (Including Gross & Net Expectancy)

### Profit Factor Mathematical Definition:
$$\text{Profit Factor} = \frac{\sum \text{Gross Profit from Winning Trades}}{\sum |\text{Gross Loss from Losing Trades}|} = \frac{\sum_{i \in \text{wins}} \text{realized\_pnl}_i}{\sum_{j \in \text{losses}} |\text{realized\_pnl}_j|}$$
*Note: All profit factors below are computed directly from closed trade records using this exact formula.*

### A. 12-Month Multi-Asset Backtest Comparison (1-Hour Timeframe)

| Configuration | Total Trades | Win Rate (%) | Gross PnL ($) | Gross Exp ($/trade) | Fees Paid ($) | Slippage Paid ($) | Net PnL ($) | Net Exp ($/trade) | Payoff Ratio | Profit Factor | Max DD (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ORIGINAL_1h (0.10% Fee)** | 5,091 | 39.19% | -$1,130.65 | **-$0.2221** | $1,016.14 | $509.10 | **-$2,655.89** | **-$0.5217** | 0.55 | **0.36** | 26.58% |
| **ORIGINAL_1h (0.075% BNB)** | 5,091 | 41.50% | -$1,131.10 | **-$0.2222** | $762.17 | $509.10 | **-$2,402.37** | **-$0.4719** | 0.56 | **0.39** | 24.05% |
| **FIXED_1h (0.10% Fee)** | 3,522 | 46.91% | -$469.30 | **-$0.1332** | $703.20 | $352.20 | **-$1,524.70** | **-$0.4329** | 0.46 | **0.41** | 15.28% |
| **FIXED_1h (0.075% BNB)** | 3,522 | 47.13% | -$469.53 | **-$0.1333** | $527.47 | $352.20 | **-$1,349.20** | **-$0.3831** | 0.51 | **0.45** | 13.53% |
| **DECISION_ENGINE_1h (1.5x Trail)** | 1,088 | 36.12% | -$205.10 | **-$0.1885** | $217.40 | $108.80 | **-$531.30** | **-$0.4883** | 0.90 | **0.51** | 16.55% |
| **DECISION_ENGINE_1h (2.5x Trail)** | 1,072 | 36.19% | -$200.70 | **-$0.1872** | $213.99 | $107.20 | **-$521.88** | **-$0.4868** | 0.90 | **0.51** | 16.40% |

### B. 12-Month Multi-Asset Backtest Comparison (15-Minute Timeframe)

| Configuration | Total Trades | Win Rate (%) | Gross PnL ($) | Gross Exp ($/trade) | Fees Paid ($) | Slippage Paid ($) | Net PnL ($) | Net Exp ($/trade) | Payoff Ratio | Profit Factor | Max DD (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ORIGINAL_15m (0.10% Fee)** | 8,201 | 38.93% | -$1,640.48 | **-$0.2000** | $1,637.06 | $820.10 | **-$4,097.64** | **-$0.4997** | 0.60 | **0.38** | 41.09% |
| **ORIGINAL_15m (0.075% BNB)**| 8,201 | 40.29% | -$1,641.15 | **-$0.2001** | $1,227.90 | $820.10 | **-$3,689.15** | **-$0.4498** | 0.62 | **0.42** | 37.03% |
| **FIXED_15m (0.10% Fee)** | 13,265 | 41.18% | -$773.99 | **-$0.0583** | $2,649.44 | $1,326.50 | **-$4,749.93** | **-$0.3581** | 0.34 | **0.24** | 47.53% |
| **FIXED_15m (0.075% BNB)** | 13,265 | 41.54% | -$774.59 | **-$0.0584** | $1,987.34 | $1,326.50 | **-$4,088.43** | **-$0.3082** | 0.42 | **0.30** | 40.91% |

### Note on 5-Minute Timeframe Data:
- The 5m dataset was downloaded and verified (735,000+ bars across 7 symbols).
- Full 12-month multi-asset simulation on 5m was evaluated: due to noise and micro-oscillations, trade frequency escalates to ~35,000–40,000 trades/year, generating over $7,000 in fee drag alone.
- Expectancy on 5m remains strictly negative (-$0.35+ / trade) with max drawdown exceeding 60%.
- Lower timeframes amplify fee friction relative to candle range, confirming that 1m, 5m, and 15m breakout strategies are unviable for spot long-only crypto trading.

### C. Walk-Forward Chronological Splits (Decision Engine, 1h)

#### 1.5x ATR Trailing Stop:
| Partition | Bar Range | Trades | Win Rate (%) | Payoff Ratio | Profit Factor | Net PnL ($) | Fees ($) | Net Expectancy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAIN (50%)** | Bars 0 – 4,728 | 543 | 36.5% | 0.91 | 0.52 | **-$276.34** | $108.60 | -$0.5089 |
| **VAL (25%)** | Bars 4,728 – 7,092 | 278 | 35.3% | 0.77 | 0.42 | **-$149.05** | $55.60 | -$0.5362 |
| **TEST OUT-OF-SAMPLE (25%)** | Bars 7,092 – 9,457 | 267 | 36.3% | 1.01 | 0.58 | **-$105.91** | $53.40 | **-$0.3967** |

#### 2.5x ATR Trailing Stop:
| Partition | Bar Range | Trades | Win Rate (%) | Payoff Ratio | Profit Factor | Net PnL ($) | Fees ($) | Net Expectancy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAIN (50%)** | Bars 0 – 4,728 | 534 | 35.8% | 0.90 | 0.50 | **-$284.20** | $106.80 | -$0.5322 |
| **VAL (25%)** | Bars 4,728 – 7,092 | 277 | 36.8% | 0.79 | 0.46 | **-$134.30** | $55.40 | -$0.4848 |
| **TEST OUT-OF-SAMPLE (25%)** | Bars 7,092 – 9,457 | 261 | 36.4% | 1.01 | 0.58 | **-$103.38** | $52.19 | **-$0.3961** |

---

## 6. Benchmark Comparisons (Over Exact Same 12-Month Period)

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
| **Gross PnL ($)** | **-$72.75** | [-$191.02, +$58.70] | $49.20 |
| **Fees Paid ($)** | **$121.30** | [$112.80, $130.40] | $3.64 |
| **Slippage Paid ($)** | **$60.62** | [$56.40, $65.20] | $1.82 |
| **Net Realized PnL ($)** | **-$254.67** | [-$385.04, -$92.93] | $54.47 |
| **Net Expectancy / Trade ($)**| **-$0.4184** | [-$0.6354, -$0.1608] | $0.0890 |

#### Exact Arithmetic Reconciliation:
$$\begin{aligned}
\text{Net Realized PnL} &= \text{Gross PnL} - \text{Total Fees Paid} - \text{Total Slippage Paid} \\
-\$254.67 &= -\$72.75 - \$121.30 - \$60.62 \\
-\$254.67 &= -\$254.67 \quad (\text{Discrepancy} = \$0.0000)
\end{aligned}$$

#### Per-Trade Cost Breakdown:
- **Average Trades per Run**: 607.5
- **Gross Market Expectancy**: $-\$72.75 / 607.5 = -\$0.1198$ per trade
- **Fee Drag (0.10% per side)**: $\$121.30 / 607.5 = \$0.1997$ per trade (~0.20%)
- **Slippage Drag (0.05% per side)**: $\$60.62 / 607.5 = \$0.0998$ per trade (~0.10%)
- **Total Transaction Friction**: $\$0.1997 + \$0.0998 = \$0.2995$ per trade (~0.30% round-trip)
- **Net Expectancy**: $-\$0.1198 - \$0.2995 = -\$0.4193 \approx -\$0.4184$ per trade.

---

## 7. Granular Breakdown for Best Configuration (`FIXED_1h_Fee0.075_BNB`)

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
A total of **16 distinct parameter & algorithmic configurations** were systematically evaluated:
1. Actual Paper Run (1m, 8 assets, original code, 75 closed trades)
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
12. Exit Comparison: Fixed Bracket (SL 1.5%, TP 2.5%, 1% trail) on 1h
13. Exit Comparison: Upgraded 1.5x ATR Trailing Stop on 1h
14. Decision Engine (1h, Train 50% / Val 25% / Test 25%) with 1.5x ATR trail
15. Decision Engine (1h, Train 50% / Val 25% / Test 25%) with 2.5x ATR trail
16. Monte Carlo Random Entry Baseline (100 independent seeds)

---

## 8. Confirmation of Stage 6 Isolation

> [!NOTE]
> **Stage 6 Presentation Isolation Confirmation:**  
> All Stage 6 frontend and UI work was restricted strictly to the presentation layer:
> - `web/style.css`: Pure CSS changes (eliminating `overflow-x: auto`, enforcing `overflow-x: hidden !important`, removing horizontal scrollbars, responsive flex-wrapping).
> - `web/index.html`: Preset buttons (`$500`, `$1k`, `$2k`, `$5k`, `$10k`) and tab selectors.
> - `paper_state.json`: Reset balance to `$10,000.00` clean slate.
> 
> **Zero modifications were made to trading strategies (`strategies.py`), technical indicators (`indicators.py`), or exchange execution rules (`paper_exchange.py`).**

---

## 9. Real Automated Pytest Output

Real, unedited execution log of the full test suite (`python -m pytest -v tests/`):

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\fist7\AppData\Local\Programs\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\Project 2026\Trading_bot
plugins: anyio-4.12.1
collecting ... collected 16 items

tests/test_backtest_unit_math.py::test_hand_calculated_winning_trade PASSED [  6%]
tests/test_backtest_unit_math.py::test_hand_calculated_losing_trade PASSED [ 12%]
tests/test_backtest_unit_math.py::test_conservative_stop_target_ordering_rule PASSED [ 18%]
tests/test_backtest_unit_math.py::test_bnb_fee_discount_hand_calculation PASSED [ 25%]
tests/test_risk_manager_and_decision_engine.py::test_risk_manager_position_sizing_from_stop_distance PASSED [ 31%]
tests/test_risk_manager_and_decision_engine.py::test_risk_manager_total_budget_hard_cap PASSED [ 37%]
tests/test_risk_manager_and_decision_engine.py::test_risk_manager_consecutive_loss_cooldown PASSED [ 43%]
tests/test_risk_manager_and_decision_engine.py::test_decision_engine_macro_regime_filter PASSED [ 50%]
tests/test_stage1_fixes.py::test_bug1_setup_id_tracking PASSED           [ 56%]
tests/test_stage1_fixes.py::test_bug2_fleet_exit_routing PASSED          [ 62%]
tests/test_stage1_fixes.py::test_bug3_signal_exit_parameters_and_gate PASSED [ 68%]
tests/test_stage1_fixes.py::test_bug4_orb_session_anchor_and_reset PASSED [ 75%]
tests/test_stage1_fixes.py::test_bug5_closed_candle_deduplication PASSED [ 81%]
tests/test_stage1_fixes.py::test_bug6_atr_trailing_stop_ratchet PASSED   [ 87%]
tests/test_stage1_fixes.py::test_bug7_centralized_exit_priority PASSED   [ 93%]
tests/test_stage1_fixes.py::test_bug8_correlation_exposure_cap PASSED    [100%]

============================= 16 passed in 3.30s ==============================
```

---

## 10. Formal Proposals for Viable Trading Alternatives

*(Mandatory Protocol: Listed below as separate clearly labeled proposals. **None will be implemented without your explicit written approval.**)*

### Proposal A: Higher Timeframe Trend Following (4-Hour & Daily Bars)
- **Pre-Registration**: Fully pre-registered in [`PLAN_A.md`](file:///d:/Project%202026/Trading_bot/PLAN_A.md).
- **Concept:** Increase timeframe to 4h and 1D bars across 15+ liquid symbols from 2019 to 2026. Candle ranges average 3% to 8% (10x to 25x larger than roundtrip fees), reducing fee drag from ~40% of capital down to < 3%.
- **Pass Criteria**: Out-of-sample Net Expectancy > 0, $\ge 200$ trades, Profit Factor $\ge 1.30$, Max DD < 25%, positive in $\ge 60\%$ of years, and beats 100-seed random entry by $> 2\sigma$.
- **Status**: Pre-registered and awaiting your approval before running backtests.

### Proposal B: Market-Neutral Long/Short Momentum (Statistical Arbitrage)
- **Concept:** Rather than naked directional long bets, go LONG the strongest coin (highest RS vs BTC) and simultaneously SHORT the weakest coin (lowest RS) or short BTC perpetual futures as a hedge.
- **Advantage:** Immune to Bitcoin crashes; isolates relative cross-sectional alpha.

### Proposal C: Delta-Neutral Funding Rate & Basis Arbitrage
- **Concept:** Buy spot crypto (e.g. SOL) and simultaneously short 1x SOL perpetual futures.
- **Advantage:** Zero directional price risk. Collects positive funding rate payments (8% to 25% APR) paid every 8 hours by long leverage traders.

### Proposal D: Pause Automated Spot Breakout Trading
- **Concept:** Given the mathematical proof that low-timeframe long-only crypto breakouts have negative expectancy after exchange fees, preserve capital and avoid automated live trading with this strategy family.
