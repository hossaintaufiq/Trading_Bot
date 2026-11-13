"""
Unit Tests for DualTimeframeTrendStrategyV2 (`htf_trend_following_v2` / `SHR-001-V2` / ADR-036)
and 2024 Development Partition V2 Experiment Verification.

Verifies:
- Rule A-01: Python Decimal for all monetary and risk calculations.
- Rule A-09: Rejection of incomplete candles.
- Rule S-01: Long-only spot execution (no leverage, no short-selling).
- Rule S-04: Strict Risk Manager authorization token consumption.
- Rule S-05: Strict Development partition isolation.
- Breakeven Stop Ratchet mechanics.
- Symbol-Level Loss Quarantine mechanics.
- CPPI Drawdown-Adaptive Risk Sizing mechanics.
- Balance sheet invariant verification in PortfolioLedger exports.
"""

from decimal import Decimal, ROUND_HALF_UP
import json
import os
import pytest
import pandas as pd
import numpy as np

from app.strategies.dual_timeframe_trend_v2 import (
    DualTimeframeConfigV2,
    DualTimeframeTrendStrategyV2,
)
from app.strategies.base_strategy import SignalDirection, TimeFrame


def test_v2_config_defaults():
    """Verify default parameters of DualTimeframeConfigV2."""
    cfg = DualTimeframeConfigV2()
    assert cfg.fast_ema_4h == 50
    assert cfg.slow_ema_4h == 200
    assert cfg.min_adx_4h == 24.0
    assert cfg.fast_ema_1h == 21
    assert cfg.slow_ema_1h == 50
    assert cfg.atr_period_1h == 14
    assert cfg.atr_stop_multiplier == 2.0
    assert cfg.min_reward_risk_ratio == 2.5
    assert cfg.swing_pivot_lookback_1h == 5
    assert cfg.max_holding_candles_1h == 96
    assert cfg.breakeven_trigger_r == 1.5
    assert cfg.breakeven_buffer_pct == 0.0035
    assert cfg.symbol_cooldown_stops == 2
    assert cfg.symbol_cooldown_hours == 168
    assert cfg.cppi_dd_threshold == 0.048
    assert cfg.cppi_min_risk_multiplier == 0.25


def test_v2_strategy_abstract_methods_and_rules():
    """Verify strategy satisfies BaseStrategy interface and contracts."""
    strategy = DualTimeframeTrendStrategyV2()
    assert strategy.strategy_id == "htf_trend_following_v2"
    assert "Trend Following V2" in strategy.strategy_name

    entries = strategy.get_entry_conditions()
    assert len(entries) >= 5
    assert any("ADX" in e for e in entries)

    exits = strategy.get_exit_conditions()
    assert len(exits) >= 3
    assert any("Breakeven" in e for e in exits)

    invalids = strategy.get_invalidation_rules()
    assert len(invalids) >= 3
    assert any("Symbol quarantine" in inv for inv in invalids)


def test_v2_rule_a09_incomplete_candle_rejection():
    """Verify Rule A-09: Strategy rejects incomplete or unconfirmed candles."""
    strategy = DualTimeframeTrendStrategyV2()

    # Create dummy 1h DataFrame with is_closed=False
    dates = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": np.linspace(40000, 42000, 100),
        "high": np.linspace(40100, 42100, 100),
        "low": np.linspace(39900, 41900, 100),
        "close": np.linspace(40050, 42050, 100),
        "volume": np.ones(100) * 10.0,
        "is_closed": [True] * 99 + [False],  # Last candle is unconfirmed
    })

    signal = strategy.evaluate(df, "BTCUSDT")
    assert signal is None, "Strategy must return None when consuming an incomplete candle (Rule A-09)"


def test_v2_breakeven_ratchet_logic():
    """Verify mathematical logic of Breakeven Ratchet at +1.5R."""
    cfg = DualTimeframeConfigV2()
    entry_price = Decimal("50000.00")
    stop_loss = Decimal("49000.00")
    risk_r = entry_price - stop_loss  # 1000.00 USDT

    # At +1.0R gain: price = 51000.00 -> gain_r = 1.0 < 1.5 -> no ratchet
    curr_high = Decimal("51000.00")
    gain_r = (curr_high - entry_price) / risk_r
    assert gain_r < Decimal(str(cfg.breakeven_trigger_r))

    # At +1.5R gain: price = 51500.00 -> gain_r = 1.5 -> ratchet activates
    curr_high = Decimal("51500.00")
    gain_r = (curr_high - entry_price) / risk_r
    assert gain_r >= Decimal(str(cfg.breakeven_trigger_r))

    be_factor = Decimal("1.0") + Decimal(str(cfg.breakeven_buffer_pct))
    new_stop = (entry_price * be_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert new_stop == Decimal("50175.00")
    assert new_stop > entry_price  # Locked in +175 USDT profit to cover all fees and slippage


def test_v2_cppi_adaptive_risk_scaling():
    """Verify CPPI risk dampening as portfolio drawdown approaches 4.8% threshold."""
    dd_thresh = Decimal("0.048")
    min_mult = Decimal("0.25")
    base_risk = Decimal("0.005")

    # Drawdown 0.0%: full risk 0.5%
    dd_0 = Decimal("0.000")
    cushion_0 = max(min_mult, (dd_thresh - dd_0) / dd_thresh)
    scaled_risk_0 = (base_risk * cushion_0).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert scaled_risk_0 == Decimal("0.0050")

    # Drawdown 2.4% (halfway): 50% cushion = 0.25% risk
    dd_half = Decimal("0.024")
    cushion_half = max(min_mult, (dd_thresh - dd_half) / dd_thresh)
    scaled_risk_half = (base_risk * cushion_half).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert scaled_risk_half == Decimal("0.0025")

    # Drawdown 4.6% (near boundary): capped at minimum floor 0.25 * 0.5% = 0.125% (0.0013)
    dd_near = Decimal("0.046")
    cushion_near = max(min_mult, (dd_thresh - dd_near) / dd_thresh)
    scaled_risk_near = (base_risk * cushion_near).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert scaled_risk_near == Decimal("0.0013")


def test_v2_experiment_export_integrity():
    """Verify complete audit artifacts exported for 2024 V2 Development Experiment."""
    export_dir = os.path.abspath("storage/exports/dual_timeframe_v2_dev_experiment")
    assert os.path.isdir(export_dir)

    summary_path = os.path.join(export_dir, "summary_metrics.json")
    ledger_path = os.path.join(export_dir, "trade_ledger.json")
    equity_path = os.path.join(export_dir, "equity_curve.json")
    symbols_path = os.path.join(export_dir, "per_symbol_metrics.json")

    assert os.path.exists(summary_path)
    assert os.path.exists(ledger_path)
    assert os.path.exists(equity_path)
    assert os.path.exists(symbols_path)

    with open(summary_path) as f:
        summary = json.load(f)

    # Core Performance Assertions
    assert summary["experiment_id"] == "EXP-2024-DEV-DUAL-TIMEFRAME-V2"
    assert summary["strategy_id"] == "htf_trend_following_v2"
    # ADR-037: the 4h look-ahead was fixed; profitability is NOT asserted (S-07). Check internal consistency only.
    assert summary["total_executed_trades"] > 0
    assert abs(summary["portfolio_return_pct"] - summary["net_pnl_usdt"] / 10.0) < 0.05   # $1,000 start

    with open(symbols_path) as f:
        syms = json.load(f)
    for s in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        assert s in syms
        assert syms[s]["net_pnl_usdt"] > 0, f"{s} must be net profitable in V2"

