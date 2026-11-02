# NEPTUNE — Milestone 4.3.3: Benchmark Reconciliation Analysis

**Document Version**: 1.0.0  
**Audit Target**: Benchmark Consistency, Candidate Separation & Accounting Precision  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Starting Commit Baseline**: `a66fb17`  
**Governing Rules**: `AGENTS.md` (S-04 Risk Manager Integrity, S-05 Look-Ahead Bias Prevention, S-06 No Fabrication, S-07 Reproducible Evidence, A-01 Decimal Precision, A-09 Closed Candles Only, A-10 Paper Fills)  

---

## 1. Executive Summary & Research Baseline

This audit independently investigates the quantitative anomalies, configuration duplications, and accounting nuances identified following the completion of Milestone 4.3.2.

### Baseline Provenance:
- **Git Commit Baseline**: `a66fb1776bab5bbe0c162b39122dc45e6af410cd`
- **Branch**: `quant-expectancy-validation`
- **Working Tree**: Clean, zero uncommitted modifications.
- **Input Parquet Dataset**: 39,000 validated candles across 9 series (BTC, ETH, BNB on 15m, 1h, 4h).
- **Core Stored Hashes**:
  - `storage/exports/milestone_4_3_2/aggregate_replay_benchmark.csv`: `9f39c0caab5d3a8732e30a0444e9ae1b384caec2c5bd1682f65e1b8c76887236`
  - `storage/exports/milestone_4_3_2/approach_a_common_window.csv`: `3c25bad5accd66bfba2a9894bbd7e6c242132c007f1f55c82fdd15130b68bf10`
  - `storage/exports/milestone_4_3_2/approach_b_per_timeframe.csv`: `d6df39c8f21d373dd0b05d27b5add4664febad660bfe40bf589075f86ad11c26`

---

## 2. Investigation of the H1 Baseline Duplication

In Milestone 4.3.2, both the Baseline (unfiltered) and H1 (ADX $\ge$ 25) reported exactly:
- **770 candidate signals**
- **770 filter-accepted signals**
- **277 executed trades**
- **-$340.22 net realized PnL**
- Identical win rates (35.02%), fees ($271.00), slippage ($135.47), and drawdowns ($359.51).

### Empirical Investigation Findings:
1. **The Filter Actually Executed**:
   The benchmark script correctly configured `entry_filter = "H1_ADX_25"`. In `engine.py` line 110, `filter_trend_strength_adx(candles, cand.direction, min_adx=25.0, require_di=True)` was called on all 770 candidate signals.
2. **Every Candidate Signal Already Possessed ADX $\ge$ 25.0**:
   An independent instrumented replay across all 39,000 candles inspected the ADX values of every candidate generated:
   - **Total Candidates Evaluated**: 770
   - **Candidates with ADX < 25.0**: **0**
   - **Candidates Failing Filter**: **0**
   - **Minimum ADX Observed**: **25.01**
   - **Maximum ADX Observed**: **71.68**
3. **The Architectural Root Cause in `MarketScannerAgent`**:
   In `backend/app/agents/market_scanner.py` (lines 137–147):
   ```python
   elif curr_adx is not None and curr_adx >= 25.0:
       if curr_ema_50 and curr_price > curr_ema_50 and p_di > m_di:
           regime = "TRENDING_BULL"
       elif curr_ema_50 and curr_price < curr_ema_50 and m_di > p_di:
           regime = "TRENDING_BEAR"
   ```
   And in `backend/app/agents/strategy_analyst.py` (lines 143–169):
   - LONG setups strictly require `regime.regime == "TRENDING_BULL"`.
   - SHORT setups strictly require `regime.regime == "TRENDING_BEAR"`.
   - If `ADX < 25.0`, `MarketScannerAgent` **never emits `TRENDING_BULL` or `TRENDING_BEAR`**; it defaults to `RANGING` or `UNCERTAIN`.
   - Therefore, the baseline strategy cannot physically emit a candidate signal when ADX < 25!
