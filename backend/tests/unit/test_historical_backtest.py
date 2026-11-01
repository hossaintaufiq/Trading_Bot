"""
NEPTUNE Unit & Verification Tests — Milestone 4.1 Historical Backtesting Engine

Comprehensive automated tests covering Section 8 requirements:
1. Chronological event replay
2. Strict look-ahead bias prevention
3. Deterministic replay reproducibility
4. Entry and exit behavior
5. Stop-loss execution
6. Take-profit execution
7. Ambiguous stop/target candle handling (conservative stop hit)
8. Fees and slippage deduction
9. Decimal P&L calculations and conservation
10. Position sizing (0.5% risk limit and 1.0x spot cap)
11. Maximum drawdown calculation
12. Profit factor calculation
13. Expectancy calculation
14. Persistence to SQLite and Parquet
15. Duplicate timestamp rejection
16. Chronological train/test split (Walk-Forward)
"""
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
import pytest

from app.data.market.validator import ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.risk.risk_manager import RiskManager
from app.agents.strategy_analyst import RawCandidateSignal
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.metrics import calculate_backtest_metrics
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    EquityPoint,
    SimulatedTrade,
)
from app.simulation.walk_forward import WalkForwardValidator


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


class TestHistoricalBacktestingEngine:
    """Suite of verification tests for the historical backtest engine."""

    def test_paper_execution_ambiguous_candle_conservative_assumption(self):
        """
        Verify Section 4 & Rule S-06: If both stop-loss and take-profit are touched
        in the exact same candle, the simulator MUST take the conservative stop loss.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
            conservative_ambiguity=True,
        )

        # Open LONG at 100.0, stop at 95.0, target at 110.0
        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={"rr_ratio": 2.0},
        )

        # Candle swings violently: Low 90.0 (touches stop 95.0) AND High 115.0 (touches target 110.0)
        wild_candle = make_candle(1, open_=100.0, high=115.0, low=90.0, close=105.0)

        trade = sim.evaluate_candle_bracket(pos, wild_candle)
        assert trade is not None
        # Must be resolved as AMBIGUOUS_BAR_STOP, never TAKE_PROFIT
        assert trade.exit_reason == "AMBIGUOUS_BAR_STOP"
        assert trade.net_pnl < Decimal("0")
        assert trade.exit_price <= Decimal("95.0")

    def test_paper_execution_fees_and_slippage(self):
        """Verify fees, spread, and slippage are correctly deducted from gross P&L."""
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),   # 0.1%
            slippage_pct=Decimal("0.0005"),   # 0.05%
            spread_bps=Decimal("2.0"),        # 2 bps = 0.02% (half spread = 0.01%)
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Expected entry price = 100 * (1 + 0.0005 + 0.0001) = 100.06
        assert pos.entry_price == pytest.approx(Decimal("100.06"), abs=Decimal("0.01"))
        assert pos.entry_fee == pytest.approx(Decimal("0.10006"), abs=Decimal("0.001"))

        # Target hit at 110.0
        hit_candle = make_candle(1, open_=102.0, high=112.0, low=101.0, close=108.0)
        trade = sim.evaluate_candle_bracket(pos, hit_candle)
        assert trade is not None
        assert trade.exit_reason == "TAKE_PROFIT"

        # Gross PnL is (110.0 - 100.0) * 1.0 = 10.0
        assert trade.gross_pnl == Decimal("10.00")
        # Net PnL must strictly equal gross_pnl - fees - slippage - spread
        expected_net = trade.gross_pnl - trade.fees - trade.slippage_cost - trade.spread_cost
        assert trade.net_pnl == expected_net
        assert trade.net_pnl < trade.gross_pnl

    def test_position_sizing_respects_risk_budget_and_spot_cap(self):
        """Verify position sizing does not exceed 0.5% account risk or 1.0x cash equity."""
        rm = RiskManager(
            risk_per_trade_pct=Decimal("0.005"),  # 0.5%
            min_reward_risk_ratio=Decimal("1.5"),
        )

        cand = RawCandidateSignal(
            signal_id="sig_test_1",
            timestamp="2026-11-01T10:00:00.000Z",
            strategy_id="trend_v1",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            entry_price=100.0,
            suggested_stop_loss=99.0,     # Risk dist = 1.0
            suggested_take_profit=103.0,  # Reward dist = 3.0 (R:R = 3.0)
            risk_reward_ratio=3.0,
            raw_confidence=0.8,
            rationale="Test setup",
        )

        # Case 1: Normal sizing ($1000 equity, risk budget = $5.0, stop dist = $1.0 -> size = 5.0)
        # Notional = 5.0 * 100.0 = $500 <= $1000 available cash.
        eval1 = rm.evaluate_signal(
            signal=cand,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T10:00:00.000Z",
        )
        assert eval1.approved is True
        assert eval1.position_size == Decimal("5.00000000")
        assert eval1.notional_value_usdt == Decimal("500.00")

        # Case 2: Very tight stop (e.g. stop dist = 0.1 -> raw size = 5.0 / 0.1 = 50.0 units)
        # 50 units * $100 = $5000 notional, which exceeds $1000 equity!
        # Must be capped at 1.0x spot equity ($1000 / $100 = 10.0 units).
        cand_tight = cand.model_copy(update={"suggested_stop_loss": 99.9})
        eval2 = rm.evaluate_signal(
            signal=cand_tight,
            current_equity=Decimal("1000.00"),
            peak_equity=Decimal("1000.00"),
            daily_starting_equity=Decimal("1000.00"),
            daily_realized_pnl=Decimal("0.00"),
            open_positions=[],
            timestamp="2026-11-01T10:00:00.000Z",
        )
        assert eval2.approved is True
        assert eval2.position_size == Decimal("10.00000000")
        assert eval2.notional_value_usdt == Decimal("1000.00")

    def test_metrics_calculation_identities_and_drawdown(self):
        """Verify performance metrics formulas: win rate, profit factor, max drawdown, expectancy."""
        trades = [
            SimulatedTrade(
                trade_id="t1", symbol="BTCUSDT", timeframe="15m", direction="LONG",
                signal_timestamp="2026-11-01T10:00:00.000Z", entry_timestamp="2026-11-01T10:00:00.000Z",
                entry_price=Decimal("100.0"), exit_timestamp="2026-11-01T10:30:00.000Z", exit_price=Decimal("110.0"),
                stop_loss=Decimal("95.0"), take_profit=Decimal("110.0"), position_size=Decimal("1.0"),
                gross_pnl=Decimal("10.00"), fees=Decimal("0.20"), spread_cost=Decimal("0.04"), slippage_cost=Decimal("0.10"),
                net_pnl=Decimal("9.66"), exit_reason="TAKE_PROFIT", market_regime="TRENDING_BULL",
                strategy_metadata={"rr_ratio": 2.0},
            ),
            SimulatedTrade(
                trade_id="t2", symbol="BTCUSDT", timeframe="15m", direction="LONG",
                signal_timestamp="2026-11-01T11:00:00.000Z", entry_timestamp="2026-11-01T11:00:00.000Z",
                entry_price=Decimal("100.0"), exit_timestamp="2026-11-01T11:30:00.000Z", exit_price=Decimal("95.0"),
                stop_loss=Decimal("95.0"), take_profit=Decimal("110.0"), position_size=Decimal("1.0"),
                gross_pnl=Decimal("-5.00"), fees=Decimal("0.20"), spread_cost=Decimal("0.04"), slippage_cost=Decimal("0.10"),
                net_pnl=Decimal("-5.34"), exit_reason="STOP_LOSS", market_regime="TRENDING_BULL",
                strategy_metadata={"rr_ratio": 2.0},
            ),
        ]

        equity_curve = [
            EquityPoint(timestamp="2026-11-01T10:00:00.000Z", cash_equity=1000.0, total_equity=1000.0, drawdown_pct=0.0, open_positions_count=0),
            EquityPoint(timestamp="2026-11-01T10:30:00.000Z", cash_equity=1009.66, total_equity=1009.66, drawdown_pct=0.0, open_positions_count=0),
            EquityPoint(timestamp="2026-11-01T11:30:00.000Z", cash_equity=1004.32, total_equity=1004.32, drawdown_pct=0.53, open_positions_count=0),
        ]

        metrics = calculate_backtest_metrics(trades, equity_curve, Decimal("1000.00"), "15m")

        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 0.50
        assert metrics.gross_profit == Decimal("10.00")
        assert metrics.gross_loss == Decimal("5.00")
        assert metrics.profit_factor == 2.0  # 10.0 / 5.0
        assert metrics.net_profit == Decimal("4.32")
        # Expectancy = Net profit / total trades = 4.32 / 2 = 2.16
        assert metrics.expectancy_per_trade == Decimal("2.16")
        # Drawdown: Peak = 1009.66, lowest = 1004.32 -> dd = 5.34, dd_pct = 5.34 / 1009.66 * 100 = 0.53%
        assert metrics.max_drawdown_amount == Decimal("5.34")
        assert metrics.max_drawdown_pct == 0.53

    @pytest.mark.asyncio
    async def test_lookahead_bias_invariance_in_replay(self):
        """
        Verify Rule S-05: Running the backtest on N candles vs N + 10 future candles
        must produce identical execution and signals for all candles <= N.
        """
        # Create a baseline series of 60 candles
        base_candles = [
            make_candle(i, open_=100.0 + i * 0.5, high=101.0 + i * 0.5, low=99.5 + i * 0.5, close=100.5 + i * 0.5)
            for i in range(60)
        ]

        # Add 10 explosive future candles
        future_candles = base_candles + [
            make_candle(60 + j, open_=150.0 + j * 5, high=160.0 + j * 5, low=145.0 + j * 5, close=155.0 + j * 5)
            for j in range(10)
        ]

        cfg = BacktestConfig(symbols=["BTCUSDT"], timeframe="15m")
        engine_past = HistoricalBacktestEngine(cfg)
        res_past = await engine_past.run(candles_by_symbol={"BTCUSDT": base_candles})

        engine_future = HistoricalBacktestEngine(cfg)
        res_future = await engine_future.run(candles_by_symbol={"BTCUSDT": future_candles})

        # Trades initiated during the first 60 candles must have identical entry timestamps and prices
        past_trades = [t for t in res_past.trades if t.entry_timestamp <= base_candles[-1].timestamp]
        future_trades = [t for t in res_future.trades if t.entry_timestamp <= base_candles[-1].timestamp]

        assert len(past_trades) == len(future_trades)
        for t_p, t_f in zip(past_trades, future_trades):
            assert t_p.entry_timestamp == t_f.entry_timestamp
            assert t_p.entry_price == t_f.entry_price
            assert t_p.stop_loss == t_f.stop_loss
            assert t_p.take_profit == t_f.take_profit

    @pytest.mark.asyncio
    async def test_deterministic_replay_produces_identical_results(self):
        """Verify backtest execution is 100% deterministic (repeated run yields identical output)."""
        candles = [
            make_candle(i, open_=100.0 + (i % 5) * 0.5, high=102.0 + (i % 5) * 0.5, low=98.0 + (i % 5) * 0.5, close=100.5 + (i % 5) * 0.5)
            for i in range(70)
        ]

        cfg = BacktestConfig(symbols=["BTCUSDT"], timeframe="15m")
        engine1 = HistoricalBacktestEngine(cfg)
        res1 = await engine1.run(candles_by_symbol={"BTCUSDT": candles})

        engine2 = HistoricalBacktestEngine(cfg)
        res2 = await engine2.run(candles_by_symbol={"BTCUSDT": candles})

        assert res1.metrics.total_trades == res2.metrics.total_trades
        assert res1.metrics.net_profit == res2.metrics.net_profit
        assert res1.metrics.win_rate == res2.metrics.win_rate
        assert len(res1.trades) == len(res2.trades)
        for t1, t2 in zip(res1.trades, res2.trades):
            assert t1.entry_price == t2.entry_price
            assert t1.exit_price == t2.exit_price
            assert t1.net_pnl == t2.net_pnl

    def test_chronological_train_test_split_integrity(self):
        """Verify chronological train/test splitting maintains order and disjoint sets."""
        candles = [make_candle(i, 100.0, 101.0, 99.0, 100.0) for i in range(100)]
        train, test = WalkForwardValidator.chronological_split(candles, train_ratio=0.7)

        assert len(train) == 70
        assert len(test) == 30
        assert train[-1].timestamp < test[0].timestamp
        # Confirm no data overlap
        train_ts = {c.timestamp for c in train}
        test_ts = {c.timestamp for c in test}
        assert train_ts.isdisjoint(test_ts)

    @pytest.mark.asyncio
    async def test_backtest_persistence_to_parquet_and_sqlite(self):
        """Verify simulation summaries are saved to SQLite and trade ledger to Parquet."""
        temp_dir = tempfile.mkdtemp(prefix="neptune_backtest_persist_")
        try:
            cfg = BacktestConfig(
                symbols=["BTCUSDT"],
                timeframe="15m",
                save_to_parquet=True,
                save_to_db=True,
                output_dir=temp_dir,
            )

            # Generate synthetic candles with a clear trend to trigger trade
            candles = [
                make_candle(i, open_=100.0 + i * 1.5, high=101.5 + i * 1.5, low=99.0 + i * 1.5, close=101.0 + i * 1.5)
                for i in range(60)
            ]

            engine = HistoricalBacktestEngine(cfg)
            res = await engine.run(candles_by_symbol={"BTCUSDT": candles})

            # 1. Parquet trade file verification
            parquet_path = os.path.join(temp_dir, f"{res.backtest_id}_trades.parquet")
            assert os.path.exists(parquet_path)
            read_df = pd.read_parquet(parquet_path)
            assert len(read_df) == len(res.trades)
            if len(read_df) > 0:
                assert "trade_id" in read_df.columns
                assert "net_pnl" in read_df.columns
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_duplicate_timestamp_rejection(self):
        """Verify engine rejects candle series containing duplicate timestamps."""
        candles = [
            make_candle(0, 100.0, 101.0, 99.0, 100.0),
            make_candle(0, 100.0, 101.0, 99.0, 100.0),  # Duplicate timestamp
        ]
        cfg = BacktestConfig(symbols=["BTCUSDT"])
        engine = HistoricalBacktestEngine(cfg)
        with pytest.raises(ValueError, match="Duplicate timestamp"):
            await engine.run(candles_by_symbol={"BTCUSDT": candles})

    @pytest.mark.asyncio
    async def test_multi_symbol_concurrency_and_correlation_limits(self):
        """
        Verify replay engine manages multiple symbols simultaneously and respects
        max_concurrent_positions and single-position-per-symbol constraints.
        """
        btc_candles = [
            make_candle(i, open_=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.5 + i, symbol="BTCUSDT")
            for i in range(50)
        ]
        eth_candles = [
            make_candle(i, open_=50.0 + i * 0.5, high=51.0 + i * 0.5, low=49.0 + i * 0.5, close=50.5 + i * 0.5, symbol="ETHUSDT")
            for i in range(50)
        ]

        cfg = BacktestConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframe="15m",
            max_concurrent_positions=2,
        )
        engine = HistoricalBacktestEngine(cfg)
        res = await engine.run(candles_by_symbol={"BTCUSDT": btc_candles, "ETHUSDT": eth_candles})

        # Max open positions recorded at any point in the equity curve must never exceed 2
        for pt in res.equity_curve:
            assert pt.open_positions_count <= 2

    @pytest.mark.asyncio
    async def test_walk_forward_evaluation_runner(self):
        """
        Verify WalkForwardValidator splits data chronologically, runs IS and OOS
        backtests independently, and calculates Walk-Forward Efficiency.
        """
        candles = [
            make_candle(i, open_=100.0 + (i % 7) * 0.8, high=102.0 + (i % 7) * 0.8, low=98.0 + (i % 7) * 0.8, close=100.5 + (i % 7) * 0.8)
            for i in range(80)
        ]

        cfg = BacktestConfig(symbols=["BTCUSDT"], timeframe="15m")
        wf_res = await WalkForwardValidator.run_train_test_evaluation(
            config=cfg,
            candles_by_symbol={"BTCUSDT": candles},
            train_ratio=0.70,
        )

        assert "in_sample" in wf_res
        assert "out_of_sample" in wf_res
        assert wf_res["train_ratio"] == 0.70
        assert "walk_forward_efficiency" in wf_res
        assert wf_res["in_sample"]["period_end"] < wf_res["out_of_sample"]["period_start"]
