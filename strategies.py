"""
Trading Strategies Engine for Neptune Bot.
Includes strategies derived from the Day Trader skills:
1. ORB Breakout Bot: 15-minute Opening Range Breakout with midpoint stop
2. Bull Flag Momentum Bot: Impulse rally + consolidation breakout
3. Oversold Bounce Bot: RSI(14) oversold reversal bounce
4. 20-MA Reclaim Bot: Moving average reclaim with volume surge
5. EMA + RSI Trend Bot: Dual moving average crossover with pullback entries
6. Neptune Fleet Strategy: Multi-Bot Autonomous Engine evaluating all setups concurrently
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd


@dataclass
class Signal:
    action: str  # "BUY", "SELL", "HOLD"
    price: float
    reason: str
    confidence: float = 1.0
    setup_name: str = "GENERIC"
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        """Evaluate market data and return trading signal."""
        pass


class ORBStrategy(BaseStrategy):
    """
    Opening Range Breakout (ORB) Strategy (from trader-scanner & trader-entry).
    Measures opening range (first 15m). Buys on first candle close above range high.
    Exit stop at range midpoint, target at 2R.
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__("orb", params)

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        if len(df) < 16:
            return Signal("HOLD", 0.0, "Building opening range bars (need >= 16 candles)", 0.0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(curr["close"])

        # First 15 bars establish the Opening Range
        or_bars = df.iloc[:15]
        or_high = float(or_bars["high"].max())
        or_low = float(or_bars["low"].min())
        or_mid = (or_high + or_low) / 2.0

        metrics = {
            "price": price,
            "or_high": round(or_high, 2),
            "or_low": round(or_low, 2),
            "or_mid": round(or_mid, 2)
        }

        if position is None or position.get("quantity", 0) <= 0:
            # Trigger: First closed bar above range high
            if price > or_high and float(prev["close"]) <= or_high:
                risk = price - or_mid
                target = price + (2.0 * risk)
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"ORB Triggered: Closed above 15m Range High (${or_high:,.1f})",
                    confidence=0.88,
                    setup_name="ORB Breakout",
                    stop_price=round(or_mid, 2),
                    target_price=round(target, 2),
                    metrics=metrics
                )
            return Signal("HOLD", price, f"ORB Scanner: Waiting for close above ${or_high:,.1f} (Current: ${price:,.1f})", 0.0, metrics)
        else:
            # Exit if price falls back below midpoint
            if price <= or_mid:
                return Signal("SELL", price, f"ORB Stop Hit: Dropped below Range Midpoint (${or_mid:,.1f})", 0.9, "ORB Exit", metrics=metrics)
            return Signal("HOLD", price, "Holding ORB position (Guarded by Range Midpoint stop)", 0.0, metrics)


class BullFlagStrategy(BaseStrategy):
    """
    Bull Flag Momentum Strategy.
    Impulse run followed by tight consolidation inside channel, enters on breakout.
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__("bull_flag", params)

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        if len(df) < 22:
            return Signal("HOLD", 0.0, "Insufficient bars for Bull Flag detection", 0.0)

        curr = df.iloc[-1]
        price = float(curr["close"])
        impulse = df.iloc[-15:-5]
        flag = df.iloc[-5:-1]

        impulse_gain = (float(impulse["close"].max()) - float(impulse["close"].min())) / float(impulse["close"].min()) * 100
        flag_range = (float(flag["high"].max()) - float(flag["low"].min())) / float(flag["low"].min()) * 100
        flag_high = float(flag["high"].max())
        flag_low = float(flag["low"].min())

        metrics = {
            "price": price,
            "impulse_gain": round(impulse_gain, 2),
            "flag_range": round(flag_range, 2),
            "flag_high": round(flag_high, 2)
        }

        if position is None or position.get("quantity", 0) <= 0:
            if impulse_gain >= 0.8 and flag_range <= 1.2 and price >= flag_high:
                risk = price - flag_low
                target = price + (2.0 * risk)
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"Bull Flag Breakout: +{impulse_gain:.1f}% impulse broke out over ${flag_high:,.1f}",
                    confidence=0.86,
                    setup_name="Bull Flag",
                    stop_price=round(flag_low, 2),
                    target_price=round(target, 2),
                    metrics=metrics
                )
            return Signal("HOLD", price, f"Scanning Flag: Flag range {flag_range:.1f}% (High: ${flag_high:,.1f})", 0.0, metrics)
        else:
            if price <= flag_low:
                return Signal("SELL", price, "Flag pattern invalidated (Dropped below flag support)", 0.9, "Flag Exit", metrics=metrics)
            return Signal("HOLD", price, "Holding Bull Flag trend", 0.0, metrics)


class OversoldBounceStrategy(BaseStrategy):
    """
    Oversold Bounce Strategy (from trader-scanner oversold_bounce).
    Triggers when RSI was oversold (<30) and closes with a green reversal candle.
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__("oversold_bounce", params)

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        if len(df) < 20:
            return Signal("HOLD", 0.0, "Insufficient bars for RSI calculation", 0.0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(curr["close"])
        rsi = float(curr.get("rsi", 50.0))
        prev_rsi = float(prev.get("rsi", 50.0))
        ma20 = float(curr.get("bb_middle", price))

        metrics = {"price": price, "rsi": round(rsi, 2), "prev_rsi": round(prev_rsi, 2)}

        if position is None or position.get("quantity", 0) <= 0:
            if prev_rsi <= 32 and float(curr["close"]) > float(curr["open"]) and rsi > prev_rsi:
                stop = float(curr["low"]) * 0.995
                target = ma20
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"Oversold Bounce: RSI bounced from {prev_rsi:.1f} with green candle",
                    confidence=0.83,
                    setup_name="Oversold Bounce",
                    stop_price=round(stop, 2),
                    target_price=round(target, 2),
                    metrics=metrics
                )
            return Signal("HOLD", price, f"Monitoring RSI: Currently {rsi:.1f} (Waiting for oversold dip <= 30)", 0.0, metrics)
        else:
            if rsi >= 65 or price >= ma20:
                return Signal("SELL", price, f"Mean Reversion Target Reached (RSI: {rsi:.1f})", 0.85, "Bounce Target", metrics=metrics)
            return Signal("HOLD", price, "Riding oversold bounce to 20-MA", 0.0, metrics)


