# Product Requirements Document (PRD)

## Document Information
- **Project**: NEPTUNE
- **Vision**: Autonomous Market Intelligence & Paper Trading Platform
- **Document Version**: 1.0.0
- **Status**: Approved / Active Specification
- **Target Release**: v1.0.0
- **Author**: Neptune Architecture & Core Engineering Team
- **Date**: 2026-11-01

---

## 1. Executive Summary & Product Vision

### 1.1 Vision Statement
> **"NEPTUNE — Autonomous Market Intelligence & Paper Trading Platform"**

NEPTUNE is an enterprise-grade, institutional-inspired cryptocurrency market intelligence, quantitative strategy simulation, and automated paper trading system. Designed from the ground up for extreme precision, algorithmic rigor, and transparent autonomous decision-making, NEPTUNE operates a multi-agent analytical hierarchy coordinated by an overarching Central Brain.

NEPTUNE bridges the gap between opaque "black box" trading bots and institutional quantitative terminals. It models market dynamics, validates strategic hypotheses through forward Monte Carlo and bootstrap simulations ("Time Machine"), enforces non-negotiable risk rules, and conducts realistic paper execution without risking capital.

### 1.2 Core Philosophy
1. **Capital Preservation Above All**: No strategy or signal can bypass hard-coded risk guardrails.
2. **Deterministic Explainability**: Every trade recommendation must have a fully traceable, mathematically sound causal chain from raw market ticks to brain state transitions.
3. **Realistic Simulation**: Paper trading is treated with live-execution fidelity, including slippage modeling, fill latencies, taker fees, and spread penalties.
4. **Zero-Trust Intelligence**: Specialized agents compute domain-specific insights (trend, momentum, volume, sentiment), but only the Central Brain, Signal Validator, and Risk Manager have the authority to progress signals into orders.

---

## 2. Scope & Guardrails

### 2.1 In-Scope (Version 1.0)
- **Market Data**: Real-time and historical cryptocurrency spot market data via Binance Public REST and WebSocket APIs (e.g., BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT).
- **Execution Mode**: Strictly **Paper Trading Only**. All account balances, orders, fills, positions, and profit/loss calculations are simulated locally.
- **API Credentials**: Zero private API keys, zero wallet seed phrases, and zero real money account connectivity. All data ingress utilizes unauthenticated public endpoints.
- **Agent Architecture**: 10 deterministic specialist agents running concurrently in an asynchronous execution pipeline.
- **Simulation Engine (Time Machine)**: 1000-path forward simulation incorporating Historical Bootstrap, Block Bootstrap, Volatility-Conditioned, and Regime-Conditioned modeling.
- **Storage**: Local embedded architecture combining SQLite (WAL mode) for transactional state/metadata and Apache Parquet for time-series tick/candle storage.
- **User Interface**: High-performance, dark-mode financial workstation built with Next.js 14+ App Router, Zustand, Tailwind CSS, Framer Motion, and TradingView Lightweight Charts.

### 2.2 Explicitly Out-of-Scope (v1)
- **Live / Real-Money Execution**: No live broker or exchange execution routing.
- **Exchange Authentication**: No account keys (`API_KEY`, `API_SECRET`) or signing routines.
- **Database Servers**: No external PostgreSQL, MySQL, or distributed databases.
- **Distributed Message Brokers**: No Redis, Kafka, or RabbitMQ clusters. Inter-process messaging is handled in-process via Python `asyncio` and internal event buses.
- **Microservices Deployment**: No Docker Swarm or Kubernetes orchestration required for local development; packaged as a modular monolith.
- **Generative LLM Reasoning in Critical Path**: No non-deterministic external LLM API calls in the execution or risk approval loop.

---

## 3. Specialist Agent Topology

NEPTUNE deploys ten distinct specialist agents. Each agent possesses a single, bounded context of analysis, strict input/output contracts, and isolated failure domains.

