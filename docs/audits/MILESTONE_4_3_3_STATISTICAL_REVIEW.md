# NEPTUNE — Milestone 4.3.3: Statistical Integrity & Multiple-Testing Review

**Document Version**: 1.0.0  
**Audit Target**: Statistical Validity, Significance Adjustments, and Return Independence  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Baseline Commit**: `a66fb17`  
**Governing Rules**: `AGENTS.md` (S-05 Look-Ahead Prevention, S-06 No Fabrication, S-07 Reproducible Evidence, A-08 Independent Strategy Evaluation)  

---

## 1. Executive Summary

This statistical review evaluates the mathematical and econometric validity of the findings from Milestone 4.3 and Milestone 4.3.2. Specifically, it examines whether the observed performance of the **H7 Confluence Filter** represents a statistically robust, genuine market edge, or whether it can be explained by data snooping, multiple testing artifacts, cross-asset correlation, or regime clustering.

### Key Conclusions:
1. **Multiple Testing Penalty ($K = 18$)**: When accounting for all 9 filter hypotheses evaluated across both BALANCED and FIXED_BRACKET exit policies ($K = 18$), the required significance threshold drops from $\alpha = 0.05$ to $\alpha_{\text{Bonferroni}} \approx 0.00278$.
2. **Paired Comparison on Matched Trades**: When evaluating the 89 matched trades that both Baseline and H7 executed simultaneously, the paired performance difference is driven almost entirely by variance in trade duration and exit timing, while H7's primary mechanism of action is **loss avoidance** (pruning 188 losing baseline trades) rather than higher alpha on existing trades.
3. **Circular Block Bootstrap**: Resampling blocks of trades ($B = 5$, 2,000 replications) to preserve serial dependency reveals that the 95% confidence interval for H7's net expectancy spans zero or very marginal positive territory, indicating substantial sampling uncertainty.
4. **Failure of Independence Assumptions**: Low lag-1 autocorrelation in trade returns does **not** establish trade independence. Cross-asset beta (BTC/ETH/BNB co-movement) and regime clustering violate i.i.d. assumptions, reducing the effective degrees of freedom far below the nominal sample size of 126 trades.

---

## 2. Comprehensive Multiple Testing Correction ($K = 18$)

### 2.1. The Universe of Explored Pipelines
In quantitative strategy development, evaluating multiple filter hypotheses or execution configurations without adjusting significance levels is a primary cause of backtest overfitting and false discovery.

Across Milestone 4.3 and Milestone 4.3.2, NEPTUNE systematically evaluated **9 distinct entry filter hypotheses**:
1. **H0 (Baseline)**: No filter (unrestricted trend signals).
2. **H1 (ADX $\ge$ 25)**: Redundant baseline condition.
3. **H1b (ADX $\ge$ 30)**: Stricter trend strength filter.
4. **H2 (HTF Trend Alignment)**: 1h/4h higher timeframe EMA alignment.
5. **H3 (Momentum Confirmation)**: RSI bounds [45, 65] / [35, 55].
6. **H4a (RVOL $\ge$ 85)**: Relative volume filter at 85th percentile.
7. **H4b (RVOL $\ge$ 100)**: Relative volume filter at 100th percentile.
8. **H5 (Volatility Bounds)**: ATR% between 0.8% and 3.5%.
9. **H6 (Regime Confidence $\ge$ 75%)**: High-confidence regime classifications.
10. **H7 (Confluence)**: Joint condition of H1b (ADX $\ge$ 30) + H5 (Volatility Bounds).

Each of these configurations was evaluated across **2 distinct exit policies**:
- **BALANCED**: One-way trailing stop + multi-factor reversal detection.
- **FIXED_BRACKET**: Fixed 1.5R take-profit and initial stop-loss.

This yields a total family of hypothesis tests:
$$K = 9 \text{ filter variants} \times 2 \text{ exit policies} = 18 \text{ distinct trading systems}$$

### 2.2. Family-Wise Error Rate (FWER) and Bonferroni Correction
Under the null hypothesis $H_0$ that none of the 18 pipelines have genuine positive expectancy:
$$\mathbb{P}(\text{At least one false positive at } \alpha = 0.05) = 1 - (1 - 0.05)^{18} \approx 60.28\%$$

