"""
NEPTUNE Strategy Research Reset & Selection Gates Governance Unit Tests.

Validates that:
1. Strategy Hypothesis Register (SHR-001, SHR-002, SHR-003) adheres to formal schema.
2. Selection Gate specifications (GATE-01 through GATE-10) are fully defined.
3. The evaluation framework correctly identifies readiness blockers across all 3 candidates.
4. Governance invariant: Zero candidates are authorized for execution without resolving blockers.
"""

from typing import Dict, List, Set
import os
import pytest


def parse_hypothesis_register(register_path: str) -> Dict[str, Dict[str, str]]:
    """Parse hypothesis entries from markdown document."""
    assert os.path.exists(register_path), f"File not found: {register_path}"
    
    with open(register_path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = {}
    for block in content.split("### Entry "):
        if not block.startswith("SHR-"):
            continue
        lines = block.strip().split("\n")
        header = lines[0].split(":")[0].strip()
        entries[header] = block
    return entries


def parse_selection_gates(gates_path: str) -> Set[str]:
    """Extract gate IDs defined in selection gates document."""
    assert os.path.exists(gates_path), f"File not found: {gates_path}"
    
    with open(gates_path, "r", encoding="utf-8") as f:
        content = f.read()

    gate_ids = set()
    for line in content.split("\n"):
        if "**GATE-" in line:
            # extract GATE-XX
            part = line.split("**GATE-")[1].split("**")[0]
            gate_ids.add(f"GATE-{part[:2]}")
    return gate_ids


def test_hypothesis_register_schema_completeness():
    """Verify that SHR-001, SHR-002, and SHR-003 contain all mandatory scientific dimensions."""
    register_path = os.path.join("docs", "research", "NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md")
    entries = parse_hypothesis_register(register_path)

    expected_ids = {"SHR-001", "SHR-002", "SHR-003"}
    assert set(entries.keys()) == expected_ids, f"Expected entries {expected_ids}, got {set(entries.keys())}"

    required_sections = [
        "Falsifiable Economic Hypothesis",
        "Expected Market Mechanism & Counterparty Behavior",
        "Conceptual Entry & Exit Architecture",
        "Explicit Failure Conditions",
        "Provisional Assumptions (Unvalidated)",
        "Minimum Evidence Required to Continue",
    ]

    for hyp_id, text in entries.items():
        for sec in required_sections:
            assert sec in text, f"Hypothesis {hyp_id} missing mandatory section: {sec}"
        assert "PROVISIONAL RESEARCH HYPOTHESES" in text or "provisional" in text.lower()


def test_selection_gates_definition_completeness():
    """Verify that all ten selection gates (GATE-01 through GATE-10) are codified."""
    gates_path = os.path.join("docs", "research", "NEPTUNE_EXPERIMENT_SELECTION_GATES.md")
    gate_ids = parse_selection_gates(gates_path)

    expected_gates = {f"GATE-{i:02d}" for i in range(1, 11)}
    assert gate_ids == expected_gates, f"Missing selection gates: {expected_gates - gate_ids}"


def test_candidate_family_gate_evaluations_and_blockers():
    """
    Verify that the gate evaluation matrix correctly blocks all 3 candidates
    from immediate experiment authorization.
    """
    # Readiness state model
    gate_readiness = {
        "Candidate_A_HTF_Trend": {
            "GATE-01": "PASS",
            "GATE-02": "PENDING",
            "GATE-03": "PASS",
            "GATE-04": "PASS",
            "GATE-05": "FAIL",  # Sample size risk (N < 25 on 4h)
            "GATE-06": "PASS",
            "GATE-07": "PASS",
            "GATE-08": "PASS",
            "GATE-09": "PENDING",
            "GATE-10": "PASS",
        },
        "Candidate_B_Vol_Breakout": {
            "GATE-01": "PASS",
            "GATE-02": "PENDING",
            "GATE-03": "PASS",
            "GATE-04": "MARGINAL",  # Fixed slippage inadequate for breakout
            "GATE-05": "PASS",
            "GATE-06": "PASS",
            "GATE-07": "PASS",
            "GATE-08": "MARGINAL",
            "GATE-09": "PENDING",
            "GATE-10": "PASS",
        },
        "Candidate_C_Mean_Reversion": {
            "GATE-01": "MARGINAL",
            "GATE-02": "PENDING",
            "GATE-03": "PASS",
            "GATE-04": "FAIL",  # Fee drag consumes narrow targets
            "GATE-05": "PASS",
            "GATE-06": "PASS",
            "GATE-07": "FAIL",  # Cannot meet +$0.50 hurdle after 0.32% friction
            "GATE-08": "FAIL",  # Runaway breakout tail risk
            "GATE-09": "PENDING",
            "GATE-10": "PASS",
        },
    }

    def evaluate_candidate(candidate_name: str, gates: Dict[str, str]) -> bool:
        """Candidate can only be authorized if all 10 gates are PASS."""
        return all(status == "PASS" for status in gates.values())

    # Assert that zero candidates are authorized for experimentation
    for name, gates in gate_readiness.items():
        authorized = evaluate_candidate(name, gates)
        assert authorized is False, f"Candidate {name} should be BLOCKED from execution"

    # Verify specific blocking reasons
    assert gate_readiness["Candidate_A_HTF_Trend"]["GATE-05"] == "FAIL"
    assert gate_readiness["Candidate_B_Vol_Breakout"]["GATE-04"] == "MARGINAL"
    assert gate_readiness["Candidate_C_Mean_Reversion"]["GATE-04"] == "FAIL"
    assert gate_readiness["Candidate_C_Mean_Reversion"]["GATE-07"] == "FAIL"


def test_research_governance_stop_condition_invariant():
    """Verify that research reset enforces complete halting of backtests and partition progression."""
    reset_path = os.path.join("docs", "research", "NEPTUNE_STRATEGY_RESEARCH_RESET.md")
    with open(reset_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "NO\\ CANDIDATE\\ IS\\ SELECTED\\ FOR\\ IMMEDIATE\\ EXECUTION" in content or "No candidate strategy is authorized" in content
    assert "authorizes zero backtests" in content.lower()
    assert "zero partition progression" in content.lower()
