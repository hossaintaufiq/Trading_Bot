"use client";

import React from "react";
import { type Agent, NAMES, SHORT, niceDate, pct, usd } from "./types";

/** Plain-English explanation of what the agent is doing right now for the selected market. */
export default function AgentPanel({ agent, livePrice }: { agent: Agent | null; livePrice: number | null }) {
  if (!agent) return <div className="rounded-lg border border-slate-800 p-4 text-slate-400">Loading the agent…</div>;
  const name = NAMES[agent.symbol];
  const price = livePrice ?? agent.last_close;
  const holding = agent.position === "LONG";
  const open = agent.markers.find((m) => m.open);
  const gain = open ? (price / open.price - 1) * 100 : null;
  const toBuy = (agent.buy_above / price - 1) * 100;
  const toSell = (agent.sell_below / price - 1) * 100;

  return (
    <div className={`rounded-lg border p-5 ${holding ? "border-emerald-700 bg-emerald-950/30" : "border-slate-700 bg-slate-900/60"}`}>
      <div className="flex items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${holding ? "bg-emerald-600 text-white" : "bg-slate-700 text-slate-200"}`}>
          {holding ? "HOLDING" : "WAITING (in cash)"}
        </span>
        <h2 className="text-lg font-semibold">{name} ({SHORT(agent.symbol)})</h2>
      </div>

      {holding ? (
        <p className="mt-3 text-slate-200">
          The agent <b>bought {name}</b>{open ? <> on <b>{niceDate(open.time)}</b> at <b>{usd(open.price)}</b></> : null} because the price is in an uptrend.
          {gain !== null && <> Right now that position is <b className={gain >= 0 ? "text-emerald-400" : "text-red-400"}>{pct(gain)}</b> (before fees).</>}
          {" "}It will <b>sell</b> if a day closes below <b className="text-red-400">{usd(agent.sell_below)}</b>
          {" "}({pct(toSell)} from now), which would mean the uptrend is over.
        </p>
      ) : (
        <p className="mt-3 text-slate-200">
          The agent is <b>keeping its money in cash</b> on {name} because there is no clear uptrend.
          It will <b>buy</b> if a day closes above <b className="text-emerald-400">{usd(agent.buy_above)}</b>
          {" "}({pct(toBuy)} from the current price of {usd(price)}).
        </p>
      )}
      <p className="mt-3 text-xs text-slate-400">
        The agent only decides when a daily candle <b>closes</b> (midnight UTC) and trades at the next open, so it can wait days or weeks without doing anything. That is normal.
        Practice money only (paper trading). Latest closed day: {niceDate(agent.as_of)}.
      </p>
    </div>
  );
}
