# NEPTUNE — Milestone 4.6.2.5: News Point-in-Time & Macro Boundary Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.5  
**Topic:** Audit C & D — News Point-in-Time Eligibility, Provenance Taxonomy & Macro Calendar Reconciliation  
**Date:** 2026-11-03  
**Status:** Audited & Verified  

---

## 1. Provenance Timestamp Taxonomy

To prevent look-ahead bias and revisionism in news-driven research (Rule S-05), NEPTUNE establishes an immutable temporal hierarchy:

| Coordinate | Definition | Source Attribution | Point-in-Time Defensibility |
|---|---|---|---|
| `published_at` | Official publication timestamp declared by publisher or exchange. | Binance Announcements (`publishDate`) | Validated millisecond timestamp. |
| `provider_seen_at` | First observation timestamp recorded by an indexing provider. | GDELT GKG (15-minute slice timestamp) | Observation time, NOT publisher publication time. |
| `first_observed_at` | Timestamp when NEPTUNE first crawled or indexed the record. | All Ingestion Pipelines | System entry watermark. |
| `collected_at` | Wall-clock execution timestamp of the ingestion job. | Ingestion Checkpoint | Anti-lookahead boundary ($T_{\text{pub}} \le T_{\text{coll}} + 1\text{h}$). |
| `available_at` | Earliest defensible timestamp at which a trader could have consumed the data. | Synchronizer Output | Binance: $T_{\text{pub}}$; GDELT: $T_{\text{seen}} + 300\text{s}$; Macro: $T_{\text{actual\_release}}$. |
| `revision_observed_at` | Timestamp when an updated payload version was scraped. | Version Ledger | Used to quarantine future article edits. |

---

## 2. Forensic Reconciliation of Macro Calendar Records (68 Total)

An independent query of all 68 records in `news_macro_events` was conducted under a decision cutoff of `2026-11-02T12:00:00Z` for symbol `BTCUSDT`:

```
Total Macro Records: 68
├─► Eligible Records:                                         62 (91.18%)
└─► Excluded Records:                                          6 ( 8.82%)
      ├─► FORWARD_SCHEDULED_EVENT_QUARANTINED:                2
      ├─► MISSING_REQUIRED_PROVENANCE:                        1
      └─► IRRELEVANT_TO_TARGET_ASSET_BTCUSDT:                 3
```

### 2.1 Quarantined Forward Scheduled Events (2 Records)
The following events represent scheduled forward releases occurring beyond the historical audit cutoff (`2026-11-03T23:59:59Z`). They are strictly quarantined from historical backtests:
1. `macro_20261104_fomc_decision`: FOMC Rate Decision scheduled for `2026-11-04T19:00:00Z`.
2. `macro_20261112_bls_cpi`: US BLS CPI Release scheduled for `2026-11-12T13:30:00Z`.

### 2.2 Missing Provenance Exclusion (1 Record)
1. `macro_20240802_bls_nfp`: US BLS Nonfarm Payrolls (`2024-08-02T12:30:00Z`).
   - Audit Inspection: `first_observed_at: None`, `collected_at: None`.
   - Action: **Strictly Excluded** with `MISSING_REQUIRED_PROVENANCE`. Records lacking ingestion provenance watermarks are never promoted to verified backtest status.

### 2.3 Asset Irrelevance Exclusion (3 Records)
1. `macro_20240313_eth_dencun`: Ethereum Dencun Hard Fork (`affected_assets: ["ETH"]`).
2. `macro_20240523_sec_eth_etf`: SEC Spot Ethereum ETF Approval (`affected_assets: ["ETH"]`).
3. `macro_20250507_eth_pectra`: Ethereum Pectra Network Upgrade (`affected_assets: ["ETH"]`).
   - Action: **Excluded** for BTCUSDT simulations with `IRRELEVANT_TO_TARGET_ASSET_BTCUSDT`.

---

## 3. Schema Normalization & Boundary Gating

### 3.1 Defect Discovery (F-4625-01)
During initial inspection, `NewsIntelligenceBoundary` relied on dictionary keys `event_id`, `actual_release_time`, and `available_at`. However, SQLite and Parquet partitions for macro events use schema column names `macro_event_id`, `actual_release_at`, and `affected_assets_json`.

This mismatch caused all raw macro events to be excluded with `MISSING_AVAILABLE_AT_TIMESTAMP`.

### 3.2 Implemented Remediation
In [`backend/app/simulation/news_boundary.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/news_boundary.py), multi-key fallback normalization was implemented:
- `event_id`: Resolves across `event_id`, `macro_event_id`, `article_code`, `cluster_id`, `source_record_id`.
- `available_at_iso`: Resolves across `available_at`, `actual_release_at`, `actual_release_time`, `published_at`.
- `actual_release`: Resolves across `actual_release_time`, `actual_release_at`, `scheduled_at`.
- `affected_assets`: Resolves across `affected_assets` list or deserializes `affected_assets_json` string.
- `is_macro`: Evaluates true for `source in ("macro_calendar", "bls", "sec_gov", "bitcoin_core", "ethereum_foundation", "federal_reserve")` or `event_category == "MACROECONOMIC"` or `relevance_classification == "MACRO"`.

---

## 4. GDELT and Revision Isolation Verification

1. **GDELT Sub-Daily Prohibition:**
   `NewsIntelligenceBoundary` enforces that GDELT GKG records are strictly rejected on 15m, 1h, and 4h backtests with `GDELT_SUB_DAILY_INTRADAY_PROHIBITED`. GDELT is only admitted on daily (`1d`) or longer horizons where 15-minute indexing jitter cannot cause intrabar look-ahead.
2. **Revision Isolation:**
   When an article contains multiple versions in its revision history, `PointInTimeExecutionSynchronizer.filter_visible_version` selects only the highest version number with `available_at <= candle_close_dt`. Revisions scraped after the decision cutoff remain completely invisible to simulated agents.
