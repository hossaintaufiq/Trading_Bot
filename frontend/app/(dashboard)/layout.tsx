"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

const NAV = [
  ["/live-markets", "Live Market & Agent", "See the market and what the agent is doing"],
  ["/command-center", "Command Center", "System overview and research results"],
] as const;

/** Dashboard shell: sidebar + page. */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r border-slate-800 bg-navy-950 p-4 md:block">
        <div className="mb-6 text-lg font-bold tracking-wide">NEPTUNE</div>
        <nav className="space-y-1">
          {NAV.map(([href, label, hint]) => (
            <Link key={href} href={href}
              className={`block rounded-md px-3 py-2 text-sm ${path === href ? "bg-blue-600/20 text-white" : "text-slate-300 hover:bg-slate-800"}`}>
              <div className="font-medium">{label}</div>
              <div className="text-xs text-slate-500">{hint}</div>
            </Link>
          ))}
        </nav>
        <div className="mt-8 rounded-md border border-amber-700/50 bg-amber-950/20 p-3 text-xs text-amber-200">
          Paper trading only. No real money is used or at risk.
        </div>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
