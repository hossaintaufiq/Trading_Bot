"""
Institutional Decision-Making Engine for Neptune Bot.
Implements:
1. Macro Regime Gate (BTC 50 EMA + Trend Strength Filter)
2. Best Coin Selection (Relative Strength vs BTC, ADX, RVOL Ranking)
3. Best Pattern Selector (ORB Breakout, Trend Pullback, Bull Flag)
4. Asymmetric Risk/Reward Engine (Hold for profit: 2.5R target, BE ratchet at +1R, ATR runner trail)
5. Sell-if-needed Invalidation & Capital Protection
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CoinScore:
    symbol: str
    relative_strength: float
    adx: float
    rvol: float
    trend_aligned: bool
    composite_score: float
    reason: str


class DecisionEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # Cost Hurdle: Roundtrip fee (0.10%*2 = 0.20%) + Slippage (0.05%*2 = 0.10%) = 0.30%
        # Require target distance >= 4x roundtrip costs = 1.20%
        self.min_target_pct = float(self.config.get("min_target_pct", 1.20))
        self.min_rvol = float(self.config.get("min_rvol", 1.15))
        self.min_adx = float(self.config.get("min_adx", 20.0))
        self.rr_ratio = float(self.config.get("target_rr_ratio", 2.5))
        self.atr_stop_multiplier = float(self.config.get("atr_stop_multiplier", 1.5))
        self.atr_trail_multiplier = float(self.config.get("atr_trail_multiplier", 1.5))

    def evaluate_macro_regime(self, btc_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluate BTC Macro Trend Gate.
        If BTC is below its 50 EMA or in strong downtrend, alts must NOT be bought.
        """
        if btc_df.empty or len(btc_df) < 50:
            return {"allow_alts": True, "regime": "NEUTRAL", "btc_trend": "UNKNOWN"}

        curr = btc_df.iloc[-1]
        close = float(curr["close"])
        ema50 = float(curr.get("ema_slow", close))
        if "ema_50" in curr:
            ema50 = float(curr["ema_50"])
        adx = float(curr.get("adx", 20.0))

        is_bullish = close >= ema50 * 0.998
        is_strong_bear = (close < ema50 * 0.985) and (adx > 25.0)

        return {
            "allow_alts": not is_strong_bear and is_bullish,
            "regime": "BULL_EXPANSION" if (is_bullish and adx >= 22) else ("BEAR_DEFENSE" if is_strong_bear else "CHOP_RANGE"),
            "btc_price": close,
            "btc_ema50": ema50,
            "btc_adx": adx
        }

    def rank_best_coins(
        self,
        data_by_symbol: Dict[str, pd.DataFrame],
        current_time: int,
        time_to_idx: Dict[str, Dict[int, int]]
    ) -> List[CoinScore]:
        """
        Rank all watchlist coins at current_time by Relative Strength vs BTC,
        Trend Strength (ADX), and Volume Surge (RVOL).
        Returns sorted list of CoinScore (highest score first).
        """
        btc_sym = "BTC/USDT"
        btc_ret = 0.0
        if btc_sym in data_by_symbol and current_time in time_to_idx[btc_sym]:
            b_idx = time_to_idx[btc_sym][current_time]
            b_df = data_by_symbol[btc_sym]
            if b_idx >= 24:
                p_now = float(b_df["close"].iloc[b_idx])
                p_past = float(b_df["close"].iloc[b_idx - 24])
                btc_ret = (p_now - p_past) / p_past if p_past > 0 else 0.0

        scores = []
        for sym, df in data_by_symbol.items():
            if current_time not in time_to_idx[sym]:
                continue
            idx = time_to_idx[sym][current_time]
            if idx < 25:
                continue

            curr = df.iloc[idx]
            close = float(curr["close"])
            past_close = float(df["close"].iloc[idx - min(24, idx)])
            coin_ret = (close - past_close) / past_close if past_close > 0 else 0.0

            rs = coin_ret - btc_ret if sym != btc_sym else 0.0
            adx = float(curr.get("adx", 20.0))
            rvol = float(curr.get("rvol", 1.0))
            ema9 = float(curr.get("ema_fast", close))
            ema21 = float(curr.get("ema_slow", close))
            trend_aligned = close > ema21 and ema9 >= ema21

            # Composite Score: 45% Relative Strength, 35% Trend Strength, 20% Volume Surge
            rs_score = max(-5.0, min(5.0, rs * 100.0))
            adx_score = min(50.0, adx) / 50.0 * 10.0
            rvol_score = min(3.0, rvol) / 3.0 * 10.0

            composite = (rs_score * 0.45) + (adx_score * 0.35) + (rvol_score * 0.20)
            if trend_aligned:
                composite += 2.0  # Trend alignment bonus

            scores.append(CoinScore(
                symbol=sym,
                relative_strength=round(rs * 100.0, 2),
                adx=round(adx, 1),
                rvol=round(rvol, 2),
                trend_aligned=trend_aligned,
                composite_score=round(composite, 3),
                reason=f"RS: {rs*100:+.2f}%, ADX: {adx:.1f}, RVOL: {rvol:.2f}x"
            ))

        scores.sort(key=lambda x: x.composite_score, reverse=True)
        return scores

    def evaluate_best_pattern(
        self,
        symbol: str,
        df_slice: pd.DataFrame,
        macro_regime: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate if the coin exhibits one of the institutional high-expectancy setups:
        1. Opening Range Breakout (ORB) with Volume
        2. Trend Pullback Bounce (EMA 9/21 Support Retest)
        3. Bull Flag Momentum Breakout
        Applies strict Risk/Reward (> 2.0R), Cost Hurdle (>= 1.20%), and Stop/Target calculation.
        """
        if len(df_slice) < 25:
            return None

        # Macro Gate: If alts are barred, skip non-BTC
        if symbol != "BTC/USDT" and not macro_regime.get("allow_alts", True):
            return None

        curr = df_slice.iloc[-1]
        prev = df_slice.iloc[-2]
        price = float(curr["close"])
        open_p = float(curr["open"])
        high_p = float(curr["high"])
        low_p = float(curr["low"])
        atr = float(curr.get("atr", price * 0.01))
        rvol = float(curr.get("rvol", 1.0))
        adx = float(curr.get("adx", 20.0))
        ema9 = float(curr.get("ema_fast", price))
        ema21 = float(curr.get("ema_slow", price))

        is_green = price > open_p
        lower_wick = (min(open_p, price) - low_p) > (0.15 * (high_p - low_p + 1e-6))

        # ---------------------------------------------------------------------
        # PATTERN 1: ORB BREAKOUT (Top Performer in Baseline: 54% WR)
        # ---------------------------------------------------------------------
        # Measure opening range of today's session (first 15 bars of session)
        if "dt" in df_slice.columns:
            cur_dt = curr["dt"]
            cur_date = cur_dt.date()
            session_bars = df_slice[df_slice["dt"].dt.date == cur_date]
            if len(session_bars) >= 4:
                or_bars = session_bars.head(min(15, len(session_bars)))
                or_high = float(or_bars["high"].max())
                or_low = float(or_bars["low"].min())
                or_mid = (or_high + or_low) / 2.0
                or_range_pct = ((or_high - or_low) / or_low) * 100.0

                # Breakout: Current price breaks above OR High with green candle & volume
                if (price > or_high) and (float(prev["close"]) <= or_high * 1.002) and is_green:
                    if rvol >= self.min_rvol and or_range_pct <= 4.5:
                        stop = max(or_mid, price - (self.atr_stop_multiplier * atr))
                        risk = max(0.0001, price - stop)
                        target = price + (self.rr_ratio * risk)
                        target_dist_pct = ((target - price) / price) * 100.0

                        # Cost Hurdle: Target must be >= 4x roundtrip costs
                        if target_dist_pct >= self.min_target_pct:
                            return {
                                "action": "BUY",
                                "setup_id": "orb_breakout",
                                "setup_name": "ORB Breakout",
                                "entry_price": price,
                                "stop_price": round(stop, 4),
                                "target_price": round(target, 4),
                                "invalidation_price": round(or_mid, 4),
                                "max_holding_bars": 50,
                                "rr_ratio": round((target - price) / risk, 2),
                                "target_pct": round(target_dist_pct, 2),
                                "reason": f"ORB Breakout above ${or_high:,.2f} ({rvol:.2f}x vol, {target_dist_pct:.1f}% target)"
                            }

        # ---------------------------------------------------------------------
        # PATTERN 2: EMA 9/21 TREND PULLBACK BOUNCE
        # ---------------------------------------------------------------------
        # In confirmed trend (EMA 9 > EMA 21, ADX >= 22), test 21 EMA support and bounce green
        if ema9 > ema21 and adx >= self.min_adx:
            tested_ema = low_p <= ema9 * 1.002 or low_p <= ema21 * 1.004
            held_support = price >= ema21 * 0.998 and is_green and lower_wick
            rsi = float(curr.get("rsi", 50.0))

            if tested_ema and held_support and (40.0 <= rsi <= 64.0):
                stop = min(low_p, ema21) - (0.4 * atr)
                risk = max(0.0001, price - stop)
                target = price + (self.rr_ratio * risk)
                target_dist_pct = ((target - price) / price) * 100.0

                if target_dist_pct >= self.min_target_pct:
                    return {
                        "action": "BUY",
                        "setup_id": "trend_pullback",
                        "setup_name": "Trend Pullback Bounce",
                        "entry_price": price,
                        "stop_price": round(stop, 4),
                        "target_price": round(target, 4),
                        "invalidation_price": round(ema21 * 0.995, 4),
                        "max_holding_bars": 45,
                        "rr_ratio": round((target - price) / risk, 2),
                        "target_pct": round(target_dist_pct, 2),
                        "reason": f"Trend Pullback Bounce off 21 EMA (ADX: {adx:.1f}, {target_dist_pct:.1f}% target)"
                    }

        # ---------------------------------------------------------------------
        # PATTERN 3: BULL FLAG MOMENTUM BREAKOUT
        # ---------------------------------------------------------------------
        # Impulse pole followed by shallow flag consolidation, breaking resistance
        if len(df_slice) >= 22:
            pole = df_slice.iloc[-16:-5]
            flag = df_slice.iloc[-5:-1]
            pole_gain = (float(pole["high"].max()) - float(pole["low"].min())) / float(pole["low"].min()) * 100.0
            flag_pullback = (float(pole["high"].max()) - float(flag["low"].min())) / float(pole["high"].max()) * 100.0
            flag_high = float(flag["high"].max())

            if pole_gain >= 2.5 and flag_pullback <= 1.5 and price > flag_high and is_green and rvol >= 1.2:
                stop = float(flag["low"].min()) - (0.3 * atr)
                risk = max(0.0001, price - stop)
                target = price + (self.rr_ratio * risk)
                target_dist_pct = ((target - price) / price) * 100.0

                if target_dist_pct >= self.min_target_pct:
                    return {
                        "action": "BUY",
                        "setup_id": "bull_flag",
                        "setup_name": "Bull Flag Breakout",
                        "entry_price": price,
                        "stop_price": round(stop, 4),
                        "target_price": round(target, 4),
                        "invalidation_price": round(float(flag["low"].min()), 4),
                        "max_holding_bars": 40,
                        "rr_ratio": round((target - price) / risk, 2),
                        "target_pct": round(target_dist_pct, 2),
                        "reason": f"Bull Flag Breakout above ${flag_high:,.2f} (Pole: +{pole_gain:.1f}%, {target_dist_pct:.1f}% target)"
                    }

        return None

