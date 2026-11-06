# NEPTUNE — Milestone 4.6.3.1.2: Statistical Revalidation

**Report ID:** `NEP-REP-4.6.3.1.2-STAT`  
**Date:** 2026-11-07  
**Status:** Revalidation Complete & Certified  
**Governing Documents:** Rule S-06, Rule S-07, ADR-028, ADR-031, ADR-033  
**Data Partition:** 2024 Development Partition  
**Analysis Module:** [`run_milestone_4_6_3_1_2.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/run_milestone_4_6_3_1_2.py)  
**Machine-Readable Deliverable:** [`statistical_revalidation.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_2/statistical_revalidation.json)

---

## 1. Executive Summary

Milestone 4.6.3.1.2 audited and revalidated the statistical inference framework used to evaluate NEPTUNE's confirmatory hypotheses.

The audit identified three major methodological anomalies in the original Milestone 4.6.3.1 bootstrap implementation:
1. **Uncentered Null Distribution:** The original bootstrap resampled the unshifted series $\Delta x$ and calculated $p = \frac{1}{B}\sum \mathbb{I}(\bar{x}^* \le 0)$. This is an uncentered confidence distribution tail calculation, not an empirical test of the sharp null hypothesis $H_0: \mu \le 0$.
2. **Time Grid Distortions (Candidate vs. Chronological Time):** The original 384-bar block was applied across the 3,678 candidate-index array rather than a continuous market-time grid. Because candidate signals occur irregularly across time, a 384-candidate window spans an unpredictable duration (weeks or months). Furthermore, because 98.4% of candidate observations were zero, blocks were dominated by zero point-masses, distorting standard errors.
3. **Estimand Confusion:** The pre-registered economic hurdle was defined as $+0.50$ USDT net expectancy per trade ($E_{\text{trade}}$), but was inconsistently reported alongside candidate-level expectancy ($E_{\text{cand}}$). An economic hurdle of $+0.50$ USDT per candidate would demand an unrealistic $+1,839$ USDT profit on a \$1,000 account.

In Milestone 4.6.3.1.2, a mathematically sound **Null-Centered Moving Block Bootstrap** on a **Continuous 15m Chronological Market-Time Grid (35,136 bars)** was implemented and executed. Under this rigorous procedure, **none of the hypotheses achieve statistical significance**, and the economic hurdle is **decisively rejected**.

---

## 2. Theoretical Remediation of the Bootstrap Procedure

### 2.1 The Null-Centering Principle
In classical bootstrap hypothesis testing (Hall & Wilson 1991, Efron & Tibshirani 1993), testing $H_0: \mu = 0$ against $H_1: \mu > 0$ requires that the bootstrap distribution reflect the data-generating process under the null hypothesis.

#### Defective Procedure (Milestone 4.6.3.1)
The original code drew resamples directly from the raw observed sample $X = \{x_1, \dots, x_n\}$ with sample mean $\bar{x}_{\text{obs}} > 0$:
$$p_{\text{flawed}} = \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\bar{x}^*_b \le 0)$$
This simply calculates the probability that a confidence interval bounded at the 5th percentile covers zero. If $\bar{x}_{\text{obs}}$ is positive, shifting the distribution without centering causes the p-value to measure how far the sample mean is from zero rather than testing $H_0$.

#### Corrected Procedure (Milestone 4.6.3.1.2)
To test $H_0: \mu = 0$, the series is shifted to impose the null:
$$\tilde{x}_i = x_i - \bar{x}_{\text{obs}}$$
Bootstrap blocks are drawn from $\tilde{X} = \{\tilde{x}_1, \dots, \tilde{x}_n\}$, yielding resampled null means $\bar{x}^*_{b, H_0}$ centered exactly at zero. The valid empirical p-value for an upper-tailed test ($H_1: \mu > 0$) is:
$$p_{\text{null-centered}} = \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\bar{x}^*_{b, H_0} \ge \bar{x}_{\text{obs}})$$
Simultaneously, the 95% bootstrap confidence interval is constructed from the uncentered resamples $\bar{x}^*_b$ centered around $\bar{x}_{\text{obs}}$:
$$\text{CI}_{95} = \left[ q_{0.025}(\bar{x}^*), q_{0.975}(\bar{x}^*) \right]$$

---

### 2.2 Continuous Market-Time Grid vs. Candidate-Index Space

To preserve the true autocorrelation, volatility clustering, and regime persistence of crypto markets, block resampling must operate in **continuous chronological market time**:

```
Continuous 15m Calendar Grid (35,136 bars = 366 days in 2024)
├──────────────┼──────────────┼──────────────┼──────────────┤
  Bar 0          Bar 384        Bar 768        ...            Bar 35,135
  [  4.0 Days  ] [  4.0 Days  ] [  4.0 Days  ]

Candidate Space (3,678 events irregularly spaced over 35,136 bars)
|  |       |||               ||        |                      ||
Event 0    Event 384 (spans 38 days)    Event 768 (spans 19 days)
```

