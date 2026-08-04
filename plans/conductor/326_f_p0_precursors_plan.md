# 326_f — P0 precursors plan: routing_dev_val lock, cycle/R_cycle, beta smoke, launch admission (for review)

The spine is merged (`conductor_stage1` @82645e8; merge-gate
record 325_f). This plan covers the remaining pre-P0 sequence in
the charter-mandated order (211_f §7 pre-P0 list; 303_f §10;
325_f §2 registered obligations). Each unit keeps its own small
freeze (303_f §2); the `P0LaunchFreeze` pins their reviewed
outputs through the already-frozen `PrecursorOutputs` schema
(`routing_dev_val_lock_sha256`, `cycle_record_sha256`,
`r_cycle_record_sha256`, `beta_smoke_record_sha256`).

Everything below is built AGAINST the frozen artifacts: contract
`d47a63ff…`, canonical runtime profile `202bc377…`, the pinned
157-row epoch `135a72bf…`. Ledger head = the C2 closeout
`2bf50c1e…` (17 entries verify); envelope 3.1305 consumed /
56.8695 remaining; provisional finalization reserve 5.0 GPU-h.

## 1. Unit V — the `routing_dev_val` lock (outcome-blind freeze → GPU tranche → lock)

Charter obligations (211_f §3/§7): adaptive development
validation; NATURAL MIXTURE only (frozen definition: task cells
equally weighted; latent clusters equally weighted within cell;
renderers equally weighted within latent); never trained on;
consulted between runs; the P0 checkpoint-evaluation population
anchored by the checkpoint-zero baseline.

**Step V1 — outcome-blind cohort freeze (CPU).** Frozen BEFORE
any surface value exists, by construction:

- namespace `routing_dev_val` (already in `NAMESPACE_CONFIG`; cap
  500/cell) — identities disjoint from every other namespace by
  the namespace string;
- the six extension cells (code_atomic, fork_join, lookup_atomic,
  lookup_math, math_atomic, math_code), equally weighted;
- latent clusters: the deterministic prefix 0–4 per cell (5 fresh
  clusters per cell — no selection function that could smuggle
  outcome information);
- renderers: ALL THREE per latent (bound_var, goal_first,
  resource_first), equally weighted;
- cohort: 6 × 5 × 3 = **90 observations**;
- the frozen evaluation configuration: decoding from the
  canonical profile `202bc377…` (temperature 1.0, policy cap 128,
  group size 8), a FRESH evaluation seed (20260804), and the
  isolated-RNG discipline (evaluating never perturbs training
  rollout RNG — charter §7);
- registered falsifiable predictions (per the review process):
  identity intersection with ALL existing namespaces = 0;
  materialization cost within the ceiling; the 4^S surface
  complete for every observation (no missing assignment row).

**Step V2 — surface materialization tranche (GPU,
envelope-charged).** The §4 machinery (`dev_support` declaration
→ `materialize_dev_support` → authentication), reusing the
support-launch manifest/preflight/anchored-verifier pattern of
the extension run. Calibration: the extension materialized 864
observations in 0.4934 GPU-h measured; 90 observations scale to
≈0.05 GPU-h plus fixed model-load overhead. **Proposed ceiling:
0.35 GPU-h** (generous for overhead + preflight), admission on
the current ledger head.

**Step V3 — the val lock (CPU).** A lock record binding: the
cohort identities, the natural-mixture weights, the evaluation
configuration (seed + decoding), and the complete surface hashes
— the record whose sha256 becomes `routing_dev_val_lock_sha256`.
Never trained on is structural: the P0 trainer consumes ONLY the
pinned mixture schedule; the val namespace appears nowhere in it.

## 2. Unit Y — `routing_dev_cycle` cohort + `R_cycle` (CPU-only, two records)

Charter: the cycle-end holdout's cohort AND its
checkpoint-selection/evaluation rule are frozen BEFORE P0; its
surfaces are materialized only AT cycle synthesis (one-reveal),
then the population is permanently retired.