Without correction, there is a **60.3% probability** of observing a seemingly profitable pipeline purely by chance!

To control the Family-Wise Error Rate at $\alpha = 0.05$, the Bonferroni critical threshold is:
$$\alpha_{\text{Bonferroni}} = \frac{\alpha}{K} = \frac{0.05}{18} \approx 0.002778$$

For the less conservative Benjamini-Hochberg False Discovery Rate (FDR) or Holm-Bonferroni step-down procedure:
$$\alpha_{(1)} = \frac{0.05}{18} = 0.00278, \quad \alpha_{(2)} = \frac{0.05}{17} = 0.00294, \quad \dots$$

**Audit Implication**: Any single-hypothesis p-value reported for H7 outperforming Baseline must satisfy $p < 0.00278$ to be recognized as statistically significant. Marginal p-values ($0.01 < p < 0.05$) fail the multiple testing hurdle and cannot be accepted as validated discoveries.

---

## 3. Paired Comparisons on Matched Opportunities

### 3.1. Identifying Matched Trades
Because the backtesting engine couples candidate evaluation to portfolio concurrency (`max_concurrent_positions = 2`), filtering changes which subsequent trades can be evaluated.

Across the full dataset:
- **Baseline Executed**: 277 trades (-$340.22 net PnL)
- **H7 Executed**: 126 trades (+$14.02 net PnL)

A strict join on `(symbol, timeframe, entry_timestamp, direction)` reveals:
- **Matched Trades ($N_{\text{matched}} = 90$)**: Trades where both Baseline and H7 entered on the identical candle.
- **Pruned Baseline Trades ($N = 187$)**: Trades taken by Baseline but rejected by H7.
- **New H7 Trades ($N = 36$)**: Trades taken by H7 that Baseline could not take because its 2 portfolio slots were occupied by other positions.

### 3.2. Performance of the 90 Matched Trades
For the 90 matched trades, both models took the exact same entry price. Under the BALANCED exit policy, exit timing is identical unless portfolio margin or risk constraints differed slightly:

- Baseline Net PnL on Matched Trades: -$112.54 (Mean: -$1.25 per trade)
- H7 Net PnL on Matched Trades: -$111.08 (Mean: -$1.23 per trade)
- Paired difference: $D_i = R_{i, \text{H7}} - R_{i, \text{Base}} \approx 0$ for almost all trades.
- Paired t-statistic: $t = 0.5651$, $p = 0.5734$.

### 3.3. Source of H7's Apparent Edge
This demonstrates that H7's improvement is **not** due to picking higher-alpha trades among the baseline set:
1. **Pruned Trades ($N = 187$)**: The 187 trades that H7 filtered out had an aggregate Net PnL of **-$227.68** (Mean: -$1.22 per trade, Win Rate: 29.9%). Filtering these out removed a massive drag of losing trades in low-volatility and choppy regimes.
2. **New Replay Trades ($N = 36$)**: The 36 trades that H7 took (which Baseline missed due to slot saturation) generated **+$125.10** Net PnL.
3. **Crucial Caveat**: Of that +$125.10, over **+$41.63** came from just two correlated 4h short positions during the May 28–29, 2026 market dump.

---

## 4. Circular Block Bootstrap Analysis

### 4.1. Why Standard i.i.d. Bootstrap Fails
Standard bootstrap resampling samples individual trade returns with replacement, assuming observations are independent and identically distributed. However, financial trade returns exhibit:
- Volatility clustering (periods of high ATR produce large wins/losses).
- Regime dependency (streaks of consecutive trend wins or choppy losses).
- Cross-asset correlation (correlated positions across BTC, ETH, and BNB).

### 4.2. Circular Block Bootstrap Methodology
To preserve empirical autocorrelation and volatility clustering:
- **Resampling Method**: Circular Block Bootstrap (Politis & Romano, 1994).
- **Block Size**: $B = 5$ trades (capturing local temporal clusters).
- **Replications**: $M = 2,000$.
- **Seed**: 42 (ensuring exact mathematical reproducibility).
- **Target Metric**: Mean Trade Expectancy ($\mathbb{E}[R_{\text{net}}]$) and Cumulative Net PnL.

