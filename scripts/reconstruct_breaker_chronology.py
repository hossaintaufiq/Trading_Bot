"""
Reconstruct exact chronology of Risk Breaker events for Milestone 4.6.3.1.3 Audit C.
"""
import json
import os
from decimal import Decimal

def main():
    equity_curves_path = "storage/exports/milestone_4_6_3_1_2/equity_curves.json"
    trades_path = "storage/exports/milestone_4_6_3_1_2/trade_ledger_reproduction.json"
    risk_events_path = "storage/exports/milestone_4_6_3_1_2/risk_breaker_events.json"
    
    print("Loading equity curves...")
    with open(equity_curves_path, "r", encoding="utf-8") as f:
        curves = json.load(f)
        
    print("Loading trades...")
    with open(trades_path, "r", encoding="utf-8") as f:
        trades_data = json.load(f)
        
    print("Loading risk breaker events...")
    with open(risk_events_path, "r", encoding="utf-8") as f:
        risk_events = json.load(f)
        
    results = {}
    
    for grp_key in ["GROUP_A", "GROUP_B", "GROUP_C", "GROUP_D"]:
        curve = curves[grp_key]
        grp_trades = trades_data[grp_key]
        
        # Track peak, find first >= 5% dd
        peak_eq = Decimal("1000.0")
        first_breach = None
        max_dd = Decimal("0.0")
        max_dd_point = None
        
        breach_idx = None
        
        for idx, pt in enumerate(curve):
            tot_eq = Decimal(str(pt["total_equity"]))
            if tot_eq > peak_eq:
                peak_eq = tot_eq
            dd = (peak_eq - tot_eq) / peak_eq * Decimal("100.0")
            if dd > max_dd:
                max_dd = dd
                max_dd_point = pt
                
            if dd >= Decimal("5.0") and first_breach is None:
                first_breach = pt
                first_breach["peak_equity_at_breach"] = float(peak_eq)
                first_breach["calculated_dd_pct"] = float(dd)
                first_breach["index"] = idx
                breach_idx = idx
                
        # Find trades that were open at breach
        breach_ts = first_breach["timestamp"] if first_breach else None
        open_at_breach = []
        trades_entered_after_breach = []
        
        for t in grp_trades:
            entry_ts = t.get("entry_timestamp")
            exit_ts = t.get("exit_timestamp")
            if entry_ts and exit_ts:
                if entry_ts <= breach_ts and exit_ts > breach_ts:
                    open_at_breach.append(t)
                elif entry_ts > breach_ts:
                    trades_entered_after_breach.append(t)
                    
        # Identify the window of 20 bars around breach
        window_start = max(0, breach_idx - 5) if breach_idx else 0
        window_end = min(len(curve), breach_idx + 25) if breach_idx else 30
        sub_curve = curve[window_start:window_end]
        
        results[grp_key] = {
            "first_breach": first_breach,
            "max_dd_reached": float(max_dd),
            "max_dd_point": max_dd_point,
            "open_trades_at_breach": open_at_breach,
            "trades_entered_after_breach": trades_entered_after_breach,
            "total_trades": len(grp_trades),
            "final_equity": curve[-1]["total_equity"],
            "sub_curve_around_breach": sub_curve,
        }
        
    out_path = "storage/exports/milestone_4_6_3_1_3/risk_breaker_chronology.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved risk breaker chronology to {out_path}")

if __name__ == "__main__":
    main()
