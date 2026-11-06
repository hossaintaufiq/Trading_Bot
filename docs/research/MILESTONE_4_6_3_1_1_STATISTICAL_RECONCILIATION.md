# NEPTUNE — Milestone 4.6.3.1.1
## Statistical Integrity, Moving Block Bootstrap & Multiple Testing Reconciliation

**Document:** Statistical Methodology & Hypothesis Reconciliation  
**Audit Target:** Milestone 4.6.3.1 Statistical Plan & Hypothesis Results  
**Artifact Link:** [`bootstrap_reconstruction.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_1/bootstrap_reconstruction.json) & [`bh_fdr_recalculation.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_1/bh_fdr_recalculation.json)  

---

## 1. Audit Mandate: The Confidence Interval vs $p$-Value Anomaly

The audit inquiry demanded an investigation into the reported statistical results for the primary confirmatory hypotheses:

- **H1 (Group B vs Group A):**
  - Observed Difference ($\Delta E_{\text{cand}}$): $+0.0273$ USDT
  - Reported 95% Confidence Interval: $[0.0000, 0.0511]$
  - Reported Empirical $p$-value: **$0.5950$**
- **H2 (Group B vs Group C):**
  - Observed Difference ($\Delta E_{\text{cand}}$): $+0.0195$ USDT
  - Reported 95% Confidence Interval: $[0.0000, 0.0428]$
  - Reported Empirical $p$-value: **$0.5950$**
- **H3 (Group B vs Group D):**
  - Observed Difference ($\Delta E_{\text{cand}}$): $+0.0137$ USDT
  - Reported 95% Confidence Interval: $[0.0000, 0.0272]$
  - Reported Empirical $p$-value: **$0.5900$**

### The Core Statistical Paradox
In standard Gaussian or continuous bootstrap distributions, if the 95% confidence interval for a difference $\mu$ has a lower bound of $0.0000$ (or positive), the one-sided $p$-value for $H_0: \mu \le 0$ must be $\le 0.025$. 

Why, then, did the simulation report a 95% CI of $[0.0000, 0.0511]$ alongside a massive $p$-value of **$0.5950$** (over 50%)?

---

## 2. Forensic Discovery: The Discrete Point Mass at Zero

Re-running the Moving Block Bootstrap across the 3,678 candidate stream revealed the mathematical truth:

```python
# Array analysis of diff_b_minus_a (length 3,678):
Total candidates:        3,678
Zero elements:           3,622 (98.48%)
Positive elements:          28 (0.76%)
Negative elements:          28 (0.76%)
```

### The Mechanism of the Point Mass:
1. **Extreme Sparsity:** Out of 3,678 candidate setups, only 56 setups had non-zero P&L differences between Group A and Group B. Over **98.48% of the candidate array consists of exact zeros**!
2. **Block Sampling on Sparsity:** When sampling blocks of $L = 384$ candidates with replacement, in **58.2% of all 2,000 bootstrap iterations**, the randomly selected blocks happened to contain *only zeros*!
3. **Distribution Breakdown:**
   $$\text{Fraction of Bootstrap Resample Means} = \begin{cases} < 0.0000 & 1.3\% \text{ (26 iterations)} \\ = 0.0000 & \mathbf{58.2\%} \text{ (1,164 iterations)} \\ > 0.0000 & 40.5\% \text{ (810 iterations)} \end{cases}$$

```
                Bootstrap Resampling Mean Distribution (H1)
    Frequency
       ▲
1164 ──┤                         [Point Mass at 0.0000 (58.2%)]
       │                                     █
       │                                     █
 200 ──┤                                     █     ▄
 100 ──┤                                     █   ▄ █ ▄
       │                                 ▄   █ █ █ █ █ ▄
   0 ──┴───────────────┬─────────────────┴───┴─┴─┴─┴─┴─┴─┴──────►
                     -0.004                 0.000      +0.051   Boot Mean
                       ▲                      ▲          ▲
                   Min Resample           2.5th Pct   97.5th Pct
                   (-0.0043)               (0.0000)    (0.0511)
```

### Mathematical Reconciliation:
- **Percentile Confidence Interval (2.5% to 97.5%):**
  - The 2.5th percentile falls within the massive point mass at 0.0 (which spans from cumulative probability 1.3% up to 59.5%). Therefore, `np.percentile(boot_means, 2.5)` evaluates to **$0.0000$**.
  - The 97.5th percentile falls at **$0.0511$**.