In the corrected implementation:
1. Each completed trade's net P&L is mapped to its exact exit candle timestamp on the 35,136-bar continuous 15m grid.
2. Candle bars with no trade exits have P&L strictly equal to \$0.00.
3. Moving blocks of length $L = 384$ bars correspond to **exactly $384 \times 15\text{ min} = 5,760\text{ min} = 96.0\text{ hours} = 4.0\text{ calendar days}$**.
4. Resampling contiguous 4-day blocks correctly maintains the real-world temporal correlation between consecutive market regimes.

---

## 3. Estimand Disambiguation

| Estimand | Formula | Denominator | Observed Value ($\Delta B - A$) | Pre-Registered Hurdle | Hurdle Status |
|---|---|---|---|---|---|
| **Trade Expectancy ($E_{\text{trade}}$)** | $\frac{\sum \text{Net P&L}}{N_{\text{trades}}}$ | Executed Trades ($N = 12$) | **+\$0.0009 USDT** | **+\$0.50 USDT** | **FAILED** (0.18% of hurdle) |
| **Candidate Expectancy ($E_{\text{cand}}$)** | $\frac{\sum \text{Net P&L}}{N_{\text{cand}}}$ | Emitted Setups ($N = 3,678$) | **\$0.0000 USDT** | N/A | **INCONCLUSIVE** |
| **Bar Expectancy ($E_{\text{bar}}$)** | $\frac{\sum \text{Net P&L}}{N_{\text{bars}}}$ | Market Bars ($N = 35,136$) | **\$0.0000 USDT** | N/A | **INCONCLUSIVE** |

The protocol's pre-registered economic hurdle was strictly defined as $+0.50$ USDT net expectancy per executed trade. Group B achieved $-\$1.9633$ USDT per trade versus Group A at $-\$1.9642$ USDT per trade. The delta of $+\$0.0009$ USDT is negligible noise.

---

## 4. Revalidated Statistical Test Results

Moving block bootstrap ($B = 2,000$ iterations, $L = 384$ bars / 4.0 days, seed=42) executed on the continuous chronological market-time grid:

### 4.1 Primary Hypothesis Results

| Hypothesis | Comparison | Null Hypothesis ($H_0$) | Observed Mean Diff ($\Delta$) | 95% Bootstrap CI | Null-Centered Empirical $p$-value | Alpha Critical Value ($\alpha=0.05$) | Statistical Verdict |
|---|---|---|---|---|---|---|---|
| **H1** | Group B vs. Group A | $\mu_B - \mu_A \le 0$ | \$0.000000 | [-\$0.000383, +\$0.000191] | **$p = 0.1740$** | 0.0500 | **Fail to Reject $H_0$** |
| **H2** | Group B vs. Group C | $\mu_B - \mu_C \le 0$ | -\$0.000013 | [-\$0.000013, +\$0.000001] | **$p = 0.9800$** | 0.0500 | **Fail to Reject $H_0$** |
| **H3** | Group B vs. Group D | $\mu_B - \mu_D \le 0$ | -\$0.000010 | [-\$0.000020, +\$0.000196] | **$p = 0.9600$** | 0.0500 | **Fail to Reject $H_0$** |

### 4.2 Benjamini-Hochberg FDR Multiplicity Correction

To control the False Discovery Rate across multiple comparisons ($q = 0.05$):

| Rank $k$ | Hypothesis ID | Raw $p$-value | BH Critical Threshold $\frac{k}{m} \cdot q$ | Significant under FDR? |
|---|---|---|---|---|
| 1 | `H1_group_b_vs_group_a` | 0.1740 | $\frac{1}{3} \times 0.05 = 0.0167$ | **NO** ($0.1740 > 0.0167$) |
| 2 | `H3_group_b_vs_group_d` | 0.9600 | $\frac{2}{3} \times 0.05 = 0.0333$ | **NO** ($0.9600 > 0.0333$) |
| 3 | `H2_group_b_vs_group_c` | 0.9800 | $\frac{3}{3} \times 0.05 = 0.0500$ | **NO** ($0.9800 > 0.0500$) |

**Conclusion:** Zero out of three confirmatory hypotheses achieve statistical significance after FDR adjustment.

---

## 5. Economic Significance Assessment

The statistical results are unambiguous:
1. **No Edge in News Filtering:** Point-in-time news intelligence provided no statistically defensible advantage ($p = 0.174$).
2. **Economic Hurdle Failed:** The observed gain of $+\$0.0009$ USDT per trade represents less than 0.2% of the mandatory $+0.50$ USDT economic hurdle.
3. **Underlying Systemic Deficit:** Both Group A and Group B produced negative net trading expectancies ($-\$1.96$ USDT per trade) and tripped the 5.0% maximum drawdown circuit breaker within 5 days of live simulation replay.

No strategy configuration demonstrates positive net expectancy after accounting for execution fees, spread, and slippage.

