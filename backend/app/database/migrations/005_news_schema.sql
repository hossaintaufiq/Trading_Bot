-- Migration 005 — Immutable News Schema & Point-in-Time Event Tracking
-- Date: 2026-11-03
-- Description: Create tables for immutable news articles, revision history, event clusters, and ingestion runs
-- Governed by: Rule S-05, Rule S-08, ADR-001, ADR-023

-- Core Article Metadata (Immutable identity)
CREATE TABLE IF NOT EXISTS news_articles (
    article_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,                     -- 'binance_announcements', 'gdelt_gkg'
    source_record_id TEXT,                    -- Unique code or GKG record ID
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    entities_json TEXT NOT NULL DEFAULT '[]', -- JSON list of symbols: ['BTC', 'ETH', 'BNB']
    source_verification_status TEXT NOT NULL, -- 'POINT_IN_TIME_VERIFIED', 'PARTIALLY_VERIFIED', 'HISTORICAL_TIMESTAMP_UNVERIFIED', 'REJECTED'
    raw_payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL                  -- Ingestion time (ISO UTC)
);

CREATE INDEX IF NOT EXISTS idx_news_articles_source_rec
    ON news_articles (source, source_record_id);

CREATE INDEX IF NOT EXISTS idx_news_articles_url
    ON news_articles (url);

CREATE INDEX IF NOT EXISTS idx_news_articles_canonical_url
    ON news_articles (canonical_url);

CREATE INDEX IF NOT EXISTS idx_news_articles_norm_title
    ON news_articles (normalized_title);

-- Immutable Article Revision History
-- If an article is updated, a new version row is created with an incremented version_number.
-- Historical version rows are NEVER overwritten or deleted.
CREATE TABLE IF NOT EXISTS news_article_versions (
    version_id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES news_articles(article_id),
    version_number INTEGER NOT NULL,          -- 1, 2, 3...
    title TEXT NOT NULL,
    body_text TEXT,
    category TEXT,
    pairs_json TEXT NOT NULL DEFAULT '[]',
    raw_payload TEXT NOT NULL,                -- Full raw response payload / CSV record
    raw_payload_sha256 TEXT NOT NULL,
    published_at TEXT,                        -- Original publisher publication time (ISO UTC)
    updated_at TEXT,                          -- Publisher update time (ISO UTC)
    provider_seen_at TEXT,                    -- Provider indexing timestamp (ISO UTC)
    first_seen_at TEXT NOT NULL,              -- First observed by NEPTUNE (ISO UTC)
    collected_at TEXT NOT NULL,               -- System ingestion timestamp (ISO UTC)
    available_at TEXT,                        -- Point-in-time research eligibility timestamp (ISO UTC)
    timestamp_precision TEXT NOT NULL,        -- 'millisecond', 'second', '15_minute', 'day'
    created_at TEXT NOT NULL,
    UNIQUE (article_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_news_versions_article_ver
    ON news_article_versions (article_id, version_number);

CREATE INDEX IF NOT EXISTS idx_news_versions_avail_at
    ON news_article_versions (available_at);

CREATE INDEX IF NOT EXISTS idx_news_versions_pub_at
    ON news_article_versions (published_at);

-- Event Deduplication Clusters
CREATE TABLE IF NOT EXISTS news_event_clusters (
    cluster_id TEXT PRIMARY KEY,
    cluster_title TEXT NOT NULL,
    primary_symbol TEXT,                      -- 'BTC', 'ETH', 'BNB', etc.
    earliest_available_at TEXT NOT NULL,      -- min(available_at) across all members (ISO UTC)
    article_count INTEGER NOT NULL DEFAULT 1,
    clustering_algorithm TEXT NOT NULL,       -- 'simhash_v1_entity_matched'
    confidence_score REAL NOT NULL,           -- 0.0 to 1.0
    matching_evidence_json TEXT NOT NULL,     -- JSON explaining match criteria
    review_status TEXT NOT NULL DEFAULT 'UNREVIEWED', -- 'UNREVIEWED', 'VERIFIED', 'FLAGGED'
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_clusters_earliest_avail
    ON news_event_clusters (earliest_available_at);

CREATE INDEX IF NOT EXISTS idx_news_clusters_sym
    ON news_event_clusters (primary_symbol, earliest_available_at);

-- Many-to-Many Article to Event Cluster Mapping
CREATE TABLE IF NOT EXISTS news_cluster_members (
    cluster_id TEXT NOT NULL REFERENCES news_event_clusters(cluster_id),
    article_id TEXT NOT NULL REFERENCES news_articles(article_id),
    simhash_distance INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL,
    PRIMARY KEY (cluster_id, article_id)
);

-- Ingestion Runs & Resumable Checkpoints
CREATE TABLE IF NOT EXISTS news_ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target_asset TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL,                     -- 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL'
    records_ingested INTEGER NOT NULL DEFAULT 0,
    unique_articles INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    cursor_state_json TEXT,                   -- JSON cursor state for resuming
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT
);
