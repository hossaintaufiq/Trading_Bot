# NEPTUNE — Milestone 4.3.1: Quantitative Results Reconciliation

**Document Version**: 1.0.0  
**Audit Target**: Milestone 4.3 Empirical Findings & Hypothesis Ledger  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Governing Rules**: `AGENTS.md` (S-06 No Fabrication, S-07 Reproducible Evidence, A-01 Decimal Precision, A-10 Paper Execution Assumptions)  

---

## 1. Executive Summary

This reconciliation document provides an independent mathematical verification of the empirical results reported in **Milestone 4.3 (Entry Strategy Diagnosis & Regime-Aware Filtering)**.

Every baseline trade, hypothesis filter calculation, cash flow, transaction cost, and performance metric was recomputed from raw Parquet candle storage using deterministic Decimal arithmetic.

### Headline Reconciliation Findings:
1. **Baseline P&L & Friction Reconciliation (BIT-FOR-BIT VERIFIED)**:
   - The reported baseline net loss of **-$340.22** across 277 executed paper trades reconciles exactly.
   - Gross trading P&L was actually **positive (+$93.47)** (Gross Wins +$719.03, Gross Losses -$625.56).
   - Execution friction totaled **-$433.61** (Fees: $271.00, Slippage: $135.47, Spread: $27.14), completely converting a gross-profitable strategy into a net loser.
2. **Post-Hoc Trade Ledger Pruning Identified (METHODOLOGICAL DEFECT)**:
   - The reported H7 Confluence Net PnL of **+$35.78** (Train: -$1.51, Val: +$37.29, OOS: $0.00 across 65 trades) was computed by **post-hoc filtering an already-executed trade ledger** (`entry_diagnostics.csv`), rather than simulating real-time candidate evaluation in an event loop.
   - When losing trades are deleted post-hoc, portfolio capacity and slot availability are not accurately modeled.
3. **MFE/MAE Unit Distortion Reconciled (DIMENSIONAL DEFECT)**:
   - Milestone 4.3 reported an average MFE of **$1,223.69** on a $1,000 portfolio.
   - This was an unweighted average of raw price displacement per coin ($/coin) heavily distorted by BTC price levels ($65,000 vs BNB $580).
   - In actual portfolio cash USDT, the true average MFE is **$9.60** (+1.92% price move / +1.58R).

---

## 2. Bit-for-Bit Reconciliation of the 277 Baseline Trades

### Aggregate Accounting Ledger

| Accounting Component | Reported in Milestone 4.3 | Recalculated by Audit | Reconciliation Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Baseline Trades** | 277 | 277 | 0 | **EXACT MATCH** |
| **Winning Trades** | 97 | 97 | 0 | **EXACT MATCH** |
| **Losing Trades** | 180 | 180 | 0 | **EXACT MATCH** |
| **Win Rate** | 35.02% | 35.02% | 0.00% | **EXACT MATCH** |
| **Gross Wins ($)** | $719.03 | $719.03 | $0.00 | **EXACT MATCH** |
| **Gross Losses ($)** | -$625.56 | -$625.56 | $0.00 | **EXACT MATCH** |
| **Gross Trading P&L ($)** | +$93.47 | +$93.47 | $0.00 | **EXACT MATCH** |
| **Taker Exchange Fees ($)** | $271.00 | $271.00 | $0.00 | **EXACT MATCH** |
| **Simulated Slippage ($)** | $135.47 | $135.47 | $0.00 | **EXACT MATCH** |
| **Simulated Spread ($)** | $27.14 | $27.14 | $0.00 | **EXACT MATCH** |
| **Total Execution Friction ($)** | **-$433.61** | **-$433.61** | $0.00 | **EXACT MATCH** |
| **Net Realized P&L ($)** | **-$340.22** | **-$340.22** | $0.00 | **EXACT MATCH** |
| **Profit Factor** | 0.71 | 0.71 | 0.00 | **EXACT MATCH** |
| **Expectancy ($/trade)** | -$1.23 | -$1.23 | $0.00 | **EXACT MATCH** |

### Reconciliation Insight: The "Friction Tax"
Gross trading edge was positive ($+93.47$ across 277 trades, or $+0.34$ per trade before friction). However:
- Every round-trip trade incurred $0.10\%$ entry fee $+ 0.10\%$ exit fee $= 0.20\%$ fee.
- Slippage contributed $0.05\%$ per side $= 0.10\%$.
- Spread contributed $0.02\%$ round-trip.
- Total friction per round trip was **$0.32\%$ of position notional**.
- Across 277 trades, friction consumed $\$433.61$, which is **$464\%$ of the gross profits generated**.

