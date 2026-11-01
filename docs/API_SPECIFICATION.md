# NEPTUNE API & Transport Specification (REST & WebSockets)

## Document Information
- **Project**: NEPTUNE — Autonomous Market Intelligence & Paper Trading Platform
- **Document Version**: 1.0.0
- **Status**: Approved / API Contract
- **Author**: Neptune Lead API Architect
- **Date**: 2026-11-01

---

## 1. Overview & Transport Protocol Standards

The NEPTUNE interface layer provides a dual transport architecture:
1. **REST API (`/api/v1/*`)**: Used for state queries, historical lookups, strategy configurations, backtest triggers, and system commands. Follows OpenAPI 3.1 standards with JSON payloads.
2. **WebSocket Hub (`/ws/*`)**: Used for sub-100ms real-time event streaming across 7 dedicated domain channels.

All timestamps are **strictly 64-bit integer Unix epoch milliseconds in UTC**.

---

## 2. Complete REST API Specification (`/api/v1`)

---

### 2.1 System Health (`/health`)
- **Method**: `GET`
- **Path**: `/api/v1/health`
- **Description**: Returns overall system operational status, subsystem health, uptime, and database connectivity.
- **Request Body**: None
- **Response Schema (`200 OK`)**:
```json
{
  "status": "HEALTHY",
  "version": "1.0.0",
  "uptime_seconds": 14520,
  "timestamp": 1730472000000,
  "subsystems": {
    "binance_feed": "CONNECTED",
    "sqlite_db": "HEALTHY",
    "central_brain": "OBSERVING",
    "risk_manager": "ARMED",
    "agent_swarm": "10/10_HEALTHY"
  }
}
```

---

### 2.2 Active Markets (`/markets`)
- **Method**: `GET`
- **Path**: `/api/v1/markets`
- **Description**: Returns list of all configured cryptocurrency trading pairs with 24h summary statistics.
- **Request Body**: None
- **Response Schema (`200 OK`)**:
```json
{
  "markets": [
    {
      "symbol": "BTCUSDT",
      "base_asset": "BTC",
      "quote_asset": "USDT",
      "current_price": 65420.50,
      "change_24h_pct": 2.45,
      "high_24h": 66100.00,
      "low_24h": 63850.00,
      "volume_24h_usdt": 184500200.0,
      "status": "ACTIVE"
    }
  ]
}
```

---

### 2.3 Market Candles (`/market/candles`)
- **Method**: `GET`
- **Path**: `/api/v1/market/candles`
- **Description**: Retrieves OHLCV candle series for a specified symbol and timeframe from the hot ring buffer and historical storage.
- **Query Parameters**:
  - `symbol` (string, required): e.g., `BTCUSDT`
  - `timeframe` (string, default `15m`): e.g., `1m`, `5m`, `15m`, `1h`, `4h`, `1d`
  - `limit` (integer, default `100`, max `1000`): Number of candles to return
  - `start_time` (integer, optional): Epoch milliseconds
  - `end_time` (integer, optional): Epoch milliseconds
