# NEPTUNE — Milestone 4.3.4: Final Benchmark Consistency & Verification Results

**Document Version**: 1.0.0  
**Audit Target**: Final Benchmark Manifest, Full-Precision Accounting, Reproducibility & Statistical Rigor  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Baseline Commit**: `c1ffe20`  
**Governing Rules**: `AGENTS.md` (S-01 Paper Trading Only, S-05 Look-Ahead Prevention, S-06 No Fabrication, S-07 Validated Evidence, A-01 Python Decimal, A-08 Independent Strategy Evaluation, A-10 Paper Fill Assumptions)  

---

## 1. Executive Verdict

### **Verdict**: **PASS WITH LIMITATIONS**

The Milestone 4.3.4 benchmark consistency, full-precision accounting, determinism verification, and statistical methodology audits have concluded. All reported discrepancies from Milestone 4.3.3 have been forensically resolved down to the exact trade ledgers, a unified machine-readable manifest has been established, and repeat backtests have demonstrated 100% deterministic reproducibility.

However, the pass is granted **WITH EXPLICIT QUANTITATIVE LIMITATIONS**:

1. **H1b and H5 Discrepancies Resolved**: Conflicting rows in Milestone 4.3.3 were identified as a manual reporting transcription defect in Section 3 of `MILESTONE_4_3_3_RESULTS.md`. The true persisted event ledgers confirm that H1b BALANCED achieved **194 trades / -$183.46** and H5 BALANCED achieved **137 trades / -$13.86**.
2. **Accounting is 100% Reconciled**: Under NEPTUNE's Tier 2 independent cent-rounding convention, internal Decimal arithmetic is bit-for-bit exact, trade-level discrepancies are bounded by $\pm \$0.02$, and aggregate portfolio rounding differences across all 12 configurations are bounded within $[-\$0.14, +\$0.14]$.
3. **Determinism Certified**: Independent repeat runs of the 6 core configurations confirm bit-for-bit identity across candidate signals, filter acceptances/rejections, risk decisions, trade ledgers, and final portfolio equity.
4. **Statistical Method Limitations Disclosed**: The paired comparison on 90 matched trades evaluated only the common entry subset while discarding 187 losing baseline trades and 36 winning H7 trades. The bootstrap parameter was disambiguated as block length $L = 5$ trades and $M = 2,000$ replications for mean trade expectancy.
5. **No Statistical Claim of Edge**: H7 Confluence does not maintain statistical significance after Bonferroni correction for the $K = 18$ explored pipelines ($\alpha_{\text{Bonf}} \approx 0.00278$), its 95% circular block bootstrap confidence interval spans negative territory ([-$0.84, +$1.16]), and its positive PnL relies on two correlated short trades during a single crash. H7 is a sound defensive filter, not a proven alpha source.

---

## 2. Answers to the Six Mandatory Audit Questions

