-- Migration 006 — News Event Taxonomy, Relevance & Macro Calendar Registry
-- Date: 2026-11-03
-- Description: Creates news_macro_events table and registers schema for Milestone 4.6.2
-- Governed by: Rule S-05, Rule S-08, ADR-023, ADR-024

-- Macroeconomic & Protocol Event Calendar Registry (Source C)
CREATE TABLE IF NOT EXISTS news_macro_events (
    macro_event_id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_category TEXT NOT NULL,             -- 'MONETARY_POLICY', 'MACROECONOMIC', 'ETF_INSTITUTIONAL_FLOW', 'PROTOCOL_UPGRADE'
    scheduled_at TEXT NOT NULL,               -- Scheduled time in ISO-8601 UTC
    actual_release_at TEXT NOT NULL,          -- Actual release time in ISO-8601 UTC
    source TEXT NOT NULL,                     -- 'federal_reserve', 'bls', 'sec_gov', 'bitcoin_core'
    source_url TEXT NOT NULL,
    source_record_id TEXT,
    affected_assets_json TEXT NOT NULL DEFAULT '[]', -- JSON list of symbols: ['BTC', 'ETH', 'BNB']
    relevance_classification TEXT NOT NULL,   -- 'MACRO', 'MARKET_WIDE', 'DIRECT_ASSET'
    source_verification_status TEXT NOT NULL DEFAULT 'POINT_IN_TIME_VERIFIED',
    timestamp_precision TEXT NOT NULL DEFAULT 'second',
    description TEXT,
    raw_payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_macro_events_cat_rel
    ON news_macro_events (event_category, relevance_classification);

CREATE INDEX IF NOT EXISTS idx_macro_events_release_time
    ON news_macro_events (actual_release_at);
