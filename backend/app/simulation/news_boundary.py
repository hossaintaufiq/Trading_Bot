"""
NEPTUNE News Intelligence Simulation Boundary (`news_boundary.py`)

Governs the ingestion, point-in-time filtering, revision isolation,
and relevance classification of news records for simulation research (Milestone 4.6.2.4).

Safety & Invariant Rules:
1. GDELT records are strictly excluded from intraday (< 1d) backtesting.
2. Future scheduled macro events (> 2026-11-03 23:59:59 UTC) are quarantined.
3. Macro records missing required provenance (observed/collected dates) are rejected.
4. Article revisions available after the decision cutoff are strictly invisible.
5. Multi-article clusters are deduplicated to earliest available timestamp.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.data.news.models import SourceVerificationStatus
from app.data.news.temporal import (
    PointInTimeExecutionSynchronizer,
    is_eligible_at_candle_close,
    parse_iso_utc,
    to_iso_utc,
)


class NewsIntelligenceBoundary:
    """
    Manages news and macro event availability for historical backtest engines.
    Ensures zero look-ahead bias and strict point-in-time eligibility.
    """

    # Conservative audit cutoff: all verified historical data in v2.0.0-news-historical is <= Nov 3, 2026
    HISTORICAL_AUDIT_CUTOFF = "2026-11-03T23:59:59.000Z"

    # Known future scheduled calendar entries quarantined from historical backtesting
    QUARANTINED_FORWARD_EVENTS = {
        "macro_20261104_fomc_decision",
        "macro_20261112_bls_cpi",
        "macro_20261105_fomc_rate",
        "macro_20261113_bls_cpi",
    }

    def __init__(self, audit_cutoff_iso: Optional[str] = None):
        self.audit_cutoff_iso = audit_cutoff_iso or self.HISTORICAL_AUDIT_CUTOFF
        self._dt_cutoff = parse_iso_utc(self.audit_cutoff_iso)

    def filter_events_at_decision_cutoff(
        self,
        events: List[Dict[str, Any]],
        symbol: str,
        candle_close_dt: datetime,
        timeframe: str = "15m",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters news/macro events strictly visible and eligible at candle_close_dt for symbol.

        Returns:
            (eligible_events, excluded_events)
            where each excluded event dictionary includes an 'exclusion_reason' field.
        """
        eligible: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []

        if candle_close_dt.tzinfo is None:
            candle_close_dt = candle_close_dt.replace(tzinfo=timezone.utc)
        else:
            candle_close_dt = candle_close_dt.astimezone(timezone.utc)

        # Track clusters to prevent duplicate signal emission across syndicated articles
        seen_clusters: Dict[str, Dict[str, Any]] = {}

        for raw_event in events:
            event = dict(raw_event)
            event_id = (
                event.get("event_id")
                or event.get("macro_event_id")
                or event.get("article_code")
                or event.get("cluster_id")
                or event.get("source_record_id")
                or "unknown"
            )
            source = event.get("source", "")
            category = event.get("event_category", "")
            relevance = event.get("relevance_classification", "UNCLASSIFIED")
            status_str = event.get("source_verification_status") or event.get("verification_status")
            status = SourceVerificationStatus(status_str) if status_str else SourceVerificationStatus.HISTORICAL_TIMESTAMP_UNVERIFIED

            # 1. Forward scheduled macro event quarantine check
            if event_id in self.QUARANTINED_FORWARD_EVENTS or event.get("is_future_scheduled") is True:
                event["exclusion_reason"] = "FORWARD_SCHEDULED_EVENT_QUARANTINED"
                excluded.append(event)
                continue

            actual_release = (
                event.get("actual_release_time")
                or event.get("actual_release_at")
                or event.get("scheduled_at")
            )
            if actual_release and self._dt_cutoff:
                dt_rel = parse_iso_utc(actual_release)
                if dt_rel and dt_rel > self._dt_cutoff:
                    event["exclusion_reason"] = "EVENT_BEYOND_HISTORICAL_AUDIT_CUTOFF"
                    excluded.append(event)
                    continue

            # 2. Macro provenance completeness check
            is_macro = (
                source in ("macro_calendar", "bls", "sec_gov", "bitcoin_core", "ethereum_foundation", "federal_reserve")
                or category == "MACROECONOMIC"
                or relevance == "MACRO"
            )
            if is_macro:
                first_obs = event.get("first_observed_at")
                coll_at = event.get("collected_at")
                if not first_obs and not coll_at:
                    event["exclusion_reason"] = "MISSING_REQUIRED_PROVENANCE"
                    excluded.append(event)
                    continue

            # 3. GDELT intraday restriction
            tf_lower = timeframe.lower()
            is_intraday = tf_lower in ("15m", "1h", "4h") or (tf_lower.endswith("m") and int(tf_lower[:-1]) < 1440)
            if source == "gdelt_gkg" and is_intraday:
                event["exclusion_reason"] = "GDELT_SUB_DAILY_INTRADAY_PROHIBITED"
                excluded.append(event)
                continue

            # 4. Status check: REJECTED status is never eligible
            if status == SourceVerificationStatus.REJECTED:
                event["exclusion_reason"] = "SOURCE_STATUS_REJECTED"
                excluded.append(event)
                continue

            # 5. Point-in-time availability cutoff check
            available_at_iso = (
                event.get("available_at")
                or event.get("actual_release_at")
                or event.get("actual_release_time")
                or event.get("published_at")
            )
            if not available_at_iso:
                event["exclusion_reason"] = "MISSING_AVAILABLE_AT_TIMESTAMP"
                excluded.append(event)
                continue

            dt_avail = parse_iso_utc(available_at_iso)
            if dt_avail is None or dt_avail > candle_close_dt:
                event["exclusion_reason"] = "EVENT_AVAILABLE_AFTER_DECISION_CUTOFF"
                excluded.append(event)
                continue

            # 6. Revision filtering (if article has multiple versions)
            versions = event.get("versions")
            if versions and isinstance(versions, list) and len(versions) > 1:
                visible_ver = PointInTimeExecutionSynchronizer.filter_visible_version(
                    versions=versions,
                    as_of_dt=candle_close_dt,
                )
                if not visible_ver:
                    event["exclusion_reason"] = "NO_REVISION_VISIBLE_AT_DECISION_CUTOFF"
                    excluded.append(event)
                    continue
                # Update event representation to match visible revision
                event["headline"] = visible_ver.get("headline", event.get("headline"))
                event["version_number"] = visible_ver.get("version_number", 1)

            # 7. Asset relevance matching
            assets = event.get("affected_assets")
            if assets is None and "affected_assets_json" in event:
                try:
                    assets = json.loads(event["affected_assets_json"]) if event["affected_assets_json"] else []
                except Exception:
                    assets = []
            elif assets is None:
                assets = []

            clean_sym = symbol.upper().replace("USDT", "")

            # Target asset relevant if:
            # - directly affected (symbol or base asset in affected_assets)
            # - exchange-wide or market-wide relevance
            # - macro event affecting whole market
            is_relevant = False
            if relevance in ("EXCHANGE_WIDE", "MARKET_WIDE", "MACRO") or source == "macro_calendar":
                is_relevant = True
            elif clean_sym in assets or symbol.upper() in assets:
                is_relevant = True

            if not is_relevant:
                event["exclusion_reason"] = f"IRRELEVANT_TO_TARGET_ASSET_{symbol}"
                excluded.append(event)
                continue

            # 8. Event cluster deduplication
            cluster_id = event.get("cluster_id")
            if cluster_id:
                if cluster_id in seen_clusters:
                    # Already processed earlier syndication of this event cluster
                    event["exclusion_reason"] = f"DUPLICATE_CLUSTER_MEMBER_{cluster_id}"
                    excluded.append(event)
                    continue
                seen_clusters[cluster_id] = event

            eligible.append(event)

        return eligible, excluded
