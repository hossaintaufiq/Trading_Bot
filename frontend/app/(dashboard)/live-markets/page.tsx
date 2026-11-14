"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ActivityFeed from "@/components/live/ActivityFeed";
import AgentPanel from "@/components/live/AgentPanel";
import CandleChart, { INTERVALS, type Interval } from "@/components/live/CandleChart";
import EquityPanel from "@/components/live/EquityPanel";
import MarketCards from "@/components/live/MarketCards";
import PaperAccount from "@/components/live/PaperAccount";
import {
  type Agent, type FeedEvent, NAMES, SYMBOLS, type Symbol, niceDate, pct, usd,
} from "@/components/live/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Turn the agent's recorded trades into plain-English history entries. */
function historyEvents(agents: Partial<Record<Symbol, Agent>>): FeedEvent[] {
  const out: FeedEvent[] = [];
  for (const s of SYMBOLS) {
    for (const m of agents[s]?.markers ?? []) {
      const name = NAMES[s];
      if (m.side === "BUY") {
        out.push({
          id: `${s}-${m.time}-B`, when: niceDate(m.time), symbol: s, kind: "BUY",
          title: `Bought ${name} at ${usd(m.price)}`,
          detail: "The price closed above its highest level of the last 20 days. The agent reads that as the start of an uptrend.",
        });
      } else {
        const win = (m.pct ?? 0) >= 0;
        out.push({
          id: `${s}-${m.time}-S`, when: niceDate(m.time), symbol: s, kind: "SELL",
          title: `Sold ${name} at ${usd(m.price)} — ${win ? "made" : "lost"} ${pct(Math.abs(m.pct ?? 0)).replace("+", "")} after fees`,
          detail: "The price closed below its lowest level of the last 10 days. The agent reads that as the uptrend ending, so it sold to protect the money.",
        });
      }
    }
  }
  const key = (e: FeedEvent) => e.id.split("-")[1];
  return out.sort((a, b) => (key(a) < key(b) ? 1 : -1));
}

