-- Migration 007 — Macro Event Provenance & Timestamp Granularity Schema
-- Date: 2026-11-03
-- Description: Adds separate columns for first_observed_at, collected_at, revision_observed_at
-- Governed by: Rule S-05, ADR-023, ADR-024, ADR-025

ALTER TABLE news_macro_events ADD COLUMN first_observed_at TEXT;
ALTER TABLE news_macro_events ADD COLUMN collected_at TEXT;
ALTER TABLE news_macro_events ADD COLUMN revision_observed_at TEXT;

