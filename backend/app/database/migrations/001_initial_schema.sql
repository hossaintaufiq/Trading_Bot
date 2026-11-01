-- Migration 001 — Initial NEPTUNE Schema
-- Date: 2026-11-01
-- Description: Create all base tables for NEPTUNE v1

-- ============================================================
-- MARKET DATA
-- ============================================================
CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_price REAL NOT NULL,
    price_change_pct_24h REAL,
    volume_24h REAL,
    high_24h REAL,
    low_24h REAL,
    regime TEXT DEFAULT 'UNKNOWN',
    spread_bps REAL,
    snapshot_at TEXT NOT NULL  -- UTC ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_time
    ON market_snapshots (symbol, snapshot_at DESC);

-- ============================================================
-- AGENT EXECUTION LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    execution_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    success INTEGER NOT NULL DEFAULT 0,  -- 0=false, 1=true
    duration_ms REAL,
    input_json TEXT,
    output_json TEXT,
    error_message TEXT,
    error_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_executions_agent_id
    ON agent_executions (agent_id, started_at DESC);

-- ============================================================
-- CENTRAL BRAIN DECISIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS brain_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    signal_id TEXT,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    agent_outputs_json TEXT,
    timestamp TEXT NOT NULL  -- UTC ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_brain_decisions_signal
    ON brain_decisions (signal_id);

-- ============================================================
-- SIGNALS
-- ============================================================
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL UNIQUE,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL,   -- LONG | SHORT
    status TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL NOT NULL,
    reward_risk_ratio REAL NOT NULL,
    signal_strength REAL NOT NULL,
    invalidation_price REAL,
    max_holding_candles INTEGER,
    generated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    explanation TEXT,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_status
    ON signals (symbol, status, generated_at DESC);

-- ============================================================
-- SIMULATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id TEXT NOT NULL UNIQUE,
    signal_id TEXT NOT NULL REFERENCES signals(signal_id),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    created_at TEXT NOT NULL,
    seed INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    method TEXT NOT NULL,
    horizon_candles INTEGER NOT NULL,
    num_paths INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    p5 REAL, p10 REAL, p25 REAL, p50 REAL, p75 REAL, p90 REAL, p95 REAL,
    stop_hit_probability REAL,
    target_hit_probability REAL,
    max_adverse_excursion_median REAL,
    assumptions_json TEXT,
    parquet_path TEXT  -- path to stored paths file
);

-- ============================================================
-- PAPER ORDERS
-- ============================================================
CREATE TABLE IF NOT EXISTS paper_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,
    signal_id TEXT REFERENCES signals(signal_id),
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    order_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    quantity REAL NOT NULL,
    limit_price REAL,
    stop_price REAL,
    target_price REAL,
    created_at TEXT NOT NULL,
    filled_at TEXT,
    fill_price REAL,
    fee_paid REAL,
    slippage_pct REAL,
    execution_assumptions_json TEXT  -- required per AGENTS.md E-06
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_status
    ON paper_orders (status, created_at DESC);

-- ============================================================
-- PAPER POSITIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id TEXT NOT NULL UNIQUE,
    signal_id TEXT REFERENCES signals(signal_id),
    order_id TEXT REFERENCES paper_orders(order_id),
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    close_reason TEXT,
    realized_pnl REAL,
    max_unrealized_pnl REAL,
    max_adverse_excursion REAL
);

CREATE INDEX IF NOT EXISTS idx_positions_status
    ON positions (status, opened_at DESC);

-- ============================================================
-- RISK EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,  -- DAILY_LOSS_LIMIT | DRAWDOWN_BREAKER | KILL_SWITCH | etc.
    signal_id TEXT,
    description TEXT NOT NULL,
    equity_at_event REAL,
    triggered_at TEXT NOT NULL
);

-- ============================================================
-- STRATEGY METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS strategy_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    win_rate REAL,
    avg_win_pct REAL,
    avg_loss_pct REAL,
    profit_factor REAL,
    max_drawdown_pct REAL,
    net_pnl_pct REAL,
    sharpe_ratio REAL,
    computed_at TEXT NOT NULL
);

-- ============================================================
-- SYSTEM EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    level TEXT NOT NULL,    -- INFO | WARNING | ERROR | CRITICAL
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    context_json TEXT,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_events_level
    ON system_events (level, occurred_at DESC);
