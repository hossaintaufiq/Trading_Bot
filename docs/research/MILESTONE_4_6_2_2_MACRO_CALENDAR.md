# NEPTUNE — Milestone 4.6.2.2: Macroeconomic & Regulatory Calendar Expansion Report

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.2 (Workstream B)  
**Title:** Historical Macroeconomic & Regulatory Calendar Expansion (2024–2026)  
**Status:** Completed & Provenance Verified  
**Governing Rules:** S-05, S-08, ADR-020, ADR-024, ADR-025  

---

## 1. Executive Summary & Objective

In Milestone 4.6.2, Source C (Macroeconomic Calendar) was introduced with 26 canonical events. However, an independent audit (Milestone 4.6.2.1) revealed:
- Events were clustered primarily in early 2024 (e.g. Spot BTC ETF approvals) and late 2026.
- The entire year 2025 and mid-2024 to early-2026 lacked regular Federal Reserve FOMC rate decisions, Bureau of Labor Statistics (BLS) Consumer Price Index (CPI) releases, and Non-Farm Payrolls (NFP) reports.
- Observation timestamps (`first_observed_at`, `collected_at`, `revision_observed_at`) were missing from the SQLite schema.

Workstream B executed Migration 007 and expanded the canonical macroeconomic registry across all 35 calendar months.

---

## 2. Schema Evolution (Migration 007)

Applied migration `backend/app/database/migrations/007_macro_provenance_schema.sql` to add provenance tracking columns to `news_macro_events`:
- `first_observed_at TEXT`: Timestamp when the scheduled event was first registered into the research system.
- `collected_at TEXT`: Verification crawl timestamp.
- `revision_observed_at TEXT`: Timestamp of any retroactive economic indicator revisions (e.g. BLS seasonal factor adjustments).

---

## 3. Macro Event Registry Expansion

The registry in `backend/app/data/news/macro_calendar.py` was expanded from 26 to **68 canonical records** spanning January 2024 through November 2026.

### 3.1 Event Categories & Provenance URLs

| Event Type | Count | Official Provenance Source | Verification Status | Precision |
|------------|-------|----------------------------|---------------------|-----------|
| **FOMC Interest Rate Decisions** | 24 | Federal Reserve Board (`federalreserve.gov`) | `POINT_IN_TIME_VERIFIED` | MINUTE (18:00 or 19:00 UTC) |
| **BLS Consumer Price Index (CPI)** | 22 | US Bureau of Labor Statistics (`bls.gov`) | `POINT_IN_TIME_VERIFIED` | MINUTE (12:30 or 13:30 UTC) |
| **BLS Non-Farm Payrolls (NFP)** | 16 | US Bureau of Labor Statistics (`bls.gov`) | `POINT_IN_TIME_VERIFIED` | MINUTE (12:30 or 13:30 UTC) |
| **Regulatory & SEC Orders** | 4 | US SEC (`sec.gov`) | `POINT_IN_TIME_VERIFIED` | SECOND / MINUTE |
| **Ethereum Protocol Milestones** | 2 | Ethereum Foundation (`ethereum.org`) | `POINT_IN_TIME_VERIFIED` | SECOND |

### 3.2 Monthly Macro Coverage (100.0%)

Every single month in the 35-month window contains at least 1 verified macroeconomic release:
- **2024:** 2024-01 (3), 2024-02 (1), 2024-03 (3), 2024-04 (2), 2024-05 (3), 2024-06 (2), 2024-07 (2), 2024-08 (2), 2024-09 (2), 2024-10 (2), 2024-11 (3), 2024-12 (2).
- **2025:** 2025-01 (2), 2025-02 (1), 2025-03 (2), 2025-04 (1), 2025-05 (3), 2025-06 (2), 2025-07 (2), 2025-08 (1), 2025-09 (2), 2025-10 (3), 2025-11 (1), 2025-12 (2).
- **2026:** 2026-01 (2), 2026-02 (1), 2026-03 (2), 2026-04 (1), 2026-05 (2), 2026-06 (2), 2026-07 (2), 2026-08 (1), 2026-09 (3), 2026-10 (1), 2026-11 (2).

---

## 4. Relevance & Trading Asset Attribution

- **Basket Relevance (`MACRO`):** FOMC, CPI, and NFP prints systematically affect macro liquidity and risk-free discount rates. They are assigned `relevance_classification = "MACRO"` and attributed to all target assets: `["BTC", "ETH", "BNB"]`.
- **Look-Ahead Prevention:** The exact scheduled release timestamp (`scheduled_at`) is identical to `actual_release_at` for scheduled releases. Any post-release revision is timestamped at `revision_observed_at`, preventing historical back-fitting.
- **Export Verification:** Parquet export to `storage/news/macro_calendar/macro_events.parquet` and machine-readable ledger `storage/exports/milestone_4_6_2_2/macro_calendar_coverage.csv` match SQLite records with 0 delta.
