/**
 * NEPTUNE Zustand Store — Agent Status
 */
import { create } from "zustand";
import { AgentStatus } from "@/types";

interface AgentState {
  agents: Record<string, AgentStatus>;
  lastUpdated: string | null;

  updateAgent: (status: AgentStatus) => void;
  setAllAgents: (agents: AgentStatus[]) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: {},
  lastUpdated: null,

  updateAgent: (status) =>
    set((state) => ({
      agents: { ...state.agents, [status.agent_id]: status },
      lastUpdated: new Date().toISOString(),
    })),

  setAllAgents: (agents) => {
    const map = agents.reduce(
      (acc, a) => ({ ...acc, [a.agent_id]: a }),
      {} as Record<string, AgentStatus>
    );
    set({ agents: map, lastUpdated: new Date().toISOString() });
  },
}));
