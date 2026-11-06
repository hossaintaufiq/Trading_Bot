# NEPTUNE — Milestone 4.6.3.1
## Experiment Reproduction Guide: 2024 Development Partition

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.3.1  
**Target:** Independent Bit-for-Bit Reproduction of Development Partition Results  
**Governing Rules:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030  

---

## 1. Prerequisites and Environment Verification

Before executing the simulation, independently verify repository cleanliness and cryptographic baselines:

```bash
# 1. Verify Git branch and status
git status
# Branch must be quant-expectancy-validation, clean working tree

# 2. Verify pre-execution fingerprints using python
python -c "
import json, hashlib
from app.simulation.research_protocol import FrozenBaselineConfig, OOSAccessGuard

# Verify baseline config fingerprint
cfg = FrozenBaselineConfig()
fp = cfg.compute_configuration_fingerprint()
expected_fp = '33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278'
assert fp == expected_fp, f'Fingerprint mismatch: {fp}'

# Verify OOS Guard blocks locked partition
try:
    OOSAccessGuard.verify_partition_access('2026-03-01T00:00:00Z', '2026-06-01T00:00:00Z')
    raise AssertionError('OOS guard failed to block!')
except PermissionError:
    pass

print('All cryptographic pre-flight checks passed.')
"
```

---

## 2. Command Execution

To reproduce the complete 4-group simulation across the 2024 Development partition:

```bash
# From workspace root
python backend/app/simulation/run_milestone_4_6_3_1.py
```

### Expected Output Summary

```
================================================================================
NEPTUNE Milestone 4.6.3.1: 2024 Development Partition Experiment Execution
Governing Rules: Rule S-01, S-04, S-05, S-06, ADR-028, ADR-029, ADR-030
================================================================================
Verifying OOSAccessGuard for period: 2024-01-01T00:00:00Z to 2024-12-31T23:59:59Z...
OOSAccessGuard verified: Access to Development partition permitted.
Frozen Baseline Fingerprint verified: 33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278

Loaded 380 2024 news & macro event contracts.
Starting parallel 4-group simulation across 2024 (105,408 candles)...
```

---

## 3. Output Artifact Locations

All machine-readable experimental deliverables are persisted to:
`storage/exports/milestone_4_6_3_1/`

| File | Contents |
|------|----------|
| `experiment_summary.json` | High-level execution metadata, runtime, and primary hypothesis results. |
| `group_metrics.json` | Full trade, portfolio, and expectancy metrics for Groups A, B, C, D. |
| `trade_level_results.json` | Discrete trade ledger for all completed positions with fill prices and PnL. |
| `candidate_level_stream.json` | Complete stream of eligible technical candidate setups emitted in 2024. |
| `news_veto_decisions.json` | Detailed audit log of every news veto, triggering article, and rationale. |
| `exposure_and_frequency_diagnostics.json` | 7-dimensional exposure comparison and ex-post diagnostic benchmarks. |
| `statistical_analysis.json` | Moving block bootstrap resample distributions, CI, p-values, FDR table. |
| `protocol_fingerprints.json` | Cryptographic hashes freezing git, datasets, configurations, and partitions. |
| `exclusion_audit_logs.json` | Audit log of quarantined forward events and GDELT intraday exclusions. |

---

## 4. Verification of Frozen Baselines

Confirm that the historical data files remain bit-for-bit unchanged:

- Market Dataset v2.0.0 Tree SHA-256:
  `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`
- News Dataset v2.0.0 Manifest SHA-256:
  `6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec`
- Frozen Baseline Configuration Fingerprint:
  `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`