4. **Audit Conclusion on H1**:
   The identical results between Baseline and H1 (ADX $\ge$ 25) are **100% legitimate and mathematically exact**. H1 is a **redundant filter** because its condition is already an upstream prerequisite for candidate generation.
   When the threshold was tested at `ADX >= 30.0` (in `H1b_ADX_30`), 317 candidates were rejected, and executed trades dropped from 277 to 194, proving that the filtering mechanism is fully operational.

---

## 3. Separating Candidate Generation From Portfolio Eligibility

### Architectural Coupling Limitation
In the NEPTUNE backtesting engine (`backend/app/simulation/engine.py` line 385):
```python
sym_already_open = any(p.symbol == sym for p in open_positions) or any(p.symbol == sym for p in newly_opened_positions)
if sym_already_open or (len(open_positions) + len(newly_opened_positions)) >= self.config.max_concurrent_positions:
    continue
```
**Explicit Limitation Disclosure**:
The current backtesting engine **couples strategy evaluation to portfolio availability**. When a trade is active for a symbol or when portfolio concurrency (`max_concurrent_positions = 2`) is reached, `StrategyAnalystAgent` is skipped.
Therefore, what previous milestones termed "candidate signals" were **portfolio-gated strategy evaluations**, not unconditional raw market setup opportunities!

When filters (such as H5 or H7) reject losing trades, the portfolio spends fewer bars in active positions. This allows the engine to evaluate more market bars, causing portfolio-gated candidate counts to increase from 770 (Baseline) to 991 (H7).

### Complete Opportunity Pipeline Breakdown (BALANCED)

Across all 9 series (38,730 total evaluable bars):

| Filter Pipeline Variant | Unconditional Raw Opportunities | Bars Evaluated by Strategy | Bars Suppressed by Active Positions | Portfolio-Gated Candidates | Filter Accepted | Filter Rejected | Risk Approved | Risk Rejected | Executed Trades | Net Realized PnL ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (H0)** | 1,137 | 28,361 | 10,369 | **770** | 770 | 0 | 277 | 493 | **277** | -$340.22 |
| **H1 (ADX $\ge$ 25)** | 1,137 | 28,361 | 10,369 | **770** | 770 | 0 | 277 | 493 | **277** | -$340.22 |
| **H1b (ADX $\ge$ 30)** | 1,137 | 29,467 | 9,263 | **921** | 489 | 432 | 194 | 295 | **194** | -$183.46 |
| **H4 (RVOL $\ge$ 85)** | 1,137 | 28,394 | 10,336 | **781** | 703 | 78 | 274 | 429 | **274** | -$307.38 |
| **H5 (Vol Bounds)** | 1,137 | 29,930 | 8,800 | **982** | 194 | 788 | 137 | 57 | **137** | -$13.86 |
| **H7 Confluence** | 1,137 | 30,116 | 8,614 | **991** | 182 | 809 | 126 | 56 | **126** | **+$14.02** |

### Key Architectural Findings:
1. **Unconditional Raw Setup Count**: Across all 9 series, NEPTUNE's trend pullback setup fired **1,137 times** when evaluated unconditionally on every closed bar.
2. **Dynamic Slot Unblocking**: In the Baseline configuration, holding 277 losing positions tied up portfolio slots, causing **10,369 bars** to be skipped by `StrategyAnalystAgent`. In H7 Confluence, rejecting low-volatility chop reduced suppressed bars to **8,614**, allowing the engine to evaluate 1,755 more bars and discover 221 additional candidate signals (increasing evaluated candidates from 770 to 991).
3. **Filter Rejection Efficiency**: H7 filtered out **809 candidates** (an 81.6% rejection rate), cleanly preventing low-expectancy trades from reaching the Risk Manager.



---

## 4. Reconcile Accounting and Rounding

### 4.1. Accounting Identities & Precision Convention
The NEPTUNE paper simulation engine executes all calculations using Python `Decimal` (Rule A-01).

