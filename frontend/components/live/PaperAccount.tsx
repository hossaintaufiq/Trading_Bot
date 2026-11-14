"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart, createSeriesMarkers, LineSeries, type ISeriesApi, type UTCTimestamp,
} from "lightweight-charts";
import { NAMES, type Symbol, niceDate, usd } from "./types";
import { chartOptions, curvedLine } from "./chartTheme";

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
const tone = (n: number) => (n >= 0 ? "text-bull" : "text-bear");

/** The practice-money wallet: what the account holds, and how the money changed after every buy and sell. */
export default function PaperAccount() {
  const el = useRef<HTMLDivElement>(null);
  const line = useRef<ISeriesApi<"Line"> | null>(null);
  const [start, setStart] = useState<string>(STARTS[0][0]);
  const [acc, setAcc] = useState<Account | null>(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    if (!el.current) return;
    const chart = createChart(el.current, chartOptions);
    line.current = chart.addSeries(LineSeries, curvedLine);
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
      color: r.side === "BUY" ? "#34d399" : "#fb7185",
    }));
    const have = new Set(acc.curve.map((p) => Date.parse(p.date) / 1000));
    createSeriesMarkers(line.current, marks.filter((m) => have.has(m.time as number)));
  }, [acc]);

  const rows = acc ? [...acc.ledger].reverse() : [];
  const shown = all ? rows : rows.slice(0, 12);

  return (
    <div className="surface space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold"><span className="curve-underline">Practice wallet</span></h3>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Imagine a practice account opened with <b>$1,000</b> and split evenly across the three coins. Every time the agent buys or sells, this is what happens to the money.
          </p>
        </div>
        <div className="seg self-start">
          {STARTS.map(([k, l]) => (
            <button key={k} data-active={k === start} onClick={() => setStart(k)} className="seg-btn">{l}</button>
          ))}
        </div>
      </div>

      {!acc ? <p className="text-sm text-slate-400">Loading the wallet…</p> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3 sm:p-4"><div className="text-xs text-slate-400">Started with</div><div className="text-lg font-mono sm:text-xl">{usd(acc.initial)}</div></div>
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3 sm:p-4"><div className="text-xs text-slate-400">Worth now</div>
              <div className={`text-lg font-mono sm:text-xl ${tone(acc.total_now - acc.initial)}`}>{usd(acc.total_now)}</div>
              <div className={`text-xs ${tone(acc.return_pct)}`}>{money(acc.total_now - acc.initial)} ({acc.return_pct.toFixed(1)}%)</div></div>
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3 sm:p-4"><div className="text-xs text-slate-400">Cash (not invested)</div><div className="text-lg font-mono sm:text-xl">{usd(acc.cash_now)}</div></div>
            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3 sm:p-4"><div className="text-xs text-slate-400">Fees paid so far</div><div className="text-lg font-mono sm:text-xl">{usd(acc.fees_paid)}</div></div>
          </div>

          <p className="text-sm text-slate-300">
            {acc.holdings.length === 0
              ? <>Right now the agent holds <b>no coins</b>. All the money is in cash, waiting for the next buy signal.</>
              : <>Right now the agent holds: {acc.holdings.map((h) => (
                  <span key={h.symbol} className="mr-3"><b>{NAMES[h.symbol]}</b> worth {usd(h.value)} (<span className={tone(h.unrealized_pct)}>{h.unrealized_pct.toFixed(1)}%</span> since buying)</span>
                ))}</>}
          </p>

          <div ref={el} className="h-[200px] w-full sm:h-[260px]" />
          <p className="text-xs text-slate-500">Blue line = total value of the wallet (cash + coins). Green ▲ = a buy, red ▼ = a sell.</p>

          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-xs uppercase text-slate-500">
                <tr><th className="p-2">Date</th><th className="p-2">What the agent did</th><th className="p-2 text-right">Cash after</th>
                  <th className="p-2 text-right">In coins after</th><th className="p-2 text-right">Wallet total</th><th className="p-2 text-right">Change</th></tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={`${r.date}-${r.symbol}-${r.side}-${i}`} className="border-t border-white/5">
                    <td className="p-2 whitespace-nowrap text-slate-400">{niceDate(r.date)}</td>
                    <td className="p-2">
                      <span className={`mr-2 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${r.side === "BUY" ? "bg-bull/20 text-bull" : "bg-bear/20 text-bear"}`}>{r.side === "BUY" ? "BOUGHT" : "SOLD"}</span>
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
            <button onClick={() => setAll(!all)} className="text-sm text-iris-400 hover:text-iris-300">{all ? "Show fewer" : `Show all ${rows.length} trades`}</button>
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
