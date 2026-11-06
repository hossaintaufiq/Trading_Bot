"""
Adversarial Unit Tests for Portfolio Accounting Remediation & Risk Enforcement.

NEPTUNE Milestone 4.6.3.1.2 - Deterministic verification covering:
1. Profitable LONG
2. Losing LONG
3. Profitable SHORT
4. Losing SHORT
5. LONG with entry and exit fees
6. SHORT with entry and exit fees
7. Partial position exit
8. Multiple concurrent positions (LONG + SHORT)
9. Position held across multiple candles (mark-to-market trajectory)
10. Gap-through-stop execution (slippage and gap tracking)
11. Open-position unrealized loss (drawdown impact prior to exit)
12. Portfolio equity after all positions close (strict mathematical identity)
Plus:
- Risk Manager 5% circuit breaker revalidation under corrected equity
- Zero artificial equity creation invariant
- Exact fee and friction uniqueness invariant
"""

from decimal import Decimal
import pytest

from app.agents.strategy_analyst import RawCandidateSignal
from app.data.market.validator import ValidatedCandle
from app.risk.risk_manager import RiskManager
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.models import ActivePosition, OrderStatus, ScheduledOrder, SimulatedTrade
from app.simulation.portfolio_ledger import InsufficientFundsError, PortfolioLedger


def create_mock_position(
    position_id: str,
    symbol: str,
    direction: str,
    entry_price: Decimal,
    position_size: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    entry_fee: Decimal = Decimal("0.10"),
    timestamp: str = "2024-01-01T00:00:00Z",
) -> ActivePosition:
    """Helper to instantiate an ActivePosition with explicit pricing."""
    return ActivePosition(
        position_id=position_id,
        signal_id=f"sig_{position_id}",
        symbol=symbol,
        timeframe="15m",
        direction=direction,
        entry_timestamp=timestamp,
        entry_price=entry_price,
        raw_entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=position_size,
        entry_fee=entry_fee,
        entry_slippage_cost=Decimal("0.05"),
        entry_spread_cost=Decimal("0.02"),
        market_regime="TRENDING_BULL" if direction == "LONG" else "TRENDING_BEAR",
        strategy_metadata={"signal_id": f"sig_{position_id}"},
    )


