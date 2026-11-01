# NEPTUNE — Milestone 4.3: Experiment Protocol & Filter Hypothesis Testing

- **Document Version**: 1.0.0
- **Protocol Date**: 2026-11-02
- **Objective**: Formulate and rigorously evaluate regime-aware entry filters to determine if `trend_momentum_pullback_v1` can achieve positive net expectancy under realistic execution costs.
- **Governing Rules**: `AGENTS.md` (S-01, S-04, S-05, S-06, S-07, A-01, A-02, A-09, A-10, E-02, E-03)

---

## 1. Experimental Methodology & Anti-Leakage Invariants

To avoid data snooping, p-hacking, and look-ahead bias (Rule `S-05`), all evaluations adhere to the following protocol:

1. **Chronological Splitting (No Shuffling)**:
   - Financial time series have autocorrelation and regime persistence. Random cross-validation is strictly forbidden.
   - Every historical dataset is partitioned into three chronological windows:
     - **TRAIN (50% chronological)**: In-sample exploration and baseline parameter comparison.
     - **VALIDATION (25% chronological)**: Selection and tuning verification.
     - **OUT-OF-SAMPLE / OOS (25% chronological)**: Strictly held out and untouched until final evaluation. No parameter adjustments may be made based on OOS results.
2. **Two-Tier Evaluation Framework**:
   - **Tier 1: Frozen Common-Entry Evaluation**: Evaluates the mathematical filter effect on the identical universe of signals without portfolio allocation or concurrency changes. Isolates indicator edge from portfolio path effects.
   - **Tier 2: Portfolio-Level Simulation**: Re-runs the full event-driven engine (`HistoricalBacktestEngine`) with dynamic position sizing, Risk Manager authorization (Rule `S-04`), capital recycling, and max 2 concurrent positions.
3. **Realistic Execution Friction**:
   - All simulations enforce Binance VIP-0 paper execution assumptions: 0.10% taker fee, 0.05% slippage per side, and conservative intrabar resolution.
4. **Honesty & Falsification Invariant (Rules `S-06`, `S-07`)**:
   - Every filter is treated as an unproven null hypothesis. If a filter reduces trade count without improving net expectancy or remains net negative after transaction costs, this outcome is recorded honestly.

---

## 2. Dataset Chronological Partitions

