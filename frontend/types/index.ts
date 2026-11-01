/**
 * NEPTUNE Frontend — Shared TypeScript Types
 * These types must remain in sync with backend Pydantic models.
 * Last sync: 2026-11-01
 */

// ============================================================
// Market Data Types
// ============================================================

export type Timeframe = "15m" | "1h" | "4h";

export type MarketRegime = "TRENDING_UP" | "TRENDING_DOWN" | "RANGING" | "VOLATILE" | "UNKNOWN";

export interface Candle {
  timestamp: string;        // ISO 8601 UTC
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  is_closed: boolean;
}

export interface MarketSnapshot {
  symbol: string;
  timeframe: Timeframe;
  last_price: number;
  price_change_pct_24h: number;
  volume_24h: number;
  high_24h: number;
  low_24h: number;
  regime: MarketRegime;
  spread_bps: number;
  last_updated: string;     // ISO 8601 UTC
}

// ============================================================
// Agent Types
// ============================================================

export type AgentState =
  | "IDLE"
  | "RUNNING"
  | "SUCCESS"
  | "ERROR"
  | "DISABLED";

export interface AgentStatus {
  agent_id: string;
  agent_name: string;
  state: AgentState;
  last_run_at: string | null;
  last_duration_ms: number | null;
  current_task: string | null;
  last_result_summary: string | null;
  error_message: string | null;
  total_executions: number;
  success_rate: number;
}

// ============================================================
// Signal Types
// ============================================================

export type SignalDirection = "LONG" | "SHORT";

export type SignalStatus =
  | "GENERATED"
  | "VALIDATING"
  | "VALIDATED"
  | "REJECTED"
  | "SIMULATING"
  | "RISK_REVIEW"
  | "APPROVED"
  | "EXPIRED";

export interface Signal {
  signal_id: string;
  strategy_id: string;
  symbol: string;
  timeframe: Timeframe;
  direction: SignalDirection;
  status: SignalStatus;
  entry_price: number;
  stop_price: number;
  target_price: number;
  reward_risk_ratio: number;
  signal_strength: number;   // 0.0 – 1.0
  generated_at: string;
  expires_at: string;
  explanation: string;
}

// ============================================================
// Brain Decision Types
// ============================================================

export type BrainState =
  | "OBSERVING"
  | "ANALYZING"
  | "SIGNAL_DETECTED"
  | "VALIDATING"
  | "SIMULATING"
  | "RISK_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "PAPER_ORDER_CREATED"
  | "POSITION_MONITORING"
  | "CLOSED"
  | "AUDITED";

export interface BrainDecision {
  decision_id: string;
  signal_id: string | null;
  from_state: BrainState;
  to_state: BrainState;
  reason: string;
  agent_outputs: Record<string, unknown>;
  timestamp: string;
}

// ============================================================
// Simulation Types
// ============================================================

export interface SimulationResult {
  simulation_id: string;
  signal_id: string;
  symbol: string;
  timeframe: Timeframe;
  created_at: string;
  seed: number;
  model_version: string;
  method: string;
  horizon_candles: number;
  num_paths: number;
  entry_price: number;
  percentiles: {
    p5: number;
    p10: number;
    p25: number;
    p50: number;
    p75: number;
    p90: number;
    p95: number;
  };
  stop_hit_probability: number;
  target_hit_probability: number;
  max_adverse_excursion_median: number;
}

// ============================================================
// Paper Trading Types
// ============================================================

export type OrderType = "MARKET" | "LIMIT" | "STOP" | "TAKE_PROFIT";
export type OrderStatus = "PENDING" | "OPEN" | "FILLED" | "PARTIALLY_FILLED" | "CANCELLED" | "REJECTED";
export type PositionStatus = "OPEN" | "CLOSED";

export interface PaperOrder {
  order_id: string;
  signal_id: string;
  symbol: string;
  direction: SignalDirection;
  order_type: OrderType;
  status: OrderStatus;
  quantity: number;
  limit_price: number | null;
  stop_price: number | null;
  target_price: number | null;
  created_at: string;
  filled_at: string | null;
  fill_price: number | null;
  fee_paid: number | null;
  slippage_pct: number | null;
}

export interface PaperPosition {
  position_id: string;
  signal_id: string;
  symbol: string;
  direction: SignalDirection;
  status: PositionStatus;
  entry_price: number;
  quantity: number;
  stop_price: number;
  target_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number | null;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
}

// ============================================================
// Portfolio Types
// ============================================================

export interface PortfolioSnapshot {
  equity: number;
  available_balance: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  realized_pnl_total: number;
  open_positions_count: number;
  drawdown_current_pct: number;
  drawdown_max_pct: number;
  daily_loss_pct: number;
  kill_switch_active: boolean;
  snapshot_at: string;
}

// ============================================================
// System Types
// ============================================================

export interface SystemHealth {
  status: "healthy" | "degraded" | "critical";
  version: string;
  paper_trading_only: boolean;
  real_money_trading: boolean;
  uptime_seconds: number;
  market_data_connected: boolean;
  database_connected: boolean;
  last_candle_received_at: string | null;
}

// ============================================================
// WebSocket Event Types
// ============================================================

export interface WsEvent<T = unknown> {
  event_id: string;
  event_type: string;
  timestamp: string;       // ISO 8601 UTC
  version: string;
  payload: T;
}

