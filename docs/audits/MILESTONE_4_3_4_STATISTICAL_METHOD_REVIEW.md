# NEPTUNE — Milestone 4.3.4: Statistical Method Verification & Rigor Review

**Document Version**: 1.0.0  
**Audit Target**: Methodological Review of Paired Tests, Block Bootstraps & Statistical Inference  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Starting Commit Baseline**: `c1ffe20`  
**Governing Rules**: `AGENTS.md` (S-06 No Fabrication, S-07 Validated Evidence, A-08 Independent Evaluation)  

---

## 1. Executive Summary

This review critically audits the statistical methods deployed in Milestone 4.3.3. It resolves ambiguities regarding matched observation definitions, clarifies the exact mechanics and parameter notation of the block bootstrap, evaluates the treatment of unmatched trades, and determines whether the existing historical dataset can support a defensible quantitative inference of strategy edge.

### Core Audit Conclusions:
1. **The 90 Matched Observations**: Represent **matched executed trades** between Baseline and H7. They are not raw market opportunities or time buckets.
2. **Treatment of Unmatched Trades**: The paired t-test ($p = 0.5734$) **completely discarded 187 losing baseline trades (-$227.68) and 36 profitable H7 trades (+$125.10)**. Therefore, the paired t-test is an incomplete test: it demonstrates that identical entries yield identical exits, but it does not evaluate portfolio-level loss-avoidance.
3. **Clarification of Bootstrap Parameter $B=5$**: In Milestone 4.3.3, "B=5" was an ambiguous typographical shorthand for **block length $L = 5$ trades**, while the number of bootstrap replications was $M = 2,000$.
4. **Resampled Quantity**: The reported 95% confidence interval of **[-$0.84, +$1.16]** is strictly an interval for **mean trade expectancy ($\mathbb{E}[R_{\text{net}}]$ in USDT per trade)**, not portfolio return or equity growth.
5. **Lack of Defensible Statistical Edge**: Because the bootstrap 95% confidence interval spans deeply into negative territory (-$0.84), effective degrees of freedom are reduced ($N_{\text{eff}} \approx 40$), and multiple testing penalty ($K = 18$) lowers the threshold to $\alpha \approx 0.00278$, **NEPTUNE's historical sample cannot support a statistically validated claim of positive expectancy**.

---

## 2. Forensic Review of the Paired Comparison

### 2.1. Nature of the 90 Matched Observations
In Milestone 4.3.3, trades were matched using the compound key:
$$\text{Key} = (\text{symbol}, \text{timeframe}, \text{entry\_timestamp}, \text{direction})$$

Across the full 39,000 candle history:
- **Baseline Executed**: 277 trades
- **H7 Confluence Executed**: 126 trades
- **Exact Matches**: Exactly **90 trades** matched on symbol, timeframe, entry timestamp, and direction.

These 90 observations are **matched executed trades**. They are not raw candle setups, nor are they arbitrary time intervals.

### 2.2. Critical Methodological Flaw: Treatment of Unmatched Trades
In the Milestone 4.3.3 paired t-test:
- Paired difference on 90 matched trades: $t = 0.5651, p = 0.5734$.
- **What Was Discarded**:
  - **187 Unmatched Baseline Trades**: Aggregate Net PnL = **-$227.68** (Win Rate: 29.9%, Expectancy: -$1.22/trade).
  - **36 Unmatched H7 Trades**: Aggregate Net PnL = **+$125.10** (Win Rate: 69.4%, Expectancy: +$3.47/trade).

### 2.3. Failure to Preserve Portfolio Slot and Capital Interactions
A standard paired t-test assumes observations are drawn from identical underlying conditions. However, in an event-driven backtester with portfolio limits (`max_concurrent_positions = 2`):
- When Baseline entered trade $T_1$, its portfolio slots were locked.
- H7 rejected $T_1$ because of low volatility, keeping slots and margin free.
- Four hours later, a high-conviction breakout $T_2$ appeared. H7 took $T_2$ and gained +$15.00, while Baseline was blocked from entering $T_2$ because it was stuck in losing trade $T_1$.

**Audit Finding**: A paired t-test on matched entries evaluates only the common subset where both models entered. It cannot evaluate path-dependent slot allocation or the opportunity cost of holding losing trades. The true portfolio comparison must be evaluated at the full event-ledger level, not via pairwise truncation.

---

## 3. Dissection of the Circular Block Bootstrap

### 3.1. Parameter Disambiguation ($L = 5$ vs. $M = 2,000$)
In Milestone 4.3.3, the documentation loosely stated: `"Block Bootstrap (Block=5, B=2000, Seed=42)"`, but in narrative text referred to "B=5".

