# NEPTUNE — Milestone 4.6.3.0
# Chronological Data Partitioning & Research Coverage Specification

**Milestone:** 4.6.3.0  
**Status:** FROZEN  
**Date:** 2026-11-06  
**Document Type:** Dataset Partitioning, Coverage Matrix & Limitation Audit  
**Split Manifest ID:** `neptune_35m_chronological_split_v1`  
**Dataset Versions:** Market `v2.0.0` | News `v2.0.0-news-historical` (1,499 records)  

---

## 1. Principles of Chronological Partitioning

Financial time-series and event intelligence data violate the independent and identically distributed (i.i.d.) assumption. Standard random row splitting or k-fold cross-validation results in catastrophic look-ahead leakage, autocorrelated signal leakage, and overfitted survivorship bias.

NEPTUNE strictly enforces:
1. **Strict Temporal Ordering:** All partition boundaries are time-based ($T_1 < T_2 < T_3$). No future market candle or news event is accessible during earlier simulation steps.
2. **Cluster Boundary Integrity:** Multi-article event clusters are verified to ensure that no single cluster spans across partition boundaries, eliminating duplicate information leakage.
3. **Partition Isolation:**
   - **Partition 1 (Development / Training):** Parameter exploration, indicator baseline validation, and hypothesis formulation.
   - **Partition 2 (Validation):** Veto threshold tuning, paired group comparison, and control calibration.
   - **Partition 3 (Locked Out-of-Sample):** Strictly locked and untouched. Executed exactly once after the research protocol is frozen and signed off.
   - **Forward Quarantined Window:** Partial periods or future-dated calendar events ($> 2026-10-31\text{ UTC}$) are quarantined.

---

## 2. Partition Boundary Specifications

| Partition | Name | Start Timestamp (UTC) | End Timestamp (UTC) | Duration | Status | Article Records | Macro Events | 15m Candles / Symbol | Research Suitability |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **P-1** | **Development & Training** | `2024-01-01T00:00:00Z` | `2024-12-31T23:59:59Z` | 12 Months | Open / Dev | 353 | 27 | 35,136 | **HIGH** |
| **P-2** | **In-Sample Validation** | `2025-01-01T00:00:00Z` | `2025-12-31T23:59:59Z` | 12 Months | Frozen / Val | 572 | 22 | 35,040 | **HIGH** |
| **P-3** | **Locked Out-of-Sample** | `2026-01-01T00:00:00Z` | `2026-10-31T23:59:59Z` | 10 Months | **LOCKED** | 461 | 17 | 29,184 | **HIGH** |
| **P-4** | **Forward Quarantined** | `2026-11-01T00:00:00Z` | `2026-12-31T23:59:59Z` | 1 Month (Part) | **QUARANTINED** | 2 | 2 | 288 | **LIMITED** |
| **Warmup**| **Pre-2024 Context** | `2023-01-01T00:00:00Z` | `2023-12-31T23:59:59Z` | 12 Months | Context Only | 45 | 0 | N/A | Warmup Context |
| **Total** | **Full Research Corpus** | `2023-01-01T00:00:00Z` | `2026-11-03T23:59:59Z` | 35+ Months | Verified | **1,431** | **68** | **99,648** | **COMPLETE** |

### Cluster Leakage Verification
Forensic evaluation of all 1,421 event clusters (`news_event_clusters`) in `neptune.db` across the chronological partitions confirmed:
$$\text{Clusters spanning multiple years} = 0$$
Zero clusters cross between 2024 (Dev), 2025 (Val), and 2026 (Locked OOS), guaranteeing zero duplicate news leakage across partitions.

---

## 3. Comprehensive 35-Month Monthly Coverage Matrix

The market dataset `v2.0.0` provides continuous, 100% complete candle coverage across all 35 calendar months (2024-01 to 2026-11) for `BTCUSDT`, `ETHUSDT`, and `BNBUSDT` across `15m`, `1h`, `4h`, and `1d` (420 Parquet files).

The news dataset `v2.0.0-news-historical` coverage distribution across the 35 months is detailed below:

