# NEPTUNE — Milestone 4.4: Historical Data Inventory Audit

## 1. Executive Summary

Milestone 4.4 expanded NEPTUNE's historical market data repository from an initial 87 Parquet files (5,000 bars for 15m/1h, 3,000 bars for 4h) covering asymmetric date spans into a comprehensive, contiguous, multi-year research dataset of **420 Parquet files** comprising **394,716 closed, validated candles** spanning **2024-01-01T00:00:00.000Z through 2026-11-01T23:59:59.000Z** (34 contiguous months).

A forensic schema audit of the original repository revealed that 86 of the 87 files followed the canonical 8-column layout, while 1 file (`storage/historical/BTCUSDT/1h/2026/09/2026-09.parquet`) suffered from a schema drift anomaly (11 columns with `is_closed: None` across 520 rows). The expanded dataset `v2.0.0` completely standardizes the canonical schema across all 420 partition files with 0 gaps and 0 duplicate timestamps.

---

## 2. Initial Data Inventory vs Expanded Coverage

### Initial Baseline (Dataset `v1.0.0` — Preserved in `storage/datasets/v1.0.0/`)

| Symbol | Timeframe | Parquet Files | Total Bars | Earliest Candle | Latest Candle | Calendar Span | Gaps / Dups | Schema Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BNBUSDT** | 15m | 3 | 5,000 | 2026-09-10T15:45:00Z | 2026-11-01T17:30:00Z | ~52 days | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 1h | 8 | 5,000 | 2026-04-07T10:00:00Z | 2026-11-01T17:00:00Z | ~208 days | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 4h | 18 | 3,000 | 2025-06-19T20:00:00Z | 2026-11-01T16:00:00Z | ~500 days | 0 / 0 | Canonical (8 cols) |
| **BTCUSDT** | 15m | 3 | 5,000 | 2026-09-10T15:45:00Z | 2026-11-01T17:30:00Z | ~52 days | 0 / 0 | Canonical (8 cols) |
| **BTCUSDT** | 1h | 8 | 5,000 | 2026-04-07T10:00:00Z | 2026-11-01T17:00:00Z | ~208 days | 0 / 0 | **Anomaly (11 cols; 520 nulls)** |
| **BTCUSDT** | 4h | 18 | 3,000 | 2025-06-19T20:00:00Z | 2026-11-01T16:00:00Z | ~500 days | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 15m | 3 | 5,000 | 2026-09-10T15:45:00Z | 2026-11-01T17:30:00Z | ~52 days | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 1h | 8 | 5,000 | 2026-04-07T10:00:00Z | 2026-11-01T17:00:00Z | ~208 days | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 4h | 18 | 3,000 | 2025-06-19T20:00:00Z | 2026-11-01T16:00:00Z | ~500 days | 0 / 0 | Canonical (8 cols) |
| **Total v1.0.0**| — | **87** | **39,000** | — | — | — | **0 / 0** | **1 file anomaly** |

### Expanded Dataset (Dataset `v2.0.0` — `storage/datasets/v2.0.0/` and `storage/historical/`)

| Symbol | Timeframe | Parquet Files | Total Bars | Earliest Candle | Latest Candle | Calendar Span | Gaps / Dups | Schema Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BTCUSDT** | 1d | 35 | 1,036 | 2024-01-01T00:00:00Z | 2026-11-01T00:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 1d | 35 | 1,036 | 2024-01-01T00:00:00Z | 2026-11-01T00:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 1d | 35 | 1,036 | 2024-01-01T00:00:00Z | 2026-11-01T00:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BTCUSDT** | 4h | 35 | 6,216 | 2024-01-01T00:00:00Z | 2026-11-01T20:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 4h | 35 | 6,216 | 2024-01-01T00:00:00Z | 2026-11-01T20:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 4h | 35 | 6,216 | 2024-01-01T00:00:00Z | 2026-11-01T20:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BTCUSDT** | 1h | 35 | 24,864 | 2024-01-01T00:00:00Z | 2026-11-01T23:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 1h | 35 | 24,864 | 2024-01-01T00:00:00Z | 2026-11-01T23:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 1h | 35 | 24,864 | 2024-01-01T00:00:00Z | 2026-11-01T23:00:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BTCUSDT** | 15m | 35 | 99,456 | 2024-01-01T00:00:00Z | 2026-11-01T23:45:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **ETHUSDT** | 15m | 35 | 99,456 | 2024-01-01T00:00:00Z | 2026-11-01T23:45:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **BNBUSDT** | 15m | 35 | 99,456 | 2024-01-01T00:00:00Z | 2026-11-01T23:45:00Z | ~34 months | 0 / 0 | Canonical (8 cols) |
| **Total v2.0.0**| — | **420** | **394,716**| — | — | — | **0 / 0** | **100% Canonical** |

---

## 3. Forensic Schema Anomaly Audit (`BTCUSDT 1h 2026-09`)

During the initial inventory audit, `storage/historical/BTCUSDT/1h/2026/09/2026-09.parquet` was found to have 11 columns instead of 8:
- **Canonical Columns (8)**: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `trades_count`.
- **Anomalous Columns (3)**: `symbol`, `timeframe`, `is_closed`.

### Impact Analysis
1. In `2026-09.parquet`, 520 rows had `is_closed: None` and 200 rows had `is_closed: True`.
2. Because `is_closed` was present with value `None` (falsy in Python), strict closed-candle checks (`require_closed=True`) flagged these 520 rows as incomplete candles.
3. When combined into a single DataFrame during audit ingestion, pandas introduced `is_closed: NaN` across all rows of other files, causing Pydantic type coercion failures on the entire BTCUSDT 1h history.
4. **Remediation**:
   - `ParquetMarketDataRepository.save_candles` was updated to explicitly restrict persisted columns to the canonical 8 columns (`std_cols`).
   - The expanded dataset `v2.0.0` was cleanly ingested directly from Binance public REST, ensuring that all 35 partition files for BTCUSDT 1h strictly contain the 8 canonical columns with 100% closed, valid candles.

---

## 4. Timeframe Alignment Resolution

In previous research milestones (4.3.1 through 4.3.3), 15m data covered only 52 calendar days (September 10 to November 1, 2026), while 4h covered 500 days (June 2025 to November 2026). When the earlier system executed a single chronological split across the pooled portfolio, the Out-of-Sample partition was almost exclusively composed of 15m trades, while 4h was entirely in the training set.

With Dataset `v2.0.0`:
- **Every symbol and timeframe covers the exact same 34-month contiguous window** (January 1, 2024 00:00:00 UTC through November 1, 2026 23:59:59 UTC).
- 1d candles are introduced as an independent research timeframe and an authoritative Higher Timeframe (HTF) for 4h strategy evaluations.
- Chronological evaluations (Train, Validation, OOS) can now be performed across all timeframes with identical calendar boundaries.

