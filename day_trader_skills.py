"""
Day Trader Skill Suite for Neptune Bot.
Implements the core quantitative skills from the Day Trader framework:
1. Scanner: Scans for ORB Breakouts, Bull Flags, Oversold Bounces, and 20-MA Reclaims.
2. Entry Timer: Bar-by-bar trigger verification on closed candles.
3. Exit Planner: Calculates bracket orders (Stop at OR-mid or ATR:1.5, Target at 2R/1R).
4. Time Machine: Monte Carlo simulation replaying 1,000 paths from historical return distribution.
5. Budget Manager: Risk-based position sizing (Position = Max Risk / Stop Distance).
6. Risk Gate: Pre-trade validation gate (Reward:Risk >= 1.5R, Daily Loss limit, PASS/BLOCK).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import time


@dataclass
class TradePlan:
    symbol: str
    setup_name: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_unit: float
    reward_per_unit: float
    reward_risk_ratio: float
    stop_rule: str
    target_rule: str
    timestamp: int


@dataclass
class TimeMachineResult:
    replays: int
    target_first_pct: float
    stop_first_pct: float
    neither_pct: float
    expected_r: float
    verdict: str  # "FAVORABLE EDGE", "COIN FLIP", "UNFAVORABLE"
    confidence: float
    percentiles: Dict[str, float]
    sample_paths: Optional[List[Dict[str, Any]]] = None
    cone_bounds: Optional[Dict[str, List[float]]] = None
    entry_price: float = 0.0
    target_price: float = 0.0
    stop_price: float = 0.0
    horizon_steps: int = 30


@dataclass
class RiskVerdict:
    passed: bool
    reason: str
    max_risk_usd: float
    allowed_units: float
    position_cost_usd: float


class DayTraderSuite:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    # -------------------------------------------------------------------------
    # 1. SCANNER SKILL: Detect Setups across OHLCV bars
    # -------------------------------------------------------------------------
    def scan_setups(self, df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """
        Scans OHLCV bars for the 4 core day-trading setups:
        1. Opening Range Breakout (ORB)
        2. Bull Flag Momentum Breakout
        3. Oversold Bounce (RSI(14) < 30 with green confirmation)
        4. Reclaim 20-MA with volume surge
        """
        if len(df) < 25:
            return []

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(curr["close"])
        rsi = float(curr.get("rsi", 50.0))
        ma20 = float(curr.get("bb_middle", price))
        prev_ma20 = float(prev.get("bb_middle", price))

        setups = []

        # --- Setup 1: Opening Range Breakout (ORB) ---
        # Measure opening range of the session (e.g. first 15 bars)
        or_bars = df.iloc[:15] if len(df) >= 15 else df.iloc[:5]
        or_high = float(or_bars["high"].max())
        or_low = float(or_bars["low"].min())
        or_mid = (or_high + or_low) / 2.0

        if price > or_high and float(prev["close"]) <= or_high:
            pct_over = ((price - or_high) / or_high) * 100
            setups.append({
                "setup": "ORB_BREAKOUT",
                "name": "Opening Range Breakout",
                "badge": "ORB",
                "active": True,
                "confidence": 0.88,
                "level": round(or_high, 2),
                "or_mid": round(or_mid, 2),
                "or_low": round(or_low, 2),
                "detail": f"Closed {pct_over:.2f}% above 15m Opening Range (${or_high:,.1f})"
            })
        elif price > or_high:
            setups.append({
                "setup": "ORB_BREAKOUT",
                "name": "Opening Range Breakout",
                "badge": "ORB",
                "active": False,
                "confidence": 0.65,
                "level": round(or_high, 2),
                "detail": f"Trading above Range High (${or_high:,.1f})"
            })

        # --- Setup 2: Bull Flag Breakout ---
        # Impulse move in bars [-15:-5] (> 1.2% in crypto) + consolidation in [-5:-1] (< 0.8% range)
        if len(df) >= 20:
            impulse_window = df.iloc[-15:-5]
            flag_window = df.iloc[-5:-1]
            impulse_gain = (float(impulse_window["close"].max()) - float(impulse_window["close"].min())) / float(impulse_window["close"].min()) * 100
            flag_range = (float(flag_window["high"].max()) - float(flag_window["low"].min())) / float(flag_window["low"].min()) * 100
            flag_high = float(flag_window["high"].max())

            if impulse_gain >= 1.0 and flag_range <= 1.2 and price >= flag_high:
                setups.append({
                    "setup": "BULL_FLAG",
                    "name": "Bull Flag Breakout",
                    "badge": "FLAG",
                    "active": True,
                    "confidence": 0.85,
                    "level": round(flag_high, 2),
                    "detail": f"Breakout from {flag_range:.1f}% flag after +{impulse_gain:.1f}% impulse"
                })

        # --- Setup 3: Oversold Bounce ---
        # RSI was < 32 on previous bar, current bar closes green with rising RSI
        prev_rsi = float(prev.get("rsi", 50.0))
        if prev_rsi <= 32 and float(curr["close"]) > float(curr["open"]) and rsi > prev_rsi:
            setups.append({
                "setup": "OVERSOLD_BOUNCE",
                "name": "Oversold Bounce",
                "badge": "BOUNCE",
                "active": True,
                "confidence": 0.82,
                "level": round(price, 2),
                "detail": f"Reversal bounce: RSI recovered from {prev_rsi:.1f} to {rsi:.1f}"
            })

        # --- Setup 4: 20-MA Reclaim ---
        # Previous close was below 20-MA, current close is firmly above 20-MA
        if float(prev["close"]) < prev_ma20 and price > ma20:
            setups.append({
                "setup": "RECLAIM_MA20",
                "name": "20-MA Reclaim",
                "badge": "RECLAIM",
                "active": True,
                "confidence": 0.80,
                "level": round(ma20, 2),
                "detail": f"Reclaimed 20-period Moving Average at ${ma20:,.1f}"
            })

        return setups

    # -------------------------------------------------------------------------
    # 2. EXIT PLANNER SKILL: Bracket Order (Stop & 2R Target)
    # -------------------------------------------------------------------------
    def plan_bracket_exit(
        self,
        symbol: str,
        setup_name: str,
        entry_price: float,
        df: pd.DataFrame,
        stop_mode: str = "or-mid",
        target_mode: str = "2R"
    ) -> TradePlan:
        """
        Computes bracket exit prices:
        - Stop: 'or-mid', 'atr:1.5', or 'pct:1.5'
        - Target: '2R' (twice the risk) or '1R'
        """
        curr = df.iloc[-1]
        atr = float(curr.get("atr", entry_price * 0.008))

        # 1. Determine Stop-Loss
        if stop_mode == "or-mid" and len(df) >= 15:
            or_bars = df.iloc[:15]
            or_high = float(or_bars["high"].max())
            or_low = float(or_bars["low"].min())
            stop_loss = (or_high + or_low) / 2.0
            # If or-mid is above entry or too far (> 2.5%), fallback to ATR
            if stop_loss >= entry_price or (entry_price - stop_loss) / entry_price > 0.03:
                stop_loss = entry_price - (1.5 * atr)
        elif stop_mode.startswith("atr"):
            multiplier = 1.5
            stop_loss = entry_price - (multiplier * atr)
        else:
            # Default fallback 1.5% stop
            stop_loss = entry_price * 0.985

        risk_per_unit = max(0.01, entry_price - stop_loss)

        # 2. Determine Take-Profit Target (1R or 2R)
        r_multiplier = 2.0 if target_mode == "2R" else 1.0
        take_profit = entry_price + (r_multiplier * risk_per_unit)
        reward_per_unit = take_profit - entry_price
        rr_ratio = reward_per_unit / risk_per_unit

        return TradePlan(
            symbol=symbol,
            setup_name=setup_name,
            entry_price=round(entry_price, 4),
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            risk_per_unit=round(risk_per_unit, 4),
            reward_per_unit=round(reward_per_unit, 4),
            reward_risk_ratio=round(rr_ratio, 2),
            stop_rule=stop_mode,
            target_rule=target_mode,
            timestamp=int(df.iloc[-1].get("time", 0) * 1000)
        )

    # -------------------------------------------------------------------------
    # 3. TIME MACHINE SKILL: Monte Carlo Setup Replay (1,000 paths)
    # -------------------------------------------------------------------------
    def run_time_machine(
        self,
        plan: TradePlan,
        df: pd.DataFrame,
        num_replays: int = 1000
    ) -> TimeMachineResult:
        """
        Replays the remaining session 1,000 times using the empirical distribution
        of the asset's own recent 5-minute bar returns.
        Computes Target First %, Stop First %, Neither %, and Expected R.
        """
        if len(df) < 30:
            return TimeMachineResult(
                replays=0,
                target_first_pct=50.0,
                stop_first_pct=50.0,
                neither_pct=0.0,
                expected_r=0.0,
                verdict="COIN FLIP (LIMITED DATA)",
                confidence=0.5,
                percentiles={"p10": plan.stop_loss, "p50": plan.entry_price, "p90": plan.take_profit}
            )

        # Compute empirical bar-by-bar percentage returns
        closes = df["close"].values
        bar_returns = np.diff(closes) / closes[:-1]

        entry = plan.entry_price
        target = plan.take_profit
        stop = plan.stop_loss

        # Horizon: next 30 bars (e.g. 30 minutes in 1m timeframe)
        horizon = 30
        target_first = 0
        stop_first = 0
        neither = 0
        terminal_prices = []

        path_matrix = np.zeros((num_replays, horizon + 1))
        path_matrix[:, 0] = entry

        target_paths = []
        stop_paths = []
        neutral_paths = []

        # Use time-seeded random generator so live animations evolve as market moves
        rng = np.random.default_rng(int(time.time() * 1000) % 2**32)

        for i in range(num_replays):
            # Sample empirical returns with replacement
            sampled_rets = rng.choice(bar_returns, size=horizon, replace=True)
            path = entry * np.cumprod(1 + sampled_rets)
            path_matrix[i, 1:] = path

            hit_target = np.where(path >= target)[0]
            hit_stop = np.where(path <= stop)[0]

            full_path = [round(float(x), 2) for x in path_matrix[i]]

            if len(hit_target) > 0 and len(hit_stop) > 0:
                if hit_target[0] < hit_stop[0]:
                    target_first += 1
                    if len(target_paths) < 10:
                        target_paths.append(full_path)
                else:
                    stop_first += 1
                    if len(stop_paths) < 8:
                        stop_paths.append(full_path)
            elif len(hit_target) > 0:
                target_first += 1
                if len(target_paths) < 10:
                    target_paths.append(full_path)
            elif len(hit_stop) > 0:
                stop_first += 1
                if len(stop_paths) < 8:
                    stop_paths.append(full_path)
            else:
                neither += 1
                if len(neutral_paths) < 4:
                    neutral_paths.append(full_path)

            terminal_prices.append(path[-1])

        target_pct = (target_first / num_replays) * 100.0
        stop_pct = (stop_first / num_replays) * 100.0
        neither_pct = (neither / num_replays) * 100.0

        # Expected R: Target gives +2R, Stop gives -1R
        expected_r = (target_first * plan.reward_risk_ratio - stop_first * 1.0) / num_replays

        # Verdict
        if target_pct >= 58.0 and expected_r >= 0.25:
            verdict = "FAVORABLE EDGE"
        elif target_pct <= 42.0 or expected_r < -0.1:
            verdict = "POOR ODDS (AVOID)"
        else:
            verdict = "BALANCED / COIN FLIP"

        confidence = target_pct / 100.0

        percentiles = {
            "p10": float(np.percentile(terminal_prices, 10)),
            "p50": float(np.percentile(terminal_prices, 50)),
            "p90": float(np.percentile(terminal_prices, 90))
        }

        # Step-by-step percentile envelopes across all 30 forward steps
        cone_bounds = {
            "p10": [round(float(x), 2) for x in np.percentile(path_matrix, 10, axis=0)],
            "p25": [round(float(x), 2) for x in np.percentile(path_matrix, 25, axis=0)],
            "p50": [round(float(x), 2) for x in np.percentile(path_matrix, 50, axis=0)],
            "p75": [round(float(x), 2) for x in np.percentile(path_matrix, 75, axis=0)],
            "p90": [round(float(x), 2) for x in np.percentile(path_matrix, 90, axis=0)]
        }

        # Representative sample paths tagged by outcome for visual canvas
        sample_paths = []
        for p in target_paths:
            sample_paths.append({"type": "target", "points": p})
        for p in stop_paths:
            sample_paths.append({"type": "stop", "points": p})
        for p in neutral_paths:
            sample_paths.append({"type": "neutral", "points": p})

        return TimeMachineResult(
            replays=num_replays,
            target_first_pct=round(target_pct, 1),
            stop_first_pct=round(stop_pct, 1),
            neither_pct=round(neither_pct, 1),
            expected_r=round(expected_r, 2),
            verdict=verdict,
            confidence=round(confidence, 2),
            percentiles=percentiles,
            sample_paths=sample_paths,
            cone_bounds=cone_bounds,
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stop_price=round(stop, 2),
            horizon_steps=horizon
        )

    # -------------------------------------------------------------------------
    # 4. LIVE MARKET TRENDS & MOMENTUM CONFLUENCE
    # -------------------------------------------------------------------------
    def compute_market_trends(self, df: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """Compute live multi-timeframe trend momentum, volume surges, and volatility regimes."""
        if df.empty or len(df) < 20:
            return {
                "trend_direction": "NEUTRAL",
                "trend_strength_pct": 50,
                "trend_label": "INITIALIZING MARKET",
                "trend_class": "neutral",
                "volatility_regime": "STABLE",
                "volume_surge_ratio": 1.0,
                "ema_spread_usd": 0.0,
                "ema_spread_pct": 0.0,
                "multi_timeframe": []
            }

        curr = df.iloc[-1]
        price = current_price or float(curr["close"])
        ema9 = float(curr.get("ema_fast", price))
        ema21 = float(curr.get("ema_slow", price))
        rsi = float(curr.get("rsi", 50.0))
        ma20 = float(curr.get("bb_middle", price))

        # 1. EMA Spread & Momentum Velocity
        ema_spread = ema9 - ema21
        ema_spread_pct = (ema_spread / price) * 100 if price > 0 else 0.0

        # 2. Volume Surge Ratio vs 20-period average
        vol_curr = float(curr.get("volume", 0))
        vol_avg = float(df["volume"].tail(20).mean()) if "volume" in df.columns else 1.0
        vol_surge = round(vol_curr / max(0.001, vol_avg), 2)

        # 3. Trend Direction & Strength Score (0 to 100)
        bull_score = 50
        if price > ema9: bull_score += 15
        else: bull_score -= 15
        if ema9 > ema21: bull_score += 15
        else: bull_score -= 15
        if price > ma20: bull_score += 10
        else: bull_score -= 10
        if rsi >= 55: bull_score += 10
        elif rsi <= 45: bull_score -= 10
        bull_score = max(5, min(95, bull_score))

        if bull_score >= 70:
            trend_dir = "STRONG BULLISH"
            trend_label = "BULLISH EXPANSION"
            trend_class = "bull"
        elif bull_score >= 55:
            trend_dir = "MILD BULLISH"
            trend_label = "MODERATE UPTREND"
            trend_class = "bull"
        elif bull_score <= 30:
            trend_dir = "STRONG BEARISH"
            trend_label = "BEARISH ACCELERATION"
            trend_class = "bear"
        elif bull_score <= 45:
            trend_dir = "MILD BEARISH"
            trend_label = "MODERATE DOWNTREND"
            trend_class = "bear"
        else:
            trend_dir = "NEUTRAL"
            trend_label = "SIDEWAYS COMPRESSION"
            trend_class = "neutral"

        # 4. Volatility Regime
        atr = float(curr.get("atr", price * 0.005))
        atr_avg = float(df["atr"].tail(20).mean()) if "atr" in df.columns else atr
        if atr > atr_avg * 1.25:
            vol_regime = "HIGH VOLATILITY EXPANSION"
        elif atr < atr_avg * 0.75:
            vol_regime = "LOW VOLATILITY SQUEEZE"
        else:
            vol_regime = "STABLE REGIME"

        # 5. Multi-Timeframe Trend Confluence (1m, 3m, 5m, 15m)
        t_1m = "BULL" if price >= ema9 else "BEAR"
        c_3m_ago = float(df.iloc[-4]["close"]) if len(df) >= 4 else price
        t_3m = "BULL" if price >= c_3m_ago else "BEAR"
        c_5m_ago = float(df.iloc[-6]["close"]) if len(df) >= 6 else price
        t_5m = "BULL" if price >= c_5m_ago else "BEAR"
        c_15m_ago = float(df.iloc[-16]["close"]) if len(df) >= 16 else price
        t_15m = "BULL" if price >= c_15m_ago else "BEAR"

        multi_tf = [
            {"tf": "1m", "name": "Micro Scalp", "trend": t_1m, "class": "bull" if t_1m == "BULL" else "bear"},
            {"tf": "3m", "name": "Fast Momentum", "trend": t_3m, "class": "bull" if t_3m == "BULL" else "bear"},
            {"tf": "5m", "name": "Session Trend", "trend": t_5m, "class": "bull" if t_5m == "BULL" else "bear"},
            {"tf": "15m", "name": "Macro Filter", "trend": t_15m, "class": "bull" if t_15m == "BULL" else "bear"}
        ]

        return {
            "trend_direction": trend_dir,
            "trend_strength_pct": bull_score,
            "trend_label": trend_label,
            "trend_class": trend_class,
            "volatility_regime": vol_regime,
            "volume_surge_ratio": vol_surge,
            "ema_spread_usd": round(ema_spread, 2),
            "ema_spread_pct": round(ema_spread_pct, 3),
            "multi_timeframe": multi_tf
        }

    # -------------------------------------------------------------------------
    # 5. BUDGET SKILL: Risk-Based Position Sizing
    # -------------------------------------------------------------------------
    def size_position(self, plan: TradePlan, available_cash: float) -> Tuple[float, float]:
        """
        Sizes position so that max loss at stop equals max_loss_per_trade,
        strictly capped by trade_amount_usdt (default $500) and available cash.
        """
        max_trade_budget = self.config.get("trade_amount_usdt", 500.0)
        max_loss_usd = self.config.get("max_loss_per_trade_usd", 50.0)
        risk_per_unit = plan.risk_per_unit

        if risk_per_unit <= 0 or plan.entry_price <= 0:
            units = max_trade_budget / plan.entry_price
        else:
            units = max_loss_usd / risk_per_unit

        # Strict cap: Do not exceed user-configured trade amount ($500)
        max_units_by_budget = max_trade_budget / plan.entry_price
        if units > max_units_by_budget:
            units = max_units_by_budget

        # Cap by available cash with 10% buffer
        cash_buffer = self.config.get("cash_buffer_pct", 10.0) / 100.0
        max_spend = available_cash * (1.0 - cash_buffer)
        if units * plan.entry_price > max_spend:
            units = max_spend / plan.entry_price

        # Minimum order sanity check ($15)
        min_order_usd = 15.0
        if units * plan.entry_price < min_order_usd:
            units = min_order_usd / plan.entry_price

        total_cost = units * plan.entry_price
        return units, total_cost

    # -------------------------------------------------------------------------
    # 5. RISK GATE SKILL: Pre-Trade Validation
    # -------------------------------------------------------------------------
    def check_risk_gate(self, plan: TradePlan, total_cost: float, daily_loss_so_far: float) -> RiskVerdict:
        """
        Verifies trade against institutional limits:
        1. Stop-Loss exists and is below entry
        2. Reward:Risk >= min_reward_risk (default 1.5R)
        3. Daily loss + planned loss does not breach max_daily_loss_usd
        """
        min_rr = self.config.get("min_reward_risk", 1.5)
        max_daily_loss = self.config.get("max_daily_loss_usd", 200.0)
        max_loss_trade = self.config.get("max_loss_per_trade_usd", 50.0)

        if plan.stop_loss >= plan.entry_price:
            return RiskVerdict(False, "BLOCK: Stop loss must be below entry price", 0, 0, 0)

        if plan.reward_risk_ratio < min_rr:
            return RiskVerdict(False, f"BLOCK: Reward:Risk ({plan.reward_risk_ratio:.1f}R) is below minimum required {min_rr:.1f}R", 0, 0, 0)

        if (daily_loss_so_far + max_loss_trade) > max_daily_loss:
            return RiskVerdict(False, f"BLOCK: Daily risk limit reached (${daily_loss_so_far:.1f} / ${max_daily_loss:.1f})", 0, 0, 0)

        return RiskVerdict(True, "PASS: All institutional risk rules satisfied", max_loss_trade, total_cost / plan.entry_price, total_cost)
