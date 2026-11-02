# NEPTUNE — Milestone 4.6.2.1: Historical Coverage Audit

**Document:** Historical Coverage Reconciliation & 35-Month Temporal Mapping  
**Milestone:** 4.6.2.1 (Forensic Data Audit)  
**Evaluator:** Independent Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — RECONCILED WITH LIMITATIONS  

---

## 1. Executive Summary

This audit independently assesses the temporal completeness of the historical news dataset (`v1.0.0-news-historical`) across the entire 35-month evaluation window defined by market dataset `v2.0.0` (January 2024 through November 2026).

A rigorous, month-by-month accounting across all 35 calendar months was conducted across all three ingested sources:
1. **Source A:** Binance Official Announcements (Public CMS API)
2. **Source B:** GDELT 2.0 Global Knowledge Graph (GKG Historical Archives)
3. **Source C:** Canonical Historical Macroeconomic & Crypto Calendar (`news_macro_events`)

### Primary Forensic Findings:
- **Total Months in Benchmark:** 35 months (2024-01 to 2026-11).
- **Populated Months (All Sources Combined):** 18 of 35 months ($51.4\%$).
- **Zero-Record Months (All Sources Combined):** 17 of 35 months ($48.6\%$).
- **Populated Months (News Articles Only):** 14 of 35 months ($40.0\%$).
- **Missing Months (News Articles Only):** 21 of 35 months ($60.0\%$).
- **The 2025 Coverage Void Root Cause:** Every calendar month in 2025 (12 consecutive months) contains exactly zero records. The technical root cause is confirmed to be **`SOURCE_NOT_QUERIED` (intentional bounded sampling design)** in `execute_staged_ingest.py`, NOT an absence of historical events in 2025.

---

## 2. Complete 35-Month Historical Coverage Matrix

The following matrix provides the definitive, independently audited accounting of records across each month from 2024-01 through 2026-11. All 35 months are represented, including zero-count periods.

| Month | Total Records | Binance (A) | GDELT (B) | Macro (C) | BTC Mentions | ETH Mentions | BNB Mentions | PIT Verified | PIT Partial | Status | Technical Operational Reason |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---|
| **2024-01** | 34 | 0 | 31 | 3 | 34 | 3 | 3 | 3 | 31 | `POPULATED` | GDELT ETF launch sample + 3 Macro events |
| **2024-02** | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | `POPULATED` | BLS CPI release |
| **2024-03** | 3 | 0 | 0 | 3 | 2 | 3 | 2 | 3 | 0 | `POPULATED` | ETH Dencun Hard Fork + FOMC + BLS CPI |
| **2024-04** | 8 | 0 | 6 | 2 | 8 | 2 | 2 | 2 | 6 | `POPULATED` | BTC 4th Halving + BLS CPI + GDELT Halving |
| **2024-05** | 26 | 18 | 5 | 3 | 11 | 9 | 4 | 21 | 5 | `POPULATED` | Binance Cat 49 + SEC ETH ETF + GDELT |
| **2024-06** | 41 | 39 | 0 | 2 | 19 | 10 | 6 | 41 | 0 | `POPULATED` | Binance Cat 49 (Pages 58-62) + FOMC + CPI |
| **2024-07** | 2 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | 0 | `POPULATED` | FOMC Rate Decision + BLS CPI |
| **2024-08** | 9 | 0 | 7 | 2 | 9 | 2 | 2 | 2 | 7 | `POPULATED` | GDELT Crash Sample + BLS CPI + Jackson Hole |
| **2024-09** | 25 | 22 | 1 | 2 | 16 | 7 | 6 | 24 | 1 | `POPULATED` | Binance Cat 49 + FOMC 50bps cut + GDELT |
| **2024-10** | 55 | 53 | 0 | 2 | 31 | 18 | 15 | 55 | 0 | `POPULATED` | Binance Cat 49 (Pages 48-52) + BLS NFP + CPI |
| **2024-11** | 34 | 21 | 10 | 3 | 25 | 11 | 7 | 24 | 10 | `POPULATED` | Binance Cat 49 + US Election GDELT + FOMC |
| **2024-12** | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | `POPULATED` | FOMC 25bps Rate Cut |
| **2025-01** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-02** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-03** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-04** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-05** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-06** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-07** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-08** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-09** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-10** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-11** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2025-12** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-47 not queried; GDELT 2025 skipped; Macro 2025 unpopulated |
| **2026-01** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-20 (Jan-May 2026) not queried; Macro 2026 unpopulated |
| **2026-02** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-20 (Jan-May 2026) not queried; Macro 2026 unpopulated |
| **2026-03** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-20 (Jan-May 2026) not queried; Macro 2026 unpopulated |
| **2026-04** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-20 (Jan-May 2026) not queried; Macro 2026 unpopulated |
| **2026-05** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | `SOURCE_NOT_QUERIED` | Pages 11-20 (Jan-May 2026) not queried; Macro 2026 unpopulated |
| **2026-06** | 46 | 46 | 0 | 0 | 17 | 10 | 12 | 46 | 0 | `POPULATED` | Binance Cat 49 (Pages 8-10) + Cat 161 |
| **2026-07** | 45 | 45 | 0 | 0 | 18 | 9 | 10 | 45 | 0 | `POPULATED` | Binance Cat 49 (Pages 6-8) |
| **2026-08** | 35 | 35 | 0 | 0 | 12 | 7 | 8 | 35 | 0 | `POPULATED` | Binance Cat 49 (Pages 4-6) |
| **2026-09** | 78 | 78 | 0 | 0 | 25 | 16 | 21 | 78 | 0 | `POPULATED` | Binance Cat 49 (Pages 2-4) |
| **2026-10** | 54 | 54 | 0 | 0 | 21 | 14 | 14 | 54 | 0 | `POPULATED` | Binance Cat 49 (Pages 1-2) |
| **2026-11** | 8 | 2 | 6 | 0 | 3 | 2 | 2 | 2 | 6 | `POPULATED` | Binance Cat 49 (Page 1) + GDELT Live Test |
| **TOTAL** | **505** | **413** | **66** | **26** | **236** | **154** | **126** | **439** | **66** | — | — |

