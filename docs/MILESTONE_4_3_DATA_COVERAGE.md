# NEPTUNE — Milestone 4.3 Historical Market Data Coverage

- **Document Version**: 1.0.0
- **Ingestion Date**: 2026-11-02
- **Data Source**: Binance Public REST API (Unauthenticated, Rule `S-02`, ADR-011)
- **Validation**: Strict OHLCV invariant validation & sequence gap detection (`CandleValidator`)
- **Storage**: Partitioned monthly Apache Parquet (`ParquetMarketDataRepository`)
- **Total Validated Candles Ingested**: **39,000 closed candles**

---

## 1. Historical Dataset Inventory

| Symbol | Timeframe | Stored Candles | Calendar Duration | Earliest Timestamp (UTC) | Latest Timestamp (UTC) | Storage Partitions |
| :--- | :---: | :---: | :---: | :--- | :--- | :---: |
| **BTCUSDT** | **4h** | 3,000 | 500.5 days (~1.37 years) | `2025-06-19T20:00:00.000Z` | `2026-11-01T16:00:00.000Z` | 2025/06 $\to$ 2026/11 |
| **BTCUSDT** | **1h** | 5,000 | 208.3 days (~6.9 months) | `2026-04-07T10:00:00.000Z` | `2026-11-01T17:00:00.000Z` | 2026/04 $\to$ 2026/11 |
| **BTCUSDT** | **15m** | 5,000 | 52.1 days (~1.7 months) | `2026-09-10T15:45:00.000Z` | `2026-11-01T17:30:00.000Z` | 2026/09 $\to$ 2026/11 |
| **ETHUSDT** | **4h** | 3,000 | 500.5 days (~1.37 years) | `2025-06-19T20:00:00.000Z` | `2026-11-01T16:00:00.000Z` | 2025/06 $\to$ 2026/11 |
| **ETHUSDT** | **1h** | 5,000 | 208.3 days (~6.9 months) | `2026-04-07T10:00:00.000Z` | `2026-11-01T17:00:00.000Z` | 2026/04 $\to$ 2026/11 |
| **ETHUSDT** | **15m** | 5,000 | 52.1 days (~1.7 months) | `2026-09-10T15:45:00.000Z` | `2026-11-01T17:30:00.000Z` | 2026/09 $\to$ 2026/11 |
| **BNBUSDT** | **4h** | 3,000 | 500.5 days (~1.37 years) | `2025-06-19T20:00:00.000Z` | `2026-11-01T16:00:00.000Z` | 2025/06 $\to$ 2026/11 |
| **BNBUSDT** | **1h** | 5,000 | 208.3 days (~6.9 months) | `2026-04-07T10:00:00.000Z` | `2026-11-01T17:00:00.000Z` | 2026/04 $\to$ 2026/11 |
| **BNBUSDT** | **15m** | 5,000 | 52.1 days (~1.7 months) | `2026-09-10T15:45:00.000Z` | `2026-11-01T17:30:00.000Z` | 2026/09 $\to$ 2026/11 |

---

## 2. Ingestion Pipeline & Resumability

- **Rate Limit Compliance**: Each REST request of 1,000 candles consumes 2 request weight. Binance permits 1,200 weight/minute. The entire ingestion consumed $< 80$ weight with $150\text{ms}$ pacing, causing zero HTTP 429 or 418 throttle responses.
- **Resumability**: `HistoricalDataBackfiller` queries local Parquet storage on launch (`get_earliest_candle_time`), requests only prior timestamps, and deduplicates records on disk. Subsequent runs finish in $< 0.1\text{s}$ without making network calls.
- **Validation**: 100% of stored candles conform to `high >= max(open, close)`, `low <= min(open, close)`, positive volume, and strictly closed bars (Rule `A-09`).

