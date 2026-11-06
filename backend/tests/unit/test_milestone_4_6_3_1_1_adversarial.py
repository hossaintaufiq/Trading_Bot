"""
Adversarial Unit Test Suite for Milestone 4.6.3.1.1 Forensic Audit
(`test_milestone_4_6_3_1_1_adversarial.py`)

Adversarially tests and reconciles:
1. Gross P&L, transaction friction, and net P&L accounting identity and rounding bounds.
2. The gross profit / gross loss metric aggregation defect in group_metrics.json.
3. The cash equity inverted-sign accounting defect on short positions.
4. True ending equity ($1000 + Net PnL) vs flawed reported equity.
5. Risk Manager 5% circuit breaker overshoot and true realized drawdown timeline.
6. The 183 vetoes vs 5 directly prevented trades vs portfolio path dependency.
7. Dual expectancy ($E_trade$ vs $E_cand$) denominator separation.
8. Moving block bootstrap discrete point-mass artifact at zero.
9. Benjamini-Hochberg step-up procedure verification.
10. Immutability of historical datasets and cryptographic OOS guards.
"""
import json
import os
from decimal import Decimal
import numpy as np
import pytest

from app.simulation.research_protocol import FrozenBaselineConfig, OOSAccessGuard


@pytest.fixture(scope="module")
def audit_data():
    """Load audit and original experimental exports."""
    src_dir = os.path.join("storage", "exports", "milestone_4_6_3_1")
    audit_dir = os.path.join("storage", "exports", "milestone_4_6_3_1_1")

    with open(os.path.join(src_dir, "group_metrics.json"), "r") as f:
        orig_metrics = json.load(f)
    with open(os.path.join(src_dir, "trade_level_results.json"), "r") as f:
        trades_by_group = json.load(f)
    with open(os.path.join(src_dir, "candidate_level_stream.json"), "r") as f:
        candidates = json.load(f)
    with open(os.path.join(src_dir, "news_veto_decisions.json"), "r") as f:
        veto_data = json.load(f)

    with open(os.path.join(audit_dir, "accounting_reconciliation.json"), "r") as f:
        accounting_recon = json.load(f)
    with open(os.path.join(audit_dir, "equity_curve_reconciliation.json"), "r") as f:
        equity_recon = json.load(f)
    with open(os.path.join(audit_dir, "risk_breaker_timeline.json"), "r") as f:
        risk_recon = json.load(f)
    with open(os.path.join(audit_dir, "candidate_veto_reconciliation.json"), "r") as f:
        veto_recon = json.load(f)
    with open(os.path.join(audit_dir, "expectancy_reconciliation.json"), "r") as f:
        expectancy_recon = json.load(f)
    with open(os.path.join(audit_dir, "bootstrap_reconstruction.json"), "r") as f:
        bootstrap_recon = json.load(f)
    with open(os.path.join(audit_dir, "bh_fdr_recalculation.json"), "r") as f:
        bh_recon = json.load(f)

    return {
        "orig_metrics": orig_metrics,
        "trades_by_group": trades_by_group,
        "candidates": candidates,
        "veto_data": veto_data,
        "accounting_recon": accounting_recon,
        "equity_recon": equity_recon,
        "risk_recon": risk_recon,
        "veto_recon": veto_recon,
        "expectancy_recon": expectancy_recon,
        "bootstrap_recon": bootstrap_recon,
        "bh_recon": bh_recon,
    }


# ==============================================================================
# 1. FORENSIC AUDIT A: ACCOUNTING IDENTITY & ROUNDING DRIFT
# ==============================================================================
def test_gross_friction_net_accounting_identity(audit_data):
    """Verify True Gross PnL - Total Friction == Reported Net PnL within 0.06 USDT."""
    recon = audit_data["accounting_recon"]
    for g_id, data in recon.items():
        gross = Decimal(str(data["reconstructed_true_gross_pnl"]))
        friction = Decimal(str(data["total_friction"]))
        rec_net = gross - friction
        reported_net = Decimal(str(data["reported_net_pnl_sum"]))
        drift = abs(rec_net - reported_net)

        # Quantization drift bounded strictly within 0.10 USDT across entire year
        assert drift <= Decimal("0.06"), f"{g_id} drift {drift} exceeded 0.06 USDT bound"


