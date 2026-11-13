export const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"] as const;
export type Symbol = (typeof SYMBOLS)[number];

export const NAMES: Record<Symbol, string> = { BTCUSDT: "Bitcoin", ETHUSDT: "Ethereum", BNBUSDT: "BNB" };
export const SHORT = (s: string) => s.replace("USDT", "");

export interface Marker {
  time: string; side: "BUY" | "SELL"; price: number; pct?: number; open?: boolean;
}
export interface Agent {
  symbol: Symbol; as_of: string; position: "LONG" | "FLAT"; last_close: number;
  buy_above: number; sell_below: number; markers: Marker[];
}
export interface Period {
  net_return_pct: number; max_drawdown_pct: number; trades: number; wins: number;
  fees: number; buy_hold_pct: number; equity_curve: { date: string; equity: number }[];
}
export interface DailyTrend { periods: Record<string, Period>; }

export interface FeedEvent {
  id: string; when: string; symbol: Symbol; kind: "BUY" | "SELL" | "ALERT" | "WAIT";
  title: string; detail: string; live?: boolean;
}

export const usd = (n: number) => "$" + n.toLocaleString(undefined, { maximumFractionDigits: n < 10 ? 4 : 2 });
export const pct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
export const niceDate = (iso: string) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
