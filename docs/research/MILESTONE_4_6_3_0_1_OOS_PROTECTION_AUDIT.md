# NEPTUNE — Milestone 4.6.3.0.1
## Out-of-Sample Partition Protection & Access Guard Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Document:** Out-of-Sample Cryptographic Protection & Governance Audit  
**Author:** Quantitative Audit Agent  
**Governing Rules:** Rule S-05, Rule S-06, ADR-030  

---

## 1. The Threat of Out-of-Sample Snooping

In empirical finance and quantitative trading research, **data snooping bias** is the most pervasive cause of backtest overfitting. 

When researchers or automated agents have unrestricted programmatic access to test partitions during exploratory data analysis, strategy development, or bug fixing:
- Implicit parameters are unconsciously tuned to the test data.
- Strategies that happened to fail on the test data are discarded or modified.
- By the time the formal "out-of-sample test" is run, the dataset is no longer out-of-sample.

---

## 2. Chronological Partition Boundaries

Milestone 4.6.3.0 defined three chronological partitions across the 35-month frozen dataset:

```
┌──────────────────────────────────────┬──────────────────────┬───────────────────────────────┐
│        DEVELOPMENT / TRAINING        │      VALIDATION      │     LOCKED OUT-OF-SAMPLE      │
│        (2023-12-01 - 2025-06-30)     │ (2025-07-01 - 12-31) │     (2026-01-01 - 2026-10-31) │
│               19 Months              │       6 Months       │           10 Months           │
├──────────────────────────────────────┼──────────────────────┼───────────────────────────────┤
│ • Indicator calibration              │ • Protocol tuning    │ • CRYPTOGRAPHICALLY LOCKED    │
│ • Baseline parameter freezing        │ • Control validation │ • Zero access without token   │
│ • Classifier v1.1.0 training         │ • Leakage checks     │ • One-shot final evaluation   │
└──────────────────────────────────────┴──────────────────────┴───────────────────────────────┘
```

---

## 3. Implementation of `OOSAccessGuard`

In Milestone 4.6.3.0.1, NEPTUNE introduced a programmatic barrier: [`OOSAccessGuard`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py).

### Guard Logic

```python
class OOSAccessGuard:
    LOCKED_START_ISO = "2026-01-01T00:00:00Z"
    LOCKED_END_ISO   = "2026-10-31T23:59:59Z"

    @classmethod
    def verify_partition_access(
        cls,
        simulation_start_iso: str,
        simulation_end_iso: str,
        authorization_token: Optional[str] = None,
    ) -> bool:
        # Check date overlap with locked window
        has_overlap = not (
            simulation_end_iso < cls.LOCKED_START_ISO or
            simulation_start_iso > cls.LOCKED_END_ISO
        )
        if not has_overlap:
            return True  # Dev or Val partition

        if not authorization_token:
            raise PermissionError(
                "LOCKED_OOS_PARTITION_VIOLATION: Requested date range touches locked OOS partition."
            )
        # Verify HMAC token...
```

### Protection Characteristics

1. **Non-Bypassable:** Any simulation run requesting data overlapping `2026-01-01` to `2026-10-31` triggers the guard.
2. **Cryptographic Authorization:** Only a valid HMAC-SHA256 signature generated with the governance secret can unlock the partition.
3. **Audit Trail:** Access attempts with invalid or forged tokens are logged and rejected with `PermissionError`.
4. **Development Accessibility:** Dates entirely within Development (2023-12-01 to 2025-06-30) and Validation (2025-07-01 to 2025-12-31) execute without requiring a token.

---

## 4. Verification Status

All adversarial tests for OOS protection passed in [`test_milestone_4_6_3_0_1_adversarial.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_3_0_1_adversarial.py):
- `test_unauthorized_oos_access_raises_permission_error`: **PASSED**
- `test_authorized_governance_token_permits_access`: **PASSED**
- `test_forged_governance_token_rejected`: **PASSED**
- `test_dev_and_val_partitions_accessible_without_token`: **PASSED**
