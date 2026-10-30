"""
Regression and Verification Test Suite for Stage 1 Bug Fixes (Bugs 1 - 8).
Validates fixes to:
1. learning_engine.py setup_id tracking & learning attribution
2. strategies.py NeptuneFleetStrategy exit routing via setup_id
3. strategies.py & bot_engine.py explicit stop/target/invalidation/holding parameters & rejection gate
4. strategies.py ORBStrategy session anchor & daily reset
5. bot_engine.py closed-candle requirement & timestamp deduplication
6. bot_engine.py ATR-based trailing stop with +1R activation & break-even ratchet
7. bot_engine.py centralized exit evaluator priority hierarchy
8. bot_engine.py correlated altcoin exposure cap
"""

import os
import json
import time
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from learning_engine import LocalLearningEngine
from paper_exchange import PaperExchange
from strategies import (
    Signal,
    ORBStrategy,
    BullFlagStrategy,
    OversoldBounceStrategy,
    MAReclaimStrategy,
    BollingerRangeHunterStrategy,
    EMARSIStrategy,
    NeptuneFleetStrategy
)
from indicators import enrich_dataframe
from bot_engine import BotEngine


def _make_dummy_candle(t_sec, open_p, high_p, low_p, close_p, vol=100.0, is_closed=True):
    return {
        "time": int(t_sec),
        "open": float(open_p),
        "high": float(high_p),
        "low": float(low_p),
        "close": float(close_p),
        "volume": float(vol),
        "is_closed": is_closed
    }


def _make_dummy_df(num_bars=50, base_price=100.0, trend=0.0):
    rows = []
    start_t = 1700000000
    p = base_price
    for i in range(num_bars):
        p += trend + (np.sin(i / 5.0) * 0.5)
        high_p = p + 0.8
        low_p = p - 0.8
        rows.append({
            "time": start_t + (i * 60),
            "open": p - 0.1,
            "high": high_p,
            "low": low_p,
            "close": p,
            "volume": 200.0 + (i * 2.0),
            "is_closed": True
        })
    df = pd.DataFrame(rows)
    return enrich_dataframe(df)


# ==============================================================================
# BUG 1 REGRESSION TEST: setup_id tracking in learning engine & paper exchange
# ==============================================================================
def test_bug1_setup_id_tracking(tmp_path):
    mem_file = tmp_path / "test_memory.json"
    engine = LocalLearningEngine(storage_path=str(mem_file))

    # Test identify_setup_key recognition
    assert engine.identify_setup_key("Bull Flag Breakout", "Bull Flag") == "bull_flag"
    assert engine.identify_setup_key("20-MA Reclaimed", "20-MA Reclaim") == "reclaim_ma20"
    assert engine.identify_setup_key("ORB Breakout", "ORB Breakout") == "orb"
    assert engine.identify_setup_key("Oversold Bounce", "Oversold Bounce") == "oversold_bounce"
    assert engine.identify_setup_key("Range Hunter", "Range Hunter") == "bollinger_reversion"

    # Test closed trade ingestion with explicit setup_id
    trade_bf = {
        "id": "TRD-1",
        "symbol": "BTC/USDT",
        "setup_id": "bull_flag",
        "realized_pnl": 5.0,
        "realized_pnl_pct": 5.0,
        "reason": "Bracket Stop Exit"  # generic exit string that previously defaulted to ema_rsi
    }
    engine.record_closed_trade(trade_bf)

    assert engine.memory["setups"]["bull_flag"]["trades"] == 1
    assert engine.memory["setups"]["bull_flag"]["wins"] == 1
    assert engine.memory["setups"]["ema_rsi"]["trades"] == 0  # Did NOT pollute ema_rsi!

    # Test PaperExchange preserves setup_id from entry through exit
    pe_state = tmp_path / "test_pe.json"
    pex = PaperExchange(state_file=str(pe_state))
    pex.learning_engine = engine
    pex.execute_buy(
        symbol="ETH/USDT",
        market_price=3000.0,
        usdt_amount=100.0,
        reason="20-MA Reclaim",
        setup_id="reclaim_ma20"
    )
    assert pex.positions["ETH/USDT"]["setup_id"] == "reclaim_ma20"

    sell_res = pex.execute_sell("ETH/USDT", 3100.0, "Bracket Target Hit")
    assert sell_res["success"] is True
    assert pex.trades_history[0]["setup_id"] == "reclaim_ma20"
    assert engine.memory["setups"]["reclaim_ma20"]["trades"] == 1