- **Response Schema (`200 OK`)**:
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "candles": [
    {
      "timestamp": 1730471100000,
      "open": 65200.0,
      "high": 65450.0,
      "low": 65150.0,
      "close": 65420.5,
      "volume": 142.85
    }
  ]
}
```

---

### 2.4 Market Snapshot (`/market/snapshot`)
- **Method**: `GET`
- **Path**: `/api/v1/market/snapshot`
- **Description**: Returns complete multi-market snapshot including current orderbook depth, active regimes, and rolling volatility.
- **Request Body**: None
- **Response Schema (`200 OK`)**:
```json
{
  "timestamp": 1730472000000,
  "snapshots": {
    "BTCUSDT": {
      "mark_price": 65420.50,
      "regime": "TRENDING_BULL",
      "atr_14": 420.50,
      "orderbook": {
        "bids": [[65420.0, 1.45], [65419.5, 3.20]],
        "asks": [[65421.0, 0.85], [65421.5, 2.10]]
      }
    }
  }
}
```

---

### 2.5 Specialist Agents Registry (`/agents`)
- **Method**: `GET`
- **Path**: `/api/v1/agents`
- **Description**: Returns status, invocation count, error count, and configuration for all 10 specialist agents.
- **Request Body**: None
- **Response Schema (`200 OK`)**:
```json
{
  "agents": [
    {
      "agent_id": "trend_analyst",
      "name": "TrendAnalyst",
      "version": "1.0.0",
      "status": "HEALTHY",
      "total_invocations": 1420,
      "total_errors": 0,
      "avg_latency_ms": 18.4,
      "last_invoked_at": 1730471995000
    }
  ]
}
```

---

### 2.6 Agent Execution Results (`/agents/{id}/results`)
- **Method**: `GET`
- **Path**: `/api/v1/agents/{id}/results`
- **Description**: Retrieves the most recent execution input and output payloads for a specific agent.
- **Path Parameters**: `id` (string, e.g., `momentum_analyst`)
- **Response Schema (`200 OK`)**:
```json
{
  "agent_id": "momentum_analyst",
  "timestamp": 1730471995000,
  "execution_time_ms": 14.2,
  "input_payload": { "symbol": "BTCUSDT", "timeframe": "15m" },
  "output_payload": {
    "rsi": 62.4,
    "macd_histogram": 14.8,
    "rsi_divergence": "NONE",
    "momentum_score": 0.65
  }
}
```

---

### 2.7 Brain Decisions Audit (`/brain/decisions`)
- **Method**: `GET`
- **Path**: `/api/v1/brain/decisions`
- **Description**: Returns chronological log of Central Brain finite state transitions.
- **Query Parameters**: `limit` (int, default 50)
- **Response Schema (`200 OK`)**:
```json
{
  "decisions": [
    {
      "decision_id": "dec_88192a",
      "from_state": "ANALYZING",
      "to_state": "SIGNAL_DETECTED",
      "trigger_event": "CONFLUENCE_THRESHOLD_MET",
      "symbol": "BTCUSDT",
      "timeframe": "15m",
      "rationale": "Strong bull trend confirmed by ADX (32.4) and volume surge (2.8x MA).",
      "created_at": 1730471996000
    }
  ]
}
```

---

### 2.8 Candidate & Validated Signals (`/signals`)
- **Method**: `GET`
- **Path**: `/api/v1/signals`
- **Description**: Retrieves recent candidate and validated trading signals.
- **Query Parameters**: `status` (optional), `limit` (default 50)
- **Response Schema (`200 OK`)**:
```json
{
  "signals": [
    {
      "signal_id": "sig_btc_9901",
      "strategy_id": "trend_follower",
      "symbol": "BTCUSDT",
      "timeframe": "15m",
      "direction": "LONG",
      "entry_price": 65400.0,
      "stop_loss": 64400.0,
      "take_profit": 67400.0,
      "risk_reward_ratio": 2.0,
      "raw_confidence": 0.86,
      "is_validated": true,
      "validation_score": 0.88,
      "status": "VALIDATED",
      "created_at": 1730471997000
    }
  ]
}
```

---

### 2.9 Time Machine Simulations (`/simulations`)
- **Method**: `GET`
- **Path**: `/api/v1/simulations`
- **Description**: Retrieves simulation records and percentile projections for a given signal.
- **Query Parameters**: `signal_id` (string, required)
- **Response Schema (`200 OK`)**:
```json
{
  "simulation_id": "sim_004812",
  "signal_id": "sig_btc_9901",
  "symbol": "BTCUSDT",
  "method": "BLOCK_BOOTSTRAP",
  "horizon_candles": 48,
  "num_paths": 1000,
  "seed": 884729105523,
  "entry_price": 65400.0,
  "percentiles": {
    "p5": 63850.0, "p10": 64200.0, "p25": 64900.0,
    "p50": 65950.0, "p75": 67100.0, "p90": 68050.0, "p95": 68600.0
  },
  "stop_hit_probability": 0.165,
  "target_hit_probability": 0.624,
  "max_adverse_excursion_median": 380.0
}
```

---

### 2.10 Paper Orders (`/paper/orders`)
- **Method**: `GET`, `POST`
- **Path**: `/api/v1/paper/orders`
- **Description**:
  - `GET`: Returns active and past paper orders.
  - `POST`: Manually submits a paper order (requires internal risk token or manual flag).
- **POST Request Body**:
```json
{
  "symbol": "BTCUSDT",
  "order_type": "LIMIT",
  "side": "BUY",
  "requested_price": 65400.0,
  "requested_size": 0.005,
  "stop_loss": 64400.0,
  "take_profit": 67400.0
}
```
- **Response Schema (`201 Created`)**:
```json
{
  "order_id": "ord_paper_9941",
  "status": "PENDING",
  "symbol": "BTCUSDT",
  "requested_price": 65400.0,
  "requested_size": 0.005,
  "created_at": 1730472001000
}
```

---

### 2.11 Open Positions (`/paper/positions`)
- **Method**: `GET`
- **Path**: `/api/v1/paper/positions`
- **Description**: Retrieves current open virtual positions, entry prices, mark prices, and live PnL.
- **Request Body**: None
- **Response Schema (`200 OK`)**:
```json
{
  "positions": [
    {
      "position_id": "pos_btc_01",
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "size": 0.005,
      "entry_price": 65400.0,
      "current_price": 65620.0,
      "stop_loss": 64400.0,
      "take_profit": 67400.0,
      "margin_allocated": 327.0,
      "unrealized_pnl": 1.10,
      "unrealized_pnl_pct": 0.336,
      "opened_at": 1730472005000
    }
  ]
}
```

---

### 2.12 Performance Analytics (`/analytics/performance`)
- **Method**: `GET`
- **Path**: `/api/v1/analytics/performance`
- **Description**: Retrieves comprehensive Sharpe, Sortino, Win Rate, and drawdown analytics.
- **Response Schema (`200 OK`)**:
```json
{
  "virtual_equity": 1045.20,
  "realized_pnl_total": 45.20,
  "total_trades": 24,
  "winning_trades": 16,
  "losing_trades": 8,
  "win_rate": 0.667,
  "profit_factor": 1.85,
  "sharpe_ratio": 1.92,
  "sortino_ratio": 2.45,
  "max_drawdown_pct": 0.024
}
```

---

### 2.13 System Control Endpoints (`/system/pause`, `/resume`, `/kill-switch`)
- **`/system/pause`** (`POST`): Pauses Central Brain state progression; leaves positions active.
- **`/system/resume`** (`POST`): Resumes normal operational state machine progression.
- **`/system/kill-switch`** (`POST`): Immediate emergency halt with dual-mode operational control:
  - **Request Body**:
    ```json
    {
      "mode": "PAUSE_NEW_ORDERS",  // or "LIQUIDATE_ALL_AND_HALT"
      "reason": "Operator manual emergency stop"
    }
    ```
  - **Response Schema (`200 OK`)**:
    ```json
    {
      "action": "KILL_SWITCH",
      "mode": "PAUSE_NEW_ORDERS",
      "status": "ENGAGED",
      "timestamp": "2026-11-01T21:05:00.000Z",
      "open_positions_affected": 2,
      "message": "Kill switch activated in PAUSE_NEW_ORDERS mode: new orders halted; open positions continue bracket monitoring."
    }
    ```

---

## 3. WebSocket Real-Time Channels Specification

All WebSocket channels bind under `ws://localhost:8000/ws/{channel}`.

