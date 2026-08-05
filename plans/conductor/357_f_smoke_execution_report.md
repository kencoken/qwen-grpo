# 357_f — Unit T beta-smoke EXECUTION REPORT (timing-only, for execution sign-off)

The smoke ran to COMPLETION under the signed 356_f rev2
identity: manifest `6c717d47…` admitted on head `6fea9e3b…`,
**0.3117 GPU-h measured** against the 0.75 ceiling. Every shape
proof held, both in-run terminal verifications passed, the
post-hoc chain-authenticated verification passes from a fresh
process, and the trained state was verified then discarded. Per
the frozen rule this report is TIMING-ONLY: no reward, payoff,
or routing content appears here or appeared on the console
(grep of the full console log: zero reward/KL/loss lines; only
model-loading bars and the known benign bitsandbytes CUBLASLT
warning).

## 1. Ledger state (entries 21–22, committed at closure)

| item | value |
|---|---|
| launch entry (21) | `4738b32b3e1cdd079235062f1587d4326adb030daf80c44eb0484aef470c0d90` on parent `6fea9e3b…` (the frozen head; first-launch lineage check bound) |
| closeout entry (22) = **NEW HEAD** | `df4bf7ad7c649a5b550b58673368811854c42493125f86a68e6abbf5ce91da56`, `terminal_status: complete`, consumed **0.3117** |
| envelope | 3.5059 consumed / **56.4941 remaining**; FINAL 1.0 reserve intact |
| chain | 22 entries verify under the new head |

The worktree carries ONLY the ledger modification; per the
V-established closure rule the entries are committed UNCHANGED
in the closure commit after this sign-off.

## 2. Predictions vs measurement — one band miss, disclosed

- Ceiling 0.75: **held** (0.3117, 42% of ceiling).
- **Prediction band 0.50–0.65: MISSED LOW** — the measurement is
  below the band. The conservatism came from pricing each eval
  pass at the ~7-min allowance (actual: 142.95 s / 142.72 s for
  90 observations — the allowance was ~3× actual) and from the
  C2-derived rollout scaling (actual per-group generation sum
  396.6 s over 157 groups, max single group 2.77 s). The error
  is entirely in the safe direction, but the band was stated as
  a falsifiable prediction and it was wrong; the cap arithmetic
  consumes only MEASURED values, so no downstream quantity
  inherits the misprediction.
- All frozen falsifiers passed: exactly 157 optimizer updates;
  warmup trajectory exactly `1e-5·i/10 → 1e-5` plateau
  (rel-tol 1e-6); epoch wall 827.16 s ≥ 396.64 s group-timing
  sum; `adapter_state_changed` True; 10 reference-KL logged
  events (count only); peak reserved VRAM 6,652 MiB (fits the
  4090 with wide margin).

## 3. The validated measurements (closed 13-field set)

| field | value |
|---|---|
| `startup_seconds` | 7.381 |
| `checkpoint_zero_eval_seconds` | 142.955 |
| `whole_epoch_seconds` | 827.157 |
| `per_group_generation_seconds` | 157 entries; sum 396.641, max 2.771 |
| `checkpoint_bundle_write_seconds` | 0.759 |
| `post_epoch_eval_seconds` | 142.721 |
| `trace_flush_archive_seconds` | 0.0018 |
| `per_epoch_trace_bytes` | 90,367 |
| `peak_reserved_vram_mib` | 6,652 |
| `warmup_lr_trajectory` | exact frozen shape (11 values) |
| `optimizer_updates` | 157 |
| `reference_kl_logged_events` | 10 |
| `adapter_state_changed` | True |

## 4. The timing-only worked projection (NON-BINDING)

From `worked_launch_projection` (recomputed and persisted in the
record; the BINDING derivation happens at the P0LaunchFreeze in
Unit L):

- eval price = max(142.955, 142.721) = **142.955 s**, used
  everywhere; measured finalization reserve **147.485 s**
  (worst batch 2.771 + eval 142.955 + bundle 0.759 + scaled
  trace 1.0).
- frozen non-rollout overhead **1,443.757 s** (ckpt-0 eval +
  9 intermediate (eval+bundle) + startup).
- available generation seconds 34,408.8 of the 36,000
  operational ceiling → **capacity 41 epochs ≥ nominal 39 →
  `launch_epochs = 39`, branch `no_extra_training`, 2 spare
  epochs not trained, `launchable: true`** under cap rule
  `p0-cap-v1`.

## 5. Verification and evidence

- In-run: `verify_smoke_run` passed BEFORE the success closeout
  and was re-run against the COMPLETED head (352_s #3) — both
  inside the exit-0 run.
- Post-hoc from a fresh process: **PASS** against committed-file
  head `df4bf7ad…` (chain-authenticated launch, closed record
  schema, projection recomputed, environment cross-bindings,
  exact inventories, trained state ABSENT).
- Terminal inventory is exactly the 9 files (3 prelaunch +
  `execute_env_manifest.json` + `smoke_record.json` + 4 sealed
  `.gz`); `checkpoint_proof` counters 157/157/157/1256;
  `smoke_record.json` sha256
  `a9d6f55b6300b97df03135beed4b82cb82ff5d555f7d1eee48688cf88a743b80`.
- Development-only binding stands: nothing here retunes P0
  mixture, prompts, or workers; the measurements feed ONLY the
  frozen cap formula.

## 6. Requested sign-off + next

Approve: (1) the measured 0.3117 GPU-h and entries 21–22 for the
closure commit (entries unchanged, V-style); (2) the
measurements as the cap-arithmetic inputs Unit L will consume
through `derive_cap_inputs`/`derive_launch_plan` at the
P0LaunchFreeze. Then: Unit L (P0LaunchFreeze instance +
P0ExecutionIdentity + `admit_p0_execution`, with the registered
carry-forwards: final-reserve cross-check vs `e13cf4d3…` +
duplicate rejection; per-slot seed realization binding) →
ckpt-0 eval → P0.
