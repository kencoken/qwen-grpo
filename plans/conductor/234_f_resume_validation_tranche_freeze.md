# 234_f — Step-5 GPU resume-validation tranche: implementation + FREEZE

The 232_s sequence item 2: the tranche is implemented on the REAL
training stack, CPU-tested, and frozen here for review BEFORE the
GPU run. Full CPU suite: **965 passed under `-W error`, TRUE process
exit 0** (49 in the routing battery). No GPU work has run.

## 1. The frozen tranche (lightweight freeze, 211_f §1)

- **Freeze hash `539ccc2c…`** over the complete
  `RESUME_VALIDATION_CONFIG` (config hash **`283523da…`**) +
  question + motivation + budget.
- **EXACT ceiling: 0.5 GPU-hours** (212_f reminder 2 — a hard
  in-loop deadline between phases, not an estimate; expected cost
  is minutes).
- Training shape: the stage-0C profile values — Qwen2.5-3B NF4 +
  LoRA (r16/α32), G=8 completions per group, per-device 2 ×
  grad-accum 4 → 8 completions = exactly ONE group per optimizer
  step, generation at the start of each accumulation cycle — so
  EVERY optimizer step is a v1 boundary by construction (the
  accountant still verifies `generated == consumed` at the save).
- **6 optimizer updates** over a deterministic 6-observation
  schedule (canonical order from the LOCKED Step-4 surface,
  `61c4e85a…`); few-shot system prompt + rendered user message —
  the same construction P0 will use; rewards authenticate against
  the locked surface (malformed → 0; missing row = infrastructure
  abort); every group appends a trace row with its global index.
- **Checkpoint at update 3**: the HF-native checkpoint (optimizer/
  scheduler/dataloader/RNG restore) PLUS the v1 contract bundle
  (adapter.safetensors / optimizer.pt / scheduler.pt /
  rng_state.json under the fixed filename manifest, hashed and
  bound into a `build_checkpoint_record` with the full ten-identity
  set: routing source digest incl. THIS driver, environment
  manifest, config, prompt, cohort, renderer schedule, surface
  manifest, pool fingerprint, cache identity, seed).
- **Comparison tolerance: 0.0 — EXACT, frozen before the test**
  (211_f §11.5). A nonzero difference is a reported finding for
  review, never a silent widening.

## 2. The three runs and the §11 acceptance

1. UNINTERRUPTED: 0→6 updates (saving at 3 too, so the two
   trajectories are structurally identical).
2. INTERRUPTED: 0→3, stops at the bundle.
3. RESUME: fail-closed `validate_resume` (record rehash, ten
   identities, mandatory bundle re-hash under the fixed filenames,
   RNG cross-binding) → `GroupAccountant.restore` →
   `restore_rng_state` → HF `resume_from_checkpoint` → 3→6.

Acceptance (211_f §11, all mechanical):

1. checkpoints only at the v1 boundary (authorize_checkpoint);
2. generated/consumed counters separate and restored exactly;
3. + 4. the interrupted and resumed segments merge through
   `merge_segments` (exact ranges, parent linkage, no
   missing/duplicated groups);
5. final adapter/optimizer/scheduler state EXACT (tolerance 0.0),
   next sampler/renderer identity, counters, and merged trace
   cardinality all equal between the uninterrupted and
   interrupted+resumed runs (`compare_runs`).

Lifecycle: the same failure-safe shape as Step 4 — full validation
(live canonical environment, locked-surface reload, schedule
identities) BEFORE the irreversible ledger admission
(`resume_validation` launch, freeze + config hashes in its freeze
field, 0.5 h allocation admitted against the reserve rule:
remaining 59.93 ≥ 0.5 + 5.0); any post-admission failure appends an
ABORTED closeout with measured cost and the content-hashed partial
inventory; success writes `validation_record.json` and a complete
closeout binding it plus the exact terminal inventory.

## 3. CPU verification in this commit

- The frozen config re-verifies against the COMMITTED Step-4
  artifacts: the schedule/reward tests reconstruct the surface from
  committed evidence bytes (the 233_f pattern) and load it under
  the committed lock — on any clean clone.
- Deterministic schedule + identity hashes; authenticated reward
  (valid = exact payoff, malformed = 0, missing row refuses,
  partial groups refuse, trace rows carry global indices);
  comparison refusals for tensor drift (naming the worst key),
  counter drift, sampler drift, and trace-cardinality drift.

## 4. Next

Reviewer pass on this freeze, then the GPU run
(`execute_resume_validation` with the committed ledger head
`264066e6…`), its close-out record, and — per 232_s — the unchanged
grouped-probe freeze (step 6).
