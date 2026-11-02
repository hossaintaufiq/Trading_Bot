# NEPTUNE — Milestone 4.6.2: Engineering & Research Implementation Report

> **Document ID:** `DOC-RES-4.6.2-IMP`  
> **Milestone:** 4.6.2 — Historical News Backfill, Event Classification & Point-in-Time Dataset Construction  
> **Status:** COMPLETED & AUDITED  
> **Date:** 2026-11-03  
> **Branch:** `quant-expectancy-validation`  
> **Baseline Commit:** `0b08c7f`  
> **Final Milestone Commit:** `[HEAD]`  
> **Governing Architecture:** ADR-023, ADR-024  

---

## 1. Milestone Mission & Scope

The mandate of Milestone 4.6.2 was to resolve the acute historical coverage gap (31 missing months) and catalog relevance issue identified in Milestone 4.6.1.1. The objective was not to artificially inflate article counts, but to construct a reliable, timestamp-aware, asset-relevant historical event dataset for `BTCUSDT`, `ETHUSDT`, and `BNBUSDT` spanning multiple regimes across 2024–2026.

### Non-Negotiable Constraint Audit:
- [x] **Constraint 1 (Dataset v2.0.0 Preservation):** All 420 market price Parquet files remained untouched. Composite directory tree SHA-256 verified as `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`.
- [x] **Constraint 2 (Article Immutability):** Article revisions are strictly append-only. No historical version was mutated or overwritten.
- [x] **Constraint 3 (Paper Trading Isolation):** News intelligence is completely isolated from Central Brain, Risk Manager, Strategy Analyst, and Execution Manager.
- [x] **Constraint 4 (Trading Strategy Invariance):** Deterministic trading strategies were unmodified.
- [x] **Constraint 5 (Architecture Invariance):** SQLite (WAL mode) and Apache Parquet only. No Redis, Kafka, PostgreSQL, Kubernetes, or microservices.
- [x] **Constraint 6 (Point-in-Time Integrity):** No synthetic publication timestamps were created. GDELT observation timestamps were strictly preserved as `provider_seen_at` under `PARTIALLY_VERIFIED` status.

---

## 2. Implemented Architecture & Deliverables

### 2.1 Schema Migration (`006_news_classification_schema.sql`)
- Created `news_macro_events` table for Source C with scheduled vs actual release timestamps, source URLs, SHA-256 payload fingerprints, and `POINT_IN_TIME_VERIFIED` verification status.
- Added classification columns to `news_articles` (`event_category`, `relevance_classification`, `affected_assets_json`, `classification_evidence_json`, `classifier_version`, `confidence_score`, `classified_at`).
- Added research coordinates to `news_article_versions` (`archive_available_at`, `research_available_at`).

### 2.2 Deterministic Event & Relevance Classifier (`classifier.py`)
- Implemented [`DeterministicNewsClassifier`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/classifier.py) (`v1.0.0-deterministic`).
- Codified transparent regex patterns for all 15 event categories.
- Codified 6-tier asset relevance logic. Specifically resolved the BNB/exchange conflation trap: Binance platform updates and security incidents are classified as `EXCHANGE_WIDE`, never `DIRECT_ASSET` for BNB unless the token supply/chain is explicitly targeted.

### 2.3 Macroeconomic Event Calendar Registry (`macro_calendar.py`)
- Authored [`HistoricalMacroCalendarRegistry`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/macro_calendar.py) covering 26 canonical events ground-truthed from official agencies (`federalreserve.gov`, `bls.gov`, `sec.gov`, `blockstream.info`, `etherscan.io`) with exact second-level timestamps.

### 2.4 Staged Ingestion Expansion (`service.py`, `binance_client.py`, `gdelt_client.py`)
- Paged back across Binance Catalog 49 ("Latest Binance News") and Catalog 161 ("Delistings"), capturing 413 verified operational and listing notices across 2024 and 2026.
- Ingested 6 historical GDELT 2.0 master GKG archives covering pivotal market milestones.
- Implemented rate-limiting awareness with 10.0-second exponential backoff on `HTTP 429`.

