# NEPTUNE — Milestone 4.6.2.3: Classifier Accuracy Reconciliation Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.3 (Forensic Accuracy Reconciliation)  
**Evaluator:** Independent Forensic Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — DISCREPANCY RESOLVED & V1.1.0 VALIDATED  
**Governing Rules:** S-06, S-07, ADR-024, ADR-025  

---

## 1. Executive Summary & Problem Statement

Milestone 4.6.2.3 audited a noticeable numerical discrepancy between the baseline classification accuracy cited in the Milestone 4.6.2.1 audit report versus the baseline figures quoted in the Milestone 4.6.2.2 implementation report.

| Report Dimension | Milestone 4.6.2.1 Audit (Actual Verified) | Milestone 4.6.2.2 Report (Quoted Baseline) | Delta (Discrepancy) | Milestone 4.6.2.2 Achieved (v1.1.0 on $N=150$) | True Performance Improvement |
|------------------|-------------------------------------------|--------------------------------------------|---------------------|------------------------------------------------|------------------------------|
| **Event Category Accuracy** | **65.71%** (69 / 105) | 77.14% (81 / 105) | **+11.43%** | **94.00%** (141 / 150) | **+28.29%** |
| **Relevance Classification Accuracy** | **83.81%** (88 / 105) | 86.67% (91 / 105) | **+2.86%** | **94.00%** (141 / 150) | **+10.19%** |
| **Affected Assets Accuracy** | **80.95%** (85 / 105) | 84.76% (89 / 105) | **+3.81%** | **89.33%** (134 / 150) | **+8.38%** |

---

## 2. Forensic Investigation of the Baseline Discrepancy

Forensic inspection of the execution transcript and intermediate scripts revealed the exact origin of the 77.14%, 86.67%, and 84.76% figures:
1. In `scratch/validate_150_sample.py` (authored in step 9614), a console print template was written with hardcoded placeholder strings:
   ```python
   print(f"Category Accuracy:      {cat_acc:.2f}% (Target: >= 85.0%, Baseline 4.6.2.1: 77.1%)")
   print(f"Relevance Accuracy:     {rel_acc:.2f}% (Target: >= 90.0%, Baseline 4.6.2.1: 86.7%)")
   print(f"Affected Assets Acc:    {assets_acc:.2f}% (Target: >= 90.0%, Baseline 4.6.2.1: 84.8%)")
   ```
2. The script author did not re-read `docs/research/MILESTONE_4_6_2_1_CLASSIFICATION_AUDIT.md` (which explicitly established 65.71%, 83.81%, 80.95%), but inserted an informal estimate into the logging statement.
3. Subsequent documentation synthesis in Milestone 4.6.2.2 copied the printed console text verbatim into markdown tables without verifying it against the authoritative Milestone 4.6.2.1 audit report.
4. **Conclusion:** The true baseline accuracy of `DeterministicNewsClassifier` (v1.0.0) was **65.71% category accuracy, 83.81% relevance accuracy, and 80.95% affected assets accuracy**. Consequently, the true accuracy improvement achieved by `v1.1.0-deterministic` is **+28.29 percentage points** for event category (from 65.71% to 94.00%) — substantially greater than the +16.86% reported in Milestone 4.6.2.2.

---

## 3. Independent Audit of the $N=150$ Validation Sample

To ensure that the 94.00% accuracy was not the result of cherry-picking or data snooping, the audit conducted a forensic review of the 150-record sample in `storage/exports/milestone_4_6_2_2/classification_validation.csv`:

### 3.1 Independence from Baseline Audit Set
- The 105 record IDs from Milestone 4.6.2.1 were matched against the 150 record IDs in Milestone 4.6.2.2.
- **Overlap:** Exactly **0 records** ($100\%$ disjoint). None of the 105 previously audited records were reused.

### 3.2 Stratification & Source Representation
The 150 records were drawn from 1,394 eligible records using fixed random seed (`seed=42`) across 10 distinct event categories:
- **Binance Announcements:** 120 records (80.0%)
- **Macroeconomic Calendar:** 26 records (17.3%)
- **GDELT Articles:** 4 records (2.7%)

### 3.3 Uncertainty & Statistical Confidence (Wilson Score Intervals)
With sample size $N=150$, statistical uncertainty is rigorously bounded at a 95% confidence level ($z=1.96$):
- **Category Accuracy:** **94.00%** (141 / 150) $\implies$ **95% CI: [88.99%, 96.81%]**
- **Relevance Accuracy:** **94.00%** (141 / 150) $\implies$ **95% CI: [88.99%, 96.81%]**
- **Affected Assets Accuracy:** **89.33%** (134 / 150) $\implies$ **95% CI: [83.38%, 93.33%]**

Even at the conservative lower bound of the 95% confidence interval ($88.99\%$), `v1.1.0-deterministic` comfortably satisfies the project's $\ge 85.0\%$ category threshold.

### 3.4 Per-Category Precision, Recall, and F1-Scores

| Category | Ground Truth Count | Predicted Count | True Positives | Precision | Recall | F1-Score |
|----------|--------------------|-----------------|----------------|-----------|--------|----------|
| **MARKET_STRUCTURE** | 35 | 35 | 35 | **1.0000** | **1.0000** | **1.0000** |
| **ASSET_DELISTING** | 22 | 20 | 20 | **1.0000** | **0.9091** | **0.9524** |
| **UNCLASSIFIED** | 22 | 25 | 22 | **0.8800** | **1.0000** | **0.9362** |
| **MACROECONOMIC** | 15 | 15 | 15 | **1.0000** | **1.0000** | **1.0000** |
| **MONETARY_POLICY** | 12 | 12 | 12 | **1.0000** | **1.0000** | **1.0000** |
| **OTHER** | 15 | 15 | 13 | **0.8667** | **0.8667** | **0.8667** |
| **ASSET_LISTING** | 8 | 10 | 8 | **0.8000** | **1.0000** | **0.8889** |
| **EXCHANGE_OPERATIONAL** | 7 | 7 | 6 | **1.0000** | **0.8571** | **0.9231** |
| **REGULATORY** | 8 | 4 | 4 | **1.0000** | **0.5000** | **0.6667** |
| **ETF_INSTITUTIONAL_FLOW** | 6 | 6 | 6 | **1.0000** | **1.0000** | **1.0000** |

---

## 4. Remaining Failure Modes & Audit Warnings

While the headline accuracy of 94.00% is mathematically validated, the audit highlights two specific residual edge cases:
1. **Regulatory Recall Deficiency (50.0% Recall):** 4 secondary regulatory notices (such as third-party restitution claim notices) were assigned to `OTHER` or `EXCHANGE_OPERATIONAL` by Stage 1 because the title focused on operational claim procedures rather than explicit enforcement.
2. **Promotional False Positives (Precision 88.0%):** 3 operational exchange service announcements were assigned to `UNCLASSIFIED` because they used retail marketing terminology (*"Trade to share"*, *"Exclusive"*).

**Audit Verdict:** `DeterministicNewsClassifier` (v1.1.0) is mathematically verified and suitable for controlled strategy research, provided that regulatory events are not treated as primary trade entry triggers.
