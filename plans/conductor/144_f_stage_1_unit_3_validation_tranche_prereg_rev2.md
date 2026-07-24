# 144_f — Unit 3 preregistration, revision 2: the §8.4 design-validation
tranche

> **This document supersedes `141_f`, which is preserved at the exact
> bytes `142_s` reviewed (the record discipline: reviewed artifacts are
> never rewritten; revisions are reissued forward).** It completes the
> preregistration per the `142_s` findings: the executable D registry,
> tranche runner, artifact schema, fail-closed aggregator, and B replay
> contract now exist in `stage1_tranche.py` / `stage1_replay.py`; the
> grid-count and hash corrections are applied; Wilson bounds are frozen
> as ONE-SIDED 95%. Point-by-point dispositions in `143_f`.

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
    effects {0.05, 0.10, 0.15} × σ ∈ {0.25, 0.50, 0.75, 0.95} — **24
    cells** (142_s correction; 0.75/0.95 are stress disclosures, gated
    cells are σ ≤ 0.50), 10,000 trials.
  - **C:** schedules {ordinary, fork} × every registered look (5
    (schedule, N) combinations) × eligibility {0.60, 0.65, 0.80, 1.00}
    × θ ∈ {0, 0.05, 0.10} × both frozen joint distributions
    (cluster-correlated primary, row-dispersed stress) — **120 cells**
    (142_s correction); m = 3 (renderer-crossed rows per cluster per
    directed edge; the persistence gate is per edge and never pools
    edges); 10,000 trials per cell.
  - **D:** deterministic half in CI
    (`test_conductor_stage1_validation.py`, extended per 142_s:
    renderer-coupled cluster resampling — permutation-invariant within
    cluster, sensitive across; unequal cell sizes; zero-cluster adverse
    replicates propagating ±∞ through the percentile endpoint;
    equivalence trichotomy at both ±0.10 boundaries; the complete
    sequential stake trichotomy; plus the original interval algebra).
    Monte-Carlo half: the EXACT frozen registry `D_SCENARIOS` in
    `stage1_tranche.py` — eight scenarios, each with a frozen DGP,
    per-trial seed `scenario_seed("{id}|{trial}")`, truth, error
    definition, and allocated operational alpha:
    `D1` ordinary sequential null (div3, σ=0.75, 5 cells; error =
    false pass; allocated 3×0.05/9); `D2` fork sequential null (div3,
    σ=0.50; 2×0.05/6); `D3`/`D4` equivalence boundaries θ=±0.10
    (error = false equivalence pass; 3×0.05/6); `D5` pilot equal-cell
    aggregation with heterogeneous σ_c and UNEQUAL cluster counts
    (12,12,12,12,12,6) at the null (0.05/2); `D6` persistence constant
    eligibility θ=0.10 boundary, `D7` variable eligibility θ=0.01
    near-zero, `D8` variable eligibility θ=0 at the fork floor —
    persistence scenarios are exact CP/Hoeffding (no bootstrap) and
    their error is UNDERCOVERAGE (operational bound below the true row
    rate at any registered look). 5,000 outer × 2,000 inner replicates
    where a bootstrap applies; the 1,000-dataset 2,000-vs-10,000
    agreement check (boundary deltas cycling {0.08, 0.10, 0.12}) runs
    and must pass BEFORE any reduced-replicate scenario executes
    (enforced in `run_d_battery`, not by convention); acceptance = the
    operational-alpha Wilson-UB ceiling
    `allocated + max(0.005, 0.25 × allocated)`.
- **Runner and artifacts:** `stage1_tranche.py` enumerates the exact
  grids in frozen order (48 A-position + 24 A-router + 120 C + 8 D
  keys, registries asserted by test), binds the content-addressed
  execution identity, and writes canonical content-addressed artifacts
  containing INTEGER sufficient statistics only — floats are never
  persisted or hashed; every rate/bound is recomputed at load.
  `load_artifact` fails closed on hash, name/tag, or key-set mismatch;
  `aggregate_verdict` refuses missing, duplicate, extra, malformed,
  non-finite or wrong-size results, recomputes every Wilson bound from
  counts, and incorporates all four checks plus B — empty inputs can
  never yield `confirm_possible`.
- **Wilson bounds are ONE-SIDED 95%** (z = Φ⁻¹(0.95) ≈ 1.645), lower
  for pass-probability/agreement criteria, upper for the
  operational-error ceiling (142_s smaller item, frozen).
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

## 4. Check B — direct-gradient feasibility replay (GPU), frozen
executable contract

The contract is code, not prose: `stage1_replay.py` freezes
`REPLAY_CONTRACT` (literal model `Qwen/Qwen2.5-3B-Instruct` @
`aa8e72537993ba99e69dfaafa59ed015b17504d1` — asserted equal to the
Stage-0C launch profile by test; NF4 double-quant bfloat16-compute;
adapter = freshly initialized LoRA r16/α32/d0.05 with zero B-matrices —
base-equivalent outputs through the byte-identical Stage-2 sampling
path; `sdpa` attention; do_sample, temperature 1.0, top-p/top-k
explicitly DISABLED, 128-token cap, EOS stop; **singleton generation,
batch 1, one seeded generator per (observation, prompt_sha256,
completion_index)** per the D16 batch-sensitivity evidence), the
eligible-pair builder (`eligible_pair_table`, derived from the pinned
surface BEFORE sampling; a missing family-correct variant row fails
closed), the 2,304-key accounting (`expected_completion_keys`), the
rendered-request hashing, the source-bound `build_replay_manifest`
(refuses incomplete request-hash coverage), and `summarize_replay`
(malformed/wrong-length/truncated completions REMAIN in the 64-sample
denominator; integer counts only).