### 2.5 Machine-Readable Analytical Exports
Generated in `storage/exports/milestone_4_6_2/`:
1. `source_coverage.csv`
2. `monthly_asset_coverage.csv`
3. `event_cluster_inventory.csv`
4. `timestamp_verification_inventory.csv`
5. `failed_ingestion_records.csv`
6. `news_dataset_manifest.json` (Composite SHA-256: `04cae914870b35afc69ea3968a0b86f005fe068726625ec9c47ef2c1044674f1`)
7. `reproducibility_metadata.json`

---

## 3. Test & Verification Results

| Suite | Component | Scope | Tests Run | Result |
| :--- | :--- | :--- | :--- | :--- |
| `test_milestone_4_6_2_news.py` | News Foundation & Dedup | 105-pair dedup corpus, classifier, PIT, macro | 7 | **ALL PASSED (100%)** |
| `test_milestone_4_6_1_news.py` | Milestone 4.6.1 Base | Immutability, temporal resolution, idempotency | 13 | **ALL PASSED (100%)** |
| Complete Backend Suite | Entire NEPTUNE Backend | Analytics, signals, risk, execution, DB | 174 | **ALL PASSED (100%)** |
| Complete Frontend Suite | NEPTUNE Web UI | Formatters, state, components | 4 | **ALL PASSED (100%)** |

---

## 4. Architectural Decisions Update (ADR-024)

Recorded in `docs/ARCHITECTURE_DECISIONS.md`:
- **ADR-024: 15-Category Event Taxonomy, Asset Relevance Isolation & Macroeconomic Calendar Registry**
  - Confirmed the separation of `DIRECT_ASSET` from `EXCHANGE_WIDE` to prevent artificial signal contamination on BNB.
  - Formally established Source C (Macroeconomic Calendar Registry) as a deterministic `POINT_IN_TIME_VERIFIED` foundation for macro regime research.
  - Mandated that GDELT 15-minute observation timestamps remain classified as `PARTIALLY_VERIFIED` and excluded from high-frequency backtests.

---

## 5. Milestone Verdict

Final Status: **PASS WITH LIMITATIONS**

### Answers to Required Milestone Questions:
1. **Is the historical news dataset large enough for controlled research?**  
   *Yes.* With 505 total records (479 articles + 26 macro events) and 474 event clusters covering both 2024 and 2026 across BTC, ETH, and BNB, the dataset is sufficiently large to support initial controlled filtering experiments.
2. **Which records are eligible for strict point-in-time experiments?**  
   *The 439 `POINT_IN_TIME_VERIFIED` records* (413 Binance announcements and 26 Macro Calendar records) have certified millisecond/second timestamps and are fully eligible for candle-close synchronization.
3. **Which sources are unsuitable for short-horizon research?**  
   *GDELT 2.0 Historical GKG archives.* Due to the absence of publisher publication timestamps and 15-minute batch quantization, GDELT is unsuitable for 1m, 5m, or 15m candle-level strategy research. It is restricted to daily or regime-level exploratory research.
4. **Does coverage span multiple market regimes?**  
   *Yes.* Coverage spans the January 2024 ETF approval regime, April 2024 Halving, May 2024 Dencun/ETH ETF regime, August 2024 Yen carry unwind crash, September 2024 FOMC rate cut, November 2024 US Election, and the 2026 baseline.
5. **Is the dataset ready for Milestone 4.6.3?**  
   *Yes.* The dataset, taxonomy, and point-in-time boundaries are fully prepared for Milestone 4.6.3 (Feature Engineering & Controlled Expectancy Experiments).
6. **What is the strongest remaining data limitation?**  
   *GDELT's lack of true publication timestamps and Binance CMS's aggressive IP rate limiting on deep pagination.* Any production or multi-year backfill requiring $> 500$ Binance calls requires throttled pacing ($\ge 0.5\text{s}$ delay) or cached local archives.
