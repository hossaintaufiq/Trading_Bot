# NEPTUNE Phased Development Roadmap (v1.0.0)

## Document Information
- **Project**: NEPTUNE — Autonomous Market Intelligence & Paper Trading Platform
- **Document Version**: 1.0.0
- **Status**: Approved / Engineering Execution Plan
- **Author**: Neptune Program Director & Core Technical Leads
- **Date**: 2026-11-01

---

## 1. Executive Summary & Delivery Strategy

The NEPTUNE development roadmap follows a rigorous, dependency-ordered 10-milestone engineering pipeline. Each milestone represents a discrete, testable increment of system capability, progressing methodically from data infrastructure and core algorithms up to presentation tier rendering and end-to-end operational hardening.

```mermaid
gantt
    title NEPTUNE Engineering Milestones (v1.0)
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundations
    M1: Foundation & Architecture Specs         :done,    m1, 2026-11-01, 2026-11-03
    M2: Data Infrastructure & Storage Tier     :active,  m2, 2026-11-03, 2026-11-08
    section Phase 2: Core Engines
    M3: Backend Core, FSM & Agent Swarm Stubs   :         m3, 2026-11-08, 2026-11-14
    M4: Strategy Engine & Historical Backtester :         m4, 2026-11-14, 2026-11-19
    M5: Time Machine Simulation Engine          :         m5, 2026-11-19, 2026-11-24
    M6: Risk Gatekeeper & Paper Matching Engine :         m6, 2026-11-24, 2026-11-29
    section Phase 3: Presentation Tier
    M7: Frontend Scaffold & Design System       :         m7, 2026-11-29, 2026-12-04
    M8: Frontend Dashboards & Visualizations    :         m8, 2026-12-04, 2026-12-11
    section Phase 4: Hardening & Release
    M9: Analytics & Performance Auditing        :         m9, 2026-12-11, 2026-12-15
    M10: E2E Integration, Hardening & v1.0 Launch:        m10, 2026-12-15, 2026-12-20
```

---

## 2. Milestone Breakdown & Specification

---

### Milestone 1 — Foundation & Engineering Standards
- **Scope**: System architecture definition, complete documentation suite, repository directory initialization, and baseline configuration.
- **Deliverables**:
  - Comprehensive documentation suite (12 core architecture specifications in `/docs`).
  - Directory skeleton for monorepo: `backend/`, `frontend/`, `storage/`, `scripts/`, `infrastructure/`.
  - Python project dependencies setup (`pyproject.toml`, virtual environment specifications).
  - Pre-commit formatting hooks, Ruff linter rules, TypeScript strict config.
- **Success Criteria**:
  - All 12 documentation documents fully written, validated, and approved.
  - Zero syntax or schema discrepancies between backend and frontend contracts.
- **Effort Rating**: **M** (Medium)

---

### Milestone 2 — Data Infrastructure & Ingestion Engine
- **Scope**: Live market data client, ring buffers, Parquet historical store, SQLite schema, migration runner, and repository pattern implementations.
- **Deliverables**:
  - Binance Public REST & WebSocket client (`app/data/ingest.py`) with automatic reconnect.
  - In-memory candle ring buffer (`app/data/buffer.py`) supporting $O(1)$ lookups.
  - Custom SQLite migration runner and 12-table schema in `storage/neptune_trading.db`.
  - Apache Parquet storage manager (`app/data/parquet/store.py`) with monthly partitioning.
  - Concrete repository implementations (`IMarketDataRepository`, `IOrderRepository`, etc.).
- **Success Criteria**:
  - Continuous ingestion of 1m/5m candles for BTCUSDT, ETHUSDT, SOLUSDT with zero memory leaks.
  - Parquet write/read benchmark achieves $> 500,000$ candles/sec.
  - Migration runner successfully initializes and verifies schema integrity.
- **Effort Rating**: **L** (Large)

---

### Milestone 3 — Backend Core, FSM & Agent Swarm
- **Scope**: FastAPI application server, WebSocket hub, BaseAgent abstraction, 10 specialist agent stubs with typed I/O contracts, and Central Brain finite state machine.
- **Deliverables**:
  - FastAPI server setup with Lifespan management and CORS configuration.
  - Asynchronous WebSocket hub (`/ws/*`) with channel broadcast mechanics.
  - `BaseAgent` class with timeout safeguards and latency profiling.
  - All 10 specialist agent implementations with Pydantic contracts.
  - 11-State Central Brain state machine driver (`app/brain/state_machine.py`).
  - Core `/health`, `/markets`, and `/agents` REST endpoints.
- **Success Criteria**:
  - Central Brain steps deterministically through states on closed candle triggers.
  - All 10 agents execute within their latency budgets ($< 50$ ms).
  - WebSocket hub broadcasts mock events to concurrent subscribers with $< 10$ ms internal latency.
- **Effort Rating**: **XL** (Extra Large)

---

### Milestone 4 — Quantitative Strategy Laboratory & Backtester
- **Scope**: Implementation of 4 built-in strategies, strategy registry, parameter schema validation, and vectorized historical backtesting engine.
- **Deliverables**:
  - `IStrategy` protocol definition and strategy registry.
  - 4 baseline strategy implementations:
    1. Trend Follower (EMA Ribbon & ADX)
    2. Mean Reversion (Bollinger Bands & RSI)
    3. Volatility Breakout (ATR & Volume Surge)
    4. Dual Momentum Oscillator (MACD & StochRSI)
  - Vectorized historical backtesting engine (`app/strategies/backtester.py`) querying Parquet archives.
