"""
NEPTUNE Backtest Performance Metrics (`metrics.py`)

Deterministic calculations for portfolio performance, risk-adjusted returns,
drawdowns, expectancy, and multi-dimensional breakdowns (by symbol, timeframe, regime).
Formulas adhere strictly to quantitative standards and avoid floating-point drift.
"""
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
import numpy as np

from app.simulation.models import BacktestMetrics, EquityPoint, SimulatedTrade


def calculate_backtest_metrics(
    trades: List[SimulatedTrade],
    equity_curve: List[EquityPoint],
    initial_capital: Decimal,
    timeframe: str = "15m",
) -> BacktestMetrics:
    """
    Compute comprehensive quantitative performance metrics from a trade ledger and equity curve.
    """
    total_trades = len(trades)

    if total_trades == 0:
        return BacktestMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            gross_profit=Decimal("0.00"),
            gross_loss=Decimal("0.00"),
            net_profit=Decimal("0.00"),
            total_fees=Decimal("0.00"),
            total_slippage=Decimal("0.00"),
            total_spread=Decimal("0.00"),
            average_win=Decimal("0.00"),
            average_loss=Decimal("0.00"),
            win_loss_ratio=0.0,
            expectancy_per_trade=Decimal("0.00"),
            profit_factor=0.0,
            max_drawdown_amount=Decimal("0.00"),
            max_drawdown_pct=0.0,
            average_reward_to_risk=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            performance_by_symbol={},
            performance_by_timeframe={},
            performance_by_regime={},
        )

    # 1. Basic trade counts & P&L aggregates
    winning_trades_list = [t for t in trades if t.net_pnl > Decimal("0")]
    losing_trades_list = [t for t in trades if t.net_pnl < Decimal("0")]

    winning_trades = len(winning_trades_list)
    losing_trades = len(losing_trades_list)
    win_rate = float(winning_trades / total_trades)

    gross_profit = sum(t.gross_pnl for t in trades if t.gross_pnl > Decimal("0"))
    gross_loss = abs(sum(t.gross_pnl for t in trades if t.gross_pnl < Decimal("0")))
    net_profit = sum(t.net_pnl for t in trades)

    total_fees = sum(t.fees for t in trades)
    total_slippage = sum(t.slippage_cost for t in trades)
    total_spread = sum(t.spread_cost for t in trades)

    average_win = (
        (sum(t.net_pnl for t in winning_trades_list) / Decimal(str(winning_trades)))
        if winning_trades > 0
        else Decimal("0.00")
    )
    average_loss = (
        abs(sum(t.net_pnl for t in losing_trades_list) / Decimal(str(losing_trades)))
        if losing_trades > 0
        else Decimal("0.00")
    )

    win_loss_ratio = (
        float(average_win / average_loss)
        if average_loss > Decimal("0")
        else (999.0 if average_win > Decimal("0") else 0.0)
    )

    expectancy_per_trade = net_profit / Decimal(str(total_trades))

    profit_factor = (
        float(gross_profit / gross_loss)
        if gross_loss > Decimal("0")
        else (999.0 if gross_profit > Decimal("0") else 0.0)
    )

    # 2. Maximum Drawdown calculation from equity curve
    max_dd_amount = Decimal("0.00")
    max_dd_pct = 0.0
    peak_equity = float(initial_capital)

    if equity_curve:
        for pt in equity_curve:
            eq = pt.total_equity
            if eq > peak_equity:
                peak_equity = eq
            dd_amt = peak_equity - eq
            dd_pct = (dd_amt / peak_equity * 100.0) if peak_equity > 0 else 0.0

            if Decimal(str(round(dd_amt, 2))) > max_dd_amount:
                max_dd_amount = Decimal(str(round(dd_amt, 2)))
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

    # 3. Average Reward-to-Risk ratio
    rr_values = [
        float(t.strategy_metadata.get("rr_ratio", 0.0))
        for t in trades
        if t.strategy_metadata and "rr_ratio" in t.strategy_metadata
    ]
    avg_rr = float(np.mean(rr_values)) if rr_values else 0.0

    # 4. Consecutive streaks
    max_cons_wins = 0
    max_cons_losses = 0
    curr_wins = 0
    curr_losses = 0

    for t in trades:
        if t.net_pnl > Decimal("0"):
            curr_wins += 1
            curr_losses = 0
            if curr_wins > max_cons_wins:
                max_cons_wins = curr_wins
        elif t.net_pnl < Decimal("0"):
            curr_losses += 1
            curr_wins = 0
            if curr_losses > max_cons_losses:
                max_cons_losses = curr_losses
        else:
            curr_wins = 0
            curr_losses = 0

    # 5. Risk-Adjusted Ratios (Sharpe and Sortino)
    # Annualization factor based on candles per year (24/7 crypto markets)
    annualization_factors = {
        "15m": math.sqrt(365 * 24 * 4),
        "1h": math.sqrt(365 * 24),
        "4h": math.sqrt(365 * 6),
        "1d": math.sqrt(365),
    }
    ann_factor = annualization_factors.get(timeframe, math.sqrt(365 * 24 * 4))

    returns: List[float] = []
    if len(equity_curve) > 1:
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1].total_equity
            curr = equity_curve[i].total_equity
            if prev > 0:
                returns.append((curr - prev) / prev)

    sharpe_ratio = 0.0
    sortino_ratio = 0.0

    if len(returns) >= 2:
        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns, ddof=1))

        if std_ret > 0:
            sharpe_ratio = float((mean_ret / std_ret) * ann_factor)

        # Downside deviation for Sortino (returns < 0)
        downside_diffs = [r for r in returns if r < 0.0]
        if downside_diffs:
            downside_std = float(math.sqrt(sum(r ** 2 for r in downside_diffs) / len(returns)))
            if downside_std > 0:
                sortino_ratio = float((mean_ret / downside_std) * ann_factor)
        elif mean_ret > 0:
            sortino_ratio = 999.0

    # 6. Breakdowns by Symbol, Timeframe, and Regime
    perf_by_sym: Dict[str, Dict[str, Any]] = {}
    perf_by_tf: Dict[str, Dict[str, Any]] = {}
    perf_by_reg: Dict[str, Dict[str, Any]] = {}

    for sym in set(t.symbol for t in trades):
        sym_trades = [t for t in trades if t.symbol == sym]
        sym_wins = [t for t in sym_trades if t.net_pnl > Decimal("0")]
        sym_losses = [t for t in sym_trades if t.net_pnl < Decimal("0")]
        sym_gross_profit = sum(t.gross_pnl for t in sym_trades if t.gross_pnl > Decimal("0"))
        sym_gross_loss = abs(sum(t.gross_pnl for t in sym_trades if t.gross_pnl < Decimal("0")))
        perf_by_sym[sym] = {
            "total_trades": len(sym_trades),
            "win_rate": round(len(sym_wins) / len(sym_trades), 4) if sym_trades else 0.0,
            "net_pnl": float(sum(t.net_pnl for t in sym_trades)),
            "profit_factor": round(float(sym_gross_profit / sym_gross_loss), 2) if sym_gross_loss > Decimal("0") else (999.0 if sym_gross_profit > Decimal("0") else 0.0),
        }

    for tf_key in set(t.timeframe for t in trades):
        tf_trades = [t for t in trades if t.timeframe == tf_key]
        tf_wins = [t for t in tf_trades if t.net_pnl > Decimal("0")]
        perf_by_tf[tf_key] = {
            "total_trades": len(tf_trades),
            "win_rate": round(len(tf_wins) / len(tf_trades), 4) if tf_trades else 0.0,
            "net_pnl": float(sum(t.net_pnl for t in tf_trades)),
        }

    for reg in set(t.market_regime for t in trades):
        reg_trades = [t for t in trades if t.market_regime == reg]
        reg_wins = [t for t in reg_trades if t.net_pnl > Decimal("0")]
        perf_by_reg[reg] = {
            "total_trades": len(reg_trades),
            "win_rate": round(len(reg_wins) / len(reg_trades), 4) if reg_trades else 0.0,
            "net_pnl": float(sum(t.net_pnl for t in reg_trades)),
        }

    return BacktestMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 4),
        gross_profit=gross_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        gross_loss=gross_loss.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        net_profit=net_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_fees=total_fees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_slippage=total_slippage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_spread=total_spread.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        average_win=average_win.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        average_loss=average_loss.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        win_loss_ratio=round(win_loss_ratio, 2),
        expectancy_per_trade=expectancy_per_trade.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        profit_factor=round(profit_factor, 2),
        max_drawdown_amount=max_dd_amount,
        max_drawdown_pct=round(max_dd_pct, 2),
        average_reward_to_risk=round(avg_rr, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        sortino_ratio=round(sortino_ratio, 2),
        max_consecutive_wins=max_cons_wins,
        max_consecutive_losses=max_cons_losses,
        performance_by_symbol=perf_by_sym,
        performance_by_timeframe=perf_by_tf,
        performance_by_regime=perf_by_reg,
    )
