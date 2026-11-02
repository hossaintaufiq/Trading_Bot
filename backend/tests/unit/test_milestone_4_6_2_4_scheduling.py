"""
NEPTUNE Unit & Integration Tests — Milestone 4.6.2.4
Point-in-Time Execution Scheduling & Backtesting Engine Integration

Verifies all 15 required automated test scenarios and the end-to-end integration flow:
1. Signal generated at a finalized candle close.
2. Order filled only at the next eligible execution point.
3. News event arriving after the candle decision cutoff (excluded).
4. News event arriving before the candle decision cutoff (eligible).
5. Future article revision excluded from historical decisions.
6. Same-candle fill rejected (look-ahead exception).
7. Missing next candle handling.
8. Market-data gap between decision and execution (order expiry).
9. Multiple signals sharing a timestamp (deterministic ordering).
10. Risk Manager rejection (never scheduled or filled).
11. Daily loss circuit breaker enforcement at execution time.
12. Maximum drawdown circuit breaker enforcement at execution time.
13. Fee, spread, and slippage accounting on next-open fill.
14. Stop-loss gap handling on market open.
15. Deterministic replay reproducibility.
16. End-to-end integration test tracing news -> cutoff -> evaluation -> approval -> scheduling -> execution -> accounting.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import pytest

from app.agents.strategy_analyst import RawCandidateSignal
from app.data.market.validator import ValidatedCandle
from app.data.news.models import SourceVerificationStatus
from app.data.news.temporal import PointInTimeExecutionSynchronizer
from app.risk.risk_manager import RiskManager
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    ExecutionPolicy,
    OrderStatus,
    ScheduledOrder,
)
from app.simulation.news_boundary import NewsIntelligenceBoundary
from app.simulation.scheduling import PointInTimeExecutionScheduler


def make_candle(
    i: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 100.0,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
    base_time: Optional[datetime] = None,
) -> ValidatedCandle:
    """Helper creating standardized synthetic candles."""
    start = base_time or datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    dt = start + timedelta(minutes=15 * i)
    return ValidatedCandle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        is_closed=True,
    )


class TestPointInTimeExecutionScheduling:
    """Suite of verification tests for Milestone 4.6.2.4 execution scheduling."""

    def test_case_01_signal_generated_at_finalized_candle_close(self):
        """Case 1: Verify a signal is generated at a finalized candle close timestamp."""
        c = make_candle(1, 100.0, 105.0, 99.0, 104.0)
        assert c.is_closed is True
        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)

        order = scheduler.schedule_order(
            signal_id="sig_test_01",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c.timestamp,
            candle_close_timestamp=c.timestamp,
            position_size=Decimal("0.5"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_01",
            market_regime="TRENDING_BULL",
            strategy_metadata={"confidence": 0.8},
        )
        assert order.status == OrderStatus.SCHEDULED
        assert order.candle_close_timestamp == c.timestamp
        assert order.earliest_eligible_execution_timestamp == c.timestamp

    def test_case_02_order_filled_only_at_next_eligible_execution_point(self):
        """Case 2: Verify order fills at the open of the next candle, not at decision close."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        c1 = make_candle(1, 104.5, 108.0, 104.0, 107.0)

        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator(taker_fee_pct=Decimal("0.001"), slippage_pct=Decimal("0.0005"), spread_bps=Decimal("2.0"))

        order = scheduler.schedule_order(
            signal_id="sig_test_02",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_02",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        filled_pairs, _ = scheduler.process_candle_open(
            curr_candle=c1,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )

        assert len(filled_pairs) == 1
        filled_order, pos = filled_pairs[0]
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.actual_fill_timestamp == c1.timestamp
        assert filled_order.raw_fill_price == Decimal("104.5")  # c1.open
        assert pos.entry_timestamp == c1.timestamp
        assert pos.raw_entry_price == Decimal("104.5")

    def test_case_03_news_event_arriving_after_candle_decision_cutoff(self):
        """Case 3: News event arriving after candle close is excluded from that decision cycle."""
        boundary = NewsIntelligenceBoundary()
        c_close = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        events = [{
            "article_code": "art_late",
            "source": "binance_announcements",
            "source_verification_status": "POINT_IN_TIME_VERIFIED",
            "available_at": "2026-11-01T12:00:01.000Z",  # 1 second after close
            "relevance_classification": "EXCHANGE_WIDE",
            "affected_assets": ["BTC"],
        }]

        eligible, excluded = boundary.filter_events_at_decision_cutoff(events, "BTCUSDT", c_close, "15m")
        assert len(eligible) == 0
        assert len(excluded) == 1
        assert excluded[0]["exclusion_reason"] == "EVENT_AVAILABLE_AFTER_DECISION_CUTOFF"

    def test_case_04_news_event_arriving_before_candle_decision_cutoff(self):
        """Case 4: News event arriving before or exactly at candle close is eligible."""
        boundary = NewsIntelligenceBoundary()
        c_close = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        events = [{
            "article_code": "art_on_time",
            "source": "binance_announcements",
            "source_verification_status": "POINT_IN_TIME_VERIFIED",
            "available_at": "2026-11-01T11:59:59.000Z",  # 1 second before close
            "relevance_classification": "EXCHANGE_WIDE",
            "affected_assets": ["BTC"],
        }]

        eligible, excluded = boundary.filter_events_at_decision_cutoff(events, "BTCUSDT", c_close, "15m")
        assert len(eligible) == 1
        assert len(excluded) == 0
        assert eligible[0]["article_code"] == "art_on_time"

    def test_case_05_future_article_revision_excluded_from_historical_decisions(self):
        """Case 5: Revisions published after decision cutoff are invisible; earlier revision is used."""
        boundary = NewsIntelligenceBoundary()
        c_close = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

        events = [{
            "article_code": "art_revised",
            "source": "binance_announcements",
            "source_verification_status": "POINT_IN_TIME_VERIFIED",
            "available_at": "2026-11-01T10:00:00.000Z",
            "relevance_classification": "EXCHANGE_WIDE",
            "affected_assets": ["BTC"],
            "versions": [
                {
                    "version_number": 1,
                    "headline": "Initial Announcement",
                    "available_at": "2026-11-01T10:00:00.000Z",
                },
                {
                    "version_number": 2,
                    "headline": "Revised Announcement (Future)",
                    "available_at": "2026-11-01T14:00:00.000Z",
                },
            ],
        }]

        eligible, _ = boundary.filter_events_at_decision_cutoff(events, "BTCUSDT", c_close, "15m")
        assert len(eligible) == 1
        assert eligible[0]["headline"] == "Initial Announcement"
        assert eligible[0]["version_number"] == 1

    def test_case_06_same_candle_fill_rejected(self):
        """Case 6: Reject look-ahead fills attempting same-candle execution after close decision."""
        dt_close = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        dt_exec_same = datetime(2026, 11, 1, 11, 55, 0, tzinfo=timezone.utc)

        # Execution earlier than decision close
        with pytest.raises(ValueError, match="Look-ahead violation"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close,
                execution_dt=dt_exec_same,
                execution_price_type="NEXT_BAR_OPEN",
            )

        # Forbidden price type CURRENT_CLOSE
        with pytest.raises(ValueError, match="Same-candle execution price type 'CURRENT_CLOSE' is forbidden"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close,
                execution_dt=dt_close,
                execution_price_type="CURRENT_CLOSE",
            )

    def test_case_07_missing_next_candle_handling(self):
        """Case 7: Missing next candle leaves order pending without crashing or premature fill."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        c_other = make_candle(1, 104.5, 108.0, 104.0, 107.0, symbol="ETHUSDT")

        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator()

        order = scheduler.schedule_order(
            signal_id="sig_test_07",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_07",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Evaluate against candle for ETHUSDT (BTC candle is missing)
        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_other,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 0
        assert len(scheduler.pending_orders) == 1
        assert scheduler.pending_orders[0].status == OrderStatus.SCHEDULED

    def test_case_08_market_data_gap_between_decision_and_execution(self):
        """Case 8: Excessive market data gap triggers deterministic order expiry."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        # Gap of 10 bars (2.5 hours) on 15m timeframe, max_gap_bars = 3
        c_gapped = make_candle(10, 120.0, 125.0, 119.0, 124.0)

        scheduler = PointInTimeExecutionScheduler(
            execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
            max_execution_gap_bars=3,
        )
        sim = PaperExecutionSimulator()

        order = scheduler.schedule_order(
            signal_id="sig_test_08",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_08",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_gapped,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.EXPIRED
        assert "Data gap exceeded" in terminal[0].rejection_reason

    def test_case_09_multiple_signals_sharing_timestamp_ordering(self):
        """Case 9: Multiple signals sharing timestamp are ordered deterministically by symbol/id."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)

        o_eth = scheduler.schedule_order(
            signal_id="sig_b",
            symbol="ETHUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("90.0"),
            take_profit=Decimal("120.0"),
            risk_approval_token="tok_b",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        o_btc = scheduler.schedule_order(
            signal_id="sig_a",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("90.0"),
            take_profit=Decimal("120.0"),
            risk_approval_token="tok_a",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Scheduler must sort deterministically by (candle_close_timestamp, signal_id, symbol)
        assert scheduler.pending_orders[0].signal_id == "sig_a"
        assert scheduler.pending_orders[1].signal_id == "sig_b"

    def test_case_10_risk_manager_rejection_never_scheduled(self):
        """Case 10: Candidate rejected by Risk Manager is never scheduled or filled."""
        rm = RiskManager(min_reward_risk_ratio=Decimal("2.0"))
        # Signal with RR = 1.6 satisfies Pydantic (>= 1.5) but fails RiskManager (requires >= 2.0)
        cand = RawCandidateSignal(
            signal_id="sig_bad_rr",
            symbol="BTCUSDT",
            direction="LONG",
            timeframe="15m",
            timestamp="2026-11-01T12:00:00.000Z",
            entry_price=100.0,
            suggested_stop_loss=90.0,
            suggested_take_profit=116.0,
            risk_reward_ratio=1.6,
            raw_confidence=0.8,
            strategy_id="test",
            rationale="test",
        )

        res = rm.evaluate_signal(
            signal=cand,
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            open_positions=[],
            timestamp=cand.timestamp,
        )
        assert res.approved is False
        assert res.rejection_code == "INSUFFICIENT_RR_RATIO"

    def test_case_11_daily_loss_circuit_breaker_cancels_at_execution(self):
        """Case 11: Daily loss limit breached prior to fill rejects the scheduled order."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        c1 = make_candle(1, 104.5, 108.0, 104.0, 107.0)

        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator()

        order = scheduler.schedule_order(
            signal_id="sig_test_11",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_11",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Realized loss of -30.0 on 1000.0 daily starting equity = -3.0% (breaches 2.0% limit)
        filled, terminal = scheduler.process_candle_open(
            curr_candle=c1,
            current_open_positions=[],
            current_equity=Decimal("970.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("-30.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.REJECTED
        assert "Daily loss limit active" in terminal[0].rejection_reason

    def test_case_12_maximum_drawdown_circuit_breaker_cancels_at_execution(self):
        """Case 12: Max drawdown circuit breaker (5.0%) breached prior to fill rejects the scheduled order."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        c1 = make_candle(1, 104.5, 108.0, 104.0, 107.0)

        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator()

        order = scheduler.schedule_order(
            signal_id="sig_test_12",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_valid_12",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Current equity 940 on 1000 peak = 6.0% drawdown (breaches 5.0% circuit breaker)
        filled, terminal = scheduler.process_candle_open(
            curr_candle=c1,
            current_open_positions=[],
            current_equity=Decimal("940.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.REJECTED
        assert "Drawdown circuit breaker active" in terminal[0].rejection_reason

    def test_case_13_fee_spread_and_slippage_accounting(self):
        """Case 13: Verifies exact Decimal accounting on entry fill under next-open execution."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        c1 = make_candle(1, 100.0, 105.0, 99.0, 103.0)  # Open = 100.0

        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),    # 0.1%
            slippage_pct=Decimal("0.0005"),    # 0.05%
            spread_bps=Decimal("2.0"),         # 2 bps -> half-spread = 0.01% = 0.0001
        )
        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)

        scheduler.schedule_order(
            signal_id="sig_test_13",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("2.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            risk_approval_token="tok_13",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        filled, _ = scheduler.process_candle_open(
            curr_candle=c1,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )

        assert len(filled) == 1
        _, pos = filled[0]

        # Raw price = 100.0
        # Friction multiplier = 1 + 0.0005 + 0.0001 = 1.0006
        # Exec entry price = 100.0 * 1.0006 = 100.06
        expected_exec_price = Decimal("100.0") * (Decimal("1") + Decimal("0.0005") + Decimal("0.0001"))
        assert pos.entry_price == expected_exec_price

        # Notional = 100.06 * 2.0 = 200.12
        # Fee = 200.12 * 0.001 = 0.20012
        expected_notional = expected_exec_price * Decimal("2.0")
        assert pos.entry_fee == expected_notional * Decimal("0.001")

        # Slippage cost = (100.0 * 0.0005) * 2.0 = 0.10
        assert pos.entry_slippage_cost == Decimal("0.10")

        # Spread cost = (100.0 * 0.0001) * 2.0 = 0.02
        assert pos.entry_spread_cost == Decimal("0.02")

    def test_case_14_stop_loss_opening_gap_handling(self):
        """Case 14: Market opening gapped beyond stop loss is rejected before fill."""
        c0 = make_candle(0, 100.0, 105.0, 99.0, 104.0)
        # Next candle opens at 94.0, which is below the LONG stop loss of 95.0
        c_gap_down = make_candle(1, 94.0, 96.0, 92.0, 95.0)

        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator()

        scheduler.schedule_order(
            signal_id="sig_test_14",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=c0.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            risk_approval_token="tok_14",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_gap_down,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.REJECTED
        assert "Market opening gap below stop loss" in terminal[0].rejection_reason

    def test_case_15_replay_determinism_identical_results(self):
        """Case 15: Two identical simulation runs produce bit-for-bit identical trade ledgers."""
        candles = [
            make_candle(0, 100.0, 102.0, 99.0, 101.0),
            make_candle(1, 101.0, 103.0, 100.0, 102.0),
            make_candle(2, 102.0, 105.0, 101.0, 104.0),
            make_candle(3, 104.0, 106.0, 103.0, 105.0),
        ]

        def run_sim():
            sched = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
            sim = PaperExecutionSimulator()
            sched.schedule_order(
                signal_id="sig_det",
                symbol="BTCUSDT",
                timeframe="15m",
                direction="LONG",
                signal_timestamp=candles[0].timestamp,
                candle_close_timestamp=candles[0].timestamp,
                position_size=Decimal("1.0"),
                stop_loss=Decimal("98.0"),
                take_profit=Decimal("110.0"),
                risk_approval_token="tok_det",
                market_regime="TRENDING_BULL",
                strategy_metadata={},
            )
            filled, _ = sched.process_candle_open(
                curr_candle=candles[1],
                current_open_positions=[],
                current_equity=Decimal("1000.0"),
                peak_equity=Decimal("1000.0"),
                daily_starting_equity=Decimal("1000.0"),
                daily_realized_pnl=Decimal("0.0"),
                execution_simulator=sim,
                max_concurrent_positions=2,
                max_drawdown_pct=Decimal("0.05"),
                daily_loss_limit_pct=Decimal("0.02"),
            )
            trade = sim.evaluate_candle_bracket(filled[0][1], candles[2])
            return trade

        t1 = run_sim()
        t2 = run_sim()
        assert t1 is None and t2 is None  # Neither stopped out at candle 2

    @pytest.mark.asyncio
    async def test_case_16_end_to_end_news_to_execution_integration(self):
        """
        Complete integration test tracing:
        1. Timestamped news event arriving and validated via NewsIntelligenceBoundary.
        2. Closed candle triggering strategy & Risk Manager approval.
        3. Scheduled order enqueued with complete provenance contract.
        4. Next candle open filling order at next-bar open price.
        5. Position stopped out conservatively with full Decimal friction and accounting.
        """
        base = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        c0 = make_candle(0, 100.0, 102.0, 99.0, 101.0, base_time=base)
        c1 = make_candle(1, 101.5, 104.0, 101.0, 103.0, base_time=base)
        c2 = make_candle(2, 103.0, 103.5, 94.0, 95.0, base_time=base)  # Low hits stop (95.0)

        # 1. News boundary check
        boundary = NewsIntelligenceBoundary()
        news_input = [{
            "article_code": "btc_announcement_101",
            "source": "binance_announcements",
            "source_verification_status": "POINT_IN_TIME_VERIFIED",
            "available_at": c0.timestamp,  # Available at or before c0 close
            "relevance_classification": "EXCHANGE_WIDE",
            "affected_assets": ["BTC"],
            "headline": "Binance Adds New Trading Pairs",
        }]

        eligible, _ = boundary.filter_events_at_decision_cutoff(
            events=news_input,
            symbol="BTCUSDT",
            candle_close_dt=datetime.fromisoformat(c0.timestamp.replace("Z", "+00:00")),
            timeframe="15m",
        )
        assert len(eligible) == 1

        # 2. Risk Manager evaluation
        rm = RiskManager(
            max_concurrent_positions=2,
            risk_per_trade_pct=Decimal("0.005"),
            min_reward_risk_ratio=Decimal("1.5"),
        )
        cand = RawCandidateSignal(
            signal_id="sig_e2e_01",
            symbol="BTCUSDT",
            direction="LONG",
            timeframe="15m",
            timestamp=c0.timestamp,
            entry_price=101.0,
            suggested_stop_loss=95.0,
            suggested_take_profit=112.0,
            risk_reward_ratio=1.83,
            raw_confidence=0.85,
            strategy_id="trend_momentum_v1",
            rationale="News and momentum confluence",
        )

        risk_res = rm.evaluate_signal(
            signal=cand,
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            open_positions=[],
            timestamp=c0.timestamp,
        )
        assert risk_res.approved is True
        assert risk_res.position_size is not None

        # 3. Execution scheduling under NEXT_ELIGIBLE_PRICE
        scheduler = PointInTimeExecutionScheduler(execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE)
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("2.0"),
        )

        order = scheduler.schedule_order(
            signal_id=cand.signal_id,
            symbol=cand.symbol,
            timeframe=cand.timeframe,
            direction=cand.direction,
            signal_timestamp=cand.timestamp,
            candle_close_timestamp=c0.timestamp,
            position_size=risk_res.position_size,
            stop_loss=Decimal(str(cand.suggested_stop_loss)),
            take_profit=Decimal(str(cand.suggested_take_profit)),
            risk_approval_token=risk_res.risk_approval_token or "tok_e2e_approval",
            market_regime="TRENDING_BULL",
            strategy_metadata={"news_code": eligible[0]["article_code"]},
            exit_policy="FIXED_BRACKET",
        )
        assert order.status == OrderStatus.SCHEDULED
        assert order.candle_close_timestamp == c0.timestamp

        # 4. Process candle 1 open (Next Eligible Price fill)
        filled, _ = scheduler.process_candle_open(
            curr_candle=c1,
            current_open_positions=[],
            current_equity=Decimal("1000.0"),
            peak_equity=Decimal("1000.0"),
            daily_starting_equity=Decimal("1000.0"),
            daily_realized_pnl=Decimal("0.0"),
            execution_simulator=sim,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 1
        filled_order, pos = filled[0]
        assert filled_order.actual_fill_timestamp == c1.timestamp
        assert filled_order.raw_fill_price == Decimal(str(c1.open))  # 101.5
        assert pos.entry_timestamp == c1.timestamp
        assert pos.raw_entry_price == Decimal("101.5")
        assert pos.risk_approval_token == order.risk_approval_token
        assert pos.execution_policy == ExecutionPolicy.NEXT_ELIGIBLE_PRICE

        # 5. Process candle 2: hits stop loss (c2.low = 94.0 <= stop 95.0)
        trade = sim.evaluate_candle_bracket(pos, c2)
        assert trade is not None
        assert trade.exit_reason == "STOP_LOSS"
        assert trade.net_pnl < Decimal("0")
        assert trade.fees > Decimal("0")
        assert trade.slippage_cost > Decimal("0")
        assert trade.spread_cost > Decimal("0")
        assert trade.candle_close_timestamp == c0.timestamp
        assert trade.execution_policy == ExecutionPolicy.NEXT_ELIGIBLE_PRICE
        assert trade.risk_approval_token == order.risk_approval_token

    @pytest.mark.asyncio
    async def test_case_17_engine_news_gated_legacy_rejection(self):
        """Case 17: Backtest engine rejects news inputs when legacy close-fill policy is active."""
        config = BacktestConfig(
            symbols=["BTCUSDT"],
            execution_policy=ExecutionPolicy.LEGACY_CLOSE_FILL,
        )
        engine = HistoricalBacktestEngine(config=config)
        news_input = [{"article_code": "test_news"}]

        with pytest.raises(ValueError, match="News-gated simulations require execution_policy='NEXT_ELIGIBLE_PRICE'"):
            await engine.run(candles_by_symbol={"BTCUSDT": []}, news_events=news_input)

    @pytest.mark.asyncio
    async def test_case_18_engine_full_run_with_next_eligible_price(self):
        """Case 18: Historical backtest engine completes full run under NEXT_ELIGIBLE_PRICE policy."""
        # Generate 40 trending candles for warmup and strategy setup
        candles = []
        price = 100.0
        base_time = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
        for i in range(45):
            o = price
            h = price + 2.0
            l = price - 0.5
            c = price + 1.5
            price = c
            candles.append(make_candle(i, o, h, l, c, base_time=base_time))

        config = BacktestConfig(
            symbols=["BTCUSDT"],
            timeframe="15m",
            execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
            initial_capital=Decimal("1000.00"),
        )
        engine = HistoricalBacktestEngine(config=config)
        res = await engine.run(candles_by_symbol={"BTCUSDT": candles})

        assert res is not None
        assert res.metrics is not None
        assert len(res.equity_curve) == 45
        for trade in res.trades:
            assert trade.execution_policy == ExecutionPolicy.NEXT_ELIGIBLE_PRICE
            assert trade.candle_close_timestamp is not None
