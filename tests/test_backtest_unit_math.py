"""
Unit tests with hand-calculated expected PnL for trading costs, slippage,
and the conservative stop/target ordering rule.
"""

import pytest
import pandas as pd
import numpy as np


def compute_trade_pnl(entry_tick: float, exit_tick: float, usdt_allocated: float, fee_pct: float, slippage_pct: float):
    """
    Exact mathematical trade PnL calculation matching live execution.
    - Buy execution price: entry_tick * (1 + slippage_pct / 100)
    - Buy fee deducted from cash: fee_buy = usdt_allocated * (fee_pct / 100)
    - Net USDT deployed: net_usdt = usdt_allocated - fee_buy
    - Quantity purchased: qty = net_usdt / buy_execution_price
    - Sell execution price: exit_tick * (1 - slippage_pct / 100)
    - Gross proceeds: gross_proceeds = qty * sell_execution_price
    - Sell fee: fee_sell = gross_proceeds * (fee_pct / 100)
    - Net proceeds: net_proceeds = gross_proceeds - fee_sell
    - Net PnL: realized_pnl = net_proceeds - usdt_allocated
    """
    buy_px = entry_tick * (1.0 + slippage_pct / 100.0)
    buy_fee = usdt_allocated * (fee_pct / 100.0)
    net_usdt = usdt_allocated - buy_fee
    qty = net_usdt / buy_px

    sell_px = exit_tick * (1.0 - slippage_pct / 100.0)
    gross_proceeds = qty * sell_px
    sell_fee = gross_proceeds * (fee_pct / 100.0)
    net_proceeds = gross_proceeds - sell_fee

    net_pnl = net_proceeds - usdt_allocated
    total_fees = buy_fee + sell_fee
    return {
        "buy_px": buy_px,
        "sell_px": sell_px,
        "qty": qty,
        "buy_fee": buy_fee,
        "sell_fee": sell_fee,
        "total_fees": total_fees,
        "net_proceeds": net_proceeds,
        "net_pnl": net_pnl
    }


def test_hand_calculated_winning_trade():
    """
    Hand-calculated winning trade:
    Entry: $100.00, Exit: $102.00 (+2.00% price move)
    Allocated: $100.00
    Fee: 0.10%, Slippage: 0.05%
    """
    # Manual steps:
    # 1. Buy:
    #    buy_px = 100.00 * (1 + 0.0005) = 100.05
    #    buy_fee = 100.00 * 0.001 = $0.10
    #    net_usdt = 100.00 - 0.10 = $99.90
    #    qty = 99.90 / 100.05 = 0.998500749625...
    # 2. Sell:
    #    sell_px = 102.00 * (1 - 0.0005) = 101.949
    #    gross_proceeds = 0.998500749625 * 101.949 = 101.796152923...
    #    sell_fee = 101.796152923 * 0.001 = 0.10179615...
    #    net_proceeds = 101.796152923 - 0.10179615... = 101.69435677...
    # 3. Net PnL:
    #    net_pnl = 101.69435677 - 100.00 = +$1.69435677
    res = compute_trade_pnl(100.0, 102.0, 100.0, fee_pct=0.1, slippage_pct=0.05)
    assert abs(res["buy_px"] - 100.05) < 1e-6
    assert abs(res["sell_px"] - 101.949) < 1e-6
    assert abs(res["buy_fee"] - 0.10) < 1e-6
    assert abs(res["net_pnl"] - 1.69435677) < 1e-4
    assert abs(res["total_fees"] - 0.201796) < 1e-4


def test_hand_calculated_losing_trade():
    """
    Hand-calculated losing trade:
    Entry: $100.00, Exit: $98.50 (-1.50% stop loss)
    Allocated: $100.00
    Fee: 0.10%, Slippage: 0.05%
    """
    # Manual steps:
    # 1. Buy:
    #    buy_px = 100.05, net_usdt = 99.90, qty = 0.998500749625...
    # 2. Sell:
    #    sell_px = 98.50 * 0.9995 = 98.45075
    #    gross_proceeds = 0.998500749625 * 98.45075 = 98.30314282...
    #    sell_fee = 98.30314282 * 0.001 = 0.09830314...
    #    net_proceeds = 98.30314282 - 0.09830314 = 98.20483968...
    # 3. Net PnL:
    #    net_pnl = 98.20483968 - 100.00 = -$1.7951603...
    res = compute_trade_pnl(100.0, 98.50, 100.0, fee_pct=0.1, slippage_pct=0.05)
    assert abs(res["net_pnl"] - (-1.7951603)) < 1e-4
    assert abs(res["total_fees"] - 0.198303) < 1e-4


def test_conservative_stop_target_ordering_rule():
    """
    When a single candle touches BOTH stop_price and target_price:
    Conservative rule mandates: STOP LOSS HITS FIRST.
    """
    stop_price = 98.0
    target_price = 104.0
    candle = {
        "open": 100.0,
        "high": 105.0,  # Target exceeded (105 >= 104)
        "low": 97.0,    # Stop breached (97 <= 98)
        "close": 103.0
    }

    # Simulate ordering rule
    def resolve_candle_exit(pos, bar):
        sl = pos["stop_loss"]
        tp = pos["take_profit"]
        hit_sl = bar["low"] <= sl
        hit_tp = bar["high"] >= tp

        if hit_sl and hit_tp:
            # Conservative: assume stop hits first
            return "STOP_LOSS", sl
        elif hit_sl:
            return "STOP_LOSS", sl
        elif hit_tp:
            return "TAKE_PROFIT", tp
        return None, None

    pos = {"stop_loss": stop_price, "take_profit": target_price}
    exit_type, exit_price = resolve_candle_exit(pos, candle)

    assert exit_type == "STOP_LOSS"
    assert exit_price == stop_price


def test_bnb_fee_discount_hand_calculation():
    """
    BNB fee discount case: 0.075% fee per side (instead of 0.10%).
    Entry: $100.00, Exit: $102.00
    """
    res_std = compute_trade_pnl(100.0, 102.0, 100.0, fee_pct=0.10, slippage_pct=0.05)
    res_bnb = compute_trade_pnl(100.0, 102.0, 100.0, fee_pct=0.075, slippage_pct=0.05)

    # Fee savings: (0.10 - 0.075)% * ~$200 round trip = ~$0.05 savings
    fee_saved = res_std["total_fees"] - res_bnb["total_fees"]
    assert abs(fee_saved - 0.0504) < 1e-3
    assert res_bnb["net_pnl"] > res_std["net_pnl"]