To eliminate confusion, the exact parameter definitions from the codebase are:
- **Resampling Method**: Circular Block Bootstrap (Politis & Romano, 1994).
- **Block Length ($L$)**: **5 trades** (a contiguous slice of 5 sequential trades in the ledger).
- **Number of Blocks per Replication ($K$)**: $\lceil 126 / 5 \rceil = 26$ blocks.
- **Number of Bootstrap Replications ($M$)**: **2,000 replications**.
- **Random Seed**: `42` (fixed deterministic pseudo-random sequence).

### 3.2. What Quantity is Being Resampled?
In `scratch/audit_pipeline_and_stats.py`:
```python
block_means.append(np.mean(sample_pnls[:n_trades]))
```
The quantity calculated in each replication is the **arithmetic mean net PnL per trade**:
$$\hat{\mu}_b = \frac{1}{N} \sum_{i=1}^{N} R_{i, b} \quad (\text{in USDT per trade})$$

The resulting 95% confidence interval **[-$0.84, +$1.16]** is strictly an interval for **Trade Expectancy ($\mathbb{E}[R_{\text{net}}]$)**. It is not an interval for total portfolio return, compound annual growth rate (CAGR), or terminal equity.

### 3.3. Failure of the Block Construction to Preserve Macro Regimes
The 5-trade circular block bootstrap has two critical limitations:
1. **Cross-Symbol Interleaving**:
   The trade ledger pools trades from BTCUSDT, ETHUSDT, and BNBUSDT. A block of 5 sequential trades mixes across symbols and timeframes, breaking the pure temporal auto-covariance of any individual asset.
2. **Regime Duration vs. Block Length**:
   Five trades on a 4h/1h strategy cover approximately 7 to 15 calendar days. However, crypto market regimes (e.g. multi-month low-volatility ranges or multi-month trending bull runs) persist for 60 to 180 days. A 5-trade block resamples local micro-clusters but fails to model the persistence of macro regimes.

---

## 4. Multi-Testing Adjustments & Effective Degrees of Freedom

### 4.1. The Bonferroni Hurdle ($K = 18$)
Across Milestones 4.3 and 4.3.2, 9 entry filters were evaluated across 2 exit policies ($9 \times 2 = 18$ pipelines):
$$\alpha_{\text{Bonferroni}} = \frac{0.05}{18} \approx 0.002778$$

Neither the paired test on matched trades ($p = 0.5734$) nor the independent cross-sectional tests clear this significance hurdle.

### 4.2. Severe Reduction in Effective Degrees of Freedom ($N_{\text{eff}}$)
Standard inference assumes 126 independent observations. However:
- **Cross-Asset Beta**: Correlation between BTC and ETH exceeds 0.82. Concurrent positions are correlated bets on market beta.
- **Event Clustering**: Out of +$14.02 net PnL in H7, **+$41.63** was generated by two short positions entered within 12 hours of each other on May 28–29, 2026.
- The effective number of independent events is estimated at $N_{\text{eff}} \approx 35 \text{ to } 45$.

With $N_{\text{eff}} \approx 40$ and $\sigma \approx \$4.50$, the minimum detectable effect size at 80% power is over **+$1.80 per trade**. H7's observed sample mean of +$0.11/trade is statistically indistinguishable from zero.

---

## 5. Summary and Methodological Guidelines

| Dimension | Milestone 4.3.3 Description | Milestone 4.3.4 Audited Reality | Methodological Status |
| :--- | :--- | :--- | :--- |
| **Matched Dataset** | "90 matched opportunities" | 90 matched executed trades (187 losing baseline & 36 winning H7 trades discarded) | **Biased Sub-sample** (Does not evaluate portfolio edge) |
| **Bootstrap $B$** | "B=5" | Block length $L = 5$ trades; Replications $M = 2,000$ | **Notation Clarified** |
| **Bootstrap Metric** | Unspecified | Mean net PnL per trade ($\mathbb{E}[R_{\text{net}}]$ in USDT) | **Expectancy Interval** |
| **Temporal Preservation** | Claimed | Micro-clustering preserved, but multi-month macro regimes broken | **Partial / Limited** |
| **Statistical Verdict** | "Positive expectancy" | 95% CI spans [-$0.84, +$1.16]; $N_{\text{eff}} \approx 40$; Fails Bonferroni | **INCONCLUSIVE / NO VALIDATED EDGE** |

**Final Methodological Recommendation**:
NEPTUNE should not report H7 as a validated profitable trading strategy. H7 is a defensible, mechanically sound volatility filter that eliminates low-volatility churn, but its positive net expectancy is statistically unproven on this sample.

