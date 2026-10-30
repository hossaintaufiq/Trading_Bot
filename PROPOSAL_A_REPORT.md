# PROPOSAL A EMPIRICAL VALIDATION REPORT (PROPOSAL_A_REPORT.md)

**Date**: 2026-10-30  
**Role**: Senior Quantitative Developer  
**Status**: Comprehensive Empirical Validation Completed — **PROPOSAL A FAILED VALIDATION**  
**Execution Environment**: Binance Spot Historical Data (17 Liquid Assets), 2019-01-01 to 2026-10-30 (~7.8 Years, 236,929 4-Hour Bars).  
**Cost Assumptions**: Taker Fee 0.10% (and 0.075% BNB Tier), Slippage 0.05% per side (Total Round-Trip Friction: 0.30% / 0.25%). Next-bar open execution, closed candles only, conservative intrabar stop-loss priority.

---

## 1. Executive Verdict & Core Finding

> [!CAUTION]
> **OFFICIAL QUANTITATIVE VERDICT: PROPOSAL A FAILED VALIDATION.**  
> In strict accordance with the pre-registered protocol in [`PLAN_A.md`](file:///d:/Project%202026/Trading_bot/PLAN_A.md) and institutional quantitative standards:
> - **Out-of-Sample Net Expectancy**: **-$0.2283 / trade** (Required $> \$0.00$) — ❌ **FAILED**
> - **Out-of-Sample Profit Factor**: **0.85** (Required $\ge 1.30$) — ❌ **FAILED**
> - **Annual Consistency**: Positive in only **2 of 8 calendar years (25.0%)** (Required $\ge 60.0\%$) — ❌ **FAILED**
> - **Statistical Significance vs Random**: **1.37$\sigma$** above 100-seed random entry (Required $> 2.0\sigma$) — ❌ **FAILED**
> 
> **Zero pass criteria have been lowered, no rules were modified post-hoc, and automated live trading remains disabled.**

---

## 2. Universe & Historical Data Survivorship Bias Audit

All 17 liquid spot symbols were downloaded from Binance REST API across the entire ~7.8-year historical window (January 1, 2019 to October 30, 2026). Late listing dates are tracked explicitly to avoid survivorship bias:

| Symbol | Timeframe | Total Bars | First Available Bar | Last Available Bar | Survivorship / Listing Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **ETH/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **BNB/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **XRP/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **ADA/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **TRX/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **LTC/USDT** | 4h | 17,150 | 2019-01-01 | 2026-10-30 | Full Period (7.8 Years) |
| **LINK/USDT** | 4h | 17,058 | 2019-01-16 | 2026-10-30 | Listed 2019-01-16 (Omitted 15 days) |
| **ATOM/USDT** | 4h | 16,442 | 2019-04-29 | 2026-10-30 | Listed 2019-04-29 (Omitted 118 days) |
| **DOGE/USDT** | 4h | 16,040 | 2019-07-05 | 2026-10-30 | Listed 2019-07-05 (Omitted 185 days) |
| **MATIC/USDT**| 4h | 11,778 | 2019-04-26 | 2024-09-10 | Listed 2019-04-26, Migrated 2024-09 |
| **SOL/USDT** | 4h | 13,626 | 2020-08-11 | 2026-10-30 | Listed 2020-08-11 (Omitted 588 days) |
| **DOT/USDT** | 4h | 13,580 | 2020-08-18 | 2026-10-30 | Listed 2020-08-18 (Omitted 595 days) |
| **UNI/USDT** | 4h | 13,405 | 2020-09-17 | 2026-10-30 | Listed 2020-09-17 (Omitted 625 days) |
| **AVAX/USDT** | 4h | 13,374 | 2020-09-22 | 2026-10-30 | Listed 2020-09-22 (Omitted 630 days) |
| **NEAR/USDT** | 4h | 13,242 | 2020-10-14 | 2026-10-30 | Listed 2020-10-14 (Omitted 652 days) |
| **SUI/USDT** | 4h | 7,654 | 2023-05-03 | 2026-10-30 | Listed 2023-05-03 (Omitted 1,583 days) |
| **TOTAL** | **4h** | **236,929** | — | — | **17 Assets Processed** |

---

## 3. In-Sample Parameter Grid Search (70% Partition: 2019-01-01 to 2024-06-24)

Under pre-registered rules, 54 candidate parameter combinations were evaluated across the first 70% of chronological bars (12,005 bars).
- Trend Filter: EMA $T \in \{150, 200\}$
- Donchian Breakout: $N \in \{20, 40, 55\}$ bars
- Initial Risk Stop: $K \in \{2.0, 2.5, 3.0\} \times \text{ATR}$
- ATR Runner Trail: $M \in \{2.0, 2.5, 3.0\} \times \text{ATR}$

### Top 5 In-Sample Configurations (Ranked by Profit Factor):

| Config ID | EMA ($T$) | Donchian ($N$) | Stop ATR ($K$) | Trail ATR ($M$) | Trades | Win Rate (%) | Payoff | Profit Factor | Net PnL ($) | Expectancy ($/trade) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#26 (BEST)** | **150** | **55** | **3.0** | **2.5** | **1,920** | **38.07%** | **1.54** | **0.95** | **-$208.49** | **-$0.1086** |
| **#27** | 150 | 55 | 3.0 | 3.0 | 1,874 | 37.94% | 1.54 | 0.94 | -$218.74 | -$0.1167 |
| **#53** | 200 | 55 | 3.0 | 2.5 | 1,866 | 37.83% | 1.54 | 0.94 | -$231.86 | -$0.1243 |
| **#25** | 150 | 55 | 3.0 | 2.0 | 2,018 | 37.86% | 1.52 | 0.93 | -$295.89 | -$0.1466 |
| **#18** | 150 | 40 | 3.0 | 3.0 | 2,050 | 38.78% | 1.47 | 0.93 | -$258.17 | -$0.1259 |

> [!NOTE]
> **Critical In-Sample Finding:**
> Not a single parameter combination achieved positive net PnL even on the in-sample training partition. The very best configuration (#26) achieved a profit factor of 0.95 and net expectancy of -$0.1086 / trade.

---

## 4. Neighbor Parameter Robustness Check ($\pm 20\%$)

To verify whether Config #26 represented an overfit spike or stable performance plateaus, parameter neighbors were tested on the in-sample partition:

| Parameter Variation | Test Value | Trades | Win Rate (%) | Profit Factor | Net PnL ($) | Expectancy ($/trade) | Robustness Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Config #26)**| $K=3.0, M=2.5, N=55$ | 1,920 | 38.07% | 0.95 | -$208.49 | -$0.1086 | Reference |
| **Stop ATR -20%** | $K=2.40$ | 1,980 | 39.14% | 0.84 | -$634.48 | -$0.3204 | Loss increased (tighter stops clipped) |
| **Stop ATR +20%** | $K=3.60$ | 1,882 | 37.25% | 0.99 | -$20.61 | -$0.0110 | Marginally improved (wider room) |
| **Trail ATR -20%** | $M=2.00$ | 2,018 | 37.86% | 0.93 | -$295.89 | -$0.1466 | Stable negative |
| **Trail ATR +20%** | $M=3.00$ | 1,874 | 37.94% | 0.94 | -$218.74 | -$0.1167 | Stable negative |
| **Entry Window -20%** | $N=44$ bars | 2,051 | 38.18% | 0.93 | -$266.33 | -$0.1299 | Stable negative |
| **Entry Window +20%** | $N=66$ bars | 1,810 | 38.62% | 0.98 | -$72.47 | -$0.0400 | Stable negative |

The strategy behavior is smooth and non-fragile across $\pm 20\%$ parameter shifts; however, it is **consistently negative across all variations**.

---

## 5. Frozen Out-of-Sample Test Evaluation (Final 30%: 2024-06-24 to 2026-10-30)

Config #26 was evaluated **EXACTLY ONCE** on the out-of-sample test partition (5,145 bars) under both cost tiers:

| Cost Tier | Closed Trades | Win Rate (%) | Gross PnL ($) | Fees Paid ($) | Slippage Paid ($) | Net Realized PnL ($) | Net Expectancy ($/trade) | Payoff Ratio | Profit Factor | Max Drawdown (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Taker (0.10%)** | 766 | 34.46% | +$54.72 | $153.10 | $76.51 | **-$174.89** | **-$0.2283** | 1.62 | **0.85** | 2.66% |
| **BNB Discount (0.075%)** | 766 | 35.12% | +$54.58 | $114.84 | $76.53 | **-$136.80** | **-$0.1786** | 1.63 | **0.88** | 2.46% |

### Exact Arithmetic Reconciliation:
$$\begin{aligned}
\text{Net Realized PnL} &= \text{Gross PnL} - \text{Fees Paid} - \text{Slippage Paid} \\
-\$174.89 &= +\$54.72 - \$153.10 - \$76.51 \\
-\$174.89 &= -\$174.89 \quad (\text{Discrepancy} = \$0.0000)
\end{aligned}$$

---

## 6. Year-by-Year Performance Breakdown (2019 to 2026, Full 7.8-Year Window)

To detect whether performance was distorted by macro regimes, each year was evaluated individually:

| Year | Market Context | Trades | Win Rate (%) | Payoff Ratio | Profit Factor | Fees Paid ($) | Net Realized PnL ($) | Net Expectancy ($/trade) | Profitable? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2019** | Post-Winter Chop & Rebound | 246 | 41.5% | 1.30 | 0.92 | $49.20 | **-$44.02** | -$0.1789 | ❌ No |
| **2020** | Halving & Parabolic Expansion | 348 | 43.4% | 1.36 | **1.04** | $69.60 | **+$24.13** | **+$0.0693** | ✅ **YES** |
| **2021** | Historic Macro Bull Market | 506 | 39.9% | 1.87 | **1.23** | $101.20 | **+$286.16** | **+$0.5655** | ✅ **YES** |
| **2022** | Macro Bear & Deleveraging | 252 | 33.7% | 1.11 | 0.56 | $50.40 | **-$192.59** | -$0.7643 | ❌ No |
| **2023** | Accumulation / Sideways Chop | 370 | 33.5% | 1.48 | 0.74 | $74.00 | **-$158.63** | -$0.4287 | ❌ No |
| **2024** | ETF Rally & Chop | 431 | 37.4% | 1.45 | 0.86 | $86.20 | **-$97.53** | -$0.2263 | ❌ No |
| **2025** | Range-Bound Consolidation | 263 | 32.7% | 1.67 | 0.81 | $52.60 | **-$83.23** | -$0.3164 | ❌ No |
| **2026** | Macro Pullback & Rotation | 270 | 31.1% | 1.48 | 0.67 | $54.00 | **-$117.67** | -$0.4358 | ❌ No |
| **TOTAL** | **7.8 Years** | **2,686** | **37.04%** | **1.56** | **0.92** | **$537.20** | **-$383.38** | **-$0.1427** | **2 / 8 Yrs (25%)** |

> [!WARNING]
> **Regime Dependency:**
> The strategy produced positive net returns **only during 2020 and 2021** (the historic zero-interest-rate liquidity cycle). In all subsequent 5 years (2022 through 2026), it lost money continuously due to whipsaws and false breakouts in mature crypto markets.

---

## 7. Benchmark Comparisons (Over Exact Same OOS Test Window)

### Benchmark 1: Buy-and-Hold Bitcoin (`BTC/USDT`)
- **Period**: 2024-06-24 to 2026-10-30 (2.3 years)
- **Start Price**: $59,306.72 | **End Price**: $78,235.15
- **Buy-and-Hold Return**: **+31.92%**
- **Net PnL on $10,000 Portfolio**: **+$3,191.62**
- **Max Portfolio Drawdown**: **53.45%**

### Benchmark 2: 100-Seed Monte Carlo Random-Entry Baseline (Same Exits & Costs)
- **Mean Trades per Seed**: 1,603.5
- **Mean Win Rate**: 32.58%
- **Mean Profit Factor**: 0.66
- **Mean Net Realized PnL**: -$506.05
- **Mean Expectancy**: -$0.3157 / trade ($\sigma = \$0.0638$)
- **Proposal A Expectancy**: -$0.2283 / trade
- **Statistical Z-Score**:
  $$Z = \frac{-\$0.2283 - (-\$0.3157)}{\$0.0638} = \mathbf{+1.37\sigma}$$

While Proposal A outperformed pure random entries by $1.37\sigma$, it failed the pre-registered threshold of $> 2.0\sigma$ required to demonstrate true statistical skill beyond noise.

---

## 8. Final Pre-Registered Validation Audit (PLAN_A.md)

| Pre-Registered Criterion | Required Threshold | Measured Value (Out-of-Sample) | Status |
| :--- | :--- | :--- | :--- |
| **1. Net Expectancy** | **$> \$0.00$ / trade** | **-$0.2283 / trade** | ❌ **FAIL** |
| **2. Sample Size** | **$\ge 200$ trades** | **766 trades** | ✅ **PASS** |
| **3. Profit Factor** | **$\ge 1.30$** | **0.85** | ❌ **FAIL** |
| **4. Max Drawdown** | **$< 25.0\%$** | **2.66%** | ✅ **PASS** |
| **5. Consistency** | **Positive in $\ge 60\%$ of years** | **25.0% (2 of 8 years)** | ❌ **FAIL** |
| **6. Monte Carlo Edge** | **$> 2.0\sigma$ over random** | **1.37$\sigma$** | ❌ **FAIL** |

### Official Verdict: **PROPOSAL A FAILED VALIDATION** (Failed 4 of 6 criteria).
In strict accordance with pre-registered rules, development on Proposal A stops immediately. No pass criteria have been lowered.

---

## 9. Total Configurations Tested in Research Program

Across all stages of this research engagement, an exact total of **78 configurations** were systematically evaluated and logged in `results/`:
1. Actual Paper Run (1m, 8 coins, 75 closed trades)
2. Paper Replay Original Logic (1m, 14.4h window)
3. Paper Replay Fixed Logic (1m, 14.4h window)
4–11. Baseline Comparisons (Original vs Fixed on 1h and 15m, 0.10% and 0.075% fee tiers) [8 configs]
12. Truly Identical Single-Trade Exit Comparison (15,867 signals)
13. Decision Engine 1h (1.5x ATR trail)
14. Decision Engine 1h (2.5x ATR trail)
15. 100-Seed Random Entry Baseline (1h)
16–69. Proposal A In-Sample Grid Search (54 parameter combinations on 4h)
70–75. Proposal A Neighbor Robustness Check (6 variations)
76. Proposal A Out-of-Sample Test (0.10% fee)
77. Proposal A Out-of-Sample Test (0.075% fee)
78. Proposal A 100-Seed Random Baseline (4h)

---

## 10. Quantitative Conclusion

Low-timeframe (1m, 5m, 15m) and intermediate-timeframe (1h, 4h) **long-only spot breakout trading does not generate positive net expectancy in crypto markets after exchange fees and slippage.** 

While expanding from 1m to 4h dramatically reduced fee drag (from >70% of PnL down to ~8%), spot crypto breakouts suffer from high false-breakout rates (62–66% loss rate) in all modern market regimes outside parabolic macro bull runs. Directional long-only spot trading cannot sustain positive expectancy across full market cycles.

