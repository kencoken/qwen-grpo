# 230_f — Support-materialization FREEZE (211_f §15 step 4; Step-4 GO)

Ken signed off the infrastructure (229_f) and directed Step 4
(2026-07-28). `support_run.prepare_support_launch` ran on the GPU
host with the real four-worker runtime and the LIVE environment
manifest; this document commits the prelaunch records and the
identities the execution boundary will consume. The support
tranche is authorized by the signed charter (212_f §1); this freeze
is its local, outcome-blind record — committed BEFORE any worker
executes on `routing_dev`.

## 1. The frozen launch (externally committed identities)

- **Support-launch manifest hash (the execution boundary's
  `expected_manifest_sha256`):**
  `ea4c28061f49275e5902d811a3626e772867c1d99de566978353764e0e67ca22`
- **Ledger head at launch: EMPTY** (`expected_head_sha256 = None`;
  `plans/conductor/routing_dev_ledger.md` does not exist yet — the
  admitted support launch will be the chain's first entry).
- Declaration `290c7410…`: namespace `routing_dev`, ALL six cells ×
  the outcome-blind prefix `[0..5]` (36 latent clusters), ALL three
  renderers in canonical order, visibility `private` — 108 rendered
  observations, 4,824 planned step executions, full `4^S` surface
  contract; worker pool `wp-197e286115f56e4a`, worker-visible
  `wv-4e196a1c467d108b`, request contract
  `worker-blocks-task-last-v1`, cache identity
  `worker_completions/slw/worker-blocks-task-last-v1`.
- **First-probe rule** (`0b616b88…`, kind
  `routing-dev-first-probe-v1`): group size 8, ALL renderers,
  prefix 6 per cell (factor-balanced), **4 groups per observation**
  (→ the later probe: 432 groups, 3,456 completions, within its 3
  GPU-h charter ceiling). Frozen HERE, before execution, and bound
  into the manifest; the surface lock will carry it and no other
  rule can bind (220_s F3).
- Search cap: **108 rendered observations** (the declaration
  exactly covers it — no slack, no silent expansion).
- Budget: **1.0 GPU-h** (measured stage-0 support timing ≈ 46 s for
  804 planned steps; 4,824 planned steps ≈ 5–10 min with loading
  overhead — 1.0 h is a hard ceiling, not an estimate).
- Environment manifest `b7a2ce8f…` (live-built, canonical,
  self-hash validated; source identity = the current tree);
  routing source digest `ac90348a…` with driver
  `tasks/routing/support_run.py`; runtime profile
  `rtp-8510479a336ee0dc` (the frozen four-worker profile with the
  dev-track cache path `runs/routing-dev/support-cache/`).
- Scientific-design identity: computed from the manifest at
  admission (`scientific_design_sha256`) — any aborted-retry must
  preserve it (224_s F2).

The four prelaunch records are committed byte-for-byte under
`plans/conductor/routing_dev_support_prelaunch/` (declaration,
environment manifest, support-launch manifest, probe rule); the
runner will consume its own persisted copies under
`runs/routing-dev/support-v1/prelaunch/` and the execution boundary
verifies them against the manifest hash above.

## 2. Execution plan (the fixed 223_f/227_f/229_f sequence)

`execute` validates everything (manifest recompute, rule match,
frozen-env revalidation, LIVE-environment attestation — this freeze
commit is the allowed documentation-only `git_commit` change —
output preflight) BEFORE the irreversible admission; admits the
launch (entry names the manifest, carries its budget and design
identity); materializes under that admission; locks; reloads
fail-closed; discloses direction yields; selects `c_fixed_dev`;
binds the probe cohort; and closes out complete (with the exact
terminal inventory) or aborted (with measured cost and partial
evidence bound by hash).

## 3. Provisional-reserve plan (recorded AFTER the run, via
`record_provisional_reserve` against the verified terminal run)

- `assumed_cohort_size = 3000` rendered observations — a
  deliberately generous ceiling for the cycle-end evaluation
  (`routing_dev_cycle` at, e.g., ≤166 latents/cell × 3 renderers
  ≈ 3,000; the actual cycle cohort will be frozen pre-P0 and is
  expected to be smaller).
- `evaluation_multiplier = 2.0` — surface materialization plus
  selected-checkpoint inference, verification, traces and archival.
- `measured_seconds_per_observation` — DERIVES exactly from the
  completed closeout (`consumed × 3600 / 108`); never asserted.
- `rounding = ceil_to_whole_gpu_hours`; `r_cycle = ceil(basis)`.
- Status: provisional (final reserves are disabled until the cycle
  validators exist, 228_s F2).

## 4. Boundary

This freeze authorizes exactly the one-shot support materialization
described above, within its 1.0 GPU-h allocation under the 60 GPU-h
envelope. The probe itself remains a separate tranche with its own
freeze (211_f §15 steps 5–6); nothing here touches any frozen
Stage-0/Stage-1 artifact; every output is development data
permanently.
