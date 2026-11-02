"""
NEPTUNE Simulation Models

Data structures for historical backtesting, simulated trade ledgers,
portfolio equity curves, and performance evaluation metrics.
All monetary calculations strictly use Python Decimal (Rule A-01).
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BacktestConfig(BaseModel):
    """Configuration for historical backtest runs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT"])
    timeframe: str = "15m"
    start_time: Optional[str] = None          # ISO 8601 UTC
    end_time: Optional[str] = None            # ISO 8601 UTC
    initial_capital: Decimal = Decimal("1000.00")
    maker_fee_pct: Decimal = Decimal("0.001")     # 0.1%
    taker_fee_pct: Decimal = Decimal("0.001")     # 0.1%
    slippage_pct: Decimal = Decimal("0.0005")     # 0.05%
    spread_bps: Decimal = Decimal("2.0")          # 0.02% spread
    max_concurrent_positions: int = 2
    risk_per_trade_pct: Decimal = Decimal("0.005") # 0.5%
    daily_loss_limit_pct: Decimal = Decimal("0.02") # 2.0%
    max_drawdown_pct: Decimal = Decimal("0.05")   # 5.0%
    min_reward_risk_ratio: Decimal = Decimal("1.5")
    strategy_id: str = "trend_momentum_pullback_v1"
    strategy_config: Dict[str, Any] = Field(default_factory=dict)
    conservative_ambiguous_bars: bool = True      # Stop hit if both stop & target touched in 1 bar
    exit_policy: str = "BALANCED"                 # BALANCED, FIXED_BRACKET, AGGRESSIVE, TREND_FOLLOWING
    trailing_atr_multiplier: Decimal = Decimal("2.0")
    trailing_activation_threshold_r: Decimal = Decimal("1.0")
    entry_filter: Optional[str] = None           # None, H1_ADX_25, H1_ADX_30, H4_RVOL_85, H5_VOLATILITY_BOUNDS, H7_CONFLUENCE
    save_to_db: bool = False
    save_to_parquet: bool = False
    output_dir: Optional[str] = None


class SimulatedTrade(BaseModel):
    """
    Immutable trade ledger entry recording complete trade lifecycle.
    Satisfies Section 5 Trade Ledger requirements and Rule A-10 execution assumptions.
    """

    trade_id: str
    symbol: str
    timeframe: str
    direction: str                              # LONG or SHORT
    signal_timestamp: str                       # ISO 8601 UTC
    entry_timestamp: str                        # ISO 8601 UTC
    entry_price: Decimal                        # Executed entry price (including slippage & spread)
    exit_timestamp: str                         # ISO 8601 UTC
    exit_price: Decimal                         # Executed exit price (including slippage & spread)
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal                      # Base asset quantity
    gross_pnl: Decimal                          # Notional exit - notional entry (pre-friction)
    fees: Decimal                               # Entry fee + Exit fee
    spread_cost: Decimal                        # Spread penalty across entry & exit
    slippage_cost: Decimal                      # Slippage penalty across entry & exit
    net_pnl: Decimal                            # gross_pnl - fees - spread_cost - slippage_cost
    exit_reason: str                            # STOP_LOSS, TAKE_PROFIT, AMBIGUOUS_BAR_STOP, REVERSAL_CONFIRMED, FORCE_CLOSE
    market_regime: str                          # Regime at entry (e.g. TRENDING_BULL, RANGING)
    strategy_metadata: Dict[str, Any] = Field(default_factory=dict)
    initial_stop_loss: Decimal = Decimal("0.00")
    final_stop_loss: Decimal = Decimal("0.00")
    trailing_stop_updates: int = 0
    peak_favorable_price: Decimal = Decimal("0.00")
    original_theoretical_target: Optional[Decimal] = None
    reversal_detection_timestamp: Optional[str] = None
    mfe: Decimal = Decimal("0.00")
    mae: Decimal = Decimal("0.00")
    mfe_pct: float = 0.0
    mae_pct: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0
    mfe_cash: Decimal = Decimal("0.00")
    mae_cash: Decimal = Decimal("0.00")
    holding_duration_seconds: float = 0.0
    reversal_reasons: List[str] = Field(default_factory=list)
    reversal_superseded: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to a dictionary with float serialization for tabular/parquet export."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "signal_timestamp": self.signal_timestamp,
            "entry_timestamp": self.entry_timestamp,
            "entry_price": float(self.entry_price),
            "exit_timestamp": self.exit_timestamp,
            "exit_price": float(self.exit_price),
            "stop_loss": float(self.stop_loss),
            "take_profit": float(self.take_profit) if self.take_profit is not None else 0.0,
            "position_size": float(self.position_size),
            "gross_pnl": float(self.gross_pnl),
            "fees": float(self.fees),
            "spread_cost": float(self.spread_cost),
            "slippage_cost": float(self.slippage_cost),
            "net_pnl": float(self.net_pnl),
            "exit_reason": self.exit_reason,
            "market_regime": self.market_regime,
            "strategy_metadata": self.strategy_metadata,
            "initial_stop_loss": float(self.initial_stop_loss),
            "final_stop_loss": float(self.final_stop_loss),
            "trailing_stop_updates": self.trailing_stop_updates,
            "peak_favorable_price": float(self.peak_favorable_price),
            "original_theoretical_target": float(self.original_theoretical_target) if self.original_theoretical_target is not None else None,
            "reversal_detection_timestamp": self.reversal_detection_timestamp,
            "mfe": float(self.mfe),
            "mae": float(self.mae),
            "mfe_pct": round(float(self.mfe_pct), 4),
            "mae_pct": round(float(self.mae_pct), 4),
            "mfe_r": round(float(self.mfe_r), 4),
            "mae_r": round(float(self.mae_r), 4),
            "mfe_cash": float(self.mfe_cash),
            "mae_cash": float(self.mae_cash),
            "holding_duration_seconds": self.holding_duration_seconds,
            "reversal_reasons": self.reversal_reasons,
            "reversal_superseded": self.reversal_superseded,
        }


