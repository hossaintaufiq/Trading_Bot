"""
Quantitative Performance Analytics and Reporting Module.
Computes institutional risk and return metrics: Net PnL, Win Rate, Payoff,
Expectancy after costs, Profit Factor, Max Drawdown, Sharpe, and breakdowns.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional


def compute_performance_metrics(
    trades: List[Dict[str, Any]],
    equity_curve: Optional[List[Dict[str, Any]]] = None,
    initial_capital: float = 10000.0,
    timeframe: str = "5m"
) -> Dict[str, Any]:
    """
    Compute full suite of quantitative metrics from closed trade records.
    """
    if not trades:
        return {
            "total_trades": 0,
            "net_pnl": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "expectancy_usd": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "fees_paid": 0.0,
            "breakdowns": {}
        }

    df_trades = pd.DataFrame(trades)

    total_trades = len(df_trades)
    wins = df_trades[df_trades["realized_pnl"] > 0]
    losses = df_trades[df_trades["realized_pnl"] <= 0]

    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = (n_wins / total_trades) * 100.0 if total_trades > 0 else 0.0
    loss_rate = (n_losses / total_trades) * 100.0 if total_trades > 0 else 0.0

    gross_profit = float(wins["realized_pnl"].sum()) if n_wins > 0 else 0.0
    gross_loss = float(abs(losses["realized_pnl"].sum())) if n_losses > 0 else 0.0
    net_pnl = float(df_trades["realized_pnl"].sum())
    total_fees = float(df_trades["total_fees"].sum())

    avg_win = float(wins["realized_pnl"].mean()) if n_wins > 0 else 0.0
    avg_loss = float(abs(losses["realized_pnl"].mean())) if n_losses > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else (avg_win if avg_win > 0 else 1.0)

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

    # Net Expectancy per trade = (WR * Avg Win) - (LR * Avg Loss)
    expectancy = ((win_rate / 100.0) * avg_win) - ((loss_rate / 100.0) * avg_loss)

    avg_hold_sec = float(df_trades["hold_duration_sec"].mean()) if "hold_duration_sec" in df_trades else 0.0
    avg_hold_min = avg_hold_sec / 60.0
    avg_hold_bars = float(df_trades["hold_bars"].mean()) if "hold_bars" in df_trades else 0.0

    # Max Drawdown & Sharpe calculation from equity curve or cumulative PnL
    if equity_curve and len(equity_curve) > 1:
        eq_series = pd.Series([e["equity"] for e in equity_curve])
        peak = eq_series.cummax()
        dd_series = (eq_series - peak) / peak * 100.0
        max_dd_pct = float(abs(dd_series.min()))
        max_dd_usd = float(abs((eq_series - peak).min()))

        # Annualized Sharpe (assuming 252 trading days, 24/7 crypto)
        returns = eq_series.pct_change().dropna()
        if len(returns) > 5 and returns.std() > 0:
            # Scale factor based on timeframe
            bars_per_day = 1440 if timeframe == "1m" else (288 if timeframe == "5m" else (96 if timeframe == "15m" else 24))
            annual_factor = np.sqrt(365 * bars_per_day)
            sharpe = float((returns.mean() / returns.std()) * annual_factor)
        else:
            sharpe = 0.0
    else:
        cum_pnl = df_trades["realized_pnl"].cumsum()
        eq = initial_capital + cum_pnl
        peak = eq.cummax()
        dd = (eq - peak) / peak * 100.0
        max_dd_pct = float(abs(dd.min())) if len(dd) > 0 else 0.0
        max_dd_usd = float(abs((eq - peak).min())) if len(dd) > 0 else 0.0

        ret = df_trades["realized_pnl_pct"] / 100.0
        sharpe = float((ret.mean() / ret.std()) * np.sqrt(365)) if len(ret) > 5 and ret.std() > 0 else 0.0

    # Breakdowns
    breakdown_strategy = {}
    for sid, grp in df_trades.groupby("setup_id"):
        w = grp[grp["realized_pnl"] > 0]
        l = grp[grp["realized_pnl"] <= 0]
        gp = float(w["realized_pnl"].sum()) if len(w) > 0 else 0.0
        gl = float(abs(l["realized_pnl"].sum())) if len(l) > 0 else 0.0
        pf = (gp / gl) if gl > 0 else gp
        breakdown_strategy[str(sid)] = {
            "trades": len(grp),
            "wins": len(w),
            "win_rate_pct": round((len(w) / len(grp)) * 100.0, 1),
            "net_pnl": round(float(grp["realized_pnl"].sum()), 2),
            "profit_factor": round(pf, 2),
            "fees_paid": round(float(grp["total_fees"].sum()), 2)
        }

    breakdown_symbol = {}
    for sym, grp in df_trades.groupby("symbol"):
        w = grp[grp["realized_pnl"] > 0]
        breakdown_symbol[str(sym)] = {
            "trades": len(grp),
            "wins": len(w),
            "win_rate_pct": round((len(w) / len(grp)) * 100.0, 1),
            "net_pnl": round(float(grp["realized_pnl"].sum()), 2),
            "fees_paid": round(float(grp["total_fees"].sum()), 2)
        }

    return {
        "total_trades": total_trades,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate_pct": round(win_rate, 2),
        "loss_rate_pct": round(loss_rate, 2),
        "net_pnl_usd": round(net_pnl, 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "fees_paid_usd": round(total_fees, 2),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "payoff_ratio": round(payoff_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy_per_trade_usd": round(expectancy, 4),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_hold_minutes": round(avg_hold_min, 1),
        "avg_hold_bars": round(avg_hold_bars, 1),
        "breakdown_by_strategy": breakdown_strategy,
        "breakdown_by_symbol": breakdown_symbol
    }

