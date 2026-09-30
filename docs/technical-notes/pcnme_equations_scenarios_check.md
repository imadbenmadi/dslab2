# PCNME vs PPO Paper — Equation Checks and Scenario Design (Simple)

For: Imed. Date: 2026-09-29.
Goal: before running any experiment, make sure (1) the equations are right, (2) the scenarios are meaningful.

---

## Part 1 — Equations

### 1.1 Errors found in the PPO paper (arXiv:2410.03472) — verified against its code

I cloned https://github.com/Procedurally-Generated-Human/VFC-Offloading-RL and checked `src/custom_components.py` (2026-09-29):

| # | Paper says | Code does (correct) | What you must use |
|---|---|---|---|
| 1 | Eq. 9: d_trans = **CU**_x / TR_w | `ind.sz / rate` → d_trans = **SZ**_x / TR_w | SZ (size), not CU. Paper typo. |
| 2 | Table 2: N0 = **174** dBm/Hz | `10**(-17.4)` → N0 = **−174** dBm/Hz | −174. Missing minus sign in paper. |
| 3 | Carrier frequency: not stated | `20*log10(5900)` → **5.9 GHz** (DSRC) | 5900 MHz. Needed for their path-loss model. |

Their delay pipeline in code (use this, it is consistent):
- Service compute: `CU / MIPS`
- Cloud: `CU / MIPS + Uniform(0.05, 0.2)` internet delay
- Cloud transmission: `SZ / 1 Gbps`
- Wireless rate: free-space path loss (dB): `G_T + G_R − 32.44 − 20log10(d_km) − 20log10(f_MHz)`, then Shannon: `r = B·log2(1 + P_R / (N0·B))`, delay = `SZ / r`

**Rule: when re-implementing their PPO baseline, follow their CODE, not their equations. Cite the repo commit you used.**

### 1.2 Fixes needed in OUR equations (DSLAB2 report)

1. **Double DQN:** report writes `a* = arg min_a Q(s', a; θ)`. Our reward is a value to maximize → must be **arg max** (or redefine Q as cost and say so explicitly). Fix the report.
2. **TOF-Broker:** `EC = ℓj/μk` is in **seconds** (it is the execution time). So θ = 1.0 means "tasks longer than 1 s go to cloud." State this. Better: compare EC against the task deadline (`EC ≥ α·Dτ → Boulder`), which is self-explaining.
3. **Texit:** `(Rk − dist)/v_closing` → if v_closing ≤ 0 (car moving away/parallel) you get division by zero or negative time. Define: `Texit = +∞ if v_closing ≤ ε`.
4. **Reward:** every term must be dimensionless. `Lj/Dτ` ✓, `Ej/Eref` ✓ — keep it that way; never mix raw seconds with normalized terms.

### 1.3 How to verify equations BEFORE the big experiment (1–2 days, do all four)

1. **Units table.** One table: every symbol, its unit. Every equation must balance. (Catches errors like #1 above instantly.)
2. **Hand-calculation oracle.** One task, empty system, fixed numbers → compute total delay by hand on paper → run the simulator with the same numbers → must match within 1%. Do this once per destination (fog, cloud, RSU).
3. **Queuing-theory oracle.** Configure one node as M/M/1 (Poisson arrivals rate λ, exp. service rate μ) → simulated mean waiting time must match the formula `W = λ/(μ(μ−λ))`. This validates the whole queuing machinery.
4. **Sanity invariants (asserts in code):** no negative delays; d_total = sum of its parts; energy ≥ 0; feasibility ∈ [0,1]. Leave the asserts on during all experiments.

If all four pass, the equations are defensible. Put the oracle tests in the repo (`tests/`) — reviewers love this.

---

## Part 2 — Scenarios

### 2.1 Why their scenarios are actually well-designed (and what to copy)

Their 3 scenarios (5/2, 10/4, 20/8 vehicles) are not arbitrary — they sweep **traffic intensity (TI = arrival bits / transmission capacity)**: scenario 2 has TI ≈ 0.9 (cloud barely holds), scenario 3 has TI ≈ 1.8 (cloud collapses). That is what made their result interesting.

**Copy the principle: design scenarios around load, not around vehicle counts.**

### 2.2 Our scenario grid (6 scenarios, enough for a paper)

| Scenario | Load (TI) | Deadlines | Mobility | What it shows |
|---|---|---|---|---|
| S1 Light | ≈ 0.5 | loose | low | everyone works; sanity |
| S2 Critical | ≈ 0.9 | loose | low | queues matter; greedy starts failing |
| S3 Overload | ≈ 1.5–2 | loose | low | cloud collapses (their headline result, reproduced) |
| S4 Tight deadlines | ≈ 0.9 | tight | low | feasibility separates methods (their env has NO deadlines — our addition) |
| S5 High mobility | ≈ 0.9 | tight | high (fast cars, small zones) | handoff/Texit component earns its place |
| S6 Heterogeneous fog | ≈ 0.9 | tight | low | weak+strong fog mix; placement intelligence matters |

- Keep their 5/2, 10/4, 20/8 sizes inside S1–S3 for continuity with the published paper.
- Compute and REPORT the TI value of every scenario (one line each) — it justifies the design.
- 5 seeds per scenario per method, mean ± 95% CI, plus worst-1% latency.

### 2.3 Fairness notes for the PCNME vs PPO experiment

- Same simulator, same traces, same seeds for both. PPO gets the same online step budget as our online fine-tuning.
- PPO optimizes delay only → compare on latency/feasibility/queues everywhere; on energy, footnote that PPO does not optimize it.
- Our offline dataset advantage IS the contribution — state it openly, and include the random-init DQN row to quantify it.

---

## Do this in order

1. Units table + fix the 3 equation issues in our report (arg max, θ meaning, Texit clamp).
2. Write the 3 oracle tests; make them pass.
3. Implement scenarios S1–S3; reproduce their qualitative result (cloud collapse at TI>1) with our simulator. If we can't reproduce that, stop and debug — something is wrong with our queuing.
4. Add S4–S6. Then run the full comparison.

## Sources
- PPO paper: https://arxiv.org/abs/2410.03472 — code: https://github.com/Procedurally-Generated-Human/VFC-Offloading-RL (checked `src/custom_components.py`, main branch, 2026-09-29)
- Free-space path loss (32.44 constant, d in km, f in MHz): standard Friis-in-dB form
- M/M/1 waiting time: any queuing-theory textbook (e.g., Kleinrock Vol. 1)
