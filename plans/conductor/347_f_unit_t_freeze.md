# 347_f — Unit T (rev1): the beta timing smoke — frozen design + CPU boundaries (for review)

Issued from the staging draft with the post-Y state, per the
SIGNED precursors plan (328_f §2 isolation; 328_f §3 + 330_f §2
the frozen cadence and the executable mapping; 330_f §5
disclosure and abort/retry). Full suite: **1034 passed under `-W
error`, TRUE exit 0** (1033 + the Unit-T design test).

**Scope of THIS rev**: the frozen design and every CPU-testable
boundary in `tasks/routing/p0_smoke.py` — the config and pins,
the timing cohort, the deterministic measurement→cap-input
mapping, the worked non-binding projection, and the CLOSED
measurement schema. The instrumented GPU runner (the two-phase
prepare/execute against these boundaries, mirroring the Unit-V
pattern) is the rev2 deliverable once this design is signed — the
same freeze-before-GPU order every unit has followed. The staged
draft's §7 open items are resolved below.

## 1. Identities and context

- **`SMOKE_CONFIG_SHA256` =
  `cda554d2909568d477756e2d4c51f441083e66b1d9609de8b65910af3db9e62c`**
- **freeze record =
  `168728b902d5d1748ab638f5e22e979d8a4dd8a8b06492fd775eac75ead18997`**
- lineage parent = the Unit-Y final-reserve entry `6fea9e3b…`
  (the current verified head, 20 entries); envelope 56.8058
  remaining, FINAL reserve 1.0.
- runtime profile `202bc377…`; contract `d47a63ff…`; ledger kind
  `engineering_smoke`; **budget 0.6 GPU-h**; run root
  `runs/routing-dev/beta-smoke-v1`; smoke seed **20260806**
  (pairwise-distinct from val 20260804 and cycle 20260805 —
  test-asserted).

## 2. The frozen design

- **Training shape**: the canonical profile exactly (beta 1e-3,
  lr 1e-5, 10-step `constant_with_warmup`, 2×4, NF4 + fp32 LoRA,
  pinned trainer settings); ONE complete 157-group epoch of the
  pinned mixture through the STRICT spine loader under the
  reviewed contract pin. The trained adapter is verified to
  differ from checkpoint zero (an infrastructure fact) and
  DISCARDED.
- **The timing cohort (328_f §2)**: 90 shape-matched
  `routing_dev` observations (prefix 0–4 × six cells × three
  renderers), EVERY one asserted to be on the LOCKED extension
  surface — already development-exposed; the locked
  `routing_dev_val` cohort receives NO policy output before
  checkpoint zero. Resolved from the draft's open item: the eval
  pass uses the FROZEN sampling identity (the measured cost is
  the real evaluation cost); outputs discarded unread.
- **The frozen cadence, both unit systems**: epochs
  {0, 4, …, 36, 39} = updates {0, 628, …, 5652, 6123}; eleven
  evaluations; cap derived once, out-of-horizon indices trimmed
  without reclaiming reserved time.
- **Instrumentation points (resolved from the draft's open
  items)**: startup (load → first update); whole-epoch (first
  rollout → 157th update end, NO eval time); ALL 157 per-group
  rollout wall times ("worst rollout batch" = their maximum);
  checkpoint write; the three eval-pass timings (checkpoint-zero
  / intermediate / final, each a 90-group pass);
  one-epoch trace flush/verify/archive + the per-epoch trace
  volume; peak reserved VRAM; the warmup lr trajectory (updates
  1–10 + the plateau — must ramp monotonically to the constant
  plateau, enforced by the schema).
- **The trace-scaling rule, frozen**: `full_run_trace_seconds =
  ceil(one_epoch_seconds × 39 × 1.2)` (nominal horizon, 1.2
  conservatism multiplier).

## 3. The deterministic mapping and the closed schema (CPU-tested now)

- `validate_measurements`: a CLOSED field set — a semantic field
  (e.g. `mean_reward`) structurally CANNOT enter the record
  (regression); 157 per-group times required; the warmup
  trajectory shape enforced.
- `derive_cap_inputs`: the verbatim 330_f §2 decomposition —
  overhead = ckpt-0 eval + 9 × (intermediate eval + write) +
  startup; reserve = worst batch + final eval + final write +
  the scaled full-run trace; `cumulative_consumed_seconds = 0`
  (P0-local). Tested against hand-computed synthetic values.
- `worked_launch_projection`: `derive_launch_plan` over the
  derived inputs, labelled `binding: False` — resolved from the
  draft's open item: the projection IS executed inside the smoke
  record, and the BINDING derivation happens at the
  P0LaunchFreeze with the persisted inputs.

## 4. Registered falsifiable predictions

Whole-epoch 12–16 min; eval pass ≈7 min; checkpoint write
seconds-scale; derived capacity 33–38 epochs (the DISCLOSED
under-target branch remains the expected P0 outcome); the warmup
ramp observed; cost 0.35–0.45 GPU-h within the 0.6 ceiling.

## 5. Next

Reviewer pass on this design (recording the §1 pins) → rev2: the
instrumented two-phase GPU runner against these boundaries (with
its own prelaunch review of the prepared manifest) → the smoke
launch on head `6fea9e3b…` → the timing-only projection → Unit L.
