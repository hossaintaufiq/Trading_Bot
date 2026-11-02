# NEPTUNE — Milestone 4.6.2: Comprehensive Data Quality & Deduplication Audit Report

> **Document ID:** `DOC-RES-4.6.2-QUAL`  
> **Milestone:** 4.6.2 — Historical News Backfill, Event Classification & Point-in-Time Dataset Construction  
> **Status:** AUDITED & EMPIRICALLY CERTIFIED  
> **Date:** 2026-11-03  
> **Governing Rules:** Rule S-06 (No Fabricated Metrics), Rule S-08 (SQLite + Parquet WAL Integrity), ADR-023, ADR-024  
> **Audit Test Suite:** [`test_milestone_4_6_2_news.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_2_news.py) (7/7 Passed, 174/174 Backend Suite Passed)  

---

## 1. Executive Summary

This report delivers the quantitative audit of the historical news and event dataset produced under Milestone 4.6.2. 

Every record, version, cluster, and macro event persisted in [`neptune.db`](file:///d:/Project%202026/Trading_bot/storage/db/neptune.db) and exported to `storage/news/` was audited across:
- **Completeness:** Volume, unique URLs, missing timestamps, and monthly distribution.
- **Deduplication Accuracy:** Validation of the 6-stage deduplication engine across a 105-pair labeled corpus.
- **Classification Fidelity:** Event category distribution and asset relevance isolation.
- **Storage Reconciliation:** 1:1 parity between relational SQLite and partitioned Parquet files.

---

## 2. Quantitative Dataset Statistics

```
========================================================================
NEPTUNE HISTORICAL NEWS DATA QUALITY AUDIT LEDGER
========================================================================
Total News Articles Ingested:               479
Total Article Version Records:              479
Total Event Clusters:                       474
Total Macroeconomic Calendar Events:         26
Total Records (Articles + Macro):           505
Total Ingestion Runs Executed:               15

--- URL & Identity Deduplication ---
Unique Raw URLs:                            479 (100.00%)
Unique Canonical URLs:                      479 (100.00%)
Multi-Article Event Clusters:                 5 (1.05%)
Multi-Version Articles:                       0 (0.00%)

--- Point-in-Time Verification Breakdown ---
POINT_IN_TIME_VERIFIED:                     439 (86.93%)  [413 Binance + 26 Macro]
PARTIALLY_VERIFIED:                          66 (13.07%)  [66 GDELT GKG]
HISTORICAL_TIMESTAMP_UNVERIFIED:              0 (0.00%)
REJECTED:                                     0 (0.00%)

--- Timestamp Precision Distribution ---
Millisecond Precision:                      413 (81.78%)
Second Precision:                            26 (5.15%)
15-Minute Aggregator Precision:              66 (13.07%)
Missing Published Timestamp:                 66 (13.07%)  [All GDELT GKG]
Missing Available Timestamp:                  0 (0.00%)
========================================================================
```

---

## 3. Deduplication Benchmark Corpus Evaluation

To rigorously test NEPTUNE's deduplication engine against real-world news conditions, a manually labeled validation corpus of **105 article pairs** was constructed in [`test_milestone_4_6_2_news.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_2_news.py#L50-L210).

The corpus spans five distinct pair archetypes:
1. **Exact Duplicates (30 pairs):** Identical headlines, identical or canonical URLs.
2. **Canonical URL Variations (15 pairs):** Same story published with tracking parameters, UTM codes, or affiliate tags.
3. **Syndicated Wire Rewrites (20 pairs):** Same event reported independently by CoinDesk, Cointelegraph, Bloomberg, and Reuters with rewritten syntax.
4. **Distinct Events with Similar Headlines (25 pairs - False Merge Traps):** Closely related titles referring to distinct events across time or different assets (e.g., "US CPI Jan 2024" vs "US CPI Feb 2024", "Binance List TON" vs "Binance List BANANA", "Spot BTC ETF Approval" vs "Spot ETH ETF Approval").
5. **Different Topics / Altcoins (15 pairs):** Unrelated crypto news items.

### Empirical Evaluation Results:

| Metric | Measured Value | Acceptance Threshold | Result |
| :--- | :--- | :--- | :--- |
| **Total Test Pairs** | **105 pairs** | $\ge 100\text{ pairs}$ | **PASS** |
| **True Positives (TP)** | **61** | — | **PASS** |
| **False Positives (FP) [False Merges]** | **0** | $\le 3$ | **EXCEPTIONAL (0 False Merges)** |
| **True Negatives (TN)** | **40** | — | **PASS** |
| **False Negatives (FN) [Missed Duplicates]** | **4** | — | **4 Minor Syndicated Misses** |
| **Precision** | **100.00%** ($1.0000$) | $\ge 85.00\%$ | **PASS** |
| **Recall** | **93.85%** ($0.9385$) | $\ge 80.00\%$ | **PASS** |
| **F1 Score** | **96.83%** ($0.9683$) | $\ge 82.00\%$ | **PASS** |

> [!NOTE]
> The engine achieved **zero false merges ($FP = 0$)** across all 25 difficult trap pairs. When headlines are subtly different (e.g. CPI January vs February), the combination of temporal window verification and entity-overlap checking successfully prevented conflation. The 4 missed duplicates occurred on syndicated wire rewrites where journalists completely restructured the headline vocabulary, resulting in SimHash distances $> 3$.

---

## 4. Monthly Coverage Progression & Asset Balance

The following ledger details coverage across every active month in the 2024–2026 research window:

| Month | Total Records | BTC | ETH | BNB | Exchange-Wide | Market-Wide | Macro | Other | Event Clusters |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2024-01** | 31 | 28 | 3 | 1 | 0 | 0 | 0 | 31 | 29 |
| **2024-04** | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| **2024-05** | 23 | 17 | 15 | 9 | 6 | 2 | 0 | 15 | 23 |
| **2024-06** | 39 | 26 | 22 | 19 | 13 | 0 | 0 | 26 | 39 |
| **2024-08** | 7 | 3 | 3 | 1 | 0 | 0 | 0 | 7 | 7 |
| **2024-09** | 23 | 12 | 7 | 8 | 10 | 0 | 0 | 13 | 22 |
| **2024-10** | 53 | 20 | 19 | 16 | 28 | 0 | 1 | 24 | 52 |
| **2024-11** | 31 | 18 | 5 | 3 | 11 | 0 | 0 | 20 | 30 |
| **2026-06** | 46 | 15 | 13 | 8 | 27 | 3 | 2 | 14 | 46 |
| **2026-07** | 45 | 10 | 8 | 4 | 32 | 2 | 0 | 11 | 45 |
| **2026-08** | 35 | 10 | 8 | 5 | 26 | 0 | 2 | 7 | 35 |
| **2026-09** | 78 | 36 | 25 | 19 | 45 | 5 | 10 | 18 | 78 |
| **2026-10** | 54 | 20 | 12 | 9 | 38 | 0 | 7 | 9 | 54 |
| **2026-11** | 8 | 3 | 2 | 2 | 5 | 0 | 0 | 3 | 8 |
| **Total** | **479** | **224** | **142** | **104** | **241** | **12** | **22** | **203** | **474** |

---

## 5. Storage Reconciliation & Integrity Verification

A complete reconciliation check was executed between relational SQLite and analytical Parquet:
- **Articles Exported:** 479 SQLite rows $\rightarrow$ 479 Parquet rows across 4 source/year partitions ($100\%$ parity).
- **Versions Exported:** 479 SQLite rows $\rightarrow$ 479 Parquet rows across 4 source/year partitions ($100\%$ parity).
- **Clusters Exported:** 474 SQLite rows $\rightarrow$ 474 Parquet rows in `clusters/event_clusters.parquet` ($100\%$ parity).
- **Macro Events Exported:** 26 SQLite rows $\rightarrow$ 26 Parquet rows in `macro_calendar/macro_events.parquet` ($100\%$ parity).
- **Composite Hash Match:** The dataset manifest verifies the composite cryptographic hash `04cae914870b35afc69ea3968a0b86f005fe068726625ec9c47ef2c1044674f1`.
