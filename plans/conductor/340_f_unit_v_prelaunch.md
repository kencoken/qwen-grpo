# 340_f — Unit V LOCKED at rev5; the REAL prelaunch manifest (narrow launch sign-off requested)

Unit V is approved and locked at rev5 (331_f…339_f @822bd8e).
Per 338_s/339_f, the REAL prelaunch bundle has been prepared on
this machine (the launch box) and is recorded here for the NARROW
launch sign-off. **No GPU launch has been admitted** — the ledger
head is untouched at the frozen C2 closeout; execution follows
only after this record is signed, via `execute_val_run` with the
manifest hash below as the externally frozen argument.

## 1. The prepared prelaunch bundle (exact hashes for sign-off)

Prepared by `prepare_val_launch()` at HEAD `822bd8e` (clean tree,
`git_dirty: 0`), persisted under
`runs/routing-dev/val-surface-v1/prelaunch/` (declaration,
environment manifest, val-launch manifest, tranche freeze):

| field | value |
|---|---|
| **`manifest_sha256`** (the launch argument) | `424b692d2e9f4557d88c3f7ed852931d67fbcbe6589eae54a9c4ef35cc0fe6d2` |
| `scientific_design_sha256` | `a9ca17c39b2ddc347ce1bf0002cad578017a65376681703d9d307ed6e1c902fa` |
| `declaration_sha256` | `acc17de79384c6f570b5d0af12ba48fdc82bfae2114e923cd8a68aa765c0ca6d` |
| `environment_manifest_sha256` | `bd1dffc177e69af7a191f3a0b00be65a75001ddd0eb9adb8e2a763d565be01a3` |
| `routing_source_sha256` | `f82a2bba0678b029f3df8991c129cee7cd28333e7ff77df7afca4a734aa95818` |
| `val_config_sha256` (rederived) | `73376e07…` (the signed pin) |
| `val_freeze_sha256` (rederived) | `8ba9677f…` (the signed pin) |
| `lineage_parent_sha256` | `2bf50c1e…` (the frozen C2 closeout — equals the CURRENT verified ledger head) |
| `execution_root` | `/home/ken/qwen-grpo/runs/routing-dev/val-surface-v1` (the registered attempt-1 root) |
| `budget_gpu_hours` | 0.35 |
| declaration | 90 observations; `worker_visible_fingerprint` `wv-4e196a1c467d1…`; `runtime_profile_fingerprint` `rtp-8510479a336e…` (the REAL pool, loaded and fingerprinted at preparation) |

Revalidation from the persisted bytes at recording time:
`validate_val_launch_manifest(recompute=True)` PASSES (closed
schema; every configuration-owned field rederived; the source
digest recomputed from the tree; the persisted tranche freeze
byte-equal to the live rederivation).

Note (222_s F2 policy, unchanged): committing THIS record moves
HEAD; `git_commit` alone may differ between preparation and
launch, and the routing source digest is unaffected (the commit
adds only a `plans/` document).

## 2. What the launch will do (already signed, restated)

`execute_val_run(expected_manifest_sha256 = 424b692d…,
expected_head_sha256 = 2bf50c1e…)`: lineage check → full
pre-admission validation → `val_materialization` admission
(0.35 GPU-h against the envelope, reserve intact) →
materialization of the 90-observation 4^S surface under the
budget deadline → surface lock → the three-way overlap gate
(alpha-normalized semantic intersections must be 0; template
overlap disclosed at the frozen membership) → the val lock → the
chain-authenticated terminal verifier → the success closeout
binding the complete inventory. Predictions on record (the
signed freeze): cost 0.05–0.15 GPU-h within the 0.35 ceiling;
complete surfaces; overlap gate values equal the pre-launch
measurements.

## 3. Next

Narrow sign-off of the §1 hashes → V2 GPU launch → V3 lock
record + closeout → Unit Y.
