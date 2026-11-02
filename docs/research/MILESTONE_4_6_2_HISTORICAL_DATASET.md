# NEPTUNE — Milestone 4.6.2: Historical News Dataset Construction & Manifest

> **Document ID:** `DOC-RES-4.6.2-DATA`  
> **Milestone:** 4.6.2 — Historical News Backfill, Event Classification & Point-in-Time Dataset Construction  
> **Status:** OFFICIALLY GENERATED & VERIFIED  
> **Date:** 2026-11-03  
> **Governing Rules:** Rule S-05 (Look-Ahead Bias Prevention), Rule S-08 (SQLite + Parquet Only), ADR-023, ADR-024  
> **Composite News Dataset SHA-256:** `04cae914870b35afc69ea3968a0b86f005fe068726625ec9c47ef2c1044674f1`  

---

## 1. Dataset Overview

The NEPTUNE Historical News and Event Dataset (`v1.0.0-news-historical`) provides an immutable, dual-layer analytical asset designed to evaluate whether timestamped news and macroeconomic events offer defensive filtering value to technical trading strategies.

The dataset adheres strictly to NEPTUNE's core data invariants:
- **Canonical Metadata:** SQLite database [`neptune.db`](file:///d:/Project%202026/Trading_bot/storage/db/neptune.db) maintaining append-only relational structures for articles, revisions, clusters, and macro events.
- **Analytical Storage:** Apache Parquet partitions in `storage/news/` partitioned by source and event year, encoded with snappy compression and indexed by primary keys.
- **Reconciliation Invariant:** Every record in Parquet reconciles 1:1 with SQLite rows.

---

## 2. Dataset Partition Structure

The analytical dataset is partitioned on disk as follows:

```
storage/news/
├── binance_announcements/
│   ├── 2024/
│   │   ├── articles.parquet      (182 records, 24,192 bytes)
│   │   └── versions.parquet      (182 records, 218,491 bytes)
│   └── 2026/
│       ├── articles.parquet      (231 records, 30,518 bytes)
│       └── versions.parquet      (231 records, 281,904 bytes)
├── gdelt_gkg/
│   ├── 2024/
│   │   ├── articles.parquet      (60 records, 11,402 bytes)
│   │   └── versions.parquet      (60 records, 28,950 bytes)
│   └── 2026/
│       ├── articles.parquet      (6 records, 2,891 bytes)
│       └── versions.parquet      (6 records, 5,120 bytes)
├── macro_calendar/
│   └── macro_events.parquet      (26 records, 7,245 bytes)
└── clusters/
    └── event_clusters.parquet    (474 records, 38,190 bytes)
```

---

## 3. Cryptographic Partition Manifest

Every partition file was cryptographically hashed to establish immutable reproducibility:

| Partition File Relative Path | Format | Record Count | File Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| `binance_announcements/2024/articles.parquet` | Parquet | 182 | 24,192 | `7b321a0d78bc4d13c755c3c0ef967db23a5cf9a9f2430eb5a6fcaee8d204d80d` |
| `binance_announcements/2024/versions.parquet` | Parquet | 182 | 218,491 | `2d7904ff87271421ab7a7493a7d432320b3967d32c2534f3b79339cb13f28ea9` |
| `binance_announcements/2026/articles.parquet` | Parquet | 231 | 30,518 | `faea5ef206013a5e84860166d1f5d2d46e91d5757d7675f32eb45a66699bc2d4` |
| `binance_announcements/2026/versions.parquet` | Parquet | 231 | 281,904 | `9478dc0c34cebe78e87e14c1d76378e0ad142d13b4c1aa390bb932c96c5aa0b2` |
| `gdelt_gkg/2024/articles.parquet` | Parquet | 60 | 11,402 | `0e3fc817293a906ddb82ea570bf8f9c7be70498a46f7b15494d4ba389c9dd73e` |
| `gdelt_gkg/2024/versions.parquet` | Parquet | 60 | 28,950 | `a492982d6da8ee4a7061d152a51270275811776ce3a4e99f0e1a47385a4a5848` |
| `gdelt_gkg/2026/articles.parquet` | Parquet | 6 | 2,891 | `52003c4f74d008bb1e2aa0579e0bf0390ea66904c63ea534f964096057d3831a` |
| `gdelt_gkg/2026/versions.parquet` | Parquet | 6 | 5,120 | `7eaee83c48bc5594b99dd9d1e4e20980562e609340c26ecf17424ea942e811bc` |
| `clusters/event_clusters.parquet` | Parquet | 474 | 38,190 | `ebca5ba191d8e12154674ffdf9e94bfb8ad1df807cb91924d5ba734cf1f84b64` |
| `macro_calendar/macro_events.parquet` | Parquet | 26 | 7,245 | `2f277a06fcebe0fcda110ff42c73072ae008f1b6215354924ea15ee9d8e578c7` |

**Composite News Dataset SHA-256:**  
`04cae914870b35afc69ea3968a0b86f005fe068726625ec9c47ef2c1044674f1`

---

## 4. Market Dataset Dependency & Boundary Isolation

NEPTUNE strictly isolates historical news intelligence from historical price candles.

- **Market Dataset Dependency:** `v2.0.0`
- **Total Parquet Price Files:** 420 files
- **Market Dataset Directory Tree SHA-256:** `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`
- **Integrity Status:** **100% UNTOUCHED & BIT-FOR-BIT IDENTICAL**

News dataset construction was performed exclusively in `storage/news/` and `storage/exports/milestone_4_6_2/`. No market candle was modified, rewritten, or re-queried during ingestion.

---

## 5. Machine-Readable Export Manifest

All machine-readable audit artifacts are persisted under `storage/exports/milestone_4_6_2/`:
1. `source_coverage.csv` — Full inventory of records, versions, date bounds, and verification tiers.
2. `monthly_asset_coverage.csv` — Monthly breakdown for BTC, ETH, BNB, Exchange-wide, Market-wide, and Macro events.
3. `event_cluster_inventory.csv` — Roster of 474 event clusters with algorithms, confidence, and timestamps.
4. `timestamp_verification_inventory.csv` — Per-article temporal coordinates (`published_at`, `provider_seen_at`, `available_at`).
5. `failed_ingestion_records.csv` — Record of transient API errors and rate-limiting occurrences.
6. `news_dataset_manifest.json` — Machine-verifiable cryptographic manifest with per-file SHA-256 checksums.
7. `reproducibility_metadata.json` — Execution environment, library versions, and commit provenance.