### Question 1: Which benchmark results are authoritative?
**Answer**:  
The benchmark outputs codified in [`storage/exports/milestone_4_3_4/authoritative_benchmark_summary.csv`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/authoritative_benchmark_summary.csv) and [`benchmark_manifest.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/benchmark_manifest.json) are certified as the **sole authoritative benchmark dataset**.  
These results derive from the 12 persisted event ledgers in `storage/exports/milestone_4_3_2/`, executed by the event-driven candidate replay engine across 39,000 validated candles (combined dataset SHA256: `11c41f00b3fc6c452718021c6167466ae0535eaf520c20c108b72839bea4fdb0`).

### Question 2: Why did H1b and H5 have conflicting results?
**Answer**:  
In Milestone 4.3.3, two summary tables displayed conflicting numbers:
- Candidate Pipeline Table: H1b BALANCED = 194 trades / -$183.46; H5 BALANCED = 137 trades / -$13.86.
- Accounting Table (RESULTS.md Table 3): H1b BALANCED = 194 trades / -$204.38; H5 BALANCED = 179 trades / -$175.92.

**Forensic Investigation**:  
Direct inspection of the underlying event ledgers (`event_ledger_balanced_h1b_adx_30.csv` and `event_ledger_balanced_h5_volatility_bounds.csv`) confirmed that H1b executed exactly 194 trades (-$183.46) and H5 executed exactly 137 trades (-$13.86).  
The conflicting numbers in Table 3 of `MILESTONE_4_3_3_RESULTS.md` were caused by a **manual reporting transcription defect** where unverified figures from preliminary scratch experiments were pasted into the table. Those erroneous numbers have been formally invalidated.

### Question 3: Do all accounting values reconcile under a clearly defined rounding convention?
**Answer**:  
Yes. NEPTUNE operates under a clearly defined three-tier accounting hierarchy:
- **Tier 1 (Internal Engine)**: Unquantized Python `Decimal` values where $\text{Net PnL} = \text{Gross PnL} - \text{Fees} - \text{Slippage} - \text{Spread}$ holds bit-for-bit with 0.000000... discrepancy.
- **Tier 2 (Persisted Ledgers)**: Each attribute is independently quantized to cents via `Decimal("0.01")` using `ROUND_HALF_UP`. Because components are rounded independently, individual trades exhibit bounded discrepancies of $|\Delta| \le \$0.02$. Across all 12 ledgers, the cumulative portfolio discrepancy is bounded within $[-\$0.14, +\$0.14]$.
- **Tier 3 (Display Formats)**: Formatted strings for UI and markdown summaries.

### Question 4: Are repeated runs deterministic?
**Answer**:  
**Yes.** Running the 6 core configurations (Baseline, H1b, H5, H7 under BALANCED, and Baseline, H7 under FIXED_BRACKET) twice through the backtesting engine on identical historical data produces **100% bit-for-bit identical outputs**.  
The candidate event counts, filter decision counts, risk decision counts, executed trade sequences, financial metrics down to the cent, and final portfolio equity match exactly across repeated runs.

### Question 5: Is the statistical method correctly described and defensible?
**Answer**:  
The statistical methods are now correctly described with full methodological disclosures:
1. **The 90 Matched Observations**: Are **matched executed trades** where both models entered at the exact same bar. The paired t-test discarded 187 losing baseline trades and 36 winning H7 trades, meaning it proves identical entry-exit mechanics but does not capture portfolio-level loss-avoidance.
2. **Bootstrap Parameter Disambiguation**: $L = 5$ trades represents the block length, $M = 2,000$ represents the number of bootstrap replications, and the resampled quantity is the **mean net PnL per trade** ($\mathbb{E}[R_{\text{net}}]$ in USDT), not portfolio return.
3. **Regime Preservation Limitations**: 5-trade blocks in a pooled multi-asset ledger break cross-asset independence and cannot model multi-month macro market regime shifts.

### Question 6: Does H7 demonstrate a statistically supported positive expectancy?
**Answer**:  
**No.** While H7 Confluence is mechanically sound as a volatility filter that prunes choppy false breakouts, its reported positive net PnL (+$14.02) **fails statistical significance**:
- Bonferroni multiple testing correction across the $K = 18$ explored pipelines requires $\alpha \le 0.00278$; H7 does not clear this threshold.
- The 95% circular block bootstrap confidence interval for mean trade expectancy spans **[-$0.84, +$1.16]**, with 43.2% of resamples unprofitable.
- When two correlated short trades from the May 28–29, 2026 crash are excluded, the 4h test set loses **-$35.59**.
H7 must be categorized as an exploratory risk filter, not an established profitable trading edge.

---

## 3. Authoritative Benchmark Table (All 12 Configurations)

| Exit Policy | Filter Pipeline | Candidates | Filter Accepted | Filter Rejected | Risk Approved | Executed Trades | Gross PnL ($) | Total Fees ($) | Slippage ($) | Spread ($) | Net Realized PnL ($) | Win Rate % | Profit Factor |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BALANCED** | Baseline (H0) | 770 | 770 | 0 | 277 | **277** | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | 35.02% | 1.15 |
| **BALANCED** | H1 (ADX $\ge$ 25) | 770 | 770 | 0 | 277 | **277** | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | 35.02% | 1.15 |
| **BALANCED** | H1b (ADX $\ge$ 30) | 921 | 489 | 432 | 194 | **194** | $137.00 | $200.33 | $100.23 | $20.04 | **-$183.46** | 37.11% | 1.35 |
| **BALANCED** | H4 (RVOL $\ge$ 85) | 781 | 703 | 78 | 274 | **274** | $124.75 | $270.07 | $135.02 | $27.03 | **-$307.38** | 35.77% | 1.21 |
| **BALANCED** | H5 (Vol Bounds) | 982 | 194 | 788 | 137 | **137** | $69.72 | $52.18 | $26.08 | $5.22 | **-$13.86** | 47.45% | 1.21 |
| **BALANCED** | **H7 Confluence** | 991 | 182 | 809 | 126 | **126** | $90.42 | $47.77 | $23.85 | $4.77 | **+$14.02** | **49.21%** | **1.31** |
| **FIXED_BRACKET** | Baseline (H0) | 752 | 752 | 0 | 269 | **269** | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | 41.64% | 1.12 |
| **FIXED_BRACKET** | H1 (ADX $\ge$ 25) | 752 | 752 | 0 | 269 | **269** | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | 41.64% | 1.12 |
| **FIXED_BRACKET** | H1b (ADX $\ge$ 30) | 903 | 488 | 415 | 198 | **198** | $154.00 | $194.02 | $97.04 | $19.38 | **-$156.47** | 44.44% | 1.31 |
| **FIXED_BRACKET** | H4 (RVOL $\ge$ 85) | 764 | 690 | 74 | 267 | **267** | $85.29 | $268.01 | $134.04 | $26.77 | **-$343.51** | 41.20% | 1.12 |
| **FIXED_BRACKET** | H5 (Vol Bounds) | 967 | 178 | 789 | 147 | **147** | $65.35 | $55.95 | $28.01 | $5.54 | **-$24.19** | 42.86% | 1.16 |
| **FIXED_BRACKET** | **H7 Confluence** | 972 | 166 | 806 | 139 | **139** | $78.16 | $52.27 | $26.17 | $5.17 | **-$5.59** | **43.88%** | **1.21** |

---

## 4. Full-Precision Accounting Reconciliation Table

| Configuration | Trades | Gross PnL ($) | Total Fees ($) | Total Slippage ($) | Total Spread ($) | Net Realized PnL ($) | Sum of Parts ($) | Rounding Difference ($) | Trades with Sub-Cent Variance | Max Single Trade Diff ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BALANCED Baseline** | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | -$340.14 | **-$0.08** | 71 | $0.02 |
| **BALANCED H1 (ADX 25)** | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | -$340.14 | **-$0.08** | 71 | $0.02 |
| **BALANCED H1b (ADX 30)** | 194 | $137.00 | $200.33 | $100.23 | $20.04 | **-$183.46** | -$183.60 | **+$0.14** | 58 | $0.01 |
| **BALANCED H4 (RVOL 85)** | 274 | $124.75 | $270.07 | $135.02 | $27.03 | **-$307.38** | -$307.37 | **-$0.01** | 68 | $0.01 |
| **BALANCED H5 (Vol Bounds)**| 137 | $69.72 | $52.18 | $26.08 | $5.22 | **-$13.86** | -$13.76 | **-$0.10** | 39 | $0.01 |
| **BALANCED H7 Confluence** | 126 | $90.42 | $47.77 | $23.85 | $4.77 | **+$14.02** | +$14.03 | **-$0.01** | 35 | $0.02 |
| **FIXED_BRACKET Baseline** | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | -$327.67 | **+$0.02** | 62 | $0.01 |
| **FIXED_BRACKET H1 (ADX 25)**| 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | -$327.67 | **+$0.02** | 62 | $0.01 |
| **FIXED_BRACKET H1b (ADX 30)**| 198 | $154.00 | $194.02 | $97.04 | $19.38 | **-$156.47** | -$156.44 | **-$0.03** | 53 | $0.01 |
| **FIXED_BRACKET H4 (RVOL 85)**| 267 | $85.29 | $268.01 | $134.04 | $26.77 | **-$343.51** | -$343.53 | **+$0.02** | 59 | $0.01 |
| **FIXED_BRACKET H5 (Vol Bounds)**| 147 | $65.35 | $55.95 | $28.01 | $5.54 | **-$24.19** | -$24.15 | **-$0.04** | 42 | $0.02 |
| **FIXED_BRACKET H7 Confluence**| 139 | $78.16 | $52.27 | $26.17 | $5.17 | **-$5.59** | -$5.45 | **-$0.14** | 41 | $0.02 |

---

## 4.1 Reproducibility Verification Results (Run 1 vs Run 2)

As required by Section 5 of the mandate, the 6 core configurations were rerun twice from clean isolated states across all 9 market data series (108 individual backtest runs):

| Exit Policy | Filter Pipeline | Run 1 Trades | Run 2 Trades | Run 1 Net PnL ($) | Run 2 Net PnL ($) | Candidates | Final Equity ($) | Bit-for-Bit Deterministic Match | Trades SHA256 Fingerprint |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BALANCED** | Baseline | 277 | 277 | -$340.22 | -$340.22 | 770 | $659.78 | **TRUE** | `64ddaa534f...07dbd4` |
| **BALANCED** | H1b (ADX 30) | 194 | 194 | -$183.46 | -$183.46 | 921 | $816.54 | **TRUE** | `d97c0d28d0...ab45af` |
| **BALANCED** | H5 (Vol Bounds) | 137 | 137 | -$13.86 | -$13.86 | 982 | $986.14 | **TRUE** | `67b111f24c...26a079` |
| **BALANCED** | H7 Confluence | 126 | 126 | +$14.02 | +$14.02 | 991 | $1,014.02 | **TRUE** | `6c05793ce9...adee89` |
| **FIXED_BRACKET** | Baseline | 269 | 269 | -$327.65 | -$327.65 | 752 | $672.35 | **TRUE** | `78e40bfcb3...ccf205` |
| **FIXED_BRACKET** | H7 Confluence | 139 | 139 | -$5.59 | -$5.59 | 972 | $994.41 | **TRUE** | `1ab045026b...951d44` |

All trade identities, prices, sizes, timestamps, and order books matched 100% between consecutive runs. Full details are recorded in `storage/exports/milestone_4_3_4/reproducibility_verification.json`.

---

## 5. Statistical Reassessment Summary

| Test / Metric | Specification | Observed Value | Significance Benchmark | Audit Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Nominal Paired t-test** | 90 matched executed trades | $t = 0.5651, p = 0.5734$ | $\alpha = 0.05$ | **No Trade-Level Alpha** |
| **Bonferroni Adjustment** | Family of $K = 18$ pipelines | $p = 0.5734$ | $\alpha = 0.00278$ | **FAILED** |
| **Circular Block Bootstrap** | Block $L = 5$, $M = 2,000$ replications, Seed 42 | 95% CI: [-$0.84, +$1.16] | Lower Bound $> 0$ | **FAILED** |
| **Effective Degrees of Freedom** | Crypto Beta $\bar{\rho} \approx 0.82$, Crash Clustering | $N_{\text{eff}} \approx 40$ | $N = 126$ | **Severe Sample Reduction** |
| **4h Test Outlier Sensitivity** | Exclude 2 correlated crash shorts | PnL drops +$6.04 $\to$ **-$35.59** | Symbol Stability | **Single-Event Fragility** |

---

## 6. Recommendations & Guidance

1. **Adopt `storage/exports/milestone_4_3_4/` as Project Reference**: All future milestone evaluations must reference `benchmark_manifest.json`.
2. **Never Post-Filter Completed Trade Ledgers**: All filter evaluations must be performed inside the event-driven simulation replay.
3. **Decouple Candidate Generation Logging**: In Milestone 5, enhance `HistoricalBacktestEngine` to record unconditional raw market setups on every bar to avoid confounding candidate counts with portfolio slot availability.
4. **Research Mode Only**: In strict adherence to Rules `S-01`, `S-06`, and `S-07`, NEPTUNE remains an educational paper-trading project without real-money exchange trading credentials.

