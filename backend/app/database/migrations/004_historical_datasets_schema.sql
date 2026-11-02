-- Migration 004 — Historical Datasets Schema
-- Date: 2026-11-02
-- Description: Create historical_datasets table for tracking expanded market data versions, fingerprints, and validation status

CREATE TABLE IF NOT EXISTS historical_datasets (
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

CREATE INDEX IF NOT EXISTS idx_historical_datasets_sym_tf
    ON historical_datasets (symbol, timeframe, dataset_version);

