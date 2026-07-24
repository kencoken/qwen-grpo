# 153_f — Unit 3 preregistration, revision 5: the §8.4 design-validation
tranche

> **This document supersedes `150_f` (lineage: 141_f → 144_f → 147_f →
> 150_f; every predecessor is preserved at the exact bytes its review
> saw).** Revision 5 applies the `151_s` mechanical corrections
> (dispositions in `152_f`): real-support recount (JSON-text positions
> parsed), the verifier's internal authoritative loading with COMPLETE
> regenerated-manifest equality (request hashes included), zero
> eligibility staying `unresolved`, pre-model persistence and abort
> records in the GPU driver, per-scenario wall times preserved on
> abort, and the two phrasing corrections below. Revision 4 had
> applied the `148_s` corrections: preregistered seeds used
> verbatim (no modulus), the Stage-2-parity model construction with B
> honestly framed as a separately frozen singleton replay regime, the
> B evidence-verification boundary (pair table rederived from the
> pinned surface; raw completions hash-matched and REPARSED to the
> counts; execution identity proven to be the hash of a valid
> environment manifest), agreement datasets in the exact D1–D5 shapes
> with alternating equivalence boundaries, staged persistence with an
> in-loop scenario deadline and aborted-run records plus
> refuse-overwrite run directories, and the eligible-aware point
> estimate. It also removes rev3's two internal contradictions (the
> stale "64-sample denominator"; the "seed table" phrasing — the
> manifest carries the deterministic per-completion seed RECIPE, and
> the exact seeds are a pure function of it; no table is persisted).
> Revision 3 had applied the `145_s`-directed decisions: **256 completions
> per observation per prompt** (9,216 total; the 145_s-directed
> amendment of 132_s §8.4B's 64), the `not_ruled_out` status
> vocabulary, the corrected Wilson agreement criterion (≥ 999/1000),
> agreement families covering D1–D5, cluster-level DGP variance,
> per-gate adverse replicate handling, strict artifact schemas with
> one-execution binding, the deterministic 10,000-replicate
> equivalence set, the end-to-end B driver, and the narrow
> `run_full_tranche` command. Dispositions in `146_f`.

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
    agreement check runs and must pass BEFORE any reduced-replicate
    scenario executes (enforced in `run_d_battery`, not by
    convention); its datasets cycle the FOUR reduced-replicate
    families it authorizes — stake-ordinary / equivalence /
    pilot-unequal-cells / stake-fork — with boundary effects cycling
    {0.08, 0.10, 0.12}; the passing criterion is the one-sided 95%
    Wilson LOWER bound ≥ 0.995 on exactly 1,000 datasets (minimum
    passing count 999/1000; any other sample size refuses). Before the
    gate, the deterministic 10,000-replicate equivalence set
    (`run_deterministic_equivalence_set`: six constant datasets with
    analytically forced decisions, including `fail` at the exact ±0.10
    null boundary) must match exactly. DGP rows carry ONE
    cluster-level two-point draw through all renderer rows, so
    declared cluster-level sigmas are tested as declared. Acceptance =
    the operational-alpha Wilson-UB ceiling
    `allocated + max(0.005, 0.25 × allocated)`.
- **Runner and artifacts:** `stage1_tranche.py` enumerates the exact
  grids in frozen order (48 A-position + 24 A-router + 120 C + 8 D
  keys, registries asserted by test), binds the content-addressed
  execution identity, and writes canonical content-addressed artifacts
  containing INTEGER sufficient statistics only — floats are never
  persisted or hashed; every rate/bound is recomputed at load.
  `load_artifact` fails closed on hash, name/tag, key-set mismatch,
  per-artifact row schemas (exact field sets, frozen trial counts
  10,000/10,000/5,000/256, count identities — impossible counts
  refuse), and the ONE authoritative execution identity shared by all
  four artifacts (B's GPU-session compatibility rule is identity: same
  box, same `stage1-environment-v2` manifest). `aggregate_verdict`
  recomputes every Wilson bound and every B direction status from
  integer counts, and incorporates all four checks — empty inputs,
  empty B, and mixed-execution artifacts all refuse (each is a named
  test). Adverse bootstrap replicates follow §8.3 per gate kind:
  −∞ lower-gate, +∞ upper-gate, and BOTH adverse endpoints for
  equivalence. The narrow `run_full_tranche()` command enforces the
  frozen order with the 4×-projection per-scenario abort and
  persist-reload verification of every artifact.
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
base-equivalent outputs through the SAME frozen construction the
Stage-2 trainer uses, within a **separately frozen singleton replay
regime** (`regime: singleton-replay-v1`; no byte-identity-with-trainer-
rollouts claim); `sdpa` attention; do_sample, temperature 1.0,
top-p/top-k explicitly DISABLED, 128-token cap, EOS stop; **singleton
generation, batch 1, with the GLOBAL CPU and CUDA RNG state reset per
singleton draw from the preregistered per-(observation, prompt_sha256,
completion_index) seed** per the D16 batch-sensitivity evidence), the
eligible-pair builder (`eligible_pair_table`, derived from the pinned
surface BEFORE sampling; a missing family-correct variant row fails
closed), the 9,216-key accounting (`expected_completion_keys`), the
rendered-request hashing, the source-bound `build_replay_manifest`
(refuses incomplete request-hash coverage), and `summarize_replay`
(malformed/wrong-length/truncated completions REMAIN in the
**256-sample** denominator; integer counts only).

