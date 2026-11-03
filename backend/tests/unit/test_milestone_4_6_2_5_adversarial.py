"""
NEPTUNE Milestone 4.6.2.5 — Independent Adversarial Verification Suite
(`test_milestone_4_6_2_5_adversarial.py`)

Forensic, adversarial validation tests covering:
1. Temporal look-ahead invariants (same-candle fill prevention, delayed availability).
2. Revision isolation and future leakage prevention.
3. Macro calendar provenance, future quarantine, and schema normalization.
4. GDELT intraday prohibition.
5. Deduplication and clustering under adversarial conditions (distinct events vs syndicated copies).
6. Execution cost arithmetic, cash conservation, and double-count prevention.
7. Cryptographic HMAC risk token authorization, tamper detection, replay prevention, and run binding.
8. Data-gap expiration, circuit-breaker re-verification, and deterministic replay.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.agents.strategy_analyst import RawCandidateSignal
from app.data.market.validator import ValidatedCandle
from app.data.news.deduplication import are_articles_event_duplicates, NewsEventClusterer
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


@pytest.fixture
def risk_manager():
    return RiskManager(
        max_concurrent_positions=2,
        risk_per_trade_pct=Decimal("0.005"),
        daily_loss_limit_pct=Decimal("0.02"),
        max_drawdown_pct=Decimal("0.05"),
        min_reward_risk_ratio=Decimal("1.5"),
        auth_secret="test_secret_key_milestone_4_6_2_5",
    )


@pytest.fixture
def execution_simulator():
    return PaperExecutionSimulator(
        taker_fee_pct=Decimal("0.001"),
        maker_fee_pct=Decimal("0.001"),
        slippage_pct=Decimal("0.0005"),
        spread_bps=Decimal("2.0"),
        conservative_ambiguity=True,
    )


@pytest.fixture
def sample_signal():
    return RawCandidateSignal(
        signal_id="sig_adversarial_001",
        strategy_id="trend_momentum_pullback_v1",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        timestamp="2026-11-01T12:00:00Z",
        entry_price=50000.0,
        suggested_stop_loss=49000.0,
        suggested_take_profit=52000.0,
        risk_reward_ratio=2.0,
        raw_confidence=0.85,
        rationale="Strong trend alignment",
    )


class TestMilestone4625Adversarial:
    """Comprehensive Adversarial Test Suite for Milestone 4.6.2.5."""

    # 1. Same-candle look-ahead prevention
    def test_adversarial_01_same_candle_lookahead(self):
        """Assert that executing at decision candle close or before candle open raises fatal error."""
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)
        dt_same_open = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

        # 1. Attempt fill before decision close (timestamp look-ahead)
        with pytest.raises(ValueError, match="Look-ahead violation"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close,
                execution_dt=dt_same_open,
                execution_price_type="NEXT_BAR_OPEN",
            )

        # 2. Attempt same-candle execution price types (CURRENT_CLOSE / BAR_CLOSE / INTRABAR)
        with pytest.raises(ValueError, match="Same-candle execution price type"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close,
                execution_dt=dt_close,
                execution_price_type="CURRENT_CLOSE",
            )

        with pytest.raises(ValueError, match="Same-candle execution price type"):
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close,
                execution_dt=dt_close,
                execution_price_type="INTRABAR",
            )

    # 2. Delayed event availability
    def test_adversarial_02_delayed_event_availability(self):
        """Events published before candle close but delayed in arrival are excluded."""
        boundary = NewsIntelligenceBoundary()
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)

        events = [
            {
                "event_id": "art_delayed_1",
                "source": "binance_announcements",
                "published_at": "2026-11-01T12:10:00Z",
                "available_at": "2026-11-01T12:16:00Z",  # Arrived 1 minute after close
                "affected_assets": ["BTC"],
                "relevance_classification": "MARKET_WIDE",
            }
        ]

        eligible, excluded = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="15m",
        )
        assert len(eligible) == 0
        assert len(excluded) == 1
        assert excluded[0]["exclusion_reason"] == "EVENT_AVAILABLE_AFTER_DECISION_CUTOFF"

    # 3. Revision leakage prevention
    def test_adversarial_03_revision_leakage(self):
        """Article revisions published after the decision cutoff must not leak into decisions."""
        boundary = NewsIntelligenceBoundary()
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)

        events = [
            {
                "event_id": "art_rev_1",
                "source": "binance_announcements",
                "available_at": "2026-11-01T12:00:00Z",
                "affected_assets": ["BTC"],
                "relevance_classification": "MARKET_WIDE",
                "versions": [
                    {
                        "version_number": 1,
                        "headline": "Binance Evaluates Maintenance",
                        "available_at": "2026-11-01T12:00:00Z",
                    },
                    {
                        "version_number": 2,
                        "headline": "Binance Emergency Shutdown Confirmed",
                        "available_at": "2026-11-01T12:30:00Z",  # Future revision
                    },
                ],
            }
        ]

        eligible, _ = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="15m",
        )
        assert len(eligible) == 1
        assert eligible[0]["version_number"] == 1
        assert eligible[0]["headline"] == "Binance Evaluates Maintenance"

    # 4. Future macro quarantine
    def test_adversarial_04_future_macro_quarantine(self):
        """Future scheduled macro releases must be quarantined from historical backtests."""
        boundary = NewsIntelligenceBoundary()
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)

        events = [
            {
                "macro_event_id": "macro_20261104_fomc_decision",
                "event_name": "Federal Reserve FOMC Rate Decision",
                "source": "federal_reserve",
                "event_category": "MACROECONOMIC",
                "actual_release_at": "2026-11-04T19:00:00Z",
                "first_observed_at": "2026-10-01T00:00:00Z",
                "collected_at": "2026-10-01T00:00:00Z",
                "relevance_classification": "MACRO",
            },
            {
                "macro_event_id": "macro_20261112_bls_cpi",
                "event_name": "US Consumer Price Index",
                "source": "bls",
                "event_category": "MACROECONOMIC",
                "actual_release_at": "2026-11-12T13:30:00Z",
                "first_observed_at": "2026-10-01T00:00:00Z",
                "collected_at": "2026-10-01T00:00:00Z",
                "relevance_classification": "MACRO",
            },
        ]

        eligible, excluded = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="15m",
        )
        assert len(eligible) == 0
        assert len(excluded) == 2
        for e in excluded:
            assert e["exclusion_reason"] == "FORWARD_SCHEDULED_EVENT_QUARANTINED"

    # 5. Missing provenance exclusion
    def test_adversarial_05_missing_provenance(self):
        """Macro events lacking observed/collected provenance must be rejected."""
        boundary = NewsIntelligenceBoundary()
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)

        events = [
            {
                "macro_event_id": "macro_20240802_bls_nfp",
                "event_name": "US BLS Employment Situation / NFP",
                "source": "bls",
                "event_category": "MACROECONOMIC",
                "actual_release_at": "2024-08-02T12:30:00Z",
                "first_observed_at": None,
                "collected_at": None,
                "relevance_classification": "MACRO",
            }
        ]

        eligible, excluded = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="15m",
        )
        assert len(eligible) == 0
        assert len(excluded) == 1
        assert excluded[0]["exclusion_reason"] == "MISSING_REQUIRED_PROVENANCE"

    # 6. GDELT intraday exclusion
    def test_adversarial_06_gdelt_intraday_exclusion(self):
        """GDELT records must be rejected on intraday simulations (< 1d)."""
        boundary = NewsIntelligenceBoundary()
        dt_close = datetime(2026, 11, 1, 12, 15, tzinfo=timezone.utc)

        events = [
            {
                "event_id": "gdelt_1",
                "source": "gdelt_gkg",
                "available_at": "2026-11-01T12:00:00Z",
                "affected_assets": ["BTC"],
                "relevance_classification": "MARKET_WIDE",
            }
        ]

        # 15m intraday: excluded
        eligible, excluded = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="15m",
        )
        assert len(eligible) == 0
        assert excluded[0]["exclusion_reason"] == "GDELT_SUB_DAILY_INTRADAY_PROHIBITED"

        # 1d daily horizon: eligible
        eligible_1d, _ = boundary.filter_events_at_decision_cutoff(
            events=events,
            symbol="BTCUSDT",
            candle_close_dt=dt_close,
            timeframe="1d",
        )
        assert len(eligible_1d) == 1

    # 7. Distinct events within 6 hours
    def test_adversarial_07_distinct_events_within_six_hours(self):
        """A time window alone must not merge distinct real-world events."""
        art1 = {
            "article_id": "art_staking",
            "title": "Binance Launches ETH Staking Yield Program",
            "url": "https://binance.com/eth-staking",
            "entities": ["ETH"],
            "published_at": "2024-07-10T10:00:00Z",
        }
        art2 = {
            "article_id": "art_roadmap",
            "title": "Vitalik Buterin Proposes Rollup Scaling Roadmap",
            "url": "https://coindesk.com/vitalik-roadmap",
            "entities": ["ETH"],
            "published_at": "2024-07-10T14:00:00Z",
        }

        is_dup, _, _ = are_articles_event_duplicates(art1, art2, max_time_delta_seconds=86400)
        assert is_dup is False

    # 8. Duplicate syndicated articles
    def test_adversarial_08_duplicate_syndicated_articles(self):
        """Syndicated wire reports sharing normalized titles must be clustered."""
        art1 = {
            "article_id": "art_source",
            "title": "Binance Adds New Trading Pairs for BTC and ETH",
            "url": "https://binance.com/announcement/123",
            "entities": ["BTC", "ETH"],
            "published_at": "2024-08-01T08:00:00Z",
        }
        art2 = {
            "article_id": "art_syndicated",
            "title": "Binance Adds New Trading Pairs for BTC and ETH",
            "url": "https://finance.yahoo.com/binance-adds-pairs-123.html",
            "entities": ["BTC", "ETH"],
            "published_at": "2024-08-01T12:00:00Z",
        }

        is_dup, conf, evidence = are_articles_event_duplicates(art1, art2)
        assert is_dup is True
        assert conf >= 0.95
        assert evidence["stage"] == "exact_normalized_title"

    # 9. Cost arithmetic precision
    def test_adversarial_09_cost_arithmetic_precision(self, execution_simulator):
        """Execution cost calculations must use Python Decimal with exact precision."""
        pos = execution_simulator.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("50000.00"),
            position_size=Decimal("0.01"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            signal_timestamp="2026-11-01T12:00:00Z",
            entry_timestamp="2026-11-01T12:15:00Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        assert isinstance(pos.entry_price, Decimal)
        assert isinstance(pos.entry_fee, Decimal)
        assert isinstance(pos.entry_slippage_cost, Decimal)
        assert isinstance(pos.entry_spread_cost, Decimal)

        # Expected price: 50000 * (1 + 0.0005 + 0.0001) = 50030.00
        assert pos.entry_price == Decimal("50030.00")
        assert pos.entry_slippage_cost == Decimal("0.25")
        assert pos.entry_spread_cost == Decimal("0.05")
        assert pos.entry_fee == Decimal("0.5003")

    # 10. No double-counted spread or slippage & cash conservation
    def test_adversarial_10_no_double_counted_spread_slippage(self, execution_simulator):
        """Delta cash must equal trade net_pnl within cent-rounding quantization."""
        raw_entry = Decimal("50000.00")
        raw_exit = Decimal("52000.00")
        size = Decimal("0.01")
        initial_cash = Decimal("1000.00")

        pos = execution_simulator.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=raw_entry,
            position_size=size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("53000.00"),
            signal_timestamp="2026-11-01T12:00:00Z",
            entry_timestamp="2026-11-01T12:15:00Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )
        cash_outflow = (pos.position_size * pos.entry_price) + pos.entry_fee
        cash_after_entry = initial_cash - cash_outflow

        trade = execution_simulator._finalize_trade(
            position=pos,
            exit_price_raw=raw_exit,
            exit_timestamp="2026-11-01T13:00:00Z",
            exit_reason="TAKE_PROFIT",
        )
        exit_notional = pos.position_size * trade.exit_price
        exit_fee = exit_notional * execution_simulator.taker_fee_pct
        cash_inflow = exit_notional - exit_fee
        cash_after_exit = cash_after_entry + cash_inflow

        delta_cash = cash_after_exit - initial_cash
        # Assert conservation holds to less than 0.01 cent display rounding
        assert abs(delta_cash - trade.net_pnl) < Decimal("0.01")

    # 11. Risk token tampering detection
    def test_adversarial_11_risk_token_tampering(self, risk_manager, execution_simulator, sample_signal):
        """Altering order quantity, symbol, or stop loss invalidates HMAC risk authorization."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
            run_id="run_alpha",
        )
        assert res.approved is True
        token = res.risk_approval_token
        assert token.startswith("rat_v1_")

        scheduler = PointInTimeExecutionScheduler(
            execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
            risk_manager=risk_manager,
        )

        # Schedule authentic order
        order = scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol=sample_signal.symbol,
            timeframe=sample_signal.timeframe,
            direction=sample_signal.direction,
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "run_alpha"},
        )

        # Adversarially tamper with order quantity
        order.position_size = Decimal("1.00000000")  # Inflate position size

        c_open = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=50020.0,
            high=50100.0,
            low=49950.0,
            close=50050.0,
            volume=50.0,
            is_closed=True,
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_open,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )

        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.REJECTED
        assert "Risk token verification failed" in terminal[0].rejection_reason

    # 12. Token replay prevention across orders
    def test_adversarial_12_token_replay_across_orders(self, risk_manager, execution_simulator, sample_signal):
        """Using a token authorized for Signal A on Signal B must be rejected."""
        res_a = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
            run_id="run_alpha",
        )

        scheduler = PointInTimeExecutionScheduler(risk_manager=risk_manager)
        # Attempt to use Token A on a different signal ID
        scheduler.schedule_order(
            signal_id="sig_different_002",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp="2026-11-01T12:00:00Z",
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res_a.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res_a.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "run_alpha"},
        )

        c_open = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=50020.0,
            high=50100.0,
            low=49950.0,
            close=50050.0,
            volume=50.0,
            is_closed=True,
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_open,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )

        assert len(filled) == 0
        assert len(terminal) == 1
        assert "Risk token verification failed" in terminal[0].rejection_reason

    # 13. Wrong-run token rejection
    def test_adversarial_13_wrong_run_token(self, risk_manager, execution_simulator, sample_signal):
        """Tokens bound to simulation run A cannot be executed in simulation run B."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
            run_id="run_first",
        )

        scheduler = PointInTimeExecutionScheduler(risk_manager=risk_manager)
        scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol=sample_signal.symbol,
            timeframe=sample_signal.timeframe,
            direction=sample_signal.direction,
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "run_second"},  # Wrong run
        )

        c_open = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=50020.0,
            high=50100.0,
            low=49950.0,
            close=50050.0,
            volume=50.0,
            is_closed=True,
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_open,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert "Risk token verification failed" in terminal[0].rejection_reason

    # 14. Execution after circuit-breaker activation
    def test_adversarial_14_execution_after_circuit_breaker(self, risk_manager, execution_simulator, sample_signal):
        """Drawdown circuit breaker active at candle open cancels scheduled orders."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
        )

        scheduler = PointInTimeExecutionScheduler(risk_manager=risk_manager)
        scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol=sample_signal.symbol,
            timeframe=sample_signal.timeframe,
            direction=sample_signal.direction,
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "default_run"},
        )

        c_open = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=50020.0,
            high=50100.0,
            low=49950.0,
            close=50050.0,
            volume=50.0,
            is_closed=True,
        )

        # Equity collapsed to 900 (10% drawdown > 5% max drawdown)
        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_open,
            current_open_positions=[],
            current_equity=Decimal("900.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert "Drawdown circuit breaker active" in terminal[0].rejection_reason

    # 15. Missing next eligible candle leaves order pending
    def test_adversarial_15_missing_next_candle(self, risk_manager, sample_signal):
        """When curr_candle belongs to another symbol, order remains safely pending."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
        )
        scheduler = PointInTimeExecutionScheduler(risk_manager=risk_manager)
        scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "default_run"},
        )

        # Next candle is for ETHUSDT, not BTCUSDT
        c_eth = ValidatedCandle(
            symbol="ETHUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=3000.0,
            high=3020.0,
            low=2990.0,
            close=3010.0,
            volume=10.0,
            is_closed=True,
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_eth,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=PaperExecutionSimulator(),
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 0
        assert len(scheduler.pending_orders) == 1

    # 16. Large execution data gap causes order expiry
    def test_adversarial_16_large_execution_gap(self, risk_manager, sample_signal):
        """Data gaps exceeding max_execution_gap_bars expire scheduled orders deterministically."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
        )
        scheduler = PointInTimeExecutionScheduler(max_execution_gap_bars=2, risk_manager=risk_manager)
        scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "default_run"},
        )

        # Gap of 5 hours (20 bars > 2 allowed bars)
        c_gap = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T17:15:00Z",
            open=51000.0,
            high=51200.0,
            low=50900.0,
            close=51100.0,
            volume=50.0,
            is_closed=True,
        )

        filled, terminal = scheduler.process_candle_open(
            curr_candle=c_gap,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=PaperExecutionSimulator(),
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled) == 0
        assert len(terminal) == 1
        assert terminal[0].status == OrderStatus.EXPIRED

    # 17. Duplicate order execution prevented
    def test_adversarial_17_duplicate_order_execution_prevented(self, risk_manager, execution_simulator, sample_signal):
        """A filled scheduled order is removed from pending_orders and never re-executed."""
        res = risk_manager.evaluate_signal(
            signal=sample_signal,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T12:15:00Z",
        )
        scheduler = PointInTimeExecutionScheduler(risk_manager=risk_manager)
        scheduler.schedule_order(
            signal_id=sample_signal.signal_id,
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            signal_timestamp=sample_signal.timestamp,
            candle_close_timestamp="2026-11-01T12:15:00Z",
            position_size=res.position_size,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_approval_token=res.risk_approval_token,
            market_regime="TRENDING_BULL",
            strategy_metadata={"entry_price": str(sample_signal.entry_price), "run_id": "default_run"},
        )

        c_open = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:30:00Z",
            open=50020.0,
            high=50100.0,
            low=49950.0,
            close=50050.0,
            volume=50.0,
            is_closed=True,
        )

        filled1, _ = scheduler.process_candle_open(
            curr_candle=c_open,
            current_open_positions=[],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled1) == 1
        assert len(scheduler.pending_orders) == 0

        # Subsequent step with another candle
        c_next = ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp="2026-11-01T12:45:00Z",
            open=50050.0,
            high=50150.0,
            low=50000.0,
            close=50120.0,
            volume=50.0,
            is_closed=True,
        )
        filled2, _ = scheduler.process_candle_open(
            curr_candle=c_next,
            current_open_positions=[filled1[0][1]],
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            execution_simulator=execution_simulator,
            max_concurrent_positions=2,
            max_drawdown_pct=Decimal("0.05"),
            daily_loss_limit_pct=Decimal("0.02"),
        )
        assert len(filled2) == 0

    # 18. Deterministic replay invariance
    @pytest.mark.asyncio
    async def test_adversarial_18_deterministic_replay(self):
        """Repeated simulation replay under NEXT_ELIGIBLE_PRICE produces identical results."""
        candles = []
        base = 50000.0
        start_dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        for i in range(80):
            cur_dt = start_dt + timedelta(minutes=15 * i)
            ts = cur_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            p = base + (i * 15.0) if i < 40 else base + 600.0 - ((i - 40) * 10.0)
            candles.append(
                ValidatedCandle(
                    symbol="BTCUSDT",
                    timeframe="15m",
                    timestamp=ts,
                    open=p - 5.0,
                    high=p + 15.0,
                    low=p - 15.0,
                    close=p,
                    volume=100.0,
                    is_closed=True,
                )
            )

        cfg = BacktestConfig(
            symbols=["BTCUSDT"],
            timeframe="15m",
            execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
            initial_capital=Decimal("1000.00"),
        )

        engine1 = HistoricalBacktestEngine(cfg)
        res1 = await engine1.run(candles_by_symbol={"BTCUSDT": candles})

        engine2 = HistoricalBacktestEngine(cfg)
        res2 = await engine2.run(candles_by_symbol={"BTCUSDT": candles})

        assert res1.metrics.net_profit == res2.metrics.net_profit
        assert res1.metrics.total_trades == res2.metrics.total_trades
        assert len(res1.equity_curve) == len(res2.equity_curve)
        for ep1, ep2 in zip(res1.equity_curve, res2.equity_curve):
            assert ep1.total_equity == ep2.total_equity
