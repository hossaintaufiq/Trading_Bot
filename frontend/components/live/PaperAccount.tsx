"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart, createSeriesMarkers, LineSeries, type ISeriesApi, type UTCTimestamp,
} from "lightweight-charts";
import { NAMES, type Symbol, niceDate, usd } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const STARTS = [["2026-01-01", "Since Jan 2026"], ["2025-01-01", "Since Jan 2025"], ["2024-01-01", "Since Jan 2024"]] as const;

interface Row {
  date: string; symbol: Symbol; side: "BUY" | "SELL"; price: number; qty: number; amount: number; fee: number;
  profit: number | null; cash_after: number; coins_after: number; total_after: number; total_change: number;
}
interface Account {
  start: string; initial: number; total_now: number; cash_now: number; coins_now: number; return_pct: number;
  fees_paid: number; holdings: { symbol: Symbol; qty: number; bought_at: number; value: number; unrealized_pct: number }[];
  ledger: Row[]; curve: { date: string; total: number }[];
}

const money = (n: number) => `${n >= 0 ? "+" : "−"}$${Math.abs(n).toFixed(2)}`;
const tone = (n: number) => (n >= 0 ? "text-emerald-400" : "text-red-400");

/** The practice-money wallet: what the account holds, and how the money changed after every buy and sell. */
export default function PaperAccount() {
  const el = useRef<HTMLDivElement>(null);
  const line = useRef<ISeriesApi<"Line"> | null>(null);
  const [start, setStart] = useState<string>(STARTS[0][0]);
  const [acc, setAcc] = useState<Account | null>(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    if (!el.current) return;
    const chart = createChart(el.current, {
      layout: { background: { color: "#0b1020" }, textColor: "#9aa4bf" },
      grid: { vertLines: { color: "#161d33" }, horzLines: { color: "#161d33" } }, autoSize: true,
    });
    line.current = chart.addSeries(LineSeries, { color: "#4f8cff", lineWidth: 2, priceLineVisible: false });
    return () => { chart.remove(); line.current = null; };
  }, []);

  useEffect(() => {
    let dead = false;
    const load = () => fetch(`${API}/daily-trend/account?start=${start}`).then((r) => r.json())
      .then((a) => { if (!dead && a.ledger) setAcc(a); }).catch(() => undefined);
    setAcc(null); load();
    const t = window.setInterval(load, 60_000);
    return () => { dead = true; window.clearInterval(t); };
  }, [start]);

  useEffect(() => {
    if (!acc || !line.current) return;
    line.current.setData(acc.curve.map((p) => ({ time: (Date.parse(p.date) / 1000) as UTCTimestamp, value: p.total })));
    const byDay = new Map<string, Row>();
    acc.ledger.forEach((r) => byDay.set(`${r.date}-${r.side}`, r));
    const marks = [...byDay.values()].map((r) => ({
      time: (Date.parse(r.date) / 1000) as UTCTimestamp,
      position: r.side === "BUY" ? ("belowBar" as const) : ("aboveBar" as const),
      shape: r.side === "BUY" ? ("arrowUp" as const) : ("arrowDown" as const),
      color: r.side === "BUY" ? "#22c55e" : "#ef4444",
    }));
    const have = new Set(acc.curve.map((p) => Date.parse(p.date) / 1000));
    createSeriesMarkers(line.current, marks.filter((m) => have.has(m.time as number)));
  }, [acc]);

  const rows = acc ? [...acc.ledger].reverse() : [];
  const shown = all ? rows : rows.slice(0, 12);

  return (
    <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold">Practice wallet: how the money changed</h3>
          <p className="text-sm text-slate-400">
            Imagine a practice account opened with <b>$1,000</b> and split evenly across the three coins. Every time the agent buys or sells, this is what happens to the money.
          </p>
        </div>
        <div className="flex gap-1">
          {STARTS.map(([k, l]) => (
            <button key={k} onClick={() => setStart(k)} className={`rounded px-3 py-1 text-sm ${k === start ? "bg-blue-600" : "bg-slate-800 hover:bg-slate-700"}`}>{l}</button>
          ))}
        </div>
      </div>

      {!acc ? <p className="text-sm text-slate-400">Loading the wallet…</p> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-md bg-slate-800/60 p-3"><div className="text-xs text-slate-400">Started with</div><div className="text-xl font-mono">{usd(acc.initial)}</div></div>
            <div className="rounded-md bg-slate-800/60 p-3"><div className="text-xs text-slate-400">Worth now</div>
              <div className={`text-xl font-mono ${tone(acc.total_now - acc.initial)}`}>{usd(acc.total_now)}</div>
              <div className={`text-xs ${tone(acc.return_pct)}`}>{money(acc.total_now - acc.initial)} ({acc.return_pct.toFixed(1)}%)</div></div>
            <div className="rounded-md bg-slate-800/60 p-3"><div className="text-xs text-slate-400">Cash (not invested)</div><div className="text-xl font-mono">{usd(acc.cash_now)}</div></div>
            <div className="rounded-md bg-slate-800/60 p-3"><div className="text-xs text-slate-400">Fees paid so far</div><div className="text-xl font-mono">{usd(acc.fees_paid)}</div></div>
          </div>

          <p className="text-sm text-slate-300">
            {acc.holdings.length === 0
              ? <>Right now the agent holds <b>no coins</b>. All the money is in cash, waiting for the next buy signal.</>
              : <>Right now the agent holds: {acc.holdings.map((h) => (
                  <span key={h.symbol} className="mr-3"><b>{NAMES[h.symbol]}</b> worth {usd(h.value)} (<span className={tone(h.unrealized_pct)}>{h.unrealized_pct.toFixed(1)}%</span> since buying)</span>
                ))}</>}
          </p>

          <div ref={el} className="h-[220px] w-full" />
          <p className="text-xs text-slate-500">Blue line = total value of the wallet (cash + coins). Green ▲ = a buy, red ▼ = a sell.</p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-500">
                <tr><th className="p-2">Date</th><th className="p-2">What the agent did</th><th className="p-2 text-right">Cash after</th>
                  <th className="p-2 text-right">In coins after</th><th className="p-2 text-right">Wallet total</th><th className="p-2 text-right">Change</th></tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={`${r.date}-${r.symbol}-${r.side}-${i}`} className="border-t border-slate-800">
                    <td className="p-2 whitespace-nowrap text-slate-400">{niceDate(r.date)}</td>
                    <td className="p-2">
                      <span className={`mr-2 rounded px-1.5 py-0.5 text-xs font-bold ${r.side === "BUY" ? "bg-emerald-600" : "bg-red-600"}`}>{r.side === "BUY" ? "BOUGHT" : "SOLD"}</span>
                      {NAMES[r.symbol]} for <b>{usd(r.amount)}</b> <span className="text-slate-500">(fee {usd(r.fee)})</span>
                      {r.profit !== null && <span className={`ml-2 ${tone(r.profit)}`}>{r.profit >= 0 ? "profit" : "loss"} {money(r.profit)}</span>}
                    </td>
                    <td className="p-2 text-right font-mono">{usd(r.cash_after)}</td>
                    <td className="p-2 text-right font-mono">{usd(r.coins_after)}</td>
                    <td className="p-2 text-right font-mono">{usd(r.total_after)}</td>
                    <td className={`p-2 text-right font-mono ${tone(r.total_change)}`}>{money(r.total_change)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > 12 && (
            <button onClick={() => setAll(!all)} className="text-sm text-blue-400 hover:underline">{all ? "Show fewer" : `Show all ${rows.length} trades`}</button>
          )}
          <p className="text-xs text-slate-500">
            Replay of past market data with a $1,000 practice account (no real money). Prices include 0.05% slippage and 0.01% spread, plus a 0.10% fee on every buy and sell.
            &quot;Change&quot; is how much the wallet total moved at that trade (mostly price moves of coins held that day, minus fees). Past results do not promise future profit.
          </p>
        </>
      )}
    </div>
  );
}
