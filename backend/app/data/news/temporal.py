"""
NEPTUNE News Temporal Integrity Module (`temporal.py`)

Governs timestamp parsing, provenance tracking, latency buffers, and point-in-time
eligibility verification to eliminate look-ahead bias and revisionism.
Governed by: Rule S-05, ADR-020, ADR-023.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

from app.data.news.models import SourceVerificationStatus, TimestampPrecision


def parse_iso_utc(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 string to timezone-aware UTC datetime."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def parse_epoch_ms(epoch_ms: Optional[int]) -> Optional[datetime]:
    """Convert Unix epoch milliseconds to timezone-aware UTC datetime."""
    if epoch_ms is None or epoch_ms <= 0:
        return None
    try:
        return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    except (ValueError, OSError):
        return None


def parse_gdelt_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse GDELT YYYYMMDDHHMMSS format to timezone-aware UTC datetime.
    Example: '20261102171500' -> 2026-11-02 17:15:00 UTC.
    """
    if not date_str or len(date_str.strip()) < 14:
        return None
    clean_str = date_str.strip()[:14]
    try:
        return datetime.strptime(clean_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime as canonical ISO-8601 UTC string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def resolve_temporal_coordinates(
    source: str,
    raw_pub_ms: Optional[int] = None,
    raw_update_ms: Optional[int] = None,
    gdelt_date_str: Optional[str] = None,
    collected_at: Optional[datetime] = None,
    latency_buffer_seconds: int = 300,
) -> Dict[str, Any]:
    """
    Determine immutable temporal coordinates and defensible availability timestamp.

    Rules:
    1. Binance Announcements:
       - publishDate is verified millisecond timestamp.
       - published_at = to_iso_utc(raw_pub_ms).
       - updated_at = to_iso_utc(raw_update_ms).
       - available_at = published_at (exchange-level point-in-time timestamp).
       - Precision: MILLISECOND.
       - Status: POINT_IN_TIME_VERIFIED.

    2. GDELT GKG Records:
       - provider_seen_at is parsed from 15-minute slice (YYYYMMDDHHMMSS).
       - published_at is set to None (observation time is NOT publisher publication time).
       - available_at = provider_seen_at + latency_buffer_seconds (default 300s = 5m).
       - Precision: FIFTEEN_MINUTE.
       - Status: PARTIALLY_VERIFIED.
       - NEVER silently promote to POINT_IN_TIME_VERIFIED.

    3. Invariant Checks:
       - If published_at or provider_seen_at is in the future relative to collected_at + 1h:
         Status becomes REJECTED.
    """
    if collected_at is None:
        collected_at = datetime.now(timezone.utc)

    now_iso = to_iso_utc(collected_at)

    if source == "binance_announcements":
        dt_pub = parse_epoch_ms(raw_pub_ms)
        dt_upd = parse_epoch_ms(raw_update_ms)

        if dt_pub is None:
            return {
                "published_at": None,
                "updated_at": None,
                "provider_seen_at": None,
                "first_seen_at": now_iso,
                "collected_at": now_iso,
                "available_at": None,
                "timestamp_precision": TimestampPrecision.MILLISECOND,
                "source_verification_status": SourceVerificationStatus.REJECTED,
                "rejection_reason": "Missing required publishDate in Binance detail payload",
            }

        # Check for future timestamp look-ahead anomaly (> 1 hour ahead of collection)
        if dt_pub > collected_at + timedelta(hours=1):
            return {
                "published_at": to_iso_utc(dt_pub),
                "updated_at": to_iso_utc(dt_upd),
                "provider_seen_at": None,
                "first_seen_at": now_iso,
                "collected_at": now_iso,
                "available_at": None,
                "timestamp_precision": TimestampPrecision.MILLISECOND,
                "source_verification_status": SourceVerificationStatus.REJECTED,
                "rejection_reason": f"Future publication timestamp anomaly: {dt_pub.isoformat()} > {collected_at.isoformat()}",
            }

        pub_iso = to_iso_utc(dt_pub)
        upd_iso = to_iso_utc(dt_upd) if dt_upd else pub_iso

        return {
            "published_at": pub_iso,
            "updated_at": upd_iso,
            "provider_seen_at": None,
            "first_seen_at": now_iso,
            "collected_at": now_iso,
            "available_at": pub_iso,
            "timestamp_precision": TimestampPrecision.MILLISECOND,
            "source_verification_status": SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
            "rejection_reason": None,
        }

    elif source == "gdelt_gkg":
        dt_seen = parse_gdelt_date(gdelt_date_str)
        if dt_seen is None:
            return {
                "published_at": None,
                "updated_at": None,
                "provider_seen_at": None,
                "first_seen_at": now_iso,
                "collected_at": now_iso,
                "available_at": None,
                "timestamp_precision": TimestampPrecision.FIFTEEN_MINUTE,
                "source_verification_status": SourceVerificationStatus.REJECTED,
                "rejection_reason": f"Invalid GDELT date format: '{gdelt_date_str}'",
            }

        # Lookahead anomaly check
        if dt_seen > collected_at + timedelta(hours=1):
            return {
                "published_at": None,
                "updated_at": None,
                "provider_seen_at": to_iso_utc(dt_seen),
                "first_seen_at": now_iso,
                "collected_at": now_iso,
                "available_at": None,
                "timestamp_precision": TimestampPrecision.FIFTEEN_MINUTE,
                "source_verification_status": SourceVerificationStatus.REJECTED,
                "rejection_reason": f"Future GDELT indexing timestamp anomaly: {dt_seen.isoformat()} > {collected_at.isoformat()}",
            }

        seen_iso = to_iso_utc(dt_seen)
        dt_avail = dt_seen + timedelta(seconds=latency_buffer_seconds)
        avail_iso = to_iso_utc(dt_avail)

        return {
            "published_at": None,  # Conservative: observation time is not publisher publication time
            "updated_at": None,
            "provider_seen_at": seen_iso,
            "first_seen_at": now_iso,
            "collected_at": now_iso,
            "available_at": avail_iso,
            "timestamp_precision": TimestampPrecision.FIFTEEN_MINUTE,
            "source_verification_status": SourceVerificationStatus.PARTIALLY_VERIFIED,
            "rejection_reason": None,
        }

    else:
        return {
            "published_at": None,
            "updated_at": None,
            "provider_seen_at": None,
            "first_seen_at": now_iso,
            "collected_at": now_iso,
            "available_at": now_iso,
            "timestamp_precision": TimestampPrecision.SECOND,
            "source_verification_status": SourceVerificationStatus.HISTORICAL_TIMESTAMP_UNVERIFIED,
            "rejection_reason": f"Unknown news source: '{source}'",
        }


def is_eligible_at_candle_close(
    available_at_iso: Optional[str],
    candle_close_dt: datetime,
    status: SourceVerificationStatus,
) -> bool:
    """
    Evaluate whether a news record is strictly eligible for consumption at candle close.

    Requirements:
    1. available_at must be populated and parseable.
    2. available_at <= candle_close_dt.
    3. Status must be POINT_IN_TIME_VERIFIED or PARTIALLY_VERIFIED (never REJECTED).
    """
    if status == SourceVerificationStatus.REJECTED:
        return False

    if not available_at_iso:
        return False

    dt_avail = parse_iso_utc(available_at_iso)
    if dt_avail is None:
        return False

    if candle_close_dt.tzinfo is None:
        candle_close_dt = candle_close_dt.replace(tzinfo=timezone.utc)
    else:
        candle_close_dt = candle_close_dt.astimezone(timezone.utc)

    return dt_avail <= candle_close_dt