class ActivePosition:
    """Internal position tracking object during event replay."""

    def __init__(
        self,
        position_id: str,
        signal_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        entry_timestamp: str,
        entry_price: Decimal,
        raw_entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Optional[Decimal],
        position_size: Decimal,
        entry_fee: Decimal,
        entry_slippage_cost: Decimal,
        entry_spread_cost: Decimal,
        market_regime: str,
        strategy_metadata: Dict[str, Any],
        exit_policy: str = "BALANCED",
        theoretical_take_profit: Optional[Decimal] = None,
    ):
        self.position_id = position_id
        self.signal_id = signal_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.direction = direction
        self.entry_timestamp = entry_timestamp
        self.entry_price = entry_price
        self.raw_entry_price = raw_entry_price
        self.initial_stop_loss = stop_loss
        self.stop_loss = stop_loss
        self.trailing_stop = stop_loss
        self.take_profit = take_profit
        self.theoretical_take_profit = theoretical_take_profit or take_profit
        self.position_size = position_size
        self.entry_fee = entry_fee
        self.entry_slippage_cost = entry_slippage_cost
        self.entry_spread_cost = entry_spread_cost
        self.market_regime = market_regime
        self.strategy_metadata = strategy_metadata
        self.exit_policy = exit_policy
        self.current_price = entry_price
        self.unrealized_pnl = Decimal("0")

        # Balanced Protection tracking fields
        self.initial_risk_per_unit = abs(raw_entry_price - stop_loss)
        self.peak_price_since_entry = raw_entry_price
        self.trough_price_since_entry = raw_entry_price
        self.unrealized_high_water_mark = Decimal("0.00")
        self.trailing_updates_count = 0
        self.reversal_exit_pending = False
        self.reversal_detection_timestamp: Optional[str] = None
        self.reversal_reason_codes: List[str] = []
        self.reversal_superseded: bool = False
        self.mfe = Decimal("0.00")
        self.mae = Decimal("0.00")


class EquityPoint(BaseModel):
    """Snapshot of portfolio equity at a given point in time."""

    timestamp: str
    cash_equity: float
    total_equity: float
    drawdown_pct: float
    open_positions_count: int


class BacktestMetrics(BaseModel):
    """Comprehensive performance analytics per Section 6."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    total_fees: Decimal
    total_slippage: Decimal
    total_spread: Decimal
    average_win: Decimal
    average_loss: Decimal
    win_loss_ratio: float
    expectancy_per_trade: Decimal
    profit_factor: float
    max_drawdown_amount: Decimal
    max_drawdown_pct: float
    average_reward_to_risk: float
    sharpe_ratio: float
    sortino_ratio: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    performance_by_symbol: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    performance_by_timeframe: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    performance_by_regime: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    performance_by_exit_reason: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    average_mfe: Decimal = Decimal("0.00")
    average_mae: Decimal = Decimal("0.00")
    average_mfe_pct: float = 0.0
    average_mae_pct: float = 0.0
    average_mfe_r: float = 0.0
    average_mae_r: float = 0.0
    average_mfe_cash: Decimal = Decimal("0.00")
    average_mae_cash: Decimal = Decimal("0.00")
    average_holding_duration_seconds: float = 0.0
    candidate_signals: int = 0
    filter_accepted_signals: int = 0
    filter_rejected_signals: int = 0
    risk_approved_signals: int = 0
    risk_rejected_signals: int = 0
    reversal_metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BacktestResult(BaseModel):
    """Complete output packaging for a backtest execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    backtest_id: str
    config: BacktestConfig
    metrics: BacktestMetrics
    trades: List[SimulatedTrade]
    equity_curve: List[EquityPoint]
