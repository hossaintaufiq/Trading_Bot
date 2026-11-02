# NEPTUNE — Milestone 4.6.2: Historical News Source Coverage Analysis

> **Document ID:** `DOC-RES-4.6.2-SRC`  
> **Milestone:** 4.6.2 — Historical News Backfill, Event Classification & Point-in-Time Dataset Construction  
> **Status:** APPROVED & EMPIRICALLY VALIDATED  
> **Date:** 2026-11-03  
> **Governing Rules:** Rule S-05 (Look-Ahead Bias Prevention), Rule S-06 (No Fabricated Data), ADR-023, ADR-024  
> **Baseline Commit:** `0b08c7f`  

---

## 1. Executive Summary

Milestone 4.6.1.1 identified two fundamental vulnerabilities in NEPTUNE's initial news ingestion infrastructure:
1. **Severe Historical Sparsity:** Only 66 records existed across the multi-year market dataset window, leaving 31 months completely devoid of news coverage.
2. **Catalog Misalignment:** Ingestion was confined to Binance Catalog 48 ("New Cryptocurrency Listing"), capturing obscure altcoin spot listings while missing exchange security upgrades, wallet maintenance, proof-of-reserves audits, delistings, and direct BTC/ETH developments.

Milestone 4.6.2 executed a staged historical backfill across three distinct source classes:
- **Source A (Binance CMS Catalogs 49 & 161):** 413 verified announcements spanning continuous operations from May 2024 through November 2026.
- **Source B (GDELT 2.0 Historical GKG Master Archives):** 66 crypto-filtered records extracted directly from unthrottled 15-minute master archives covering historical anchor dates (Bitcoin ETF approval Jan 2024, Bitcoin 4th Halving Apr 2024, Ethereum ETF approval May 2024, Yen carry unwind Aug 2024, FOMC 50bps cut Sep 2024, US Election Nov 2024).
- **Source C (Historical Macroeconomic Event Registry):** 26 canonical events ground-truthed from Federal Reserve, BLS, and SEC official releases with second-level timestamps.

Total dataset expansion grew from **66 records to 505 authoritative historical records**, establishing multi-regime empirical continuity across 2024–2026.

---

## 2. Empirical Source Inventory

