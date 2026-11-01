"""
NEPTUNE Walk-Forward and Out-of-Sample Validation (`walk_forward.py`)

Validation framework for detecting curve-fitting and strategy degradation:
- Chronological train/test separation (Rule S-05: never randomly shuffle time series).
- Rolling walk-forward evaluation windows.
- Walk-Forward Efficiency (WFE) metric calculation.
- Strategy configuration versioning and reproducible evaluation.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.data.market.validator import ValidatedCandle
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.models import BacktestConfig, BacktestResult


class WalkForwardWindowResult(BaseModel):
    """Result of a single walk-forward in-sample and out-of-sample cycle."""

    window_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    in_sample_trades: int
    in_sample_win_rate: float
    in_sample_net_profit: float
    in_sample_profit_factor: float
    out_of_sample_trades: int
    out_of_sample_win_rate: float
    out_of_sample_net_profit: float
    out_of_sample_profit_factor: float
    walk_forward_efficiency: float                # OOS return / IS return
    degradation_pct: float                        # (IS - OOS) / IS


class WalkForwardReport(BaseModel):
    """Aggregated walk-forward evaluation report."""

    strategy_id: str
    symbol: str
    timeframe: str
    windows: List[WalkForwardWindowResult]
    mean_wfe: float
    is_robust: bool                               # WFE >= 0.50 without negative OOS bias
    summary: str


class WalkForwardValidator:
    """
    Executes chronological train/test and walk-forward evaluations.
    """

    @staticmethod
    def chronological_split(
        candles: List[ValidatedCandle],
        train_ratio: float = 0.70,
    ) -> Tuple[List[ValidatedCandle], List[ValidatedCandle]]:
        """
        Split candles chronologically into In-Sample (Train) and Out-of-Sample (Test).
        Never shuffles candles (Rule S-05).
        """
        if not candles:
            return [], []

        sorted_candles = sorted(candles, key=lambda c: c.timestamp)
        split_idx = int(len(sorted_candles) * train_ratio)

        train_set = sorted_candles[:split_idx]
        test_set = sorted_candles[split_idx:]
        return train_set, test_set

    @classmethod
    async def run_train_test_evaluation(
        cls,
        config: BacktestConfig,
        candles_by_symbol: Dict[str, List[ValidatedCandle]],
        train_ratio: float = 0.70,
    ) -> Dict[str, Any]:
        """
        Execute an isolated In-Sample backtest followed by an Out-of-Sample backtest.
        """
        train_map: Dict[str, List[ValidatedCandle]] = {}
        test_map: Dict[str, List[ValidatedCandle]] = {}

        for sym, candles in candles_by_symbol.items():
            train_c, test_c = cls.chronological_split(candles, train_ratio)
            train_map[sym] = train_c
            test_map[sym] = test_c

        engine_train = HistoricalBacktestEngine(config)
        res_train = await engine_train.run(candles_by_symbol=train_map)

        engine_test = HistoricalBacktestEngine(config)
        res_test = await engine_test.run(candles_by_symbol=test_map)

        is_profit = float(res_train.metrics.net_profit)
        oos_profit = float(res_test.metrics.net_profit)

        wfe = (oos_profit / is_profit) if is_profit > 0 else 0.0

        return {
            "strategy_id": config.strategy_id,
            "train_ratio": train_ratio,
            "in_sample": {
                "period_start": train_map[config.symbols[0]][0].timestamp if train_map[config.symbols[0]] else "",
                "period_end": train_map[config.symbols[0]][-1].timestamp if train_map[config.symbols[0]] else "",
                "total_trades": res_train.metrics.total_trades,
                "win_rate": res_train.metrics.win_rate,
                "net_profit": is_profit,
                "profit_factor": res_train.metrics.profit_factor,
                "max_drawdown_pct": res_train.metrics.max_drawdown_pct,
            },
            "out_of_sample": {
                "period_start": test_map[config.symbols[0]][0].timestamp if test_map[config.symbols[0]] else "",
                "period_end": test_map[config.symbols[0]][-1].timestamp if test_map[config.symbols[0]] else "",
                "total_trades": res_test.metrics.total_trades,
                "win_rate": res_test.metrics.win_rate,
                "net_profit": oos_profit,
                "profit_factor": res_test.metrics.profit_factor,
                "max_drawdown_pct": res_test.metrics.max_drawdown_pct,
            },
            "walk_forward_efficiency": round(wfe, 2),
            "result_train": res_train,
            "result_test": res_test,
        }
