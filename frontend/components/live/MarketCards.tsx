"use client";

import React from "react";
import { type Agent, NAMES, SHORT, SYMBOLS, type Symbol, usd } from "./types";

interface Props {
  selected: Symbol; onSelect: (s: Symbol) => void;
  prices: Partial<Record<Symbol, number>>; agents: Partial<Record<Symbol, Agent>>;
}

/** Clickable market switcher showing live price and what the agent is doing in each market. */
export default function MarketCards({ selected, onSelect, prices, agents }: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {SYMBOLS.map((s) => {
        const a = agents[s];
        const holding = a?.position === "LONG";
        const active = s === selected;
        return (
          <button key={s} onClick={() => onSelect(s)} aria-pressed={active}
            className={`group rounded-2xl border p-4 text-left transition duration-300 sm:p-5 ${active
              ? "border-iris-500/40 bg-gradient-to-b from-iris-500/15 to-transparent shadow-glow"
              : "border-white/[0.06] bg-white/[0.025] hover:-translate-y-0.5 hover:border-white/15"}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-base font-semibold">{NAMES[s]} <span className="text-slate-500">{SHORT(s)}</span></span>
              <span className={`pill ${holding ? "bg-bull/15 text-bull" : "bg-white/5 text-slate-400"}`}>
                {a ? (holding ? "Holding" : "In cash") : "…"}
              </span>
            </div>
            <div className="mono-num mt-3 text-xl sm:text-2xl">{prices[s] ? usd(prices[s]!) : "—"}</div>
          </button>
        );
      })}
    </div>
  );
}