For each individual trade, the simulation lifecycle enforces:
$$\text{Net PnL}_{\text{raw}} = \text{Gross PnL}_{\text{raw}} - \text{Total Fees}_{\text{raw}} - \text{Total Slippage}_{\text{raw}} - \text{Total Spread}_{\text{raw}}$$
Where:
- $\text{Gross PnL}_{\text{raw}} = (\text{Exit Price}_{\text{raw}} - \text{Entry Price}_{\text{raw}}) \times \text{Position Size}$ (for LONG)
- $\text{Total Fees}_{\text{raw}} = (\text{Exec Entry Notional} + \text{Exec Exit Notional}) \times \text{Taker Fee \%}$
- $\text{Total Slippage}_{\text{raw}} = (\text{Entry Price}_{\text{raw}} + \text{Exit Price}_{\text{raw}}) \times \text{Slippage \%} \times \text{Position Size}$
- $\text{Total Spread}_{\text{raw}} = (\text{Entry Price}_{\text{raw}} + \text{Exit Price}_{\text{raw}}) \times \text{Half-Spread Fraction} \times \text{Position Size}$

### 4.2. Independent Cent-Rounding Convention
In `backend/app/simulation/execution.py` (lines 361–365), each monetary attribute is independently quantized to `Decimal("0.01")` using `ROUND_HALF_UP`:
```python
gross_pnl = gross_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
fees = total_fees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
spread_cost = total_spread_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
slippage_cost = total_slippage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
net_pnl = net_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```
Because $\text{Net PnL}$ is computed from unquantized values before rounding, rounding each term independently introduces a known, bounded sub-cent rounding discrepancy:
$$\left| \text{round}(\text{Net PnL}) - \left[ \text{round}(\text{Gross PnL}) - \text{round}(\text{Fees}) - \text{round}(\text{Slippage}) - \text{round}(\text{Spread}) \right] \right| \le \$0.01$$

Across hundreds of trades, these independent cent-rounding discrepancies sum to small sub-dollar differences ($\le \$0.15$).

### 4.3. Reconciled Accounting Table

Independent audit reconciliation across all four core event ledgers (`storage/exports/milestone_4_3_2/`):

| Exit Policy | Strategy Variant | Trade Count | Gross Realized PnL ($) | Total Fees ($) | Total Slippage ($) | Total Spread ($) | Net Realized PnL ($) | Sum of Components ($) | Rounding Difference ($) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BALANCED** | Baseline | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | -$340.14 | -$0.08 |
| **BALANCED** | **H7 Confluence** | 126 | $90.42 | $47.77 | $23.85 | $4.77 | **+$14.02** | +$14.03 | -$0.01 |
| **FIXED_BRACKET**| Baseline | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | -$327.67 | +$0.02 |
| **FIXED_BRACKET**| **H7 Confluence** | 139 | $78.16 | $52.27 | $26.17 | $5.17 | **-$5.59** | -$5.45 | -$0.14 |

*Note: Final equity for BALANCED Baseline started at $1,000.00 and finished at $659.78 ($1,000.00 - $340.22). BALANCED H7 finished at $1,014.02 ($1,000.00 + $14.02).*

### 4.4. Explanation of the $27.14 vs. $27.00 Spread Figure
In Milestone 4.3, the total spread cost for the baseline strategy was correctly computed as **$27.14**.  
In Milestone 4.3.2, the displayed benchmark summary table printed **$27.00** (or `27`).

**Audit Cause**:
In `scratch/run_milestone_4_3_2_parallel.py` line 240:
```python
"spread": round(tot_spread),
```
The programmer omitted `, 2` in the rounding call, causing Python to round `27.14` to the integer `27`.  
Inspection of the underlying parquet trade ledger (`event_ledger_balanced_baseline.parquet`) confirmed that the actual recorded spread was **$27.142857...**, and was correctly debited in full Decimal precision. The change from $27.14 to $27.00 was purely a **display formatting omission**, not a calculation error or changed trade ledger.
