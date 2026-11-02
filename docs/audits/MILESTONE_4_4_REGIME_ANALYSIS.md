# NEPTUNE — Milestone 4.4: Market Regime Census & Concentration Analysis

## 1. Executive Summary

Milestone 4.4 analyzes the macroeconomic and market regime distribution across the expanded 34-month contiguous dataset (January 1, 2024 to November 1, 2026) using NEPTUNE's deterministic `MarketScannerAgent`.

The objective is to establish:
1. The empirical distribution of market regimes across BTCUSDT, ETHUSDT, and BNBUSDT.
2. Whether deterministic strategy performance and entry filters are regime-dependent.
3. Whether positive performance in earlier milestones (e.g. H7 in Milestone 4.3.2) was genuine edge or an artifact of concentrated single-event tail risk (e.g., the May 28–29, 2026 market sell-off).

---

## 2. Deterministic Regime Classification Taxonomy

The `MarketScannerAgent` classifies every closed candle into one of five mutually exclusive states:

1. **`TRENDING_BULL`**:
   - $Close > EMA_{50} > EMA_{200}$
   - $ADX_{14} \ge 25$ with $+DI > -DI$.
   - Directional expansion with upward momentum.
2. **`TRENDING_BEAR`**:
   - $Close < EMA_{50} < EMA_{200}$
   - $ADX_{14} \ge 25$ with $-DI > +DI$.
   - Directional expansion with downward momentum.
3. **`RANGING`**:
   - Price oscillating around flat EMAs ($|EMA_{50} - EMA_{200}| / EMA_{200} < 0.5\%$).
   - $ADX_{14} < 20$.
   - Bollinger Bandwidth compressed inside Keltner Channels (Squeeze).
4. **`VOLATILE`**:
   - $ATR\% > 3.0\%$ or Bollinger Bandwidth expanding aggressively without directional EMA alignment.
   - High churn, wide bar spreads, whipsaw price action.
5. **`UNCERTAIN`**:
   - Insufficient historical warmup (< 30 bars) or conflicting indicator signals.

---

## 3. Market Regime Distribution (Census Across Expanded History)

*Scanned across 34-month contiguous dataset (2024-01-01 to 2026-11-01). Data exported to `storage/exports/milestone_4_4/regime_breakdown.csv`.*

### Observations & Regime Proportions

The empirical regime census across daily (1d), 4-hour (4h), and 1-hour (1h) series indicates:
- **Ranging & Low-Momentum Chop**: Represents approximately **48% to 54%** of all market observations across BTCUSDT, ETHUSDT, and BNBUSDT.
- **Trending Bull**: Represents approximately **22% to 26%** of observations, concentrated primarily in Q1 2024, Q4 2024, and select parabolic expansion phases in 2025.
- **Trending Bear**: Represents approximately **14% to 18%** of observations, concentrated in mid-2024 pullbacks and the sustained 2026 corrections.
- **Volatile & Uncertain**: Represents **6% to 10%** of observations, coinciding with high-impact macroeconomic announcements, liquidations, and regime transition inflection points.

---

## 4. Regime-Specific Strategy Dynamics

Evaluating baseline strategies and entry filters across distinct regimes reveals:

### A. Ranging / Compression Regimes
- **Baseline Behavior**: Severe capital erosion. Trend-following breakout signals triggered during ranging regimes suffer from frequent false breakouts, hitting stop-losses before 1R targets are reached.
- **Filter Impact**: The H5 Volatility Bounds and H7 Confluence filters systematically reject candidates in this regime ($ATR\% < 0.8\%$ or $ADX < 25$), preventing 70–80% of losing trades.

### B. Trending Regimes (Bull & Bear)
- **Baseline Behavior**: When sustained trends occur, both Long and Short momentum setups capture large positive excursions.
- **Exit Policy Interaction**: The `BALANCED` exit policy outperforms `FIXED_BRACKET` in strong trending regimes by allowing trailing stops to ratchet profits without artificial caps, whereas `FIXED_BRACKET` truncates winning runners.

### C. Outlier Concentration & Single-Event Fragility
- In Milestone 4.3.2, H7's reported positive net PnL (+$14.02) was driven entirely by two correlated short trades entered during the May 28–29, 2026 market sell-off.
- In the expanded 2024–2026 history, when tested across multiple independent trending and ranging cycles, H7 and baseline strategies show that **no configuration achieves statistically stable positive expectancy across all regimes**.
- Entry filters function primarily as **capital preservation regimes** (reducing trade frequency and fee drag) rather than active alpha engines.

