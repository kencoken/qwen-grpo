# 335_f — Unit V REV3 (response to 334_s)

All four P1s and the deadline correction repaired. Full suite:
**1029 passed under `-W error`, TRUE exit 0**. New identities in
§6 (the config changed pre-signature: the framing amendment and
the disclosure entered the frozen record).

## 1. P1 — substantive alpha normalization; overlap DISCLOSED, not hidden

Opaque resource handles (`R-8V9` style) are identity-only aliases;
`alpha_normalize` canonicalizes them to R0, R1, … by first
appearance. The reviewer's numbers reproduce EXACTLY and are now
pinned regressions:

- val ↔ training: **21** unique template collisions affecting
  **39/90** val observations;
- val ↔ cycle: **15**, affecting **30/90**;
- cycle ↔ training: **30**;
- alpha-normalized LATENT/RESOURCE SEMANTICS: **0 throughout**.

Disposition per the review (no cohort re-selection — the natural
mixture stands): the HARD requirement is alpha-normalized
semantic disjointness (gated at zero; the smuggled-latent
regression bites); alpha-normalized prompt-template overlap is
DISCLOSED in the report, the lock, and the freeze record; the
frozen framing now reads "validation tests HELD-OUT
LATENT/RESOURCE INSTANCES, not template-disjoint prompts", with
repeated-vs-novel-template descriptive reporting registered as
optional. `normalized_latent_semantics` alpha-normalizes the
serialized semantic body, so the hard gate itself is
handle-insensitive.

## 2. P1 — the manifest rederives the frozen launch

`_require_frozen_cohort_declaration` — ONE shared validator
(builder AND revalidation boundary): namespace/cohort/renderers/
visibility equal the frozen config, the outcome-blind prefix, and
the declaration's observation rows equal the REGENERATED frozen
cohort. `validate_val_launch_manifest` now REDERIVES every
configuration-owned field (`budget_gpu_hours`, `search_cap`,
`support`, `driver` — now enforced against the constant —
and the newly bound `run_root`) from the frozen config.
Parameterized re-signing regressions: correctly re-signed
manifests changing each of those fields, a re-signed cohort
substitution, a truncated observation list, and a re-signed
foreign source digest all refuse.

## 3. P1 — frozen lineage and registered retry semantics

The `lineage_parent_sha256` bypass is REMOVED. `execute_val_run`
enforces, before any file access: the FIRST launch only from the
frozen C2 lineage parent; never after an OPEN or COMPLETED
attempt; aborted-retry design equality after the manifest loads.
**The ledger admission block enforces the same rules
authoritatively** (no entry path bypasses them) and additionally
requires the entry to persist the ACTUAL lineage parent — the
verified head it is admitted on (`"parent": None` is gone).
Cumulative envelope accounting holds by construction: aborted
closeouts record measured cost and the envelope sums closeouts.
The end-to-end fixture now exercises the REAL first-launch head
check (the config lineage is patched COHERENTLY with its pin to
the test ledger's head; the PRISTINE constant — captured at
import — is asserted equal to the C2 closeout pin). Regressions:
wrong-head first launch; open-attempt refusal at admission;
changed-design retry refusal at admission; post-completion launch
refusal.

## 4. P1 — the terminal verifier authenticates the archive

`verify_val_run(run_dir, expected_val_lock_sha256, closeout=None)`
now mirrors the established terminal-verifier pattern: EXACT
inventory (the complete 16-file expected set — a deleted
`execute_env_manifest.json` and an unbound extra file both
refuse); execution-environment self-hash validation + attestation
against the prelaunch environment; the launch manifest
revalidated and cross-bound to the surface's persisted manifest,
the run record (CLOSED schema), and — post-hoc — the closeout's
`closes_entry_sha256`/`val_lock_sha256` and its bound
`terminal_artifact_hashes` byte-for-byte; the surface
authenticated at the consuming boundary (`load_val_lock` now
REQUIRES `surface_dir` — an unauthenticated surface has no path
in); and the three-way overlap RECOMPUTED FRESH and compared to
the persisted report, the lock's bound result, and the run record
(a tampered report refuses). ABORTED runs verify explicitly:
partial hashes byte-for-byte and NO val lock present.

## 5. The deadline correction

A post-materialization deadline check aborts a run whose final
observation finishes past the ceiling. The regression drives a
fake clock past the deadline: the run aborts into an
aborted-closed ledger entry, and the aborted-run verifier passes
on the partial evidence.

## 6. New identities

- `VAL_CONFIG_SHA256 =
  73376e07cf83197bb210093bb31a38f5dbf4e17101eb6d61cc273b899a6deccf`
- `VAL_SEED_SCHEDULE_SHA256` UNCHANGED
  (`7f5f6518…` — the seed derivation did not change)
- freeze record =
  `8ba9677fe770ec96aa0ccdd4eac96238c76058eb84aaa9f7aaf38fb378c68666`
- Changed files: `p0_val.py`, `ledger.py` (the val retry block +
  parent binding), `test_routing_dev.py`. No frozen artifact
  touched; the spine gates pass unchanged.

## 7. Next

Narrow changed-lines review (per 334_s) → the real prelaunch
manifest preparation and its narrow launch sign-off → the V2 GPU
launch on the frozen C2 head → V3 lock → Unit Y.