| Agent Name | Agent ID | Core Responsibility | Trigger Frequency / Mode |
|---|---|---|---|
| **Market Scanner** | `market_scanner` | Continuously scans target symbols, evaluates volatility regimes (low, normal, high, extreme), classifies market state (trending, mean-reverting, compressed). | Event-driven (new 1m/5m candle) & 10s poll |
| **Trend Analyst** | `trend_analyst` | Computes directional bias across multiple timeframes (1m, 5m, 15m, 1h, 4h) using EMA ribbons (20, 50, 100, 200), Parabolic SAR, and ADX directional strength. | On candle close (1m, 5m, 15m) |
| **Momentum Analyst** | `momentum_analyst` | Analyzes velocity and acceleration of price moves via RSI, Stochastic RSI, MACD histogram, and multi-timeframe divergence detection. | On candle close & significant price movement |
| **Volume Analyst** | `volume_analyst` | Evaluates liquidity profile, volume anomalies (>2.5x rolling standard deviation), Volume Weighted Average Price (VWAP) deviations, and Order Flow Imbalance. | On candle close & volume spike event |
| **News Analyst** | `news_analyst` | Deterministic sentiment proxy evaluating aggregated news headlines, economic calendar alerts, and volatility event flags without stochastic LLM latency. | Scheduled (every 60s) & breaking event |
| **Strategy Analyst** | `strategy_analyst` | Evaluates active strategy definitions (Trend Following, Mean Reversion, Breakout, Volatility Squeeze) against current technical contexts to emit raw candidate signals. | On analysis bundle ready from upstream analysts |
| **Signal Validator** | `signal_validator` | Performs cross-timeframe alignment, rule-based confluence scoring, false-breakout filtering, and historical reliability checking on candidate signals. | Event-driven (on raw signal emission) |
| **Risk Manager** | `risk_manager` | Absolute veto and sizing authority. Verifies account drawdown, daily loss limit, open position limits, correlation exposure, and assigns strict position sizing. | Event-driven (on validated signal) |
| **Execution Manager** | `execution_manager` | Simulates realistic paper order lifecycle (LIMIT, MARKET, STOP_LOSS, TAKE_PROFIT), models fill latency, spread, slippage, and tracks active position PnL. | Event-driven (on order approval) & 1s tick |
| **Performance Auditor** | `performance_auditor` | Computes live execution metrics (Sharpe ratio, Sortino ratio, Win rate, Profit factor, Maximum drawdown, Expectancy), flags execution slippage anomalies. | On position close & scheduled (every 5m) |

---

## 4. User Stories & Functional Requirements by Section

### 4.1 Section 1: Command Center (Executive Dashboard)
- **User Story**: *As a quantitative trader, I want a single high-level command console displaying real-time system health, active positions, equity curves, brain state, and urgent alerts, so that I can immediately assess platform performance and system integrity.*
- **Functional Requirements**:
  - `REQ-CC-01`: Render real-time virtual equity, unrealized PnL, realized PnL, available margin, and total exposure updated at $\le 1$ Hz.
  - `REQ-CC-02`: Display Central Brain status badge indicating current operational state (e.g., `OBSERVING`, `ANALYZING`, `RISK_REVIEW`).
  - `REQ-CC-03`: Display status indicators for all 10 specialist agents (Healthy, Degraded, Stalled, Offline).
  - `REQ-CC-04`: Provide one-click global emergency controls: "System Pause", "System Resume", and "Kill Switch" (halts all new trading immediately).
  - `REQ-CC-05`: Stream system notification feed showing high-priority risk warnings, filled orders, and regime transitions.

### 4.2 Section 2: Live Markets
- **User Story**: *As an analyst, I want to inspect live multi-symbol candlestick charts with real-time price updates, order book depth previews, technical overlays, and agent signal annotations, so that I can visually verify algorithmic assessments.*
- **Functional Requirements**:
  - `REQ-LM-01`: Integrate high-performance TradingView Lightweight Charts supporting Candlestick, Line, and Volume Histogram representations.
  - `REQ-LM-02`: Support timeframe switching: 1m, 3m, 5m, 15m, 1h, 4h, 1d.
  - `REQ-LM-03`: Render real-time price tick updates over WebSocket with zero chart lag or stutter.
  - `REQ-LM-04`: Overlay specialist agent indicators directly on charts (EMA 20/50/200, VWAP bands, Bollinger Bands, ATR channels).
  - `REQ-LM-05`: Plot historical and pending paper orders, stop-loss markers, and take-profit targets directly onto the price canvas.

