# 177_f — Final amendment preregistration, rev2 (placeholder-free successor)

The final amendment preregistration required by 158_s §10 Unit D:
the executable preregistration of record for the AMENDED §8.4
validation tranche. Rev2 supersedes 174_f (preserved at reviewed
bytes) per 175_s; the deltas are the frozen-deadline semantics (§6),
the derived lock/bundle provenance and corrected lock sequence
(§2/§10), the concrete executable commands (§7), and the five 175_s
documentation corrections (§§3, 5, 6, 8). It succeeds 153_f (the v1
prereg of record; v1 evidence pinned under manifest `b01b7060…`)
through the accepted amend-once plan 158_s (accepted unchanged by
159_f) as implemented in 160_f–176_f. Every literal below is frozen;
none is a placeholder. The single amend-once allowance (132_s §8.4)
is CONSUMED by this document — a scientific failure of the amended
tranche is terminal for unit 3.

## 1. Code identity

- Successor source digest (`stage1_source_digest()`, all tracked
  `tasks/conductor/*.py`, including the formal run module
  `stage1_amend1_run.py`):
  `d73cde71682fb87222c33e889b2cf77730ad338360a5226fea5919457296c461`
- `uv.lock` SHA-256:
  `f5486ec478b080aa79c6d0444478b019d2ce6262173a643fd1d6aa8f779e48c9`
- Numerical stack (load-bearing, carried in the env manifest and
  required at validation): Python 3.12.3, NumPy 2.3.5, SciPy 1.18.0,
  torch 2.11.0+cu130.
- Full CPU suite at this identity: 899 passed under `-W error`,
  TRUE process exit 0.

## 2. Execution identities, lock provenance, and lifecycle

