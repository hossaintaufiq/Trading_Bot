# NEPTUNE — Milestone 4.6.2.2: Event Classification Remediation Report

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.2 (Workstream C)  
**Title:** Deterministic Classification Remediation (`DeterministicNewsClassifier` v1.1.0)  
**Status:** Remediated & Validated  
**Governing Rules:** S-06, S-08, ADR-024, ADR-025  

---

## 1. Executive Summary & Problem Formulation

In Milestone 4.6.2.1, an independent manual audit of 105 records revealed that the initial classifier (`v1.0.0-deterministic`) exhibited significant classification degradation:
- **Category Accuracy:** 77.14% (target $\ge 85\%$).
- **Relevance Accuracy:** 86.67% (target $\ge 90\%$).
- **Affected Assets Accuracy:** 84.76% (target $\ge 90\%$).

Forensic debugging isolated **six distinct failure modes** arising from naive keyword searching and regex greediness. Non-deterministic LLM classifiers were strictly ruled out due to non-reproducibility and execution latency. Workstream C redesigned the classifier into `v1.1.0-deterministic` using a two-stage waterfall architecture.

---

## 2. Six Failure Modes & Technical Remediations

### Failure Mode 1: Taxonomy Boundary Overlap (Market Structure vs Exchange Operations)
- **Problem:** Margin tier schedules, tick size updates, leverage adjustments, and funding rate changes were classified as `EXCHANGE_OPERATIONAL` instead of `MARKET_STRUCTURE`.
- **Root Cause:** Inverted category evaluation order where operational terms matched first.
- **Remediation:** Enforced strict precedence of `MARKET_STRUCTURE` over `EXCHANGE_OPERATIONAL`. Re-ordered evaluation hierarchy.

### Failure Mode 2: Boilerplate Legal Disclaimer False Positives
- **Problem:** Promotional announcements (e.g. *Earn Wednesday*, *Trading Tournament*) were misclassified as `REGULATORY` due to boilerplate footers (*"Risk Warning: Digital asset prices are subject to high market risk..."*).
- **Root Cause:** Uncleaned body text evaluation triggered regulatory regex on legal disclaimers.
- **Remediation:** Implemented `_strip_boilerplate()` which strips text matching `(risk warning\s*:|risk disclaimer\s*:|disclaimer\s*:|terms and conditions\s*:|general notice\s*:)` prior to classification.

### Failure Mode 3: Security Regex False Positives
- **Problem:** Fee promotions and protective exchange policies (e.g. *"Binance Will Support Zero Withdrawal Fees for bStocks"*) were misclassified as `SECURITY_INCIDENT`.
- **Root Cause:** Regex `(?<!\w)security(?!\w)` matched the word "security" in financial securities or generic safety phrases.
- **Remediation:** Constrained `SECURITY_INCIDENT` regex to explicit operational threats: `HACK`, `EXPLOIT`, `DRAIN`, `FLASH LOAN ATTACK`, `PRIVATE KEY LEAK`, `SECURITY BREACH`.

### Failure Mode 4: Retail Campaign Asset De-Attribution
- **Problem:** Marketing giveaways and retail earn competitions offering BNB or BTC rewards were misclassified as fundamental asset events (`DIRECT_ASSET`).
- **Root Cause:** Naive asset entity scanning detected "BNB" or "BTC" inside prize pool descriptions.
- **Remediation:** Created `PROMOTIONAL_PATTERNS`. Any article matching retail promotional keywords (*Earn Wednesday*, *Yield Arena*, *Voucher*, *Competition*) has affected assets explicitly stripped to `[]` and relevance assigned to `UNCLASSIFIED`.

### Failure Mode 5: Category Precedence Masking & Title-Primary Evaluation
- **Problem:** New listing announcements with regulatory disclaimers in the body were misclassified as `REGULATORY`.
- **Root Cause:** Flat body matching masked the primary event described in the headline.
- **Remediation:** Architected a **Two-Stage Title-Primary Waterfall**:
  1. *Stage 1 (Title Evaluation):* Evaluate headline against category patterns. If a match occurs, assign category with high confidence ($0.98$) and bypass body category evaluation.
  2. *Stage 2 (Body Fallback):* Only if the headline does not match any category pattern is the cleaned body evaluated ($0.90$ confidence).

### Failure Mode 6: Punctuation-Delimited Acronym Normalization
- **Problem:** Headlines using `E.T.F.` or `S.E.C.` or `F.O.M.C.` failed regex pattern matching.
- **Root Cause:** Literal periods broke word-boundary tokens (`\bETF\b`).
- **Remediation:** Implemented `_normalize_punctuation()` which maps `E.T.F.` $\to$ `ETF`, `S.E.C.` $\to$ `SEC`, and `F.O.M.C.` $\to$ `FOMC` before pattern compilation.

---

## 3. Unit Test Verification

All six failure modes were codified into a dedicated test suite `backend/tests/unit/test_milestone_4_6_2_2_classification.py`:
- `test_failure_mode_1_market_structure_boundary`: PASSED
- `test_failure_mode_2_boilerplate_disclaimer_stripping`: PASSED
- `test_failure_mode_3_security_regex_false_positive`: PASSED
- `test_failure_mode_4_promotional_asset_deattribution`: PASSED
- `test_failure_mode_5_category_precedence_masking`: PASSED
- `test_failure_mode_6_punctuation_acronym_normalization`: PASSED

Execution time: **0.19 seconds** (100% deterministic, zero API calls, zero cost).

