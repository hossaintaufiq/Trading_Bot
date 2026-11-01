-- Migration 002 — Backtest Runs Schema
-- Date: 2026-11-01
-- Description: Create backtest_runs table for persisting backtest metadata and summaries

CREATE TABLE IF NOT EXISTS backtest_runs (
    backtest_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    final_capital REAL NOT NULL,
    net_profit REAL NOT NULL,
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    profit_factor REAL NOT NULL,
    sharpe_ratio REAL NOT NULL,
    max_drawdown_pct REAL NOT NULL,
    expectancy_per_trade REAL NOT NULL,
    config_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    parquet_trades_path TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
    ON backtest_runs (strategy_id, created_at DESC);