### 4.3 Section 3: AI Agent Center
- **User Story**: *As a systems engineer, I want to inspect the internal telemetry, execution logs, compute latency, and decision output of all 10 agents individually, so that I can audit agent logic and detect anomalies.*
- **Functional Requirements**:
  - `REQ-AC-01`: Provide dedicated tab/card view for each of the 10 specialist agents.
  - `REQ-AC-02`: Display agent configuration parameters, execution schedule, dependencies, and average execution runtime in milliseconds.
  - `REQ-AC-03`: Present live payload inspector showing input contract received and output contract produced for any selected execution cycle.
  - `REQ-AC-04`: Display rolling error rate, exception traces, and circuit-breaker status per agent.
  - `REQ-AC-05`: Allow manual execution trigger ("Run Cycle Now") for debugging during market observation states.

### 4.4 Section 4: Central Brain
- **User Story**: *As a lead researcher, I want to observe the Central Brain’s finite state machine in real time, inspecting how upstream agent analyses coalesce into validated hypotheses, so that I understand why every trade was initiated or rejected.*
- **Functional Requirements**:
  - `REQ-CB-01`: Render visual state machine diagram highlighting the active state:
    `OBSERVING` $\rightarrow$ `ANALYZING` $\rightarrow$ `SIGNAL_DETECTED` $\rightarrow$ `VALIDATING` $\rightarrow$ `SIMULATING` $\rightarrow$ `RISK_REVIEW` $\rightarrow$ `APPROVED / REJECTED` $\rightarrow$ `PAPER_ORDER_CREATED` $\rightarrow$ `POSITION_MONITORING` $\rightarrow$ `CLOSED` $\rightarrow$ `AUDITED`.
  - `REQ-CB-02`: Provide an immutable, sequential decision timeline logging every evaluation step with timestamp, trigger condition, and voting weights.
  - `REQ-CB-03`: Expose the hypothesis synthesizer output, detailing confidence scores, conflicting agent signals, and resolution rationale.
  - `REQ-CB-04`: Stream live state change events over dedicated WebSocket (`/ws/brain`).

### 4.5 Section 5: Time Machine (Monte Carlo & Forward Simulation)
- **User Story**: *As a risk engineer, I want candidate signals to undergo high-speed forward trajectory simulations across 1000 synthetic paths before execution approval, so that I can quantify tail risk, maximum adverse excursion, and stop-out probabilities.*
- **Functional Requirements**:
  - `REQ-TM-01`: Execute 1000-path stochastic forward projections over configurable horizons (12 to 96 candles).
  - `REQ-TM-02`: Support four distinct simulation methods:
    1. Historical Bootstrap (sampling return distributions with replacement)
    2. Block Bootstrap (preserving 24-candle autocorrelation)
    3. Volatility-Conditioned (scaling paths by live ATR / historical ATR ratio)
    4. Regime-Conditioned (filtering paths to match current market regime)
  - `REQ-TM-03`: Calculate path percentiles ($p5, p10, p25, p50, p75, p90, p95$), median Maximum Adverse Excursion (MAE), and target-hit vs. stop-hit probabilities.
  - `REQ-TM-04`: Provide interactive visual fan charts (cone of uncertainty) in the frontend matching exact simulation percentiles.
  - `REQ-TM-05`: Enforce deterministic reproducibility: any simulation must be 100% reproducible given its unique 64-bit integer seed and model version.

### 4.6 Section 6: Strategy Laboratory
- **User Story**: *As a quantitative strategist, I want to configure, backtest, and compare rule-based trading strategies against historical Parquet datasets, so that I can validate parameters before activating them in paper trading.*
- **Functional Requirements**:
  - `REQ-SL-01`: Support built-in baseline strategies: EMA Cross & Trend Follower, Mean Reversion with RSI/Bollinger Bands, Volatility Breakout with Volume Confirmation, and Dual-Momentum Oscillator.
  - `REQ-SL-02`: Enable granular parameter configuration (lookbacks, thresholds, ATR multipliers, stop-loss ratios) with schema validation.
  - `REQ-SL-03`: Run backtests against multi-year historical Parquet candle datasets stored locally.
  - `REQ-SL-04`: Generate backtest metrics: Cumulative Return, CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, Calmar Ratio, Win Rate, and Average Trade Duration.
  - `REQ-SL-05`: Enable/disable strategies dynamically for the `StrategyAnalyst` agent.

