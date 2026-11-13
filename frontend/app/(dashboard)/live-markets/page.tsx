"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const INTERVALS = ["1m", "5m", "15m", "1h", "4h"] as const;
const PERIODS = [
  ["train_2018_2023", "Train 2018-23"],
  ["test_2024_2026", "Test 2024-26"],
] as const;

interface Period {
  net_return_pct: number; max_drawdown_pct: number; trades: number; wins: number;
  fees: number; buy_hold_pct: number; equity_curve: { date: string; equity: number }[];
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
          `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=${interval}&limit=500`
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
      ws = new WebSocket(`wss://stream.binance.com:9443/ws/btcusdt@kline_${interval}`);
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
  }, [interval]);

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
          BTC/USDT Live · <span className="font-mono">{price ? price.toLocaleString() : "—"}</span>
          <span className="ml-3 text-xs text-slate-400">({status})</span>
        </h1>
        <div className="flex gap-1">
          {INTERVALS.map((i) => (
            <button key={i} onClick={() => setIntervalSel(i)}
              className={`px-3 py-1 rounded text-sm ${i === interval ? "bg-blue-600" : "bg-slate-800"}`}>
              {i}
            </button>
          ))}
        </div>
      </div>
      <div ref={candleEl} className="h-[420px] w-full rounded border border-slate-800" />

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
