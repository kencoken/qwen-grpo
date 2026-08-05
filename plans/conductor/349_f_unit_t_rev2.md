# 349_f — Unit T REV2 (response to 348_s): the repaired design + the two-phase runner (for review)

All four blocking findings and the minor issue repaired, AND the
instrumented two-phase runner is implemented per the 348_s
closing note. Full suite: **1034 passed under `-W error`, TRUE
exit 0**. New identities in §6.

## 1. Finding 1 — the workload fits its budget

BOTH remedies adopted: the design measures **two** evaluation
passes (checkpoint-zero and post-epoch, once each) and prices
every scheduled evaluation — checkpoint zero, all nine
intermediates, AND the final — at their conservative MAXIMUM; and
the reviewed ceiling is raised to **0.75 GPU-h**. Predicted
workload: 2 evals ≈14 min + epoch 12–16 min + startup + bundle +
seal ≈ 31–36 min → prediction **0.50–0.65 GPU-h**, honest
headroom against the ceiling (envelope impact of the extra 0.15
ceiling: nil — remaining 56.8058).

## 2. Finding 2 — disjoint intervals, real P0 operations

The run is now SIX SEQUENTIAL PHASES with explicit boundaries
(P1 startup → P2 ckpt-0 eval → P3 epoch → P4 checkpoint bundle →
P5 post-epoch eval → P6 trace seal) — no interval overlaps:
startup ends at READY (before any rollout or evaluation); the
first rollout is counted once, inside P3; checkpoint-zero
evaluation is its own phase in production order. The per-group
rollout definition is frozen operationally: reward-entry time
minus the previous update-end boundary. P4 times a **complete
resumable bundle** (adapter + optimizer + scheduler + RNG states
— the resume-validation shape), not adapter-only. Both eval
phases time the **complete path**: generation + parse/score
against the locked surface + telemetry + sealed trace
persistence.

## 3. Finding 3 — the validator proves the frozen shape

`validate_measurements` now enforces, all as infrastructure
facts: the EXACT `constant_with_warmup` trajectory — lr sampled
at the end of each of updates 1–10 must equal `1e-5 × i/10`, the
plateau exactly `1e-5`, within rel tol 1e-6 (the reviewer's flat
trajectory and wrong-plateau reproductions refuse); the epoch
wall must CONTAIN the sum of its 157 sequential group timings
(the 10-second-epoch reproduction refuses); `optimizer_updates`
must equal exactly 157; `reference_kl_logged_events ≥ 1` proves
the beta/reference-logprob path engaged (a COUNT of trainer log
events — never a value); and `adapter_state_changed` must be True
(the before/after LoRA state hash comparison).

## 4. Finding 4 — an executable identity boundary

The freeze is now PERSISTED and committed
(`plans/conductor/p0/beta_smoke_freeze.json`) with FULL hashes
only: the science contract, the pinned mixture (record AND file),
the ACTUAL computed prompt hash, the extension surface lock, the
runtime profile, and the frozen 720-entry timing seed schedule
with the ordered cohort ids. `load_smoke_freeze` is the strict
admission boundary (external hash required; complete rederivation
from the frozen sources) — GPU execution starts there or not at
all. Operational disclosure enforcement is frozen in config and
implemented in the runner: `report_to="none"`, `disable_tqdm`,
no completion printing anywhere, trainer log history and both
evaluation traces SEALED (deterministic-gzip, hashed into the
closeout), only the closed timing record surfaced.

## 5. The two-phase runner (implemented)

`prepare_smoke_launch` (CPU): persists env/manifest/freeze once;
the manifest is closed-schema, rederives every
configuration-owned field, binds the freeze hash, the lineage
parent, and the resolved execution root; the prepared hash goes
to the narrow prelaunch review. `execute_smoke_run` (GPU): the
frozen-parent lineage rule with aborted-identical-design retry
semantics; admission (`engineering_smoke`, 0.75 budget) on the
verified head; the six instrumented phases; the closed
measurement record validated in-run; the worked NON-BINDING
projection; the timing-only `smoke_record.json`; abort path with
partial hashes; the closeout binding every terminal byte. The
trainer construction is the canonical-profile shape (the
C2-validated literals + the signed deltas), fp32 LoRA enforced,
seed 20260806.

## 6. Minor issue + identities

`derive_cap_inputs` preserves EXACT values (no `round(...,1)`;
the only rounding is the frozen ceil inside the trace-scaling
rule).

| identity | hash |
|---|---|
| `SMOKE_CONFIG_SHA256` | `70e4be03cc23b382404def3e3813c7696b4b5cfc34e9d6fa8f2b150470f3a110` |
| timing seed schedule (720, unique) | `cbfe528435882c0728eb79235e9303d85f403de2b7cf1a96cdae99328eb9992b` |
| **`SMOKE_FREEZE_SHA256`** (`beta_smoke_freeze.json`) | `bd499f0376924cc2278df6c11f5a715ee98a6859a1dee4663cbd428fb08fb164` |

## 7. Next

Reviewer pass (recording the §6 pins) → the narrow prelaunch
review of the prepared manifest → the smoke launch on head
`6fea9e3b…` → the timing-only projection → Unit L.
