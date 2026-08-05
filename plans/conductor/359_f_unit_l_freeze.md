# 359_f — Unit L (rev1): the REAL P0LaunchFreeze + P0ExecutionIdentity + fail-closed admission (for review)

Unit L per the signed identity graph (328_f §4) and the
fail-closed boundary (330_f §4), consuming the authenticated
smoke record and the 39-epoch launch plan exactly as the
execution sign-off directs. Full suite: **1038 passed under
`-W error`, TRUE exit 0** (1036 + two Unit-L tests). Two
persisted artifacts and their pins (§2) are presented for
external review. **No GPU work; no real ledger append** — the
admission was rehearsed end-to-end on a COPY of the real ledger;
the real chain still heads at `df4bf7ad…`.

## 1. The implementation (`tasks/routing/p0_execution.py`)

**Step 1 — the chain-authenticated smoke record.**
`authenticate_smoke_record`: the record file bytes must hash to
the reviewed pin `a9d6f55b…`; the committed chain must verify;
the COMPLETE smoke closeout (`df4bf7ad…`, closing launch
`4738b32b…`) must bind exactly that file hash; the record must
bind the signed smoke freeze `d2d87971…`; the measurements
revalidate through the closed 13-field schema. A forged pin or a
re-anchored closeout refuses (regressions).

**Step 2 — the BINDING derivation.** `derive_real_launch_plan`:
every cap input REDERIVES from the authenticated timing record
through the frozen 330_f §2 mapping (`derive_cap_inputs`);
`cumulative_consumed_seconds` is P0-LOCAL zero at a fresh
launch; the result must equal the projection the smoke record
persisted (a post-review drift in record or mapping refuses).
Result: **nominal 39 / capacity 41 / launch 39,
`no_extra_training`, 2 spare epochs never trained** — exactly
the signed-off plan.

**Step 3 — the REAL P0LaunchFreeze.** Built by the Unit-5
`build_p0_launch_freeze` (plan rederived through
`require_launchable`; runtime bound to the canonical profile +
the ACTUAL prompt) with:

- the four reviewed precursor pins: val lock `2aecdf28…`, cycle
  record `d617ab5f…`, R_cycle reserve `e13cf4d3…`, beta-smoke
  record `a9d6f55b…`;
- **the frozen P0 training seed `20260807`** — pairwise-distinct
  from the val (20260804), cycle (20260805), and smoke
  (20260806) seeds, asserted at every build (328_f §4);
- the COMMIT-INDEPENDENT attested environment, which must equal
  the C2-reviewed attestation `372f958f…` — the freeze refuses
  to bind an unreviewed stack.

Persisted EXACTLY ONCE (fail-fast on an existing file) to
`plans/conductor/p0/p0_launch_freeze.json`.
`load_real_launch_freeze` additionally re-asserts the four REAL
precursor pins and the frozen seed.

**Step 4 — the cadence, both unit systems.** `derive_cadence`:
epoch labels {0, 4, …, 36, 39} with checkpoint zero AND final
MANDATORY, out-of-horizon trimmed; update indices = label × 157.
For launch 39 this reproduces the frozen
`CADENCE_UPDATES = (0, 628, …, 5652, 6123)` exactly
(test-asserted); a 10-epoch horizon trims to {0, 4, 8, 10}.

**Step 5 — the P0ExecutionIdentity** (schema
`p0-execution-identity-v1`), constructed ONLY against the
externally reviewed freeze hash and BINDING it (328_f §4):

- the cadence (both forms) and the trajectory index sets
  consumed by `assemble_sentinel_trajectories` (update units —
  the checkpoint and evaluation trajectories are the cadence);
- the evaluation identity FROM the reviewed val lock: domain
  `p0_val_eval`, base seed 20260804, the CRN seed rule with
  **NO checkpoint index** (common random numbers — every
  checkpoint evaluates the full 90-observation cohort under
  IDENTICAL per-slot seeds), the full sampling identity, and
  the frozen 720-entry per-slot seed schedule pin `7f5f6518…`
  RECOMPUTED at build (342_f realization binding);
- the telemetry identity: the closed sentinel-block field
  schema (the Unit-5 tuples) in optimizer-update units;