**Design property, resolved by the 256 amendment (145_s):** at the
original n = 64 the consequence rule could not produce
`not_demonstrated` — `g(u,u) ≈ 56u²` and `U_CP(0; 64)` ≥ 0.056 already
maps above the 0.10 floor. At n = 256, `U_CP(0; 256) ≈ 0.025 →
g ≈ 0.031 < 0.10`; the branch is reachable up to ≈ 2 observed hits
(reachability pinned by test through `aggregate_verdict`). B is
described accurately (145_s): a **minimally informative early-warning
screen** — it can rule out feasibility in sufficiently low-frequency
cases; it may NOT rule out one-sided collapse where one Code
assignment is absent but the other is common; the 576-draw cold-start
gate remains the definitive signal-density check. Status vocabulary:
`not_ruled_out` (a conservative upper bound above the floor does not
demonstrate feasibility), `not_demonstrated` (below the floor for both
prompts — blocks confirmation), `unknown` (direction unrepresented).
The Bonferroni population `O` is frozen structurally as
`2 × distinct-payoff observations`, derived from the pre-sampling pair
table, never from supplied counts.

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
  untrained QLoRA initialization, temperature 1.0, **256 independent
  sampled completions per observation per prompt** (not groups), no
  optimizer updates. **9,216 completions total.** (145_s-directed
  amendment; the reviewer's signature on 145_s is the reviewed
  amendment of 132_s §8.4B's 64.)
- **Seeds:** `scenario_seed("B|{observation_id}|{prompt_sha256}|
  {completion_index}")` — SINGLETON generation, one seeded draw per
  completion (`generation_batch = 1`); the RNG semantics are frozen in
  code, not recorded after the fact.
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
  surface digests + prompt digests + the deterministic per-completion
  seed RECIPE (`scenario_seed('B|{obs}|{prompt_sha}|{index}')`, applied
  verbatim as unsigned 64-bit seeds — no modulus; the exact seeds are a
  pure function of the recipe, so no table is persisted), confirming
  exactly 18 retained observations before sampling.
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
session (9,216 sampled completions at 256/observation/prompt; Stage-0
measured 0.315 s per generation worst-case ⇒ ≈ 48–60 min including
loads; verify ollama's VRAM is released first).

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

## 148_s corrections carried by this revision

1. **Seeds verbatim:** `run_replay` applies `completion_seed` outputs
   directly (the pinned torch build accepts the full unsigned 64-bit
   range); the `% 2**63` that would have changed 4,541 of 9,216 seeds
   is removed.
2. **Model condition:** the replay constructs the model with the same
   frozen kwargs the Stage-2 trainer freezes (`torch_dtype=bfloat16`,
   `sdpa`, NF4 double-quant, `task_type="CAUSAL_LM"`, TRL k-bit
   preparation applied explicitly). B is described honestly as a
   **separately frozen singleton replay regime**
   (`regime: singleton-replay-v1`): generation batching is
   deliberately singleton per the D16 batch-sensitivity evidence, so
   no byte-identity-with-trainer-rollouts claim is made.
3. **B evidence verification at the consuming boundary:**
   `verify_replay_evidence` validates the environment manifest
   (identity proven to be the hash of a valid `stage1-environment-v2`
   whose source identity matches current bytes), the self-hashed
   replay manifest carrying this contract verbatim, the raw-completions
   file (hash + exact 9,216-key coverage), REDERIVES the pair table
   and observation meta from the pinned surface and support, and
   REPARSES all completions, requiring exact count reproduction.
   `aggregate_verdict` consumes B only as this evidence bundle; a
   self-rehashed artifact with altered counts cannot survive (named
   test). `load_b_artifact` is explicitly structural-only.
4. **Agreement represents what it authorizes:** stake-ordinary
   datasets use the exact D1 shape (five equally weighted σ=0.75
   cells); stake-fork the D2 shape; equivalence datasets alternate the
   +0.10/−0.10 boundaries; pilot datasets the D5 shape.
5. **Staged persistence and real aborts:** the run directory refuses
   overwrite; the environment manifest, deterministic-set outcome,
   benchmark, A/C artifacts, agreement outcome, per-scenario partial
   results and wall times persist at each stage boundary; the
   per-scenario deadline is checked IN-LOOP (every 50 trials) so an
   over-budget scenario is interrupted, and any failure leaves an
   `aborted` run record. The replay directory has the same
   refuse-overwrite rule.
6. **Eligible-aware point estimate:** `sequential_stake_decision` uses
   the same eligible-cluster, equal-cell statistic as the bootstrap
   (`point_estimate`); a cell with zero eligible observations leaves
   the gate unresolved instead of a NaN comparing false.

## 151_s corrections carried by this revision

1. **Real-support recount:** `recount_from_raw` parses the JSON-text
   `positions` the real `build_smoke_rows()` rows carry (either form
   accepted); a test recounts against actual support rows.
2. **Authoritative verification:** `verify_replay_evidence` loads the
   pinned surface, support rows, and REGENERATED rendered-request
   hashes internally (`load_pinned_replay_inputs`; tokenizer-hashed at
   the boundary), rebuilds the COMPLETE expected replay manifest, and
   requires exact equality — a rehashed manifest with any altered
   field, including one request hash, is refused (named probes).
   `aggregate_verdict`'s B bundle is now {artifact, replay_manifest,
   raw_completions_text} only.
3. **Zero eligibility:** an undefined point estimate skips both
   decision branches at that look; unresolved at the cap stays
   unresolved (the adverse −∞ UCB no longer fires a conclusive fail).
4. **Failure-path persistence:** the replay driver claims its run
   directory and persists the environment manifest, replay manifest
   and a `running` record BEFORE any model work; generation is wrapped
   so any abort writes an `aborted` record with wall time; the D loop
   records each scenario's wall time even when the in-loop deadline
   interrupts it (the partial error count travels in the abort error
   text).
5. **Phrasing:** the residual "byte-identical Stage-2 sampling path"
   line is replaced with the singleton-regime wording, and the seeding
   description now says what the code does: the global CPU/CUDA RNG is
   reset per singleton draw from the preregistered seed.

**Stop point: per 151_s, after these narrow fixes the focused suite
plus the real-row recount and changed-request-hash refusal probes have
been rerun; lockable without another broader review.** The 8-scenario D registry is frozen in
`D_SCENARIOS`; the 256 decision is taken as directed; no open sign-off
questions remain from our side.
