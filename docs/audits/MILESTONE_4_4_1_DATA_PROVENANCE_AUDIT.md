# NEPTUNE Milestone 4.4.1 — Data Provenance & Ingestion Integrity Audit

**Audit Date:** 2026-11-02  
**Baseline Commit:** `ae908d1` / `4f59a94`  
**Dataset Version:** `v2.0.0`  
**Audit Scope:** Independent forensic audit of dataset size, file partitions, bar counts, timestamp continuity, network provenance, and cryptographic fingerprint integrity.

---

## 1. Executive Summary & Verdict

An exhaustive, adversarial verification was conducted directly against disk storage (`storage/datasets/v2.0.0/` and `storage/historical/`), the SQLite database (`storage/db/neptune.db`), and public Binance REST endpoints.

* **Audit Verdict:** **PASS WITH ADVERSARIAL LIMITATIONS NOTED**
* **Total Parquet Files:** Exactly **420 monthly partition files** in `storage/datasets/v2.0.0/` and **420 identical files** in active `storage/historical/` (0 byte mismatches).
* **Total Closed Candles:** Exactly **394,716 validated candles** spanning **2024-01-01T00:00:00.000Z to 2026-11-01T23:59:59.000Z** (34 contiguous months).
* **Data Quality:** **0 sequence gaps, 0 duplicate timestamps, 0 malformed OHLC records, and 0 partial/unclosed candles**.
* **Critical Finding (Hash Reconciliation):** The aggregate dataset hash `a937a06f4f2f4d6d67cfce4ce16e78b7bdf0814fa513e9a4058b8d4cf72d4b29` quoted in the Milestone 4.4 final report was an ungrounded string placeholder. The true cryptographic directory tree hash of `storage/datasets/v2.0.0/` is `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`. However, all 12 series fingerprints registered in SQLite `historical_datasets` are 100% authentic and verified.

---

## 2. Parquet File Matrix & Candle Inventory

Dataset `v2.0.0` expands historical depth to 34 contiguous months across three Tier-1 spot pairs and four operational/macro timeframes.

| Symbol | Timeframe | Monthly Files | Total Bars | Earliest UTC Candle | Latest UTC Candle | Dups | Gaps | Invalid OHLC | SQLite Validation |
|---|---|---:|---:|---|---|---:|---:|---:|---|
| **BTCUSDT** | `15m` | 35 | 99,456 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:45:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BTCUSDT** | `1h` | 35 | 24,864 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BTCUSDT** | `4h` | 35 | 6,216 | 2024-01-01T00:00:00.000Z | 2026-11-01T20:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BTCUSDT** | `1d` | 35 | 1,036 | 2024-01-01T00:00:00.000Z | 2026-11-01T00:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **ETHUSDT** | `15m` | 35 | 99,456 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:45:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **ETHUSDT** | `1h` | 35 | 24,864 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **ETHUSDT** | `4h` | 35 | 6,216 | 2024-01-01T00:00:00.000Z | 2026-11-01T20:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **ETHUSDT** | `1d` | 35 | 1,036 | 2024-01-01T00:00:00.000Z | 2026-11-01T00:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BNBUSDT** | `15m` | 35 | 99,456 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:45:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BNBUSDT** | `1h` | 35 | 24,864 | 2024-01-01T00:00:00.000Z | 2026-11-01T23:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BNBUSDT** | `4h` | 35 | 6,216 | 2024-01-01T00:00:00.000Z | 2026-11-01T20:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **BNBUSDT** | `1d` | 35 | 1,036 | 2024-01-01T00:00:00.000Z | 2026-11-01T00:00:00.000Z | 0 | 0 | 0 | `VALIDATED` |
| **TOTAL** | — | **420** | **394,716** | — | — | **0** | **0** | **0** | **12 / 12 VALIDATED** |

---

## 3. Investigation of Ingestion Provenance & Network Reachability

### Forensic Background
The audit inquiry requested clarification regarding initial failed reachability tests and confirmation that data was genuinely sourced from Binance.

### Forensic Findings
1. **The Initial "Reachability" Failure:**
   - Log inspection revealed that the initial execution of `scratch/test_reach.py` failed with:
     ```
     ModuleNotFoundError: No module named 'app'
     ```
   - This was an import resolution defect in the standalone scratch script, not an exchange network block, DNS error, or HTTP 429/403 block.
   - Once `sys.path.insert(0, "backend")` was added, `scratch/test_reach.py` connected immediately to `https://api.binance.com/api/v3/klines` and retrieved 5 live candles.

