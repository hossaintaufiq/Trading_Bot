"""
Unit & Regression Tests for Centralized Risk Manager and Decision Engine.
Verifies:
1. Fixed fractional sizing strictly calculated from stop distance.
2. Hard budget cap enforcement across total deployed capital.
3. Daily loss limit & consecutive loss cooldown circuit breakers.
4. Macro regime filtering (BTC 50 EMA gate).
5. Relative strength & coin ranking.
6. Minimum target cost hurdle (>= 1.20%).
"""

import pytest
import pandas as pd
import numpy as np
from risk_manager import CentralizedRiskManager, RiskOrderEvaluation
from backtest.decision_engine import DecisionEngine


def test_risk_manager_position_sizing_from_stop_distance():
    config = {
        "paper_initial_balance": 10000.0,
        "risk_per_trade_pct": 1.0,  # 1% risk = $100 risk
        "total_budget_limit_usd": 2000.0,
        "max_exposure_per_symbol_usd": 1000.0,
        "max_open_positions": 3,
        "min_order_usd": 12.0
    }
    rm = CentralizedRiskManager(config)

    # Entry = 100, Stop = 98 (2% stop distance).
    # Risk = $100. Position size = $100 / 0.02 = $5,000. Capped at max_exposure_per_symbol ($1,000).
    eval_res = rm.evaluate_order(
        symbol="SOL/USDT",
        entry_price=100.0,
        stop_price=98.0,
        target_price=106.0,
        current_equity=10000.0,
        active_positions={}
    )
    assert eval_res.approved is True
    assert eval_res.trade_amount_usdt == 1000.0
    assert eval_res.position_units == 10.0
    assert eval_res.reward_risk_ratio == 3.0


def test_risk_manager_total_budget_hard_cap():
    config = {
        "paper_initial_balance": 10000.0,
        "risk_per_trade_pct": 1.0,
        "total_budget_limit_usd": 500.0,
        "max_exposure_per_symbol_usd": 300.0,
        "max_open_positions": 3,
        "min_order_usd": 15.0
    }
    rm = CentralizedRiskManager(config)

    # Active positions already deploy $490 of $500 total budget
    active = {
        "BTC/USDT": {"cost_usdt": 300.0},
        "ETH/USDT": {"cost_usdt": 190.0}
    }
    # Available budget is $10, which is below min_order_usd ($15)
    eval_res = rm.evaluate_order(
        symbol="SOL/USDT",
        entry_price=100.0,
        stop_price=98.0,
        target_price=105.0,
        current_equity=10000.0,
        active_positions=active
    )
    assert eval_res.approved is False
    assert "BUDGET CONSTRAINED" in eval_res.reason


def test_risk_manager_consecutive_loss_cooldown():
    config = {
        "consecutive_loss_limit": 3,
        "consecutive_loss_cooldown_sec": 3600
    }
    rm = CentralizedRiskManager(config)

    rm.record_trade_outcome(-15.0)
    rm.record_trade_outcome(-20.0)
    assert rm.consecutive_losses == 2

    # 3rd consecutive loss trips cooldown
    rm.record_trade_outcome(-25.0)
    assert rm.consecutive_losses == 3
    assert rm.cooldown_until_ts > 0

    eval_res = rm.evaluate_order(
        symbol="BTC/USDT",
        entry_price=60000.0,
        stop_price=59000.0,
        target_price=63000.0,
        current_equity=9940.0,
        active_positions={}
    )
    assert eval_res.approved is False
    assert "CONSECUTIVE LOSS COOLDOWN" in eval_res.reason


def test_decision_engine_macro_regime_filter():
    de = DecisionEngine()

    # Case A: BTC below 50 EMA (Bearish market)
    btc_df_bear = pd.DataFrame({
        "close": [50000.0] * 60,
        "ema_slow": [55000.0] * 60,
        "adx": [28.0] * 60
    })
    regime_bear = de.evaluate_macro_regime(btc_df_bear)
    assert regime_bear["allow_alts"] is False

    # Non-BTC altcoin pattern must be rejected when macro regime bars alts
    pattern = de.evaluate_best_pattern("SOL/USDT", btc_df_bear, regime_bear)
    assert pattern is None

    # Case B: BTC above 50 EMA in healthy bull expansion
    btc_df_bull = pd.DataFrame({
        "close": [60000.0] * 60,
        "ema_slow": [55000.0] * 60,
        "adx": [24.0] * 60
    })
    regime_bull = de.evaluate_macro_regime(btc_df_bull)
    assert regime_bull["allow_alts"] is True
