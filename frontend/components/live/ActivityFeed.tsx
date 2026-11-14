"use client";

import React, { useState } from "react";
import { type FeedEvent, SHORT } from "./types";

const STYLE: Record<FeedEvent["kind"], { badge: string; label: string }> = {
  BUY: { badge: "bg-bull/20 text-bull", label: "BOUGHT" },
  SELL: { badge: "bg-bear/20 text-bear", label: "SOLD" },
  ALERT: { badge: "bg-gold/20 text-gold", label: "HEADS UP" },
  WAIT: { badge: "bg-white/10 text-slate-300", label: "WAITING" },
};

/** Newest-first story of everything the agent did, in plain English. */
export default function ActivityFeed({ events }: { events: FeedEvent[] }) {
  const [all, setAll] = useState(false);
  const shown = all ? events : events.slice(0, 8);
  return (
    <div className="surface p-5 sm:p-6">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold"><span className="curve-underline">Recent activity</span></h3>
        <span className="text-xs text-slate-500">newest first</span>
      </div>
      {shown.length === 0 && <p className="text-sm text-slate-400">No activity yet.</p>}
      <ul className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
        {shown.map((e) => (
          <li key={e.id} className={`flex flex-col gap-2 rounded-xl p-3 sm:flex-row sm:gap-3 ${e.live ? "bg-gold/[0.06] ring-1 ring-gold/30" : "hover:bg-white/[0.03]"}`}>
            <span className={`h-fit w-fit shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wide ${STYLE[e.kind].badge}`}>{STYLE[e.kind].label}</span>
            <div className="min-w-0 text-sm">
              <div className="font-medium text-slate-100">{e.title} <span className="text-slate-500">· {SHORT(e.symbol)}</span></div>
              <div className="text-slate-300">{e.detail}</div>
              <div className="text-xs text-slate-500">{e.when}</div>
            </div>
          </li>
        ))}
      </ul>
      {events.length > 8 && (
        <button onClick={() => setAll(!all)} className="mt-3 text-sm text-iris-400 hover:text-iris-300">
          {all ? "Show fewer" : `Show all ${events.length}`}
        </button>
      )}
    </div>
  );
}
