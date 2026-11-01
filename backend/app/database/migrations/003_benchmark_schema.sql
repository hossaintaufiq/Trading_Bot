-- Migration 003 — Benchmark Runs Schema
-- Date: 2026-11-01
-- Description: Create benchmark_runs and benchmark_comparisons tables for exit policy evaluation

CREATE TABLE IF NOT EXISTS benchmark_runs (
    benchmark_id TEXT PRIMARY KEY,
    git_commit TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    timeframes_json TEXT NOT NULL,
    train_ratio REAL NOT NULL,
    dataset_start TEXT,
    dataset_end TEXT,
    config_json TEXT NOT NULL,
    comparison_summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_strategy
    ON benchmark_runs (strategy_id, created_at DESC);