### 4.7 Section 7: Paper Trading Execution Console
- **User Story**: *As an active operator, I want to monitor simulated order generation, fill simulations, order book matching delays, and slippage calculations in real time, so that I experience realistic institutional order handling.*
- **Functional Requirements**:
  - `REQ-PT-01`: Model order types: `MARKET`, `LIMIT`, `STOP_LOSS_LIMIT`, and `TAKE_PROFIT_LIMIT`.
  - `REQ-PT-02`: Simulate realistic execution physics:
    - Order fill delay: 50ms – 250ms stochastic latency.
    - Slippage modeling: Function of order size relative to 1-minute volume and volatility.
    - Fee modeling: Configurable taker (default 0.04%) and maker (default 0.02%) fees deducted in USDT.
  - `REQ-PT-03`: Provide live table of pending orders with cancel, modify, and force-fill capabilities for testing.
  - `REQ-PT-04`: Record granular order life-cycle timestamps: `created_at`, `submitted_at`, `partially_filled_at`, `filled_at`, `cancelled_at`, `rejected_at`.

### 4.8 Section 8: Portfolio & Positions
- **User Story**: *As a portfolio manager, I want an exhaustive overview of open positions, entry prices, liquidation thresholds, unrealized PnL, margin utilization, and position risk contributions.*
- **Functional Requirements**:
  - `REQ-PP-01`: Display active positions table: Symbol, Direction (LONG/SHORT), Size, Entry Price, Mark Price, Liquidation Buffer, Unrealized PnL (USDT & %), Target Price, Stop Loss.
  - `REQ-PP-02`: Provide position management actions: One-click Market Close, Tighten Stop to Breakeven, Scale Out (50%), and Cancel Attached Bracket Orders.
  - `REQ-PP-03`: Calculate portfolio-level Greeks and exposure metrics: Net Delta, Gross Exposure, Portfolio Leverage Ratio (capped at 1.0x in v1).
  - `REQ-PP-04`: Display interactive position timeline showing unrealized PnL progression against historical entry.

### 4.9 Section 9: Performance Analytics & Auditing
- **User Story**: *As an auditor, I want detailed historical trade logs, equity curves, drawdown underwater charts, trade duration distributions, and anomaly reports to mathematically evaluate platform edge.*
- **Functional Requirements**:
  - `REQ-PA-01`: Display equity curve and underwater drawdown chart (percentage drop from high-water mark over time).
  - `REQ-PA-02`: Tabulate comprehensive closed trade history with entry/exit timestamps, fees paid, net return, trade duration, and exit reason (Take Profit, Stop Loss, Trailing Stop, Manual Close, Circuit Breaker).
  - `REQ-PA-03`: Calculate rolling performance statistics: Sharpe Ratio, Sortino Ratio, Profit Factor, Expectancy, Win/Loss Ratio, and Maximum Consecutive Losses.
  - `REQ-PA-04`: Automated execution audit report highlighting slippage variance (expected vs. realized) and latency distribution.

### 4.10 Section 10: System Monitoring & Telemetry
- **User Story**: *As a site reliability engineer, I want visibility into backend resource utilization, WebSocket connection health, database query latencies, and event bus throughput to ensure 99.99% operational uptime.*
- **Functional Requirements**:
  - `REQ-SM-01`: Display host machine metrics: CPU utilization, RAM usage, disk I/O, SQLite file size, and Parquet storage footprint.
  - `REQ-SM-02`: Real-time status for all inbound Binance WebSocket feeds and outbound client WebSocket connections.
  - `REQ-SM-03`: Real-time event bus metrics: Messages processed per second, queue depth, average event latency.
  - `REQ-SM-04`: Live streaming system logs with log level filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### 4.11 Section 11: System Settings & Risk Parameters
