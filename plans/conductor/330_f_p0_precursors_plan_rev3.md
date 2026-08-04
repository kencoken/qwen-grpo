# 330_f — P0 precursors plan REV3 (response to 329_s)

All four blocking findings amended and the small clarifications
folded in. 326_f + 328_f stand except where superseded below.

## 1. Common random numbers: no checkpoint index in seed derivation (329_s #1)

328_f §6's per-(checkpoint, observation) derivation is WITHDRAWN —
it would give checkpoint zero and later checkpoints different
draws, breaking the charter's same-seed paired comparison. The
frozen derivation is:

```
seed = H(evaluation_domain || base_seed || observation_id
         || completion_slot)
```

— NO checkpoint index. Every checkpoint evaluates under IDENTICAL
random draws (common random numbers); the checkpoint index lives
in PROVENANCE (the trace and the trajectory records), never in
RNG derivation. The SAME rule applies to the two cycle
checkpoints (their own domain string + the cycle base seed).
Domains are separated by construction:
`p0_val_eval` / `cycle_eval` / `p0_train` / `timing_smoke`.

## 2. The cap decomposition, corrected and unit-fixed (329_s #2)

The nominal cadence has ELEVEN evaluations
({0, 4, …, 36, 39} = checkpoint zero + nine intermediates +
final). 328_f priced nine + final; checkpoint zero's ≈420 s was
missing. The frozen decomposition (adopted verbatim):

```
frozen_non_rollout_overhead_seconds =
    checkpoint-zero evaluation (measured, ≈420 s)
  + 9 × (intermediate evaluation + checkpoint write)   [measured]
  + any one-time startup inside the ten-hour clock     [measured]

measured_finalization_reserve_seconds =
    worst rollout batch (max observed group-batch duration)
  + final evaluation (90 groups, measured)
  + final checkpoint write (measured)
  + FULL-RUN trace flush / verification / archival
```

The full-run trace term is NOT the smoke's one-epoch value: the
smoke measures the one-epoch flush/verify/archive cost and the
per-epoch trace volume, and the reserve prices the NOMINAL
39-epoch volume by linear scaling with a conservative rounding-up
(the scaling rule and its inputs are persisted in the beta-smoke
record; falsifiable against the actual P0 closure).

**Cadence indices are persisted in the spine's optimizer-update
units**, not only epoch labels: with 157 groups/epoch and one
group per update, epoch 4 = update 628, …, nominal final =
update 6,123. The `P0ExecutionIdentity` carries BOTH forms; the
trajectory index sets consumed by `assemble_sentinel_trajectories`
use the update units.

## 3. One exact recomputable R_cycle rule (329_s #3)

328_f mixed the registered ledger basis with an itemized sum.
Frozen rule (the reviewer's option, adopted):

1. implement the currently disabled validator-gated
   final-reserve path (`record_provisional_reserve`'s registered
   successor), computing the REGISTERED basis:
   `cohort × multiplier × measured support seconds/observation`
   = 90 × 2 × 2.44 / 3600 = 0.122 h → ceil = **1.0 h**;
2. independently derive the ITEMIZED closure ceiling:
   cycle-surface materialization + two checkpoint evaluations +
   verification/traces/archival (current estimate ≈0.30 h + the
   itemized margins, each component named);
3. the final `R_cycle` = the ROUNDED MAXIMUM of the two,
   persisted with BOTH derivations in the reserve record (the
   coincidence that both round to 1 h is thereby exposed, not
   concealed);
4. a test PROVES the complete cycle-closure maximum (every
   obligation itemized) ≤ the resulting reserve.

## 4. The explicit fail-closed launch-admission boundary (329_s #4)

One consuming operation — `admit_p0_execution` — runs BEFORE
checkpoint zero, and NO trainer entry point can bypass it (the
trainer builder takes its dataset and configuration ONLY from
this boundary's returned bundle). It freshly, fail-closed:

1. loads and verifies all FOUR raw precursor records under their
   freeze pins (val lock, cycle record, R_cycle reserve record,
   beta-smoke record);
2. rederives EVERY cap input from the timing record + the frozen
   cadence + the ledger (P0-local consumed), and re-runs
   `require_launchable` on the freeze's persisted plan;
3. verifies the `P0ExecutionIdentity` under its EXTERNALLY
   reviewed hash and its binding to the reviewed launch-freeze
   hash;
4. verifies the source/driver identities and the live environment
   attestation (the execution manifest as the EXTERNAL argument);
5. runs dataset preparation and the standing gates
   (`prepare_p0_dataset`: equivalence oracle + appendix +
   runtime binding);
6. enforces the envelope inequality:
   `remaining envelope ≥ P0 launch maximum + final R_cycle`.

## 5. Small clarifications (folded in)

- **Engineering resume vs relaunch**: a resume retains the
  existing launch freeze, epoch target and cadence unchanged and
  enforces CUMULATIVE wall time against the same cap; only a
  genuinely new REVIEWED relaunch may rederive the cap.
- **Cycle partial reveal**: if cycle-surface materialization
  partially reveals outcomes, only an EXACT design-preserving
  resume/retry is permitted; otherwise that cohort is retired and
  cycle evaluation is reported UNAVAILABLE — never re-selected.
- **Unit T disclosure**: reviewers receive an automated
  TIMING-ONLY projection from the smoke; the semantic trace is
  retained (provenance) but not inspected until after the P0
  freeze.
- **Substantive semantic overlap check**: the
  latent-semantics/rendered-prompt intersections are computed
  AFTER normalizing away namespace/identity-only fields — an
  empty intersection is substantive, not tautological.
- **Development-only**: all P0, validation, and cycle evidence
  remains development-only (the charter's confirmatory boundary
  is untouched); stated in every unit record.

## 6. Next

Reviewer sign-off on this rev3 → Unit V implementation + freeze.
Lineage 331+.
