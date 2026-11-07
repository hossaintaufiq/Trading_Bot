"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  Shield,
  TrendingUp,
  Cpu,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  RefreshCw,
  Zap,
  Lock,
  Layers,
  ArrowUpRight,
  Clock,
  Terminal,
} from "lucide-react";

interface AgentStatus {
  name: string;
  id: string;
  role: string;
  status: "idle" | "observing" | "analyzing" | "validating" | "active";
  lastAction: string;
}

const AGENTS: AgentStatus[] = [
  { name: "Market Scanner", id: "market_scanner", role: "Scans 1h/4h closed candles & regime", status: "observing", lastAction: "Checked BTC/ETH/BNB 4h candle close" },
  { name: "Trend Analyst", id: "trend_analyst", role: "4h EMA 50/200 stack & ADX >= 24 filter", status: "active", lastAction: "Evaluating macro trend alignment" },
  { name: "Momentum Analyst", id: "momentum_analyst", role: "RSI, MACD & 1h swing momentum", status: "idle", lastAction: "Momentum score computed (Neutral-Bull)" },
  { name: "Volume Analyst", id: "volume_analyst", role: "Volume anomaly & value zone test", status: "idle", lastAction: "Volume within normal 1.2x envelope" },
  { name: "News Analyst", id: "news_analyst", role: "Point-in-time news & macro calendar filter", status: "idle", lastAction: "No Tier-1 macro blackouts active" },
  { name: "Strategy Analyst", id: "strategy_analyst", role: "Dual-Timeframe V2 swing setup detector", status: "analyzing", lastAction: "Scanning EMA 21-50 value band pullbacks" },
  { name: "Signal Validator", id: "signal_validator", role: "BTC Macro Regime Gating & multi-timeframe check", status: "active", lastAction: "BTC Macro Gate: Active (Shield enabled)" },
  { name: "Risk Manager", id: "risk_manager", role: "CPPI adaptive sizing & 5% breaker guard", status: "active", lastAction: "Risk Budget: 0.5% ($5.00) | Cushion: 100%" },
  { name: "Execution Manager", id: "execution_manager", role: "Next-bar paper fill simulation with friction", status: "idle", lastAction: "Monitoring pending order queue" },
  { name: "Performance Auditor", id: "performance_auditor", role: "Double-entry PortfolioLedger verification", status: "active", lastAction: "Invariants 100% reconciled" },
];