The following table summarizes the persisted news dataset in [`neptune.db`](file:///d:/Project%202026/Trading_bot/storage/db/neptune.db) and Parquet partitions:

| Source Identifier | Source Category | Ingested Records | Unique URLs | Earliest Event UTC | Latest Event UTC | Missing Published Date | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `binance_announcements` | Exchange Operations / Listings | **413** | 413 | 2024-05-15 03:00:14 | 2026-11-02 12:45:05 | 0 (0.0%) | `POINT_IN_TIME_VERIFIED` |
| `gdelt_gkg` | Global News Wire Aggregator | **66** | 66 | 2024-01-10 21:00:00 | 2026-11-02 17:15:00 | 66 (100.0%) | `PARTIALLY_VERIFIED` |
| `macro_calendar` | Central Bank & Agency Releases | **26** | 26 | 2024-01-10 20:45:00 | 2024-12-18 19:00:00 | 0 (0.0%) | `POINT_IN_TIME_VERIFIED` |
| **Combined Total** | **Multi-Source Foundation** | **505** | **505** | **2024-01-10 20:45:00** | **2026-11-02 17:15:00** | **66 (13.1%)** | **86.9% Strict PIT** |

```
Distribution of Source Records:
  Binance CMS Announcements:   ████████████████████████████████ 413 (81.8%)
  GDELT 2.0 Historical GKG:   █████ 66 (13.1%)
  Macroeconomic Registry:      ██ 26 (5.1%)
```

---

## 3. Source Investigation Findings

### 3.1 Source A: Binance CMS Catalogs (49 & 161)
- **Catalog 49 ("Latest Binance News"):** Contains 4,477 total historical articles extending continuously from 2020 to November 2026.
  - Page 1–10: June 2026 to November 2026 (Operational updates, wallet upgrades, security recovery updates).
  - Page 45–55: August 2024 to November 2024 (Proof of Reserves, futures tick size adjustments).
  - Page 58–70: December 2023 to June 2024 (Dencun preparation, fee reductions, order size revisions).
- **Catalog 161 ("Delistings / Removals"):** Contains 446 articles covering periodic removal of spot trading pairs, margin delistings, and leverage adjustments.
- **Pacing & Rate Limiting:** Binance's public REST endpoint `/bapi/composite/v1/public/cms/article/detail/query` enforces strict IP rate limiting (~100 requests per minute). Excessive bursts return `HTTP 429: Too Many Requests`. This was resolved in [`BinanceNewsClient`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/binance_client.py#L31-L75) via exponential backoff with a mandatory 10.0-second cooldown upon encountering `429`.

### 3.2 Source B: GDELT 2.0 Historical GKG Master Archives
- **Master Archive Availability:** Rather than relying on the DOC API (limited to rolling 3-month lookback and aggressive rate throttling), historical master archives are unthrottled and hosted permanently at `http://data.gdeltproject.org/gdeltv2/{YYYYMMDDHHMMSS}.gkg.csv.zip`.
- **Extraction Protocol:** In-memory streaming decompression using [`GdeltGkgClient.parse_gkg_archive_content`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/gdelt_client.py#L126-L195) successfully extracts records mentioning `BTC`, `ETH`, or `BNB` with zero disk clutter.
- **Timestamp Integrity:** GDELT provides only 15-minute batch indexing timestamps (`provider_seen_at`), never verified publisher timestamps (`published_at`). In accordance with Rule S-05 and ADR-023, these records are strictly designated as `PARTIALLY_VERIFIED` with a conservative 5-minute ingestion latency buffer.

### 3.3 Source C: Historical Macroeconomic Event Registry
- **Deterministic Ground Truth:** Ingested via [`HistoricalMacroCalendarRegistry`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/macro_calendar.py#L22-L135), providing second-level precision for:
  - 8 FOMC rate decisions across 2024.
  - 11 BLS Consumer Price Index (CPI) releases.
  - 3 BLS Non-Farm Payroll (NFP) releases (including the Aug 2, 2024 Sahm-rule trigger).
  - 4 Structural Crypto Milestones (Bitcoin Spot ETF Omnibus Approval, 4th Bitcoin Halving Block 840,000, Ethereum Dencun Hard Fork, and Spot Ethereum ETF 19b-4 Omnibus Approval).

---

## 4. Coverage Across Market Regimes

The historical backfill successfully bridges the missing coverage gap across key market regimes:

1. **ETF Approval & Accumulation Regime (Jan 2024 – Mar 2024):** Ingested GDELT ETF approval batches and BLS CPI prints.
2. **Post-Halving & Dencun L2 Regime (Apr 2024 – Jun 2024):** Ingested Halving block 840,000, Dencun activation, Ethereum ETF 19b-4 order, and Binance Catalog 49 maintenance updates.
3. **Macro Volatility & Yen Unwind Regime (Aug 2024 – Oct 2024):** Ingested the Aug 2 NFP trigger, Aug 5 market crash coverage, and September FOMC 50bps rate cut.
4. **Election & Year-End Rally Regime (Nov 2024):** Ingested US election GDELT batch and subsequent FOMC rate cuts.
5. **Milestone Baseline Regime (Jun 2026 – Nov 2026):** Ingested 231 Binance operational notices, Proof-of-Reserves audits, and delisting notices.

---

## 5. Summary Verdict

Source coverage expanded from an unviable 66 listing notices to a balanced, multi-source corpus of 505 records. All source records are permanently archived, reproducible from raw payloads, and reconciled between SQLite and partitioned Parquet storage.
