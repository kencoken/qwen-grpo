# 333_f — Unit V REV2 (response to 332_s)

All seven blocking findings and the conformance gaps repaired,
with the recommended consolidated CPU-fake END-TO-END test now
covering the complete lifecycle (prepare → admit → materialize →
surface lock → overlap gate → val lock → terminal verification →
closeout). Full suite: **1028 passed under `-W error`, TRUE exit
0**. New identities (§8) — the config changed pre-signature.

## 1. P0 — the dedicated `val_materialization` admission path

The ledger gains the registered kind **`val_materialization`**
(entry + launch kind) with its own admission block: the entry
must bind the val-launch manifest kind and hash
(`val_launch_sha256`), the manifest budget, the manifest's
scientific-design identity, AND the SIGNED tranche-freeze hash
(`val_freeze_sha256`) — the probe-bearing support schema is never
borrowed. A val launch is an ordinary pre-closure launch against
the standing reserve. The end-to-end test admits and closes a
real entry through this path.

## 2. P0 — the surface locks under the val manifest

`_load_persisted_launch` gains the val dispatch branch (mirroring
the extension branch): a persisted `routing-dev-val-launch-v1`
manifest validates through `validate_val_launch_manifest` — so
`build_surface_lock` and every later `load_dev_surface` work. The
end-to-end test locks and reloads the materialized surface.

## 3. P1 — the V3 lock authenticates what it freezes

`build_val_lock(surface_dir, overlap_report=…)`: loads and FULLY
verifies the materialized surface under its own lock BEFORE any
claim is copied; refuses if the surface is not exactly the frozen
cohort; requires the PASSING three-way overlap report; binds it
into the record. The stub-lock test path is REMOVED.
`load_val_lock`: CLOSED schema; the cohort, evaluation identity,
canonical weights, and seed-schedule pin are REDERIVED from the
frozen config — the reviewer's rehashed `base_seed=999` record
now refuses at the rederivation (regression); with `surface_dir`
the surface BYTES authenticate under the bound lock.
`verify_val_run` (new): the val-specific terminal verifier — runs
BEFORE the success closeout and post-hoc.

## 4. P1 — the frozen CRN formula, exactly

`seed_for_completion` uses the COMPLETE SHA-256 digest as an
integer, mod 2³¹. The reviewer's vector is a pinned regression:
first observation, slot 0 → **1176822329**. Slots are bounded
0..7 (the frozen group size; 8, −1, and True refuse). The
complete 720-seed schedule is frozen:
**`VAL_SEED_SCHEDULE_SHA256 = 7f5f6518…`** — `seed_schedule()`
recomputes and enforces it (720 entries, all unique; a forged pin
refuses).

## 5. P1 — the canonical mixture weights, bound

The lock persists `natural_mixture_weights` — the frozen
`charter.natural_mixture_weights` applied to the exact ordered
cohort, as ordered [observation_id, weight] pairs (1/90 each,
asserted) — and the loader REDERIVES them.

## 6. P1 — the ceiling is enforced; provenance completed

- `execute_val_run` passes `deadline_monotonic = admission +
  budget × 3600` into `materialize_dev_support` (the existing
  per-observation deadline mechanism) — an overrun aborts into a
  closed-out aborted entry.
- `validate_val_launch_manifest` is CLOSED-schema (an extra field
  refuses) and RECOMPUTES the source digest from the tree (a
  re-signed manifest with a foreign digest refuses — regression).
- The frozen C2 lineage parent is ENFORCED: the production launch
  refuses any head other than `2bf50c1e…` (regression; the test
  also asserts the frozen default equals the C2 closeout pin);
  tests supply their own ledgers explicitly.
- The manifest binds the signed tranche-freeze hash; the
  admission entry carries it; prepare persists
  declaration/environment/manifest/freeze for the NARROW
  PRELAUNCH REVIEW, and execution requires the reviewed manifest
  hash.
- The terminal verifier (§3) runs before the success closeout.

## 7. Conformance gaps

- **Three-way overlap**: `three_way_overlap_reports` checks
  training↔validation↔cycle pairwise (the cycle cohort
  regenerated CPU-side for the gate only; its own freeze is Unit
  Y); measured now: all three intersections 0; the post-run gate
  and the lock bind all three.
- **All namespaces**: the disjointness test now regenerates
  latent identities in EVERY registered `NAMESPACE_CONFIG`
  namespace at the same coordinates — zero collisions.
- **Full sampling identity**: the evaluation record now binds
  do_sample/temperature/top_p/top_k/repetition_penalty/
  max_new_tokens/group_size — the eval runner must construct
  generation from this record.
- The never-trained-on statement carries the FULL pinned mixture
  identity (`135a72bf4deb…f53fa` in full).

## 8. New identities (config changed pre-signature)

- `VAL_CONFIG_SHA256 =
  cd555009667f1778a03dbb064132c5a05c1ac822daa1dd15f6b75a453fee9242`
- `VAL_SEED_SCHEDULE_SHA256 =
  7f5f65181e41b8011e2a5ccd735dc287ce6b1fd77e948d004ac4e9a1d6035215`
- freeze record (`val_tranche_freeze`) =
  `401835f0746aa6b21dfaf6d6e9645fca87e51f7999a57dce97873727274d2ab3`
- Changed files: `ledger.py` (the new kind + admission block),
  `dev_support.py` (the dispatch branch), `p0_val.py`,
  `test_routing_dev.py`. No frozen artifact touched; the spine
  gates pass unchanged.

## 9. Next

Sign-off on this rev2 → the NARROW PRELAUNCH REVIEW (the
prepared manifest/environment/declaration hashes) → the V2 GPU
launch on the frozen C2 head → V3 lock → Unit Y.
