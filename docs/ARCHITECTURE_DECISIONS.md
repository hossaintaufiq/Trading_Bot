# NEPTUNE Architecture Decision Records (ADRs)

## Document Information
- **Project**: NEPTUNE — Autonomous Market Intelligence & Paper Trading Platform
- **Document Version**: 1.0.0
- **Status**: Active Architectural Log
- **Author**: Neptune Principal Systems Architects
- **Date**: 2026-11-01

---

## Index of Architectural Decisions

- [ADR-001: SQLite over PostgreSQL for v1 Storage](#adr-001-sqlite-over-postgresql-for-v1-storage)
- [ADR-002: Apache Parquet for Historical Candle Storage](#adr-002-apache-parquet-for-historical-candle-storage)
- [ADR-003: Monorepo Architecture with Independent Frontend and Backend](#adr-003-monorepo-architecture-with-independent-frontend-and-backend)
- [ADR-004: FastAPI over Django and Flask](#adr-004-fastapi-over-django-and-flask)
- [ADR-005: Next.js App Router over Pages Router](#adr-005-nextjs-app-router-over-pages-router)
- [ADR-006: Zustand over Redux Toolkit for Frontend State Management](#adr-006-zustand-over-redux-toolkit-for-frontend-state-management)
- [ADR-007: Modular Monolith over Microservices Architecture](#adr-007-modular-monolith-over-microservices-architecture)
- [ADR-008: Deterministic Specialist Agents before LLM Reasoning](#adr-008-deterministic-specialist-agents-before-llm-reasoning)
- [ADR-009: Strictly Paper Trading in Version 1.0](#adr-009-strictly-paper-trading-in-version-10)
- [ADR-010: Repository Pattern for Persistence Abstraction](#adr-010-repository-pattern-for-persistence-abstraction)
- [ADR-011: Binance Public Unauthenticated API for Market Data Ingress](#adr-011-binance-public-unauthenticated-api-for-market-data-ingress)
- [ADR-012: UTC-Only Timestamps Throughout Entire System](#adr-012-utc-only-timestamps-throughout-entire-system)

---

### ADR-001: SQLite over PostgreSQL for v1 Storage

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: The platform requires a transactional storage engine for orders, positions, signals, agent logs, and audit decisions. We evaluated whether to bundle an external PostgreSQL server or utilize an embedded engine like SQLite.
- **Decision**: Adopt SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and `synchronous = NORMAL` for v1.
- **Rationale**:
  - Eliminates external process dependencies, user credential setup, Docker requirements, and network IPC latency.
  - SQLite in WAL mode easily exceeds 50,000 read operations/sec and hundreds of writes/sec, far exceeding NEPTUNE’s single-workstation requirements.
  - Backups and database portability are trivial (single file `neptune_trading.db`).
- **Alternatives Considered**: PostgreSQL 16, MySQL 8.4, DuckDB. DuckDB is analytical (OLAP) and less optimal for high-frequency transactional point-updates; Postgres introduces unnecessary operational friction for local installations.
- **Consequences**: Single-writer constraint requires handling write concurrency with `busy_timeout = 5000` and thread-safe repository connection pooling.

---

### ADR-002: Apache Parquet for Historical Candle Storage

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Backtesting and forward simulations require rapid scanning and vectorized computation over millions of 1m, 5m, and 15m OHLCV historical candles. Storing millions of time-series rows in SQLite or flat CSV files causes database bloat and excessive deserialization latencies.
- **Decision**: Store historical time-series datasets in Snappy-compressed Apache Parquet files, partitioned as `storage/historical/{symbol}/{timeframe}/YYYY/MM/YYYY-MM.parquet`.
- **Rationale**:
  - Columnar layout allows PyArrow and Pandas to load only required columns (e.g., `close` or `volume`) directly into contiguous memory buffers.
  - Delivers 80% to 90% compression compared to raw CSV or JSON.
  - Queries across hundreds of thousands of rows execute in sub-100ms timeframes.
- **Alternatives Considered**: InfluxDB, TimescaleDB, CSV archives. Time-series databases require dedicated daemons; CSVs are drastically slower to parse.
- **Consequences**: Time-series historical data is stored separately from transactional relational tables, requiring a repository abstraction to query both tiers seamlessly.

---

### ADR-003: Monorepo Architecture with Independent Frontend and Backend

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: NEPTUNE contains a Python scientific backend and a TypeScript/Next.js frontend. We needed to choose between multi-repository management or a single unified monorepo.
- **Decision**: Maintain a single monorepo with clean root-level separation: `/backend`, `/frontend`, `/docs`, `/storage`, `/infrastructure`, and `/scripts`.
- **Rationale**:
  - Allows synchronized atomic commits when schemas or contracts change.
  - Simplifies single-command development startup scripts (`scripts/run_all.bat`).
  - Keeps architectural documentation and design assets collocated with code.
- **Alternatives Considered**: Git submodules, separate repositories (`neptune-backend`, `neptune-frontend`). Separate repositories introduce synchronization friction and version drift.
- **Consequences**: Requires independent package management files (`pyproject.toml` for Python, `package.json` for Node.js) in their respective subdirectories.

---

### ADR-004: FastAPI over Django and Flask

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: A Python web framework is needed to expose REST endpoints and orchestrate multiple real-time WebSocket channels.
- **Decision**: Select FastAPI powered by Uvicorn (ASGI).
- **Rationale**:
  - Native first-class asynchronous (`asyncio`) support across HTTP routes and WebSocket connections.
  - Automatic OpenAPI 3.1 documentation and Pydantic v2 validation out-of-the-box.
  - Superior execution speed compared to traditional WSGI frameworks.
  - Clean dependency injection architecture (`Depends`).
- **Alternatives Considered**: Django Ninja, Flask, Sanic, Tornado. Django is heavyweight and assumes relational ORM overhead; Flask lacks native asynchronous WebSocket multiplexing.
- **Consequences**: Async handlers must never execute blocking CPU-heavy operations on the main event loop; heavy math must be offloaded to thread workers.

---

### ADR-005: Next.js App Router over Pages Router

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Selecting the routing and rendering paradigm for the Next.js presentation workstation.
- **Decision**: Adopt Next.js 14+ App Router (`src/app/*`).
- **Rationale**:
  - React Server Components (RSC) enable static layout scaffolding without client-side JavaScript overhead.
  - Native nested layouts preserve WebSocket connections and chart states during page navigation.
  - Represents the modern standard for long-term Next.js ecosystem support.
- **Alternatives Considered**: Next.js Pages Router (`pages/*`), Vite + React SPA. Vite SPA lacks built-in server component routing and unified full-stack developer tooling; Pages router is legacy.
- **Consequences**: High-frequency chart and streaming components must be explicitly marked with `'use client'` directives.

---

### ADR-006: Zustand over Redux Toolkit for Frontend State Management

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: The frontend receives dozens of high-frequency price ticks, order updates, and agent events per second over WebSockets. We must minimize unnecessary component re-renders.
- **Decision**: Adopt Zustand for client-side state management, partitioned into domain-specific stores (`marketStore`, `agentStore`, `brainStore`, `paperStore`, `simulationStore`, `systemStore`).
- **Rationale**:
  - Extremely minimal boilerplate with zero reducer ceremony.
  - Fine-grained transient update subscriptions and custom equality selectors prevent full-component tree re-renders during 60fps streaming.
  - Lightweight bundle size ($< 2$ KB vs $\sim 40$ KB for Redux Toolkit).
- **Alternatives Considered**: Redux Toolkit, MobX, React Context API. Context API causes catastrophic re-render cascades under high-frequency updates; Redux adds unnecessary boilerplate.
- **Consequences**: Developers must design selectors carefully to avoid subscribing components to whole store objects.

---

### ADR-007: Modular Monolith over Microservices Architecture

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Determining the distributed deployment architecture for the analytical and execution components.
- **Decision**: Build NEPTUNE as an in-process **Modular Monolith**.
- **Rationale**:
  - Eliminates inter-service network serialization latency (gRPC/HTTP), network partition failures, and orchestration complexity (Docker Swarm/Kubernetes).
  - In-process memory passing between agents and the Central Brain runs in microseconds rather than milliseconds.
  - Drastically lowers development, debugging, and testing complexity for local workstations.
- **Alternatives Considered**: Microservices orchestrated via Docker Compose and Kafka. Microservices introduce massive operational overhead with zero performance benefit for single-user algorithmic workstations.
- **Consequences**: Requires strict internal module boundaries, abstract interfaces, and linting rules to prevent monolithic spaghetti code.

---

### ADR-008: Deterministic Specialist Agents before LLM Reasoning

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Modern AI platforms often route analysis through Large Language Models (LLMs). We evaluated whether to embed LLMs directly in the real-time execution loop.
- **Decision**: Version 1.0 implements **100% deterministic, rule-based, and mathematically grounded specialist agents**. LLMs are strictly excluded from the critical path of order generation and risk validation.
- **Rationale**:
  - LLMs introduce 500ms – 3000ms latency, high API costs, hallucination hazards, and non-deterministic outputs incompatible with institutional risk guarantees.
  - Financial signals require rigorous mathematical formulations (EMA stacks, ADX thresholds, RSI divergences, VWAP deviations).
  - Predictable execution behavior and complete reproducibility are required.
- **Alternatives Considered**: LangChain / AutoGPT multi-agent wrappers, OpenAI Function Calling. Both introduce latency, cost, and reliability risks incompatible with high-speed trading.
- **Consequences**: Quantitative indicators and confluence logic must be hand-crafted, mathematically validated, and unit tested.

---

### ADR-009: Strictly Paper Trading in Version 1.0

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Determining whether to support live broker/exchange order routing with real capital in the v1.0 release.
- **Decision**: Restrict Version 1.0 strictly to **Paper Trading**. No real capital, private keys, or authenticated exchange connectivity will be built into v1.0.
- **Rationale**:
  - Guarantees 100% capital safety for users and developers during initial platform development and quantitative strategy verification.
  - Allows aggressive validation of the Central Brain, Time Machine, and Risk Manager without financial liability.
  - Enables modeling of realistic execution physics (slippage, fill latencies, taker fees) without exchange counterparty risk.
- **Alternatives Considered**: Live trading with small test capital ($50 USDT). Introducing live keys introduces severe security liabilities, regulatory concerns, and potential capital loss.
- **Consequences**: Live exchange connector adapters (`CCXT`, private Binance order endpoints) are deferred to v2.0 roadmap milestones.

---

### ADR-010: Repository Pattern for Persistence Abstraction

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Decoupling domain business logic, agent workflows, and API handlers from direct database SQL statements.
- **Decision**: Introduce explicit abstract repository interfaces (`IMarketDataRepository`, `IOrderRepository`, `IPositionRepository`, `ISignalRepository`).
- **Rationale**:
  - Allows unit tests to run with lightning-fast in-memory mock repositories without touching the disk or SQLite.
  - Isolates SQL query generation into dedicated repository implementations (`app/data/sqlite/repositories/*`).
  - Simplifies future migration to other storage engines if necessary.
- **Alternatives Considered**: Direct SQL queries inside API route handlers, full-featured ORM (SQLAlchemy / Tortoise). Direct SQL creates tight coupling; heavyweight ORMs add unnecessary complexity and latency.
- **Consequences**: Requires writing clean repository interface contracts and concrete class implementations.

---

### ADR-011: Binance Public Unauthenticated API for Market Data Ingress

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Acquiring reliable, liquid real-time and historical cryptocurrency market data.
- **Decision**: Connect to Binance’s public REST and WebSocket endpoints (`wss://stream.binance.com:9443/ws` and `https://api.binance.com/api/v3`) without authentication.
- **Rationale**:
  - Deepest spot liquidity and highest trade volume in crypto markets.
  - High uptime, public unauthenticated access requires no user sign-up or API key management.
  - Generous rate limits (1200 request weight/min on REST; unlimited WebSocket streaming).
- **Alternatives Considered**: Coinbase Public API, Kraken API, CoinGecko. Binance provides the lowest latency WebSocket streams and highest tick granularity.
- **Consequences**: Public IP rate-limiting must be respected; automated backoffs must handle HTTP 429 or 418 responses.

---

### ADR-012: ISO 8601 UTC String Timestamps Throughout Backend and Persistence

- **Status**: Accepted (Amended 2026-11-01)
- **Date**: 2026-11-01
- **Context**: Standardizing time representation across SQLite, Parquet, backend domain models, REST/WebSocket APIs, and frontend state.
- **Decision**: Enforce **standardized ISO 8601 UTC strings** (e.g. `2026-11-01T20:00:00.000Z`) throughout all backend Pydantic models, SQLite database columns, REST API contracts, and WebSocket event payloads. Timestamp conversion to Unix seconds (`Math.floor(Date.parse(iso) / 1000)`) is performed **only in the frontend chart utility layer** (`frontend/app/lib/utils.ts` `toChartTime()`) for TradingView Lightweight Charts canvas compatibility.
- **Rationale**:
  - Unambiguous human-readable auditability in logs, database inspections, and JSON contracts.
  - Native support in Pydantic v2 and TypeScript ISO string validation.
  - Consistent timezone handling without ambiguity between milliseconds vs seconds.
- **Alternatives Considered**: Integer epoch milliseconds everywhere. While fast, epoch integers reduce readability during debugging and audit logs.
- **Consequences**: Frontend chart components must use the utility conversion helper when passing timestamps to Lightweight Charts.

---

### ADR-013: Simulation Path Partitioning and SQLite Summary Metrics

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Avoiding filesystem fragmentation from generating 1,000 synthetic paths per approved signal.
- **Decision**: 
  - Store simulation metadata, assumptions, and terminal percentile metrics (`p5, p10, p25, p50, p75, p90, p95`, stop/target probabilities, MAE) directly in SQLite's `simulations` table.
  - Stream full 1,000-path arrays ephemerally to the frontend via `/ws/simulation`.
  - Persist full simulation trajectories using daily partitioned Parquet files (`storage/simulations/YYYY/MM/simulations_YYYY-MM-DD.parquet`) or on explicit user export, avoiding thousands of tiny independent Parquet files.
- **Rationale**:
  - Prevents inode/file descriptor exhaustion and sluggish queries on Windows filesystems.
  - Retains rapid historical analytics and percentile queries via SQLite without reading Parquet files for summary dashboards.
- **Alternatives Considered**: One Parquet file per simulation. Rejected due to file fragmentation.
- **Consequences**: Loading full 1,000-path history for past simulations queries the daily partition or export file.

---

### ADR-014: Cache-First Historical Market-Data Backfill

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Avoiding public Binance REST IP rate limits (HTTP 429/418) during local development and frequent server hot-reloads.
- **Decision**: Implement a strict **cache-first strategy** in `MarketDataService`. On startup or on-demand backfill, the service inspects existing local Parquet storage first, identifies the latest available closed candle timestamp, and only queries Binance REST for the incremental missing range (`latest_stored_time` to `now`). If local data is already fresh, zero REST calls are issued.
- **Rationale**:
  - Prevents IP rate bans on developer machines during testing and server reloads.
  - Near-instantaneous backend startup when historical data already exists.
- **Alternatives Considered**: Always fetch last 1,000 candles from Binance on startup. Rejected due to rate limit risk.
- **Consequences**: The repository must support efficient timestamp max lookups and deduplication on append.

---

### ADR-015: Dual-Mode Emergency Kill Switch

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Enabling granular emergency operational control over paper trading positions and order generation.
- **Decision**: Implement two explicit kill-switch modes on `/api/v1/system/kill-switch`:
  1. `PAUSE_NEW_ORDERS`: Halts all new signal generation and risk approvals; existing open paper positions remain active and continue monitoring bracket stop-loss and take-profit targets.
  2. `LIQUIDATE_ALL_AND_HALT`: Halts all new signal generation and immediately executes simulated market orders to close all active open paper positions. Simulated liquidations MUST apply realistic paper execution assumptions (current bid/ask price, taker fee, and slippage).
- **Rationale**:
  - Gives the operator fine-grained choice between orderly pause and emergency capital protection.
  - Enforces Rule `S-06` and `A-10` by recording realistic execution assumptions during emergency liquidation.
- **Alternatives Considered**: Single boolean toggle that leaves positions unattended. Rejected due to operational ambiguity.
- **Consequences**: API and frontend UI must support selecting the mode and confirming liquidation actions.

---

### ADR-016: Historical Backtesting Engine and Conservative Intrabar Ambiguity Resolution

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Evaluating specialist agents and strategy candidates against historical candle data without look-ahead bias or optimistic intrabar assumptions.
- **Decision**: 
  1. Implement an event-driven deterministic replay engine (`HistoricalBacktestEngine`) advancing bar-by-bar, strictly withholding future candles from analytical agents.
  2. Require conservative resolution of intrabar ambiguity: if both stop-loss and take-profit thresholds are breached within the same OHLC bar and intrabar tick sequence is unavailable, the execution simulator MUST resolve the exit as a Stop-Loss hit (`AMBIGUOUS_BAR_STOP`). Optimistic outcomes are strictly forbidden (Rules `S-05`, `S-06`).
  3. Store backtest summaries in SQLite (`backtest_runs` and `strategy_metrics`) and comprehensive trade ledgers in Parquet (`storage/backtests/{backtest_id}_trades.parquet`), avoiding filesystem inode bloat.
  4. Perform out-of-sample and walk-forward evaluations strictly via chronological time splits without random shuffling.
- **Rationale**:
  - Prevents backtest overfitting, look-ahead leakage, and artificial win-rate inflation.
  - Preserves mathematical exactness by executing monetary calculations with Python `Decimal`.
- **Alternatives Considered**: Optimistic first-hit assumption or 50/50 randomized resolution. Rejected as violating quantitative safety standards.
- **Consequences**: Backtest performance metrics reflect conservative, realistic execution dynamics.

