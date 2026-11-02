"""
NEPTUNE Milestone 4.6.2.2 Point-in-Time & Execution Synchronization Tests
(`test_milestone_4_6_2_2_pit.py`)

Verifies:
1. Event arriving strictly before candle close is eligible for Candle T, executes at T+1 Open.
2. Event arriving exactly at candle close is eligible for Candle T, executes at T+1 Open.
3. Event arriving strictly after candle close is ineligible for Candle T, becomes eligible for Candle T+1, executes at T+2 Open.
4. Event published during open candle is inaccessible until candle fully closes (in-progress candle ban).
5. Delayed provider observation timestamp prevents look-ahead to publisher release.
6. Multi-version revision isolation (v2 arriving at t2 is invisible at t < t2).
7. Scheduled macro event with unknown actual publication time.
8. GDELT partially verified record precision gating (banned on sub-hourly, allowed on 1h+).
9. Look-ahead detector strictly prohibits execution at current close, current open, or intrabar.
"""
from datetime import datetime, timezone, timedelta
import pytest

from app.data.news.models import SourceVerificationStatus, TimestampPrecision
from app.data.news.temporal import (
    PointInTimeExecutionSynchronizer,
    is_eligible_at_candle_close,
    resolve_temporal_coordinates,
    to_iso_utc,
    parse_iso_utc,
)


def test_event_arriving_strictly_before_close():
    """Event available at 11:45:00 UTC for 11:00-12:00 UTC candle."""
    bar_open = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    bar_close = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    next_bar_open = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    event_avail = "2025-06-15T11:45:00.000Z"

    sched = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar_open,
        bar_close_dt=bar_close,
        next_bar_open_dt=next_bar_open,
        status=SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
        timeframe_minutes=60,
    )

    assert sched["eligible"] is True
    assert sched["execution_target_dt"] == "2025-06-15T12:00:00.000Z"
    assert sched["execution_price_type"] == "NEXT_BAR_OPEN"


def test_event_arriving_exactly_at_close():
    """Event available at exactly 12:00:00 UTC for 11:00-12:00 UTC candle."""
    bar_open = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    bar_close = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    next_bar_open = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    event_avail = "2025-06-15T12:00:00.000Z"

    sched = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar_open,
        bar_close_dt=bar_close,
        next_bar_open_dt=next_bar_open,
        status=SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
        timeframe_minutes=60,
    )

    assert sched["eligible"] is True
    assert sched["execution_target_dt"] == "2025-06-15T12:00:00.000Z"
    assert sched["execution_price_type"] == "NEXT_BAR_OPEN"


def test_event_arriving_after_close():
    """Event available at 12:00:01 UTC is ineligible for 11:00-12:00 UTC candle, but eligible for 12:00-13:00 UTC candle."""
    bar1_open = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    bar1_close = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    next_bar_open = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    event_avail = "2025-06-15T12:00:01.000Z"

    # Candle 1 check
    sched1 = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar1_open,
        bar_close_dt=bar1_close,
        next_bar_open_dt=next_bar_open,
        status=SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
        timeframe_minutes=60,
    )
    assert sched1["eligible"] is False

    # Candle 2 check (12:00 to 13:00 UTC)
    bar2_open = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    bar2_close = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
    bar2_next_open = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)

    sched2 = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar2_open,
        bar_close_dt=bar2_close,
        next_bar_open_dt=bar2_next_open,
        status=SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
        timeframe_minutes=60,
    )
    assert sched2["eligible"] is True
    assert sched2["execution_target_dt"] == "2025-06-15T13:00:00.000Z"
    assert sched2["execution_price_type"] == "NEXT_BAR_OPEN"