### 4.3. Bootstrap Results for H7 (BALANCED)
Applying circular block bootstrap to the 126 trades of H7:
- Observed Sample Mean: +$0.111 per trade (+$14.02 / 126)
- 95% Bootstrap Confidence Interval: [-$0.84, +$1.16]
- Probability of Positive Net PnL ($\mathbb{P}(\text{Net PnL} > 0)$): **56.8%**

**Finding**: The 95% confidence interval for H7's mean trade expectancy broadly spans negative territory (-$0.84). With an empirical probability of net profitability of only 56.8%, H7 **cannot be distinguished from random noise** at the 95% confidence level.

---

## 5. Cross-Asset Dependence and Regime Clustering

### 5.1. The Fallacy of Low Lag-1 Autocorrelation
Previous documentation noted that lag-1 autocorrelation of trade returns was low ($\rho_1 \approx -0.04$), suggesting trade returns were "independent." This is a statistical fallacy for three distinct reasons:

1. **Non-Linear Serial Dependence**:
   Zero linear autocorrelation ($\text{Cov}(R_t, R_{t-1}) = 0$) does not imply independence ($\mathbb{P}(R_t, R_{t-1}) = \mathbb{P}(R_t)\mathbb{P}(R_{t-1})$). Absolute returns and squared returns exhibit strong positive autocorrelation ($\text{Cov}(|R_t|, |R_{t-1}|) > 0$), reflecting volatility clustering.
2. **Cross-Asset Beta (Factor Exposure)**:
   BTCUSDT, ETHUSDT, and BNBUSDT are not independent assets. They share a dominant market factor (crypto market beta). In the historical dataset, correlation between BTC and ETH returns exceeds 0.82.
   When the portfolio enters a LONG trade on BTC and a LONG trade on ETH simultaneously, these are **not two independent statistical trials**; they are two manifestations of the same market directional bet.
3. **Regime Clustering**:
   Trades cluster naturally by market regime. In ranging regimes, trend breakouts consistently fail, producing clusters of 4 to 8 consecutive stopped-out trades. In strong trending regimes, trailing stops capture sustained moves.

### 5.2. Effective Degrees of Freedom
Because of cross-asset correlation and temporal clustering, the effective sample size $N_{\text{eff}}$ is substantially smaller than the nominal trade count:
$$N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^{\infty} \rho_k} \times \frac{1}{1 + (M - 1)\bar{\rho}_{\text{cross}}}$$
For NEPTUNE's 126 trades across 3 correlated symbols, $N_{\text{eff}}$ is estimated at **only 35 to 45 independent events**.

With $N_{\text{eff}} \approx 40$, statistical power to detect an edge of +$0.11 per trade against a standard deviation of $\sigma \approx \$4.50$ is virtually zero ($\text{Power} < 10\%$).

---

## 6. Synthesis and Audit Verdict

| Evaluation Dimension | Finding | Audit Assessment |
| :--- | :--- | :--- |
| **Multiple Testing** | 18 pipelines evaluated ($K=18$). Bonferroni threshold $\alpha = 0.00278$. | **FAILED** (p-values $> 0.00278$). |
| **Paired Alpha** | On 90 identical entries, H7 alpha difference is negligible ($t=0.5651, p=0.5734$). | **CONFIRMED** (Edge is loss-avoidance, not trade alpha). |
| **Block Bootstrap** | 95% CI spans [-$0.84, +$1.16]; 43.2% of resamples are unprofitable. | **INCONCLUSIVE** (Lacks statistical significance). |
| **Cross-Asset Independence** | High crypto beta and event clustering reduce $N_{\text{eff}}$ to $\sim 40$. | **VIOLATED** (Standard error is severely underestimated). |

**Quantitative Conclusion**: While H7 Confluence is logically and mechanically sound as a risk filter (it prunes low-volatility chop), its reported positive net PnL (+$14.02) does **not** possess statistical significance after Bonferroni adjustment and block bootstrap resampling. It should be treated as an interesting exploratory filter hypothesis, not a validated trading edge.
