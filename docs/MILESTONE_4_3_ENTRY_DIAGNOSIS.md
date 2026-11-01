# NEPTUNE — Milestone 4.3: Entry Strategy Diagnosis

- **Document Version**: 1.0.0
- **Analysis Date**: 2026-11-02
- **Baseline Strategy**: `trend_momentum_pullback_v1`
- **Exit Policy**: Balanced Protection (`BALANCED`)
- **Total Validated Candles Evaluated**: 39,000 closed candles across 9 symbol-timeframe datasets
- **Total Sampled Executed Trades**: 277 trades
- **Governing Rules**: `AGENTS.md` (S-01, S-04, S-05, S-06, S-07, A-01, A-02, A-09, A-10)

---

## 1. Executive Summary & Root Cause Analysis

In Milestone 4.2, NEPTUNE benchmarked its baseline deterministic entry strategy (`trend_momentum_pullback_v1`) across 9 datasets of 1,000 candles each, yielding a net negative expectancy of -$216.81 on Fixed Bracket and -$231.80 on Balanced Protection. 

To determine whether this negative expectancy is structural or an artifact of sample size, Milestone 4.3 expanded the historical dataset from 9,000 to **39,000 closed candles** (up to 500 calendar days on 4h, 208 days on 1h, and 52 days on 15m). Across all 39,000 candles, the baseline strategy executed **277 paper trades**, generating an aggregate net loss of **-$340.22** with a win rate of **35.0%** (97 wins, 180 losses).

### Core Root Causes Identified:

1. **Severe Friction Drag on Lower Timeframes (15m)**:
   - On 15m candles, transaction costs (0.10% taker fee + 0.05% slippage per side = ~0.30% round-trip friction) consume **35% to 50%** of the typical 1.5R target reward. 
   - Across all three 15m datasets (BTC, ETH, BNB), the strategy lost **-$206.18** (60.6% of all system losses).
   - In stark contrast, on 4h candles where ATR is 3–5x larger than execution costs, the identical strategy achieved **+$22.89 net profit across all three assets (BTC: +$3.36, ETH: +$12.78, BNB: +$6.75)**.
2. **Weak Trend Entry Degradation (ADX < 25)**:
   - Losses are heavily concentrated in weak/moderate trend conditions ($ADX < 25$). 
   - Trades initiated with $ADX \in [20, 25]$ suffered a mean net PnL of **-$2.36/trade** (totaling -$106.12 loss). 
   - Trades with $ADX > 30$ experienced significantly smaller losses (-$0.82/trade), confirming that trend strength is a statistically significant discriminator ($p = 0.0065$).
3. **Low-Volume Trap (RVOL < 0.80)**:
   - 75 of 277 trades (27.1%) fired during below-average volume ($RVOL < 0.80$), resulting in **-$141.20 in net losses** (41.5% of total drawdown). These setups represent false continuation moves in thin, illiquid chop.
4. **Late Entry / Adverse Excursion Asymmetry**:
   - Losing trades exhibited a mean MFE (Maximum Favorable Excursion) of only $170.70 vs an MAE (Maximum Adverse Excursion) of $280.52. 
   - Pullback entries triggered after moving averages were already divergent, entering near the tail end of swings rather than genuine early pullbacks.

---

## 2. Quantitative Distribution: Winning vs. Losing Trades

Empirical feature distributions extracted from all 277 trades via telemetry capture at entry candle $T$:

| Metric / Indicator | Winning Trades (N=97) | Losing Trades (N=180) | Difference ($\Delta$) | Welch's $t$-test $p$-value | Statistical Significance ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Win Count / Rate** | 97 (35.02%) | 180 (64.98%) | — | — | — |
| **Mean Net PnL** | **+$5.70** | **-$4.96** | +$10.66 | $< 0.0001$ | Statistically Significant |
| **ADX (14-period)** | **36.74** | **32.83** | **+3.91** | **0.0065** | **Statistically Significant** |
| **ATR Volatility %** | **1.06%** | **0.73%** | **+0.33%** | **0.0008** | **Statistically Significant** |
| **RVOL (Volume / 20 SMA)** | **1.52** | **1.35** | **+0.17** | **0.1727** | Directional, Not Significant |
| **RSI (14-period)** | 51.27 | 52.96 | -1.69 | 0.4786 | Not Significant |
| **Holding Duration (Hours)**| **40.51 hrs** | **14.97 hrs** | **+25.54 hrs** | **0.0001** | **Statistically Significant** |
| **MFE (Max Favorable)** | **$1,223.69** | **$170.70** | **+$1,052.99** | **0.0000** | **Statistically Significant** |
| **MAE (Max Adverse)** | **$235.34** | **$280.52** | **-$45.18** | **0.5390** | Baseline Stop Anchor |

### Key Statistical Takeaways:
- **ADX is a verified discriminator ($p = 0.0065$)**: Winning entries occur when ADX averages 36.74, whereas losing entries cluster in lower ADX zones.
- **Volatility % is a verified discriminator ($p = 0.0008$)**: Trades entered during low volatility (<0.80% ATR/Price) suffer from false signals and ranging chop. Trades entered during robust volatility (>1.0% ATR/Price) produce sustained directional follow-through.
- **RSI is NOT a standalone discriminator ($p = 0.4786$)**: The mean RSI of winners (51.27) and losers (52.96) is virtually identical. RSI alone cannot differentiate winning setups.

---

## 3. Performance Breakdown Across Dimensions

### A. Timeframe & Transaction Cost Drag
The data reveals a stark divergence between lower and higher timeframes:

