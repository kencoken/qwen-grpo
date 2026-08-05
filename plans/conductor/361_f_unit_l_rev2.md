# 361_f — Unit L REV2 (response to 360_s): launch-path repairs

Both P1 blockers and both P2 issues repaired with the reviewer's
reproductions as regressions. Full suite: **1038 passed under
`-W error`, TRUE exit 0**. As 360_s anticipated: **the
launch-freeze and execution-identity contents and pins are
UNCHANGED** (`88c6635a…` / `4c763cc9…` — their rederiving
loaders pass in the suite); the routing-source and
execution-manifest hashes move with these code repairs, which is
appropriate since no P0 manifest has been frozen.

## 1. P1-1 — first-launch-only, no aborted fallthrough

The ledger's `training_run` branch now refuses on **ANY prior
same-freeze P0 attempt — open, ABORTED, or complete**: an
aborted run can never receive a fresh ten-hour allocation at
`cumulative_consumed = 0`. A resume stays under the ORIGINAL
launch and its cumulative deadline; a relaunch requires a
REVIEWED successor identity. `admit_p0_execution` enforces the
same rule itself at the chain-verification step (fail-closed
before the append). Regression = the reviewer's reproduction:
valid first admission → aborted closeout at 2.5 GPU-h → second
admission under the same freeze **refuses**
(`first-launch-only`), as does a second admission on the open
attempt.

## 2. P1-2 — the manifest is EXTERNALLY authenticated

- `admit_p0_execution` now REQUIRES `expected_manifest_sha256`
  and enforces exact equality — a re-signed manifest with an
  arbitrary root and a zeroed environment hash refuses at the
  external hash (the reviewer's reproduction, now a regression).
- The **prepared environment artifact** is a required argument:
  it is authenticated against the manifest's bound
  `environment_manifest_sha256`, and then ATTESTED against the
  live environment through the established `attest_environment`
  (prepared vs live), in addition to the live-vs-freeze
  commit-independent expectation.
- The **actual resolved run root** must equal the manifest's
  `execution_root` (a divergent `run_dir` refuses — regression).
- The ledger's P0 branch now invokes the CLOSED
  `validate_p0_execution_manifest` itself (schema +
  configuration-owned field rederivation; the source digest was
  already recomputed at the admission boundary) — mutually
  consistent caller fields alone never admit.

## 3. P2-3 — the completed admission returns ADMITTED

The returned bundle carries an explicit `admission` block —
`{status: "ADMITTED", launch_entry_sha256, manifest_sha256,
launch_freeze_sha256, execution_identity_sha256}` — and the
same block REPLACES the dataset-preparation `DEFERRED` marker
inside `preparation.launch_admission` (that marker described the
pre-admission state and no longer appears in a successful
bundle). Test-asserted both places.

## 4. P2-4 — the complete final-reserve equality

`_cross_check_final_reserve` now loads the reserve record under
`REAL_PRECURSORS["r_cycle_record_sha256"]` explicitly and
compares the **COMPLETE reserve projection** (all eight fields:
status, value, cohort size, multiplier, measured
seconds/observation, measured support hours, itemized ceiling,
rounding) AND the **ledger freeze bindings** (support closeout,
surface lock, cycle-record pin, reserve-record pin, reserve
FILE hash) against the persisted entry. Regressions: a mutated
`rounding` field refuses; a forged `cycle_record_sha256`
binding refuses — alongside the existing exactly-once and
divergent-value refusals.

## 5. Identities

| artifact | pin (UNCHANGED) |
|---|---|
| `P0_LAUNCH_FREEZE_SHA256` | `88c6635aadb2d0ca1c766efc937123b7ece427190cfe3ce3675ac8f269ebccfc` |
| `P0_EXECUTION_IDENTITY_SHA256` | `4c763cc9f21de2bfc05700b22b48529ed7f2e83ed68225a1ab115f4cdfa5a4ae` |

## 6. Next

Narrow review of these repairs (the §5 pins stand) → the P0
execution runner unit → the narrow prelaunch (the REAL execution
manifest prepared AFTER sign-off, since these repairs moved the
source identity) → P0 launch on head `df4bf7ad…`.
