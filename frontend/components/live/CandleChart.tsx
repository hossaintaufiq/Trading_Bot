"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart, CandlestickSeries, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type UTCTimestamp,
} from "lightweight-charts";
import type { Agent, Symbol } from "./types";
import { chartOptions } from "./chartTheme";

export const INTERVALS = [
  ["1d", "Daily"], ["4h", "4 hours"], ["1h", "1 hour"], ["15m", "15 min"], ["1m", "1 min"],
] as const;
export type Interval = (typeof INTERVALS)[number][0];

interface Props { symbol: Symbol; interval: Interval; agent: Agent | null; onPrice: (p: number) => void; }

/** Live candlestick chart (Binance public data) with the agent's BUY/SELL arrows and trigger lines. */
export default function CandleChart({ symbol, interval, agent, onPrice }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const series = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [live, setLive] = useState(false);
  const [ready, setReady] = useState(0);

  useEffect(() => {
    if (!el.current) return;
    const chart: IChartApi = createChart(el.current, {
      ...chartOptions,
      timeScale: { ...chartOptions.timeScale, timeVisible: true, secondsVisible: false },
    });
    const s = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399", downColor: "#fb7185", borderVisible: false,
      wickUpColor: "#34d399", wickDownColor: "#fb7185",
    });
    series.current = s;
    let ws: WebSocket | null = null;
    let dead = false;
    setLive(false);

    (async () => {
      try {
        const r = await fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=1000`);
        const rows: (string | number)[][] = await r.json();
        if (dead) return;
        s.setData(rows.map((k) => ({
          time: Math.floor(Number(k[0]) / 1000) as UTCTimestamp,
          open: +k[1], high: +k[2], low: +k[3], close: +k[4],
        })));
        chart.timeScale().fitContent();
        onPrice(+rows[rows.length - 1][4]);
        setReady((n) => n + 1);
      } catch { /* shown as not live */ }
      if (dead) return;
      ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`);
      ws.onopen = () => setLive(true);
      ws.onclose = () => setLive(false);
      ws.onmessage = (m) => {
        const k = JSON.parse(m.data).k;
        s.update({ time: Math.floor(k.t / 1000) as UTCTimestamp, open: +k.o, high: +k.h, low: +k.l, close: +k.c });
        onPrice(+k.c);
      };
    })();

    return () => { dead = true; ws?.close(); chart.remove(); series.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval]);

  // Agent arrows + buy/sell lines (the agent acts on daily closes, so they are drawn on the daily view).
  useEffect(() => {
    const s = series.current;
    if (!s || !agent || agent.symbol !== symbol || interval !== "1d") return;
    const have = new Set(s.data().map((d) => d.time as number));
    const ms = agent.markers
      .map((m) => ({ ...m, ts: Math.floor(Date.parse(m.time) / 1000) }))
      .filter((m) => have.has(m.ts))
      .map((m) => ({
        time: m.ts as UTCTimestamp,
        position: m.side === "BUY" ? ("belowBar" as const) : ("aboveBar" as const),
        shape: m.side === "BUY" ? ("arrowUp" as const) : ("arrowDown" as const),
        color: m.side === "BUY" ? "#22c55e" : "#ef4444",
        text: m.side === "BUY" ? (m.open ? "BOUGHT (holding)" : "BOUGHT")
          : `SOLD ${m.pct !== undefined ? (m.pct >= 0 ? "+" : "") + m.pct.toFixed(0) + "%" : ""}`,
      }));
    createSeriesMarkers(s, ms);
    const a = s.createPriceLine({ price: agent.buy_above, color: "#22c55e", lineStyle: 2, title: "Agent buys above this" });
    const b = s.createPriceLine({ price: agent.sell_below, color: "#ef4444", lineStyle: 2, title: "Agent sells below this" });
    return () => { try { s.removePriceLine(a); s.removePriceLine(b); } catch { /* chart already gone */ } };
  }, [agent, symbol, interval, ready]);

  return (
    <div className="relative">
      <div ref={el} className="surface h-[300px] w-full overflow-hidden p-1 sm:h-[400px] lg:h-[460px]" />
      <span className={`pill absolute right-4 top-4 z-10 ${live ? "bg-bull/15 text-bull" : "bg-white/5 text-slate-400"}`}>
        {live ? "● LIVE" : "connecting…"}
      </span>
    </div>
  );
}
