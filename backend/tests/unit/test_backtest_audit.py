"""
NEPTUNE Unit & Integrity Tests — Milestone 4.1.1 Independent Backtesting Audit

Tests:
1. Double-entry cash accounting conservation (Finding 1)
2. Bid-ask spread single-application verification (Finding 2)
3. Take-profit resting limit order cap against unearned gap windfall (Finding 3)
4. Temporal isolation of signal generation vs execution (Look-Ahead Bias Guard)
5. Comprehensive metrics edge cases (Zero trades, zero losses, zero variance)
"""
from decimal import Decimal
import pytest

from app.data.market.validator import ValidatedCandle
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.metrics import calculate_backtest_metrics
from app.simulation.models import ActivePosition, BacktestConfig, EquityPoint, SimulatedTrade


def make_audit_candle(i: int, open_: float, high: float, low: float, close: float) -> ValidatedCandle:
    return ValidatedCandle(
        symbol="BTCUSDT",
        timeframe="15m",
        timestamp=f"2026-11-01T{10 + (i // 4):02d}:{(i % 4) * 15:02d}:00.000Z",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        is_closed=True,
    )


class TestBacktestingIntegrityAudit:
    """Rigorous mathematical and temporal verification suite."""

    def test_audit_finding_1_double_entry_cash_accounting_conservation(self):
        """
        Verify mathematical conservation of cash:
        Final Cash - Initial Cash must equal Net P&L to the exact penny.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),    # 0.1%
            slippage_pct=Decimal("0.0005"),    # 0.05%
            spread_bps=Decimal("2.0"),         # 2 bps (half spread = 0.01%)
        )

        initial_cash = Decimal("1000.00")
        entry_raw = Decimal("100.00")
        size = Decimal("2.0")

        # 1. Entry
        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=entry_raw,
            position_size=size,
            stop_loss=Decimal("95.00"),
            take_profit=Decimal("110.00"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Expected entry price = 100 * (1 + 0.0005 + 0.0001) = 100.06
        expected_exec_entry = Decimal("100.06")
        assert pos.entry_price == pytest.approx(expected_exec_entry, abs=Decimal("0.0001"))
        entry_notional = pos.entry_price * size
        entry_fee = entry_notional * Decimal("0.001")

        cash_outflow = entry_notional + entry_fee
        cash_after_entry = initial_cash - cash_outflow

        # 2. While position is open: Total Equity = Cash + (size * mark_price)
        # Immediately upon entry at mark = 100.00:
        mark_equity = cash_after_entry + (size * entry_raw)
        # Difference from initial cash is exactly entry friction (slippage + spread + fee)
        assert mark_equity < initial_cash
        assert (initial_cash - mark_equity) == pytest.approx(
            pos.entry_slippage_cost + pos.entry_spread_cost + pos.entry_fee, abs=Decimal("0.01")
        )

        # 3. Exit at 110.00
        candle_exit = make_audit_candle(1, open_=105.0, high=112.0, low=104.0, close=109.0)
        trade = sim.evaluate_candle_bracket(pos, candle_exit)
        assert trade is not None

        # Cash inflow at exit:
        exit_notional = size * trade.exit_price
        exit_fee = exit_notional * Decimal("0.001")
        cash_inflow = exit_notional - exit_fee
        final_cash = cash_after_entry + cash_inflow

        # Fundamental conservation law: final_cash - initial_cash == trade.net_pnl
        actual_delta_cash = (final_cash - initial_cash).quantize(Decimal("0.01"))
        assert actual_delta_cash == trade.net_pnl

    def test_audit_finding_2_spread_not_double_counted(self):
        """
        Verify bid-ask spread and slippage are isolated and neither is double-counted.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),    # 0.05%
            spread_bps=Decimal("4.0"),         # 4 bps -> half-spread = 0.02% = 0.0002
        )

        raw_price = Decimal("200.00")
        size = Decimal("1.0")

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=raw_price,
            position_size=size,
            stop_loss=Decimal("190.00"),
            take_profit=Decimal("220.00"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Pure slippage = 200 * 0.0005 = 0.10
        assert pos.entry_slippage_cost == Decimal("0.1000")
        # Pure half-spread = 200 * 0.0002 = 0.04
        assert pos.entry_spread_cost == Decimal("0.0400")
        # Total price delta from raw = 0.10 + 0.04 = 0.14
        assert (pos.entry_price - raw_price) * size == Decimal("0.1400")

    def test_audit_finding_3_take_profit_capped_at_target_price(self):
        """
        Verify resting limit order take-profit exits cap at the target price,
        preventing unrealistic unearned favorable fills when market gaps above target.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("2.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.00"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.00"),
            take_profit=Decimal("110.00"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
        )

        # Market opens above target at 115.0 and trades up to 120.0
        gap_candle = make_audit_candle(1, open_=115.0, high=120.0, low=114.0, close=118.0)
        trade = sim.evaluate_candle_bracket(pos, gap_candle)

        assert trade is not None
        assert trade.exit_reason == "TAKE_PROFIT"
        # Must cap at target 110.00 minus friction, NOT gap open 115.00!
        expected_exit_exec = Decimal("110.00") * (Decimal("1") - Decimal("0.0005") - Decimal("0.0001"))
        assert trade.exit_price == pytest.approx(expected_exit_exec, abs=Decimal("0.01"))
        assert trade.gross_pnl == Decimal("10.00")  # (110 - 100) * 1.0

    @pytest.mark.asyncio
    async def test_audit_lookahead_temporal_isolation(self):
        """
        Verify a position entered at candle T close CANNOT be stopped out or take profit
        using price movement that occurred during candle T itself.
        """
        # Candle 0: low is 90.0, but close is 100.0 (signals Long with Stop = 95.0)
        c0 = make_audit_candle(0, open_=98.0, high=101.0, low=90.0, close=100.0)
        # Candle 1: normal trading, low 98.0, high 102.0
        c1 = make_audit_candle(1, open_=100.0, high=102.0, low=98.0, close=101.0)

        cfg = BacktestConfig(symbols=["BTCUSDT"], timeframe="15m")
        engine = HistoricalBacktestEngine(cfg)

        # Run engine with these two candles
        res = await engine.run(candles_by_symbol={"BTCUSDT": [c0, c1]})

        # If a trade entered at c0 close, it must NOT have been stopped out on c0's low of 90.0!
        for t in res.trades:
            if t.entry_timestamp == c0.timestamp:
                assert t.exit_timestamp != c0.timestamp

    def test_audit_metrics_edge_cases(self):
        """Verify performance metrics handling for zero trades, all wins, all losses, flat equity."""
        # 1. Zero trades
        m_zero = calculate_backtest_metrics([], [], Decimal("1000.00"), "15m")
        assert m_zero.total_trades == 0
        assert m_zero.win_rate == 0.0
        assert m_zero.profit_factor == 0.0
        assert m_zero.sharpe_ratio == 0.0

        # 2. 100% win rate (zero losses)
        win_trade = SimulatedTrade(
            trade_id="t_win", symbol="BTCUSDT", timeframe="15m", direction="LONG",
            signal_timestamp="2026-11-01T10:00:00.000Z", entry_timestamp="2026-11-01T10:00:00.000Z",
            entry_price=Decimal("100.0"), exit_timestamp="2026-11-01T10:30:00.000Z", exit_price=Decimal("110.0"),
            stop_loss=Decimal("95.0"), take_profit=Decimal("110.0"), position_size=Decimal("1.0"),
            gross_pnl=Decimal("10.00"), fees=Decimal("0.20"), spread_cost=Decimal("0.02"), slippage_cost=Decimal("0.10"),
            net_pnl=Decimal("9.68"), exit_reason="TAKE_PROFIT", market_regime="TRENDING_BULL",
        )
        m_all_wins = calculate_backtest_metrics([win_trade], [], Decimal("1000.00"), "15m")
        assert m_all_wins.win_rate == 1.0
        assert m_all_wins.losing_trades == 0
        assert m_all_wins.gross_loss == Decimal("0.00")
        assert m_all_wins.profit_factor == 999.0
        assert m_all_wins.average_loss == Decimal("0.00")

        # 3. Flat equity curve (zero variance)
        flat_eq = [
            EquityPoint(timestamp=f"2026-11-01T{i:02d}:00:00.000Z", cash_equity=1000.0, total_equity=1000.0, drawdown_pct=0.0, open_positions_count=0)
            for i in range(10)
        ]
        m_flat = calculate_backtest_metrics([], flat_eq, Decimal("1000.00"), "15m")
        assert m_flat.sharpe_ratio == 0.0
        assert m_flat.sortino_ratio == 0.0
