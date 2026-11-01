# NEPTUNE System Architecture

## Document Information
- **Project**: NEPTUNE — Autonomous Market Intelligence & Paper Trading Platform
- **Document Version**: 1.0.0
- **Status**: Approved / Architectural Blueprint
- **Author**: Neptune Principal Systems Architect
- **Date**: 2026-11-01

---

## 1. Architectural Overview & System Blueprint

NEPTUNE is engineered as a high-performance **modular monolith** optimized for low-latency market analysis, deterministic quantitative evaluation, and institutional-grade paper trading simulation. The platform decouples computation into clean horizontal layers while strictly enforcing unidirectional dependencies from external interfaces down to core storage models.

### 1.1 Complete Layered System Diagram

The following Mermaid flowchart models the complete end-to-end topology from external data ingress and the Next.js presentation tier down to transactional storage and columnar time-series archives.

```mermaid
flowchart TD
    subgraph External_World["External World (Unauthenticated Ingress)"]
        BINANCE_WS["Binance Public WebSocket Feed\n(kline_1m, trade, depth20)"]
        BINANCE_REST["Binance Public REST API\n(historical klines, exchangeInfo)"]
    end

    subgraph Presentation_Layer["Presentation Tier (Next.js 14+ App Router)"]
        UI_SHELL["Workstation Shell / Navigation"]
        subgraph UI_Modules["Interactive Dashboards"]
            UI_CMD["Command Center"]
            UI_MKT["Live Markets (Lightweight Charts)"]
            UI_AGT["AI Agent Center"]
            UI_BRN["Central Brain Visualizer"]
            UI_SIM["Time Machine (Fan Charts)"]
            UI_STR["Strategy Laboratory"]
            UI_PAP["Paper Execution Console"]
            UI_POS["Portfolio & Positions"]
            UI_PRF["Performance Analytics"]
            UI_SYS["System Telemetry & Logs"]
            UI_SET["Risk & Market Settings"]
        end
        subgraph Client_Stores["Client State & Transport (Zustand)"]
            ZS_MKT["marketStore"]
            ZS_AGT["agentStore"]
            ZS_BRN["brainStore"]
            ZS_PAP["paperStore"]
            ZS_SIM["simulationStore"]
            ZS_SYS["systemStore"]
            WS_CLIENT["Multiplexed WebSocket Manager\n(Exponential Backoff & Heartbeat)"]
        end
    end

    subgraph API_Gateway["API & Transport Gateway (FastAPI ASGI)"]
        CORS_SEC["Local Security & CORS Guard (127.0.0.1)"]
        REST_ROUTER["REST API Router (/api/v1/*)\nPydantic Request/Response Validation"]
        WS_HUB["WebSocket Broadcast Hub\n(/ws/market, /ws/agents, /ws/brain,\n/ws/signals, /ws/simulation, /ws/execution, /ws/system)"]
    end

    subgraph Backend_Services["Core Application Services (Python Asyncio)"]
        subgraph Market_Pipeline["Market Data Pipeline"]
            INGEST["Data Ingestion Service\n(Binance WebSocket Client)"]
            RING_BUF["In-Memory Ring Buffer\n(Latest 1000 Candles O(1))"]
            VALIDATOR["Candle Integrity & Gap Detector"]
        end

        subgraph Brain_Core["Autonomous Decision Core"]
            CENTRAL_BRAIN["Central Brain State Machine\n(OBSERVING ➔ AUDITED)"]
            HYPOTHESIS["Hypothesis Synthesizer"]
        end

        subgraph Specialist_Agents["Specialist Agent Swarm (Concurrent Async Tasks)"]
            AG_SCAN["MarketScanner (Regime)"]
            AG_TRND["TrendAnalyst (EMA Ribbon/ADX)"]
            AG_MOM["MomentumAnalyst (RSI/MACD)"]
            AG_VOL["VolumeAnalyst (VWAP/Anomalies)"]
            AG_NEWS["NewsAnalyst (Deterministic Macro)"]
            AG_STRAT["StrategyAnalyst (Strategy Rules)"]
            AG_SIG["SignalValidator (Confluence Filter)"]
            AG_RISK["RiskManager (Sizing & Veto)"]
            AG_EXEC["ExecutionManager (Fill Simulation)"]
            AG_AUDIT["PerformanceAuditor (Metrics)"]
        end

        subgraph Strategy_Simulation["Quantitative & Predictive Engines"]
            STRAT_ENG["Strategy Engine (4 Built-in Strategies)"]
            SIM_ENG["Time Machine Simulation Engine\n(Historical, Block, Volatility, Regime Bootstrap)"]
        end

        subgraph Execution_Risk["Execution & Safety Engines"]
            RISK_ENGINE["Risk Gatekeeper & Sizing Engine\n(Loss Limits, Drawdown Breaker, Position Count)"]
            PAPER_ENGINE["Paper Execution Simulator\n(Spread, Slippage, Fees, Fill Latency)"]
            POS_TRACKER["Position & Margin Ledger"]
        end
    end

    subgraph Storage_Layer["Storage & Persistence Tier"]
        REPO_FACTORY["Repository Access Layer (IRepository Interfaces)"]
        subgraph Relational_DB["Transactional Metadata & State (SQLite)"]
            SQLITE_DB[("neptune_trading.db\n(PRAGMA journal_mode = WAL)\nagents, brain_decisions, signals,\nsimulations, paper_orders, positions,\nrisk_events, system_events")]
        end
        subgraph TimeSeries_Storage["Historical Columnar Archive (Apache Parquet)"]
            PARQUET_STORE[("storage/historical/{symbol}/{tf}/\nYYYY/MM/YYYY-MM.parquet\n(Snappy Compression, PyArrow)")]
        end
    end

    %% External Ingress Connections
    BINANCE_WS --> INGEST
    BINANCE_REST --> INGEST

    %% Data Pipeline Flow
    INGEST --> VALIDATOR
    VALIDATOR --> RING_BUF
    VALIDATOR -.->|Flush Closed Candles| PARQUET_STORE
    RING_BUF --> WS_HUB

    %% Agent and Brain Coordination
    RING_BUF --> Specialist_Agents
    Specialist_Agents --> CENTRAL_BRAIN
    CENTRAL_BRAIN --> HYPOTHESIS
    HYPOTHESIS --> AG_STRAT
    AG_STRAT --> AG_SIG
    AG_SIG --> SIM_ENG
    SIM_ENG --> AG_RISK
    AG_RISK --> RISK_ENGINE
    RISK_ENGINE -->|Approved Signal| AG_EXEC
    AG_EXEC --> PAPER_ENGINE
    PAPER_ENGINE --> POS_TRACKER
    POS_TRACKER --> AG_AUDIT

    %% Gateway & Client Wire
    WS_HUB <==>|Real-time WS Channels| WS_CLIENT
    REST_ROUTER <==>|HTTP Requests/Responses| Client_Stores
    Client_Stores --> UI_Modules
    UI_Modules --> UI_SHELL

    %% Storage Persistence
    CENTRAL_BRAIN --> REPO_FACTORY
    Specialist_Agents --> REPO_FACTORY
    PAPER_ENGINE --> REPO_FACTORY
    POS_TRACKER --> REPO_FACTORY
    AG_AUDIT --> REPO_FACTORY
    REPO_FACTORY --> SQLITE_DB
    REPO_FACTORY --> PARQUET_STORE
```

