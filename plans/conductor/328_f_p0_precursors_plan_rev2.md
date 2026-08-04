# 328_f — P0 precursors plan REV2 (response to 327_s)

All five blocking findings amended; the smaller clarifications
folded in. The unamended parts of 326_f (cohort construction,
ceilings, order V → Y → T → L, the §5 table) stand as written
except where superseded below.

## 1. R_cycle and the P0 finalization reserve are SEPARATE (327_s #1)

The 5.0 GPU-h is the provisional CYCLE-END reserve `R_cycle`
(231_f: basis 3,000 assumed observations × 2.0 multiplier ×
2.44 s / 3600 = 4.07 h, rounded up to 5.0) — 326_f mislabelled it
a finalization reserve. Corrected:

- **Unit Y produces the numeric FINAL `R_cycle`** as a RESERVE
  RECORD (`r_cycle_record_sha256` identifies this record, which
  BINDS the cycle cohort record): the registered 231_f basis and
  rounding rule retained, re-priced on the now-known obligations —
  cycle-surface materialization (90 observations; extension
  calibration ≈0.05 GPU-h), selected-checkpoint inference (two
  checkpoints × 90 evaluation groups ≈0.23 GPU-h at the C2
  4.65 s/group), verification, traces, archival — × the 2.0
  multiplier, rounded up as in 231_f (expected ≈1.0 GPU-h). It
  REPLACES the provisional 5.0 in the ledger via the registered
  reserve-replacement path, disclosing the freed difference.
- **Unit T separately measures the P0 run's
  `measured_finalization_reserve_seconds`** (§3). The two
  quantities never share a field or a record.

## 2. The timing smoke never touches `routing_dev_val` (327_s #2)

The timing-evaluation cohort is a SHAPE-MATCHED,
ALREADY-DEVELOPMENT-EXPOSED `routing_dev` cohort: the same
6-cell × latent-prefix-0–4 × 3-renderer crossing (90
observations) drawn from the LOCKED extension surface — surfaces
already materialized and authenticated; no new exposure; the
locked val cohort receives NO policy output before checkpoint
zero. The smoke run has:

- a dedicated seed (distinct from every other registered seed), a
  dedicated run root, and its own execution identity;
- disclosure BEFORE P0 limited to timing, memory, and
  infrastructure results — no reward, routing, or learning
  observable is reported;
- no checkpoint and no observed learning result reused in P0 (the
  trained state is discarded after verification);
- full retained provenance (manifests, trace, preflight) so what
  ran is verifiable.

## 3. The executable cap/cadence mapping (327_s #3)

**The cadence rule is frozen NOW, before Unit T** (the reviewer's
"simple solution", adopted): checkpoint + evaluation every **4
epochs** on the NOMINAL horizon, plus the mandatory endpoints —
checkpoint zero (evaluation-only) and the final epoch. Nominal
index sets: checkpoints/evaluations at epochs
{0, 4, 8, …, 36, 39}. After the cap is derived ONCE,
out-of-horizon indices are TRIMMED (the final index becomes the
capped epoch) WITHOUT reclaiming the reserved time.

The deterministic mapping from Unit-T measurements to the frozen
cap formula's inputs:

- `measured_whole_epoch_seconds` — the smoke's measured wall time
  for one complete 157-group epoch (rollout + optimizer updates,
  warmup active); no evaluation time included;
- `measured_finalization_reserve_seconds` — the sum of MEASURED
  components covering the charter's worst case: one worst-case
  rollout batch (the maximum observed group-batch duration), the
  final evaluation (90 groups, measured), the checkpoint write,
  and the trace flush + archival — each measured in the smoke,
  summed once (no component double-counted in overhead);
- `frozen_non_rollout_overhead_seconds` — the SCHEDULED
  intermediate evaluations and checkpoint writes priced at the
  nominal cadence: (number of nominal intermediate checkpoints) ×
  (measured per-evaluation + per-checkpoint-write seconds); the
  final checkpoint/evaluation is priced in the reserve, not here;
- `cumulative_consumed_seconds` — **P0-LOCAL, zero at a fresh
  launch** (326_f's implication that the 3.1305 h cycle spend
  enters the formula is WRONG and is withdrawn; the cycle
  envelope remains tracked in the ledger, not in the cap
  formula). On a registered retry it carries the P0-local spend
  of prior attempts (§6).

