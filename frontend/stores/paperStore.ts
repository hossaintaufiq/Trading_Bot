/**
 * NEPTUNE Zustand Store — Paper Trading & Portfolio
 */
import { create } from "zustand";
import { PaperOrder, PaperPosition, PortfolioSnapshot } from "@/types";

interface PaperState {
  portfolio: PortfolioSnapshot | null;
  positions: PaperPosition[];
  orders: PaperOrder[];
  recentFills: PaperOrder[];

  setPortfolio: (portfolio: PortfolioSnapshot) => void;
  setPositions: (positions: PaperPosition[]) => void;
  updatePosition: (position: PaperPosition) => void;
  addOrder: (order: PaperOrder) => void;
  updateOrder: (order: PaperOrder) => void;
}

export const usePaperStore = create<PaperState>((set, get) => ({
  portfolio: null,
  positions: [],
  orders: [],
  recentFills: [],

  setPortfolio: (portfolio) => set({ portfolio }),

  setPositions: (positions) => set({ positions }),

  updatePosition: (position) =>
    set((state) => ({
      positions: state.positions.map((p) =>
        p.position_id === position.position_id ? position : p
      ),
    })),

  addOrder: (order) =>
    set((state) => ({
      orders: [order, ...state.orders].slice(0, 200),
    })),

  updateOrder: (order) =>
    set((state) => ({
      orders: state.orders.map((o) =>
        o.order_id === order.order_id ? order : o
      ),
      recentFills:
        order.status === "FILLED"
          ? [order, ...state.recentFills].slice(0, 50)
          : state.recentFills,
    })),
}));
