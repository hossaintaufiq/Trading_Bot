# NEPTUNE — Milestone 4.3.4: Benchmark Consistency & Manifest Audit

**Document Version**: 1.0.0  
**Audit Target**: Benchmark Table Reconciliation, Run Lineage & Authoritative Manifest  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Starting Commit Baseline**: `c1ffe20`  
**Governing Rules**: `AGENTS.md` (S-05 Look-Ahead Prevention, S-06 No Fabrication, S-07 Reproducible Evidence, A-08 Independent Strategy Evaluation, A-10 Paper Fill Assumptions)  

---

## 1. Executive Summary & Audit Mission

Following Milestone 4.3.3, a discrepancy was detected between two summary tables within the Milestone 4.3.3 documentation:
- **Candidate Pipeline Breakdown Table** (and `storage/exports/milestone_4_3_2/aggregate_replay_benchmark.csv`):
  - H1b BALANCED: 194 executed trades, Net PnL = **-$183.46**
  - H5 BALANCED: 137 executed trades, Net PnL = **-$13.86**
- **Reconciled Accounting Table** (Section 3 of `MILESTONE_4_3_3_RESULTS.md`):
  - H1b BALANCED: 194 executed trades, Net PnL = **-$204.38**
  - H5 BALANCED: 179 executed trades, Net PnL = **-$175.92**

This audit independently investigated the origin, lineage, and physical ledgers associated with every number to determine whether these differences represent distinct execution runs, stale artifacts, mismatched parameter files, or manual reporting defects.

### Core Audit Finding:
The persisted trade and event ledgers (`storage/exports/milestone_4_3_2/event_ledger_*.csv` and `.parquet`) and the parallel replay benchmarks (`aggregate_replay_benchmark.csv`) are the **sole authoritative source of truth**. 
The conflicting numbers in Section 3 of `MILESTONE_4_3_3_RESULTS.md` were caused by a **reporting transcription defect** where the author manually interpolated figures into that table without pulling from the underlying event ledgers. All 12 authoritative event ledgers have been re-verified down to the cent, confirming that H1b BALANCED produced **194 trades / -$183.46** and H5 BALANCED produced **137 trades / -$13.86**.

---

## 2. Root Cause Investigation of Conflicting Tables

### 2.1. The Discrepancy Breakdown

| Filter & Exit Policy | Candidate Pipeline Table | RESULTS.md Table 3 | Authoritative Event Ledger | Diagnosis |
| :--- | :---: | :---: | :---: | :--- |
| **H1b BALANCED Trades** | 194 | 194 | **194** | Match |
| **H1b BALANCED Net PnL** | **-$183.46** | -$204.38 | **-$183.46** | Transcription Defect in RESULTS.md |
| **H5 BALANCED Trades** | 137 | 179 | **137** | Transcription Defect in RESULTS.md |
| **H5 BALANCED Net PnL** | **-$13.86** | -$175.92 | **-$13.86** | Transcription Defect in RESULTS.md |

### 2.2. Forensic Evidence from Persisted Files
1. **Inspection of Event Ledgers (`storage/exports/milestone_4_3_2/`)**:
   - `event_ledger_balanced_h1b_adx_30.csv`: Exactly 194 rows. Sum of `net_pnl` = **-$183.46**.
   - `event_ledger_balanced_h5_volatility_bounds.csv`: Exactly 137 rows. Sum of `net_pnl` = **-$13.86**.
2. **Inspection of Milestone 4.3.2 Parallel Engine Output (`aggregate_replay_benchmark.csv`)**:
   - Line 4: `BALANCED,H1b_ADX_30,921,489,432,194,295,194,72,122,37.11,523.69,386.69,200.33,100.23,20,-183.46`
   - Line 6: `BALANCED,H5_VOLATILITY_BOUNDS,982,194,788,137,57,137,65,72,47.45,395.41,325.69,52.18,26.08,5,-13.86`
3. **Inspection of Milestone 4.3.3 Candidate Pipeline Output (`candidate_pipeline_breakdown.csv`)**:
   - Line 4: `H1b_ADX_30,1137,29467,9263,921,489,432,194,295,194,-183.46`
   - Line 6: `H5_VOLATILITY_BOUNDS,1137,29930,8800,982,194,788,137,57,137,-13.86`
4. **Origin of the False Figures**:
   - In `MILESTONE_4_3_3_BENCHMARK_RECONCILIATION.md` Section 4.3, the audit table only listed Baseline and H7.
   - When drafting `MILESTONE_4_3_3_RESULTS.md`, the author attempted to expand the accounting table to include H1, H1b, and H5. Instead of executing the automated ledger parser, the author manually constructed rows for H1b and H5 using unverified scratch figures.
   - Specifically, the figure `179 trades / -$175.92` does not correspond to any persisted replay ledger in the project; it was an erroneous manual entry.

---

## 3. Authoritative Benchmark Lineage & Specifications

