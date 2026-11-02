# NEPTUNE — Milestone 4.6.2.4: Simulation Engine Integration & Architecture

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.4  
**Title:** Point-in-Time Execution Scheduling & Backtesting Engine Integration  
**Architecture Decision Record:** ADR-026  
**Document:** System Architecture & Event Replay Engine Integration  
**Status:** Approved & Verified  

---

## 1. Architectural Overview

Milestone 4.6.2.4 integrates the deterministic point-in-time execution contract into `HistoricalBacktestEngine` (`backend/app/simulation/engine.py`) through two modular components:

1. **`PointInTimeExecutionScheduler` (`backend/app/simulation/scheduling.py`):**
   Manages the lifecycle of approved orders (`ScheduledOrder`), enqueuing them at candle close and executing them deterministically at the next eligible candle open with full friction accounting.
2. **`NewsIntelligenceBoundary` (`backend/app/simulation/news_boundary.py`):**
   Enforces point-in-time eligibility barriers on news articles and macroeconomic calendar releases, filtering out forward-scheduled events, GDELT intraday noise, and future revisions.

---

## 2. Event Replay Lifecycle (Per Candle Step)

The simulation engine's main event loop advances chronologically through closed candle timestamps $T$. Under `ExecutionPolicy.NEXT_ELIGIBLE_PRICE`, each time step executes five strictly ordered phases:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Candle Step T (Timestamp: ts)                                          │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 0: Process Scheduled Orders at Candle Open                       │
│          • Query pending orders for current symbol                     │
│          • Validate data gap <= max_execution_gap_bars                 │
│          • Re-verify Circuit Breakers & portfolio limits               │
│          • Verify open price does not gap past stop loss               │
│          • Execute fill at curr_candle.open + friction                 │
│          • Deduct cash outflow & add to open_positions                 │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE A: Update Open Positions against Protective Brackets             │
│          • Prioritize pending reversal exits at candle open            │
│          • Evaluate stop-loss / trailing stop against curr_candle.low  │
│          • Credit cash inflows on closed trades                        │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE B: Update Trailing Stops & Evaluate Early Reversals              │
│          • Ratchet trailing stops in-place (one-way ratchet)           │
│          • Evaluate MultiFactorReversalDetector on surviving positions │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE C: Evaluate Strategy Candidates for Available Symbols            │
│          • Slice closed candle history [0 ... T] (capped at 300 bars)  │
│          • Query NewsIntelligenceBoundary for eligible events          │
│          • Run specialist agents (MarketScanner, Trend, Momentum, Vol) │
│          • StrategyAnalyst generates raw candidate signal              │
│          • Candidate-level filtering (Hypotheses 1 through 7)          │
│          • RiskManager evaluates the 5 Non-Negotiable Invariants       │
│          • If approved: schedule order for Bar T+1 Open                │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE D: Mark-to-Market Equity Snapshot                                │
│          • Value open positions at curr_candle.close                   │
│          • Record cash equity, total equity, and drawdown percentage   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Preservation of Realistic Execution Costs & Friction

The point-in-time scheduling pipeline preserves 100% of NEPTUNE's authoritative friction model (Rule A-01, Rule A-10):

1. **Executed Entry Price:**
   - For `LONG`:
     $$\text{Price}_{\text{entry}} = \text{Price}_{\text{open}}(T+1) \times \left(1 + \text{Slippage} + \frac{\text{Spread}}{2}\right)$$
   - For `SHORT`:
     $$\text{Price}_{\text{entry}} = \text{Price}_{\text{open}}(T+1) \times \left(1 - \text{Slippage} - \frac{\text{Spread}}{2}\right)$$
2. **Cash Outflow at Entry:**
   $$\text{Cash Outflow} = (\text{Position Size} \times \text{Price}_{\text{entry}}) + \text{Taker Fee}_{\text{entry}}$$
3. **Cash Inflow at Exit:**
   $$\text{Cash Inflow} = (\text{Position Size} \times \text{Price}_{\text{exit}}) - \text{Taker Fee}_{\text{exit}}$$
4. **Conservation of Capital:**
   All cash additions and subtractions are executed using exact Python `Decimal` arithmetic. Rounding errors and floating-point leakage are strictly prohibited.

---

## 4. Preservation of Risk Manager Authority

Persistent Engineering Rule S-04 mandates that the Risk Manager is the sole authorization authority in NEPTUNE. The scheduling integration maintains this authority without exception:

1. **Cryptographic Token Enforcement:**
   `PointInTimeExecutionScheduler.schedule_order()` requires a valid `risk_approval_token`. Orders cannot be scheduled from raw strategy signals alone.
2. **Zero Modification Authority:**
   The scheduler cannot alter `position_size`, modify suggested stops, or override a risk manager rejection.
3. **Committed Slot Tracking:**
   When evaluating candidate signals in Phase C, the Risk Manager's position count check treats both active open positions and pending scheduled orders as committed slots:
   $$\text{Total Committed} = N_{\text{open}} + N_{\text{scheduled}} \le \text{Max Concurrent Positions}$$
4. **Pre-Execution Circuit Breaker Check:**
   If portfolio drawdown breaches 5.0% or daily losses breach 2.0% between order scheduling and candle open fill, the scheduled order is immediately marked `OrderStatus.REJECTED`.

---

## 5. News Integration Boundary Architecture

The `NewsIntelligenceBoundary` serves as an immutable gatekeeper between raw external news feeds and the simulation engine:

```
[Raw News / Macro Records]
           │
           ▼
[NewsIntelligenceBoundary]
  ├─► Check 1: Forward Scheduled Macro Event? ────────► [EXCLUDE & QUARANTINE]
  ├─► Check 2: Missing Required Provenance? ──────────► [EXCLUDE: MISSING_PROVENANCE]
  ├─► Check 3: GDELT on Intraday (< 1d)? ─────────────► [EXCLUDE: GDELT_SUB_DAILY]
  ├─► Check 4: Source Verification Status REJECTED? ──► [EXCLUDE: REJECTED]
  ├─► Check 5: available_at > candle_close_dt? ───────► [EXCLUDE: AVAILABLE_AFTER_CUTOFF]
  ├─► Check 6: Revision available_at > cutoff? ───────► [FILTER TO VISIBLE REVISION]
  ├─► Check 7: Target Asset Irrelevant? ──────────────► [EXCLUDE: IRRELEVANT_ASSET]
  └─► Check 8: Multi-Article Cluster Duplicate? ──────► [DEDUPLICATE TO EARLIEST]
           │
           ▼
[Eligible Point-in-Time Events for Candle T]
```

This ensures that future research in Milestone 4.6.3 can investigate news-conditioned defensive filters and volatility gating under strict zero-leakage conditions.