2. **Ingestion Process:**
   - Ingestion was orchestrated by `scratch/download_expanded_history.py` using `HistoricalDataBackfiller` ([`backfill.py`](file:///d:/Project%202026/Trading_bot/backend/app/data/market/backfill.py)).
   - Forward pagination from `2024-01-01T00:00:00Z` to `2026-11-01T23:59:59Z` was executed in 1,000-candle batches via `BinancePublicClient` using `httpx.AsyncClient` with a strict rate-limit delay of `0.08s` per request.
   - Over 400 REST requests were dispatched; **0 requests encountered HTTP 429 (rate limit) or HTTP 418 (IP ban)**.
   - Every returned kline was passed through `CandleValidator` ([`validator.py`](file:///d:/Project%202026/Trading_bot/backend/app/data/market/validator.py)) requiring `is_closed=True`.
   - Data was written to monthly Parquet partitions using `pyarrow` under `storage/datasets/v2.0.0/` and mirrored to `storage/historical/`.

---

## 4. SQLite Provenance & Cryptographic Fingerprints

All 12 dataset segments are recorded in the SQLite database ([`storage/db/neptune.db`](file:///d:/Project%202026/Trading_bot/storage/db/neptune.db)) under table `historical_datasets`:

| Dataset ID | Timeframe | Candle Count | SHA256 Data Fingerprint |
|---|---|---:|---|
| `neptune-v2.0.0-btcusdt-15m` | `15m` | 99,456 | `4f69b8335ae963bc4cec816fcb5db78500f33c0e61352308420b9af8d1a8fe56` |
| `neptune-v2.0.0-btcusdt-1h` | `1h` | 24,864 | `687a7109b8be5e072f27be45ce6d7b367f9385f65fa064b231c3163def0c8094` |
| `neptune-v2.0.0-btcusdt-4h` | `4h` | 6,216 | `35b3c6c6af82457ef8525fa19d93eef4f0dbce9e79e9fef8c6e3569fce81a726` |
| `neptune-v2.0.0-btcusdt-1d` | `1d` | 1,036 | `52b0e3e2189daeb94ac9e61b511e6c1c2e8c41586967a12492bf3959ac8904bf` |
| `neptune-v2.0.0-ethusdt-15m` | `15m` | 99,456 | `21f760f80adffdc89779f57ee2f8487d48d65f5628d179e6541fd881a119f085` |
| `neptune-v2.0.0-ethusdt-1h` | `1h` | 24,864 | `5153479d5d279a2c747d48726b9f68588e42a896f2e2de07486e3e8b0b00e1a2` |
| `neptune-v2.0.0-ethusdt-4h` | `4h` | 6,216 | `f3c1e5f1246e98f05533424345ff27f4429a69cb8068a26a473930ae09c5a631` |
| `neptune-v2.0.0-ethusdt-1d` | `1d` | 1,036 | `7891dbe09e9f8c3f24c605f4a33ea2d67f47725bb54473aa71ca1e730f8ffdd2` |
| `neptune-v2.0.0-bnbusdt-15m` | `15m` | 99,456 | `219e20e04dc365b4baf9c8ddb1a7f34c088469b5c6eb936cb2cd7066cb058c5f` |
| `neptune-v2.0.0-bnbusdt-1h` | `1h` | 24,864 | `e5885c543fb4535b1f53504dc3d5252026a22e06b5b651a547a5613c9ecb7938` |
| `neptune-v2.0.0-bnbusdt-4h` | `4h` | 6,216 | `51efc8eb2dac095fb3c0059ab5a7b8ea249d397fd6f3e416a1685ede94ac2b7a` |
| `neptune-v2.0.0-bnbusdt-1d` | `1d` | 1,036 | `9b81ee50016f78041fdd6114d617b7440a77c03873080ce374ae9deab7a1d080` |

### Forensic Verification of Reported vs Actual Dataset Hash
* **Reported in Milestone 4.4 Summary:** `a937a06f4f2f4d6d67cfce4ce16e78b7bdf0814fa513e9a4058b8d4cf72d4b29`
* **Audit Determination:** This hash was an ungrounded string placeholder generated during report synthesis.
* **Actual Cryptographic Tree Hash:**
  Hashing all 420 relative file paths and individual SHA256 checksums yields:
  ```
  b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c
  ```
* **Actual Fingerprint Aggregate Hash:**
  Hashing the concatenated SQLite fingerprints yields:
  ```
  997441a3205d6b3cfd05d8e742d5a372fce7e00d08983fc0b173f2143a686a3f
  ```
The discrepancy is transparently documented in the authoritative run manifest.

---

## 5. Storage Immutability & Parity Check

To guarantee immutability:
1. `storage/datasets/v2.0.0/` serves as the cold, frozen archive.
2. `storage/historical/` serves as the active working copy.
3. An SHA256 check across all 420 files between `storage/datasets/v2.0.0/` and `storage/historical/` confirmed **0 mismatches**.
4. Both repositories are bit-for-bit identical.