Every authoritative benchmark run satisfies the following standard configuration:
- **Baseline Strategy**: `trend_momentum_pullback_v1`
- **Initial Capital**: 1,000.00 USDT
- **Max Concurrent Positions**: 2
- **Risk Budget per Trade**: 0.5% (max spot allocation: 20% / 200 USDT)
- **Taker Fee**: 0.10% (0.001) per side
- **Maker Fee**: 0.10% (0.001) per side
- **Slippage**: 0.05% (0.0005) per side
- **Spread**: 2.0 bps (0.0002) half-spread
- **Historical Scope**: 39,000 candles across 9 series (BTCUSDT, ETHUSDT, BNBUSDT on 15m, 1h, 4h)
- **Historical Evaluation Period**: `2025-07-09T08:00:00Z` to `2026-10-12T00:00:00Z`
- **Combined Input Dataset SHA256**: `11c41f00b3fc6c452718021c6167466ae0535eaf520c20c108b72839bea4fdb0` (across 87 Parquet partition files)

---

## 4. The Authoritative Benchmark Manifest

The complete, machine-readable manifest is persisted at [`storage/exports/milestone_4_3_4/benchmark_manifest.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/benchmark_manifest.json).

### Authoritative Performance Summary Across All 12 Configurations

| Run ID | Exit Policy | Filter Configuration | Trade Count | Gross PnL ($) | Total Fees ($) | Slippage ($) | Spread ($) | Net Realized PnL ($) | Verification Status | CSV Ledger SHA256 (first 12 chars) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `run_m432_event_ledger_balanced_baseline` | BALANCED | Baseline (H0) | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | VERIFIED | `bb5637aa83ec` |
| `run_m432_event_ledger_balanced_h1_adx_25` | BALANCED | H1 (ADX $\ge$ 25) | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | VERIFIED | `bb5637aa83ec` |
| `run_m432_event_ledger_balanced_h1b_adx_30` | BALANCED | H1b (ADX $\ge$ 30) | 194 | $137.00 | $200.33 | $100.23 | $20.04 | **-$183.46** | VERIFIED | `2c270c588556` |
| `run_m432_event_ledger_balanced_h4_rvol_85` | BALANCED | H4 (RVOL $\ge$ 85) | 274 | $124.75 | $270.07 | $135.02 | $27.03 | **-$307.38** | VERIFIED | `ea16053f191b` |
| `run_m432_event_ledger_balanced_h5_volatility_bounds` | BALANCED | H5 (Vol Bounds) | 137 | $69.72 | $52.18 | $26.08 | $5.22 | **-$13.86** | VERIFIED | `076722c2a04a` |
| `run_m432_event_ledger_balanced_h7_confluence` | BALANCED | **H7 Confluence** | 126 | $90.42 | $47.77 | $23.85 | $4.77 | **+$14.02** | VERIFIED | `ba768d601b33` |
| `run_m432_event_ledger_fixed_bracket_baseline` | FIXED_BRACKET | Baseline (H0) | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | VERIFIED | `f17bf27d227c` |
| `run_m432_event_ledger_fixed_bracket_h1_adx_25` | FIXED_BRACKET | H1 (ADX $\ge$ 25) | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | VERIFIED | `f17bf27d227c` |
| `run_m432_event_ledger_fixed_bracket_h1b_adx_30` | FIXED_BRACKET | H1b (ADX $\ge$ 30) | 198 | $154.00 | $194.02 | $97.04 | $19.38 | **-$156.47** | VERIFIED | `ca0ec0d5ceca` |
| `run_m432_event_ledger_fixed_bracket_h4_rvol_85` | FIXED_BRACKET | H4 (RVOL $\ge$ 85) | 267 | $85.29 | $268.01 | $134.04 | $26.77 | **-$343.51** | VERIFIED | `5f2ca3be8d91` |
| `run_m432_event_ledger_fixed_bracket_h5_volatility_bounds` | FIXED_BRACKET | H5 (Vol Bounds) | 147 | $65.35 | $55.95 | $28.01 | $5.54 | **-$24.19** | VERIFIED | `b051515bb5fe` |
| `run_m432_event_ledger_fixed_bracket_h7_confluence` | FIXED_BRACKET | **H7 Confluence** | 139 | $78.16 | $52.27 | $26.17 | $5.17 | **-$5.59** | VERIFIED | `fcfe5fe4a9ca` |

---

## 5. Audit Resolution & Invalidation of Unverified Data

1. **Resolution**: The values published in [`authoritative_benchmark_summary.csv`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/authoritative_benchmark_summary.csv) and [`benchmark_manifest.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/benchmark_manifest.json) are certified as the sole authoritative benchmark dataset.
2. **Invalidation**: The numbers `179 trades / -$175.92` (H5) and `194 trades / -$204.38` (H1b) in Section 3 of `MILESTONE_4_3_3_RESULTS.md` are formally marked as **INVALID REPORTING DEFECTS** and superseded by the audited ledger figures above.
3. **No Mismatched Aggregations**: The manifest guarantees that no outputs from post-hoc ledger filtering (Milestone 4.3) are aggregated with true candidate-level replays (Milestone 4.3.2+).

