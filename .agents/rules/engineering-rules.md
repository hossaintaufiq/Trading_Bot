# NEPTUNE Persistent Engineering Rules
# File: .agents/rules/engineering-rules.md
# These rules are loaded by every AI agent working on this codebase.

rules:
  safety:
    - id: S-01
      rule: "Never implement real-money exchange execution. Paper trading only in v1."
      enforcement: HARD_BLOCK
    - id: S-02
      rule: "Never expose API keys, secrets, or credentials in code, logs, or responses."
      enforcement: HARD_BLOCK
    - id: S-03
      rule: "Never commit .env files. Use .env.example only."
      enforcement: HARD_BLOCK
    - id: S-04
      rule: "Never bypass the Risk Manager. All paper orders require Risk Manager authorization."
      enforcement: HARD_BLOCK
    - id: S-05
      rule: "Never use future data in simulations or backtests. Strict look-ahead bias prevention."
      enforcement: HARD_BLOCK
    - id: S-06
      rule: "Never fabricate market data, agent decisions, or performance metrics."
      enforcement: HARD_BLOCK
    - id: S-07
      rule: "Never claim profitability without validated, reproducible evidence."
      enforcement: HARD_BLOCK
    - id: S-08
      rule: "Never add PostgreSQL in v1. SQLite only."
      enforcement: HARD_BLOCK
    - id: S-09
      rule: "Never introduce Redis, Kafka, or Kubernetes in v1."
      enforcement: HARD_BLOCK
    - id: S-10
      rule: "Never implement microservices in v1. Modular monolith only."
      enforcement: HARD_BLOCK

  architecture:
    - id: A-01
      rule: "All monetary calculations use Python Decimal or integer cents, never float."
    - id: A-02
      rule: "All timestamps stored and processed in UTC. No local time in database."
    - id: A-03
      rule: "Business logic must use repository interfaces, never direct SQLite or filesystem."
    - id: A-04
      rule: "Frontend TypeScript types must match backend Pydantic models."
    - id: A-05
      rule: "All architectural decisions recorded in docs/ARCHITECTURE_DECISIONS.md."
    - id: A-06
      rule: "Agents communicate through the Central Brain only. No direct agent-to-agent calls."
    - id: A-07
      rule: "Every agent must implement a structured input and output contract."
    - id: A-08
      rule: "Candle-close strategies must only consume fully closed candles."
    - id: A-09
      rule: "Paper fills must record execution assumptions: price, fee, slippage, timestamp."
    - id: A-10
      rule: "Every paper trade must be traceable: signal → validation → simulation → risk → fill → close → audit."

  engineering:
    - id: E-01
      rule: "Prefer small, single-responsibility modules. Target < 300 lines per module."
    - id: E-02
      rule: "Critical calculations must have unit tests before implementation."
    - id: E-03
      rule: "Use typed Python models (Pydantic) and TypeScript interfaces. No untyped any."
    - id: E-04
      rule: "Log errors with: agent ID, signal ID, timestamp, input values."
    - id: E-05
      rule: "Follow clean architecture: separate API, service, domain, persistence layers."
    - id: E-06
      rule: "Do not silently change the approved architecture. Document deviations."
    - id: E-07
      rule: "Pin all dependency versions in requirements files."

do_not_implement:
  - Real exchange API execution
  - Real fund management
  - PostgreSQL in v1
  - Redis, Kafka, Kubernetes in v1
  - Microservices in v1
  - Real API credentials in any file

approved_storage:
  transactional: SQLite
  historical_data: Parquet
  simulations: Parquet
  cache: in-memory only

approved_symbols:
  - BTCUSDT
  - ETHUSDT
  - BNBUSDT

approved_timeframes:
  - 15m
  - 1h
  - 4h