---

## 2. Layered Architecture Description

The NEPTUNE architecture is structured into five distinct operational tiers:

### 2.1 Presentation Tier (Frontend Workstation)
- **Framework**: Next.js 14+ with App Router, React Server Components (RSC) for initial page layouts, and Client Components for high-frequency interactive canvases.
- **State Management**: Zustand split into isolated domain stores (`marketStore`, `agentStore`, `brainStore`, `paperStore`, `simulationStore`, `systemStore`).
- **Visualizations**: TradingView Lightweight Charts canvas engine for sub-millisecond price rendering; HTML5 Canvas and SVG for Monte Carlo fan charts and probability density functions.
- **Design Language**: Dark financial workstation palette (Navy `#0a0e1a`, Charcoal `#1a1f2e`, Electric Blue `#00b4d8`, Cyan `#00f5d4`, Emerald `#10b981`, Crimson `#ef4444`).

### 2.2 API & Transport Gateway Tier
- **Engine**: FastAPI running on Python's `uvicorn` ASGI server.
- **REST Endpoints**: Strict OpenAPI 3.1 documentation, asynchronous route handlers, dependency injection for services/repositories, and Pydantic v2 serialization.
- **WebSocket Hub**: Asynchronous pub/sub connection manager supporting dedicated topic channels with automatic connection tracking, ping-pong keepalives, and dropped connection cleanup.

