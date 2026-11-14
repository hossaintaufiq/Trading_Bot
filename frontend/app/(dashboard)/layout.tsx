"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useState } from "react";

const NAV = [
  ["/live-markets", "Live Market & Agent", "The market and what the agent is doing"],
  ["/command-center", "Command Center", "System overview and research results"],
] as const;

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-iris-400 to-iris-700 font-display text-sm font-bold text-white shadow-glow">N</span>
      <span className="font-display text-lg font-semibold tracking-[0.18em] text-white">NEPTUNE</span>
    </div>
  );
}

function NavLinks({ path, onNavigate }: { path: string; onNavigate?: () => void }) {
  return (
    <nav className="space-y-1.5">
      {NAV.map(([href, label, hint]) => {
        const active = path === href;
        return (
          <Link key={href} href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
            className={`block rounded-xl border px-3.5 py-2.5 transition ${active
              ? "border-iris-500/30 bg-iris-500/10 text-white"
              : "border-transparent text-slate-300 hover:bg-white/[0.04]"}`}>
            <div className="text-sm font-medium">{label}</div>
            <div className="text-xs text-slate-500">{hint}</div>
          </Link>
        );
      })}
    </nav>
  );
}

function Notice() {
  return (
    <div className="rounded-xl border border-gold/20 bg-gold/[0.06] p-3 text-xs leading-relaxed text-gold/90">
      Paper trading only. No real money is used or at risk.
    </div>
  );
}

/** Dashboard shell: sidebar on desktop, sticky top bar + drawer on mobile. */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  return (
    <div className="min-h-screen lg:flex">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col justify-between border-r border-white/[0.06] bg-black/20 p-5 backdrop-blur-md lg:flex">
        <div className="space-y-8">
          <Brand />
          <NavLinks path={path} />
        </div>
        <Notice />
      </aside>

      {/* Mobile / tablet top bar */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-white/[0.06] bg-[#0a0a12]/80 px-4 py-3 backdrop-blur-xl lg:hidden">
        <Brand />
        <button onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open}
          className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-white/[0.04]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h10" /></svg>
        </button>
      </header>

      {/* Mobile drawer */}
      <div className={`fixed inset-0 z-50 lg:hidden ${open ? "" : "pointer-events-none"}`} aria-hidden={!open}>
        <div onClick={() => setOpen(false)}
          className={`absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity ${open ? "opacity-100" : "opacity-0"}`} />
        <aside className={`absolute inset-y-0 left-0 flex w-[82%] max-w-xs flex-col justify-between border-r border-white/10 bg-[#0d0d18] p-5 transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <Brand />
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:bg-white/5">✕</button>
            </div>
            <NavLinks path={path} onNavigate={() => setOpen(false)} />
          </div>
          <Notice />
        </aside>
      </div>

      <main className="min-w-0 flex-1 animate-fade-in">{children}</main>
    </div>
  );
}