Worked expectation (falsifiable at Unit T): whole-epoch ≈ 12–16
min ⇒ capped epochs ≈ floor((36000 − reserve ≈ 1000 −
overhead ≈ 9 × (420 + write)) / ~840) ≈ 33–38 — the DISCLOSED
under-target branch remains the expected outcome (290_f).

## 4. Unit L follows the signed identity graph (327_s #4)

`P0ScienceContract → P0LaunchFreeze → P0ExecutionIdentity /
admission` — 326_f's ordering is corrected to:

1. resolve all four precursor pins to their committed records and
   re-verify them; derive the launch plan
   (`derive_launch_plan` over the Unit-T measured inputs);
2. build and persist the `P0LaunchFreeze`
   (`build_p0_launch_freeze`: plan rederived, runtime bound to
   the canonical profile + ACTUAL prompt) and obtain its
   EXTERNALLY reviewed hash;
3. only then construct the authenticated `P0ExecutionIdentity`
   BINDING that reviewed freeze hash, the exact
   (cap-trimmed) checkpoint/evaluation index sets, the evaluation
   configuration (from the val lock), and the telemetry schema;
4. admission at execution: the execution manifest as the EXTERNAL
   argument + live environment attestation against the freeze
   expectation → checkpoint-zero evaluation as P0's FIRST
   execution → training with no configuration change.

**The P0 training seed is frozen explicitly in the
`P0LaunchFreeze`** (`runtime.seed`), distinct by construction
from the validation evaluation seed (20260804), the cycle
evaluation seed (fresh at Unit Y), and the timing-smoke seed
(fresh at Unit T) — a test asserts pairwise distinctness.

## 5. The cycle record's frozen meaning (327_s #5)

The cycle cohort record binds, before any surface exists: the
generator/profile identity, the ORDERED observation ids, the
renderer schedule and natural-mixture weights, the
worker/prompt/request/surface identities it will be materialized
against, the cycle evaluation seed, the checkpoint rule, and the
future materialization plan — through the EXISTING declaration +
verifier machinery (`build_dev_declaration` pattern), not new
code.

"Final P0 checkpoint" is resolved by DECLARATION: **P0 closes
this development cycle** — cycle synthesis follows P0 directly;
no continuation or fork precedes it. The abort clause is
narrowed: "last complete checkpoint" applies ONLY after a
TERMINALLY CLOSED abort (a closed-out infrastructure-abort
closeout), never a resumable interruption; if no positive-index
checkpoint exists, the zero-vs-final comparison is UNDEFINED and
recorded as such — checkpoint zero is never evaluated twice.

## 6. Smaller clarifications (folded in)

- **Semantic separation**: beyond namespace-string disjointness,
  Unit V adds cheap zero-overlap checks across
  training/validation/cycle populations on (a) latent semantics
  (reference-program content) and (b) rendered policy prompts —
  set-intersection tests, all empty.
- **Interpretive framing**: with five latents per cell, val
  results are PAIRED, LATENT-LEVEL DESCRIPTIVE evidence — never
  completion-level precision claims. Carried into every val
  report header.
- **The val lock binds the complete evaluation identity**: the
  exact ORDERED observation list, batching, full generation
  options, and DOMAIN-SEPARATED seed derivation (per-checkpoint,
  per-observation seeds derived by hashing the frozen base seed
  with the checkpoint index and observation id — not one bare
  integer reused).
- **Abort/retry rule (all GPU units)**: a partial materialization
  or partial smoke can never be locked; an identical-design retry
  receives a NEW execution identity and CUMULATIVE cost
  accounting; any material design change requires a reviewed
  successor freeze.
- **Scope restatement at launch**: the launch record restates
  that P0 studies Q1 plus coarse, cell-correlated Q2 hierarchical
  unlocking; Q3 remains out of scope (301_f boundaries).

## 7. Next

Reviewer sign-off on this rev2 → Unit V implementation + freeze
(V1 outcome-blind cohort freeze; V2 materialization tranche
≤0.35 GPU-h; V3 lock). Lineage 329+.