- **Success Criteria**:
  - Backtests execute across 1 year of 15m historical candles in $< 3.0$ seconds.
  - Generates verifiable backtest metrics (Sharpe, Sortino, MaxDD, Win Rate).
- **Effort Rating**: **L** (Large)

---

### Milestone 5 — Simulation Engine (Time Machine)
- **Scope**: 1,000-path stochastic forward simulation engine supporting all four empirical bootstrap methods with seed-based reproducibility.
- **Deliverables**:
  - Core simulation coordinator (`app/simulation/engine.py`).
  - 4 Simulation algorithms: Historical Bootstrap, Block Bootstrap, Volatility-Conditioned, Regime-Conditioned.
  - Vectorized percentile calculator ($p5$ to $p95$) and barrier hit evaluator (stop-loss vs take-profit).
  - Reproducibility generator using NumPy 64-bit seed guarantees.
  - REST endpoint `/api/v1/simulations` and streaming channel `/ws/simulation`.
- **Success Criteria**:
  - Generates 1,000 paths $\times$ 48 candles in $< 2,500$ ms.
  - Identical numerical results generated when supplied identical seed.
- **Effort Rating**: **L** (Large)

---

### Milestone 6 — Risk Gatekeeper & Paper Matching Engine
- **Scope**: Absolute risk authority implementation, position sizing mathematics, the 5 pre-order invariant checks, emergency kill switch, and realistic paper matching engine.
- **Deliverables**:
  - `RiskManager` module enforcing Drawdown, Daily Loss, Concurrent Positions, and Min R:R.
  - Deterministic position sizing engine based on 0.5% risk per trade.
  - Paper matching engine (`app/execution/engine.py`) modeling order book spread, slippage, and taker fees.
  - Position and margin accounting ledger.
  - `/paper/orders`, `/paper/positions`, and `/system/kill-switch` endpoints.
- **Success Criteria**:
  - 100% rejection rate for any candidate signal breaching any of the 5 risk invariants.
  - Execution slippage and fee calculations mathematically verified against institutional benchmarks.
  - Emergency Kill Switch cancels pending orders in $< 10$ ms.
- **Effort Rating**: **XL** (Extra Large)

---

### Milestone 7 — Frontend Foundation & Design System
- **Scope**: Next.js 14+ App Router scaffold, Tailwind design system, typography, Zustand domain stores, resilient WebSocket client manager, and 11 page shells.
- **Deliverables**:
  - Next.js workspace setup with strict TypeScript configurations.
  - Design system configuration: color tokens, Outfit/Inter/JetBrains Mono fonts, 8-pt spacing.
  - Zustand stores (`marketStore`, `agentStore`, `brainStore`, `paperStore`, `simulationStore`, `systemStore`).
  - Base `WebSocketManager` with heartbeat keep-alives and exponential backoff.
  - Header, Sidebar, StatusBar, and 11 empty route page shells.
- **Success Criteria**:
  - Zero build warnings or hydration mismatches.
  - WebSocket auto-reconnects cleanly within 5 seconds of backend restart.
- **Effort Rating**: **M** (Medium)

---

### Milestone 8 — Frontend Dashboards & Visualizations
- **Scope**: Full UI implementation for all 11 sections, TradingView Lightweight Charts integration, Time Machine fan charts, and Agent inspector.
- **Deliverables**:
  - High-performance TradingView Candlestick & Volume chart with indicator overlays.
  - Interactive HTML5 Canvas fan chart for Time Machine simulation percentiles.
  - Dynamic Finite State Machine visualizer for Central Brain.
  - Agent Center inspector with dual-pane I/O payload viewer.
  - Active Orders, Positions, and Execution tables with real-time updates.
- **Success Criteria**:
  - Continuous 60fps rendering during high-speed price tick ingestion.
  - Clean, responsive financial terminal layout with zero UI jitter.
- **Effort Rating**: **XL** (Extra Large)

---

### Milestone 9 — Analytics & Performance Auditing
- **Scope**: Automated execution auditing, slippage anomaly detection, equity curves, drawdown underwater charts, and strategy performance aggregation.
- **Deliverables**:
  - `PerformanceAuditor` agent completing post-trade and periodic audits.
  - Closed trades ledger with complete causal trace links.
  - Performance dashboard view (`/performance`) with rolling Sharpe, Sortino, and Profit Factor metrics.
  - Downloadable CSV/JSON audit export utility.
- **Success Criteria**:
  - Metrics accurately update within 500ms of any trade closure.
  - Audit logs record complete chain of causality from tick to fill.
- **Effort Rating**: **M** (Medium)

---

### Milestone 10 — Integration, Hardening & v1.0 Launch
- **Scope**: End-to-end integration testing, chaos testing (simulated network disconnects, exchange outages), test coverage verification, final documentation freeze, and v1.0 release.
- **Deliverables**:
  - End-to-end automated test suites spanning all modules.
  - 100% test coverage on Risk and Execution accounting logic.
  - Production build optimizations and single-command local boot script (`scripts/run_all.bat`).
  - Formal v1.0.0 release tag and verified user manual.
- **Success Criteria**:
  - System operates continuously for 48 hours without unhandled exceptions or memory leaks.
  - All 6 Acceptance Criteria from the PRD are fully satisfied.
- **Effort Rating**: **L** (Large)