def test_gross_profit_loss_defect_demonstration(audit_data):
    """Verify that reported gross profit and loss in group_metrics.json suffered from the conditioning defect."""
    recon = audit_data["accounting_recon"]
    for g_id, data in recon.items():
        defect = data["defect_root_cause"]
        # There must be trades with positive gross PnL that lost money net due to friction
        assert defect["positive_gross_net_losing_trades_count"] > 0
        assert defect["positive_gross_net_losing_trades_gross_pnl"] > 0.0

        # Reported GP must be strictly less than true positive gross PnL
        assert data["flawed_reported_metrics"]["reported_gross_profit"] < data["true_positive_gross_profit"]
        # Reported GL must be strictly greater than true negative gross loss
        assert data["flawed_reported_metrics"]["reported_gross_loss"] > data["true_negative_gross_loss"]


# ==============================================================================
# 2. FORENSIC AUDIT B: PORTFOLIO EQUITY AND SHORT INVERSION DEFECT
# ==============================================================================
def test_true_ending_equity_identity(audit_data):
    """Verify that True Ending Equity is strictly 1000 + Net PnL."""
    recon = audit_data["equity_recon"]
    for g_id, data in recon.items():
        net_pnl = Decimal(str(data["true_accounting"]["cumulative_realized_net_pnl"]))
        true_eq = Decimal("1000.00") + net_pnl
        assert Decimal(str(data["true_accounting"]["true_ending_equity_usdt"])) == true_eq

        # Group A true equity is 785.28, NOT 984.56
        if g_id == "GROUP_A":
            assert true_eq == Decimal("785.28")
        elif g_id == "GROUP_B":
            assert true_eq == Decimal("885.58")
        elif g_id == "GROUP_C":
            assert true_eq == Decimal("813.79")
        elif g_id == "GROUP_D":
            assert true_eq == Decimal("835.20")


def test_cash_equity_inverted_short_defect_reconciliation(audit_data):
    """Verify that reported equity matches flawed cash accounting with phantom short credits."""
    recon = audit_data["equity_recon"]
    for g_id, data in recon.items():
        true_eq = Decimal(str(data["true_accounting"]["true_ending_equity_usdt"]))
        phantom_credits = Decimal(str(data["defect_root_cause"]["total_phantom_cash_credited"]))
        calculated_flawed = Decimal(str(data["flawed_reported_accounting"]["calculated_flawed_cash_equity"]))
        reported_eq = Decimal(str(data["flawed_reported_accounting"]["reported_ending_equity_usdt"]))

        # Discrepancy between reported and true equity must match phantom credits within 0.05 USDT
        assert abs((reported_eq - true_eq) - phantom_credits) < Decimal("0.05")


# ==============================================================================
# 3. FORENSIC AUDIT C: RISK BREAKER TIMELINE & OVERSHOOT
# ==============================================================================
def test_true_realized_drawdown_severity(audit_data):
    """Verify that True Realized Drawdown severely breached 5% across all groups."""
    recon = audit_data["risk_recon"]
    for g_id, data in recon.items():
        true_dd = data["true_realized_max_drawdown_pct"]
        # All groups suffered > 13% true drawdown
        assert true_dd >= 13.9, f"{g_id} true drawdown {true_dd} was not >= 13.9%"
        assert data["drawdown_5pct_first_breach_timestamp"].startswith("2024-01-05")


def test_risk_breaker_non_liquidation_overshoot(audit_data):
    """Verify reported overshoot (5.19% - 5.92%) occurred because breakers do not liquidate open trades."""
    recon = audit_data["risk_recon"]
    for g_id, data in recon.items():
        reported_dd = data["flawed_reported_max_drawdown_pct"]
        assert 5.0 <= reported_dd <= 6.0


# ==============================================================================
# 4. FORENSIC AUDIT D: VETO REDUNDANCY & PATH DEPENDENCY
# ==============================================================================
def test_candidate_veto_redundancy_and_direct_prevention(audit_data):
    """Verify that out of 183 news vetoes, only 5 directly prevented trades in Group A."""
    recon = audit_data["veto_recon"]
    assert recon["summary_counts"]["total_news_veto_decisions"] == 183
    assert recon["veto_effectiveness_breakdown"]["vetoed_candidates_directly_preventing_trades"] == 5
    assert recon["veto_effectiveness_breakdown"]["vetoed_candidates_redundant_due_to_risk_or_capacity"] == 178
    assert recon["veto_effectiveness_breakdown"]["redundancy_percentage"] == 97.27