### 3.1 Uniform Envelope Schema
Every WebSocket frame strictly conforms to this standard JSON envelope:

```typescript
interface WebSocketEnvelope<T> {
  event_id: string;        // UUIDv4 (e.g. "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
  event_type: string;      // Topic-specific event verb
  timestamp: number;       // Epoch milliseconds UTC
  version: "1.0";          // Protocol schema version
  payload: T;              // Strongly-typed event data
}
```

### 3.2 Channel Matrix

| WebSocket URL | Event Types Emitted | Update Frequency / Trigger | Payload Contents |
|---|---|---|---|
| `ws://localhost:8000/ws/market` | `TICK`, `CANDLE_UPDATE`, `CANDLE_CLOSED` | Real-time tick (1s throttled) & Candle close | Symbol, mark price, latest OHLCV candle, volume |
| `ws://localhost:8000/ws/agents` | `AGENT_STARTED`, `AGENT_COMPLETED`, `AGENT_ERROR` | Event-driven on agent execution | Agent ID, latency ms, health status, brief output summary |
| `ws://localhost:8000/ws/brain` | `STATE_TRANSITION`, `HYPOTHESIS_FORMED` | Event-driven on FSM change | From state, to state, trigger reason, confidence score |
| `ws://localhost:8000/ws/signals` | `SIGNAL_CANDIDATE`, `SIGNAL_VALIDATED`, `SIGNAL_EXPIRED` | Event-driven on signal generation | Full signal object (entry, SL, TP, R:R, strategy) |
| `ws://localhost:8000/ws/simulation` | `SIMULATION_PROGRESS`, `SIMULATION_COMPLETE` | Event-driven during Time Machine run | Signal ID, current path progress, terminal percentiles |
| `ws://localhost:8000/ws/execution` | `ORDER_CREATED`, `ORDER_FILLED`, `ORDER_CANCELLED`, `POSITION_CLOSED` | Event-driven on paper order state change | Order ID, fill price, slippage USDT, fee USDT, PnL |
| `ws://localhost:8000/ws/system` | `SYSTEM_LOG`, `RESOURCE_METRIC`, `CIRCUIT_BREAKER_TRIGGERED` | 1s interval (metrics) & Real-time (logs) | CPU %, RAM MB, SQLite size, error stack traces |

---

## 4. Reconnection & Keep-Alive Protocol

To guarantee reliable operation over unstable local or network sockets:

1. **Keep-Alive Heartbeat**:
   - The frontend sends a text frame `{"type": "PING", "timestamp": <epoch_ms>}` every **15 seconds**.
   - The backend immediately responds with `{"type": "PONG", "timestamp": <epoch_ms>}`.
   - If the client receives no response for 30 seconds, it closes the socket and enters reconnection mode.
2. **Reconnection with Exponential Backoff & Jitter**:
   - Attempt 1: 500 ms
   - Attempt 2: 1,000 ms
   - Attempt 3: 2,000 ms
   - Attempt 4: 4,000 ms
   - Attempt $N$: $\min(500 \cdot 2^{N-1} + \text{jitter}_{[-200, +200]}, 15000)$ ms
3. **State Resynchronization Handshake**:
   - Upon reconnecting, the client issues a parallel REST fetch to `/api/v1/market/snapshot`, `/api/v1/paper/positions`, and `/api/v1/brain/decisions` to eliminate any missed state deltas.