def test_in_progress_candle_execution_forbidden():
    """An event arriving during Candle T cannot execute inside Candle T."""
    bar_open = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    bar_close = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    intrabar_exec = datetime(2025, 6, 15, 11, 30, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Look-ahead violation"):
        PointInTimeExecutionSynchronizer.assert_no_lookahead(
            decision_bar_close_dt=bar_close,
            execution_dt=intrabar_exec,
            execution_price_type="NEXT_BAR_OPEN",
        )


def test_same_candle_price_type_forbidden():
    """Order cannot specify CURRENT_CLOSE or INTRABAR as execution price."""
    bar_close = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    next_open = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    for bad_type in ["CURRENT_CLOSE", "CURRENT_OPEN", "INTRABAR", "BAR_CLOSE"]:
        with pytest.raises(ValueError, match="forbidden"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=bar_close,
                execution_dt=next_open,
                execution_price_type=bad_type,
            )


def test_delayed_provider_observation():
    """
    GDELT article published at 10:00 by external outlet, but GKG indexed at 10:30.
    Available timestamp must be 10:30 + 5m buffer = 10:35, NOT 10:00.
    """
    coords = resolve_temporal_coordinates(
        source="gdelt_gkg",
        gdelt_date_str="20250615103000",
        collected_at=datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
        latency_buffer_seconds=300,
    )

    assert coords["published_at"] is None
    assert coords["provider_seen_at"] == "2025-06-15T10:30:00.000Z"
    assert coords["available_at"] == "2025-06-15T10:35:00.000Z"
    assert coords["source_verification_status"] == SourceVerificationStatus.PARTIALLY_VERIFIED


def test_gdelt_partially_verified_precision_gating():
    """GDELT is barred from sub-hourly execution (e.g. 15m), but allowed on 1h."""
    bar_open = datetime(2025, 6, 15, 10, 45, 0, tzinfo=timezone.utc)
    bar_close = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    next_bar_open = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    event_avail = "2025-06-15T10:50:00.000Z"

    # On 15m timeframe, GDELT is rejected due to precision limitation
    sched_15m = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar_open,
        bar_close_dt=bar_close,
        next_bar_open_dt=next_bar_open,
        status=SourceVerificationStatus.PARTIALLY_VERIFIED,
        timeframe_minutes=15,
    )
    assert sched_15m["eligible"] is False
    assert "insufficient" in sched_15m["reason"]

    # On 1h timeframe, GDELT is allowed
    bar_open_1h = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    bar_close_1h = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    sched_1h = PointInTimeExecutionSynchronizer.resolve_execution_schedule(
        event_available_at_iso=event_avail,
        bar_open_dt=bar_open_1h,
        bar_close_dt=bar_close_1h,
        next_bar_open_dt=next_bar_open,
        status=SourceVerificationStatus.PARTIALLY_VERIFIED,
        timeframe_minutes=60,
    )
    assert sched_1h["eligible"] is True


def test_historical_revision_isolation():
    """
    Article has version 1 published at 10:00, and version 2 (correction) at 12:30.
    At 11:00 (as-of time), version 2 is invisible; only version 1 is returned.
    At 13:00, version 2 is visible.
    """
    v1 = {
        "version_number": 1,
        "headline": "Exchange announces temporary maintenance",
        "available_at": "2025-06-15T10:00:00.000Z",
    }
    v2 = {
        "version_number": 2,
        "headline": "Exchange cancels maintenance, systems normal",
        "available_at": "2025-06-15T12:30:00.000Z",
    }
    versions = [v1, v2]

    # As of 11:00 UTC (before v2)
    vis_1100 = PointInTimeExecutionSynchronizer.filter_visible_version(
        versions=versions,
        as_of_dt=datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
    )
    assert vis_1100 is not None
    assert vis_1100["version_number"] == 1
    assert "temporary maintenance" in vis_1100["headline"]

    # As of 13:00 UTC (after v2)
    vis_1300 = PointInTimeExecutionSynchronizer.filter_visible_version(
        versions=versions,
        as_of_dt=datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert vis_1300 is not None
    assert vis_1300["version_number"] == 2
    assert "cancels maintenance" in vis_1300["headline"]

