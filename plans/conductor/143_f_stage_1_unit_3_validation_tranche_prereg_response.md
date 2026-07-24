# 143_f — Response to 142_s (unit-3 preregistration completion)

All five blocking findings and all four smaller corrections are
implemented; `141_f` is preserved at the exact bytes 142_s reviewed,
and the completed preregistration is reissued forward as
`144_f_stage_1_unit_3_validation_tranche_prereg_rev2.md` (the record
discipline), which is now, we believe, executable and fail-closed
end-to-end. One new design property
was discovered while pinning the B contract by test and is disclosed as
a named sign-off question. Unit-3 tests: 59; full CPU suite: **720
passed** under `-W error`. No frozen grid, coverage scenario, or GPU
replay executed.

## Blocking findings

**1. D preregistered and executable — implemented.**
`stage1_tranche.py` carries the exact frozen registry `D_SCENARIOS`:
eight scenarios, each with a frozen DGP closure, per-trial seeds
(`scenario_seed("{id}|{trial}")`), truth, error definition, and
allocated operational alpha — covering the plan's required families:
ordinary and fork sequential nulls (D1, D2), both ±0.10 equivalence
boundaries (D3, D4), pilot equal-cell aggregation with heterogeneous
cells and UNEQUAL cluster counts (D5), and constant/variable
eligibility persistence at the θ = 0.10 boundary, near-zero, and zero
(D6–D8; exact CP/Hoeffding, no bootstrap, error = undercoverage at any
registered look). The 5,000-outer runner (`run_d_battery`),
Wilson-upper-vs-ceiling evaluation, and the agreement gate all exist
and are tested. Registry cardinality, uniqueness, and family coverage
are pinned by test; each DGP is exercised for one throwaway trial in
CI without touching frozen seeds.

**2. B is an executable frozen contract — implemented.**
`stage1_replay.py` freezes, in code asserted against the Stage-0C
launch profile by test: the literal model/revision
(`Qwen/Qwen2.5-3B-Instruct` @ `aa8e7253…504d1`), the adapter decision
(fresh LoRA r16/α32/d0.05, zero-initialized B — base-equivalent outputs
through the byte-identical Stage-2 path), NF4/attention/token-cap/
stopping and every sampling parameter (top-p/top-k explicitly
disabled), **singleton generation with one seeded generator per
(observation, prompt_sha256, completion_index)** — adopting the
reviewer's recommendation given the D16 batch-sensitivity evidence —
the eligible w2/w3 table derived from the pinned surface BEFORE
sampling (`eligible_pair_table`, fail-closed on missing variant rows;
uniqueness of the family-correct variant pair proven from
NODE_FAMILIES), candidate-specific rendered-request hashing with
completeness checks, malformed/wrong-length/truncated outputs REMAINING
in the 64-sample denominator, full support/surface/prompt identities as
frozen literals, and the complete 2,304-key accounting. The
source-bound manifest builder refuses incomplete request-hash coverage.

**3. Acceptance fails closed — implemented.** `evaluate_acceptance` is
deleted. `aggregate_verdict(A, C, D, B)` consumes only validated
content-addressed artifacts over the exact expected-key registries
(48 A-position, 24 A-router, 120 C, 8 D, one B artifact with typed
direction statuses); missing, duplicate, extra, malformed, non-finite
or wrong-size results refuse (`TrancheError`); every Wilson bound is
recomputed from integer counts, never trusted from a summary; the
verdict incorporates A, C, D (including the agreement block) and B.
Empty inputs cannot yield `confirm_possible` — pinned by test, along
with tampered-artifact, malformed-B, and failing-agreement paths.

**4. Frozen runner and content-addressed artifacts — implemented.**
`run_a_grids` / `run_c_grid` / `run_d_battery` enumerate the exact
frozen grids in frozen order; artifacts hold INTEGER sufficient
statistics only (a float or unknown field refuses at finalize), are
canonical-JSON content-addressed, and `load_artifact` fail-closes on
hash, name/tag, or key-set mismatch — so implementing anything after
seeing A/C outcomes is structurally impossible: the machinery that
will run is the machinery under review. The agreement gate is enforced
in code: `run_d_battery` REFUSES to start any reduced-replicate
scenario unless the agreement block has run and passed (tested).

**5. Deterministic D coverage completed — implemented.**
`paired_cluster_bootstrap` now takes (clusters × renderers) matrices —
renderer rows travel with their cluster, tested by within-cluster
permutation invariance and across-cluster sensitivity, and
renderer-collapsed input is rejected; unequal cell sizes tested;
zero-cluster cells propagate the §8.3 adverse extreme through a
purpose-built linear-quantile that handles ±∞ without NaN (numpy's
interpolation cannot); the equivalence trichotomy is implemented and
tested at both ±0.10 boundaries (±0.10 in the null); and the complete
sequential stake trichotomy (pass / conclusive fail / unresolved at
cap) is implemented as `sequential_stake_decision` /
`sequential_equivalence_decision` and exercised deterministically.

## Smaller corrections

- Router grid corrected to **24** cells; C grid corrected to **120**
  (both in 144_f and asserted by registry tests).
- Wilson frozen as explicitly **one-sided 95%** (z ≈ 1.645), lower for
  pass/agreement criteria, upper for the error ceiling; the stale
  z = 1.96 test comment is gone and the closed form is asserted.
- Full artifact hashes recorded in 144_f (support declaration
  `6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff`,
  surface manifest
  `221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23`)
  and frozen as literals in `REPLAY_CONTRACT`.
- Budget re-benchmarked against the now-heavier sequential worst case
  (0.195 s/outer trial): ≈ 1.5 h realistic, ≤ 2.5 h bound — still far
  inside the 12 h gate.

## New disclosure — a named sign-off question

While pinning the B contract by test we found that **the frozen §8.4B
consequence rule cannot produce `not_demonstrated` at n = 64**:
`g(u,u) ≈ 56u²`, and the familywise CP upper bound at zero observed
hits is already ≥ 0.056 (most favorable O), giving g ≥ 0.126 > the
0.10 floor. The conservative rule errs toward not-blocking by
construction — B classifies directions as `demonstrated` or `unknown`
and reports point estimates, but cannot refute feasibility at this
sample size. The property is pinned by test (including the mechanism's
reachability at larger n). 144_f §4 puts two preregistered options to
the reviewer, decided blind before any replay data exists: (1) accept
as-is — the rule was designed to prevent premature infeasibility
claims, the registered cold-start gate (576 draws per direction) does
the real work, and the only exposure is discovering a hopeless
direction one tranche later; or (2) amend to 256 completions per
observation, restoring the intended blocking power
(U_CP(0;256) ≈ 0.025 → g ≈ 0.031 < 0.10; reachable up to k ≈ 2 hits;
cost ×4 ≈ 45–60 min GPU). **We recommend option 2** — it is cheap,
blind, and converts a vacuous check back into a fail-closed
instrument; option 1 remains sound with the exposure disclosed.
Reviewer's call at sign-off; the signature on the chosen option is the
reviewed amendment of 132_s §8.4B's frozen 64, if taken.

## State

144_f + this response are the complete preregistration. Awaiting
sign-off; on sign-off, execution proceeds in the frozen §6 order
(A → C → agreement gate → D battery → B replay → `aggregate_verdict` →
the single reviewed confirm/amend decision, predicted amend-once on
§8.4C power).