export default function LiveMarketsPage() {
  const [symbol, setSymbol] = useState<Symbol>("BTCUSDT");
  const [interval, setIntervalSel] = useState<Interval>("1d");
  const [prices, setPrices] = useState<Partial<Record<Symbol, number>>>({});
  const [agents, setAgents] = useState<Partial<Record<Symbol, Agent>>>({});
  const [liveEvents, setLiveEvents] = useState<FeedEvent[]>([]);
  const [flash, setFlash] = useState<FeedEvent | null>(null);
  const known = useRef<Record<string, number>>({});
  const above = useRef<Record<string, boolean>>({});

  // Live prices for all three markets (Binance public stream, read-only).
  useEffect(() => {
    const streams = SYMBOLS.map((s) => `${s.toLowerCase()}@miniTicker`).join("/");
    const ws = new WebSocket(`wss://stream.binance.com:9443/stream?streams=${streams}`);
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data).data;
      setPrices((p) => ({ ...p, [d.s as Symbol]: +d.c }));
    };
    return () => ws.close();
  }, []);

  // The agent's state; re-checked every minute so a new buy/sell shows up on its own.
  const loadAgents = useCallback(async () => {
    const res = await Promise.all(SYMBOLS.map((s) => fetch(`${API}/daily-trend/agent/${s}`).then((r) => r.json()).catch(() => null)));
    const next: Partial<Record<Symbol, Agent>> = {};
    res.forEach((a, i) => { if (a && a.markers) next[SYMBOLS[i]] = a as Agent; });
    setAgents(next);
    for (const s of SYMBOLS) {
      const a = next[s];
      if (!a) continue;
      const count = a.markers.length;
      const prev = known.current[s];
      if (prev !== undefined && count > prev) {
        const m = a.markers[a.markers.length - 1];
        const ev: FeedEvent = {
          id: `live-${s}-${Date.now()}`, when: "just now", symbol: s, live: true, kind: m.side,
          title: m.side === "BUY" ? `The agent just BOUGHT ${NAMES[s]} at ${usd(m.price)}` : `The agent just SOLD ${NAMES[s]} at ${usd(m.price)}`,
          detail: m.side === "BUY" ? "A new daily candle closed above the 20-day high." : "A new daily candle closed below the 10-day low.",
        };
        setLiveEvents((e) => [ev, ...e]);
        setFlash(ev);
      }
      known.current[s] = count;
    }
  }, []);
  useEffect(() => {
    loadAgents();
    const t = window.setInterval(loadAgents, 60_000);
    return () => window.clearInterval(t);
  }, [loadAgents]);

  // "Heads up" when the live price crosses one of the agent's trigger lines.
  useEffect(() => {
    for (const s of SYMBOLS) {
      const a = agents[s]; const p = prices[s];
      if (!a || !p) continue;
      const trigger = a.position === "FLAT" ? a.buy_above : a.sell_below;
      const crossed = a.position === "FLAT" ? p > trigger : p < trigger;
      const k = `${s}-${a.position}`;
      if (above.current[k] === undefined) { above.current[k] = crossed; continue; }
      if (crossed && !above.current[k]) {
        const buying = a.position === "FLAT";
        setLiveEvents((e) => [{
          id: `alert-${s}-${Date.now()}`, when: "just now", symbol: s, live: true, kind: "ALERT",
          title: `${NAMES[s]} just moved ${buying ? "above the buy line" : "below the sell line"} (${usd(p)})`,
          detail: `Nothing has been ${buying ? "bought" : "sold"} yet. The agent only acts if today's candle CLOSES ${buying ? "above" : "below"} ${usd(trigger)} (midnight UTC); then it ${buying ? "buys" : "sells"} at the next open.`,
        }, ...e]);
      }
      above.current[k] = crossed;
    }
  }, [prices, agents]);

  const events = useMemo(() => [...liveEvents, ...historyEvents(agents)], [liveEvents, agents]);
  const onPrice = useCallback((p: number) => setPrices((x) => ({ ...x, [symbol]: p })), [symbol]);
  const selectedAgent = agents[symbol] ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 sm:space-y-6 sm:p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold sm:text-3xl"><span className="curve-underline">Live Market &amp; Trading Agent</span></h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Watch the real market live and see exactly when the practice-money agent buys and sells. No real money is used.
        </p>
      </div>

      {flash && (
        <div className={`flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-center sm:justify-between ${flash.kind === "BUY" ? "border-bull/30 bg-bull/10 text-bull" : "border-bear/30 bg-bear/10 text-bear"}`}>
          <span className="font-semibold">{flash.title}</span>
          <button onClick={() => setFlash(null)} className="self-start rounded-full bg-white/10 px-4 py-1 text-sm text-white sm:self-auto">OK</button>
        </div>
      )}

      <MarketCards selected={symbol} onSelect={setSymbol} prices={prices} agents={agents} />

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="text-sm text-slate-400">
          {interval === "1d"
            ? <>Green <b className="text-bull">▲ BOUGHT</b> and red <b className="text-bear">▼ SOLD</b> arrows show every move the agent made. Dashed lines show where it would act next.</>
            : <>Choose <b>Daily</b> to see the agent&apos;s buy and sell arrows (it decides once per day).</>}
        </div>
        <div className="seg self-start">
          {INTERVALS.map(([k, label]) => (
            <button key={k} data-active={k === interval} onClick={() => setIntervalSel(k)} className="seg-btn">{label}</button>
          ))}
        </div>
      </div>

      <CandleChart symbol={symbol} interval={interval} agent={selectedAgent} onPrice={onPrice} />

      <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
        <AgentPanel agent={selectedAgent} livePrice={prices[symbol] ?? null} />
        <ActivityFeed events={events} />
      </div>

      <PaperAccount />

      <EquityPanel />

      <p className="pb-6 text-xs leading-relaxed text-slate-500">
        Paper trading only: no real funds, no exchange orders. Results come from past data and do not promise future profit. Strategy: daily trend-following (ADR-037).
      </p>
    </div>
  );
}