- the training seed (== the freeze's, distinctness re-checked).

Persisted EXACTLY ONCE to
`plans/conductor/p0/p0_execution_identity.json`; the strict
loader REQUIRES the external hash AND rederives the complete
record from the frozen constructors — a REHASHED identity with
a mutated cadence index refuses at the rederivation
(regression).

**Step 6 — the execution manifest** (the EXTERNAL argument,
305_f §1 — never a freeze field): closed 12-key schema binding
both reviewed pins, the contract, the source digest, the frozen
lineage parent (`df4bf7ad…` — the smoke-closure head), run root
`runs/routing-dev/p0-v1`, and **budget = the contract's 10.0 h
operational ceiling**. Every configuration-owned field is
rederived at validation; a re-signed budget refuses.

**Step 7 — `admit_p0_execution`** (330_f §4, fail-closed, in
order): (1) all four precursors verified fresh under their pins
(val lock WITH surface-byte authentication, restoring committed
evidence on a clean clone); (2) cap inputs rederived +
`require_launchable` re-run + the freeze's persisted plan must
equal the fresh derivation; (3) the identity under its reviewed
hash, bound to the reviewed freeze hash; (4) live environment
attestation against the freeze's commit-independent expectation;
(5) `prepare_p0_dataset` + the standing oracles (equivalence +
appendix), 6,123 trainer rows; (6) the envelope inequality
remaining ≥ 10.0 + final R_cycle 1.0, with the **346_f
carry-forward**: the persisted final-reserve entry must exist
EXACTLY ONCE and equal the pinned reserve record (duplicates and
divergent values refuse — regressions). The FINAL act is the
ledger admission itself through the new manifest-MANDATORY
`training_run` branch (kind, exact manifest hash, budget
equality, both pins bound, ACTUAL parent, first-launch lineage =
the frozen parent, open → refuse, complete → refuse: **a
relaunch is a REVIEWED decision, never a retry**). The returned
bundle is the ONLY source of trainer dataset/configuration — no
trainer entry point bypasses the boundary.

## 2. The persisted artifacts and pins (for external review)

| artifact | pin |
|---|---|
| `plans/conductor/p0/p0_launch_freeze.json` (`P0_LAUNCH_FREEZE_SHA256`) | `88c6635aadb2d0ca1c766efc937123b7ece427190cfe3ce3675ac8f269ebccfc` |
| `plans/conductor/p0/p0_execution_identity.json` (`P0_EXECUTION_IDENTITY_SHA256`) | `4c763cc9f21de2bfc05700b22b48529ed7f2e83ed68225a1ab115f4cdfa5a4ae` |

Ordering note (328_f §4): the freeze was generated FIRST on the
clean code commit and its hash passed as the EXPLICIT argument
to the identity builder — the identity binds `88c6635a…` by
value, and both pins are presented together for this review, as
Unit Y presented its two records.

## 3. Rehearsed admission (on a ledger COPY)

The complete `admit_p0_execution` ran against a byte copy of the
real ledger at head `df4bf7ad…` with the REAL smoke execution
environment as the live attestation: every gate passed
(`launch_plan REDERIVED`, oracles PASS, 6,123 groups, reserve
cross-check 1.0), and the `training_run` entry appended on the
copy with parent = the frozen lineage. A second admission on the
grown copy refuses (`a prior P0 attempt is OPEN`); a
non-attesting environment refuses; the REAL ledger is untouched
(test-asserted). Manifestless and wrong-kind admissions refuse
at the ledger.

## 4. Test-suite note

The generic ledger tests used `training_run` as an arbitrary
launch kind in two places; with the manifest now mandatory they
use `standalone_evaluation` (the same repointing 353_f §5 did
for `engineering_smoke`).

## 5. Scope and next

Development-only throughout; nothing here evaluates routing
learning. After this review records the §2 pins: the P0
execution runner (checkpoint-zero evaluation as P0's FIRST
execution under the already-frozen record, then training with NO
configuration change, sentinel trajectory capture per the
identity's index sets) → narrow prelaunch → P0 launch on head
`df4bf7ad…`.