- **User Story**: *As a platform administrator, I want to configure risk limits, trading parameters, data storage paths, and network connection parameters safely with immediate validation.*
- **Functional Requirements**:
  - `REQ-ST-01`: Configure global risk parameters: Initial Capital (default 1000 USDT), Max Concurrent Positions (default 2), Max Risk Per Trade (default 0.5%), Daily Loss Limit (default 2.0%), Max Drawdown Circuit Breaker (default 5.0%).
  - `REQ-ST-02`: Configure market data targets: Enable/disable active trading pairs (e.g., BTC/USDT, ETH/USDT, SOL/USDT).
  - `REQ-ST-03`: Manage historical data synchronization: Trigger backfills, verify Parquet partition integrity, run SQLite vacuum and optimization routines.
  - `REQ-ST-04`: Provide one-click "Reset Paper Trading Environment" to clear virtual balances, positions, and orders while preserving historical market data.

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Performance Targets
- **NFR-PERF-01 (Candle Processing Latency)**: Ingestion, validation, technical indicator calculation, and dispatch of closed 1-minute candle events must complete in $< 500$ ms.
- **NFR-PERF-02 (WebSocket Latency)**: End-to-end latency from backend event generation to frontend client receipt must not exceed $100$ ms under normal network conditions.
- **NFR-PERF-03 (UI Render Frame Budget)**: The frontend user interface must maintain steady 60 frames per second ($< 16.6$ ms per frame render budget; maximum UI state dispatch cycle $< 100$ ms) during active real-time data streaming.
- **NFR-PERF-04 (Simulation Velocity)**: A 1000-path, 48-horizon forward bootstrap simulation must complete and stream percentiles in $< 2500$ ms on standard multi-core hardware.
- **NFR-PERF-05 (Memory Footprint)**: Backend memory footprint must remain $< 1.5$ GB under sustained operations by offloading cold market data to Parquet and employing ring buffers in memory.

### 5.2 Security Constraints
- **NFR-SEC-01 (No Secrets Required)**: System must operate fully without requiring, storing, or asking for exchange API keys, private keys, or credentials.
- **NFR-SEC-02 (Local Isolation)**: By default, the backend binds strictly to `127.0.0.1` (localhost) with Cross-Origin Resource Sharing (CORS) restricted to the authorized local frontend port (`http://localhost:3000`).
- **NFR-SEC-03 (Input Sanitization)**: All REST endpoints and WebSocket incoming frames must be validated using strict Pydantic schemas on the backend and Zod schemas on the frontend.
- **NFR-SEC-04 (Audit Trail Immutability)**: All paper order logs, risk events, and brain decisions must be append-only in SQLite; modifications of historical audit records are strictly prohibited by schema constraints and application logic.

### 5.3 Data Integrity & Reliability
- **NFR-DAT-01 (ACID Transactions)**: SQLite must operate with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and synchronous normal mode (`PRAGMA synchronous = NORMAL`) to prevent corruption during unexpected shutdowns.
- **NFR-DAT-02 (Idempotency)**: Order execution requests must use unique deterministic `order_id` / `client_order_id` values to prevent duplicate executions.
- **NFR-DAT-03 (Parquet Partitioning)**: Historical market data must be stored in immutable monthly Parquet files partitioned by symbol and timeframe, accompanied by file-level row group metadata and checksum validation.
- **NFR-DAT-04 (Graceful Degradation)**: If public WebSocket feeds disconnect, the system must trigger exponential backoff reconnection while transitioning the Central Brain into a defensive `OBSERVING` state with new orders locked.

---

## 6. Acceptance Criteria for Version 1.0 Release

1. **System Health & Connectivity**:
   - Backend boots cleanly with zero configuration errors, automatically mounts SQLite tables, and establishes Binance public WebSocket stream for at least 3 symbols.
   - Frontend starts cleanly with Next.js App Router, connecting to all backend WebSocket channels without console errors.

2. **Agent & Brain Coordination**:
   - All 10 agents execute cycles reliably without unhandled exceptions.
   - Central Brain state transitions correctly reflect real market changes, transitioning from `OBSERVING` through `ANALYZING` to `SIGNAL_DETECTED`.

3. **Simulation Verification**:
   - Time Machine executes 1000-path forward simulations for generated candidate signals, emitting percentiles ($p5$ to $p95$) and stop/target hit probabilities.
   - Simulations yield identical numerical results when given identical seed and model version parameters.

4. **Risk Enforcement Verification**:
   - Orders violating any of the 5 risk rules (daily loss, drawdown limit, max positions, risk per trade, min R:R ratio) are 100% rejected with documented risk events.
   - Kill switch activation immediately stops order generation and pauses active strategy evaluation.

5. **Paper Trading Realism**:
   - Fills reflect simulated slippage, taker fees (0.04%), and realistic fill delays (50–250ms).
   - Equity accounting updates balance, margin, and PnL with mathematical precision (verified by automated accounting tests).

6. **Documentation & Quality**:
   - Complete technical documentation suite (Architecture, Specifications, ADRs, Testing Strategy) is in place and verified against codebase realities.
   - Unit test suite passes with $\ge 80\%$ overall coverage and $100\%$ coverage on risk and monetary accounting modules.
