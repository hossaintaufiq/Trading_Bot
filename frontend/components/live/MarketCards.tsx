"use client";

import React from "react";
import { type Agent, NAMES, SHORT, SYMBOLS, type Symbol, usd } from "./types";

interface Props {
  selected: Symbol; onSelect: (s: Symbol) => void;
  prices: Partial<Record<Symbol, number>>; agents: Partial<Record<Symbol, Agent>>;
}

/** Big, clickable market switcher showing live price and what the agent is doing in each market. */
export default function MarketCards({ selected, onSelect, prices, agents }: Props) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {SYMBOLS.map((s) => {
        const a = agents[s];
        const holding = a?.position === "LONG";
        return (
          <button key={s} onClick={() => onSelect(s)}
            className={`rounded-lg border p-4 text-left transition ${s === selected ? "border-blue-500 bg-blue-950/30" : "border-slate-800 bg-slate-900/40 hover:border-slate-600"}`}>
            <div className="flex items-center justify-between">
              <span className="font-semibold">{NAMES[s]} <span className="text-slate-500">{SHORT(s)}</span></span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${holding ? "bg-emerald-600 text-white" : "bg-slate-700 text-slate-300"}`}>
                {a ? (holding ? "Holding" : "In cash") : "…"}
              </span>
            </div>
            <div className="mt-2 font-mono text-xl">{prices[s] ? usd(prices[s]!) : "—"}</div>
          </button>
        );
      })}
    </div>
  );
}