---

## 3. Discrepancy & Root Cause: MFE / MAE Metric Distortion

### The Problem in Milestone 4.3 Reporting
Milestone 4.3 reported:
- *Average Maximum Favorable Excursion (MFE)*: **$1,223.69**
- *Average Maximum Adverse Excursion (MAE)*: **$412.50**

In a portfolio initialized with **$1,000.00 USDT**, an average excursion of **$1,223.69** would imply that trades were generating over 120% return per position on average.

### Mathematical Root Cause
In `backend/app/simulation/execution.py`, MFE and MAE were tracked as:
```python
# During active position update:
if pos.direction == "LONG":
    favorable = max(Decimal("0"), candle.high - pos.entry_price)
    adverse = max(Decimal("0"), pos.entry_price - candle.low)
```
1. `favorable` was stored as raw price displacement in quote units ($/coin).
2. For BTCUSDT at price $65,000, a 2% favorable move is **$1,300.00 / coin**.
3. For BNBUSDT at price $580, a 2% favorable move is **$11.60 / coin**.
4. Averaging across BTC, ETH, and BNB without normalizing by entry price or position size yielded:
$$\text{Reported MFE} = \frac{1}{N} \sum_{i=1}^N \Delta P_i \approx \$1,223.69$$
Over **95% of this metric was driven by BTC raw dollar volatility**, completely obscuring ETH and BNB behavior. Furthermore, formatting it as `$1,223.69` misled consumers into believing it represented portfolio dollar gains.

### Corrected Normalized MFE/MAE Formulation
To resolve this dimensional defect, Milestone 4.3.1 implemented three normalized MFE/MAE representations:

1. **Percentage of Entry Price**:
   $$MFE_{\%} = \frac{MFE_{\text{price}}}{P_{\text{entry}}} \times 100, \quad MAE_{\%} = \frac{MAE_{\text{price}}}{P_{\text{entry}}} \times 100$$
2. **R-Multiple (Normalized by Initial Risk)**:
   $$MFE_R = \frac{MFE_{\text{price}}}{|P_{\text{entry}} - StopLoss_{\text{initial}}|}, \quad MAE_R = \frac{MAE_{\text{price}}}{|P_{\text{entry}} - StopLoss_{\text{initial}}|}$$
3. **Portfolio Cash (USDT Value)**:
   $$MFE_{\text{cash}} = MFE_{\text{price}} \times \text{PositionSize}, \quad MAE_{\text{cash}} = MAE_{\text{price}} \times \text{PositionSize}$$

### Reconciliation Table: Raw vs Normalized Excursions

| Metric | Raw Milestone 4.3 Representation | Normalized Percentage | Normalized R-Multiple | Normalized Portfolio Cash (USDT) |
| :--- | :---: | :---: | :---: | :---: |
| **Average MFE** | $1,223.69 (distorted $/coin) | **+1.92%** | **+1.58R** | **+$9.60 USDT** |
| **Average MAE** | $412.50 (distorted $/coin) | **-0.65%** | **-0.53R** | **-$3.25 USDT** |
| **MFE / MAE Ratio** | 2.97 | 2.95 | 2.98 | 2.95 |

The underlying price movement was favorable (price moved $\sim 3\times$ further in profit than against the position before exiting), confirming that entry direction was generally correct, but exit capture and transaction costs eroded the net payoff.

---

## 4. Reconciliation of Post-Hoc Pruning vs True Replay

### Post-Hoc Trade Ledger Pruning Results (Milestone 4.3)
Milestone 4.3 evaluated filters by iterating over the 277 pre-generated baseline trades:

| Partition | Total Trades | Wins | Losses | Win Rate % | Net PnL (USDT) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Train (50%)** | 54 | 25 | 29 | 46.30% | -$1.51 | 0.99 |
| **Validation (25%)** | 11 | 8 | 3 | 72.73% | +$37.29 | 4.44 |
| **Out-of-Sample (25%)** | 0 | 0 | 0 | — | $0.00 | — |
| **Total Post-Hoc H7** | **65** | **33** | **32** | **50.77%** | **+$35.78** | **1.22** |

### Why Post-Hoc Pruning Differs from Candidate Replay:
1. **Dynamic Slot Unblocking**: When a candidate signal is rejected by a filter in a real backtest, the portfolio concurrency slot (cap of 2) remains open.
2. **Alternative Trade Execution**: In an event-driven backtest, subsequent valid candidate setups that were previously blocked by an open position can now be executed.
3. **Compounding Capital Effects**: In post-hoc pruning, cash flow timing is static; in candidate replay, available equity changes, affecting position sizing under Risk Manager rules.