| Symbol | Timeframe | Total Bars | Train Window (50%) | Validation Window (25%) | OOS Window (25%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BTCUSDT** | **4h** | 3,000 | Bars 0 – 1,499 (2025-06 to 2026-02) | Bars 1,500 – 2,249 (2026-02 to 2026-06) | Bars 2,250 – 2,999 (2026-06 to 2026-11) |
| **BTCUSDT** | **1h** | 5,000 | Bars 0 – 2,499 (2026-04 to 2026-07) | Bars 2,500 – 3,749 (2026-07 to 2026-09) | Bars 3,750 – 4,999 (2026-09 to 2026-11) |
| **BTCUSDT** | **15m** | 5,000 | Bars 0 – 2,499 (2026-09 to 2026-10) | Bars 2,500 – 3,749 (2026-10 to 2026-10) | Bars 3,750 – 4,999 (2026-10 to 2026-11) |
| **ETHUSDT** | **4h** | 3,000 | Bars 0 – 1,499 (2025-06 to 2026-02) | Bars 1,500 – 2,249 (2026-02 to 2026-06) | Bars 2,250 – 2,999 (2026-06 to 2026-11) |
| **ETHUSDT** | **1h** | 5,000 | Bars 0 – 2,499 (2026-04 to 2026-07) | Bars 2,500 – 3,749 (2026-07 to 2026-09) | Bars 3,750 – 4,999 (2026-09 to 2026-11) |
| **ETHUSDT** | **15m** | 5,000 | Bars 0 – 2,499 (2026-09 to 2026-10) | Bars 2,500 – 3,749 (2026-10 to 2026-10) | Bars 3,750 – 4,999 (2026-10 to 2026-11) |
| **BNBUSDT** | **4h** | 3,000 | Bars 0 – 1,499 (2025-06 to 2026-02) | Bars 1,500 – 2,249 (2026-02 to 2026-06) | Bars 2,250 – 2,999 (2026-06 to 2026-11) |
| **BNBUSDT** | **1h** | 5,000 | Bars 0 – 2,499 (2026-04 to 2026-07) | Bars 2,500 – 3,749 (2026-07 to 2026-09) | Bars 3,750 – 4,999 (2026-09 to 2026-11) |
| **BNBUSDT** | **15m** | 5,000 | Bars 0 – 2,499 (2026-09 to 2026-10) | Bars 2,500 – 3,749 (2026-10 to 2026-10) | Bars 3,750 – 4,999 (2026-10 to 2026-11) |

---

## 3. Formal Hypotheses Specification (H1 – H7)

### Hypothesis 1: Trend Strength Filter (ADX & Directional Index)
- **Null Hypothesis ($H_{1,0}$)**: Filtering signals by higher ADX does not improve trade expectancy.
- **Alternative Hypothesis ($H_{1,A}$)**: Restricting entry signals to confirmed strong trends ($ADX \ge 25$ or $ADX \ge 30$) eliminates low-expectancy chop and significantly improves net PnL.
- **Mathematical Specification**:
  - Accept signal if $ADX_{14}(T) \ge \theta_{adx}$ where $\theta_{adx} \in \{25.0, 30.0\}$.
  - Directional consistency: For LONG, require $+DI_{14}(T) > -DI_{14}(T)$; for SHORT, require $-DI_{14}(T) > +DI_{14}(T)$.

### Hypothesis 2: Higher Timeframe (HTF) Trend Alignment
- **Null Hypothesis ($H_{2,0}$)**: Aligning entries with a higher timeframe trend does not reduce false pullbacks.
- **Alternative Hypothesis ($H_{2,A}$)**: Lower timeframe entries (15m, 1h) that oppose the higher timeframe macro trend (1h, 4h) suffer high stop-out rates. Requiring HTF EMA alignment ($EMA_{20}^{HTF} > EMA_{50}^{HTF}$ for Long, $EMA_{20}^{HTF} < EMA_{50}^{HTF}$ for Short) eliminates counter-trend traps.
- **Mathematical Specification**:
  - For candle $T$ on timeframe $TF$, retrieve the latest confirmed *closed* candle on $HTF(TF)$ at or before $T$.
  - Rule `S-05` compliance: Never look ahead; only use HTF candles closed strictly $\le T$.
  - Long condition: $EMA_{20}(HTF) > EMA_{50}(HTF)$ and $Close(HTF) > EMA_{50}(HTF)$.
  - Short condition: $EMA_{20}(HTF) < EMA_{50}(HTF)$ and $Close(HTF) < EMA_{50}(HTF)$.

### Hypothesis 3: Momentum Acceleration & Pullback Confirmation
- **Null Hypothesis ($H_{3,0}$)**: Momentum indicators cannot time pullbacks better than the baseline.
- **Alternative Hypothesis ($H_{3,A}$)**: Pullback entries enter either too early (falling knives) or too late (exhaustion). Requiring MACD histogram expansion in the trade direction ($Hist(T) > Hist(T-1)$ for Long; $Hist(T) < Hist(T-1)$ for Short) verifies that momentum has resumed in the trend direction before entry.
- **Mathematical Specification**:
  - Long: $MACD\_Hist(T) > MACD\_Hist(T-1)$ and $42.0 \le RSI(T) \le 62.0$.
  - Short: $MACD\_Hist(T) < MACD\_Hist(T-1)$ and $38.0 \le RSI(T) \le 58.0$.

### Hypothesis 4: Volume & Liquidity Confirmation Filter
- **Null Hypothesis ($H_{4,0}$)**: Trading volume at entry does not correlate with trade profitability.
- **Alternative Hypothesis ($H_{4,A}$)**: Low-volume entries ($RVOL < 0.80$) represent illiquid drifting price action that fails to sustain follow-through. Requiring $RVOL \ge 1.00$ (or $RVOL \ge 0.90$) significantly improves win rate.
- **Mathematical Specification**:
  - $RVOL(T) = \frac{Volume(T)}{\frac{1}{20}\sum_{i=0}^{19} Volume(T-i)}$
  - Accept signal only if $RVOL(T) \ge \theta_{vol}$ with $\theta_{vol} \in \{0.80, 1.00\}$.

### Hypothesis 5: Volatility Bounds Filter (ATR / Price)
- **Null Hypothesis ($H_{5,0}$)**: Volatility regimes do not affect strategy expectancy.
- **Alternative Hypothesis ($H_{5,A}$)**: Extreme low volatility causes trades to stagnate and get ground down by fees; extreme high volatility causes erratic stop-outs. Enforcing an ATR volatility band ($0.80\% \le \frac{ATR_{14}(T)}{Close(T)} \le 3.0\%$) optimizes trade survival.
- **Mathematical Specification**:
  - $VolPct(T) = \frac{ATR_{14}(T)}{Close(T)} \times 100\%$
  - Filter condition: $0.80\% \le VolPct(T) \le 3.00\%$.

### Hypothesis 6: Regime Confidence Filter
- **Null Hypothesis ($H_{6,0}$)**: Market Scanner regime classification provides no predictive value.
- **Alternative Hypothesis ($H_{6,A}$)**: Rejecting signals with regime confidence $< 0.65$ eliminates ambiguous market states where trends are transitioning into range-bound chop.
- **Mathematical Specification**:
  - Accept signal only if $Regime\_State \in \{\text{TRENDING\_BULL}, \text{TRENDING\_BEAR}\}$ and $Confidence \ge 0.65$.

### Hypothesis 7: Confluence Ensemble
- **Null Hypothesis ($H_{7,0}$)**: Combining multiple filters destroys sample size without delivering positive expectancy.
- **Alternative Hypothesis ($H_{7,A}$)**: Combining orthogonal filters (e.g. Trend Strength $ADX \ge 25$ + Volume $RVOL \ge 0.90$ + HTF Alignment) produces positive net expectancy and statistically robust edge after all transaction costs.

---

## 4. Evaluation Metrics & Success Criteria

1. **Net Expectancy ($E$)**:
   $$E = \frac{\sum NetPnL}{N_{trades}}$$
   Target: $E > \$0.00$ (positive net expectation after fees and slippage).
2. **Profit Factor ($PF$)**:
   $$PF = \frac{\sum GrossGains}{\sum GrossLosses}$$
   Target: $PF > 1.05$.
3. **Trade Sample Size ($N$)**:
   Minimum 20 trades in the evaluation window to avoid micro-sample delusion.
4. **Statistical Significance**:
   Welch's $t$-test or bootstrap permutation test confirming $p < 0.05$ against zero expectancy.

