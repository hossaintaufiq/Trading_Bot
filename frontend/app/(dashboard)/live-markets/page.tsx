"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  createSeriesMarkers,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"] as const;
const PERIODS = [
  ["train_2018_2023", "Train 2018-23"],
  ["test_2024_2026", "Test 2024-26"],
] as const;

interface Period {
  net_return_pct: number; max_drawdown_pct: number; trades: number; wins: number;
  fees: number; buy_hold_pct: number; equity_curve: { date: string; equity: number }[];
}
interface Agent {
  symbol: string; as_of: string; position: string; last_close: number;
  buy_above: number; sell_below: number;
  markers: { time: string; side: "BUY" | "SELL"; price: number; pct?: number; open?: boolean }[];
}
interface DailyTrend {
  periods: Record<string, Period>;
  current: { symbol: string; as_of: string; last_close: number; position: string }[];
}

const chartOpts = {
  layout: { background: { color: "#0b1020" }, textColor: "#9aa4bf" },
  grid: { vertLines: { color: "#161d33" }, horzLines: { color: "#161d33" } },
  timeScale: { timeVisible: true, secondsVisible: false },
  autoSize: true,
};

export default function LiveMarketsPage() {
  const [interval, setIntervalSel] = useState<(typeof INTERVALS)[number]>("1m");
  const [symbol, setSymbol] = useState<(typeof SYMBOLS)[number]>("BTCUSDT");
  const [agent, setAgent] = useState<Agent | null>(null);
  const [price, setPrice] = useState<number | null>(null);
  const [status, setStatus] = useState("connecting");
  const [period, setPeriod] = useState<string>("test_2024_2026");
  const [dt, setDt] = useState<DailyTrend | null>(null);

  const candleEl = useRef<HTMLDivElement>(null);
  const equityEl = useRef<HTMLDivElement>(null);
  const candleChart = useRef<IChartApi | null>(null);
  const candleSeries = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const equityChart = useRef<IChartApi | null>(null);
  const equitySeries = useRef<ISeriesApi<"Line"> | null>(null);

  // Live BTCUSDT candles: Binance public market data only (no keys, read-only).
  useEffect(() => {
    if (!candleEl.current) return;
    const chart = createChart(candleEl.current, chartOpts);
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a", downColor: "#ef5350",
      borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });
    candleChart.current = chart;
    candleSeries.current = series;

    let ws: WebSocket | null = null;
    let cancelled = false;

    (async () => {
      try {
        const r = await fetch(
          `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=1000`
        );
        const rows: (string | number)[][] = await r.json();
        if (cancelled) return;
        series.setData(
          rows.map((k) => ({
            time: Math.floor(Number(k[0]) / 1000) as UTCTimestamp,
            open: +k[1], high: +k[2], low: +k[3], close: +k[4],
          }))
        );
        chart.timeScale().fitContent();
      } catch {
        setStatus("history fetch failed");
      }
      if (cancelled) return;
      ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`);
      ws.onopen = () => setStatus("live");
      ws.onclose = () => setStatus("disconnected");
      ws.onmessage = (m) => {
        const k = JSON.parse(m.data).k;
        series.update({
          time: Math.floor(k.t / 1000) as UTCTimestamp,
          open: +k.o, high: +k.h, low: +k.l, close: +k.c,
        });
        setPrice(+k.c);
      };
    })();

    return () => {
      cancelled = true;
      ws?.close();
      chart.remove();
    };
  }, [interval, symbol]);

  useEffect(() => {
    setAgent(null);
    fetch(`${API}/daily-trend/agent/${symbol}`).then((r) => r.json()).then(setAgent).catch(() => setAgent(null));
  }, [symbol]);

  // Agent BUY/SELL markers + trigger levels on the candle chart (daily agent -> shown on 1d view).
  useEffect(() => {
    const series = candleSeries.current;
    if (!series || !agent || interval !== "1d") return;
    const t = setTimeout(() => {
      const have = new Set(series.data().map((d) => d.time as number));
      const ms = agent.markers
        .map((m) => ({ ...m, ts: Math.floor(Date.parse(m.time) / 1000) }))
        .filter((m) => have.has(m.ts))
        .map((m) => ({
          time: m.ts as UTCTimestamp,
          position: m.side === "BUY" ? ("belowBar" as const) : ("aboveBar" as const),
          shape: m.side === "BUY" ? ("arrowUp" as const) : ("arrowDown" as const),
          color: m.side === "BUY" ? "#22c55e" : "#ef4444",
          text: m.side === "BUY" ? (m.open ? "BUY (holding)" : "BUY") : `SELL ${m.pct !== undefined ? m.pct.toFixed(0) + "%" : ""}`,
        }));
      createSeriesMarkers(series, ms);
      series.createPriceLine({ price: agent.buy_above, color: "#22c55e", lineStyle: 2, title: "agent BUYS above" });
      series.createPriceLine({ price: agent.sell_below, color: "#ef4444", lineStyle: 2, title: "agent SELLS below" });
    }, 1500);
    return () => clearTimeout(t);
  }, [agent, interval, symbol]);

  // Simulation engine output (paper backtest of daily_trend_v1 from the backend).
  useEffect(() => {
    if (!equityEl.current) return;
    const chart = createChart(equityEl.current, chartOpts);
    equityChart.current = chart;
    equitySeries.current = chart.addSeries(LineSeries, { color: "#4f8cff", lineWidth: 2 });
    return () => chart.remove();
  }, []);

  useEffect(() => {
    fetch(`${API}/daily-trend`)
      .then((r) => r.json())
      .then((d: DailyTrend) => setDt(d))
      .catch(() => setDt(null));
  }, []);

  useEffect(() => {
    const p = dt?.periods[period];
    if (!p) return;
    equitySeries.current?.setData(
      p.equity_curve.map((e) => ({ time: (Date.parse(e.date) / 1000) as UTCTimestamp, value: e.equity }))
    );
    equityChart.current?.timeScale().fitContent();
  }, [dt, period]);

  const p = dt?.periods[period];

  return (
    <div className="p-6 space-y-6 text-slate-200">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">
          {symbol.replace("USDT", "/USDT")} Live · <span className="font-mono">{price ? price.toLocaleString() : "—"}</span>
          <span className="ml-3 text-xs text-slate-400">({status})</span>
        </h1>
        <div className="flex gap-1">
          {SYMBOLS.map((sy) => (
            <button key={sy} onClick={() => setSymbol(sy)}
              className={`px-3 py-1 rounded text-sm ${sy === symbol ? "bg-emerald-700" : "bg-slate-800"}`}>
              {sy.replace("USDT", "")}
            </button>
          ))}
          <span className="w-3" />
          {INTERVALS.map((i) => (
            <button key={i} onClick={() => setIntervalSel(i)}
              className={`px-3 py-1 rounded text-sm ${i === interval ? "bg-blue-600" : "bg-slate-800"}`}>
              {i}
            </button>
          ))}
        </div>
      </div>
      <div ref={candleEl} className="h-[460px] w-full rounded border border-slate-800" />
      <div className="text-sm">
        {interval !== "1d" ? (
          <span className="text-slate-400">Select <b>1d</b> to see where the agent bought and sold (it trades on daily closes).</span>
        ) : agent ? (
          <span>
            Agent status: <b className={agent.position === "LONG" ? "text-emerald-400" : "text-slate-300"}>{agent.position}</b>
            {" "}· buys if a daily close &gt; <b className="text-emerald-400">{agent.buy_above.toLocaleString()}</b>
            {" "}· sells if a daily close &lt; <b className="text-red-400">{agent.sell_below.toLocaleString()}</b>
            {" "}· green ▲ = BUY, red ▼ = SELL (% = trade result before costs)
          </span>
        ) : <span className="text-slate-400">loading agent…</span>}
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Simulation engine — daily_trend_v1 paper equity ($1,000 start, net of 0.32% costs)</h2>
        <div className="flex gap-1">
          {PERIODS.map(([k, label]) => (
            <button key={k} onClick={() => setPeriod(k)}
              className={`px-3 py-1 rounded text-sm ${k === period ? "bg-blue-600" : "bg-slate-800"}`}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div ref={equityEl} className="h-[280px] w-full rounded border border-slate-800" />
      {p ? (
        <div className="grid grid-cols-5 gap-4 text-sm">
          <div>Net return: <b className={p.net_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}>{p.net_return_pct.toFixed(1)}%</b></div>
          <div>Buy &amp; hold: <b>{p.buy_hold_pct.toFixed(1)}%</b></div>
          <div>Max drawdown: <b>{p.max_drawdown_pct.toFixed(1)}%</b></div>
          <div>Trades: <b>{p.trades}</b> ({p.wins} wins)</div>
          <div>Fees paid: <b>${p.fees.toFixed(0)}</b></div>
        </div>
      ) : <div className="text-sm text-slate-400">loading simulation…</div>}
      <div className="flex gap-6 text-sm">
        {dt?.current.map((c) => (
          <div key={c.symbol}>{c.symbol}: <b className={c.position === "LONG" ? "text-emerald-400" : "text-slate-400"}>{c.position}</b>
            <span className="text-slate-500"> @ {c.last_close.toLocaleString()} ({c.as_of})</span></div>
        ))}
      </div>
      <p className="text-xs text-slate-500">Paper trading only · no real funds · historical results are not a promise of future profit · research candidate, see ADR-037.</p>
    </div>
  );
}
