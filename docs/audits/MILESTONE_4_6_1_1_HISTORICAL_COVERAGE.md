# NEPTUNE — Milestone 4.6.1.1 Audit A: Historical Coverage
## Forensic Audit of Persisted News Coverage, Temporal Gaps & Catalog Limitations

> **Audit ID:** `AUD-4.6.1.1-COV`  
> **Date:** 2026-11-03  
> **Target Dataset:** `storage/news/` and `storage/db/neptune.db`  
> **Manifest Version:** `news-v1.0.0` (Composite SHA-256: `58c4272ace3d148e85cd031d484a17bcb69eac4234e3f50bd2403d65d1db1084`)  
> **Evaluation Window:** Full Out-of-Sample Window (`OOS_FULL`: 2024-01-01 to 2026-11-01)

---

## 1. Executive Summary

This audit performs an independent, empirical census of the persisted news data ingested during Milestone 4.6.1. Rather than relying on implementation claims, the physical SQLite database (`storage/db/neptune.db`) and exported Parquet partitions were forensically inspected.

### Core Audit Finding
The persisted dataset of 66 records is **strictly a bounded engineering proof-of-pipeline sample**, not a historical backfill. Across NEPTUNE's 34-month canonical evaluation window (2024-01-01 to 2026-11-01), **31 months have zero news coverage**. Furthermore, the Binance sample (Catalog 48, "New Cryptocurrency Listing") contains **zero direct trading announcements for BTC or ETH**.

---

## 2. Empirical Record Inventory

### Table & Partition Counts
```
========================================================================================
PERSISTED NEWS DATA INVENTORY (neptune.db & storage/news/)
========================================================================================
Total Core Articles:                66
Total Article Version Records:      66
Total Event Clusters:               66
Cluster Member Mappings:            66
Ingestion Runs Logged:              3
Unique Raw URLs:                    66
Unique Canonical URLs:              66
Parquet Partitions:                 5 files (1.73 MB total)
========================================================================================
SOURCE DISTRIBUTION:
  - binance_announcements:          60 records (90.9%)
  - gdelt_gkg:                      6 records  (9.1%)
========================================================================================
```

---

## 3. Temporal Coverage & Date Boundaries

### Boundary Timestamps
- **Earliest Published Timestamp (`min_pub`):** `2026-08-25T04:30:01.817Z`
- **Latest Published Timestamp (`max_pub`):** `2026-10-29T11:48:52.329Z`
- **Earliest Available Timestamp (`min_avail`):** `2026-08-25T04:30:01.817Z`
- **Latest Available Timestamp (`max_avail`):** `2026-11-02T17:20:00.000Z`
- **Collection Timestamp Range (`collected_at`):** `2026-11-02T18:20:52Z` to `2026-11-02T18:21:58Z`

### Monthly Distribution Across 34-Month Benchmark Horizon

| Calendar Month | Canonical Partition | Binance Announcements | GDELT GKG Records | Total Records | Coverage Status |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **2024-01 to 2024-12** (12 mos) | `TRAIN` (Fold 1) | 0 | 0 | 0 | **100% MISSING** |
| **2025-01 to 2025-06** (6 mos) | `TRAIN` (Fold 2) | 0 | 0 | 0 | **100% MISSING** |
| **2025-07 to 2025-12** (6 mos) | `VALIDATION` | 0 | 0 | 0 | **100% MISSING** |
| **2026-01 to 2026-07** (7 mos) | `OOS_HISTORICAL_REF` | 0 | 0 | 0 | **100% MISSING** |
| **2026-08** | `OOS_PRISTINE` | 7 | 0 | 7 | Bounded Sample |
| **2026-09** | `OOS_PRISTINE` | 36 | 0 | 36 | Bounded Sample |
| **2026-10** | `OOS_PRISTINE` | 17 | 0 | 17 | Bounded Sample |
| **2026-11** | Outside OOS window | 0 | 6 | 6 | 15-min Archive Only |
| **Total (34 Months)** | — | **60** | **6** | **66** | **91.2% Temporal Gap** |

---

## 4. Asset & Event Category Breakdown

### Asset Assignment Matrix
The audit examined the `entities_json` assignments for all 66 records:

```
========================================================================================
ASSET RELEVANCE BY SOURCE
========================================================================================
Asset Symbol     Binance Announcements     GDELT GKG Records     Total Assigned
----------------------------------------------------------------------------------------
BTC              0                         1                     1
ETH              0                         0                     0
BNB              0                         5                     5
OTHER (Altcoins) 60                        0                     60
========================================================================================
```

### Critical Discovery: Catalog 48 Omission of Core Assets
1. **Catalog Bias:** All 60 Binance articles were ingested exclusively from **Catalog 48** ("New Cryptocurrency Listing").
2. **Zero Core Market Coverage:** Catalog 48 contains listings for new altcoins and tokenized assets (e.g., `bStocks`, seed tag tokens). It contains **0 announcements for BTC**, **0 for ETH**, and **0 for BNB**.
3. **Implication for Research:** An algorithmic trading model or news filter targeting BTCUSDT or ETHUSDT backtests will encounter **zero signals** in this dataset. Successful pagination of 3 pages (60 items) merely retrieved recent altcoin listings, not historical market intelligence.

---

## 5. Audit Conclusion & Feasibility Assessment

1. **Not a Historical Backfill:** Successful catalog pagination and archive ingestion must not be conflated with historical completeness. The current persisted dataset represents only 2 months of Binance listings and one 15-minute slice of GDELT.
2. **Missing Catalog Coverage:** To obtain actionable news for BTC, ETH, and BNB, ingestion must expand to:
   - Binance Catalog 49 ("Latest Binance News")
   - Binance Catalog 161 ("Delisting & Trading Pair Removal")
   - Multi-year GDELT master archives across 2024–2026
3. **Suitability Determination:** The dataset in its current state is **INSUFFICIENT** for running quantitative backtests on dataset `v2.0.0`. A full historical ETL run must precede any strategy experiments.

---
*End of Audit A — Project NEPTUNE Quantitative Systems Group*