# ==============================================================================
# BUG 2 REGRESSION TEST: NeptuneFleetStrategy exit routing via setup_id
# ==============================================================================
def test_bug2_fleet_exit_routing():
    fleet = NeptuneFleetStrategy(config={"strategies": {}})

    df = _make_dummy_df(num_bars=35, base_price=50000.0)

    # 1. ORB position test: When price drops below orb_mid, ORB strategy triggers SELL
    pos_orb = {
        "symbol": "BTC/USDT",
        "setup_id": "orb",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "reason": "Bracket Stop Exit"  # doesn't contain 'orb' in string
    }
    # Configure ORB sub_bot with a known session range
    orb_bot = next(b for b in fleet.sub_bots if b.name == "orb")
    orb_bot.session_range = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "high": 51000.0,
        "low": 49000.0,
        "mid": 50000.0,
        "range_pct": 4.0
    }

    # If df last price is below orb_mid (49500 < 50000)
    df.loc[df.index[-1], "close"] = 49500.0
    sig = fleet.evaluate(df, pos_orb)
    assert sig.action == "SELL"
    assert "ORB Invalidated" in sig.reason

    # 2. Bull flag position test: When price drops below flag_low, Bull Flag triggers SELL
    pos_bf = {
        "symbol": "BTC/USDT",
        "setup_id": "bull_flag",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "reason": "Fleet Position Entry"
    }
    # Make flag low higher than last price to trigger invalidation
    df.loc[df.index[-1], "close"] = 48000.0
    sig_bf = fleet.evaluate(df, pos_bf)
    assert sig_bf.action == "SELL"
    assert "Bull Flag Support Lost" in sig_bf.reason


# ==============================================================================
# BUG 3 REGRESSION TEST: Explicit exit parameters & rejection gate
# ==============================================================================
def test_bug3_signal_exit_parameters_and_gate(tmp_path):
    df = _make_dummy_df(num_bars=60, base_price=100.0)

    # Check that individual strategies define stop, target, invalidation, max_holding_bars
    strategies = [
        EMARSIStrategy({}),
        BullFlagStrategy({}),
        ORBStrategy({}),
        OversoldBounceStrategy({}),
        MAReclaimStrategy({}),
        BollingerRangeHunterStrategy({})
    ]

    for strat in strategies:
        sig = strat.evaluate(df, position=None)
        if sig.action == "BUY":
            assert sig.stop_price is not None, f"{strat.name} BUY signal missing stop_price"
            assert sig.target_price is not None, f"{strat.name} BUY signal missing target_price"
            assert sig.invalidation_price is not None, f"{strat.name} BUY signal missing invalidation_price"
            assert sig.max_holding_bars is not None, f"{strat.name} BUY signal missing max_holding_bars"
            assert sig.stop_price < sig.price, f"{strat.name} stop_price must be below entry"
            assert sig.target_price > sig.price, f"{strat.name} target_price must be above entry"

    # Test rejection gate in BotEngine
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({"max_correlated_positions": 2}, f)

    engine = BotEngine(config_path=str(config_file))
    engine.paper_exchange.state_file = str(tmp_path / "pe_state.json")
    engine.markets["SOL/USDT"] = {"current_price": 100.0, "klines_df": df}

    # Signal missing stop_price must be REJECTED
    bad_sig_no_stop = Signal("BUY", 100.0, "Test", 0.9, "test", "test", stop_price=None, target_price=110.0)
    import asyncio
    asyncio.run(engine._process_strategy_signal_for_symbol("SOL/USDT", bad_sig_no_stop, df))
    assert "SOL/USDT" not in engine.paper_exchange.positions

    # Signal with invalid stop (stop >= current_price) must be REJECTED
    bad_sig_inverted = Signal("BUY", 100.0, "Test", 0.9, "test", "test", stop_price=105.0, target_price=110.0)
    asyncio.run(engine._process_strategy_signal_for_symbol("SOL/USDT", bad_sig_inverted, df))
    assert "SOL/USDT" not in engine.paper_exchange.positions