- **Empirical $p$-value ($P(\text{Mean} \le 0.0)$):**
  - The code evaluated `np.mean(boot_means <= 0.0)`.
  - Because 58.2% of resamples were *exactly* $0.0$, and 1.3% were $< 0.0$, the sum evaluated to $1.3\% + 58.2\% = \mathbf{59.5\%}$ ($p = 0.5950$).
- **Conclusion:** The CI $[0.0000, 0.0511]$ and the $p$-value $0.5950$ are **mathematically reconcilable and derived from the exact same discrete distribution**. However, they represent a severe methodological artifact of applying block bootstrap to an excessively sparse, irregularly spaced candidate stream.

---

## 3. Methodological Limitation: Candidate Stream vs Time-Grid Block Bootstrap

In ADR-030, the moving block size was specified as:
> *384 bars on 15m, calibrated to ~4 calendar days (96 hours) to preserve serial autocorrelation.*

### The Implementation Flaw:
- The script applied `block_size = 384` to the **3,678 candidate stream**, NOT to the **105,408 regular candle grid**!
- Because candidate setups are emitted only during market trends, 384 candidates spanned an average of **38 calendar days** (over 1 month), completely destroying the intended 4-day serial correlation structure.
- Furthermore, concatenating candidate blocks created artificial boundaries across non-contiguous months.

---

## 4. Benjamini-Hochberg False Discovery Rate ($q = 0.05$) Verification

The Benjamini-Hochberg step-up procedure was independently recalculated across the three confirmatory hypotheses:

| Rank ($k$) | Hypothesis | Raw $p$-value | Critical Threshold $\left(\frac{k}{m} \cdot q\right)$ | Adjusted $p$-value ($q$-value) | Significant under FDR? |
|:---:|---|:---:|:---:|:---:|:---:|
| **1** | **H3 (Group B vs Group D)** | 0.5900 | $\frac{1}{3} \times 0.05 = \mathbf{0.016667}$ | 1.0000 | **FAIL** |
| **2** | **H1 (Group B vs Group A)** | 0.5950 | $\frac{2}{3} \times 0.05 = \mathbf{0.033333}$ | 0.8925 | **FAIL** |
| **3** | **H2 (Group B vs Group C)** | 0.5950 | $\frac{3}{3} \times 0.05 = \mathbf{0.050000}$ | 0.5950 | **FAIL** |

### Audit Findings:
1. **Sorting Verified:** The hypotheses were properly sorted in ascending order of $p$-values before critical value assignment (H3 first, followed by H1 and H2).
2. **FDR Decision Verified:** Because all raw $p$-values ($0.59–0.60$) exceed the critical thresholds by a factor of 12x to 35x, **zero hypotheses are rejected**. The news-veto strategy demonstrates zero statistically significant alpha under multiple-testing correction.

---

## 5. Economic Hurdle Reconciliation

Under the pre-registered Statistical Analysis Plan ([`research_protocol.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py#L955)):
- **Economic Significance Hurdle:** `economic_hurdle_net_expectancy_usdt = Decimal("0.50")`.
- **Pre-Registered Denominator:** The inline specification explicitly states: `# Minimum $0.50 per trade outperformance` ($E_{\text{trade}}$).

### Reconciliation:
- Observed $\Delta E_{\text{trade}} = -2.4345 - (-3.1576) = \mathbf{+0.7232\text{ USDT / trade}}$.
- Observed $\Delta E_{\text{cand}} = -0.0311 - (-0.0584) = \mathbf{+0.0273\text{ USDT / candidate}}$.
- **Scientific Audit Verdict:**
  - On an executed-trade basis ($E_{\text{trade}}$), the point estimate numerically exceeded the nominal $+0.50$ hurdle.
  - However, because the underlying difference has an empirical bootstrap $p$-value of **$0.5950$**, the point estimate is statistically indistinguishable from zero noise.
  - On a candidate stream basis ($E_{\text{cand}}$), the outperformance is only $+0.0273$ USDT, failing the hurdle by an order of magnitude.
  - Claiming economic significance on the basis of an insignificant $p=0.595$ result is mathematically invalid.

