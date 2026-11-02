# NEPTUNE — Milestone 4.6.2.2: Dataset Versioning & Parquet Parity Report

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.2 (Workstream E)  
**Title:** Historical News Dataset Versioning (`v2.0.0-news-historical`) & Storage Parity  
**Status:** Completed & Parity Verified  
**Governing Rules:** S-05, S-08, ADR-001, ADR-020, ADR-023, ADR-025  

---

## 1. Executive Summary & Objective

Workstream E formalizes the historical news dataset into a versioned, immutable research asset: **`v2.0.0-news-historical`**.  
It guarantees:
1. Complete cryptographic inventory of all news entities across SQLite and Parquet storage.
2. Exact zero-delta parity between relational tables and Parquet partition files.
3. 100% bit-for-bit preservation of frozen market dataset `v2.0.0`.

---

## 2. Frozen Market Dataset Integrity

The baseline market dataset `v2.0.0` was audited across all 420 Parquet files in `storage/datasets/v2.0.0/`:
- **Total Parquet Files:** 420
- **Directory Tree SHA-256:** `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`
- **Audit Verification Status:** **UNTOUCHED & IMMUTABLE (Exact Cryptographic Match)**

---

## 3. News Storage Reconciliation (SQLite vs. Parquet)

All news data was exported to partitioned snappy-compressed Parquet files via `NewsParquetExporter`:
- `storage/news/binance_announcements/{YYYY}/articles.parquet`
- `storage/news/binance_announcements/{YYYY}/versions.parquet`
- `storage/news/gdelt_gkg/{YYYY}/articles.parquet`
- `storage/news/gdelt_gkg/{YYYY}/versions.parquet`
- `storage/news/clusters/event_clusters.parquet`
- `storage/news/macro_calendar/macro_events.parquet`

### 3.1 Record Count Reconciliation Ledger

| Entity / Dimension | SQLite Database (`neptune.db`) | Parquet Partitions (`storage/news/`) | Count Delta | Status |
|--------------------|--------------------------------|--------------------------------------|-------------|--------|
| **Total News Articles** | 1,431 | 1,431 | **0** | **EXACT MATCH** |
| **Total Article Versions** | 1,431 | 1,431 | **0** | **EXACT MATCH** |
| **Total Event Clusters** | 1,421 | 1,421 | **0** | **EXACT MATCH** |
| **Macro Calendar Events** | 68 | 68 | **0** | **EXACT MATCH** |
| **Total Historical Records** | 1,499 | 1,499 | **0** | **EXACT MATCH** |

---

## 4. Dataset Manifest & Fingerprint

The authoritative dataset manifest is recorded at `storage/exports/milestone_4_6_2_2/dataset_manifest.json`:
- **Dataset Identifier:** `v2.0.0-news-historical`
- **Release Date:** 2026-11-03
- **Coverage Period:** 2024-01-01 through 2026-11-03 (35 continuous months)
- **Database File:** `storage/db/neptune.db`
- **Classifier Engine:** `v1.1.0-deterministic`
- **Verification Breakdown:**
  - `POINT_IN_TIME_VERIFIED`: 1,433 records (Binance + Macro)
  - `PARTIALLY_VERIFIED`: 66 records (GDELT)
  - `REJECTED`: 0 records