- **cycle cohort record**: same natural-mixture shape, namespace
  `routing_dev_cycle`, deterministic latent prefix 0–4 per cell,
  all three renderers (90 observations), NO surfaces now →
  `cycle_record_sha256`;
- **R_cycle record**: the frozen checkpoint-selection/evaluation
  rule → `r_cycle_record_sha256`. Proposal: at cycle synthesis,
  evaluate EXACTLY TWO checkpoints — checkpoint zero and the
  FINAL P0 checkpoint (a fixed, outcome-blind selection; never
  "best-of"), under the same frozen decoding discipline with its
  own fresh seed; one reveal; archived; retired. The rule also
  freezes the abort branch: if P0 ends on the disclosed
  infrastructure-abort path, the last COMPLETE checkpoint stands
  in for "final", disclosed as such.

## 3. Unit T — the beta timing smoke (GPU, bounded)

Purpose (290_f §4; 305_f §5): measure the cap-formula inputs
under the REAL training shape — the canonical profile's beta
1e-3, lr 1e-5, 10-step `constant_with_warmup` — which the C2
zero-update run could not measure:

- `measured_whole_epoch_seconds` — one complete 157-group epoch
  on the pinned schedule (real optimizer updates, warmup active);
- `measured_finalization_reserve_seconds` — checkpoint save +
  finalization measured, replacing the provisional 5.0 GPU-h
  reserve with a measured value;
- the per-checkpoint evaluation cost on the LOCKED val cohort (90
  groups; C2 measured 4.65 s/group ⇒ ≈7 min predicted) — the
  input the cadence decision needs.

Falsifiable predictions: whole-epoch ≈ 12–16 min (C2 measured
12.2 min/epoch at beta 0; beta and warmup add bounded overhead);
eval ≈ 7 min. **Proposed ceiling: 0.6 GPU-h.** The trained state
is DISCARDED — the smoke is a timing instrument, never a
checkpoint source; its adapter deltas are never persisted beyond
verification.

## 4. Unit L — `P0LaunchFreeze` instance + launch admission (the 325_f §2 obligations)

Only after V/Y/T exist:

1. `P0ExecutionIdentity` — the authenticated home for:
   checkpoint/evaluation CADENCE (chosen at this freeze from the
   measured epoch + eval costs through the frozen cap formula —
   the launch-epochs decision and the trajectory index sets come
   OUT of `derive_launch_plan` + cadence, with checkpoint zero
   and the final checkpoint mandatory), the evaluation decoding +
   seed (from the val lock), and the telemetry identity;
2. precursor resolution: all four `PrecursorOutputs` pins
   resolved to their committed records and re-verified;
3. the freeze instance built by `build_p0_launch_freeze`
   (rederived plan; runtime bound to profile + ACTUAL prompt),
   committed, its hash EXTERNALLY reviewed → the loader's pin;
4. launch admission at execution: the execution manifest as the
   EXTERNAL argument; environment attestation against
   `runtime.attested_environment_sha256`; then **checkpoint-zero
   evaluation as P0's FIRST execution under the already-frozen
   record** (charter §7: the freeze precedes its own baseline);
   training follows with NO configuration change.

## 5. Order, gates, cost

| Unit | Kind | Ceiling | Produces |
|---|---|---|---|
| V | CPU freeze → GPU tranche → CPU lock | 0.35 GPU-h | `routing_dev_val_lock_sha256` |
| Y | CPU freeze (two records) | — | `cycle_record_sha256`, `r_cycle_record_sha256` |
| T | GPU smoke | 0.6 GPU-h | `beta_smoke_record_sha256` + measured cap inputs |
| L | CPU freeze + review | — | the reviewed `P0LaunchFreeze` pin + `P0ExecutionIdentity` |

Total new GPU exposure ≤ 0.95 GPU-h against 56.8695 remaining.
Every unit: preregister-before-GPU with falsifiable predictions,
per-unit reviewer pass, ledger admission on the verified head,
the standing spine gates (equivalence oracle + appendix) in every
test set. Sequence: V → Y → T → L → checkpoint-zero eval → P0.

## 6. Next

Reviewer pass on THIS plan → Unit V implementation + freeze
(lineage 327+).
