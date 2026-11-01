/**
 * NEPTUNE Zustand Store — Market Data
 */
import { create } from "zustand";
import { Candle, MarketSnapshot, Timeframe } from "@/types";

interface MarketState {
  snapshots: Record<string, MarketSnapshot>;
  candles: Record<string, Record<Timeframe, Candle[]>>;
  activeSymbol: string;
  activeTimeframe: Timeframe;
  isConnected: boolean;
  lastUpdated: string | null;

  // Actions
  setActiveSymbol: (symbol: string) => void;
  setActiveTimeframe: (timeframe: Timeframe) => void;
  updateSnapshot: (snapshot: MarketSnapshot) => void;
  appendCandle: (symbol: string, timeframe: Timeframe, candle: Candle) => void;
  setConnected: (connected: boolean) => void;
}

export const useMarketStore = create<MarketState>((set, get) => ({
  snapshots: {},
  candles: {},
  activeSymbol: "BTCUSDT",
  activeTimeframe: "15m",
  isConnected: false,
  lastUpdated: null,

  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
  setActiveTimeframe: (timeframe) => set({ activeTimeframe: timeframe }),

  updateSnapshot: (snapshot) =>
    set((state) => ({
      snapshots: { ...state.snapshots, [snapshot.symbol]: snapshot },
      lastUpdated: new Date().toISOString(),
    })),

  appendCandle: (symbol, timeframe, candle) =>
    set((state) => {
      const symbolCandles = state.candles[symbol] ?? {};
      const existing = symbolCandles[timeframe] ?? [];
      const updated = [...existing, candle].slice(-500); // keep last 500
      return {
        candles: {
          ...state.candles,
          [symbol]: { ...symbolCandles, [timeframe]: updated },
        },
      };
    }),

  setConnected: (connected) => set({ isConnected: connected }),
}));
