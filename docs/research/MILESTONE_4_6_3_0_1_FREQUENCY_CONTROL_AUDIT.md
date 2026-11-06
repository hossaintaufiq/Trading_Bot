# NEPTUNE — Milestone 4.6.3.0.1
## Group C Frequency Control Integrity Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Document:** Group C Methodological & Quantitative Audit  
**Author:** Quantitative Audit Agent  
**Governing Rules:** Rule S-05, Rule S-06, ADR-028, ADR-030  

---

## 1. The Core Methodological Challenge

The purpose of Group C in the four-group experimental design is to serve as an **opportunity-frequency control**. 

When Group B (News-Veto) vetoes candidate setups, it inevitably reduces the total number of trades executed relative to Group A (Technical Baseline). If Group B outperforms Group A, a critical question arises:
> *Did Group B outperform because news intelligence successfully avoided adverse regimes, or merely because reducing trade frequency lowered cumulative transaction costs and market drag?*

Group C isolates this effect by thinning Group A's trade frequency to match Group B's trade frequency without using any news intelligence.

---

## 2. Audit Discovery: The Batch-Matching Fallacy

In Milestone 4.6.3.0, three matching methods were specified for Group C:
1. Method C1: Systematic Decimation ($k$-step uniform spacing across candidate signals).
2. Method C2: Technical Confidence Priority (ranking all candidates by `raw_confidence`).
3. Method C3: Deterministic Cryptographic Seed Decimation.

### The Leakage Vulnerability

Each of these methods requires knowing the target count $K = N_B$, which is the total number of trades executed by Group B across the entire historical partition.

Consider an online simulation advancing candle by candle from time $t_0$ to $t_{\text{end}}$:
- At time $t \ll t_{\text{end}}$, the total number of trades that Group B will eventually execute by $t_{\text{end}}$ is unknown.
- If an algorithm selects candidate setups at time $t$ based on $N_B(t_{\text{end}})$, it is consuming future information that was not available at time $t$.
- If candidate signals are ranked across the entire multi-year period by confidence score, a setup at $t_1$ is accepted or rejected based on whether setups at $t_{100}$ happen to have higher confidence scores.

### Formal Resolution: Separation of Online Strategy and Ex-Post Diagnostic Benchmark

To maintain uncompromising scientific integrity, NEPTUNE establishes an explicit architectural distinction:

```
                    ┌────────────────────────────────────────────────────────┐
                    │               GROUP C MATCHING MODES                   │
                    └────────────────────────────────────────────────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   ▼                                                           ▼
    ┌───────────────────────────────┐                           ┌───────────────────────────────┐
    │     ONLINE POINT-IN-TIME      │                           │      EX-POST DIAGNOSTIC       │
    │   (OnlineFrequencyMatching)   │                           │    (ExPostFrequencyMatching)  │
    ├───────────────────────────────┤                           ├───────────────────────────────┤
    │ • Evaluates cand sequentially │                           │ • Evaluates post-simulation   │
    │ • Uses pre-registered rate ρ  │                           │ • Requires final N_B count    │
    │ • Zero future knowledge       │                           │ • Serves as benchmark control │
    │ • Fully deployable online     │                           │ • Not an online trading rule  │
    └───────────────────────────────┘                           └───────────────────────────────┘
```

---

## 3. Implementation of Online Frequency Matching (Method C-Online)

The online frequency control algorithm is implemented in [`OnlineFrequencyMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py):

$$\text{digest} = \text{HMAC-SHA256}(\text{seed}, \text{signal\_id} \parallel \text{timestamp} \parallel \text{symbol})$$
$$\text{score} = \frac{\text{int}(\text{digest}[0:8], 16)}{2^{32} - 1}$$
$$\text{is\_accepted} = (\text{score} < \rho_{\text{calib}})$$

Where:
- $\rho_{\text{calib}} \in (0, 1]$ is a fixed, pre-registered retention ratio calibrated strictly on the Development partition (e.g., $\rho = 0.85$, reflecting the historical veto rate observed on Dev).
- The seed is cryptographically fixed: `"neptune_group_c_online_seed_2026"`.
- Decision is strictly local to the arrival time of candidate setup $i$.
- No future signal arrivals, vetoes, or market outcomes are consumed.

---

## 4. Retrospective Ex-Post Diagnostic Controls

The three original methods are retained in [`ExPostFrequencyMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) with the formal attribute `is_ex_post_diagnostic = True`.

They are evaluated after the simulation completes to determine:
- How does Group B compare against an oracle decimation of Group A?
- How does Group B compare against taking only the highest-conviction technical setups?
- How does Group B compare against an exact-count pseudorandom thinning?

These comparisons are valid research diagnostics, provided they are explicitly reported as retrospective benchmarks rather than point-in-time executable strategies.

---

## 5. Verification Status

All adversarial tests for Group C passed in [`test_milestone_4_6_3_0_1_adversarial.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_3_0_1_adversarial.py):
- `test_online_frequency_matching_zero_lookahead`: **PASSED**
- `test_ex_post_frequency_engine_explicitly_labeled`: **PASSED**
