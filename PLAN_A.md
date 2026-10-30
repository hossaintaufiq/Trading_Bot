# PRE-REGISTRATION PROTOCOL: PROPOSAL A (PLAN_A.md)
**Status**: PRE-REGISTERED (Frozen Prior to Execution)  
**Author**: Senior Quantitative Developer  
**Date**: 2026-10-30  
**Objective**: Empirically evaluate whether a higher-timeframe (4-Hour and Daily), multi-year trend-following system across liquid crypto assets can achieve mathematically positive net expectancy after realistic exchange fees and slippage.

---

## 1. Experimental Design & Pre-Registration Rules

> [!IMPORTANT]
> **Strict Pre-Registration Commitment:**
> This document specifies all hypothesis rules, data requirements, parameter grids, execution models, and pass/fail thresholds **BEFORE** running any backtest or viewing results.
> Under quantitative research integrity standards:
> 1. No rules, parameter ranges, or pass thresholds may be modified after viewing test results.
> 2. The out-of-sample test partition (last 30% chronologically) shall be evaluated **EXACTLY ONCE**.
> 3. No backtest runs for Proposal A shall be initiated until explicitly approved by the user.
> 4. If the strategy fails any single out-of-sample criterion, the verdict is **FAIL** and development stops.

---

## 2. Universe and Historical Data Specifications

1. **Exchange**: Binance Spot / USDT pairs.
2. **Time Horizon**: January 1, 2019 to Present (~7.8 years), encompassing:
   - 2019: Crypto Winter recovery & chop.
   - 2020–2021: Historic bull market & parabolic expansion.
   - 2022: Severe macro bear market & deleveraging.
   - 2023: Range-bound accumulation.
   - 2024–2026: Post-halving cycle expansion & macro consolidation.
3. **Timeframes**:
   - **4-Hour (4h)**
   - **Daily (1D)**
4. **Asset Universe ($\ge 15$ Liquid Symbols)**:
   - High Liquidity Tier: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`, `DOGE/USDT`
   - Mid/Large Cap Tier: `LINK/USDT`, `AVAX/USDT`, `DOT/USDT`, `LTC/USDT`, `MATIC/USDT` (or `POL/USDT`), `NEAR/USDT`, `ATOM/USDT`, `UNI/USDT`, `TRX/USDT`
5. **Data Quality Assurance**:
   - Strict timestamp sorting, deduplication, and zero-volume gap verification.
   - Missing bars reported explicitly prior to ingestion.

---

## 3. Execution & Realistic Cost Model

1. **Candle Timing**:
   - Signals computed exclusively on **CLOSED** candles ($t$).
   - Fills executed at the **OPEN** of the next candle ($t+1$).
2. **Transaction Costs**:
   - **Baseline Case**: Taker Fee = **0.10%** per side; Slippage = **0.05%** per side (Total Round-Trip Friction: **0.30%**).
   - **Discount Tier Case**: Taker Fee = **0.075%** (BNB deduction); Slippage = **0.05%** per side (Total Round-Trip Friction: **0.25%**).
3. **Execution Tie-Breaker**:
   - Conservative intrabar rule: If both Stop Loss and Take Profit / Trailing Stop price are breached within the same bar, the Stop Loss is assumed to execute first.

---

## 4. Long-Only Trend Strategy Rules & Limited Parameter Grid

To prevent data snooping and combinatorial overfitting, the strategy family is restricted to simple trend continuation rules with **at most 3 parameter values each**:

### A. Core Trend Rules (Donchian / Moving Average Breakout)
- **Regime Filter**: Price Close > Long-Term Trend Filter:
  - Parameter $T \in \{150, 200\}$ EMA (or SMA).
- **Entry Trigger**: Price Close breaks above the $N$-period rolling High (Donchian Channel):
  - Parameter $N \in \{20, 40, 55\}$ bars.
- **Initial Risk Stop**: Placed at Entry Price minus $K \times \text{ATR}(14)$:
  - Parameter $K \in \{2.0, 2.5, 3.0\}$.
- **Exit System (ATR Trailing Stop)**:
  - Once price advances by $+1R$ ($1.0 \times \text{Initial Risk}$): Move stop to Break-Even (net of fees).
  - Trailing exit: Ratchet stop upwards at Highest High since entry minus $M \times \text{ATR}(14)$:
    - Parameter $M \in \{2.0, 2.5, 3.0\}$.
  - Chandelier exit option: Close below $N_{\text{exit}}$-period low:
    - Parameter $N_{\text{exit}} \in \{10, 20\}$ bars.

Total configuration combinations for grid search on training data: $\le 18$ candidate parameter sets.

---

## 5. Train / Test Chronological Partitioning

- **In-Sample Training Partition (First 70% of chronological bars)**:
  - Used for parameter exploration, sensitivity analysis, and robustness checks.
  - Neighboring parameter stability check: The selected configuration must remain profitable if ATR multiplier or breakout length varies by $\pm 20\%$.
- **Out-of-Sample Test Partition (Final 30% of chronological bars)**:
  - **FROZEN.** Tested **EXACTLY ONCE** on the single best candidate selected from the in-sample partition.
  - Zero tuning, parameter adjustment, or post-hoc filtering permitted on this set.

---

## 6. Pre-Registered Pass / Fail Criteria (Non-Negotiable)

The configuration passes institutional validation if and only if **ALL 6** of the following conditions are simultaneously satisfied on the **Out-of-Sample (30%)** test partition:

| Criterion | Requirement | Rationale |
| :--- | :--- | :--- |
| **1. Net Expectancy** | **$> \$0.00$ per trade** (after 0.10% fee & 0.05% slippage) | Strategy must produce genuine edge net of realistic friction. |
| **2. Sample Size** | **$\ge 200$ closed trades** | Ensures statistical significance and prevents small-sample luck. |
| **3. Profit Factor** | **$\ge 1.30$** | Ratio of gross profits to gross losses must demonstrate clear asymmetric payoff. |
| **4. Max Drawdown** | **$< 25.0\%$** | Capital preservation standard for automated spot portfolio allocation. |
| **5. Consistency** | **Net Positive in $\ge 60\%$ of calendar years** | Prevents strategies whose entire PnL is derived from a single bull run anomaly. |
| **6. Monte Carlo Edge** | **Beats 100-seed random entry by $> 2.0\sigma$** | Confirms statistical validity beyond random entry timing with the same exits. |

---

## 7. Mandatory Reporting Requirements

Regardless of pass or fail outcome, the final validation report shall include:
1. **Full Year-by-Year Breakdown**: Annual net PnL, trade count, win rate, and profit factor for each year (2019 to 2026).
2. **Buy-and-Hold BTC Benchmark**: Return, max drawdown, and Sharpe ratio over the exact same test window.
3. **100-Seed Monte Carlo Random-Entry Baseline**: Mean, standard deviation, and Z-score comparison against Proposal A.
4. **Fee Sensitivity Analysis**: Full results under both 0.10% and 0.075% fee tiers.
5. **Exact Arithmetic Reconciliation**: Verification that $\text{Net PnL} = \text{Gross PnL} - \text{Fees Paid} - \text{Slippage Cost}$.

---

## 8. Failure Protocol

If any pre-registered threshold is missed:
- The strategy is declared **FAILED**.
- No parameters will be adjusted to achieve a pass.
- Work on Proposal A stops immediately.