### 2.3 Application & Orchestration Tier
- **Central Brain**: Finite State Machine driving the analytical lifecycle. Coordinates parallel agent dispatch, evaluates confidence confluences, and mediates transitions.
- **Event Bus**: Internal in-memory asynchronous event bus utilizing `asyncio.Queue` primitives to ensure non-blocking message passing between agents and pipelines.

### 2.4 Domain & Analytical Engines Tier
- **Specialist Agent Swarm**: 10 purpose-built agents running isolated execution logic. Each agent operates under typed schemas with strict timeout enforcement.
- **Time Machine (Forward Simulation Engine)**: Monte Carlo / Bootstrap vector simulator utilizing `numpy` for high-speed multi-path trajectory generation without GIL bottlenecks.
- **Risk Gatekeeper**: Pure deterministic verification engine. Enforces capital preservation invariants prior to any trade authorization.
- **Paper Execution Engine**: Market simulator computing fill prices, slippage as a function of liquidity/volatility, simulated exchange network latency, and taker fees.

### 2.5 Persistence & Storage Tier
- **Metadata & State (SQLite)**: Embeds SQLite 3 configured with Write-Ahead Logging (`WAL`), `synchronous = NORMAL`, and foreign key enforcement. Manages relational data, system audit logs, decisions, signals, and order states.
- **Historical Time-Series (Apache Parquet)**: Stores multi-year 1m/5m/15m/1h candle histories partitioned by `{symbol}/{timeframe}/YYYY/MM/`. Compressed with Snappy via `pyarrow`.

---

## 3. End-to-End Data Flow: Market Event to Paper Order

The primary pipeline transitions an inbound WebSocket market tick or closed candle into an executed paper trade through an immutable, auditable state progression.

```mermaid
sequenceDiagram
    autonumber
    participant Binance as Binance WebSocket
    participant Ingest as Data Ingest & Buffer
    participant Brain as Central Brain (FSM)
    participant Analysts as Upstream Analysts (Trend/Mom/Vol)
    participant Strat as Strategy Analyst
    participant Val as Signal Validator
    participant Sim as Time Machine (Bootstrap)
    participant Risk as Risk Manager
    participant Exec as Execution Manager
    participant Ledger as SQLite Order & Position DB
    participant WS as WebSocket Hub / UI Client

    Binance->>Ingest: Stream 1m Candle Close Event (BTC/USDT)
    Ingest->>Ingest: Validate OHLCV, check gaps, push to Ring Buffer
    Ingest->>WS: Broadcast Candle & Indicator Update
    Ingest->>Brain: Dispatch CANDLE_CLOSED Event

    Note over Brain: State: OBSERVING ➔ ANALYZING
    Brain->>Analysts: Trigger Parallel Analysis (Trend, Mom, Vol, Regime)
    Analysts-->>Brain: Return Analytical Payloads (ADX, RSI, VWAP, Volatility)

    Note over Brain: State: ANALYZING ➔ SIGNAL_DETECTED
    Brain->>Strat: Evaluate Active Strategies with Analytical Context
    Strat-->>Brain: Emit Candidate Signal (LONG BTC/USDT @ 65,000, TP: 67,000, SL: 64,000)

    Note over Brain: State: SIGNAL_DETECTED ➔ VALIDATING
    Brain->>Val: Validate Signal Confluence & Timeframe Alignment
    Val-->>Brain: Signal Validated (Confluence Score: 0.88, Rule Pass: 4/4)

    Note over Brain: State: VALIDATING ➔ SIMULATING
    Brain->>Sim: Request 1000-Path Forward Simulation (Horizon: 48)
    Sim->>Sim: Generate Bootstrap Paths & Percentiles (p5 - p95)
    Sim-->>Brain: Simulation Result (Stop Hit Prob: 14.2%, Target Hit Prob: 68.4%)

    Note over Brain: State: SIMULATING ➔ RISK_REVIEW
    Brain->>Risk: Submit Candidate Signal + Simulation Metrics for Sizing & Veto
    Risk->>Risk: Verify Daily Loss, Max Drawdown, Max Concurrent, Min R:R (2.0 >= 1.5)
    Risk->>Risk: Compute Position Size: risk_amount (5 USDT) / risk_per_unit (1000) = 0.005 BTC
    Risk-->>Brain: Decision: APPROVED (Allocated Size: 0.005 BTC)

    Note over Brain: State: RISK_REVIEW ➔ PAPER_ORDER_CREATED
    Brain->>Exec: Dispatch Create Paper Order Command
    Exec->>Exec: Apply Simulated Latency (85ms) + Slippage (+0.02%) + Taker Fee (0.04%)
    Exec->>Ledger: Insert Record into paper_orders & positions (Atomic Transaction)
    Ledger-->>Exec: Transaction Committed (Order ID: ord_btc_018)

    Note over Brain: State: PAPER_ORDER_CREATED ➔ POSITION_MONITORING
    Exec->>WS: Broadcast ORDER_FILLED & POSITION_OPENED Events
    WS->>UI Client: Update UI (Orders Table, Active Positions, Audio Alert)
```