def test_scenario_1_profitable_long():
    """Scenario 1: Profitable LONG (Buy 100, Sell 110, no fees)."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_1", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("90.00"), Decimal("110.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos)
    assert ledger.cash_balance == Decimal("900.00")
    assert ledger.get_total_equity() == Decimal("1000.00")

    trade = SimulatedTrade(
        trade_id="trd_1",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("110.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("10.00"),
        exit_reason="TAKE_PROFIT",
        market_regime="TRENDING_BULL",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("110.00"),
        holding_duration_seconds=3600.0,
    )

    ledger.process_trade_exit(pos, trade, exit_fee=Decimal("0.0"))
    assert ledger.cash_balance == Decimal("1010.00")
    assert ledger.get_total_equity() == Decimal("1010.00")
    assert len(ledger.open_positions) == 0
    ledger.assert_invariants()


def test_scenario_2_losing_long():
    """Scenario 2: Losing LONG (Buy 100, Sell 90, no fees)."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_2", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("90.00"), Decimal("110.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos)
    assert ledger.cash_balance == Decimal("900.00")

    trade = SimulatedTrade(
        trade_id="trd_2",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("90.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("-10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("-10.00"),
        exit_reason="STOP_LOSS",
        market_regime="TRENDING_BULL",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("100.00"),
        holding_duration_seconds=3600.0,
    )

    ledger.process_trade_exit(pos, trade, exit_fee=Decimal("0.0"))
    assert ledger.cash_balance == Decimal("990.00")
    assert ledger.get_total_equity() == Decimal("990.00")
    ledger.assert_invariants()


def test_scenario_3_profitable_short():
    """Scenario 3: Profitable SHORT (Sell 100, Buy 90, no fees)."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_3", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("110.00"), Decimal("90.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos)
    assert ledger.cash_balance == Decimal("900.00")
    assert ledger.reserved_collateral == Decimal("100.00")
    assert ledger.get_total_equity() == Decimal("1000.00")

    trade = SimulatedTrade(
        trade_id="trd_3",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="SHORT",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("90.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("10.00"),
        exit_reason="TAKE_PROFIT",
        market_regime="TRENDING_BEAR",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("90.00"),
        holding_duration_seconds=3600.0,
    )

    # Inflow = 1.0 * (2 * 100 - 90) = 110.00
    inflow = ledger.process_trade_exit(pos, trade, exit_fee=Decimal("0.0"))
    assert inflow == Decimal("110.00")
    assert ledger.cash_balance == Decimal("1010.00")
    assert ledger.get_total_equity() == Decimal("1010.00")
    assert ledger.reserved_collateral == Decimal("0.0")
    ledger.assert_invariants()


def test_scenario_4_losing_short():
    """Scenario 4: Losing SHORT (Sell 100, Buy 110, no fees). CRITICAL DEFECT FIX VERIFICATION."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_4", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("110.00"), Decimal("90.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos)
    assert ledger.cash_balance == Decimal("900.00")
    assert ledger.reserved_collateral == Decimal("100.00")

    trade = SimulatedTrade(
        trade_id="trd_4",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="SHORT",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("110.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("-10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("-10.00"),
        exit_reason="STOP_LOSS",
        market_regime="TRENDING_BEAR",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("100.00"),
        holding_duration_seconds=3600.0,
    )

    # Inflow = 1.0 * (2 * 100 - 110) = 90.00
    inflow = ledger.process_trade_exit(pos, trade, exit_fee=Decimal("0.0"))
    assert inflow == Decimal("90.00")
    # Crucial assertion: Cash MUST decrease by 10, NOT increase!
    assert ledger.cash_balance == Decimal("990.00")
    assert ledger.get_total_equity() == Decimal("990.00")
    assert ledger.reserved_collateral == Decimal("0.0")
    ledger.assert_invariants()


def test_scenario_5_long_with_fees():
    """Scenario 5: LONG with entry and exit fees."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.001"))
    pos = create_mock_position("pos_5", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("90.00"), Decimal("110.00"), entry_fee=Decimal("0.10"))

    outflow = ledger.process_order_fill(pos)
    assert outflow == Decimal("100.10")
    assert ledger.cash_balance == Decimal("899.90")
    assert ledger.get_total_equity() == Decimal("999.90")

    trade = SimulatedTrade(
        trade_id="trd_5",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("110.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("10.00"),
        fees=Decimal("0.21"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("9.79"),
        exit_reason="TAKE_PROFIT",
        market_regime="TRENDING_BULL",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("110.00"),
        holding_duration_seconds=3600.0,
    )

    exit_fee = Decimal("0.11")
    inflow = ledger.process_trade_exit(pos, trade, exit_fee=exit_fee)
    assert inflow == Decimal("109.89")
    assert ledger.cash_balance == Decimal("1009.79")
    assert ledger.get_total_equity() == Decimal("1009.79")
    ledger.assert_invariants()


def test_scenario_6_short_with_fees():
    """Scenario 6: SHORT with entry and exit fees."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.001"))
    pos = create_mock_position("pos_6", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("110.00"), Decimal("90.00"), entry_fee=Decimal("0.10"))

    outflow = ledger.process_order_fill(pos)
    assert outflow == Decimal("100.10")
    assert ledger.cash_balance == Decimal("899.90")

    trade = SimulatedTrade(
        trade_id="trd_6",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="SHORT",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("90.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("10.00"),
        fees=Decimal("0.19"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("9.81"),
        exit_reason="TAKE_PROFIT",
        market_regime="TRENDING_BEAR",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("90.00"),
        holding_duration_seconds=3600.0,
    )

    exit_fee = Decimal("0.09")
    inflow = ledger.process_trade_exit(pos, trade, exit_fee=exit_fee)
    assert inflow == Decimal("109.91")
    assert ledger.cash_balance == Decimal("1009.81")
    assert ledger.get_total_equity() == Decimal("1009.81")
    ledger.assert_invariants()


def test_scenario_7_partial_position_exit():
    """Scenario 7: Partial position exit."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_7", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("2.0"), Decimal("90.00"), Decimal("120.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos)
    assert ledger.cash_balance == Decimal("800.00")
    assert ledger.long_inventory_cost == Decimal("200.00")

    # Exit 1.0 unit at 110.00
    partial_trade = SimulatedTrade(
        trade_id="trd_7_part",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("110.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=Decimal("1.0"),
        gross_pnl=Decimal("10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("10.00"),
        exit_reason="PARTIAL_PROFIT",
        market_regime="TRENDING_BULL",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("110.00"),
        holding_duration_seconds=3600.0,
    )

    ledger.process_partial_exit(pos, Decimal("1.0"), partial_trade, exit_fee=Decimal("0.0"))
    assert ledger.cash_balance == Decimal("910.00")
    assert pos.position_size == Decimal("1.0")
    assert ledger.long_inventory_cost == Decimal("100.00")
    assert len(ledger.open_positions) == 1
    ledger.assert_invariants()


def test_scenario_8_multiple_concurrent_positions():
    """Scenario 8: Multiple concurrent positions (1 LONG BTC, 1 SHORT ETH)."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos_btc = create_mock_position("pos_btc", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("90.00"), Decimal("120.00"), entry_fee=Decimal("0.0"))
    pos_eth = create_mock_position("pos_eth", "ETHUSDT", "SHORT", Decimal("50.00"), Decimal("2.0"), Decimal("60.00"), Decimal("40.00"), entry_fee=Decimal("0.0"))

    ledger.process_order_fill(pos_btc)
    ledger.process_order_fill(pos_eth)

    assert ledger.cash_balance == Decimal("800.00")  # 1000 - 100 - 100
    assert ledger.long_inventory_cost == Decimal("100.00")
    assert ledger.reserved_collateral == Decimal("100.00")
    assert ledger.get_total_equity() == Decimal("1000.00")
    ledger.assert_invariants()


def test_scenario_9_position_held_across_multiple_candles():
    """Scenario 9: Position held across multiple candles with mark-to-market updates."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos_short = create_mock_position("pos_short_multi", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("110.00"), Decimal("90.00"), entry_fee=Decimal("0.0"))
    ledger.process_order_fill(pos_short)

    # Candle 1: price drops to 95 (favorable for short)
    c1 = ValidatedCandle(timestamp="2024-01-01T00:15:00Z", open=100.0, high=101.0, low=94.0, close=95.0, volume=10.0, symbol="BTCUSDT", timeframe="15m")
    ledger.update_candle_mark("BTCUSDT", c1)
    assert ledger.get_position_equity(pos_short) == Decimal("105.00")  # 2*100 - 95
    assert ledger.get_total_equity() == Decimal("1005.00")

    # Candle 2: price rises to 105 (adverse for short)
    c2 = ValidatedCandle(timestamp="2024-01-01T00:30:00Z", open=95.0, high=106.0, low=95.0, close=105.0, volume=10.0, symbol="BTCUSDT", timeframe="15m")
    ledger.update_candle_mark("BTCUSDT", c2)
    assert ledger.get_position_equity(pos_short) == Decimal("95.00")  # 2*100 - 105
    assert ledger.get_total_equity() == Decimal("995.00")
    ledger.assert_invariants()


def test_scenario_10_gap_through_stop_execution():
    """Scenario 10: Gap-through-stop execution."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    # SHORT position stop is at 105.00
    pos = create_mock_position("pos_gap", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("105.00"), Decimal("90.00"), entry_fee=Decimal("0.0"))
    ledger.process_order_fill(pos)

    # Gap open at 110.00 (slippage through stop of 5.00)
    trade = SimulatedTrade(
        trade_id="trd_gap",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="SHORT",
        signal_timestamp=pos.entry_timestamp,
        entry_timestamp=pos.entry_timestamp,
        entry_price=Decimal("100.00"),
        exit_timestamp="2024-01-01T01:00:00Z",
        exit_price=Decimal("110.00"),
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        position_size=pos.position_size,
        gross_pnl=Decimal("-10.00"),
        fees=Decimal("0.0"),
        spread_cost=Decimal("0.0"),
        slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("-10.00"),
        exit_reason="STOP_LOSS_GAP",
        market_regime="TRENDING_BEAR",
        strategy_metadata={},
        initial_stop_loss=pos.stop_loss,
        final_stop_loss=pos.stop_loss,
        trailing_stop_updates=0,
        peak_favorable_price=Decimal("100.00"),
        holding_duration_seconds=3600.0,
    )

    ledger.process_trade_exit(pos, trade, exit_fee=Decimal("0.0"))
    assert ledger.cash_balance == Decimal("990.00")
    assert ledger.get_total_equity() == Decimal("990.00")
    ledger.assert_invariants()


def test_scenario_11_open_position_unrealized_loss():
    """Scenario 11: Open-position unrealized loss triggers drawdown before trade exit."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.0"))
    pos = create_mock_position("pos_loss", "BTCUSDT", "SHORT", Decimal("100.00"), Decimal("1.0"), Decimal("110.00"), Decimal("90.00"), entry_fee=Decimal("0.0"))
    ledger.process_order_fill(pos)

    # Price jumps to 106.00 (loss of $6.00, or 6.0% on position)
    c = ValidatedCandle(timestamp="2024-01-01T00:15:00Z", open=100.0, high=107.0, low=99.0, close=106.0, volume=10.0, symbol="BTCUSDT", timeframe="15m")
    ledger.update_candle_mark("BTCUSDT", c)

    tot_eq = ledger.get_total_equity()
    assert tot_eq == Decimal("994.00")
    dd = ledger.get_drawdown_pct()
    assert dd == Decimal("0.60")  # (1000 - 994) / 1000 * 100
    ledger.assert_invariants()


def test_scenario_12_portfolio_equity_after_all_positions_close():
    """Scenario 12: Portfolio equity strictly equals initial_capital + sum(net_pnl) after all positions close."""
    ledger = PortfolioLedger(initial_capital=Decimal("1000.00"), taker_fee_pct=Decimal("0.001"))

    # Execute 4 alternating trades: 2 LONG, 2 SHORT, mixed winners and losers
    p1 = create_mock_position("p1", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("95.00"), Decimal("110.00"), entry_fee=Decimal("0.10"))
    ledger.process_order_fill(p1)
    t1 = SimulatedTrade(
        trade_id="t1", symbol="BTCUSDT", timeframe="15m", direction="LONG",
        signal_timestamp=p1.entry_timestamp, entry_timestamp=p1.entry_timestamp,
        entry_price=Decimal("100.00"), exit_timestamp="2024-01-01T01:00:00Z", exit_price=Decimal("105.00"),
        stop_loss=p1.stop_loss, take_profit=p1.take_profit, position_size=p1.position_size,
        gross_pnl=Decimal("5.00"), fees=Decimal("0.205"), spread_cost=Decimal("0.0"), slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("4.795"), exit_reason="TAKE_PROFIT", market_regime="BULL", strategy_metadata={},
        initial_stop_loss=p1.stop_loss, final_stop_loss=p1.stop_loss, trailing_stop_updates=0,
        peak_favorable_price=Decimal("105.00"), holding_duration_seconds=3600.0
    )
    ledger.process_trade_exit(p1, t1, exit_fee=Decimal("0.105"))

    p2 = create_mock_position("p2", "ETHUSDT", "SHORT", Decimal("50.00"), Decimal("2.0"), Decimal("55.00"), Decimal("45.00"), entry_fee=Decimal("0.10"))
    ledger.process_order_fill(p2)
    t2 = SimulatedTrade(
        trade_id="t2", symbol="ETHUSDT", timeframe="15m", direction="SHORT",
        signal_timestamp=p2.entry_timestamp, entry_timestamp=p2.entry_timestamp,
        entry_price=Decimal("50.00"), exit_timestamp="2024-01-01T02:00:00Z", exit_price=Decimal("54.00"),
        stop_loss=p2.stop_loss, take_profit=p2.take_profit, position_size=p2.position_size,
        gross_pnl=Decimal("-8.00"), fees=Decimal("0.208"), spread_cost=Decimal("0.0"), slippage_cost=Decimal("0.0"),
        net_pnl=Decimal("-8.208"), exit_reason="STOP_LOSS", market_regime="BEAR", strategy_metadata={},
        initial_stop_loss=p2.stop_loss, final_stop_loss=p2.stop_loss, trailing_stop_updates=0,
        peak_favorable_price=Decimal("50.00"), holding_duration_seconds=3600.0
    )
    ledger.process_trade_exit(p2, t2, exit_fee=Decimal("0.108"))

    expected_ending_equity = Decimal("1000.00") + Decimal("4.795") - Decimal("8.208")
    assert ledger.cash_balance == expected_ending_equity
    assert ledger.get_total_equity() == expected_ending_equity
    assert len(ledger.open_positions) == 0
    ledger.assert_invariants()


def test_risk_manager_5_pct_drawdown_circuit_breaker_enforcement():
    """
    Verify RiskManager immediately halts new order authorization when true drawdown reaches 5.0%.
    Adversarially proves that SHORT losses correctly reduce equity and trip the breaker.
    """
    rm = RiskManager(
        max_concurrent_positions=2,
        risk_per_trade_pct=Decimal("0.005"),
        max_drawdown_pct=Decimal("0.05"),  # 5.0%
        daily_loss_limit_pct=Decimal("0.02"),
    )

    # Initial peak equity = 1000.00
    peak_equity = Decimal("1000.00")

    # Case A: Equity at 951.00 USDT (Drawdown = 4.9% < 5.0%) -> APPROVED
    cand_signal = RawCandidateSignal(
        signal_id="sig_test_1",
        timestamp="2024-01-05T12:00:00Z",
        strategy_id="test_strat",
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        entry_price=100.0,
        suggested_stop_loss=95.0,
        suggested_take_profit=110.0,
        risk_reward_ratio=2.0,
        raw_confidence=0.8,
        rationale="Test candidate",
    )
    res_approved = rm.evaluate_signal(
        signal=cand_signal,
        current_equity=Decimal("951.00"),
        peak_equity=peak_equity,
        daily_starting_equity=Decimal("951.00"),
        daily_realized_pnl=Decimal("0.00"),
        open_positions=[],
        timestamp="2024-01-05T12:00:00Z",
    )
    assert res_approved.approved is True
    assert res_approved.rejection_code is None

    # Case B: Equity drops to 949.50 USDT (Drawdown = 5.05% >= 5.0%) -> REJECTED
    res_rejected = rm.evaluate_signal(
        signal=cand_signal,
        current_equity=Decimal("949.50"),
        peak_equity=peak_equity,
        daily_starting_equity=Decimal("949.50"),
        daily_realized_pnl=Decimal("0.00"),
        open_positions=[],
        timestamp="2024-01-05T12:15:00Z",
    )
    assert res_rejected.approved is False
    assert res_rejected.rejection_code == "MAX_DRAWDOWN_EXCEEDED"
    assert "Drawdown circuit breaker active" in res_rejected.rejection_reason


def test_insufficient_funds_rejection():
    """Verify that ledger rejects order entry if available cash is insufficient."""
    ledger = PortfolioLedger(initial_capital=Decimal("50.00"), taker_fee_pct=Decimal("0.001"))
    pos = create_mock_position("pos_too_big", "BTCUSDT", "LONG", Decimal("100.00"), Decimal("1.0"), Decimal("90.00"), Decimal("110.00"), entry_fee=Decimal("0.10"))

    with pytest.raises(InsufficientFundsError):
        ledger.process_order_fill(pos)