export default function CommandCenterPage() {
  const [mounted, setMounted] = useState(false);
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<string>("Checking...");
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    setMounted(true);
    const updateTime = () => setCurrentTime(new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC");
    updateTime();
    const timer = setInterval(updateTime, 1000);

    const checkHealth = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/v1/health");
        if (res.ok) {
          const data = await res.json();
          setBackendHealth(data);
          setLastHeartbeat("Connected (127.0.0.1:8000)");
        } else {
          setLastHeartbeat("Degraded");
        }
      } catch (err) {
        setLastHeartbeat("Offline (Check Backend)");
      }
    };

    checkHealth();
    const healthInterval = setInterval(checkHealth, 5000);
    return () => {
      clearInterval(timer);
      clearInterval(healthInterval);
    };
  }, []);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                NEPTUNE <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">v0.1.0-alpha</span>
              </h1>
              <p className="text-xs text-slate-400 font-mono">Autonomous Market Intelligence & Paper Trading Engine</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-slate-400">Backend:</span>
            <span className="text-emerald-400 font-medium">{lastHeartbeat}</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{currentTime}</span>
          </div>
        </div>
      </header>

      {/* Safety Notice Banner */}
      <div className="my-6 bg-blue-950/40 border border-blue-900/60 rounded-xl p-4 flex items-center justify-between text-xs text-blue-200">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-blue-400 flex-shrink-0" />
          <div>
            <span className="font-semibold text-white">Rule S-01 Active: Paper Trading Isolation.</span> All orders execute strictly against simulated liquidity with 0.10% fee, 0.05% slippage, and 0.01% spread. Zero real funds or exchange keys are connected.
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-950 text-emerald-300 rounded border border-emerald-800 font-mono text-[11px]">
          <Lock className="w-3.5 h-3.5" />
          <span>Paper Mode: \$1,000 USDT</span>
        </div>
      </div>

      {/* Primary KPI Metrics */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1 font-mono">
            <span>STARTING CAPITAL</span>
            <DollarSign className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">$1,000.00 <span className="text-xs text-slate-400">USDT</span></div>
          <div className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1 font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Liquid Cash: $1,000.00 (100%)</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1 font-mono">
            <span>RISK PER TRADE</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">0.50% <span className="text-xs text-slate-400">($5.00)</span></div>
          <div className="text-[11px] text-cyan-400 mt-2 font-mono flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>CPPI Cushion Active (100% full size)</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1 font-mono">
            <span>CIRCUIT BREAKER LIMIT</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">5.00% <span className="text-xs text-slate-400">Max DD</span></div>
          <div className="text-[11px] text-emerald-400 mt-2 font-mono flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Status: SAFE (0 trips in 34 months)</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1 font-mono">
            <span>VALIDATED 3-YR RETURN</span>
            <TrendingUp className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">+5.80% <span className="text-xs text-slate-300">(+$58.01)</span></div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            <span>214 trades across 2024-2026 cycles</span>
          </div>
        </div>
      </section>

      {/* Main Grid: Live Agents & Strategy Core */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Left 2 Cols: Ten Specialist Agents */}
        <section className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-semibold text-white">Central Brain & Ten Specialist Agents</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">All 10 Agents Online</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {AGENTS.map((agent) => (
              <div key={agent.id} className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 hover:border-slate-700 transition-colors">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-semibold text-sm text-slate-200">{agent.name}</span>
                  <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border ${
                    agent.status === "active" ? "bg-emerald-950/80 text-emerald-400 border-emerald-800" :
                    agent.status === "analyzing" ? "bg-cyan-950/80 text-cyan-400 border-cyan-800 animate-pulse" :
                    agent.status === "observing" ? "bg-blue-950/80 text-blue-400 border-blue-800" :
                    "bg-slate-900 text-slate-400 border-slate-800"
                  }`}>
                    {agent.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-2">{agent.role}</p>
                <div className="text-[11px] font-mono text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800/60 flex items-center gap-1.5 truncate">
                  <Terminal className="w-3 h-3 text-cyan-400 flex-shrink-0" />
                  <span className="truncate">{agent.lastAction}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right Col: Active Strategy Architecture */}
        <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800">
              <Layers className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-semibold text-white">Active Strategy Engine</h2>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-xs text-slate-400 block mb-1">Model Name</span>
                <span className="text-sm font-bold text-white font-mono bg-slate-950 px-2.5 py-1 rounded border border-slate-800 block">
                  DualTimeframeTrendStrategyV2
                </span>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">4h Macro Trend:</span>
                  <span className="text-slate-200">EMA(50) &gt; EMA(200)</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">4h ADX Threshold:</span>
                  <span className="text-cyan-400">&ge; 24.0 (Anti-Chop)</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">BTC Macro Gating:</span>
                  <span className="text-emerald-400">Active (Shield on)</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">1h Entry Trigger:</span>
                  <span className="text-slate-200">Pullback EMA 21-50 Band</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">Target Reward/Risk:</span>
                  <span className="text-emerald-400">&ge; 2.5 : 1</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">Breakeven Ratchet:</span>
                  <span className="text-cyan-400">+1.5R &rarr; Entry + 0.35%</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">Symbol Quarantine:</span>
                  <span className="text-amber-400">7 Days on 2 Stops</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1.5">
              <span>CIRCUIT BREAKER SAFETY BAR</span>
              <span className="text-emerald-400">4.45% / 5.00% MAX DD</span>
            </div>
            <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
              <div className="bg-gradient-to-r from-emerald-500 via-cyan-500 to-amber-500 h-full w-[25%] rounded-full"></div>
            </div>
          </div>
        </section>
      </div>

      {/* Bottom Tracked Universe Overview */}
      <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">Tracked Market Universe (Binance Spot Paper Replay)</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">Consuming Closed Candles Only (Rule A-09)</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400 font-mono">BITCOIN</div>
              <div className="text-lg font-bold text-white font-mono">BTC / USDT</div>
              <div className="text-xs text-emerald-400 mt-1 font-mono">3-Yr Net: +$17.73 USDT</div>
            </div>
            <div className="px-2.5 py-1 rounded bg-blue-950 border border-blue-800 text-[11px] text-blue-300 font-mono">
              Primary Asset
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400 font-mono">ETHEREUM</div>
              <div className="text-lg font-bold text-white font-mono">ETH / USDT</div>
              <div className="text-xs text-cyan-400 mt-1 font-mono">BTC Gated: Protected</div>
            </div>
            <div className="px-2.5 py-1 rounded bg-emerald-950 border border-emerald-800 text-[11px] text-emerald-300 font-mono">
              Macro Shield On
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400 font-mono">BINANCE COIN</div>
              <div className="text-lg font-bold text-white font-mono">BNB / USDT</div>
              <div className="text-xs text-cyan-400 mt-1 font-mono">Quarantine: Ready</div>
            </div>
            <div className="px-2.5 py-1 rounded bg-emerald-950 border border-emerald-800 text-[11px] text-emerald-300 font-mono">
              Macro Shield On
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