---

## 3. Investigation of the 2025 Coverage Void

### 3.1 Technical Root Cause Analysis
A forensic code audit of `scratch/execute_staged_ingest.py` reveals the exact mechanism that produced 0 records across the entire year 2025:

1. **Binance CMS Pagination Skipping:**
   - Ingested Catalog 49 (Pages 1–10): Covered 2026-06-10 to 2026-11-02 (260 articles).
   - Ingested Catalog 49 (Pages 48–52): Covered 2024-10-15 to 2024-11-28 (100 articles).
   - Ingested Catalog 49 (Pages 58–62): Covered 2024-05-10 to 2024-06-25 (100 articles).
   - Ingested Catalog 161 (Pages 1–5, 13–16): Delistings for late 2026 and mid 2024.
   - **Pages 11 through 47 were intentionally not requested.** Because Binance announcements are paginated in reverse-chronological order, pages 11 through 47 contained all announcements published between December 2024 and May 2026 (the entirety of 2025).

2. **GDELT Sampling Design:**
   - The GDELT ingestion pipeline explicitly downloaded only 6 targeted historical archives (15-minute windows):
     - `20240111140000.gkg.csv.zip` (2024-01-11 ETF Launch)
     - `20240420001500.gkg.csv.zip` (2024-04-20 Halving)
     - `20240523211500.gkg.csv.zip` (2024-05-23 ETH ETF 19b-4)
     - `20240805120000.gkg.csv.zip` (2024-08-05 Global Market Crash)
     - `20240918181500.gkg.csv.zip` (2024-09-18 FOMC 50bps cut)
     - `20241106040000.gkg.csv.zip` (2024-11-06 US Election)
   - Zero archives from calendar year 2025 were requested.

3. **Macro Calendar Registry Scope:**
   - In `backend/app/data/news/macro_calendar.py`, `HistoricalMacroCalendarRegistry.get_canonical_macro_events()` was constructed specifically for the 2024 macroeconomic calendar (8 FOMC dates, 14 BLS CPI/NFP dates, 2 SEC ETF orders, 2 network upgrades).
   - No 2025 or 2026 FOMC or BLS release dates were added to the hardcoded registry.

### 3.2 Engineering Rationale & Justification
The decision in Milestone 4.6.2 to sample discrete blocks rather than execute a continuous crawl of pages 11–47 was motivated by operational engineering constraints:
- **HTTP 429 Rate Limiting:** Binance's public CMS API aggressively rate-limits client IP addresses after rapid bursts of article detail queries (`fetch_announcement_detail`). Crawling pages 11–47 would require querying 37 pages $\times 20 = 740$ additional article bodies, requiring hours of polite exponential backoff to avoid a temporary or permanent IP ban.
- **Milestone Scope:** Milestone 4.6.2 was designed as a data ingestion and classification prototype milestone, demonstrating multi-source ingestion, classification taxonomy, and deduplication rather than full multi-year production crawling.

---

## 4. Coverage Implications for Quantitative Strategy Research

1. **Intraday Continuous Alpha Backtests are Invalid:**
   - A strategy evaluated over the continuous 35-month market dataset `v2.0.0` cannot use this news dataset as a continuous intraday signal. A continuous backtest running across 2025 would experience 365 consecutive days of zero news input, creating an artificial regime bias.
2. **Event-Study & Regime-Overlay Research is Valid:**
   - For isolated event studies (e.g., measuring the 24-hour post-event drift following FOMC rate cuts or Spot ETF approvals in 2024), the dataset is fully valid and point-in-time safe.
3. **Recommendation for Milestone 4.6.3:**
   - Prior to authorizing news-driven strategy research on continuous historical backtests, a dedicated, throttled backfill covering pages 11–47 of Binance Catalog 49 and the 2025 Macro Calendar (FOMC/CPI) must be completed.

---
*End of Coverage Audit Report.*