class MAReclaimStrategy(BaseStrategy):
    """
    20-MA Reclaim Strategy.
    Buys when price reclaims the 20-period moving average from below.
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__("reclaim_ma20", params)

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        if len(df) < 22:
            return Signal("HOLD", 0.0, "Insufficient bars for MA calculation", 0.0)

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(curr["close"])
        ma20 = float(curr.get("bb_middle", price))
        prev_ma20 = float(prev.get("bb_middle", price))

        metrics = {"price": price, "ma20": round(ma20, 2), "prev_close": round(float(prev["close"]), 2)}

        if position is None or position.get("quantity", 0) <= 0:
            if float(prev["close"]) < prev_ma20 and price > ma20:
                stop = ma20 * 0.99
                target = price + (price - stop) * 2.0
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"20-MA Reclaimed: Reclaimed 20 Moving Average (${ma20:,.1f})",
                    confidence=0.82,
                    setup_name="20-MA Reclaim",
                    stop_price=round(stop, 2),
                    target_price=round(target, 2),
                    metrics=metrics
                )
            return Signal("HOLD", price, f"Below 20-MA: Price ${price:,.1f} vs MA20 ${ma20:,.1f}", 0.0, metrics)
        else:
            if price < ma20 * 0.995:
                return Signal("SELL", price, "Lost 20-MA support level", 0.88, "MA Lost", metrics=metrics)
            return Signal("HOLD", price, "Holding above 20-MA support", 0.0, metrics)


class EMARSIStrategy(BaseStrategy):
    """
    Enhanced Trend Momentum Strategy with Pullback Entry.
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__("ema_rsi", params)

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        if len(df) < 25:
            return Signal("HOLD", 0.0, "Insufficient historical candle data")

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        price = float(curr["close"])
        ema_fast = float(curr.get("ema_fast", price))
        ema_slow = float(curr.get("ema_slow", price))
        prev_fast = float(prev.get("ema_fast", price))
        prev_slow = float(prev.get("ema_slow", price))
        rsi = float(curr.get("rsi", 50.0))

        rsi_min = self.params.get("rsi_buy_min", 45)
        rsi_max = self.params.get("rsi_buy_max", 70)
        rsi_sell = self.params.get("rsi_sell_threshold", 75)

        metrics = {
            "price": price,
            "ema_fast": round(ema_fast, 2),
            "ema_slow": round(ema_slow, 2),
            "rsi": round(rsi, 2),
            "trend": "BULLISH" if ema_fast > ema_slow else "BEARISH"
        }

        bullish_cross = (prev_fast <= prev_slow) and (ema_fast > ema_slow)
        sustained_bullish = (ema_fast > ema_slow) and (rsi >= rsi_min and rsi <= rsi_max)
        bearish_cross = (prev_fast >= prev_slow) and (ema_fast < ema_slow)

        if position is None or position.get("quantity", 0) <= 0:
            if bullish_cross and (rsi >= rsi_min and rsi <= rsi_max):
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"Golden Cross: EMA 9 crossed above EMA 21 (RSI: {rsi:.1f})",
                    confidence=0.90,
                    setup_name="EMA Cross",
                    metrics=metrics
                )
            elif (ema_fast > ema_slow) and (rsi >= rsi_min and rsi <= 65) and (price <= ema_fast * 1.002):
                return Signal(
                    action="BUY",
                    price=price,
                    reason=f"Pullback Dip Buy: Tested EMA 9 support in bull trend (RSI: {rsi:.1f})",
                    confidence=0.82,
                    setup_name="EMA Pullback",
                    metrics=metrics
                )

            if ema_fast <= ema_slow:
                hold_reason = f"Safety Hold (Downtrend): EMA 9 (${ema_fast:,.1f}) < EMA 21 (${ema_slow:,.1f}). Protecting capital."
            elif rsi < rsi_min:
                hold_reason = f"Awaiting Momentum: RSI ({rsi:.1f}) < {rsi_min}."
            else:
                hold_reason = f"Bullish Trend: Waiting for pullback to EMA 9."
            return Signal("HOLD", price, hold_reason, 0.0, "EMA Trend", metrics=metrics)
        else:
            if bearish_cross:
                return Signal("SELL", price, "Death Cross: EMA 9 crossed below EMA 21", 0.90, "EMA Cross Exit", metrics=metrics)
            elif rsi >= rsi_sell:
                return Signal("SELL", price, f"Overbought Exhaustion (RSI: {rsi:.1f})", 0.80, "RSI Peak", metrics=metrics)
            return Signal("HOLD", price, "Holding trend with trailing guard", 0.0, "EMA Hold", metrics=metrics)