# ==============================================================================
# BUG 4 REGRESSION TEST: ORB session anchor & daily reset
# ==============================================================================
def test_bug4_orb_session_anchor_and_reset():
    orb = ORBStrategy({"opening_range_minutes": 15})

    # Day 1: 2026-01-01 00:00 to 01:00 UTC (1m candles)
    base_t = int(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    day1_candles = []
    for i in range(40):
        t = base_t + i * 60
        # In first 15 mins (0 to 14): high is 105, low is 95
        if i < 15:
            high_p = 105.0 if i == 5 else 102.0
            low_p = 95.0 if i == 10 else 98.0
        else:
            # Later bars make higher highs / lower lows - these should NOT alter opening range!
            high_p = 120.0
            low_p = 80.0
        day1_candles.append(_make_dummy_candle(t, 100.0, high_p, low_p, 101.0))

    df1 = enrich_dataframe(pd.DataFrame(day1_candles))
    sig1 = orb.evaluate(df1)

    assert orb.session_date == "2026-01-01"
    assert orb.session_range is not None
    assert orb.session_range["high"] == 105.0
    assert orb.session_range["low"] == 95.0
    assert orb.session_range["mid"] == 100.0

    # Day 2: Advance to 2026-01-02 00:16 UTC
    day2_t = int(datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    day2_candles = []
    for i in range(20):
        t = day2_t + i * 60
        # Day 2 range: high 210, low 190
        high_p = 210.0 if i == 3 else 202.0
        low_p = 190.0 if i == 8 else 195.0
        day2_candles.append(_make_dummy_candle(t, 200.0, high_p, low_p, 201.0))

    df2 = enrich_dataframe(pd.DataFrame(day2_candles))
    sig2 = orb.evaluate(df2)

    # Must have reset to Day 2
    assert orb.session_date == "2026-01-02"
    assert orb.session_range["high"] == 210.0
    assert orb.session_range["low"] == 190.0
    assert orb.session_range["mid"] == 200.0


# ==============================================================================
# BUG 5 REGRESSION TEST: Closed-candle gating & timestamp deduplication
# ==============================================================================
def test_bug5_closed_candle_deduplication(tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({
            "max_correlated_positions": 5,
            "paper_state_path": str(tmp_path / "pe_state.json")
        }, f)

    engine = BotEngine(config_path=str(config_file))
    engine.paper_exchange.state_file = str(tmp_path / "pe_state.json")
    engine.is_running = True
    engine.status = "RUNNING"

    df = _make_dummy_df(num_bars=30, base_price=100.0)
    engine.markets["BTC/USDT"] = {"current_price": 100.0, "klines_df": df}

    import asyncio

    # 1. Intrabar unclosed candle (is_closed=False)
    unclosed_candle = _make_dummy_candle(1700000000 + 3600, 100.0, 102.0, 99.0, 101.5, is_closed=False)
    asyncio.run(engine.handle_candle_update("BTC/USDT", unclosed_candle))
    # Must NOT update last_closed_candle_time
    assert "BTC/USDT" not in engine.last_closed_candle_time

    # 2. Closed candle (is_closed=True)
    closed_candle = _make_dummy_candle(1700000000 + 3600, 100.0, 102.0, 99.0, 101.5, is_closed=True)
    asyncio.run(engine.handle_candle_update("BTC/USDT", closed_candle))
    assert engine.last_closed_candle_time["BTC/USDT"] == 1700000000 + 3600

    # 3. Duplicate closed candle with same timestamp
    # Artificially track calls to _process_strategy_signal_for_symbol
    call_count = 0
    orig_process = engine._process_strategy_signal_for_symbol
    async def mock_process(sym, sig, d):
        nonlocal call_count
        call_count += 1
    engine._process_strategy_signal_for_symbol = mock_process

    asyncio.run(engine.handle_candle_update("BTC/USDT", closed_candle))
    assert call_count == 0  # Ignored duplicate closed candle!

    # 4. New closed candle with incremented timestamp
    new_candle = _make_dummy_candle(1700000000 + 3660, 101.5, 103.0, 101.0, 102.5, is_closed=True)
    asyncio.run(engine.handle_candle_update("BTC/USDT", new_candle))
    assert call_count == 1
    assert engine.last_closed_candle_time["BTC/USDT"] == 1700000000 + 3660


# ==============================================================================
# BUG 6 REGRESSION TEST: ATR trailing stop with +1R activation & BE ratchet
# ==============================================================================
def test_bug6_atr_trailing_stop_ratchet(tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({
            "trailing_stop_enabled": True,
            "atr_trail_multiplier": 1.5,
            "fee_slippage_buffer_pct": 0.30
        }, f)

    engine = BotEngine(config_path=str(config_file))

    # Entry = 100.0, Initial Stop = 98.0 -> 1R = 2.0. ATR = 1.0.
    pos = {
        "symbol": "BTC/USDT",
        "entry_price": 100.0,
        "initial_stop_price": 98.0,
        "stop_loss_price": 98.0,
        "take_profit_price": 110.0,
        "highest_price": 100.0,
        "entry_time": int(time.time() * 1000)
    }

    # Case A: Price reaches 101.0 (< 1R). Trailing stop should NOT activate.
    exit_msg = engine.evaluate_position_exit("BTC/USDT", pos, current_price=101.0, current_atr=1.0)
    assert exit_msg is None
    assert pos["stop_loss_price"] == 98.0  # Stop unchanged

    # Case B: Price reaches 102.50 (> 1R). Trailing stop activates!
    # Break-even ratchet: 100 * 1.003 = 100.30.
    # ATR trail: 102.50 - 1.5 * 1.0 = 101.00.
    # Stop ratchets up to max(100.30, 101.00) = 101.00.
    exit_msg = engine.evaluate_position_exit("BTC/USDT", pos, current_price=102.50, current_atr=1.0)
    assert exit_msg is None
    assert pos["stop_loss_price"] >= 100.30  # Locked break-even + fee buffer
    assert pos["stop_loss_price"] == 101.00

    # Case C: Price pulls back slightly from 102.50 to 101.80.
    # Stop can NEVER move down.
    exit_msg = engine.evaluate_position_exit("BTC/USDT", pos, current_price=101.80, current_atr=1.0)
    assert exit_msg is None
    assert pos["stop_loss_price"] == 101.00  # Stop did NOT move down

    # Case D: Price drops to 100.90 (<= 101.00). Trailing stop triggers exit!
    exit_msg = engine.evaluate_position_exit("BTC/USDT", pos, current_price=100.90, current_atr=1.0)
    assert exit_msg is not None
    assert "ATR Trailing Stop Hit" in exit_msg


# ==============================================================================
# BUG 7 REGRESSION TEST: Centralized exit priority hierarchy
# ==============================================================================
def test_bug7_centralized_exit_priority(tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({"trailing_stop_enabled": True}, f)

    engine = BotEngine(config_path=str(config_file))

    # Priority 1: Hard Stop-Loss Hit
    pos_sl = {
        "symbol": "BTC/USDT",
        "entry_price": 100.0,
        "stop_loss_price": 97.0,
        "take_profit_price": 105.0,
        "highest_price": 100.0,
        "entry_time": int(time.time() * 1000)
    }
    # Price is 96.0 (below stop_loss_price)
    exit_sl = engine.evaluate_position_exit("BTC/USDT", pos_sl, current_price=96.0, current_atr=1.0)
    assert "Stop-Loss Hit" in exit_sl

    # Priority 2: Take-Profit Target Hit
    pos_tp = {
        "symbol": "BTC/USDT",
        "entry_price": 100.0,
        "stop_loss_price": 97.0,
        "take_profit_price": 105.0,
        "highest_price": 104.0,
        "entry_time": int(time.time() * 1000)
    }
    # Price is 106.0 (above take_profit_price)
    exit_tp = engine.evaluate_position_exit("BTC/USDT", pos_tp, current_price=106.0, current_atr=1.0)
    assert "Take-Profit Target Hit" in exit_tp

    # Priority 4: Max Holding Duration Exceeded
    pos_time = {
        "symbol": "BTC/USDT",
        "entry_price": 100.0,
        "stop_loss_price": 95.0,
        "take_profit_price": 115.0,
        "highest_price": 100.0,
        "max_holding_bars": 10,
        "entry_time": int(time.time() * 1000) - (20 * 60 * 1000)  # 20 bars ago
    }
    exit_time = engine.evaluate_position_exit("BTC/USDT", pos_time, current_price=100.5, current_atr=1.0)
    assert "Max Holding Bars Exceeded" in exit_time


# ==============================================================================
# BUG 8 REGRESSION TEST: Correlated altcoin exposure cap
# ==============================================================================
def test_bug8_correlation_exposure_cap(tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({
            "max_correlated_positions": 2,
            "total_budget_limit_usd": 10000.0,
            "max_open_positions": 5,
            "max_trade_amount_usdt": 100.0,
            "paper_state_path": str(tmp_path / "pe_state.json")
        }, f)

    engine = BotEngine(config_path=str(config_file))
    engine.paper_exchange.state_file = str(tmp_path / "pe_state.json")
    engine.markets["ETH/USDT"] = {"current_price": 3000.0}
    engine.markets["SOL/USDT"] = {"current_price": 150.0}
    engine.markets["BNB/USDT"] = {"current_price": 600.0}
    engine.markets["BTC/USDT"] = {"current_price": 60000.0}

    # Simulate 2 active altcoin positions
    engine.paper_exchange.positions["ETH/USDT"] = {"symbol": "ETH/USDT", "entry_price": 3000.0, "quantity": 0.1, "cost_usdt": 300.0}
    engine.paper_exchange.positions["SOL/USDT"] = {"symbol": "SOL/USDT", "entry_price": 150.0, "quantity": 1.0, "cost_usdt": 150.0}

    df = _make_dummy_df(num_bars=30, base_price=600.0)
    sig_alt = Signal("BUY", 600.0, "Breakout", 0.9, "test", "test", stop_price=580.0, target_price=640.0)

    import asyncio
    # 3rd altcoin (BNB/USDT) must be REJECTED due to correlation cap
    asyncio.run(engine._process_strategy_signal_for_symbol("BNB/USDT", sig_alt, df))
    assert "BNB/USDT" not in engine.paper_exchange.positions

    # BTC/USDT is the base asset and must NOT be blocked by altcoin correlation cap
    df_btc = _make_dummy_df(num_bars=30, base_price=60000.0)
    sig_btc = Signal("BUY", 60000.0, "Breakout", 0.9, "test", "test", stop_price=59000.0, target_price=62000.0)
    asyncio.run(engine._process_strategy_signal_for_symbol("BTC/USDT", sig_btc, df_btc))
    assert "BTC/USDT" in engine.paper_exchange.positions
