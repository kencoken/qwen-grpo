# 133_f — Stage-1 unit 1: §17 sign-off and plan-freeze errata

## 1. Sign-off record

**Ken approved every §17 review choice of
`132_s_stage_1_2_four_worker_redraft_rev2.md` on 2026-07-24**, at the
recommended defaults, with no modifications. The approved draft is bound
by content:

- commit: `73f2aeb` on `conductor_stage1`;
- SHA-256: `d29f6fb9035de10a4c529f7bf1d81a3506f2249ec4add995e715311e5794d086`.

The two residual notes from the final review pass are recorded as accepted,
not amended:

1. **§9.2 both-prompts-format predicate.** `ForkColdStartFallback` requires
   both prompt candidates to pass the reward-blind format gate; a single
   format-failing prompt combined with fork sparsity in the other forces a
   full stop rather than the Core fallback. Accepted as conservative
   fail-closed exposure (Stage 0 measured 144/144 format validity and
   `FORMAT_REPAIR_V1` exists).
2. **§8.4B per-prompt visibility.** The feasibility replay reveals
   per-prompt direct-gradient densities before the single confirm/amend
   decision. The §8.4 guards ("may not iterate prompts, select a prompt, or
   choose whichever interval method passes") govern; recorded as a disclosed
   residual for the CE1 record.

This document does not authorize construction, qualification, cold-start,
or Stage-2 execution. Per 132_s, the §8.4 validation tranche (unit 3) and
its reviewed confirm/amend decision stand between this sign-off and the CE1
Freeze Record — and 132_s §8.4C already predicts the amend-once branch will
be required for the persistence envelope.

## 2. Unit-1 scope and deliverables

Unit 1 per 132_s §16: resolve REVIEW CHOICE items; D4 joint-balance and
`policy_dev` cap/ranges; active four-worker Stage-1 restatement; profile
candidates; `SYSTEM_DIRECT`; gate applicability/denominators; exact
statistics, two retry lists, and visible slice.

Delivered in this commit:

| deliverable | where |
|---|---|
| §17 resolution record | this document, §1 |
| D4 erratum (cap 130, formal cohort 30–129, fail-closed range rule) | `tasks/conductor/program.py` (`CONSTRUCTION_CONSUMED_PREFIX`, `CONSTRUCTION_FORMAL_COHORT`, `validate_construction_cohort`) |
| `policy_dev` namespace (cap 1,000; cohorts A 0–23 / B 24–47 / cold-start 48–999) | `tasks/conductor/types.py` (`NAMESPACES`), `tasks/conductor/program.py` (`NAMESPACE_CONFIG`, `POLICY_DEV_COHORTS`, `policy_dev_cohort`) |
| gate thresholds, applicability matrix, C2 position universe, alpha rules, bootstrap identity, retry taxonomy, visible slice, cold-start and Stage-2 constants, shallow-router hyperparameters, artifact digests | `tasks/conductor/stage1.py` (new; not freeze-digested) |
| acceptance tests (joint balance, range/cap rejection, cohort disjointness, identity pins, alpha/population arithmetic) | `test_conductor_stage1.py` (new), `test_conductor_program.py` (cap test updated 100→130 under the approved erratum) |
| Stage-1 restatement | §3 below |

The eight Stage-0 freeze-digested source files are untouched:
`executable_source_digest()` still opens with `688f7e06da6e9ca0`. The queued
`workerpool.py` `108_f`→`108_s` citation fix remains queued for unit 2,
which issues the successor source/environment manifest.

## 3. Active four-worker Stage-1 restatement

The active Stage-1 design is 132_s §§3–9 in full. Operative summary:

- **Phases:** CE1 freeze → construction registration → B1/control fitting →
  construction reveal (frozen whole-profile rule) → qualification
  registration → qualification at registered looks → Stage-1 verdict →
  policy development (with the one §9.2 fork fallback) → Stage-2 freeze →
  development signal → headline seeds and one test reveal.
- **Populations:** formal construction = indices 30–129 per cell;
  qualification looks 100/300/500 ordinary, 100/200 fork; visible slice =
  first 18 qualification clusters per cell, paired private+visible, all
  three renderers.
- **Estimands:** family stake `Delta_family(c,j)` and within-Code stake
  `Delta_scale(c,j)` per 132_s §6; deployable mapping, `c_fixed`, `s(c,j)`
  frozen on construction; `s_compat` descriptive-only; `Delta_router` at
  one-sided 0.025 per branch on the fixed first-100-per-cell support.
- **Claims:** C1 (family routing) and C2 (model routing, task/node only)
  are the confirmatory Stage-2 claims; C3 per hierarchy gates; C2's
  practical dependence on fork admission and trainability is disclosed
  (132_s §2/§9) and accepted.

## 4. Frozen unit-1 decisions (exact values)

All constants live in `tasks/conductor/stage1.py`; the acceptance tests
pin them to their sources. The decisions of record:

1. **D4:** construction cap 130; the one formal cohort is exactly indices
   30–129 per cell; 0–29 remain generable for historical verification but
   any manifest containing them fails closed. Index 30 is block-aligned for
   every factor-block size in {1,2,3,6}; the joint-balance acceptance test
   recomputes exact joint contingency tables over 30–129 for every cell and
   requires max−min ≤ 1 (verified: passes for all six cells).
2. **`policy_dev`:** registered ninth namespace, fail-closed cap 1,000 per
   cell, disjoint cohorts exactly as 132_s §10.1.
3. **`SYSTEM_DIRECT`:** the rev0 bytes already present in the
   freeze-digested `prompts.py` are **adopted unchanged** as the frozen
   Stage-1 artifact:
   - bytes: `Solve the problem using only the information given. You may
     reason step by step. Answer with a single integer on the final line.`
   - SHA-256:
     `b7a7d2d2bac1493eaf217dd415be1d5dd4cff4846ef16dfad825a95be2982452`
   This honors both the answer-line protocol (cell spec §1.11) and the
   in-code rev0 note that revising it without execution evidence would be a
   change without measurement (the 103_s prompt-editing discipline). No
   frozen file was edited; the digest is pinned in `stage1.py` and
   recomputed by test.
4. **Profile candidates:** one primary per cell — the current complete
   `DEFAULT_PROFILE`, digest `dp-2bcb6373340a8a79`, shared by all six
   cells — and **no registered fallbacks**: no cell has a concrete pre-CE1
   reason (132_s §5.2), and `math_code` keeps the full `L_band=[8,16]`
   with no index cap (§17.4). Failure of a primary excludes that cell
   until a new reviewed plan.
5. **Gate applicability/denominators:** the §7.1 matrix encoded as
   `GATE_MATRIX`, with C1 positions per cell and the optional C2 positions
   `(code_atomic, n1)`, `(math_code, n2)`, `(fork_join, n2)`; semantic node
   ids verified stable under `branch_order` (the fork Code leaf is always
   `n2`). Core = the five mandatory cells.
6. **Exact statistics:** ordinary tail alpha 0.05/3, fork 0.05/2; family
   position gates divide by positions within cell; model-position
   classification always divides by 3 (the registered universe), Core or
   Core+fork; aggregate router branches at one-sided 0.025 each;
   equivalence strict `|θ|<0.10`; 10,000-replicate paired percentile
   cluster bootstrap, `numpy.quantile(method="linear")`, `PCG64`, seed =
   first 8 bytes of SHA-256 over the ␟-joined
   `(population_manifest_sha256, gate_id, canonical_cell_look_vector,
   "bootstrap-v1")` with the cell-look vector as comma-joined
   `cell_id:look` sorted by cell id.
7. **Two retry lists:**
   - `CASCADE_TRIGGER_CODES` = the frozen `SYNTAX_REJECTION_CODES` already
     in `types.py` (`E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`,
     `E_UNCLOSED_ARTIFACT`, `E_UNEXPECTED_TAG`, `E_PARSE`,
     `E_NONCANONICAL_INT`, `E_DEPTH`) — byte-identical to 132_s §7.3,
     asserted by test;
   - `INFRA_RETRY_CODES`, decided from the real local-runtime taxonomy
     (no network transport at execution time): `E_INFRA_CUDA_OOM`
     (max 3 attempts, backoff 10 s/60 s, `empty_cache()` before retry),
     `E_INFRA_IO` (max 3 attempts, backoff 10 s/60 s),
     `E_INFRA_INCOMPLETE_CALL` (max 2 attempts, backoff 10 s). Attempts
     count the initial call. Typed `InfrastructureError` contract
     violations are deterministic and never retried. Exhaustion aborts the
     affected gate surface. The exception→code mapping is implemented and
     acceptance-tested in unit 2's execution layer.
8. **Visible slice:** qualification indices 0–17 per cell (first 18).
9. **Cold start:** group size 8; 72 groups per topology/treatment and per
   admitted direction `u∈{2,3}`; general gates 0.80/0.25/0.10; C2 gate
   ≥10% direct model-gradient groups at unit (prompt, direction).
10. **Stage-2 population/schedule:** train 100 clusters/cell (one balanced
    renderer); `dev_select` = dev clusters 0–23 fully crossed;
    `pilot_gate` = dev clusters 24–35 fully crossed, read once; test
    `ceil(1000/(3C))` clusters/cell fully crossed; 2 groups/update;
    snapshots at update 0 and every 25. Arithmetic at C=6/C=5 (1,008/1,005
    test observations; 300/250 updates) is asserted by test.
11. **Shallow router:** `DecisionTreeClassifier(max_depth=3,
    criterion="gini", min_samples_leaf=5, random_state=0)` on
    `(cell_id, node_id, subtype, p, q, t, k, i)`, missing −1; ties to
    worker 2 (`CODE_TIE_WINNER = 2`).

## 5. Test evidence

- `test_conductor_stage1.py`: 35 tests (parametrized) — D4 range/cap/duplicate/bool
  rejection, exact joint factorial balance over 30–129 for all six cells,
  policy_dev cohort disjointness/completeness and cap, SYSTEM_DIRECT and
  profile digest pins, cascade-code identity with `types.py`, retry-list
  disjointness from the typed-rejection contract, look-schedule identity
  with `NAMESPACE_CONFIG`, alpha and population arithmetic, gate-matrix
  positions verified against generated reference programs, visible-slice
  divisibility, bootstrap-seed determinism.
- Full suite: **608 passed** with `-W error`
  (`--ignore=test_countdown.py --ignore=test_gsm8k.py
  --ignore=test_conductor_worker_eval.py`).
- `test_conductor_worker_eval.py` is blocked at collection by an
  **environment regression unrelated to this unit**: NVML driver/library
  mismatch (userspace 595.84 vs loaded kernel driver 595.71) — a system
  package update since the last reboot. Torch CUDA init fails at import.
  Requires a reboot or NVIDIA module reload (Ken's call); recorded here so
  the gap in the test evidence is explicit. No unit-1 change touches CUDA.

## 6. What unit 1 does not do

No construction, qualification, or policy generation was executed; no
worker or policy model was loaded; no frozen Stage-0 artifact changed.
`SYSTEM_DIRECT` adoption is a freeze of existing bytes, not a prompt edit.
The statistics constants freeze decisions only — estimator implementation
and its validation are units 2–3, and the §8.4 tranche may still amend
numerical rules once, in a reviewed plan, before CE1.

Next: unit 2 (population and provenance layer), which issues the successor
source/environment manifest and carries the queued `workerpool.py`
citation fix.
