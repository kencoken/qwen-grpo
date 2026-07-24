# 141_f — Unit 3 preregistration: the §8.4 design-validation tranche

**Status: preregistration for review. Nothing frozen has run.** Per
132_s §8.4, the source, inputs, prompt bytes, support, seeds, scenario
grid, and acceptance criteria are frozen by this document BEFORE the
tranche executes; the tranche's single reviewed outcome then either
confirms the current design for CE1 or amends it once in a new reviewed
plan before construction registration. The only computations performed
so far are (a) the deterministic correctness tests now in CI, (b) the
disclosed ANALYTIC predictions below (132_s-sanctioned "preliminary
calculation", exact binomial/normal, not the frozen simulations), and
(c) timing-only dry runs with throwaway seeds and non-grid parameters.

## 1. Frozen implementation and identities

- Implementation: `tasks/conductor/stage1_validation.py` at this commit
  (bound by the successor source digest, which covers all tracked
  conductor sources).
- Seed recipe: first 8 bytes of
  `SHA256("stage1-validation-v1" ␟ scenario_id)`, `PCG64`; scenario ids
  are the exact f-strings in the module (`A|{scenario}|{delta}|{sigma}|
  {trials}`, `A-router|{mixture}|{effect}|{sigma}|{trials}`,
  `C|{schedule}|{N}|{eligibility}|{theta}|{dist}|{trials}`).
- Grids (all frozen constants in the module):
  - **A positions:** the four distinct (schedule, divisor) combinations
    the §8.2 alpha rules produce — `ordinary_div1/2/3` (looks
    100/300/500; tails 0.05/3, 0.05/6, 0.05/9) and `fork_div3` (looks
    100/200; tail 0.05/6) — × δ ∈ {0.10, 0.15, 0.20} × σ ∈ {0.25, 0.50,
    0.75, 0.95}, 10,000 trials per cell, two-point design distribution
    with invalid pairs rejected.
  - **A router:** Core (5 cells) and Core+fork (6), fixed
    first-100-per-cell support, equal-cell weighting, one-sided 0.025,
    effects {0.05, 0.10, 0.15} × σ ∈ {0.25, 0.50} (0.75/0.95 as stress),
    10,000 trials.
  - **C:** schedules {ordinary, fork} × every registered look ×
    eligibility {0.60, 0.65, 0.80, 1.00} × θ ∈ {0, 0.05, 0.10} × both
    frozen joint distributions (cluster-correlated primary,
    row-dispersed stress); m = 3 (renderer-crossed rows per cluster per
    directed edge; the persistence gate is per edge and never pools
    edges); 10,000 trials per cell.
  - **D:** deterministic half already in CI
    (`test_conductor_stage1_validation.py`: exact two-point moments, CP
    closed forms/inversion/monotonicity, Hoeffding/Wilson algebra,
    envelope simplification and unresolved handling, alpha-matrix
    arithmetic, seed determinism, null-size sanity). Monte-Carlo half:
    at most 8 adverse scenarios, 5,000 outer × 2,000 inner replicates,
    the 1,000-dataset 2,000-vs-10,000 agreement check at ≥ 99.5%, and
    the operational-alpha Wilson-UB ceiling
    `allocated + max(0.005, 0.25 × allocated)`.
- Stopping-rule interpretation frozen for review (this is our reading
  of §8.2/§8.4A and a named sign-off point): at each registered look
  with the allocated tail alpha, a position **passes** iff point ≥ 0.10
  AND normal-approx LCB > 0; **conclusively fails** iff UCB < 0;
  otherwise expands; unresolved at the cap is not-passed. `Delta_router`
  has no point-materiality rule (LCB > 0 only, single terminal test).

## 2. Acceptance criteria (verbatim targets)

- **A positions:** 95% Wilson lower bound on pass probability ≥ 80% at
  δ = 0.15, at the cap, for σ ≤ 0.50, for every required scenario;
  δ = 0.10 and σ ∈ {0.75, 0.95} are mandatory disclosures, not gates.
- **A router:** same 80% Wilson criterion at effect 0.10, σ ≤ 0.50, for
  each mixture.
- **C:** at the terminal caps and admission floors (fork 0.60 @ N=200;
  chain 0.65 @ N=500), zero persistence must yield an operational bound
  ≤ 10%, and θ = 0.05 (cluster-correlated) must give a 95% Wilson lower
  bound ≥ 80% on passing the 10% gate. Row-dispersed results are
  mandatory adverse disclosures.
- **D:** agreement ≥ 99.5%; per-hypothesis operational-error Wilson UB
  within the ceiling.

## 3. Falsifiable predictions (analytic, disclosed)

**A positions — predicted PASS everywhere it is gated.** Terminal-look
normal approximation (a lower bound on ever-pass):

| scenario | δ=0.15, σ=0.25 | δ=0.15, σ=0.50 | σ=0.75 (stress) | σ=0.95 (stress) |
|---|---:|---:|---:|---:|
| ordinary_div1 | 1.000 | 0.987 | 0.932 | 0.880 |
| ordinary_div2 | 1.000 | 0.987 | 0.932 | 0.872 |
| ordinary_div3 | 1.000 | 0.987 | 0.932 | 0.839 |
| fork_div3 | 0.998 | 0.921 | 0.668 | 0.436 |

At 10,000 trials, a true rate of 0.921 has Wilson LB ≈ 0.916 ≥ 0.80:
every gated cell is predicted to clear with margin. δ = 0.10 sits at
its point-materiality boundary (≈ 0.50 at the cap, as 132_s
anticipated; the frozen simulation reports the exact ever-pass value).

**A router — predicted PASS:** effect 0.10 gives 0.994 (Core) / 0.998
(Core+fork) at σ = 0.50; effect 0.05 at σ = 0.50 is ≈ 0.61/0.69
(reported, not gated).

**C — predicted FAIL on the power criterion (the expected amend-once).**
Exact binomial, cluster-correlated, k\* = largest any-event count still
passing the envelope:

| schedule | criterion cell | k\* | P(pass) at θ=0.05 | θ=0 |
|---|---|---:|---:|---:|
| fork | N=200, e=0.60 | 3 | **0.144** | 1.000 |
| ordinary | N=500, e=0.65 | 16 | **0.541** | 1.000 |

The zero-persistence criterion passes everywhere. The fork value 0.144
vs 132_s's preliminary 0.147 is a CP-implementation-detail discrepancy;
the frozen simulation is the artifact of record. **Predicted tranche
verdict: the single reviewed outcome is the amend-once branch, on §8.4C
power, before construction registration** — exactly as 132_s §8.4C
itself anticipated. We deliberately do not propose the replacement cap
or threshold here; that belongs to the amendment plan after the frozen
artifact exists.

Falsification: if any frozen A grid cell gated above fails its Wilson
criterion, or the frozen C simulation contradicts the failure
prediction (both hard-criterion cells ≥ 80% Wilson LB), this
preregistration's model of the design is wrong and the discrepancy is
investigated before any verdict.

## 4. Check B — direct-gradient feasibility replay (GPU), frozen spec

- **Support:** the 18 retained Stage-0 observations (support
  declaration `6df4c42b…`; payoff surface manifest `221a04d5…`;
  cached — no worker calls).
- **Prompts:** exactly `stage1.prompt_fewshot()` (`fe9bba0d…`) and
  `stage1.prompt_schema_only()` (`9efe8998…`) — pinned bytes, fail-
  closed on drift.
- **Policy:** exact Stage-2 model/tokenizer at the frozen revisions,
  untrained QLoRA initialization, temperature 1.0, 64 independent
  sampled completions per observation per prompt (not groups), no
  optimizer updates. 2,304 completions total.
- **Seeds:** `scenario_seed("B|{observation_id}|{prompt_sha256}|
  {completion_index}")` per completion batch — frozen recipe, exact
  batching recorded in the replay manifest.
- **Estimates:** per observation whose otherwise-identical w2/w3 pair
  has distinct cached payoff: p2, p3, and
  `g(p2,p3) = 1 − (1−p2)⁸ − (1−p3)⁸ + (1−p2−p3)⁸`; aggregation
  renderer-within-latent, latent-within-cell, cells equally, separately
  for directions u=2 and u=3; conservative upper sensitivity via
  one-sided familywise Clopper–Pearson upper bounds at tail
  `0.05/(2O)` substituted into monotone g (upper value 1 when the
  bounded pair leaves the simplex).
- **Manifest:** source-bound replay manifest = `stage1-environment-v2`
  (content-addressed, dirty tree refused) + the support-declaration and
  surface digests + prompt digests + per-completion seed table,
  confirming exactly 18 retained observations before sampling.
- **Consequence rules (frozen):** a represented direction with
  conservative upper value < 10% for both prompts prevents
  confirmation; an absent direction stays `unknown` and may be retained
  only as an explicitly accepted risk in the reviewed decision. The
  replay may not select or alter a prompt.
- **Prediction:** none registered for B beyond Stage 0's raw warning
  (2/36 fork groups) — that figure is an updating-policy artifact, not
  an estimate; B is a measurement, and we decline to guess it.
- Operational: verify ollama's VRAM footprint is released before the
  replay (it auto-restarts and was the cause of the NVML pinning).

## 5. CPU budget (132_s: benchmark before the full battery)

Timing-only dry runs (throwaway seed `0xDEADBEEF` / non-grid
parameters, statistical output discarded):

| component | measured basis | projected |
|---|---|---:|
| A position grid (48 cells @10k) + router (12) | 0.01 s/cell-1k | ≈ 0.1 min |
| C grid (~144 cells @10k) | 0.03 s/cell-1k | ≈ 0.8 min |
| D coverage MC (8 scenarios × 5,000 × 2,000) | 0.059 s/outer trial | ≈ 40–45 min |
| D agreement check (1,000 × (2,000+10,000) reps) | same basis | ≈ 6 min |
| **total tranche CPU** | | **≈ 1 hour** |

Comfortably inside the ≤ 12 h single-tranche gate. B adds one GPU
session (2,304 sampled completions; Stage-0 measured 0.315 s per
generation worst-case ⇒ ≈ 12–15 min including loads).

## 6. Execution order after review sign-off

1. D deterministic half — already green in CI (34 tests).
2. A grids (positions, router) with frozen seeds → artifact.
3. C grids, both distributions → artifact.
4. D Monte-Carlo battery under the approved budget (worst-case scenario
   first, abort if it exceeds projection by >4×) → artifact.
5. B replay (GPU) under the frozen manifest → artifact.
6. `evaluate_acceptance` output + all artifacts content-addressed → the
   single reviewed confirm/amend decision (predicted: amend-once on
   §8.4C power). If the decision amends, every mechanically affected
   frozen check reruns under the amended design per 132_s §8.4.

**Stop point: this preregistration awaits reviewer sign-off before step
2.** The 8-scenario D grid composition is proposed in the module
constants but the reviewer may adjust scenario selection at sign-off
without touching machinery; everything else above is frozen as written.
