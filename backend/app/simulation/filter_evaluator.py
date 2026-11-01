"""
NEPTUNE Hypothesis Filter Evaluation Engine (`filter_evaluator.py`)

Executes rigorous out-of-sample hypothesis testing for entry filters:
- Chronological partitioning: Train (50%), Validation (25%), OOS (25%).
- Zero look-ahead bias (Rule S-05).
- Metric calculation: Expectancy, Profit Factor, Win Rate, t-stat, p-value.
- Ablation analysis for multi-factor confluence.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from app.analytics.filters import (
    FilterDecision,
    filter_confluence_ensemble,
    filter_higher_timeframe_alignment,
    filter_momentum_confirmation,
    filter_regime_confidence,
    filter_trend_strength_adx,
    filter_volatility_bounds,
    filter_volume_confirmation,
)
from app.data.market.validator import ValidatedCandle
from app.simulation.models import SimulatedTrade


@dataclass
class FilterEvaluationMetrics:
    filter_id: str
    partition: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    net_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    expectancy: float
    mean_win: float
    mean_loss: float
    max_drawdown: float
    t_stat: float
    p_value: float


class FilterHypothesisEvaluator:
    """Evaluates entry filter hypotheses on chronological partitions."""

    @staticmethod
    def partition_trades_chronologically(
        trades: List[SimulatedTrade],
        train_pct: float = 0.50,
        val_pct: float = 0.25,
    ) -> Dict[str, List[SimulatedTrade]]:
        """Split trades strictly chronologically by entry timestamp into Train, Val, OOS."""
        if not trades:
            return {"train": [], "validation": [], "oos": []}

        sorted_trades = sorted(trades, key=lambda t: t.entry_timestamp)
        n = len(sorted_trades)
        train_idx = int(n * train_pct)
        val_idx = int(n * (train_pct + val_pct))

        return {
            "train": sorted_trades[:train_idx],
            "validation": sorted_trades[train_idx:val_idx],
            "oos": sorted_trades[val_idx:],
        }

    @staticmethod
    def evaluate_trades(
        trades: List[SimulatedTrade],
        filter_id: str,
        partition: str,
    ) -> FilterEvaluationMetrics:
        """Compute statistical and performance metrics for a subset of trades."""
        if not trades:
            return FilterEvaluationMetrics(
                filter_id=filter_id,
                partition=partition,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                net_pnl=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                profit_factor=0.0,
                expectancy=0.0,
                mean_win=0.0,
                mean_loss=0.0,
                max_drawdown=0.0,
                t_stat=0.0,
                p_value=1.0,
            )

        pnls = [float(t.net_pnl) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        net_pnl = sum(pnls)
        n = len(pnls)
        wr = (len(wins) / n * 100.0) if n > 0 else 0.0
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        exp = net_pnl / n if n > 0 else 0.0

        # Running drawdown
        cum_pnl = np.cumsum(pnls)
        peaks = np.maximum.accumulate(cum_pnl)
        drawdowns = peaks - cum_pnl
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # One-sample t-test testing H0: mean PnL <= 0
        if n >= 2 and np.std(pnls, ddof=1) > 0:
            t_res = stats.ttest_1samp(pnls, 0.0)
            t_stat = float(t_res.statistic)
            p_val = float(t_res.pvalue)
        else:
            t_stat, p_val = 0.0, 1.0

        return FilterEvaluationMetrics(
            filter_id=filter_id,
            partition=partition,
            total_trades=n,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=round(wr, 2),
            net_pnl=round(net_pnl, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            profit_factor=round(pf, 2),
            expectancy=round(exp, 2),
            mean_win=round(float(np.mean(wins)), 2) if wins else 0.0,
            mean_loss=round(float(np.mean(losses)), 2) if losses else 0.0,
            max_drawdown=round(max_dd, 2),
            t_stat=round(t_stat, 2),
            p_value=round(p_val, 4),
        )

    @staticmethod
    def apply_filter_to_trade(
        trade: SimulatedTrade,
        candles: List[ValidatedCandle],
        filter_func: Callable[[Sequence[ValidatedCandle], str, str], FilterDecision],
        lookback: int = 250,
    ) -> bool:
        """Evaluate a filter function on the candle history prior to trade entry."""
        # Find entry candle index
        c_idx = next((i for i, c in enumerate(candles) if c.timestamp == trade.entry_timestamp), None)
        if c_idx is None or c_idx < 30:
            return False

        # Causal slice strictly <= entry candle (Rule S-05)
        start_idx = max(0, c_idx + 1 - lookback)
        sub_c = candles[start_idx : c_idx + 1]

        decision = filter_func(sub_c, trade.direction, trade.entry_timestamp)
        return decision.passed