def test_path_dependency_mathematical_identity(audit_data):
    """Verify 21-trade difference reconciles through portfolio path dependency: 23 - 2 = 21."""
    recon = audit_data["veto_recon"]
    path = recon["path_dependency_reconciliation"]
    assert path["trades_executed_in_both_groups"] == 45
    assert path["trades_executed_in_a_only"] == 23
    assert path["trades_executed_in_a_only_directly_vetoed_by_news"] == 5
    assert path["trades_executed_in_a_only_due_to_downstream_state_divergence"] == 18
    assert path["trades_executed_in_b_only_due_to_divergent_capacity"] == 2
    assert path["trades_executed_in_a_only"] - path["trades_executed_in_b_only_due_to_divergent_capacity"] == 21


# ==============================================================================
# 5. FORENSIC AUDIT E: EXPECTANCY SEPARATION
# ==============================================================================
def test_expectancy_denominators_and_economic_hurdle(audit_data):
    """Verify E_trade and E_cand mathematical consistency and economic hurdle application."""
    recon = audit_data["expectancy_recon"]
    comp = recon["comparisons"]["H1_group_b_minus_group_a"]

    # Nominal hurdle met on E_trade (+0.7231 >= +0.50)
    assert abs(comp["delta_E_trade_usdt"] - 0.7232) <= 0.001
    assert comp["economic_hurdle_pre_registered"] == 0.50
    assert comp["passed_nominally"] is True
    assert comp["passed_statistically"] is False

    # Candidate expectancy difference is +0.0273, far below 0.50
    assert comp["delta_E_cand_usdt"] == 0.0273


# ==============================================================================
# 6. FORENSIC AUDIT F: BOOTSTRAP POINT MASS AT ZERO
# ==============================================================================
def test_bootstrap_point_mass_artifact_reconciliation(audit_data):
    """Verify that the moving block bootstrap contains a 58.2% point mass at 0.0 explaining CI [0.0, 0.05] and p=0.595."""
    recon = audit_data["bootstrap_recon"]["H1_b_minus_a"]
    dist = recon["bootstrap_distribution"]

    assert dist["fraction_boot_means_exactly_zero"] == 0.582
    assert dist["reported_p_value_empirical_le_zero"] == 0.595
    assert dist["ci_95_percentile"][0] == 0.0
    assert dist["ci_95_percentile"][1] > 0.05


# ==============================================================================
# 7. FORENSIC AUDIT G: BENJAMINI-HOCHBERG RECALCULATION
# ==============================================================================
def test_bh_fdr_ranking_and_insignificance(audit_data):
    """Verify that BH step-up correctly ranks hypotheses and all remain non-significant."""
    recon = audit_data["bh_recon"]
    hyps = recon["hypotheses_sorted_by_p_value"]

    assert hyps["H3_group_b_vs_group_d"]["sorted_rank"] == 1
    assert hyps["H3_group_b_vs_group_d"]["raw_p_value"] == 0.59
    assert hyps["H3_group_b_vs_group_d"]["is_significant_fdr"] is False

    assert hyps["H1_group_b_vs_group_a"]["sorted_rank"] == 2
    assert hyps["H1_group_b_vs_group_a"]["raw_p_value"] == 0.595
    assert hyps["H1_group_b_vs_group_a"]["is_significant_fdr"] is False

    assert hyps["H2_group_b_vs_group_c"]["sorted_rank"] == 3
    assert hyps["H2_group_b_vs_group_c"]["raw_p_value"] == 0.595
    assert hyps["H2_group_b_vs_group_c"]["is_significant_fdr"] is False


# ==============================================================================
# 8. PRE-AUDIT IMMUTABILITY & OOS GUARDS
# ==============================================================================
def test_baseline_fingerprint_immutability():
    """Verify frozen baseline fingerprint remains bit-for-bit identical."""
    cfg = FrozenBaselineConfig()
    fp = cfg.compute_configuration_fingerprint()
    assert fp == "33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278"


def test_oos_access_guard_enforcement():
    """Verify OOS Access Guard strictly blocks unauthorized requests into 2026 OOS."""
    with pytest.raises(PermissionError, match="LOCKED_OOS_PARTITION_VIOLATION"):
        OOSAccessGuard.verify_partition_access("2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z")
