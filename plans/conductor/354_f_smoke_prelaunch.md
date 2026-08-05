# 354_f — Unit T beta-smoke PRELAUNCH (prepared manifest, for narrow sign-off)

Rev4 signed (352_s response closed by 353_f; no blocking
findings; "prepare the prelaunch manifest, and proceed without
another implementation-review cycle"). Per the frozen order,
`prepare_smoke_launch` has now RUN — exactly once, on the CLEAN
tree at `2f853a8` (the signed Rev4 commit; 1035 tests exit 0) —
and this document records the EXACT prepared identities for the
narrow prelaunch sign-off. **No GPU work has occurred and no
ledger entry has been written**; the launch executes only after
this sign-off, with exactly these hashes.

## 1. The prepared manifest

| field | value |
|---|---|
| **`manifest_sha256`** | `685200a5eb4b7cc2643a683330ecb00e7d4cbf5e2f1fc454539cded8318c5287` |
| kind | `routing-dev-beta-smoke-launch-v1` |
| `smoke_freeze_sha256` | `d2d87971765d40de…` = the signed freeze pin (351_f §6, unchanged by Rev4) |
| `smoke_config_sha256` | `6e775b9079658799…` (351_f §6, unchanged) |
| `science_contract_sha256` | `d47a63ff435e3b29…` (the signed contract pin) |
| `runtime_profile_sha256` | `202bc3773f9f4d4f…` (canonical P0 profile) |
| `budget_gpu_hours` | `0.75` (the reviewed ceiling) |
| driver | `tasks/routing/p0_smoke.py` |
| run_root | `runs/routing-dev/beta-smoke-v1` |
| execution_root | `/home/ken/qwen-grpo/runs/routing-dev/beta-smoke-v1` |
| **`lineage_parent_sha256`** | `6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51` |
| `routing_source_sha256` | `5137ea074b50514d353c594f4bd908ccf3b0765f0b57fbda26bbc90433f31004` (recomputed from the tree at `2f853a8`) |
| `environment_manifest_sha256` | `6ba01418aa181ec5c2e8aace463600103159f6b7224490c8fa0e2ff9c03bf802` |

Full hashes for the two abbreviated freeze fields:
`smoke_freeze_sha256 =
d2d87971765d40da9d2c8aebc29e014e2ca24e82f46a7afbf6c9b32231f75eb7`,
`smoke_config_sha256 =
6e775b9079658799e8759a4d8d4bea969dd8bdd8c100016915c8ef6771a9cf41`.
The manifest round-trips `validate_smoke_launch_manifest`
(every configuration-owned field REDERIVED from the frozen
config; the freeze loaded through its strict boundary; the
source digest recomputed from the tree).

## 2. Persisted prelaunch inputs (exactly once)

`runs/routing-dev/beta-smoke-v1/prelaunch/` holds exactly three
files (byte hashes):

| file | sha256 |
|---|---|
| `env_manifest.json` | `53e9165744a9a1613856f0bebb739fb3068852dfe05a96ab5fbc9a46a1e00ef7` |
| `smoke_freeze.json` | `24ed45bb6d2cc93560736f4d1b27dba47e43606fce924b62f789b1c5720dd633` |
| `smoke_launch.json` | `3cd13b2aa04078b330a73ff7653db9ac4244b74bd9e629d35770344a1216217d` |

A second `prepare_smoke_launch` refuses (`prelaunch exists; a
launch is prepared exactly once`). Committing THIS document does
not perturb the manifest: the source digest covers the routing
sources and driver, not plans documents, and execute-time
environment attestation exempts documentation-commit fields (the
V-established rule).

## 3. The ledger state the launch admits on

- Committed head (20 entries verify):
  `6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51`
  — the Unit Y final-reserve entry. The manifest's
  `lineage_parent_sha256` EQUALS this head, so the mandatory
  first-launch lineage check (352_s #1) binds.
- Envelope: 3.1942 consumed / 56.8058 remaining; reserve =
  FINAL 1.0 GPU-h. Admission requires envelope ≥ 0.75 + 1.0 —
  satisfied with wide margin.
- Admission is the manifest-MANDATORY `engineering_smoke`
  branch: kind, exact manifest hash, budget equality, signed
  freeze binding, actual parent == verified head, first-launch
  lineage, no prior open/completed smoke.

## 4. Preregistered predictions (unchanged from the signed design)

- **Prediction: 0.50–0.65 GPU-h total; hard ceiling 0.75**
  (deadline-enforced at every reward entry, eval observation,
  and phase boundary — breach aborts with sanitized closeout).
- Each eval pass ≈ 6–9 min (90 obs, 4^S materialization on the
  locked extension surface); whole epoch = 157 optimizer
  updates; warmup trajectory must equal the frozen
  constant_with_warmup shape to 1e-5 (rel-tol 1e-6); adapter
  state must change; ≥ 1 reference-KL logged event.
- Falsifiers: any validate_measurements refusal (wrong update
  count, wall < sum of group timings, flat trajectory), VRAM
  beyond the 4090, or deadline breach → the run aborts, the
  abort is sanitized (trained state discarded, raw traces
  sealed), and the aborted closeout + disclosure precede any
  retry decision.

## 5. Execution protocol (on sign-off, verbatim)

1. `execute_smoke_run(expected_manifest_sha256="685200a5…",
   expected_head_sha256="6fea9e3b…", …)` — admission appends the
   launch entry on that exact head.
2. Six disjoint phases P1–P6; timing-only measurement; sealed
   `.gz` evidence; production v1 checkpoint verified
   (validate_resume) then DISCARDED; console reporters stripped.
3. `verify_smoke_run` before the success closeout AND re-run
   against the completed head; then the timing-only projection
   disclosure (non-binding `worked_launch_projection`) comes
   back for review before Unit L consumes anything.
4. Development-only: nothing here retunes P0 mixture, prompts,
   or workers; the measurements feed ONLY the cap arithmetic
   through the frozen formula.

## 6. Requested sign-off

Approve launching with EXACTLY manifest
`685200a5eb4b7cc2643a683330ecb00e7d4cbf5e2f1fc454539cded8318c5287`
on EXACTLY head
`6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51`,
run root `runs/routing-dev/beta-smoke-v1`, budget 0.75 GPU-h.
Any other manifest hash, head, or root is out of scope and
requires re-preparation.