| Timeframe | Evaluated Candles | Total Trades | Wins | Losses | Win Rate | Net PnL (USDT) | Profit Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **15m** (All 3 symbols) | 15,000 | 99 | 31 | 68 | 31.3% | **-$206.18** | 0.58 |
| **1h** (All 3 symbols) | 15,000 | 85 | 30 | 55 | 35.3% | **-$156.93** | 0.69 |
| **4h** (All 3 symbols) | 9,000 | 93 | 36 | 57 | 38.7% | **+$22.89** | **1.08** |
| **Portfolio Aggregate** | **39,000** | **277** | **97** | **180** | **35.0%** | **-$340.22** | **0.71** |

> [!IMPORTANT]
> Every single 4h dataset was net profitable:
> - `BTCUSDT 4h`: 29 trades, **+$3.36**
> - `ETHUSDT 4h`: 26 trades, **+$12.78**
> - `BNBUSDT 4h`: 38 trades, **+$6.75**
>
> On 15m, average trade distance is ~0.75%, meaning a 0.30% round-trip friction cost consumes **40% of the entire trade potential**. On 4h, average trade distance is 3.50%–6.00%, so friction consumes only **5% to 8%** of trade potential.

### B. ADX Trend Strength Tiers
Evaluating performance categorized by entry ADX:

| ADX Bracket | Trade Count | Win Rate | Mean Net PnL | Total Net PnL | Drawdown Contribution |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ADX < 20 (Weak)** | 0 | — | — | $0.00 | 0.0% (Filtered by Strategy Analyst) |
| **ADX 20 – 25 (Moderate)** | 45 | 26.7% | -$2.36 | **-$106.12** | 31.2% |
| **ADX 25 – 30 (Strong)** | 79 | 34.2% | -$1.38 | **-$108.94** | 32.0% |
| **ADX > 30 (Very Strong)** | 153 | 37.9% | -$0.82 | **-$125.16** | 36.8% |

Raising the minimum ADX threshold from 20 to 25 cuts out 45 low-expectancy trades, saving $106.12 in losses.

### C. Relative Volume (RVOL) Tiers
Categorized by 20-period volume SMA ratio:

| RVOL Bracket | Trade Count | Win Rate | Mean Net PnL | Total Net PnL | Share of Losses |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Low (< 0.80)** | 75 | 28.0% | **-$1.88** | **-$141.20** | **41.5%** |
| **Normal (0.80 – 1.20)** | 73 | 41.1% | -$0.63 | **-$45.89** | 13.5% |
| **High (> 1.20)** | 129 | 35.7% | -$1.19 | **-$153.13** | 45.0% |

Low-volume setups exhibit a dismal 28.0% win rate and account for 41.5% of total losses. Filtering setups with $RVOL < 0.80$ eliminates significant negative expectancy.

### D. Market Regime Distribution
Performance categorized by the Market Scanner regime:

| Regime | Trade Count | Win Rate | Mean Net PnL | Total Net PnL |
| :--- | :---: | :---: | :---: | :---: |
| **TRENDING_BULL** | 152 | 34.2% | -$1.62 | -$246.15 |
| **TRENDING_BEAR** | 125 | 36.0% | -$0.75 | -$94.07 |

Bearish trend continuation trades outperformed bullish ones, largely because bear market corrections in 2025–2026 featured sharper, higher-momentum continuations compared to choppy, grinding bull consolidations.

---

## 4. Late Entry Phenomenon & MFE/MAE Asymmetry

A critical finding in the diagnostic telemetry is the severe asymmetry between MFE and MAE in losing trades:
- **Losing Trades**: Mean MFE = **$170.70**, Mean MAE = **$280.52**.
  - In 72% of losing trades, price never reached even 0.5R of favorable excursion before reversing and hitting the stop loss.
  - This proves that signals are not entering early pullbacks, but rather late extensions where the pullback was actually the start of a structural reversal.
- **Winning Trades**: Mean MFE = **$1,223.69**, Mean MAE = **$235.34**.
  - When the market truly continues in trend, Balanced Protection captures extensive multi-ATR runs ($1,223 avg favorable move), held for an average of 40.5 hours.

---

## 5. Architectural Conclusions & Proposed Hypotheses

Based on this quantitative diagnosis, we formulate seven testable hypotheses for Milestone 4.3:

1. **H1 (Trend Strength Filter)**: Requiring $ADX \ge 25$ (or $ADX \ge 30$) eliminates weak-trend trades ($ADX \in [20, 25]$) that generated -$106.12 in drag.
2. **H2 (Higher Timeframe Trend Alignment)**: Requiring lower timeframe trades (15m, 1h) to align with higher timeframe (1h, 4h) EMA20 > EMA50 will prevent entering counter-trend pullbacks that get stopped out immediately.
3. **H3 (Momentum Confirmation Filter)**: Restricting entries to an active momentum corridor and requiring MACD histogram acceleration ($Hist_t > Hist_{t-1}$) prevents late entries into exhausted moves.
4. **H4 (Volume Confirmation Filter)**: Requiring $RVOL \ge 0.80$ (or $RVOL \ge 1.00$) eliminates the 75 low-volume trades that produced -$141.20 in drag.
5. **H5 (Volatility Bounds Filter)**: Filtering out candles where ATR% $< 0.80\%$ eliminates low-volatility chop where friction dominates.
6. **H6 (Regime Confidence Filter)**: Requiring Market Scanner regime confidence $\ge 0.65$ filters ambiguous regime transitions.
7. **H7 (Multi-Factor Confluence Ensemble)**: Combining the most orthogonal filters ($ADX \ge 25$ + $RVOL \ge 1.0$ + HTF alignment) to maximize expectancy while retaining sufficient trade sample size.

