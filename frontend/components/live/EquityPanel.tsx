"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, LineSeries, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import type { DailyTrend } from "./types";
import { chartOptions, curvedLine } from "./chartTheme";

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
    const chart = createChart(el.current, chartOptions);
    line.current = chart.addSeries(LineSeries, curvedLine);
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
    <div className="surface p-4 sm:p-6">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-lg font-semibold"><span className="curve-underline">How $1,000 would have grown</span></h3>
        <div className="seg">
          {PERIODS.map(([k, l]) => (
            <button key={k} data-active={k === period} onClick={() => setPeriod(k)} className="seg-btn">{l}</button>
          ))}
        </div>
      </div>
      <div ref={el} className="h-[200px] w-full sm:h-[240px]" />
      {p && (
        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          Following the agent: <b className={p.net_return_pct >= 0 ? "text-bull" : "text-bear"}>{p.net_return_pct.toFixed(0)}%</b>
          {" "}· simply holding the coins: <b>{p.buy_hold_pct.toFixed(0)}%</b>
          {" "}· biggest drop along the way: <b>{p.max_drawdown_pct.toFixed(0)}%</b>
          {" "}· {p.trades} trades, all fees included. <span className="text-slate-500">Past results do not promise future profit.</span>
        </p>
      )}
    </div>
  );
}
