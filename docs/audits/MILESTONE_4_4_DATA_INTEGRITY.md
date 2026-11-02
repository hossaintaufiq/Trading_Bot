# NEPTUNE — Milestone 4.4: Historical Data Integrity & Provenance Audit

## 1. Overview & Verification Standards

To guarantee research integrity and look-ahead prevention (Rules `S-05`, `S-06`, `A-02`, `A-09`), every candle ingested into NEPTUNE's expanded dataset `v2.0.0` was subjected to rigorous individual and sequential validation before persistence into partitioned Apache Parquet storage.

All datasets are cryptographically fingerprinted using SHA256 and tracked transactionally in SQLite table `historical_datasets`.

---

## 2. Invariant Validation Rules

Every raw kline batch fetched from Binance public REST was validated by `CandleValidator`:

1. **Closed-Candle Enforcement (Rule A-09)**:
   - Incomplete or active bars are strictly rejected (`is_closed == True` required).
2. **UTC ISO 8601 Normalization (Rule A-02, ADR-012)**:
   - All epoch millisecond timestamps are converted to UTC strings formatted as `YYYY-MM-DDTHH:MM:SS.000Z`.
3. **Mathematical OHLC Invariants**:
   - $\text{High} \ge \text{Low} > 0$
   - $\text{High} \ge \max(\text{Open}, \text{Close})$
   - $\text{Low} \le \min(\text{Open}, \text{Close})$
   - $\text{Volume} \ge 0$
4. **Sequence Continuity**:
   - Timestamps must be strictly monotonically increasing: $t_{i} > t_{i-1}$.
   - Exact duplicates are dropped during merging.
   - Gaps exceeding 1 timeframe interval ($\Delta t > \Delta t_{\text{expected}}$) trigger warning logs and gap telemetry counters.

---

## 3. Data Integrity & Validation Audit Table (Dataset `v2.0.0`)

*Retrieved: 2026-11-02 via Binance Public REST v3. Target Window: 2024-01-01T00:00:00Z to 2026-11-01T23:59:59Z.*

| Dataset ID | Symbol | Timeframe | Candle Count | Missing Intervals | Duplicate Count | Invalid OHLC | Validation Status | SHA256 Fingerprint |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `neptune-v2.0.0-btcusdt-1d` | BTCUSDT | 1d | 1,036 | 0 | 0 | 0 | **VALIDATED** | `52b0e3e2189d...ac8904bf` |
| `neptune-v2.0.0-ethusdt-1d` | ETHUSDT | 1d | 1,036 | 0 | 0 | 0 | **VALIDATED** | `7891dbe09e9f...0f8ffdd2` |
| `neptune-v2.0.0-bnbusdt-1d` | BNBUSDT | 1d | 1,036 | 0 | 0 | 0 | **VALIDATED** | `9b81ee50016f...b7a1d080` |
| `neptune-v2.0.0-btcusdt-4h` | BTCUSDT | 4h | 6,216 | 0 | 0 | 0 | **VALIDATED** | `35b3c6c6af82...ce81a726` |
| `neptune-v2.0.0-ethusdt-4h` | ETHUSDT | 4h | 6,216 | 0 | 0 | 0 | **VALIDATED** | `f3c1e5f1246e...09c5a631` |
| `neptune-v2.0.0-bnbusdt-4h` | BNBUSDT | 4h | 6,216 | 0 | 0 | 0 | **VALIDATED** | `51efc8eb2dac...94ac2b7a` |
| `neptune-v2.0.0-btcusdt-1h` | BTCUSDT | 1h | 24,864 | 0 | 0 | 0 | **VALIDATED** | `687a7109b8be...ef0c8094` |
| `neptune-v2.0.0-ethusdt-1h` | ETHUSDT | 1h | 24,864 | 0 | 0 | 0 | **VALIDATED** | `5153479d5d27...0b00e1a2` |
| `neptune-v2.0.0-bnbusdt-1h` | BNBUSDT | 1h | 24,864 | 0 | 0 | 0 | **VALIDATED** | `e5885c543fb4...cb7938` |
| `neptune-v2.0.0-btcusdt-15m`| BTCUSDT | 15m | 99,456 | 0 | 0 | 0 | **VALIDATED** | `4f69b8335ae9...1a8fe56` |
| `neptune-v2.0.0-ethusdt-15m`| ETHUSDT | 15m | 99,456 | 0 | 0 | 0 | **VALIDATED** | `21f760f80adf...119f085` |
| `neptune-v2.0.0-bnbusdt-15m`| BNBUSDT | 15m | 99,456 | 0 | 0 | 0 | **VALIDATED** | `219e20e04dc3...058c5f` |
| **Combined v2.0.0** | **Total** | — | **394,716** | **0** | **0** | **0** | **100% VALIDATED** | — |

---

## 4. Dataset Versioning & Storage Isolation

To prevent silent data corruption or loss of provenance, historical data is partitioned by immutable version identifiers:

1. **Dataset `v1.0.0` (Historical Reference Baseline)**:
   - Stored in `storage/datasets/v1.0.0/{symbol}/{timeframe}/YYYY/MM/YYYY-MM.parquet`.
   - Preserves the exact 87 Parquet files used across Milestones 4.1 through 4.3.4.
   - Combined SHA256: `11c41f00b3fc6c452718021c6167466ae0535eaf520c20c108b72839bea4fdb0`.
2. **Dataset `v2.0.0` (Expanded Research Baseline)**:
   - Stored in `storage/datasets/v2.0.0/{symbol}/{timeframe}/YYYY/MM/YYYY-MM.parquet` (and mirrored to `storage/historical/`).
   - Contains 420 monthly partition files with canonical 8-column schemas.
   - Fully documented in `storage/exports/milestone_4_4/dataset_manifest.json`.

---

## 5. SQLite Provenance Tracking

Per ADR-020, every dataset operation is logged in the `historical_datasets` table in `storage/db/neptune.db`:

```sql
CREATE TABLE historical_datasets (
    dataset_id TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    candle_count INTEGER NOT NULL,
    missing_intervals_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    invalid_candle_count INTEGER NOT NULL,
    source TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    sha256_fingerprint TEXT NOT NULL,
    retrieval_timestamp TEXT NOT NULL,
    storage_path TEXT NOT NULL
);
```

Automated unit tests in `backend/tests/unit/test_milestone_4_4_research_foundation.py` guarantee that queries against `v1.0.0` and `v2.0.0` return stable, isolated records.