---

## 4. Module Dependency Map & Architecture Invariants

To avoid circular dependencies, tight coupling, and "spaghetti" code, NEPTUNE enforces strict unidirectional dependency rules:

```mermaid
graph TD
    subgraph UI_Tier["Presentation Tier"]
        FRONTEND["frontend/ (Next.js)"]
    end

    subgraph API_Tier["API Tier"]
        API["backend/app/api/"]
    end

    subgraph Orchestration_Tier["Orchestration Tier"]
        BRAIN["backend/app/brain/"]
    end

    subgraph Domain_Tier["Domain & Engine Tier"]
        AGENTS["backend/app/agents/"]
        STRATEGIES["backend/app/strategies/"]
        SIMULATION["backend/app/simulation/"]
        RISK["backend/app/risk/"]
        EXECUTION["backend/app/execution/"]
        ANALYTICS["backend/app/analytics/"]
    end

    subgraph Data_Tier["Data & Ingestion Tier"]
        DATA["backend/app/data/"]
        CORE["backend/app/core/ (Config, Logging, Bus)"]
    end

    FRONTEND -->|HTTP / WS Only| API
    API --> BRAIN
    API --> AGENTS
    API --> RISK
    API --> EXECUTION
    API --> DATA

    BRAIN --> AGENTS
    BRAIN --> STRATEGIES
    BRAIN --> SIMULATION
    BRAIN --> RISK
    BRAIN --> EXECUTION
    BRAIN --> DATA

    AGENTS --> STRATEGIES
    AGENTS --> DATA
    AGENTS --> CORE

    SIMULATION --> DATA
    SIMULATION --> CORE

    RISK --> DATA
    RISK --> CORE

    EXECUTION --> RISK
    EXECUTION --> DATA
    EXECUTION --> CORE

    ANALYTICS --> DATA
    ANALYTICS --> CORE

    DATA --> CORE
```

### 4.1 Architecture Invariants
1. **No Circular Imports**: `core` has zero dependencies on higher layers. `data` depends only on `core`. Domain engines (`simulation`, `risk`, `execution`) depend only on `data` and `core`.
2. **Brain as Master Coordinator**: Individual agents do **not** invoke other agents directly. All multi-agent sequencing is orchestrated through the Central Brain state machine or event subscriptions.
3. **Storage Abstraction**: Domain and application engines never execute raw SQL. All persistence is handled through typed abstract repository interfaces (`IMarketDataRepository`, `IOrderRepository`, `IPositionRepository`, `ISignalRepository`).
4. **Pure Risk Authority**: The `ExecutionManager` cannot execute any paper order without a cryptographically valid, signed approval token or internal authorization object issued exclusively by `RiskManager`.

---

## 5. Technology Stack Decisions & Rationale Summary

