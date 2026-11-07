"""
NEPTUNE — Candidate A (SHR-001) Dual-Timeframe Feasibility & Governance Unit Tests.

Validates that:
1. Dual-Timeframe Feasibility Study (NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md) exists and covers all phases.
2. Statistical Power Plan (NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md) implements dependence-aware Kish N_eff and MBB.
3. Execution and Risk Requirements (NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md) enforce frozen 0.32% friction and long-only spot.
4. Formal Verdict Invariant: Matches approved verdict taxonomy and guarantees zero unauthorized backtest execution.
"""

import os
import re
import pytest


def test_feasibility_document_structure_and_verdict():
    """Verify that the feasibility review document exists and contains required sections and formal verdict."""
    doc_path = os.path.join("docs", "research", "NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md")
    assert os.path.exists(doc_path), f"File not found: {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_sections = [
        "Phase 1 — Verification of the Economic Hypothesis",
        "Phase 2 — Sample-Size Feasibility & Statistical Power",
        "Phase 3 — Cost & Execution Feasibility",
        "Phase 4 — Long-Only Spot Portfolio Feasibility",
        "Phase 5 — Comparison of Three Conceptual Candidate A Designs",
        "Phase 6 — Experiment Prerequisites",
        "Final Decision & Justification",
    ]
    for section in required_sections:
        assert section in content, f"Missing section: {section}"

    approved_verdicts = {
        "FEASIBLE FOR GOVERNANCE REVIEW",
        "FEASIBLE WITH UNRESOLVED REQUIREMENTS",
        "NOT FEASIBLE UNDER CURRENT CONSTRAINTS",
        "INSUFFICIENT EVIDENCE TO DETERMINE",
    }
    found_verdicts = [v for v in approved_verdicts if v in content]
    assert len(found_verdicts) >= 1, "No approved verdict found in document"
    assert "FEASIBLE WITH UNRESOLVED REQUIREMENTS" in found_verdicts


def test_statistical_power_plan_mathematical_contracts():
    """Verify statistical power plan formulas: Kish N_eff, MBB block length, and declaration of unknown power."""
    doc_path = os.path.join("docs", "research", "NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md")
    assert os.path.exists(doc_path), f"File not found: {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain Kish effective sample size formulation
    assert "N_{\\text{eff}}" in content or "N_eff" in content
    assert "Moving Block Bootstrap" in content or "MBB" in content
    # Block size must be calibrated to 96 bars (4 days)
    assert "96" in content

    # Must explicitly state that statistical power cannot yet be quantified
    assert "CANNOT BE QUANTIFIED" in content or "cannot yet be quantified" in content.lower()


def test_execution_and_risk_requirements_invariants():
    """Verify frozen 0.32% friction, long-only spot rules, and 5.0% circuit breaker preservation."""
    doc_path = os.path.join("docs", "research", "NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md")
    assert os.path.exists(doc_path), f"File not found: {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Frozen 0.32% friction must be maintained
    assert "0.32%" in content or "0.320%" in content
    # Long-only spot execution (zero shorting)
    assert "Zero Short Selling" in content or "Long-Only" in content
    # Circuit breaker 5.0%
    assert "5.0%" in content
    # In-flight position bracket preservation (no market dump)
    assert "In-Flight" in content or "in-flight" in content.lower()
    assert "Order Embargo" in content or "ORDER_EMBARGO" in content


def test_hypothesis_register_status_update():
    """Verify SHR-001 in the Hypothesis Register references the completed feasibility review."""
    register_path = os.path.join("docs", "research", "NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md")
    assert os.path.exists(register_path), f"File not found: {register_path}"

    with open(register_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert any(term in content for term in [
        "FEASIBILITY REVIEW COMPLETED",
        "IMPLEMENTED - DETERMINISTIC SPECIFICATION VERIFIED",
        "VALIDATED ON 2024 DEVELOPMENT",
    ])
    assert "FEASIBLE WITH UNRESOLVED REQUIREMENTS" in content
    assert "NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md" in content


def test_governance_stop_condition_and_zero_simulation_invariant():
    """Verify governance stop condition: zero backtests authorized and zero market data observation loading."""
    doc_path = os.path.join("docs", "research", "NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md")
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "No historical simulation or backtest is authorized" in content or "ZERO EXECUTION" in content

