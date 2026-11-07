"""
NEPTUNE Dual-Timeframe Trend Following Strategy (`htf_trend_following_v1` / `SHR-001`)

Implements Candidate A2 from the Strategy Research Reset:
- 4h Regime Conditioning: Macro trend alignment (EMA 50 > EMA 200, ADX >= 22.0).
- 1h Swing-Structure Entry: Pullback into dynamic value zone followed by a confirmed
  Market Structure Shift (close above local swing high).
- Long-Only Spot Execution (Rule S-01): Holds 100% USDT cash in bear/choppy regimes.
- Strict Closed-Candle Consumption (Rule A-09): Rejects incomplete candles.
- Asymmetric Payoff Geometry: Target R:R >= 2.5:1, compressing friction to < 7% of target.
- Monetary calculations executed using Python Decimal (Rule A-01).
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

from app.analytics.indicators import calculate_adx, calculate_atr, calculate_ema
from app.strategies.base_strategy import (
    BaseStrategy,
    RawSignal,
    SignalDirection,
    TimeFrame,
)


class DualTimeframeConfig(BaseModel):
    """Configuration parameters for the Dual-Timeframe Trend Strategy."""
    # 4h Macro Regime Parameters
    fast_ema_4h: int = 50
    slow_ema_4h: int = 200
    min_adx_4h: float = 22.0
    adx_period_4h: int = 14

    # 1h Micro Swing & Pullback Parameters
    fast_ema_1h: int = 21
    slow_ema_1h: int = 50
    atr_period_1h: int = 14
    atr_stop_multiplier: float = 2.0
    min_reward_risk_ratio: float = 2.5
    swing_pivot_lookback_1h: int = 5
    max_holding_candles_1h: int = 96  # 4 calendar days (96 hours)


class DualTimeframeTrendStrategy(BaseStrategy):
    """
    Flexible Dual-Timeframe Trend Strategy (`htf_trend_following_v1`).
    
    Evaluates 4h macro direction and executes on 1h swing structural confirmation.
    """

    strategy_id: str = "htf_trend_following_v1"
    strategy_name: str = "Dual-Timeframe 4h/1h Trend Following"
    supported_timeframes: List[TimeFrame] = [TimeFrame.H1, TimeFrame.H4]

    def __init__(self, config: Optional[DualTimeframeConfig] = None):
        self.config = config or DualTimeframeConfig()

    def get_entry_conditions(self) -> List[str]:
        """Human-readable entry condition descriptions."""
        return [
            f"4h Macro Trend: EMA({self.config.fast_ema_4h}) > EMA({self.config.slow_ema_4h})",
            f"4h Trend Strength: ADX({self.config.adx_period_4h}) >= {self.config.min_adx_4h}",
            "4h Price Location: Close > EMA(50)",
            f"1h Pullback: Price retraces into dynamic support band between EMA({self.config.fast_ema_1h}) and EMA({self.config.slow_ema_1h})",
            f"1h Market Structure Shift: Confirmed 1h close breaks above local {self.config.swing_pivot_lookback_1h}-bar swing high",
            "Direction: Strictly LONG spot (no short selling)",
        ]

    def get_exit_conditions(self) -> List[str]:
        """Human-readable exit condition descriptions."""
        return [
            "Stop Loss: Hit when price touches or opens below structural stop level",
            f"Profit Target: Dynamic or fixed target bracket at minimum {self.config.min_reward_risk_ratio}:1 R:R",
            f"Time Stop: Position holding period exceeds {self.config.max_holding_candles_1h} 1h candles without achieving target",
        ]

    def get_invalidation_rules(self) -> List[str]:
        """Conditions that invalidate a pending signal."""
        return [
            "4h Macro Trend reverses (EMA 50 crosses below EMA 200)",
            "4h ADX collapses below minimum threshold",
            "1h price closes below structural swing low prior to order execution",
            "5.0% Portfolio Maximum Drawdown circuit breaker trips",
        ]

    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.H1,
        df_4h: Optional[pd.DataFrame] = None,
    ) -> Optional[RawSignal]:
        """
        Evaluate market data for a valid long setup.
        
        Args:
            df: 1h candles DataFrame (must contain 'open', 'high', 'low', 'close', 'volume', 'timestamp')
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Current evaluation timeframe (defaults to 1h)
            df_4h: Optional pre-aggregated 4h DataFrame. If None, resampled from df.
        """
        if df is None or len(df) < (self.config.slow_ema_1h + 20):
            return None

        # Rule A-09: Analysis must ONLY evaluate closed candles
        if "is_closed" in df.columns and not bool(df["is_closed"].iloc[-1]):
            return None

        # Prepare 4h macro DataFrame
        macro_df = self._resolve_4h_dataframe(df, df_4h)
        if macro_df is None or len(macro_df) < (self.config.slow_ema_4h + self.config.adx_period_4h):
            return None

        # 1. Evaluate 4h Macro Regime (Cash Preservation Gate)
        is_bull_regime, regime_reason = self._evaluate_4h_macro_regime(macro_df)
        if not is_bull_regime:
            # Preserve 100% USDT cash: return NO_SIGNAL
            return None

        # 2. Evaluate 1h Micro Swing Structure & Pullback
        signal = self._evaluate_1h_entry(df, macro_df, symbol)
        return signal

    def _resolve_4h_dataframe(
        self, df_1h: pd.DataFrame, df_4h: Optional[pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """Resolve 4h DataFrame from explicit input or resample from 1h."""
        if df_4h is not None and len(df_4h) >= self.config.slow_ema_4h:
            return df_4h

        # Resample from 1h if timestamp is present
        if "timestamp" not in df_1h.columns:
            return None

        try:
            df_copy = df_1h.copy()
            if not isinstance(df_copy["timestamp"].iloc[0], pd.Timestamp):
                df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"], utc=True)
            df_copy = df_copy.set_index("timestamp").sort_index()

            resampled = df_copy.resample("4h").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna()

            # The current in-progress 4h bar must be excluded (Rule A-09)
            # If the last 1h candle is not the 4th candle of the 4h window, drop the partial 4h bar
            if len(resampled) > 1:
                return resampled.iloc[:-1].reset_index()
            return None
        except Exception:
            return None

    def _evaluate_4h_macro_regime(self, df_4h: pd.DataFrame) -> Tuple[bool, str]:
        """
        Evaluate 4h trend state and strength.
        Returns: (is_bull_regime: bool, reason: str)
        """
        closes = [float(x) for x in df_4h["close"]]
        highs = [float(x) for x in df_4h["high"]]
        lows = [float(x) for x in df_4h["low"]]

        ema_50 = calculate_ema(closes, self.config.fast_ema_4h)
        ema_200 = calculate_ema(closes, self.config.slow_ema_4h)
        adx, plus_di, minus_di = calculate_adx(highs, lows, closes, self.config.adx_period_4h)

        curr_close = closes[-1]
        curr_ema_50 = ema_50[-1]
        curr_ema_200 = ema_200[-1]
        curr_adx = adx[-1]

        if curr_ema_50 is None or curr_ema_200 is None or curr_adx is None:
            return False, "4h indicators warming up"

        # Condition 1: Moving average trend alignment (EMA 50 > EMA 200)
        if curr_ema_50 <= curr_ema_200:
            return False, f"4h Trend is BEARISH/NEUTRAL (EMA50 {curr_ema_50:.2f} <= EMA200 {curr_ema_200:.2f})"

        # Condition 2: Price location above EMA 50
        if curr_close < curr_ema_50:
            return False, f"4h Price below EMA50 ({curr_close:.2f} < {curr_ema_50:.2f})"

        # Condition 3: ADX trend strength confirmation (prevent entering sideways chop)
        if curr_adx < self.config.min_adx_4h:
            return False, f"4h ADX insufficient ({curr_adx:.1f} < {self.config.min_adx_4h})"

        return True, f"BULLISH_TREND (EMA50 > EMA200, Close > EMA50, ADX {curr_adx:.1f})"

    def _evaluate_1h_entry(
        self, df_1h: pd.DataFrame, df_4h: pd.DataFrame, symbol: str
    ) -> Optional[RawSignal]:
        """Evaluate 1h swing-structure shift after pullback into dynamic value zone."""
        closes = [float(x) for x in df_1h["close"]]
        highs = [float(x) for x in df_1h["high"]]
        lows = [float(x) for x in df_1h["low"]]

        ema_21 = calculate_ema(closes, self.config.fast_ema_1h)
        ema_50 = calculate_ema(closes, self.config.slow_ema_1h)
        atr = calculate_atr(highs, lows, closes, self.config.atr_period_1h)

        latest_idx = len(closes) - 1
        curr_close = closes[latest_idx]
        curr_high = highs[latest_idx]
        curr_low = lows[latest_idx]
        curr_ema_21 = ema_21[latest_idx]
        curr_ema_50 = ema_50[latest_idx]
        curr_atr = atr[latest_idx]

        if curr_ema_21 is None or curr_ema_50 is None or curr_atr is None:
            return None

        # Step A: Verify pullback into 1h dynamic support zone within recent 10 bars
        lookback = min(10, latest_idx)
        pullback_detected = False
        for i in range(latest_idx - lookback, latest_idx):
            if ema_21[i] is not None and lows[i] <= ema_21[i]:
                pullback_detected = True
                break

        if not pullback_detected:
            return None

        # Step B: Identify local swing high (5-bar fractal) prior to current candle
        pivot_lb = self.config.swing_pivot_lookback_1h
        prior_highs = highs[latest_idx - pivot_lb : latest_idx]
        local_swing_high = max(prior_highs)

        # Step C: Market Structure Shift Trigger — current 1h candle closes above local swing high
        prev_close = closes[latest_idx - 1]
        if not (prev_close <= local_swing_high and curr_close > local_swing_high):
            return None

        # Step D: Structural Stop Loss — lowest low of the pullback swing
        prior_lows = lows[latest_idx - pivot_lb : latest_idx + 1]
        structural_swing_low = min(prior_lows)

        # Monetary Calculations using Decimal (Rule A-01)
        entry_dec = Decimal(str(curr_close))
        swing_low_dec = Decimal(str(structural_swing_low))
        atr_dec = Decimal(str(round(curr_atr, 4)))
        buffer_dec = (atr_dec * Decimal(str(self.config.atr_stop_multiplier))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Stop placed below structural swing low minus ATR buffer
        stop_dec = swing_low_dec - (atr_dec * Decimal("0.5"))
        risk_distance = entry_dec - stop_dec

        # Sanity check: Risk distance must be between 1.0% and 4.0% of price
        min_risk_dist = entry_dec * Decimal("0.010")
        max_risk_dist = entry_dec * Decimal("0.040")
        if risk_distance < min_risk_dist:
            stop_dec = entry_dec - min_risk_dist
            risk_distance = min_risk_dist
        elif risk_distance > max_risk_dist:
            stop_dec = entry_dec - max_risk_dist
            risk_distance = max_risk_dist

        if stop_dec <= Decimal("0"):
            return None

        # Target set at minimum 2.5:1 R:R
        rr_dec = Decimal(str(self.config.min_reward_risk_ratio))
        reward_distance = (risk_distance * rr_dec).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        target_dec = entry_dec + reward_distance

        # Parse timestamp safely
        gen_time = datetime.now(timezone.utc)
        if "timestamp" in df_1h.columns:
            ts_val = df_1h["timestamp"].iloc[-1]
            if isinstance(ts_val, (datetime, pd.Timestamp)):
                gen_time = ts_val.to_pydatetime() if hasattr(ts_val, "to_pydatetime") else ts_val

        return RawSignal(
            strategy_id=self.strategy_id,
            symbol=symbol,
            timeframe=TimeFrame.H1,
            direction=SignalDirection.LONG,
            entry_price=float(entry_dec),
            stop_price=float(stop_dec),
            target_price=float(target_dec),
            signal_strength=0.85,
            invalidation_price=float(stop_dec),
            max_holding_candles=self.config.max_holding_candles_1h,
            generated_at=gen_time,
            explanation=(
                f"Dual-Timeframe Long: 4h Bullish Regime confirmed, "
                f"1h Pullback completed with Market Structure Shift close above {local_swing_high:.2f}."
            ),
            metadata={
                "timeframe_macro": "4h",
                "timeframe_micro": "1h",
                "local_swing_high": local_swing_high,
                "structural_swing_low": structural_swing_low,
                "atr_1h": float(atr_dec),
                "planned_rr": float(rr_dec),
                "frictional_drag_pct": round(float(Decimal("0.0032") / (reward_distance / entry_dec) * Decimal("100")), 2),
            },
        )
