"use client";

import React, { useState } from "react";
import { type FeedEvent, SHORT } from "./types";

const STYLE: Record<FeedEvent["kind"], { badge: string; label: string }> = {
  BUY: { badge: "bg-emerald-600 text-white", label: "BOUGHT" },
  SELL: { badge: "bg-red-600 text-white", label: "SOLD" },
  ALERT: { badge: "bg-amber-500 text-black", label: "HEADS UP" },
  WAIT: { badge: "bg-slate-600 text-white", label: "WAITING" },
};

/** Newest-first story of everything the agent did, in plain English. */
export default function ActivityFeed({ events }: { events: FeedEvent[] }) {
  const [all, setAll] = useState(false);
  const shown = all ? events : events.slice(0, 8);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">What the agent has been doing</h3>
        <span className="text-xs text-slate-500">newest first</span>
      </div>
      {shown.length === 0 && <p className="text-sm text-slate-400">No activity yet.</p>}
      <ul className="space-y-3">
        {shown.map((e) => (
          <li key={e.id} className={`flex gap-3 rounded-md p-2 ${e.live ? "bg-amber-950/30 ring-1 ring-amber-600/40" : ""}`}>
            <span className={`h-fit shrink-0 rounded px-2 py-0.5 text-xs font-bold ${STYLE[e.kind].badge}`}>{STYLE[e.kind].label}</span>
            <div className="text-sm">
              <div className="font-medium text-slate-100">{e.title} <span className="text-slate-500">· {SHORT(e.symbol)}</span></div>
              <div className="text-slate-300">{e.detail}</div>
              <div className="text-xs text-slate-500">{e.when}</div>
            </div>
          </li>
        ))}
      </ul>
      {events.length > 8 && (
        <button onClick={() => setAll(!all)} className="mt-3 text-sm text-blue-400 hover:underline">
          {all ? "Show fewer" : `Show all ${events.length}`}
        </button>
      )}
    </div>
  );
}
