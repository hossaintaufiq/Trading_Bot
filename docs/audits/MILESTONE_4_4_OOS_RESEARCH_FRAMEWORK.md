# NEPTUNE — Milestone 4.4: Robust Chronological & Out-of-Sample Research Framework

## 1. Executive Summary

Milestone 4.4 completely redesigns NEPTUNE's quantitative evaluation harness to eliminate the **timeframe-imbalance defect** identified in earlier milestones.

In previous milestones, historical data coverage was severely asymmetrical:
- 15m covered ~52 calendar days (Sept 10 to Nov 1, 2026).
- 1h covered ~208 calendar days (Apr 7 to Nov 1, 2026).
- 4h covered ~500 calendar days (Jun 19, 2025 to Nov 1, 2026).

When earlier research executed a single pooled chronological split across the entire portfolio, the Out-of-Sample window contained exclusively 15m trades, while the Training window contained exclusively 4h trades. A 15m out-of-sample test cannot validate 1h or 4h strategy dynamics.

The new research framework enforces **timeframe-independent evaluation**, **strict chronological boundaries**, **clean pre-partition indicator warmup without look-ahead leakage**, and **expanding walk-forward cross-validation**.

---

## 2. Standardized Chronological Partitions

With Dataset `v2.0.0` providing contiguous history from 2024-01-01 through 2026-11-01 across all symbols and timeframes, the canonical partition windows are defined as follows:

```
2024-01-01                                     2025-06-30   2025-12-31           2026-07-31   2026-11-01
├───────────────────────────────────────────────┼───────────┼────────────────────┼───────────┤
│                     TRAIN                     │VALIDATION │ OOS_HISTORICAL_REF │OOS_PRISTINE│
│                  (18 Months)                  │ (6 Months)│     (7 Months)     │ (3 Months)│
├───────────────────────────────────────────────┴───────────┼────────────────────┴───────────┤
│                  IN-SAMPLE EXPLORATION                    │     OUT-OF-SAMPLE VERIFICATION  │
```

### Partition Definitions (Stored in `storage/exports/milestone_4_4/partition_manifest.json`)

| Partition Name | Start Timestamp (UTC) | End Timestamp (UTC) | Calendar Span | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| **TRAIN** | `2024-01-01T00:00:00.000Z` | `2025-06-30T23:59:59.000Z` | 18 Months | Primary hypothesis discovery and baseline parameter calibration. |
| **VALIDATION** | `2025-07-01T00:00:00.000Z` | `2025-12-31T23:59:59.000Z` | 6 Months | Intermediate filter tuning and regime resilience verification. |
| **OOS_HISTORICAL_REF** | `2026-01-01T00:00:00.000Z` | `2026-07-31T23:59:59.000Z` | 7 Months | Direct benchmark alignment against Milestone 4.3.4 results. |
| **OOS_PRISTINE** | `2026-08-01T00:00:00.000Z` | `2026-11-01T23:59:59.000Z` | 3 Months | Completely blind out-of-sample data never inspected in prior audits. |
| **OOS_FULL** | `2026-01-01T00:00:00.000Z` | `2026-11-01T23:59:59.000Z` | 10 Months | Combined 2026 out-of-sample evaluation window. |
| **FULL** | `2024-01-01T00:00:00.000Z` | `2026-11-01T23:59:59.000Z` | 34 Months | Complete multi-year contiguous historical horizon. |

---

## 3. Methodological Safeguards

### A. Pre-Partition Warmup Priming (Zero Look-Ahead)
- Technical indicators (EMA 200, ATR 14, ADX 14, Bollinger Bands) require historical bars to stabilize.
- Slicing data strictly at partition start causes indicator distortion during early bars.
- `ChronologicalResearchFramework.slice_candles_for_partition` prepends 100 closed bars *strictly preceding* the partition start timestamp ($t < t_{\text{start}}$).
- The backtesting engine consumes these warmup bars for indicator initialization but **strictly discards any signals or fills generated before $t_{\text{start}}$**.

### B. Partition Boundary Enforcement (No Cross-Partition Bleed)
- Trades initiated within a partition must conclude within that partition or be attributed strictly to the originating partition.
- Post-simulation filtering ensures that `start_ts <= entry_timestamp <= end_ts`.
- Out-of-sample performance cannot be artificially inflated by carrying open winning positions across partition boundaries.

### C. Timeframe Independence
- Every timeframe (15m, 1h, 4h, 1d) and asset (BTC, ETH, BNB) is evaluated in complete isolation before any portfolio pooling is considered.
- A profitable 15m result can never be claimed as validation for 1h or 4h.
- Zero-trade windows are explicitly recorded as `INSUFFICIENT_EVIDENCE`, never counted as positive performance.

---

## 4. Expanding Walk-Forward Evaluation Architecture

To measure parameter stability across changing macro regimes, the framework implements a 4-fold expanding walk-forward runner:

| Fold | Training Window (In-Sample) | Testing Window (Out-of-Sample) | In-Sample Span | Out-of-Sample Span |
| :---: | :--- | :--- | :---: | :---: |
| **Fold 1** | `2024-01-01` to `2024-12-31` | `2025-01-01` to `2025-06-30` | 12 Months | 6 Months (2025-H1) |
| **Fold 2** | `2024-01-01` to `2025-06-30` | `2025-07-01` to `2025-12-31` | 18 Months | 6 Months (2025-H2) |
| **Fold 3** | `2024-01-01` to `2025-12-31` | `2026-01-01` to `2026-06-30` | 24 Months | 6 Months (2026-H1) |
| **Fold 4** | `2024-01-01` to `2026-06-30` | `2026-07-01` to `2026-11-01` | 30 Months | 4 Months (2026-H2) |

Results are exported to `storage/exports/milestone_4_4/walk_forward_results.csv`.

