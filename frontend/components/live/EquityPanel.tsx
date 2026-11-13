"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, LineSeries, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import type { DailyTrend } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const PERIODS = [["test_2024_2026", "Recent test (2024–26)"], ["train_2018_2023", "Older (2018–23)"]] as const;

/** How a $1,000 practice account would have grown following the agent (past data, after fees). */
export default function EquityPanel() {
  const el = useRef<HTMLDivElement>(null);
  const line = useRef<ISeriesApi<"Line"> | null>(null);
  const [dt, setDt] = useState<DailyTrend | null>(null);
  const [period, setPeriod] = useState<string>(PERIODS[0][0]);

  useEffect(() => {
    if (!el.current) return;
    const chart = createChart(el.current, {
      layout: { background: { color: "#0b1020" }, textColor: "#9aa4bf" },
      grid: { vertLines: { color: "#161d33" }, horzLines: { color: "#161d33" } }, autoSize: true,
    });
    line.current = chart.addSeries(LineSeries, { color: "#4f8cff", lineWidth: 2 });
    return () => chart.remove();
  }, []);
  useEffect(() => { fetch(`${API}/daily-trend`).then((r) => r.json()).then(setDt).catch(() => setDt(null)); }, []);
  useEffect(() => {
    const p = dt?.periods[period];
    if (p && line.current) {
      line.current.setData(p.equity_curve.map((e) => ({ time: (Date.parse(e.date) / 1000) as UTCTimestamp, value: e.equity })));
    }
  }, [dt, period]);

  const p = dt?.periods[period];
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold">Practice account: how $1,000 would have grown</h3>
        <div className="flex gap-1">
          {PERIODS.map(([k, l]) => (
            <button key={k} onClick={() => setPeriod(k)} className={`rounded px-2 py-1 text-xs ${k === period ? "bg-blue-600" : "bg-slate-800"}`}>{l}</button>
          ))}
        </div>
      </div>
      <div ref={el} className="h-[220px] w-full" />
      {p && (
        <p className="mt-2 text-sm text-slate-300">
          Following the agent: <b className={p.net_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}>{p.net_return_pct.toFixed(0)}%</b>
          {" "}· simply holding the coins: <b>{p.buy_hold_pct.toFixed(0)}%</b>
          {" "}· biggest drop along the way: <b>{p.max_drawdown_pct.toFixed(0)}%</b>
          {" "}· {p.trades} trades, all fees included. <span className="text-slate-500">Past results do not promise future profit.</span>
        </p>
      )}
    </div>
  );
}
