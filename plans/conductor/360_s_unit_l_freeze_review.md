Unit L is not ready for sign-off. The frozen science and 39-epoch derivation are sound, but two real launch-path blockers remain.

## Blocking findings

1. **P1 — An aborted P0 can receive a fresh ten-hour allocation**

`derive_real_launch_plan()` always uses zero cumulative P0 consumption (`p0_execution.py:146–172`), while the ledger rejects prior runs only when open or complete (`ledger.py:783–802`). An aborted same-freeze run falls through.

I reproduced:

- Valid first admission.
- Aborted closeout after 2.5 GPU-hours.
- Second admission under the same freeze.
- Second launch accepted with `cumulative_consumed_seconds = 0`.

This violates the registered retry/resume rules.

Simplest safe repair: make this Unit-L path first-launch-only. Any prior same-freeze P0 attempt—including aborted—must refuse. A resume stays under the original launch and cumulative ten-hour deadline; a relaunch requires a reviewed successor identity.

2. **P1 — The external execution manifest is not externally authenticated**

`admit_p0_execution()` receives no `expected_manifest_sha256`. Its validator checks the manifest’s self-hash, but does not authenticate:

- `execution_root`
- `environment_manifest_sha256`

I successfully re-signed a manifest with an arbitrary root and an all-zero environment hash; validation and full admission accepted it.

Required repair:

- Require `expected_manifest_sha256` and exact equality.
- Accept and authenticate the prepared environment artifact, then attest prepared against live.
- Compare the actual resolved run root against `execution_root`.
- Have the ledger’s P0 branch invoke the closed manifest validator, rather than accepting mutually consistent caller fields alone.

## Smaller issues

3. **P2 — Successful admission still returns `status="DEFERRED"`**

The returned trainer bundle retains `preparation.launch_admission.status == "DEFERRED"` and its four outstanding gates, even after admission completed. Return an explicit `ADMITTED` block containing the launch-entry and manifest hashes.

4. **P2 — Final-reserve equality check is incomplete**

`_cross_check_final_reserve()` claims exact equality with the pinned reserve record but compares only two numerical fields. It should load using `REAL_PRECURSORS["r_cycle_record_sha256"]` and compare the complete reserve projection plus ledger freeze/file bindings.

## What is already correct

- Launch plan independently rederives as `39 / 41 / 39`.
- Cadence ends exactly at update `6,123`.
- Freeze and execution-identity hashes rederive.
- The CRN evaluation schedule has 720 observation-slot entries with no checkpoint index.
- Dataset preparation yields 6,123 groups.
- Runtime, prompt, model, seed and precursor bindings otherwise look sound.
- Real ledger remains untouched at `df4bf7ad…`.
- `1038` tests pass under warnings-as-errors.

These repairs should not change the launch-freeze or execution-identity contents or pins, provided their rederivations remain byte-identical. They will change the future routing-source and execution-manifest hashes—which is appropriate because no P0 manifest has yet been frozen.