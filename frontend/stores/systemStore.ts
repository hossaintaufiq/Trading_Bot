/**
 * NEPTUNE Zustand Store — System State
 */
import { create } from "zustand";
import { SystemHealth } from "@/types";

interface SystemState {
  health: SystemHealth | null;
  killSwitchActive: boolean;
  wsConnections: Record<string, "connecting" | "open" | "closed" | "error">;

  setHealth: (health: SystemHealth) => void;
  setKillSwitch: (active: boolean) => void;
  setWsState: (
    channel: string,
    state: "connecting" | "open" | "closed" | "error"
  ) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  health: null,
  killSwitchActive: false,
  wsConnections: {},

  setHealth: (health) =>
    set({ health, killSwitchActive: health.status === "critical" }),

  setKillSwitch: (active) => set({ killSwitchActive: active }),

  setWsState: (channel, wsState) =>
    set((state) => ({
      wsConnections: { ...state.wsConnections, [channel]: wsState },
    })),
}));