**Disclosed design property (found while pinning the contract by
test):** at n = 64 the frozen consequence rule cannot produce
`not_demonstrated` — `g(u,u) ≈ 56u²` near zero, and the familywise CP
upper bound at zero observed hits is already ≥ 0.056 (most favorable
O = 1; ≈ 0.111 at the realistic O = 18), giving g ≥ 0.126 (realistic
≈ 0.42) > the 0.10 floor. Three individually reasonable conservatisms
— Bonferroni across ~36 parameters, exact CP upper bounds, and
substitution into a function that is quadratic near zero — compound at
a 64-draw sample size into a bound that can never fall below the
floor. B as frozen therefore classifies directions only as
`demonstrated` (possibly vacuously) or `unknown`; it cannot refute
feasibility. Pinned by test, including the mechanism's reachability at
larger n.

**Named sign-off decision — two preregistered options, reviewer's
choice before lock:**

1. **Accept as-is (64 completions; 132_s-conformant).** B becomes a
   descriptive report plus an `unknown` flag; the registered
   protection remains the cold-start ≥10% direct-gradient gate itself
   (72 groups × 8 = 576 draws per direction — adequately powered where
   B is not). Failure direction is safe: B cannot falsely block; the
   exposure is only that a hopeless direction is discovered at the
   cold start rather than here, costing one cold-start tranche
   (~12 min materialization + 3,456 policy completions).
2. **Amend to 256 completions per observation per prompt.** Restores
   the blocking power 132_s intended: at tail 0.05/36,
   `U_CP(0; 256) ≈ 0.025 → g ≈ 0.031 < 0.10`, and the branch stays
   reachable up to k = 1–2 observed hits (g ≈ 0.07); the reachability
   threshold is n ≥ 152, so 256 carries margin. Cost scales ×4 to
   9,216 completions ≈ 45–60 min GPU — still trivially within the
   budget. This amends a number frozen in the signed 132_s (§8.4B says
   64), which is why it is offered at sign-off rather than applied
   unilaterally: the reviewer's signature on this option IS the
   reviewed amendment, made before any data exists.

We recommend option 2: it is cheap, it is decided blind (no replay
data exists), and it converts a vacuous check back into the
fail-closed instrument the tranche is supposed to be. If the reviewer
prefers strict 132_s conformance, option 1 is sound and the exposure
is disclosed above.

- **Support:** the 18 retained Stage-0 observations (support
  declaration
  `6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff`;
  payoff surface manifest
  `221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23`;
  cached — no worker calls). Full hashes per 142_s; these are also
  frozen literals in `REPLAY_CONTRACT`.
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
| A position grid (48 cells @10k) + router (24) | 0.01 s/cell-1k | ≈ 0.2 min |
| C grid (120 cells @10k) | 0.03 s/cell-1k | ≈ 0.7 min |
| D coverage MC (8 scenarios, worst = 3-look sequential @0.195 s/trial) | re-benchmarked | ≤ 2.2 h cap-bound; ≈ 1.2 h realistic (D2/D5 smaller, D6–D8 exact) |
| D agreement check (1,000 × (2,000+10,000) reps) | same basis | ≈ 7–10 min |
| **total tranche CPU** | | **≈ 1.5 h realistic, ≤ 2.5 h bound** |

Comfortably inside the ≤ 12 h single-tranche gate. B adds one GPU
session (2,304 sampled completions; Stage-0 measured 0.315 s per
generation worst-case ⇒ ≈ 12–15 min including loads).

## 6. Execution order after review sign-off

1. D deterministic half — already green in CI (59 unit-3 tests).
2. A grids (positions, router) via `run_a_grids` with frozen seeds →
   content-addressed artifact "A".
3. C grid via `run_c_grid`, both distributions → artifact "C".
4. Agreement gate (`run_agreement_gate`) — must PASS before any
   reduced-replicate scenario — then the D battery via `run_d_battery`
   under the approved budget (worst-case scenario first, abort if it
   exceeds the 0.195 s/trial projection by >4×) → artifact "D".
5. B replay (GPU) under the frozen `stage1_replay` contract and
   source-bound manifest → artifact "B".
6. `aggregate_verdict(A, C, D, B)` — fail-closed over the exact
   registries — feeding the single reviewed confirm/amend decision
   (predicted: amend-once on §8.4C power). If the decision amends,
   every mechanically affected frozen check reruns under the amended
   design per 132_s §8.4.

**Stop point: this preregistration awaits reviewer sign-off before step
2.** The 8-scenario D registry is frozen in `D_SCENARIOS`; the reviewer
may adjust scenario selection at sign-off without touching machinery;
everything else above is frozen as written. The §4 disclosed B design
property (the `not_demonstrated` branch being unreachable at n = 64) is
a named sign-off question.