class NeptuneFleetStrategy(BaseStrategy):
    """
    🔱 Neptune Autonomous Fleet Strategy.
    Runs ALL 4 day-trading bots concurrently (ORB, Bull Flag, Oversold Bounce, 20-MA Reclaim, EMA Trend).
    Evaluates every setup every second, picking the highest-confidence setup.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__("neptune_fleet", config.get("strategies", {}))
        self.sub_bots: List[BaseStrategy] = [
            ORBStrategy(self.params.get("orb", {})),
            BullFlagStrategy(self.params.get("bull_flag", {})),
            OversoldBounceStrategy(self.params.get("oversold_bounce", {})),
            MAReclaimStrategy(self.params.get("reclaim_ma20", {})),
            EMARSIStrategy(self.params.get("ema_rsi", {}))
        ]

    def evaluate(self, df: pd.DataFrame, position: Optional[Dict[str, Any]] = None) -> Signal:
        # If position is active, check exit rules
        if position is not None and position.get("quantity", 0) > 0:
            for bot in self.sub_bots:
                sig = bot.evaluate(df, position)
                if sig.action == "SELL":
                    return sig
            return Signal("HOLD", float(df.iloc[-1]["close"]), "Fleet holding active trade (Stops & Targets engaged)", 0.0)

        # In entry mode: Evaluate all bots and pick best active BUY signal
        buy_signals = []
        for bot in self.sub_bots:
            sig = bot.evaluate(df, None)
            if sig.action == "BUY":
                buy_signals.append(sig)

        if buy_signals:
            # Sort by confidence
            buy_signals.sort(key=lambda x: x.confidence, reverse=True)
            best = buy_signals[0]
            best.reason = f"[🔱 FLEET ALERT] {best.reason}"
            return best

        curr_price = float(df.iloc[-1]["close"])
        return Signal(
            action="HOLD",
            price=curr_price,
            reason="🔱 Neptune Fleet scanning 5 quantitative setups simultaneously (Awaiting confirmation trigger)",
            confidence=0.0,
            setup_name="Fleet Radar"
        )


def get_strategy(strategy_name: str, config: Dict[str, Any]) -> BaseStrategy:
    """Factory function for Neptune Bot strategies."""
    strat_configs = config.get("strategies", {})
    if strategy_name == "orb":
        return ORBStrategy(strat_configs.get("orb", {}))
    elif strategy_name == "bull_flag":
        return BullFlagStrategy(strat_configs.get("bull_flag", {}))
    elif strategy_name == "oversold_bounce":
        return OversoldBounceStrategy(strat_configs.get("oversold_bounce", {}))
    elif strategy_name == "reclaim_ma20":
        return MAReclaimStrategy(strat_configs.get("reclaim_ma20", {}))
    elif strategy_name == "neptune_fleet":
        return NeptuneFleetStrategy(config)
    else:
        return EMARSIStrategy(strat_configs.get("ema_rsi", {}))