- Attempt: `stage1-pre-ce1-amend1-attempt-1` (one attempt, ever).
- Tags: validation `stage1-validation-amend1-v1`, replay
  `stage1-replay-amend1-v1`, artifacts
  `stage1-tranche-artifact-amend1-v1` (v1/amend1 artifacts refuse
  each other's loaders).
- Run roots (atomic claim; ANY pre-existing path refuses):
  `runs/stage1-validation-amend1`, `runs/stage1-replay-amend1`.
- The execution-bundle manifest's self-hash is THE amended execution
  identity: every artifact, manifest, loader and the aggregate binds
  it. The bundle is constructed ONLY by the formal lock-time
  constructor `build_lock_bundle` (175_s finding 2), which DERIVES:
  the preregistration hash from THIS file's committed bytes; the
  lock-record hash from the committed lock record's bytes;
  `git_commit` from clean HEAD; `source_digest` recomputed; the
  freshly built and validated environment manifest; and the registry
  trio from the authoritative support ids, verified canonical. Every
  consumer holding the bundle and a validated environment manifest
  additionally cross-checks `git_commit`/`source_digest` against it.
- Frozen expected provenance values, all re-verified this session:
  - `v1_evidence_manifest_sha256 =
    b01b706084c235f2024c6c3fd32e8054fb93c22bd1a96c5bc9dcfa588f0b2baa`
  - `seed_registry_sha256 =
    dbd8a12f3269694c37f0083ca0793de531df42c775ca698848801240576a5eda`
    (49,342 entries, §4)
  - `b_support_sha256 =
    5eb2ec57db8ed7ea94fed1125e10e3a8baf8e9f07aafc10bc608cefb4ff4a439`
    (the 18 real support ids, re-derived from the registry's B keys)
  - `scenario_grid_sha256 =
    ec55b07f9c1cb758240de06025e14d6ef37a26c57deca680a8e2c1031b2e2eb2`
  - `request_contract_sha256 =
    88a26f66a3b63306c4c45dbacb862d3cce71ca0cbbef50198a44a788f0363d83`
  - `artifact_schema_sha256 =
    6050cc49a7376406d02ee5986ee9a8a8e0f3e52c8ee9b66b6974be4ffd075e39`
  - `expected_file_set_sha256 =
    e73a6c3079808f274bce21b5781a0cd3400282e7db9d502e3a82a69e6ad4843a`
  - prompts (re-derived from bytes): few-shot
    `fe9bba0deafc60ec45f7883d9fb7bbddda4da847ed7e5d92a53f9b88adb29070`,
    schema-only (derived by dropping the demo block, never retyped)
    `9efe8998f1ee17fa9b194ab5e8179c61bbc1036d0c8000c064676ef2c721e9fb`;
    SYSTEM_DIRECT
    `b7a7d2d2bac1493eaf217dd415be1d5dd4cff4846ef16dfad825a95be2982452`.
- Frozen file lifecycle (`EXPECTED_RUN_FILES`): validation root =
  bundle + env manifests, deterministic set, benchmark (live
  measurement + frozen literal + frozen deadline), artifacts A/C/D,
  eight `partial_D_*` records (scenario + bundle identity + D6–D8
  branch counts), aggregate, run record; replay root = bundle + env
  manifests, replay manifest, raw completions, artifact B, run
  record. `finalize_amend1_run` preflights both roots BEFORE any
  mutation, fully validates both env manifests (recomputed hashes +
  provenance cross-check), reconciles every partial-D record against
  artifact D, writes aggregate/run-record atomically, and re-checks
  both exact sets. A run finalizes once.

## 3. The amended persistence statistic (158_s §4) — implementation literals

- Boundary `r = 0.10`; cluster score `D_c(r) = J_c − r·K_c`;
  branches exactly {zero, positive}, trigger EXACTLY `J == 0`;
  observed `K = 0` at a look → unresolved (never admitted).
- Tail allocation per look: `a = 0.05/len(looks)` per schedule;
  pre-observation Bonferroni split `a_zero = a_ratio = a/2`.
- Positive branch: Student-t bound on the mean score in the FROZEN
  float64 sufficient-statistic order (`score_components`), Fieller
  denominator check `L(K̄) > 0` else denominator-unresolved (decision
  unresolved; reported ratio upper = 1 for coverage purposes);
  `STUDENT_T_IMPL = scipy.stats.t.ppf` at SciPy 1.18.0.
- Tolerance rule (`TOLERANCE_FACTOR = 64`): scalar §4.5 rule at the
  r = 0.10 gate, `tol = 64·eps64·max(1, |S_D2|, |S_D²/N|)` (same
  form for the eligibility variance); the INVERSION SCAN variant's
  magnitude set additionally includes the summed intermediates —
  `tol(r) = 64·eps64·max(1, |S_D2(r)|, |S_D(r)²/N|, |S_J2|,
  |2r·S_JK|, |r²·S_K2|)` — because V_D(r) near r ≈ p̂ is a
  near-total cancellation of those terms (measured in 167_f).
  Values below −tol refuse; within [−tol, 0) clamp to 0.
- Zero branch (§4.4): structural (DESIGN-DECLARED full eligibility
  only — never inferred; contradiction with observed data refuses):
  `U = CP-upper(sum_A; N, a_zero)`. Non-structural:
  `U_A = CP-upper(sum_A; N, a_zero/2)`,
  `L_Q = max(0, Q̄ − sqrt(ln(2/a_zero)/(2N)))`; `L_Q ≤ 0` →
  unresolved, else `U = min(1, U_A/L_Q)`. Zero branch never fails.
- Reporting inversion: `INVERSION_RULE_ID =
  grid1001-plus-phat-bisect80-outer-v1` — membership
  `G_L(r) ≤ 0 ≤ G_U(r)` (inclusive) on the 1,001-point grid
  AUGMENTED with p̂; the member set must be one contiguous run
  containing p̂ (else refuse — never select a component); exactly 80
  float64 outward-bisection iterations per side from p̂; OUTER
  bracket endpoints; 0/1 where the set reaches the boundary.
  Endpoint comparison contract: rtol 0, atol 1e-12.
- Decisions at the gate: pass iff `G_U(0.10) ≤ 0`; fail iff
  `G_L(0.10) > 0`; else unresolved. `s_D = 0` is valid (degenerate
  interval `{p̂}`).
- D1–D5 bootstrap quantiles: method `linear` (unchanged from v1).
- Record scopes (corrected per 175_s): QUALIFICATION surfaces
  consume `qualification_look_report` — renderer-level (N × 3)
  inputs, the full per-branch §4.6 field sets, the equal-cluster
  descriptive rate (never replacing p̂), per-renderer J/K, and the
  implementation/version/inversion-rule binding. D6–D8 evaluate
  per-look records in memory with the same statistic but PERSIST
  integer scenario counts plus the eight branch-telemetry rows only.

## 4. Seeds (158_s §9.3)

- Derivation: first 8 bytes (big-endian) of SHA-256 over
  `utf8(domain ␟ key)`.
- Domains: A and C cells under the FRESH domain
  `stage1-validation-amend1-v1`; D per-trial, det-set, and B
  per-completion under the retained, never-exposed v1 domain
  `stage1-validation-v1` (equal to v1 `scenario_seed` by
  construction, asserted by test).
- Finalized registry: 48 A + 24 router + 48 C paths + 8×5,000 D +
  6 det-set + 18×2×256 B = **49,342 entries**, digest `dbd8a12f…`
  (§2). B keys use RAW unpadded completion indices — byte-identical
  to `completion_seed` material.
- Consumption: every runner first validates the bundle against the
  registry AND verifies the registry CANONICAL (complete
  rederivation from its own B-implied support ids and exact
  comparison), then consumes REGISTERED values directly — A via
  `seed_override`, C one PCG64 per path from the registered path
  seed (sequential trials), D/det-set via fail-closed lookups, B via
  the registry lookup inside the generation loop. A missing key
  refuses; nothing falls back to derivation. B evidence additionally
  re-binds the registry-implied support ids at CONSUMPTION
  (`verify_replay_evidence`).

## 5. Grids and acceptance criteria

**A (v1 criteria under fresh seeds).** 48 position cells (4
scenarios × deltas {0.10, 0.15, 0.20} × sigmas {0.25, 0.50, 0.75,
0.95}) + 24 router cells, 10,000 trials each. Gated: the **8**
position cells at delta 0.15, sigma ∈ {0.25, 0.50} and the **4**
router cells at effect 0.10, sigma ∈ {0.25, 0.50} must each have
Wilson one-sided-95% LB(pass rate) ≥ 0.80. Everything else is
disclosure.

**C (amended, 158_s §5).** 48 coupled maximum-cap paths (2 schedules
× eligibilities {0.60, 0.65, 0.80, 1.00} × thetas {0, 0.05, 0.10} ×
2 distributions) × 10,000 outer trials; one prefix-valid
maximum-length draw per trial; first terminal decision stops the
path; 120 per-look marginals persisted as telemetry. Acceptance
(§5.3, hard paths = ordinary/0.65 and fork/0.60, both
distributions): θ=0 rows must first-pass EVERY trial
(10,000/10,000); θ=0.05 rows must have Wilson LB(first-pass) ≥
0.80. θ=0.10 rows are mandatory non-gating disclosures.

**D (amended, 158_s §6).** Eight scenarios × 5,000 outer trials;
10,000 inner replicates wherever a bootstrap applies; NO agreement
gate. D1–D5 keep their v1 DGPs/ids/alphas (D2 on the amended fork
looks (100, 500)); D6–D8 are undercoverage checks of the amended
statistic: error = reported ratio upper endpoint (zero_U, pos_U_p,
or 1 on a denominator-unresolved look) STRICTLY below true θ at any
registered look (U = θ covers). D6 ordinary e=1.00 θ=0.10
cluster-correlated structural; D7 ordinary e=0.65 θ=0.10
row-dispersed; D8 fork e=0.60 θ=0.01 cluster-correlated with the
both-branches-at-each-registered-look support rule. Acceptance per
scenario: Wilson one-sided-95% upper bound on the error rate ≤
`coverage_alpha_ceiling(allocated_alpha)`; D8 additionally requires
branch support (zero and positive both present at looks 100 and
500). Branch telemetry: exactly 8 per-look rows (D6/D7 at
100/300/500, D8 at 100/500), schema-validated and reconciled against
the partial records at finalization.

**B (frozen contract, unchanged since 150_f/153_f).** 18
observations × 2 prompts × 256 singleton completions (9,216), model
`Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1`,
fresh zero-B LoRA over the NF4 base, global RNG reset per draw from
the registered seed, complete accounting (malformed stays in
n = 256), pair table derived from the pinned surface BEFORE sampling
(support declaration
`6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff`,
surface manifest
`221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23`),
conservative CP uppers at 0.05/(2·O) with structural O = 2 ×
distinct-payoff observations, direction floor 0.10. Statuses:
`not_ruled_out`, `not_demonstrated`, `unknown`.

## 6. Budgets and abort rules (158_s §5.4; 175_s finding 1)

- A ≤ 30 min; C ≤ 30 min (in-runner deadline); D6–D8 combined ≤ 30
  min; complete CPU tranche ≤ 12 h; B keeps its frozen GPU budget
  and abort behavior.
- **The FROZEN pre-lock measured literal controls the formal D1–D5
  deadline**: `MEASURED_SECONDS_PER_OUTER_X1E6 = 951_551` (the 173_f
  §5.4 10,000-inner worst-case benchmark, copied verbatim into
  source) → `D_SCENARIO_DEADLINE_SECONDS = 4 × 0.951551 × 5,000 =
  19,031 s` per scenario. Enforcement is IN-LOOP: every 50 outer
  trials on the monotonic clock, against the MINIMUM of the frozen
  per-scenario deadline and the remaining D6–D8/total budgets; a
  non-positive remainder refuses before the scenario starts.
- The live worst-case benchmark at execution is persisted and
  SANITY-BANDED only: a measurement outside the inclusive band
  [0.951551/4, 0.951551×4] s/outer is an infrastructure abort
  (`benchmark_sanity_check`) — never grounds to proceed or to move
  the frozen deadline.
- Auditable worst-case projection (175_s correction — no per-scenario
  weights are claimed): five D1–D5 scenarios bounded by the worst
  path = 5 × 0.951551 × 5,000 ≈ **6.61 h**; adding the three frozen
  30-minute component budgets bounds the CPU tranche at ≈ **8.11 h ≤
  12 h**. C measured projection 1.51 min ≤ 30 min.

## 7. Execution order (158_s §11) — executable commands

After lock, on the execution box, from the lock commit with a clean
tree (ollama VRAM checked before the GPU step). The bundle and
registry are DERIVED inside `formal_context()` — this file's
committed bytes, the unique committed lock record
(`plans/conductor/*_f_stage_1_amend1_lock.md`), clean HEAD, and the
authoritative support ids; nothing is typed in:

1. `uv run python -m tasks.conductor.stage1_amend1_run tranche` —
   verifies the v1 evidence archive, builds/validates the bundle,
   verifies the registry canonical, claims
   `runs/stage1-validation-amend1`, runs the deterministic
   equivalence set (registered seeds; exact expected decisions or
   nothing else runs), persists the sanity-banded benchmark, then A
   (fresh registered seeds) → amended C → all eight D scenarios,
   with staged persistence, per-scenario wall times, artifact
   reloads through the aggregate's loaders, and aborted-run records.
2. `uv run python -m tasks.conductor.stage1_amend1_run replay` —
   GPU B under the SAME derived bundle (~50 min), amended root/tag,
   registered per-completion seeds, full §9.4 file set, abort
   contract.
3. `uv run python -m tasks.conductor.stage1_amend1_run finalize` —
   preflight, reload/verify everything, compute and atomically
   persist `aggregate.json`, update the run record, exact-set
   checks.
4. `uv run python -m tasks.conductor.stage1_amend1_run archive` —
   byte-copies BOTH run roots to
   `plans/conductor/evidence/stage1_pre_ce1_amend1_{first12(bundle_sha256)}/`,
   writes the byte/length/SHA-256 manifest with the identity block
   and run statuses, verifies every archived byte against the run
   roots and the manifest, and refuses a pre-existing destination.
   The SAME command archives an infrastructure abort's partial
   evidence before any recovery decision. Commit the archive.
5. The reviewed §12 terminal decision, citing the archive manifest
   hash. Post-hoc diagnostics stay in a separate manifest section.

## 8. Registered falsifiable predictions

- **Deterministic sub-checks** (computed by the implementation,
  173_f §4): θ=0 hard-path C rows first-pass 10,000/10,000 —
  ordinary e=0.65 decided exactly at look 300 (zero-branch
  U = 0.032651 at that look), fork e=0.60 exactly at look 500
  (U = 0.019099); structural e=1.00 θ=0 rows decided at look 100
  (U = 0.046746). The deterministic equivalence set matches its six
  frozen decisions exactly.
- **A**: all **8** gated position cells and all **4** gated router
  cells pass (v1 measured worst gated cell 0.9432 under the retired
  seeds; fresh seeds should move rates by ~±0.01, nowhere near the
  0.80 criterion).
- **C power**: θ=0.05 hard-path first-pass rates ≈ 0.95 per 159_f's
  approximate amended-score calculation (NOT a v1 measurement — the
  v1 row-dispersed envelope passed 0/10,000, which is the failure
  this amendment remedies), comfortably above the Wilson-LB ≥ 0.80
  gate. This is the criterion the amendment exists to meet; failure
  here is a scientific stop, not grounds for any further amendment.
- **D**: all eight scenarios within their ceilings — the design uses
  Bonferroni splits and t/CP/Hoeffding bounds INTENDED to be
  conservative, though not every component carries a finite-sample
  guarantee; establishing that calibration is precisely what D6–D8
  test. D8 branch support satisfied — expected zero-branch trials
  ≈ 0.99⁶⁰ × 5,000 ≈ 2,700 at look 100 and ≈ 0.99³⁰⁰ × 5,000 ≈ 245
  at look 500, with the positive branch present in the complement.
- **B**: no registered prediction (early-warning screen; both
  directions are represented in the support, so `unknown` is not
  expected). B sets the claim state only.
- **Predicted verdict**: scientific pass on A/C/D →
  `confirm_c2_provisional` if B is `not_ruled_out` in both
  directions, else `confirm_c1_only` with
  `C2_preCE1_available = false`.

## 9. Decision table (158_s §§7, 12 — frozen)

| outcome | decision |
|---|---|
| A/C/D pass, B both `not_ruled_out` | `confirm_c2_provisional` |
| A/C/D pass, any B `not_demonstrated`/`unknown` | `confirm_c1_only`, `C2_preCE1_available = false` |
| any A/C/D scientific failure | `scientific_stop` — terminal for unit 3; no second amendment |
| malformed/unreproducible/foreign-identity evidence | infrastructure abort (raises; archive partial evidence, then reviewed recovery) |

`B_supports_C2` is the B-only diagnostic; `C2_preCE1_available`
additionally requires the scientific pass. The terminal decision is
made in review against the archived evidence — never automated.

## 10. Lock sequence (corrected per 175_s)

1. The lock record pins the reviewed preregistration (this file's
   SHA-256 at its reviewed commit) and the executable state (the
   source digest and suite result of §1).
2. The lock record is committed.
3. At run time, `build_lock_bundle` derives the lock record's byte
   hash and the current clean HEAD (the commit containing the lock
   record) into the execution bundle, alongside the recomputed
   source digest, the fresh validated environment manifest, and the
   canonical registry. The bundle exists only in the run roots.
4. Nothing is ever written back into the lock record.

Thresholds, grids, seeds, budgets and the decision table in this
document never move after that lock.