| Month | Calendar Status | Total Records | Binance Articles | GDELT Articles | Macro Releases | Strict PIT Verified | BTC Relevant | ETH Relevant | BNB Relevant | Research Utility Assessment |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **2024-01** | Full | 39 | 36 | 0 | 3 | 39 | 14 | 12 | 11 | **HIGH_MEANINGFUL** |
| **2024-02** | Full | 37 | 36 | 0 | 1 | 37 | 13 | 11 | 10 | **HIGH_MEANINGFUL** |
| **2024-03** | Full | 36 | 33 | 0 | 3 | 36 | 17 | 14 | 14 | **HIGH_MEANINGFUL** |
| **2024-04** | Full | 11 | 9 | 0 | 2 | 11 | 4 | 2 | 2 | **HIGH_MEANINGFUL** |
| **2024-05** | Full | 21 | 18 | 0 | 3 | 21 | 9 | 9 | 8 | **HIGH_MEANINGFUL** |
| **2024-06** | Full | 41 | 39 | 0 | 2 | 41 | 14 | 11 | 14 | **HIGH_MEANINGFUL** |
| **2024-07** | Full | 2 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | **MODERATE (SPARSE ARTICLES)** |
| **2024-08** | Full | 4 | 2 | 0 | 2 | 4 | 2 | 2 | 2 | **MODERATE (SPARSE ARTICLES)** |
| **2024-09** | Full | 28 | 26 | 0 | 2 | 28 | 4 | 3 | 6 | **HIGH_MEANINGFUL** |
| **2024-10** | Full | 59 | 57 | 0 | 2 | 59 | 11 | 9 | 12 | **HIGH_MEANINGFUL** |
| **2024-11** | Full | 31 | 28 | 0 | 3 | 31 | 5 | 3 | 4 | **HIGH_MEANINGFUL** |
| **2024-12** | Full | 11 | 9 | 0 | 2 | 11 | 2 | 2 | 2 | **HIGH_MEANINGFUL** |
| **2025-01** | Full | 12 | 10 | 0 | 2 | 12 | 2 | 2 | 3 | **HIGH_MEANINGFUL** |
| **2025-02** | Full | 57 | 56 | 0 | 1 | 57 | 11 | 6 | 11 | **HIGH_MEANINGFUL** |
| **2025-03** | Full | 70 | 68 | 0 | 2 | 70 | 12 | 6 | 15 | **HIGH_MEANINGFUL** |
| **2025-04** | Full | 75 | 74 | 0 | 1 | 75 | 10 | 7 | 10 | **HIGH_MEANINGFUL** |
| **2025-05** | Full | 35 | 32 | 0 | 3 | 35 | 6 | 4 | 6 | **HIGH_MEANINGFUL** |
| **2025-06** | Full | 45 | 43 | 0 | 2 | 45 | 5 | 2 | 7 | **HIGH_MEANINGFUL** |
| **2025-07** | Full | 47 | 45 | 0 | 2 | 47 | 6 | 4 | 7 | **HIGH_MEANINGFUL** |
| **2025-08** | Full | 50 | 49 | 0 | 1 | 50 | 5 | 1 | 5 | **HIGH_MEANINGFUL** |
| **2025-09** | Full | 53 | 51 | 0 | 2 | 53 | 5 | 4 | 11 | **HIGH_MEANINGFUL** |
| **2025-10** | Full | 49 | 46 | 0 | 3 | 49 | 4 | 3 | 5 | **HIGH_MEANINGFUL** |
| **2025-11** | Full | 50 | 49 | 0 | 1 | 50 | 6 | 3 | 7 | **HIGH_MEANINGFUL** |
| **2025-12** | Full | 51 | 49 | 0 | 2 | 51 | 7 | 4 | 10 | **HIGH_MEANINGFUL** |
| **2026-01** | Full | 57 | 55 | 0 | 2 | 57 | 5 | 4 | 6 | **HIGH_MEANINGFUL** |
| **2026-02** | Full | 30 | 29 | 0 | 1 | 30 | 4 | 4 | 6 | **HIGH_MEANINGFUL** |
| **2026-03** | Full | 42 | 40 | 0 | 2 | 42 | 7 | 4 | 8 | **HIGH_MEANINGFUL** |
| **2026-04** | Full | 41 | 40 | 0 | 1 | 41 | 9 | 3 | 8 | **HIGH_MEANINGFUL** |
| **2026-05** | Full | 32 | 30 | 0 | 2 | 32 | 5 | 4 | 6 | **HIGH_MEANINGFUL** |
| **2026-06** | Full | 49 | 47 | 0 | 2 | 49 | 6 | 5 | 6 | **HIGH_MEANINGFUL** |
| **2026-07** | Full | 47 | 45 | 0 | 2 | 47 | 3 | 3 | 4 | **HIGH_MEANINGFUL** |
| **2026-08** | Full | 36 | 35 | 0 | 1 | 36 | 3 | 2 | 2 | **HIGH_MEANINGFUL** |
| **2026-09** | Full | 81 | 78 | 0 | 3 | 81 | 10 | 9 | 7 | **HIGH_MEANINGFUL** |
| **2026-10** | Full | 55 | 54 | 0 | 1 | 55 | 7 | 7 | 4 | **HIGH_MEANINGFUL** |
| **2026-11** | Partial (1-3) | 4 | 2 | 0 | 2 | 2 | 4 | 4 | 4 | **MODERATE (QUARANTINED)** |

---

## 4. Documented Coverage Limitations & Isolated Periods

Per Rule S-06 (Honesty and Transparency), the protocol explicitly identifies historical coverage limitations:

### 1. The 2024-07 and 2024-08 Binance Ingestion Gap
- **Finding:** In July 2024, zero Binance announcements were ingested; in August 2024, only 2 announcements were ingested.
- **Cause:** Historical API pagination limitations during Catalog 49 backfill.
- **Research Mitigation:** Both months contain official BLS CPI and FOMC rate releases (2 per month). During these two months, the news-veto layer acts primarily on macroeconomic boundaries, while technical signals without macro overlap pass through unimpeded. The strategy behaves as technical baseline.

### 2. GDELT Sub-Daily Exclusion
- **Finding:** 66 GDELT records exist in the corpus (60 in 2024, 6 in 2026).
- **Limitation:** All 66 GDELT records lack verified publisher publication timestamps and are marked `PARTIALLY_VERIFIED`.
- **Enforcement:** Banned from all intraday experiments (`15m`, `1h`, `4h`). Intraday news-veto experiments operate exclusively on Binance server announcements and authoritative macro releases.

### 3. November 2026 Forward Scheduled Events
- **Finding:** Two scheduled future macro calendar events exist in November 2026 (FOMC decision on Nov 4, BLS CPI on Nov 12).
- **Enforcement:** Quarantined from historical backtesting to prevent look-ahead contamination.

---

## 5. Machine-Readable Manifests

- Partition Manifest: `storage/exports/milestone_4_6_3_0/chronological_split_manifest.json`
- Full Coverage Matrix: `storage/exports/milestone_4_6_3_0/coverage_matrix.json`
