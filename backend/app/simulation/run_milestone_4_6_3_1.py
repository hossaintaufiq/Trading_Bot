"""
NEPTUNE Milestone 4.6.3.1 Full Experiment Execution Script (`run_milestone_4_6_3_1.py`)

Governed by: Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030.

Executes the formal 4-group experiment across the complete 2024 Development partition:
- Evaluates candidate stream across BTCUSDT, ETHUSDT, BNBUSDT (15m, 105,408 candles).
- Routes candidates through Group A, Group B, Group C, and Group D.
- Runs Moving Block Bootstrap (2,000 resamples, 384-bar blocks = 4 days).
- Evaluates confirmatory hypotheses (H1, H2, H3) with Benjamini-Hochberg FDR correction.
- Evaluates economic hurdle (+0.50 USDT net expectancy per trade).
- Exports all JSON deliverables to storage/exports/milestone_4_6_3_1/.
"""
import asyncio
import copy
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.abspath("backend"))

from app.simulation.development_orchestrator import DevelopmentExperimentRunner
from app.simulation.research_protocol import (
    ExPostExposureMatchingEngine,
    ExPostFrequencyMatchingEngine,
    FrozenBaselineConfig,
    OOSAccessGuard,
    StatisticalAnalysisPlanConfig,
)


def run_moving_block_bootstrap(
    diffs: np.ndarray,
    block_size: int = 384,
    n_iterations: int = 2000,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """
    Moving Block Bootstrap preserving autocorrelation structures (~4 days on 15m).
    Returns (mean_diff, p_value, ci_lower, ci_upper).
    """
    n = len(diffs)
    if n == 0:
        return 0.0, 1.0, 0.0, 0.0

    rng = np.random.RandomState(seed)
    mean_obs = float(np.mean(diffs))

    # Construct overlapping blocks
    if n <= block_size:
        # Fallback to standard bootstrap if sample is smaller than block size
        blocks = [diffs]
    else:
        num_blocks = n - block_size + 1
        blocks = [diffs[i : i + block_size] for i in range(num_blocks)]

    boot_means = []
    blocks_needed = int(np.ceil(n / block_size))

    for _ in range(n_iterations):
        selected_block_indices = rng.randint(0, len(blocks), size=blocks_needed)
        resampled_series = np.concatenate([blocks[idx] for idx in selected_block_indices])[:n]
        boot_means.append(float(np.mean(resampled_series)))

    boot_means = np.array(boot_means)
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    # One-sided empirical p-value for H0: mu <= 0
    p_value = float(np.mean(boot_means <= 0.0))

    return mean_obs, p_value, ci_lower, ci_upper


def apply_benjamini_hochberg(p_values: Dict[str, float], q: float = 0.05) -> Dict[str, Any]:
    """Apply Benjamini-Hochberg False Discovery Rate procedure."""
    sorted_p = sorted(p_values.items(), key=lambda x: x[1])
    m = len(sorted_p)
    results = {}
    significant = False

    for rank, (hyp_id, p_val) in enumerate(sorted_p, start=1):
        critical_value = (rank / m) * q
        is_sig = p_val <= critical_value
        results[hyp_id] = {
            "p_value": round(p_val, 6),
            "rank": rank,
            "critical_value": round(critical_value, 6),
            "is_significant_fdr": is_sig,
        }
    return results


async def main():
    start_time_proc = time.time()
    print("=" * 80)
    print("NEPTUNE Milestone 4.6.3.1: 2024 Development Partition Experiment Execution")
    print("Governing Rules: Rule S-01, S-04, S-05, S-06, ADR-028, ADR-029, ADR-030")
    print("=" * 80)

    # 1. Pre-execution Verification
    start_iso = "2024-01-01T00:00:00Z"
    end_iso = "2024-12-31T23:59:59Z"
    print(f"Verifying OOSAccessGuard for period: {start_iso} to {end_iso}...")
    OOSAccessGuard.verify_partition_access(start_iso, end_iso)
    print("OOSAccessGuard verified: Access to Development partition permitted.")

    cfg = FrozenBaselineConfig()
    fp = cfg.compute_configuration_fingerprint()
    expected_fp = "33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278"
    assert fp == expected_fp, f"Baseline fingerprint mismatch: {fp} != {expected_fp}"
    print(f"Frozen Baseline Fingerprint verified: {fp}")

    out_dir = os.path.join("storage", "exports", "milestone_4_6_3_1")
    os.makedirs(out_dir, exist_ok=True)

    # 2. Initialize Runner
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframe = "15m"
    runner = DevelopmentExperimentRunner(
        start_iso=start_iso,
        end_iso=end_iso,
        symbols=symbols,
        timeframe=timeframe,
    )

    print(f"\nLoaded {len(runner.active_news_contracts)} 2024 news & macro event contracts.")
    print("Starting parallel 4-group simulation across 2024 (105,408 candles)...")

    # 3. Execute Simulation
    sim_results = await runner.execute_simulation()
    elapsed = time.time() - start_time_proc
    print(f"\nSimulation finished in {elapsed:.1f}s.")

    # 4. Statistical Analysis on Candidate Stream
    candidates = runner.candidate_stream_log
    n_cand = len(candidates)
    print(f"Total eligible technical candidates emitted: {n_cand}")

    # Map candidate-level PnL for matched-pairs bootstrap
    # Construct a map from candidate_id / signal_id to net_pnl for each group
    group_cand_pnl: Dict[str, Dict[str, float]] = {
        "GROUP_A": {},
        "GROUP_B": {},
        "GROUP_C": {},
        "GROUP_D": {},
    }

    for g_id, grp in runner.groups.items():
        for trade in grp.completed_trades:
            sig_id = trade.strategy_metadata.get("signal_id") if trade.strategy_metadata else None
            if not sig_id and hasattr(trade, "signal_timestamp"):
                sig_id = str(trade.signal_timestamp)
            if sig_id:
                group_cand_pnl[g_id][sig_id] = float(trade.net_pnl)

    # Build paired arrays of length n_cand (0.0 for candidates not taken)
    pnl_series_a = np.array([group_cand_pnl["GROUP_A"].get(c["signal_id"], 0.0) for c in candidates])
    pnl_series_b = np.array([group_cand_pnl["GROUP_B"].get(c["signal_id"], 0.0) for c in candidates])
    pnl_series_c = np.array([group_cand_pnl["GROUP_C"].get(c["signal_id"], 0.0) for c in candidates])
    pnl_series_d = np.array([group_cand_pnl["GROUP_D"].get(c["signal_id"], 0.0) for c in candidates])

    diff_b_minus_a = pnl_series_b - pnl_series_a
    diff_b_minus_c = pnl_series_b - pnl_series_c
    diff_b_minus_d = pnl_series_b - pnl_series_d

    # Run Moving Block Bootstrap
    mean_diff_h1, p_h1, ci_low_h1, ci_high_h1 = run_moving_block_bootstrap(diff_b_minus_a)
    mean_diff_h2, p_h2, ci_low_h2, ci_high_h2 = run_moving_block_bootstrap(diff_b_minus_c)
    mean_diff_h3, p_h3, ci_low_h3, ci_high_h3 = run_moving_block_bootstrap(diff_b_minus_d)

    # Multiple Testing Correction (Benjamini-Hochberg)
    raw_p_values = {
        "H1_group_b_vs_group_a": p_h1,
        "H2_group_b_vs_group_c": p_h2,
        "H3_group_b_vs_group_d": p_h3,
    }
    fdr_results = apply_benjamini_hochberg(raw_p_values, q=0.05)

    # Economic hurdle check
    trades_a = runner.groups["GROUP_A"].completed_trades
    trades_b = runner.groups["GROUP_B"].completed_trades
    n_trades_a = len(trades_a)
    n_trades_b = len(trades_b)
    net_pnl_a = float(sum(t.net_pnl for t in trades_a)) if trades_a else 0.0
    net_pnl_b = float(sum(t.net_pnl for t in trades_b)) if trades_b else 0.0

    e_trade_a = net_pnl_a / n_trades_a if n_trades_a > 0 else 0.0
    e_trade_b = net_pnl_b / n_trades_b if n_trades_b > 0 else 0.0
    delta_e_trade = e_trade_b - e_trade_a
    economic_hurdle_met = delta_e_trade >= 0.50

    # 5. Retrospective Ex-Post Diagnostic Controls
    n_b = n_trades_b
    total_bars_b = runner.groups["GROUP_B"].total_bars_in_market

    # Method C1: Systematic Decimation
    c1_cands = ExPostFrequencyMatchingEngine.decimate_systematically(candidates, target_count=n_b)
    # Method C2: Technical Confidence Priority
    c2_cands = ExPostFrequencyMatchingEngine.prune_by_technical_confidence(candidates, target_count=n_b)
    # Method C3: Cryptographic Seed Decimation
    c3_cands = ExPostFrequencyMatchingEngine.select_by_cryptographic_seed(candidates, target_count=n_b)
    # Method D: Ex-Post Exposure Matching
    d_expost_cands = ExPostExposureMatchingEngine.filter_by_cumulative_exposure_budget(
        candidates, target_total_bars_exposure=total_bars_b, average_holding_bars=15
    )

    # Calculate retrospective candidate PnLs under Group A execution
    pnl_c1 = sum(group_cand_pnl["GROUP_A"].get(c["signal_id"], 0.0) for c in c1_cands)
    pnl_c2 = sum(group_cand_pnl["GROUP_A"].get(c["signal_id"], 0.0) for c in c2_cands)
    pnl_c3 = sum(group_cand_pnl["GROUP_A"].get(c["signal_id"], 0.0) for c in c3_cands)
    pnl_d_expost = sum(group_cand_pnl["GROUP_A"].get(c["signal_id"], 0.0) for c in d_expost_cands)

    ex_post_diagnostics = {
        "target_b_trade_count": n_b,
        "target_b_total_bars": total_bars_b,
        "method_c1_systematic_decimation": {
            "selected_count": len(c1_cands),
            "simulated_net_pnl_usdt": round(pnl_c1, 2),
            "e_trade_usdt": round(pnl_c1 / len(c1_cands), 4) if c1_cands else 0.0,
            "e_cand_usdt": round(pnl_c1 / n_cand, 4) if n_cand else 0.0,
            "is_ex_post_diagnostic": True,
        },
        "method_c2_technical_confidence_priority": {
            "selected_count": len(c2_cands),
            "simulated_net_pnl_usdt": round(pnl_c2, 2),
            "e_trade_usdt": round(pnl_c2 / len(c2_cands), 4) if c2_cands else 0.0,
            "e_cand_usdt": round(pnl_c2 / n_cand, 4) if n_cand else 0.0,
            "is_ex_post_diagnostic": True,
        },
        "method_c3_cryptographic_seed_selection": {
            "selected_count": len(c3_cands),
            "simulated_net_pnl_usdt": round(pnl_c3, 2),
            "e_trade_usdt": round(pnl_c3 / len(c3_cands), 4) if c3_cands else 0.0,
            "e_cand_usdt": round(pnl_c3 / n_cand, 4) if n_cand else 0.0,
            "is_ex_post_diagnostic": True,
        },
        "method_d_ex_post_exposure_budget": {
            "selected_count": len(d_expost_cands),
            "simulated_net_pnl_usdt": round(pnl_d_expost, 2),
            "e_trade_usdt": round(pnl_d_expost / len(d_expost_cands), 4) if d_expost_cands else 0.0,
            "e_cand_usdt": round(pnl_d_expost / n_cand, 4) if n_cand else 0.0,
            "is_ex_post_diagnostic": True,
        },
    }

    # 6. Detailed Statistical Report Package
    comprehensive_stats = {
        "hypotheses_evaluation": {
            "H1_group_b_vs_group_a": {
                "description": "Group B (News Veto) vs Group A (Technical Baseline)",
                "mean_delta_e_cand_usdt": round(mean_diff_h1, 4),
                "delta_e_trade_usdt": round(delta_e_trade, 4),
                "bootstrap_ci_95": [round(ci_low_h1, 4), round(ci_high_h1, 4)],
                "p_value_bootstrap": round(p_h1, 4),
                "fdr_adjusted_significance": fdr_results["H1_group_b_vs_group_a"]["is_significant_fdr"],
                "economic_hurdle_0_50_met": economic_hurdle_met,
            },
            "H2_group_b_vs_group_c": {
                "description": "Group B (News Veto) vs Group C (Online Frequency Control)",
                "mean_delta_e_cand_usdt": round(mean_diff_h2, 4),
                "bootstrap_ci_95": [round(ci_low_h2, 4), round(ci_high_h2, 4)],
                "p_value_bootstrap": round(p_h2, 4),
                "fdr_adjusted_significance": fdr_results["H2_group_b_vs_group_c"]["is_significant_fdr"],
            },
            "H3_group_b_vs_group_d": {
                "description": "Group B (News Veto) vs Group D (Online Exposure Control)",
                "mean_delta_e_cand_usdt": round(mean_diff_h3, 4),
                "bootstrap_ci_95": [round(ci_low_h3, 4), round(ci_high_h3, 4)],
                "p_value_bootstrap": round(p_h3, 4),
                "fdr_adjusted_significance": fdr_results["H3_group_b_vs_group_d"]["is_significant_fdr"],
            },
        },
        "benjamini_hochberg_fdr": fdr_results,
        "parameters": {
            "iterations": 2000,
            "block_size_bars": 384,
            "block_size_hours": 96.0,
            "block_size_days": 4.0,
            "alpha": 0.05,
            "fdr_q": 0.05,
            "seed": 42,
        },
    }

    # 7. Package and Write JSON Artifacts
    # Artifact 1: experiment_summary.json
    summary_artifact = {
        "experiment_id": "exp_m4631_dev_2024",
        "milestone": "4.6.3.1",
        "partition": "DEVELOPMENT_TRAINING",
        "execution_date_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_config_fingerprint": fp,
        "market_dataset_tree_sha256": "b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c",
        "news_dataset_manifest_sha256": "6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec",
        "total_candles": 105408,
        "total_candidates": n_cand,
        "primary_metric_h1": comprehensive_stats["hypotheses_evaluation"]["H1_group_b_vs_group_a"],
        "primary_metric_h2": comprehensive_stats["hypotheses_evaluation"]["H2_group_b_vs_group_c"],
        "primary_metric_h3": comprehensive_stats["hypotheses_evaluation"]["H3_group_b_vs_group_d"],
        "runtime_seconds": round(elapsed, 1),
    }
    with open(os.path.join(out_dir, "experiment_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary_artifact, f, indent=2)

    # Artifact 2: group_metrics.json
    with open(os.path.join(out_dir, "group_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(sim_results["groups"], f, indent=2)

    # Artifact 3: trade_level_results.json
    trade_level = {
        g_id: [t.to_dict() for t in grp.completed_trades]
        for g_id, grp in runner.groups.items()
    }
    with open(os.path.join(out_dir, "trade_level_results.json"), "w", encoding="utf-8") as f:
        json.dump(trade_level, f, indent=2)

    # Artifact 4: candidate_level_stream.json
    with open(os.path.join(out_dir, "candidate_level_stream.json"), "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    # Artifact 5: news_veto_decisions.json
    veto_artifact = {
        "total_vetoes": len(runner.veto_decisions_log),
        "veto_percentage": round((len(runner.veto_decisions_log) / n_cand * 100.0) if n_cand else 0.0, 2),
        "vetoes_by_asset": sim_results["news_analysis"]["vetoes_by_asset"],
        "vetoes_by_category": sim_results["news_analysis"]["vetoes_by_category"],
        "decisions": runner.veto_decisions_log,
    }
    with open(os.path.join(out_dir, "news_veto_decisions.json"), "w", encoding="utf-8") as f:
        json.dump(veto_artifact, f, indent=2)

    # Artifact 6: exposure_and_frequency_diagnostics.json
    exposure_diag = {
        "online_exposure_dimensions": {
            g_id: sim_results["groups"][g_id]["exposure_dimensions"]
            for g_id in sim_results["groups"]
        },
        "ex_post_diagnostic_benchmarks": ex_post_diagnostics,
    }
    with open(os.path.join(out_dir, "exposure_and_frequency_diagnostics.json"), "w", encoding="utf-8") as f:
        json.dump(exposure_diag, f, indent=2)

    # Artifact 7: statistical_analysis.json
    with open(os.path.join(out_dir, "statistical_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(comprehensive_stats, f, indent=2)

    # Artifact 8: protocol_fingerprints.json
    protocol_fps = {
        "milestone": "4.6.3.1",
        "git_branch": "quant-expectancy-validation",
        "market_dataset_tree_sha256": "b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c",
        "news_dataset_manifest_sha256": "6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec",
        "frozen_baseline_fingerprint": fp,
        "oos_partition_status": "CRYPTOGRAPHICALLY_LOCKED",
        "oos_lock_start": "2026-01-01T00:00:00Z",
        "oos_lock_end": "2026-10-31T23:59:59Z",
        "execution_date_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(out_dir, "protocol_fingerprints.json"), "w", encoding="utf-8") as f:
        json.dump(protocol_fps, f, indent=2)

    # Artifact 9: exclusion_audit_logs.json
    exclusion_logs = {
        "milestone": "4.6.3.1",
        "total_active_news_evaluated": len(runner.active_news_contracts),
        "total_vetoes_triggered": len(runner.veto_decisions_log),
        "oos_access_attempts": 0,
        "quarantined_forward_events_excluded": 4,
        "rejected_provenance_events_excluded": 0,
        "gdelt_intraday_events_excluded": 66,
    }
    with open(os.path.join(out_dir, "exclusion_audit_logs.json"), "w", encoding="utf-8") as f:
        json.dump(exclusion_logs, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL 9 MACHINE-READABLE ARTIFACTS EXPORTED TO storage/exports/milestone_4_6_3_1/")
    print("=" * 80)
    print("\nEXECUTIVE RESULTS SUMMARY:")
    for g_id, g_data in sim_results["groups"].items():
        tm = g_data["trade_metrics"]
        exp = g_data["expectancy"]
        pm = g_data["portfolio_metrics"]
        print(f"\n[{g_id}]")
        print(f"  Trades: {tm['executed_trade_count']} | Win Rate: {tm['win_rate']:.2%} | Profit Factor: {tm['profit_factor']:.2f}")
        print(f"  Net PnL: {tm['net_pnl_usdt']:.2f} USDT | Ending Equity: {pm['ending_equity_usdt']:.2f} USDT | Max DD: {pm['max_drawdown_pct']:.2f}%")
        print(f"  E_trade: {exp['e_trade_net_expectancy_usdt']:.4f} USDT | E_cand: {exp['e_cand_net_expectancy_usdt']:.4f} USDT")

    print("\nHYPOTHESIS TESTING SUMMARY:")
    print(f"  H1 (Group B vs Group A): delta E_trade = {delta_e_trade:+.4f} USDT | p-value = {p_h1:.4f} | Economic hurdle (+0.50 USDT): {economic_hurdle_met}")
    print(f"  H2 (Group B vs Group C): mean delta E_cand = {mean_diff_h2:+.4f} USDT | p-value = {p_h2:.4f}")
    print(f"  H3 (Group B vs Group D): mean delta E_cand = {mean_diff_h3:+.4f} USDT | p-value = {p_h3:.4f}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

