# NEPTUNE — Milestone 4.6.2.1: Point-in-Time Integrity Audit

**Document:** Point-in-Time Temporal Architecture & Look-Ahead Prevention Audit  
**Milestone:** 4.6.2.1 (Forensic Data Audit)  
**Evaluator:** Independent Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — 439 VERIFIED / 66 PARTIAL (LOOK-AHEAD PREVENTED)  

---

## 1. Executive Summary

This audit independently verifies the temporal provenance, timestamp precision, and point-in-time (PIT) suitability of the 505 records in NEPTUNE's news database.

To guarantee compliance with Persistent Engineering Rule **S-05** (*"Never use future data in simulations or backtests. Strict look-ahead bias prevention"*), each record was evaluated across 7 distinct temporal coordinates.

### Key Audit Findings:
- **`POINT_IN_TIME_VERIFIED` Records:** Exactly **439 records** ($86.9\%$).
  - Comprises 413 Binance announcements and 26 Macro Calendar records.
  - All 439 records possess an explicit, verified primary release timestamp (`published_at` or `scheduled_at`) with millisecond or second precision.
  - Fully eligible for strict candle-close synchronization ($t_{\text{event}} \le t_{\text{candle\_close}}$).
- **`PARTIALLY_VERIFIED` Records:** Exactly **66 records** ($13.1\%$).
  - All 66 records originate from GDELT 2.0 Global Knowledge Graph.
  - Crucial Discovery: For all 66 GDELT records, `published_at` is `NULL`. GDELT provides only `provider_seen_at` (the 15-minute crawler indexing timestamp).
  - **Audit Mandate:** All 66 GDELT records **must be strictly excluded from intraday candle backtests** (1m, 5m, 15m, 1h). They may only be evaluated in daily regime models where execution occurs at $T+1$ day.
- **`UNVERIFIED` Records:** Exactly **0 records** ($0.0\%$).

---

## 2. Evaluation of Seven Temporal Coordinates

The system records 7 separate timestamps per ingested entity to establish full forensic auditability:

```
[Primary Event / Publication]  published_at
       │
       ▼
[Provider Crawling / Indexing] provider_seen_at
       │
       ▼
[Archive File Creation]       archive_available_at
       │
       ▼
[NEPTUNE First Ingestion]     first_seen_at
       │
       ▼
[Database Persistence]        collected_at
       │
       ▼
[Version / Revision Check]    revision_observed_at
       │
       ▼
[Parquet Research Freeze]     research_available_at
```

### Forensic Analysis per Coordinate:

| Coordinate | Binance Announcements (413) | GDELT 2.0 Articles (66) | Macro Calendar (26) | Forensic Integrity Assessment |
|:---|:---|:---|:---|:---|
| **1. `published_at`** | Populated (100%), ISO-8601 with millisecond precision (e.g. `2026-10-29T11:48:52.329Z`). | `NULL` (100%). GDELT GKG does not extract publisher article publish time. | Populated (100%), ISO-8601 with second precision (e.g. `2024-01-10T20:30:00Z`). | Binance and Macro provide rigorous publisher timestamps. GDELT lacks primary publish time. |
| **2. `provider_seen_at`** | Populated (matches `published_at`). | Populated (100%), 15-minute GDELT batch timestamp (e.g. `2024-01-10T21:00:00.000Z`). | Populated (matches `scheduled_at`). | Valid crawler/provider observation coordinate. |
| **3. `archive_available_at`**| `NULL` (Direct API query). | Populated (100%), matches GDELT 15m file availability. | `NULL` (Canonical official registry). | Accurate for archive-based sources. |
| **4. `first_seen_at`** | Populated (Ingestion execution timestamp). | Populated (Ingestion execution timestamp). | Populated (Registry insertion timestamp). | Full provenance recorded. |
| **5. `collected_at`** | Populated (matches `first_seen_at`). | Populated (matches `first_seen_at`). | Populated (matches `first_seen_at`). | Full provenance recorded. |
| **6. `revision_observed_at`**| Populated (100%). | Populated (100%). | Populated (100%). | Immutable versioning baseline established. |
| **7. `research_available_at`**| Populated (timestamp of Parquet freeze). | Populated (timestamp of Parquet freeze). | Populated (timestamp of Parquet freeze). | Prevents data snooping across research runs. |

---

## 3. Strict Candle-Close Synchronization Rule

To prevent look-ahead bias in backtests, NEPTUNE implements the **Candle-Close Synchronization Rule**:

$$\text{Eligible News Events for Candle } [T_{\text{open}}, T_{\text{close}}]: \quad \{ e \in \mathcal{E} \mid t_{\text{event}}(e) \le T_{\text{close}} \}$$

### Safety Enforcement Requirements:
1. **Never use news arriving during candle $[T_{\text{open}}, T_{\text{close}}]$ to trade at $T_{\text{open}}$:**
   - Any order generated using news timestamped at $t_{\text{event}}$ can only be executed at or after $T_{\text{close}}$ of the candle confirming the event.
2. **Intraday Synchronization vs GDELT:**
   - Because GDELT records only contain `provider_seen_at` rounded to 15-minute intervals (and articles may have been published minutes or hours prior to crawling), using GDELT in 1-minute or 5-minute candle backtests would introduce unknown look-ahead or lag bias.
   - **Enforced Policy:** GDELT records are assigned `intraday_backtest_eligible = False`.

---

## 4. Recomputed Point-in-Time Eligibility Ledger

The table below summarizes the eligibility ledger exported to `storage/exports/milestone_4_6_2_1/pit_eligibility_ledger.csv`:

| Source Class | Total Records | Timestamp Precision | PIT Verification Status | Intraday Candle Eligible | Allowed Research Modality |
|:---|:---:|:---:|:---:|:---:|:---|
| **Binance Announcements** | 413 | Millisecond ($10^{-3}$s) | `POINT_IN_TIME_VERIFIED` | **YES (413 / 413)** | Intraday candle close (1m, 5m, 15m, 1h, 4h, 1d) |
| **Macro Calendar** | 26 | Second ($10^{0}$s) | `POINT_IN_TIME_VERIFIED` | **YES (26 / 26)** | Intraday scheduled release close (1m, 5m, 15m, 1h, 4h, 1d) |
| **GDELT GKG Historical** | 66 | 15-minute batch ($900$s) | `PARTIALLY_VERIFIED` | **NO (0 / 66)** | Daily regime analysis only ($T+1$ execution) |
| **TOTAL** | **505** | — | — | **439 Eligible / 66 Excluded** | — |

---
*End of Point-in-Time Audit Report.*

