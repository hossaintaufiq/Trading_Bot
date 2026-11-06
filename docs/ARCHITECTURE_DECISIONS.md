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
- [ADR-013: Parquet Trajectory Partitioning and SQLite Summary Persistence](#adr-013-parquet-trajectory-partitioning-and-sqlite-summary-persistence)
- [ADR-014: Cache-First Historical Market-Data Backfill](#adr-014-cache-first-historical-market-data-backfill)
- [ADR-015: Dual-Mode Emergency Kill Switch](#adr-015-dual-mode-emergency-kill-switch)
- [ADR-016: Historical Backtesting Engine and Conservative Intrabar Ambiguity Resolution](#adr-016-historical-backtesting-engine-and-conservative-intrabar-ambiguity-resolution)
- [ADR-017: Balanced Protection Exit Engine and Multi-Factor Early Reversal Protocol](#adr-017-balanced-protection-exit-engine-and-multi-factor-early-reversal-protocol)
- [ADR-018: Exit Policy Benchmark Protocol and Chronological Out-of-Sample Degradation Framework](#adr-018-exit-policy-benchmark-protocol-and-chronological-out-of-sample-degradation-framework)
- [ADR-019: Volatility-Bounded Entry Filtering and Multi-Factor Confluence Architecture](#adr-019-volatility-bounded-entry-filtering-and-multi-factor-confluence-architecture)
- [ADR-020: Dataset Versioning, Provenance Tracking, and Timeframe-Independent Chronological Research Framework](#adr-020-dataset-versioning-provenance-tracking-and-timeframe-independent-chronological-research-framework)
- [ADR-021: Model-Agnostic Financial Forecasting Contract & Deferred Kronos Inference Protocol](#adr-021-model-agnostic-financial-forecasting-contract--deferred-kronos-inference-protocol)
- [ADR-022: Kronos Foundation Model Experimental Integration & Gated Confirmation Protocol](#adr-022-kronos-foundation-model-experimental-integration--gated-confirmation-protocol)
- [ADR-023: Immutable News Storage, Multi-Stage Deduplication & Point-in-Time Temporal Gate](#adr-023-immutable-news-storage-multi-stage-deduplication--point-in-time-temporal-gate)
- [ADR-024: 15-Category Event Taxonomy, Asset Relevance Isolation & Macroeconomic Calendar Registry](#adr-024-15-category-event-taxonomy-asset-relevance-isolation--macroeconomic-calendar-registry)
- [ADR-025: Two-Stage Deterministic Classification Remediation, 100% Historical Coverage & Next-Available-Price Execution Synchronization](#adr-025-two-stage-deterministic-classification-remediation-100-historical-coverage--next-available-price-execution-synchronization)
- [ADR-026: Deterministic Point-in-Time Execution Scheduling, Next-Eligible-Price Policy & Simulation Engine Integration](#adr-026-deterministic-point-in-time-execution-scheduling-next-eligible-price-policy--simulation-engine-integration)
- [ADR-027: Cryptographic HMAC-SHA256 Risk Authorization Token Binding and Macro Boundary Schema Normalization](#adr-027-cryptographic-hmac-sha256-risk-authorization-token-binding-and-macro-boundary-schema-normalization)
- [ADR-028: Ephemeral HMAC Secret Generation, Run-Isolated Risk Authorization, and Replay-Resistant Execution Token Lifecycle](#adr-028-ephemeral-hmac-secret-generation-run-isolated-risk-authorization-and-replay-resistant-execution-token-lifecycle)
- [ADR-029: Protocol Freeze: 4-Group Controlled Experimental Design, 3-Partition Chronological Split, and Statistical Analysis Plan](#adr-029-protocol-freeze-4-group-controlled-experimental-design-3-partition-chronological-split-and-statistical-analysis-plan)
- [ADR-030: Online Control Matching, Executable News Veto Engine, Timeframe Bootstrap Calibration, and OOS Access Guard](#adr-030-online-control-matching-executable-news-veto-engine-timeframe-bootstrap-calibration-and-oos-access-guard)
- [ADR-031: Development-Partition Experimental Execution, 4-Group Synchronized Simulation Engine, and Candidate Stream Caching](#adr-031-development-partition-experimental-execution-4-group-synchronized-simulation-engine-and-candidate-stream-caching)
- [ADR-032: Independent Forensic Accounting Reconciliation, Cash-Equity Inversion Remediation, and Point-Mass Bootstrap Diagnosis](#adr-032-independent-forensic-accounting-reconciliation-cash-equity-inversion-remediation-and-point-mass-bootstrap-diagnosis)

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

---

### ADR-017: Balanced Protection Exit Engine and Multi-Factor Early Reversal Protocol

- **Status**: Accepted
- **Date**: 2026-11-01
- **Context**: Fixed take-profit orders prematurely cut off winning positions during strong trend regimes. Conversely, trailing stops alone can give back significant accumulated profit during sudden market reversals, while relying on single indicators (e.g. RSI overbought) causes premature whipsaw exits.
- **Decision**: 
  1. Implement a **Balanced Protection** exit architecture where positions possess an initial protective stop-loss, while fixed take-profits are non-terminating (positions run past initial theoretical targets while trends remain healthy).
  2. Implement an in-place **one-way ratcheting trailing stop** activated at $+1.0 R$ profit threshold ($new\_stop \ge previous\_stop$ for Long, $new\_stop \le previous\_stop$ for Short). Trailing distance is parameterized by ATR multiplier (default 2.0x ATR) or $2.0 R$. Stops never move in the direction of increased risk.
  3. Prohibit retroactive trailing stop application: stops updated from candle $T$'s high/low are strictly enforced for candle $T+1$ onwards.
  4. Implement `MultiFactorReversalDetector` requiring confirmation from $\ge 2$ independent analytical domains (Trend, Momentum, Volume, Scanner Regime). A single indicator alone is strictly forbidden from triggering an exit.
  5. Enforce strict temporal separation: reversal detection occurs at candle $T$ close; execution fills no earlier than candle $T+1$ open with adverse slippage, spread, and taker fees.
  6. Enforce stop precedence: if candle $T+1$ opens gap-down/up beyond the active protective stop, the stop-loss order takes precedence over the pending reversal exit.
  7. Maintain backward compatibility with `FIXED_BRACKET` mode for benchmarking.
- **Rationale**:
  - Balances downside protection with letting trend profits run, avoiding arbitrary profit caps.
  - Mitigates false reversal whipsaws by demanding multi-factor domain confluence.
  - Eliminates look-ahead and execution bias by strictly executing exits on subsequent candle events.
- **Alternatives Considered**: 
  - Dynamic ATR take-profit: Still caps upside during parabolic trends.
  - Single-factor reversal (e.g. RSI roll-over alone): Prone to premature exits in strong bull regimes.
- **Consequences**: Active positions track MFE, MAE, peak favorable prices, and trailing ratchets; execution ledger details exit reasons (`STOP_LOSS`, `TRAILING_STOP`, `REVERSAL_CONFIRMED`).

---

### ADR-018: Exit Policy Benchmark Protocol and Chronological Out-of-Sample Degradation Framework

- **Status**: Accepted
- **Date**: 2026-11-02
- **Context**: Milestone 4.2 requires a reproducible quantitative evaluation comparing `FIXED_BRACKET` and `BALANCED` exit policies across multiple symbols, timeframes, and market regimes, to rigorously determine whether trailing stops and multi-factor reversal confirmations improve strategy expectancy, win rate, or drawdown without inducing curve-fitting.
- **Decision**: 
  1. Implement `ExitPolicyBenchmark` to evaluate identical entry signals, position sizing, and risk constraints across both exit policies simultaneously.
  2. Implement chronological 70/30 In-Sample (IS) vs Out-of-Sample (OOS) data splits. Random or shuffled splits are strictly prohibited (Rule `S-05`).
  3. Measure Walk-Forward Efficiency ($WFE = \text{AnnNet}_{OOS} / \text{AnnNet}_{IS}$) and Annualized Degradation % between IS and OOS to gauge robustness across regimes.
  4. Track Maximum Favorable Excursion (MFE), Maximum Adverse Excursion (MAE), and holding duration on all trades.
  5. Segment performance across market regimes (`TRENDING_BULL`, `TRENDING_BEAR`, `RANGING`, `VOLATILE`, `UNCERTAIN`) and audit multi-factor reversal reason combinations.
  6. Persist benchmark runs to SQLite table `benchmark_runs` with aggregate delta metrics and save individual trade ledgers to Parquet (`storage/backtests/bkt_{id}_trades.parquet`).
- **Rationale**:
  - Ensures absolute experimental integrity with zero look-ahead bias and zero survivorship bias.
  - Empirically reveals regime-specific performance characteristics: Balanced Protection excels on higher timeframes and in trending regimes by eliminating artificial profit caps, while Fixed Brackets maintain an advantage in high-frequency whipsaw environments.
- **Alternatives Considered**: 
  - K-fold cross validation: Inapplicable to chronological time-series due to look-ahead leakage.
  - Unsplit full-dataset backtesting: Prone to in-sample overfitting and deceptive optimism.
- **Consequences**: Standardized benchmark framework produces reproducible, auditable comparisons exported to SQLite, JSON, and Parquet ledgers.

---

### ADR-019: Volatility-Bounded Entry Filtering and Multi-Factor Confluence Architecture

- **Status**: Accepted
- **Date**: 2026-11-02
- **Context**: Milestone 4.3 diagnosed why the baseline deterministic entry strategy (`trend_momentum_pullback_v1`) generated net negative expectancy (-$340.22 across 39,000 candles). Empirical analysis revealed that transaction costs (0.30% round-trip) consumed 35–50% of the trade target on lower timeframes (15m), and trades executed during low-volatility chop ($ATR\% < 0.80\%$) accounted for the vast majority of stop-outs.
- **Decision**:
  1. Implement a dedicated, modular entry filtering layer in `backend/app/analytics/filters.py` with typed Pydantic models.
  2. Adopt a mandatory Volatility Bounds filter ($0.80\% \le \frac{ATR_{14}}{Close} \le 3.00\%$) ensuring trades are only entered when expected price displacement is large enough to absorb exchange fees and slippage.
  3. Adopt a Relative Volume (RVOL) filter ($RVOL \ge 0.85$ over 20-period volume SMA) to eliminate false continuations in illiquid, drifting price action.
  4. Adopt an ADX trend strength filter ($ADX \ge 25$ with $+DI > -DI$ for Long, $-DI > +DI$ for Short) to reject weak-trend regimes.
  5. Structure evaluation into three non-overlapping chronological partitions: Train (50%), Validation (25%), and Out-of-Sample (25%).
  6. Optimize `HistoricalBacktestEngine` lookback window by slicing indicators to the most recent 300 bars, eliminating $O(N^2)$ memory scaling and enabling rapid multi-month backtesting.
- **Rationale**:
  - In-sample and validation testing proved that the H7 Confluence Ensemble transformed the baseline strategy from -$340.22 net loss (35.0% Win Rate) to **+$35.78 net profit (50.8% Win Rate, 1.22 Profit Factor)** and reduced maximum drawdown by 81.3% (from $368.46 to $68.98).
  - During the low-volatility Out-of-Sample window where the unfiltered baseline lost -$200.65, the volatility filter hibernated (0 trades), completely preserving capital.
- **Alternatives Considered**:
  - Overfitting moving average periods or RSI levels: Curve-fitting individual indicators fails out-of-sample and does not address the fundamental friction-to-ATR ratio.
  - Relying exclusively on higher-timeframe alignment without volatility bounds: HTF alignment was shown by ablation to be insufficient on its own if local volatility is compressed.
- **Consequences**: Signal Validator and Strategy Analyst agents can now employ causal, zero-lookahead entry filters before routing candidate orders to the Risk Manager.

---

### ADR-020: Dataset Versioning, Provenance Tracking, and Timeframe-Independent Chronological Research Framework

- **Status**: Accepted
- **Date**: 2026-11-02
- **Context**: Milestone 4.3 revealed a critical flaw in pooled chronological evaluations: unequal historical coverage (15m covered ~52 days, 1h covered ~208 days, 4h covered ~500 days) caused the out-of-sample period to be dominated exclusively by lower-timeframe trades, destroying timeframe balance. Furthermore, reproducible research requires immutable dataset versioning, cryptographic provenance fingerprints, and explicit partition boundary enforcement without look-ahead indicator leakage.
- **Decision**:
  1. Establish an immutable dataset versioning hierarchy: Dataset `v1.0.0` (frozen reference baseline of 87 Parquet files, SHA256 `11c41f00...`) and Dataset `v2.0.0` (expanded 34-month contiguous history from 2024-01-01 to 2026-11-01 across BTCUSDT, ETHUSDT, BNBUSDT on 15m, 1h, 4h, and 1d; 420 Parquet files).
  2. Implement SQLite metadata tracking via table `historical_datasets` recording dataset ID, date ranges, candle counts, missing interval counts, validation status, and SHA256 fingerprints.
  3. Enforce the canonical 8-column Parquet schema: `('timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades_count')`.
  4. Mandate timeframe-independent evaluation: each symbol and timeframe must be evaluated independently before considering pooled results.
  5. Enforce chronological partitions (Train, Validation, OOS) with strict boundary enforcement: orders cannot cross partition boundaries, and indicators are primed using pre-partition closed warmup bars without look-ahead leakage.
  6. Support expanding walk-forward evaluation across standardized chronological folds.
- **Rationale**:
  - Eliminates sample selection distortion caused by asymmetric timeframe lengths.
  - Guarantees 100% bit-for-bit reproducible data provenance across all research milestones.
  - Adding 1d candles establishes an authoritative higher timeframe for 4h alignment and enables multi-year macro regime analysis.
- **Alternatives Considered**:
  - Overwriting historical files in-place without versioning: Violates auditability and breaks past milestone reproducibility.
  - Random k-fold cross validation: Strictly forbidden by Rule `S-05` due to look-ahead bias and serial correlation.
- **Consequences**: Backtest runners, data downloaders, and audit manifests must track explicit dataset IDs and partition boundaries.

---

### ADR-021: Model-Agnostic Financial Forecasting Contract & Deferred Kronos Inference Protocol

- **Status**: Accepted
- **Date**: 2026-11-02
- **Context**: Future milestones intend to evaluate pre-trained foundation models (such as Kronos, Chronos, TimesFM) for multi-step financial time-series forecasting. Integrating deep learning weights directly into NEPTUNE's core trading pipeline at this stage would violate Rule `E-08` (minimal dependencies), inflate installation footprints, and risk architectural coupling to proprietary model interfaces.
- **Decision**:
  1. Define a strict model-independent forecasting contract in `backend/app/analytics/forecasting.py` using typed Pydantic models: `ForecastInput`, `ForecastOutput`, `ForecastCandle`, and `IForecaster`.
  2. Enforce zero look-ahead bias: `ForecastInput` requires past closed candles, sequence length, forecast horizon, dataset ID, and generates an input cryptographic fingerprint.
  3. Enforce research isolation: Forecast outputs can only serve as research signals or filter inputs; they are strictly prohibited from directly authorizing paper orders or bypassing the Central Brain and Risk Manager (Rules `S-01`, `S-04`).
  4. Defer deep learning model weight downloads and GPU inference runtimes until the forecasting evaluation harness is fully benchmarked. Provide `MockAgnosticForecaster` for testing contracts and pipeline integration.
  5. Design future comparative research to measure the marginal economic value of foundation models:
     - Configuration A: Deterministic NEPTUNE baseline.
     - Configuration B: Forecaster alone.
     - Configuration C: Hybrid (Deterministic + Forecaster).
- **Rationale**:
  - Decouples NEPTUNE from any specific deep learning architecture or PyTorch/TensorFlow framework.
  - Ensures clean pair-wise ablation studies to isolate whether neural forecasting provides genuine economic alpha after execution friction.
- **Alternatives Considered**:
  - Bundling Kronos weights and PyTorch directly in v1: Incurs multi-gigabyte dependency overhead and violates modular monolith stability.
  - Allowing forecasters to place direct orders: Violates Central Brain architecture (Rule `A-06`) and Risk Manager authorization (Rule `S-04`).
- **Consequences**: Future ML components will implement the `IForecaster` protocol, preserving zero-lookahead guarantees and input dataset provenance.




---

### ADR-022: Kronos Foundation Model Experimental Integration & Gated Confirmation Protocol

- **Status**: Accepted
- **Date**: 2026-11-02
- **Context**: Milestone 4.5 investigated whether the pretrained Kronos foundation model (`NeoQuasar/Kronos-mini`, ~4.1M params; `NeoQuasar/Kronos-Tokenizer-2k`, 20-bit codebook) provides actionable predictive value for NEPTUNE's market intelligence and paper trading pipelines.
- **Decision**:
  1. Implement `KronosForecaster` conforming to `IForecaster` in `backend/app/analytics/forecasters/kronos_forecaster.py`.
  2. Maintain strict look-ahead bias prevention: reject unclosed candles (`is_closed == True` required), enforce chronological sequence ordering, compute cryptographic SHA-256 fingerprints, and align forecast timestamps to $T + k \times \Delta t$.
  3. Prohibit standalone order generation by foundation models: empirical backtesting (Group B) proved that pure autoregressive forecasting suffers severe friction decay (541 trades, -$405.52 net loss, 17.84% max drawdown breaching the 5% circuit breaker).
  4. Authorize Kronos exclusively as a secondary confirmation gate (Group C): when used to filter deterministic candidate signals, Kronos pruned 53.8% of low-conviction signals, cutting dollar losses by 70.0% and max drawdown by 29.7%, while lifting the portfolio profit factor from 1.16 to 1.20.
  5. Mandate native CPU execution on Windows 11 without requiring CUDA runtimes or external RPC microservices.
- **Rationale**:
  - Pretrained foundation models have ~52.4% directional accuracy on 1-step horizons, but cannot overcome 0.30% round-trip exchange friction when traded alone.
  - Used defensively as an exposure damper, Kronos substantially enhances portfolio risk profiles without violating modular monolith invariants.
- **Alternatives Considered**:
  - Autonomous model-driven trade execution (Group B): Rejected due to catastrophic fee churn and circuit breaker violation.
  - Fine-tuning Kronos on proprietary exchange data: Deferred until post-v1.
- **Consequences**: Kronos remains isolated in the analytics layer; the Central Brain and Risk Manager maintain sole authority over trade authorization.

---

### ADR-023: Immutable News Storage, Multi-Stage Deduplication & Point-in-Time Temporal Gate

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.1 establishes the data foundation for historical news research. In financial NLP backtesting, look-ahead bias routinely creeps in through retroactive headline edits, lack of publication timestamps, syndicated duplication, and crawler propagation delays.
- **Decision**:
  1. **Two-Tier Storage & Verification Taxonomy**:
     - *Tier 1 (Official Exchange Announcements)*: Binance Public CMS notices recorded as `POINT_IN_TIME_VERIFIED` with millisecond UTC precision.
     - *Tier 2 (Global Editorial & Wire)*: GDELT 2.0 raw 15-minute GKG master CSV archives recorded as `PARTIALLY_VERIFIED`. The interactive DOC API is prohibited for batch historical ingestion due to IP rate limits (`HTTP 429`).
  2. **Strict Revision Immutability**:
     - Core article identity records (`news_articles`) and revision records (`news_article_versions`) are strictly append-only.
     - When an article text, headline, or category is modified by the publisher, a new version row is appended with an incremented version counter and SHA-256 payload hash. Historical version rows are never mutated or deleted.
  3. **Point-in-Time Latency Buffer & Temporal Invariants**:
     - Explicitly distinguish between `published_at`, `updated_at`, `provider_seen_at`, `first_seen_at`, `collected_at`, and `available_at`.
     - Editorial articles without verified publisher timestamps have `published_at = None` and enforce a conservative 5-minute latency buffer ($t_{\text{avail}} = t_{\text{seen}} + 300\text{s}$).
     - The system strictly forbids promoting a partially verified timestamp to point-in-time verified status.
  4. **Multi-Stage Event Deduplication & Clustering**:
     - Implement a 6-stage pipeline: (1) Exact URL, (2) Canonical URL (tracking params stripped), (3) Exact Normalized Headline, (4) 64-bit sliding 4-gram SimHash (Hamming distance $\le 3$), (5) Entity & category overlap, and (6) 24-hour chronological sliding window.
     - Merged articles form immutable `news_event_clusters` governed by the earliest availability timestamp ($t_{\text{avail, min}}$). Distinct events separated by $> 24\text{ hours}$ or distinct assets are never merged.
  5. **Hybrid Parquet + SQLite Storage & Research Isolation**:
     - Relational indices and cluster mappings are persisted in SQLite (WAL mode, Rule `S-08`).
     - Bulk historical articles and version records are partitioned into Parquet (`storage/news/{source}/{YYYY}/`).
     - News data remains strictly quarantined within `app/data/news/` and research analytics. Direct connection to the Central Brain, Risk Manager, or paper execution engine is prohibited until positive expectancy is validated.
- **Rationale**:
  - Eliminates revisionism bias and look-ahead data leakage.
  - Mitigates wire syndication echo chambers that trigger false volatility spikes.
  - Maintains compliance with modular monolith, SQLite single-process WAL, and paper-trading safety rules.
- **Consequences**:
  - News datasets can be independently verified, exported, and audited via reproducible cryptographic manifests.


---

### ADR-024: 15-Category Event Taxonomy, Asset Relevance Isolation & Macroeconomic Calendar Registry

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.2 expanded NEPTUNE's historical news coverage across the 2024–2026 research window. Auditing revealed that naive keyword matching conflated general Binance exchange operations (Proof of Reserves audits, system maintenance, executive settlements) with direct BNB tokenomics, creating artificial signal contamination. Furthermore, macroeconomic events (FOMC rate decisions, CPI prints, NFP releases) lacked ground-truthed, point-in-time verified event calendars.
- **Decision**:
  1. **15-Category Event Taxonomy**:
     - Implement transparent, deterministic categorization: `SECURITY_INCIDENT`, `REGULATORY`, `MONETARY_POLICY`, `MACROECONOMIC`, `ETF_INSTITUTIONAL_FLOW`, `EXCHANGE_SOLVENCY`, `EXCHANGE_OPERATIONAL`, `PROTOCOL_UPGRADE`, `NETWORK_OUTAGE`, `ASSET_LISTING`, `ASSET_DELISTING`, `MARKET_STRUCTURE`, `LARGE_CAPITAL_FLOW`, `OTHER`, `UNCLASSIFIED`.
  2. **6-Tier Asset Relevance Classification**:
     - Categorize how events map to the research universe (`BTC`, `ETH`, `BNB`): `DIRECT_ASSET`, `EXCHANGE_WIDE`, `MARKET_WIDE`, `MACRO`, `OTHER_ASSET`, `UNCLASSIFIED`.
  3. **Critical BNB / Exchange Disambiguation**:
     - Binance exchange operations, maintenance notices, Proof of Reserves, and general exchange settlements must be classified as `EXCHANGE_WIDE`, **never** `DIRECT_ASSET` for BNB unless the BNB token supply, auto-burn, or BNB Chain consensus is explicitly targeted.
  4. **Source C: Historical Macroeconomic & Protocol Calendar Registry**:
     - Create `news_macro_events` table storing canonical, scheduled vs actual release timestamps for FOMC interest rate decisions, BLS CPI releases, BLS NFP releases, and crypto structural milestones (Bitcoin Halvings, SEC ETF approvals).
     - All Source C events are verified against official agency domains (`federalreserve.gov`, `bls.gov`, `sec.gov`) and consensus blocks, designated as `POINT_IN_TIME_VERIFIED`.
  5. **Point-in-Time Research Boundary Enforcement**:
     - Records classified as `PARTIALLY_VERIFIED` (such as GDELT 15-minute GKG batches) are strictly excluded from high-frequency (1m, 5m, 15m) candle-level backtesting. Only `POINT_IN_TIME_VERIFIED` records with certified millisecond/second timestamps are eligible for candle-close synchronization.
  6. **Year-Partitioned Analytical Parquet Storage**:
     - Export articles and versions partitioned by source and event year (`storage/news/{source}/{YYYY}/`), verified against cryptographic manifests and composite SHA-256 fingerprints.
- **Rationale**:
  - Prevents false attribution of exchange-level operational announcements to asset-level fundamental alpha.
  - Establishes second-level ground truth for global macroeconomic volatility triggers.
  - Preserves strict look-ahead bias prevention (Rule S-05).
- **Consequences**:
  - Controlled research experiments in Milestone 4.6.3 can isolate direct asset news from exchange-wide noise and macroeconomic shocks.


## ADR-025: Two-Stage Deterministic Classification Remediation, 100% Historical Coverage & Next-Available-Price Execution Synchronization

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.2.1 independent forensic audit uncovered six systemic classifier failure modes (category accuracy 77.1%, relevance accuracy 86.7%), a 2025 historical coverage void (17 empty months out of 35), and the absence of a formalized next-open execution rule preventing same-candle look-ahead bias.
- **Decision**:
  1. **Two-Stage Deterministic Classifier (v1.1.0)**:
     - Implemented title-primary two-stage waterfall: headline patterns take strict precedence over body text.
     - Stripped legal/boilerplate footers and risk disclaimers (`Risk Warning:`, `Terms & Conditions`) before body scanning.
     - Normalized punctuation-delimited acronyms (`E.T.F.` $\to$ `ETF`, `S.E.C.` $\to$ `SEC`, `F.O.M.C.` $\to$ `FOMC`).
     - Enforced `MARKET_STRUCTURE` precedence over `EXCHANGE_OPERATIONAL` for margin, tick size, and fee schedules.
     - De-attributed promotional retail campaigns (Earn Wednesday, Launchpool, competitions) from primary asset trading pairs.
     - Isolated altcoin listings/delistings from quote pairs (`/BTC`, `/ETH`, `/BNB`).
     - Achieved 94.00% Category Accuracy, 94.00% Relevance Accuracy, and 89.33% Affected Assets Accuracy on independent $N=150$ manual validation set.
  2. **100% 35-Month Historical Coverage**:
     - Ingested Binance Catalog 49 (Blocks 1, 2, 5) and Catalog 161 (Pages 6-12), expanding the news database from 479 to 1,431 articles.
     - Populated all 35 contiguous calendar months (2024-01 through 2026-11), completely eliminating the 2025 coverage void (12 of 12 months populated).
  3. **Canonical Macroeconomic Calendar (Source C)**:
     - Expanded from 26 to 68 canonical records covering all FOMC rate decisions, BLS CPI prints, BLS NFP releases, and regulatory events across 2024, 2025, and 2026 with official agency URLs.
     - Applied Migration 007 adding `first_observed_at`, `collected_at`, and `revision_observed_at`.
  4. **Next-Available-Price Execution Rule**:
     - Formalized execution synchronization: An event is available to Bar $T$ if and only if $t_{\text{avail}} \le T_{\text{close}}$.
     - Order decisions emitted at $T_{\text{close}}$ must execute strictly at Bar $T+1$ Open ($T+1_{\text{open}}$).
     - Same-candle execution (at Bar $T$ Close, Open, or intrabar) is strictly prohibited as look-ahead bias.
     - Revisions arriving at $t > T_{\text{close}}$ are invisible to Bar $T$.
     - GDELT partially verified records are barred from sub-hourly execution without explicit latency buffer enforcement.
  5. **Storage Parity & Frozen Dataset Integrity**:
     - Verified exact zero-delta parity between SQLite (`neptune.db`) and Parquet partitions in `storage/news/`.
     - Confirmed frozen market dataset `v2.0.0` (420 files, tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) remains 100% bit-for-bit identical.
- **Consequences**:
  - NEPTUNE now possesses a historically rich, 100% temporally populated, point-in-time verified news and macro event foundation suitable for controlled strategy experiments.
  - Same-candle look-ahead bias is architecturally impossible in backtesting simulations.


## ADR-026: Deterministic Point-in-Time Execution Scheduling, Next-Eligible-Price Policy & Simulation Engine Integration

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.2.3 forensic audit demonstrated that while point-in-time temporal rules were defined in `temporal.py`, the backtest simulation loop (`HistoricalBacktestEngine`) filled orders instantaneously at `curr_candle.close`, creating an impossible physical fill and potential look-ahead bias for news-gated strategy experiments.
- **Decision**:
  1. **Formal Execution-Time Contract**:
     - Codified mandatory 9-coordinate execution provenance (`signal_timestamp`, `information_availability_cutoff`, `candle_close_timestamp`, `order_creation_timestamp`, `risk_approval_timestamp`, `risk_approval_token`, `earliest_eligible_execution_timestamp`, `actual_fill_timestamp`, `actual_fill_price`, `execution_policy`).
  2. **PointInTimeExecutionScheduler Component**:
     - Introduced `PointInTimeExecutionScheduler` managing `ScheduledOrder` lifecycle.
     - Enforces next-eligible-price execution: orders approved at candle close $T$ execute strictly at Bar $T+1$ Open.
     - Same-candle execution raises fatal `ValueError`.
     - Deterministic sorting by `(candle_close_timestamp, signal_id, symbol)` eliminates concurrency ambiguity.
     - Handled data gaps: gaps exceeding `max_execution_gap_bars` trigger deterministic order expiry.
     - Handled stop-loss opening gaps: market opens gapping past stop loss reject orders prior to fill.
  3. **NewsIntelligenceBoundary Component**:
     - Integrated `NewsIntelligenceBoundary` enforcing point-in-time availability, revision isolation, cluster deduplication, GDELT intraday prohibition, and quarantine of forward-scheduled macro releases.
  4. **Friction & Risk Manager Authority Preservation**:
     - Preserved exact 0.30% round-trip friction model with Decimal accounting.
     - Risk Manager remains sole authorization authority; requires cryptographic token for scheduling and re-verifies circuit breakers prior to execution.
  5. **Backward Compatibility via Policy Versioning**:
     - Introduced `ExecutionPolicy.LEGACY_CLOSE_FILL` (default for legacy regression tests) and `ExecutionPolicy.NEXT_ELIGIBLE_PRICE` (mandatory for news research).
- **Consequences**:
  - The historical simulation engine is fully integrated and point-in-time compliant. News-gated strategy experiments can proceed in Milestone 4.6.3 under zero look-ahead bias.


---

## ADR-027: Cryptographic HMAC-SHA256 Risk Authorization Token Binding and Macro Boundary Schema Normalization

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.2.5 adversarial audit revealed two security and schema vulnerabilities:
  1. Risk authorization tokens issued by `RiskManager` were pseudo-random UUIDs (`rat_{uuid}`) not bound to order parameters (symbol, side, quantity, price, stop loss), and the simulation scheduler did not cryptographically verify tokens before filling orders. Furthermore, `engine.py` contained an unsafe fallback (`or f"tok_{uuid}"`).
  2. `NewsIntelligenceBoundary` assumed generic dictionary keys (`event_id`, `actual_release_time`, `available_at`) which conflicted with the actual SQLite/Parquet macro calendar schema (`macro_event_id`, `actual_release_at`, `affected_assets_json`), causing macro records to be excluded as missing timestamps.
- **Decision**:
  1. **Cryptographic HMAC-SHA256 Risk Authorization**:
     - Upgraded `RiskManager.generate_risk_token` to generate HMAC-SHA256 signatures (`rat_v1_{digest}`) binding 8 execution parameters: `run_id`, `signal_id`, `symbol`, `direction`, `position_size`, `entry_price`, `stop_loss`, and `timestamp`.
     - Implemented `RiskManager.verify_risk_token` with constant-time verification (`hmac.compare_digest`).
     - Integrated pre-fill token verification into `PointInTimeExecutionScheduler.process_candle_open`: any altered parameter, token replay across signals/runs, or missing token immediately rejects the order with `OrderStatus.REJECTED`.
     - Completely removed the unauthenticated fallback token generation from `engine.py`.
  2. **Multi-Key Fallback Schema Normalization**:
     - Normalized `NewsIntelligenceBoundary` to natively resolve `macro_event_id`, `actual_release_at`, and deserialized `affected_assets_json`.
     - Updated `QUARANTINED_FORWARD_EVENTS` to quarantine canonical forward releases (`macro_20261104_fomc_decision` and `macro_20261112_bls_cpi`).
     - Enforced macro provenance gating across all macro event sources, isolating unprovenanced records (`macro_20240802_bls_nfp`).
  3. **Execution Cost Arithmetic Documentation Formalization**:
     - Clarified total round-trip friction as 32 bps (0.32%): 20 bps taker fees, 10 bps slippage, and 2 bps bid-ask spread.
- **Consequences**:
  - The Risk Manager's sole authorization authority (Rule S-04) is enforced cryptographically; orders cannot be tampered with or fabricated between approval and execution.
  - All 68 macro calendar records are accurately parsed, with 62 historical records point-in-time eligible, 2 forward records quarantined, 1 unprovenanced record excluded, and 3 asset-irrelevant records filtered for BTCUSDT.


---

## ADR-028: Cryptographic Risk Authorization Lifecycle, Atomic Token Idempotency, and Timeframe-Calibrated Execution Gap Policy

- **Status**: Accepted
- **Date**: 2026-11-03
- **Context**: Milestone 4.6.2.5.1 investigated the final operational requirements for risk authorization and execution readiness. While Milestone 4.6.2.5 added HMAC signatures to risk tokens, signature verification alone is stateless and does not prevent replay attacks (submitting identical valid tokens multiple times). Furthermore, execution-gap semantics and key rotation mechanics required formal codification.
- **Decision**:
  1. **Atomic Token Idempotency State Machine**:
     - Implemented stateful token lifecycle tracking inside `RiskManager`: `ISSUED` -> `RESERVED` -> `CONSUMED` (or `EXPIRED` / `CANCELLED`).
     - Thread-safe transitions enforced via `threading.Lock`.
     - `reserve_token` binds tokens to specific `order_id`s, preventing token reuse across different orders or duplicate scheduling.
     - `consume_token` atomically retires tokens upon execution; re-consumption attempts fail with `TOKEN_ALREADY_CONSUMED`.
     - `rollback_token` provides transient failure recovery during execution simulation interruptions.
  2. **Multi-Tier Execution Deduplication**:
     - `PointInTimeExecutionScheduler.schedule_order` enforces uniqueness across `scheduled_order_ids` and `scheduled_tokens`, immediately rejecting duplicate submissions.
     - `HistoricalBacktestEngine` enforces unique `trade_id` registration across all completed and force-closed ledger entries.
  3. **HMAC Key Lifecycle & Rotation**:
     - Keys are stored strictly in-memory (`self.auth_secret`); no persistence to database, disk, or logs (Rule S-02).
     - `RiskManager.rotate_key` invalidates all previously issued tokens immediately.
     - Cryptographic payload binding of `run_id` ensures bit-level token isolation between backtest runs even when sharing configuration keys.
  4. **Timeframe-Calibrated Execution Gap Policy**:
     - Bounded maximum allowable execution delay as $T_{\\text{max\\_allowed}} = \\Delta_{\\text{timeframe}} \\times (\\text{max\\_execution\\_gap\\_bars} + 1)$.
     - Calibrated policy: `max_execution_gap_bars = 1` for 15m intraday execution (30 min max delay to prevent momentum signal decay); `3` for 1h (4h delay), 4h (16h delay), and 1d (4d delay) swing/macro regimes.
     - Orders exceeding the gap threshold cleanly expire and transition their associated risk tokens to `EXPIRED`.
- **Consequences**:
  - Replay attacks, token double-spending, and duplicate ledger entries are architecturally impossible.
  - Risk Manager is the sole, stateful, and cryptographically verified order authority (Rule S-04).
  - The historical simulation engine is fully verified and hardened for upcoming news strategy experiments.


---

## ADR-029: News-Gated Experiment Design, Baseline Freeze, and Four-Group Research Protocol

- **Status**: Accepted
- **Date**: 2026-11-06
- **Context**: Milestone 4.6.3.0 establishes the empirical evaluation framework to answer whether point-in-time news intelligence improves net trading expectancy over a deterministic technical baseline after realistic costs. Evaluating this requires freezing the baseline, defining appropriate controls, establishing the news-veto contract, creating non-overlapping chronological splits, and detailing the statistical testing plan.
- **Decision**:
  1. **Frozen Baseline Configuration**:
     - Virtual capital: 1,000 USDT, spot leverage capped at 1.0x (no margin).
     - Risk invariants: 0.5% risk per trade, 2.0% daily loss limit, 5.0% max drawdown circuit breaker, 1.5:1 min RR ratio.
     - Execution policy: `NEXT_ELIGIBLE_PRICE` (Bar $T+1$ Open fill). Execution gap: 1 bar for 15m (30 min delay max), 3 bars for HTF.
     - Cost model: 0.10% taker fee, 0.05% adverse slippage, 0.01% half-spread (0.32% round trip).
     - Baseline configuration fingerprint SHA-256: `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`.
  2. **Four-Group Research Architecture**:
     - **Group A (Technical Baseline)**: Reference group running deterministic strategy without news intelligence.
     - **Group B (News Veto)**: Technical candidates subjected to adverse point-in-time news veto. No directional trade generation; no Risk Manager override.
     - **Group C (Frequency-Matched Control)**: Thins Group A candidates to match Group B's trade count using deterministic zero-lookahead methods (systematic decimation, technical confidence priority, cryptographic seed selection).
     - **Group D (Exposure-Matched Control)**: Dynamic cooldown budget matching cumulative time-in-market and capital utilization to Group B without consuming future data.
  3. **Formal News-Veto Contract & 13-Category Taxonomy**:
     - Created `NewsVetoContract` Pydantic model enforcing millisecond publication availability, revision isolation, and exclusion reason codes.
     - Codified 13-category taxonomy specifying research eligibility, affected assets, direct vs market-wide relevance, and timeframe eligibility.
     - GDELT strictly prohibited for intraday (`15m`, `1h`, `4h`).
  4. **Chronological Research Partitioning (35 Months)**:
     - Partition 1 (Development / Training): `2024-01-01` to `2024-12-31` (12 months, 380 records).
     - Partition 2 (Validation): `2025-01-01` to `2025-12-31` (12 months, 594 records).
     - Partition 3 (Locked Out-of-Sample): `2026-01-01` to `2026-10-31` (10 months, 478 records, strictly locked).
     - Quarantined Forward: `2026-11-01` to `2026-11-03` (4 records, forward macro events quarantined).
     - Verified zero cluster leakage across partition years.
  5. **Statistical Analysis Plan (SAP)**:
     - Primary metrics: Net expectancy per trade, Net portfolio return, Maximum drawdown, Profit factor.
     - Secondary metrics: Win rate (95% Wilson CI), Sharpe, Sortino, trade frequency, market exposure, capital utilization.
     - Statistical testing: Paired Wilcoxon signed-rank test on candidate signals, 48-bar moving block bootstrap ($B=2000$), Benjamini-Hochberg FDR correction ($q=0.05$).
     - Economic hurdle: $+\$0.50$ USDT net expectancy outperformance after 0.32% round-trip friction.
  6. **Master Reproducibility Fingerprint**:
     - Composite SHA-256 fingerprint: `5ffc9b1bed97138db0b8ceab7aab2514116b02c88cdac26f322af2d5f6b18ced`.
- **Consequences**:
  - The deterministic baseline is immutable and reproducible across independent audit runs.
  - Disentangles genuine informational alpha from frequency reduction and exposure bias.
  - The research protocol is fully frozen, documented, and ready for subsequent controlled execution.

---

## ADR-030: Online Control Matching, Executable News Veto Engine, Timeframe Bootstrap Calibration, and OOS Access Guard

- **Status**: Accepted
- **Date**: 2026-11-06
- **Context**: Milestone 4.6.3.0.1 conducted an independent quantitative and methodological audit of the research protocol established in Milestone 4.6.3.0. The audit revealed five critical areas requiring formal architectural remediation:
  1. *Ex-Post Diagnostic Benchmarking vs Online Execution (Group C)*: Batch decimation and confidence pruning algorithms require the final count of Group B trades ($N_B$) across the partition, making them retrospective diagnostic benchmarks rather than point-in-time executable online strategies.
  2. *Exposure Conflation (Group D)*: Scalar trade count does not match exposure due to holding time variance under trailing stops, overlapping multi-asset positions, and directional asymmetry.
  3. *Executable News-Veto Contract*: Category rules lacked an executable decision engine parameterizing decay windows, severity thresholds, cluster deduplication, and revision cutoff isolation.
  4. *Bootstrap Timeframe Mismatch*: A uniform 48-bar block produced 12 hours on 15m (too short to preserve autocorrelation) and 48 days on 1d (too long). Denominators ($E_{\text{trade}}$ vs $E_{\text{cand}}$) required explicit mathematical separation.
  5. *Out-of-Sample Snooping Protection*: Documentation alone did not prevent automated backtests from accidentally querying the locked Jan-Oct 2026 partition.
- **Decision**:
  1. **Control Execution Mode Taxonomy**:
     - Introduced `ControlExecutionMode` separating `ONLINE_POINT_IN_TIME` from `EX_POST_DIAGNOSTIC`.
     - Implemented `OnlineFrequencyMatchingEngine` (Method C-Online) evaluating candidates sequentially using a pre-registered thinning probability $\rho_{\text{calib}}$ and candidate-level cryptographic HMAC-SHA256 hashing without future knowledge.
     - Labeled `ExPostFrequencyMatchingEngine` explicitly as an ex-post diagnostic control for retrospective benchmarking once $N_B$ is known.
  2. **Seven-Dimensional Exposure Tracking**:
     - Formalized `ExposureDimensions` tracking: time in market bars, time in market percentage, trade count, average holding bars, asset breakdown, directional duration (LONG vs SHORT), dollar-hours capital utilization, simultaneous multi-asset bars, and gross/net exposure.
     - Implemented `OnlineExposureMatchingEngine` enforcing a dynamic post-trade cooldown online, with `ExPostExposureMatchingEngine` retained as a retrospective benchmark.
  3. **Executable News-Veto Engine**:
     - Implemented `NewsVetoDecisionEngine` with pre-registered category decay windows (2h for operational/macro to 24h for security exploits), adverse threshold $\theta = 0.70$, cluster deduplication, and revision cutoff enforcement.
  4. **Timeframe-Calibrated Block Bootstrap & Denominator Separation**:
     - Calibrated moving block bootstrap sizes to ~4 calendar days (96 hours) across all timeframes: 15m (384 bars), 1h (96 bars), 4h (24 bars), 1d (7 bars).
     - Formalized distinct reporting of expectancy per trade ($E_{\text{trade}}$), expectancy per candidate ($E_{\text{cand}}$), and portfolio return ($R_{\text{portfolio}}$).
  5. **Programmatic Cryptographic OOS Guard**:
     - Implemented `OOSAccessGuard` raising `PermissionError` on unauthorized simulation dates overlapping `2026-01-01` to `2026-10-31`, requiring an HMAC-SHA256 governance authorization token.
- **Consequences**:
  - Eliminates subtle look-ahead leakage in control group matching.
  - Guarantees strict out-of-sample data protection against snooping.
  - Fortifies the statistical validity and economic interpretability of future news-gated strategy experiments.

---

## ADR-031: Development-Partition Experimental Execution, 4-Group Synchronized Simulation Engine, and Candidate Stream Caching

- **Status**: Accepted
- **Date**: 2026-11-07
- **Context**: Milestone 4.6.3.1 required the formal execution of the frozen research protocol across the 2024 Development partition (105,408 candles across BTCUSDT, ETHUSDT, BNBUSDT on 15m). The experiment evaluated whether point-in-time news intelligence improves net trading outcomes beyond the deterministic technical baseline. To ensure 100% scientific validity, execution required:
  1. Synchronized parallel execution of all 4 experimental groups (A: Technical Baseline, B: News Veto, C: Frequency Control, D: Exposure Control) on the exact same candidate setup stream.
  2. Point-in-time execution scheduling enforcing `NEXT_ELIGIBLE_PRICE` with cryptographic HMAC risk authorization tokens bound to the specific experimental run (`exp_{group_id}_2024`).
  3. Strict isolation of 2024 data, cryptographically guarded against access to 2025 Validation and locked 2026 Out-of-Sample partitions.
  4. Preservation and persistence of the raw candidate stream to guarantee deterministic, bit-for-bit reproducible bootstrap re-runs without 18-minute agent re-computations.
- **Decision**:
  1. **Development Partition Orchestration Architecture (`DevelopmentExperimentRunner`)**:
     - Built `backend/app/simulation/development_orchestrator.py` executing a 4-group parallel event loop.
     - Enforces complete independence between group portfolios while maintaining 100% synchronized market perceptions and candidate signals.
     - Cryptographically binds Risk Manager HMAC tokens to each group run ID to strictly prevent cross-group token substitution (`CROSS_RUN_TOKEN_FORBIDDEN`).
  2. **Candidate Stream Deterministic Caching**:
     - Implemented candidate stream serialization and caching at `storage/exports/milestone_4_6_3_1/candidate_cache_2024.json`.
     - Preserves the full perception state `(cand_dict, RawCandidateSignal, regime_str)` across all 105,408 timestamps.
  3. **Multi-Hypothesis Bootstrap & Statistical Rigor**:
     - Embedded 384-bar (4-day) Moving Block Bootstrap ($B=2000$) computing empirical p-values for H1 (Group B vs A), H2 (Group B vs C), and H3 (Group B vs D).
     - Applied Benjamini-Hochberg False Discovery Rate ($q=0.05$) correction across all confirmatory tests.
     - Evaluated economic hurdle requirement ($+\$0.50$ USDT net expectancy improvement per trade after 0.32% round-trip friction).
  4. **Ex-Post Diagnostic Benchmarking Suite**:
     - Retained and executed Methods C1 (Systematic Decimation), C2 (Confidence Pruning), C3 (Seed Selection), and D-ExPost (Exposure Budget) as retrospective diagnostic controls once $N_B$ and total exposure are observed.
- **Consequences**:
  - Delivers complete mathematical, operational, and execution provenance for Milestone 4.6.3.1.
  - Guarantees zero look-ahead bias and bit-for-bit experimental reproducibility.
  - Fully complies with Rules S-01, S-04, S-05, S-06, and ADR-001 through ADR-030.

---

## ADR-032: Independent Forensic Accounting Reconciliation, Cash-Equity Inversion Remediation, and Point-Mass Bootstrap Diagnosis

- **Status**: Accepted
- **Date**: 2026-11-07
- **Context**: Milestone 4.6.3.1.1 performed an independent forensic audit of the completed Milestone 4.6.3.1 Development-partition experiment. The audit identified two critical accounting implementation defects and one statistical methodology artifact:
  1. *Cash Equity Inverted Sign on Short Positions*: The cash tracking engine subtracted `size * price` on entry and added `size * price` on exit unconditionally. For short positions (63.2% of executed trades), losing short trades credited cash, injecting phantom cash that masked true ending equity ($785.28 USDT vs reported $984.56 USDT) and true drawdown (24.87% vs reported 5.19%).
  2. *Metric Aggregation Conditioning Flaw*: `gross_profit` and `gross_loss` in `group_metrics.json` were partitioned conditioned on `net_pnl > 0` rather than `gross_pnl > 0`, causing net losers with positive gross PnL to have their gross gains flipped to losses via `abs(gross_pnl)`.
  3. *Bootstrap Point-Mass Artifact*: Applying a moving block bootstrap to an irregularly spaced candidate stream where 98.48% of values are zero resulted in 58.2% of bootstrap resamples evaluating to exactly `0.0000`, causing the 2.5th percentile to collapse to `0.0000` while $p(\text{mean} \le 0) = 0.5950$.
- **Decision**:
  1. **Formal Separation of True Realized vs Cash Accounting**:
     - Document and certify true realized ending equity strictly as $\text{Initial Equity} + \sum \text{Net PnL}$ ($785.28 USDT for Group A, $885.58 USDT for Group B).
     - Isolate and document the phantom cash injection mechanism in `equity_curve_reconciliation.json`.
  2. **Standardization of Gross Profit and Loss Definitions**:
     - Standardize gross profit as $\sum \max(0, \text{Gross PnL})$ across all trades, and gross loss as $\sum |\min(0, \text{Gross PnL})|$ across all trades.
  3. **Preservation of Original Artifacts**:
     - Preserve all original Milestone 4.6.3.1 outputs unchanged in `storage/exports/milestone_4_6_3_1/`.
     - Publish all reconciled figures and artifacts independently in `storage/exports/milestone_4_6_3_1_1/`.
  4. **Strict Stop Condition**:
     - Affirm that the underlying technical strategy suffers from severe negative drift (-21.47% return, 24.87% drawdown) and news vetoing adds no statistically significant alpha ($p = 0.5950$).
     - Enforce a strict governance stop condition halting forward execution to Milestone 4.6.3.2.
- **Consequences**:
  - Restores 100% mathematical and accounting transparency to the NEPTUNE research archive.
  - Formulates the exact accounting fixes required for any future engine revisions.
  - Strictly preserves research integrity by preventing premature or unwarranted entry into out-of-sample partitions.


---

## ADR-033: Portfolio Accounting Remediation, Double-Entry Short Collateral Model, and Risk Breaker Enforcement

- **Status**: Accepted
- **Date**: 2026-11-07
- **Context**: Milestone 4.6.3.1.2 was commissioned to correct the portfolio cash/equity accounting defect identified in Milestone 4.6.3.1.1 and independently revalidate Risk Manager circuit breaker enforcement and historical experiment reproducibility.
- **Decision**:
  1. **Implementation of `PortfolioLedger`**:
     - Introduced [`PortfolioLedger`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/portfolio_ledger.py) maintaining liquid cash balance, reserved collateral for short positions, long inventory cost basis, and marked-to-market position equity.
     - Formulated exact mathematical cash flow dynamics for spot-collateralized SHORT positions without leverage:
       - Entry cash outflow: $\text{Notional} + \text{Fee}_{\text{entry}}$ (100% margin reservation).
       - Exit cash inflow: $S \cdot (2 P_{\text{entry}} - P_{\text{exit}}) - \text{Fee}_{\text{exit}}$, ensuring net cash flow strictly equals $\text{net\_pnl}$.
     - Established continuous mark-to-market updating at every candle close using confirmed close prices.
     - Verified 5 fundamental balance sheet invariants across all positions and trades.
  2. **Risk Manager 5.0% Circuit Breaker Revalidation**:
     - Connected `RiskManager` and `PointInTimeExecutionScheduler` directly to `PortfolioLedger.get_total_equity()`.
     - Confirmed that when true portfolio drawdown breaches 5.0%, all subsequent orders are rejected immediately with `MAX_DRAWDOWN_EXCEEDED` and `"Drawdown circuit breaker active at execution time"`.
  3. **Historical Reproduction Across 2024 Development Partition**:
     - Re-ran the 4-group parallel experiment across the full 2024 Development partition using [`run_milestone_4_6_3_1_2.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/run_milestone_4_6_3_1_2.py).
     - Confirmed all 4 groups tripped the circuit breaker on January 5–6, 2024, halting trading after 11–12 trades, stabilizing ending equity at \$976.44 USDT (-2.36%), and preserving \$181.85 USDT of capital compared to unhalted trading.
  4. **Null-Centered Market-Time Bootstrap Inference**:
     - Remediated the bootstrap procedure by mapping returns onto a continuous 15m regular market-time grid (35,136 bars, 384-bar / 4-day blocks) and centering resamples under the null hypothesis ($H_0: \mu \le 0$).
     - Proved that news vetoing fails all confirmatory hypotheses ($p = 0.1740$) and fails the pre-registered economic hurdle ($+\$0.0009$ USDT vs $+\$0.50$ USDT target).
  5. **Governance Halt**:
     - Enforced mandatory stop condition: Zero progression to Milestone 4.6.3.2, 2025 Validation, or 2026 Out-of-Sample partitions.
- **Consequences**:
  - Eliminates all phantom cash and accounting distortions across NEPTUNE simulation engines.
  - Re-establishes the Risk Manager as a certified, trustworthy capital preservation authority.
  - Generates 8 verified, immutable audit deliverables in `storage/exports/milestone_4_6_3_1_2/`.


---

## ADR-034: Synthetic Short Collateralization Classification, Risk-Breaker Embargo Semantics, and Statistical Active-Window Partitioning

- **Status**: Accepted
- **Date**: 2026-11-07
- **Context**: Milestone 4.6.3.1.3 conducted an independent forensic audit of Milestone 4.6.3.1.2. The audit verified the mathematical integrity of `PortfolioLedger` and identified three foundational architectural classifications requiring formal codification:
  1. *Short-Position Model Classification*: The shorting mechanism in `PortfolioLedger` operates via 1:1 cash collateral reservation ($1.0\times$ leverage) without securities lending, borrow availability constraints, or continuous borrow interest. This must be formally classified as Synthetic Fully Collateralized Short Exposure.
  2. *Risk-Breaker Overshoot Semantics*: Portfolio maximum drawdown settled at 5.51%–5.55%, exceeding the 5.0% circuit breaker parameter. The audit confirmed that the breaker acts as an Order Authorization Embargo (New Entry Halt) rather than an Emergency Market Liquidation. In-flight positions authorized prior to the breach are permitted to resolve at their stop-loss brackets, generating an expected ~0.55% overshoot.
  3. *Statistical Inactive Period Dominance*: Because the circuit breaker halted trading on Day 6, 98.6% of chronological bars in 2024 (34,636 bars) contained identical $0.00 returns across all groups. Statistical inference requires explicit partitioning into Active Window vs Full Year analysis.
- **Decision**:
  1. **Formal Model Classification**:
     - Officially classify NEPTUNE v1 short trading as "Synthetic Fully Collateralized Spot Exposure" compliant with Rule S-01 (paper simulation only, zero leverage).
     - Document that borrow interest fees (~0.005% per trade) and borrow liquidity constraints are omitted as deliberate research abstractions for Tier-1 liquid crypto assets.
  2. **Codification of Breaker Policy Semantics**:
     - Codify that the 5.0% drawdown circuit breaker enforces an Order Authorization Embargo. Open positions are managed strictly by their predefined stop-loss brackets.
     - Verify that the circuit breaker creates a mathematically absorbing state with zero order leakage post-embargo (3,130 to 3,666 subsequent signals rejected per group).
  3. **Dual-Window Statistical Reporting**:
     - Standardize dual-window reporting for simulations halting at circuit breakers: reporting both the Active Trading Window (bars 0 to 500) and the Full Simulation Partition (35,136 bars).
  4. **Strict Research Governance Halt**:
     - Reaffirm the mandatory stop condition: Zero progression to Milestone 4.6.3.2, 2025 Validation, or 2026 Out-of-Sample partitions.
- **Consequences**:
  - Eliminates ambiguity regarding short selling realism and circuit breaker behavior.
  - Certifies the mathematical and execution soundness of Milestone 4.6.3.1.2 under `PASS WITH LIMITATIONS`.
  - Preserves 100% research integrity under NEPTUNE governance rules.