| Component | Selected Technology | Alternative Evaluated | Strategic Rationale |
|---|---|---|---|
| **Backend Framework** | **FastAPI (Python 3.11+)** | Django, Flask, Express | Native `asyncio` support for concurrent WebSocket feeds, automatic OpenAPI generation, Pydantic v2 performance, unified Python scientific ecosystem (`numpy`, `pandas`, `pyarrow`). |
| **Frontend Framework** | **Next.js 14+ (App Router)** | Vite + React SPA, Nuxt | Production-grade server component routing, built-in layout management, optimized hydration, native TypeScript support, unified developer tooling. |
| **Client State** | **Zustand** | Redux Toolkit, MobX, Context API | Minimal boilerplate, unopinionated sub-store architecture, exceptional performance under 60fps high-frequency WebSocket updates without unneeded re-renders. |
| **Transactional Storage** | **SQLite (WAL Mode)** | PostgreSQL, MySQL | Zero network latency, single-file embedded distribution, ACID compliant, capable of $> 50,000$ read operations/sec under Write-Ahead Logging with zero maintenance overhead. |
| **Time-Series Storage** | **Apache Parquet (PyArrow)** | InfluxDB, TimescaleDB, CSV | Columnar compression (typically 80-90% reduction vs CSV), blazing fast vectorized querying into Pandas/NumPy arrays, partitioned filesystem hierarchy. |
| **Charting Engine** | **TradingView Lightweight Charts** | Chart.js, D3.js, Highcharts | Canvas-based rendering optimized specifically for financial candlesticks, zero DOM bloat, native support for volume histograms, markers, and multi-pane sync. |
| **Styling & UI Kit** | **Tailwind CSS + Lucide Icons** | Material UI, Ant Design | Utility-first CSS compiling to zero runtime overhead, exact hex-code color consistency, high-density financial terminal ergonomics. |

---

## 6. Error Propagation & System Resilience Model

NEPTUNE implements a multi-tiered error containment model to prevent analytical faults or network anomalies from destabilizing the trading core.

```mermaid
flowchart TD
    ERROR_SOURCE["Error Source\n(WebSocket drop, Calculation NaN, Disk I/O full)"] --> CATCH_TIER{"Error Classification"}

    CATCH_TIER -->|Network Disconnect| NET_HANDLER["Binance WS Auto-Reconnect\n- Exponential backoff (1s, 2s, 4s... max 30s)\n- Brain transitions to OBSERVING (defensive)\n- Pending fills frozen"]
    
    CATCH_TIER -->|Agent Calculation Fault| AGENT_HANDLER["Agent Error Boundary\n- Catch exception in execute()\n- Increment agent consecutive_failures\n- Mark agent status: DEGRADED\n- Brain skips agent vote; flags signal uncertain"]

    CATCH_TIER -->|Risk Rule Invariant Breach| RISK_HANDLER["Risk Critical Handler\n- Immediate Order Rejection\n- Persist risk_events audit entry\n- Broadcast HIGH-PRIORITY alert to UI\n- Trigger Kill Switch if drawdown threshold breached"]

    CATCH_TIER -->|Database Transaction Lock| DB_HANDLER["SQLite Concurrency Handler\n- Retry with exponential jitter (max 5 retries)\n- WAL checkpoint optimization\n- If catastrophic, fallback to read-only ring buffer"]

    NET_HANDLER --> LOG_AND_WS["Central Logging & /ws/system Broadcast"]
    AGENT_HANDLER --> LOG_AND_WS
    RISK_HANDLER --> LOG_AND_WS
    DB_HANDLER --> LOG_AND_WS
```

### 6.1 Domain Error Hierarchy
- `NeptuneBaseException`: Base class for all internal errors.
  - `MarketDataError`: Gaps in candle series, stale ticks, malformed exchange JSON.
  - `AgentExecutionError`: Timeout during agent computation, mathematical singularities (division by zero, NaN in indicator).
  - `BrainStateError`: Illegal finite state machine transitions (e.g., attempting to execute an unvalidated signal).
  - `RiskViolationException`: Sizing overflow, drawdown circuit-breaker breach, daily loss cap reached.
  - `PaperExecutionError`: Invalid order parameters, insufficient virtual margin, slippage calculation failure.
  - `StorageError`: SQLite disk lock, Parquet serialization failure, repository integrity violation.

### 6.2 Degraded State Protocols
- When 2 or more specialist agents enter `DEGRADED` status, the Central Brain suspends all transitions to `SIGNAL_DETECTED` and locks the platform in `OBSERVING`.
- If WebSocket market feed latency exceeds 2000ms or drops for $> 3$ consecutive heartbeat intervals, all paper trading order creation is paused automatically until 60 seconds of contiguous, validated data is re-established.
