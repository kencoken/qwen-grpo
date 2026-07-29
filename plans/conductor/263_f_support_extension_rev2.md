# 263_f — Unit A REV2 (response to 262_s) — prelaunch regenerated

All four P1s and all three smaller items repaired; the prelaunch is
regenerated at the new reviewed bytes (@0213b32). Full CPU suite:
**995 passed under `-W error`, TRUE exit 0** (13 in the extension
battery, 4 new). The declaration and scientific-design identities
are UNCHANGED (the cohort and execution identity did not move); the
manifest moved with the source digest and the new run-root binding.

## 1. P1-1 — candidate domain + the signed selection rule

- The selector's candidate domain is now **indices ≥
  `original_prefix_k`** (6–47). Legacy 0–5 latents never qualify
  for direction buckets; their direction yield appears in a
  dedicated `legacy_direction_disclosure` (Anchor material). The
  reviewer's probe is reproduced as a regression on the REAL Step-4
  surface: `code_atomic|w2 [5]`, `fork_join|w2 [1, 5]`,
  `math_code|w3 [2, 3]` all land in the legacy disclosure, every
  bucket is empty, and no legacy index can satisfy a quota.
- The signed canonical selector replaces the majority/all-members
  rule: **frozen bucket order** (Code cells ascending, w2 before
  w3); a latent qualifying for more than one bucket is consumed by
  the FIRST in that order (direction-disjoint by construction;
  renderer reversals remain diagnostics); within each bucket the
  **canonical quota-bounded subset** — ascending latent index,
  stopping once target latents, renderer strata, and
  non-`goal_first` coverage are all met; qualifying-but-unselected
  candidates are disclosed as `screened_surplus` (Unit B may place
  them only in Direction or Screened-but-unused, never Bridge).

## 2. P1-2 — Q3 eligibility from disposition states

`eligible_common_cells_q3` now derives from ACCEPTABLE disposition
states ({`full_quota`, `reduced_power_disclosed`}) — a direction
marked `quota_constraints_unmet` or `dropped_from_q3` can no longer
authorize a common cell. Dispositions enumerate **all three Code
cells × both directions**, with explicit dropped entries at zero
yield (regression-checked structurally in the end-to-end test).

## 3. P1-3 — subtype/public-factor disclosure

`observable_subtype` builds a label from the EXISTING safe public
projection only: `public_param_keys` (including the `code_atomic`
count/select shape) plus the public collision flags — nothing
private enters. The yield disclosure now carries `subtype|…` and
`cell+renderer+subtype|…` strata alongside cell/renderer/
cell×renderer, and tests require every observation of the surface
(864 in production; 126/108 in the fixtures) to enter each stratum
family — the analysis needed to detect public-subtype routing is
in the record by construction.

## 4. P1-4 — a working extension ScaleLift consumer

`telemetry.resolve_scale_lift_comparator` is now the ONE comparator
entry point for group scoring: original `c_fixed_dev-v1` records
verify and rederive exactly as before; extension consumer records
verify through `validate_extension_comparator_for` — exact closed
schema, rehash, binding to THIS extension surface's lock,
`reselected: false`, ScaleLift-only scope, development-only, worker
∈ {2, 3}. Full source reverification against the ORIGINAL lock
happens at construction (`immutable_comparator`) and post-hoc
(`verify_extension_outputs`); the consumer boundary cannot trigger
reselection. Integration-tested through the REAL `group_stats`: the
consumer record computes ScaleLift on the extension surface; the
original record refuses there (foreign lock); a re-hashed consumer
bound to a different extension lock refuses; flipped
`reselected`/scope flags refuse.

## 5. Smaller items

- **CLI**: `python -m tasks.routing.extension_run
  {prepare | execute --expected-manifest-sha256 …
  --expected-head-sha256 … | verify --closeout-entry-sha256 …}` —
  every launch argument is a reviewed hash; verify locates the
  closeout in the verified chain and runs
  `verify_extension_outputs`. Missing hashes exit nonzero.
- **Fully cache-served retry**: the surface-accounting invariant now
  admits zero singleton generations ONLY with zero uncached work
  (and refuses uncached work without generations, and zero executed
  records). A complete end-to-end regression runs a reviewed retry
  entirely from the warm slw cache to a successful lock and
  closeout.
- **Run-root identity binding**: the manifest carries the frozen
  `run_root`; `prepare_extension_launch` and `execute_extension`
  both refuse a `run_dir` that does not resolve to it — copied
  prelaunch artifacts cannot execute under a different lifecycle
  root.

## 6. Frozen identities (FULL — the launch arguments)

Config and freeze are UNCHANGED from 261_f; declaration and
scientific design are UNCHANGED (cohort identity preserved across
the repair); the manifest and environment moved with the reviewed
bytes.

- Config (unchanged):
  `22de3e4e72c41c250b0298867956336552e239f7c6aa8a8ce5d790346dacdeef`
- Freeze (unchanged):
  `03f740af3ced6dd7dfccef558b024de23f210e0717560a13b551cbeb435a993e`
- Extension-launch manifest (MOVED — regenerated at reviewed bytes):
  `c2e179837cda27e6c37381ca177d23b4fe89bfb331dd274e6586e4fbfb548d7a`
- Declaration (unchanged):
  `dba1ccd511d53fb00391d13f459a9f5d03db5b1f91d9c5f4b0460d703627e260`
- Scientific design (unchanged):
  `951e16b9b04fe83ca9f52dba1d60543b99985a293f3c43746e1607897cdd9bdd`
- Environment manifest (moved with the commit):
  `e73b2887b76e73da0823a6fe7b4e54cc5d387b2472f58e901dcf6e7300672195`
- Original Step-4 surface lock (unchanged):
  `61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b`
- Ledger head (unchanged anchor):
  `88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb`

Launch: `execute_extension(run_dir="runs/routing-dev/support-ext-v1",
expected_manifest_sha256=…c2e17983, expected_head_sha256=…88c037a1)`
— or equivalently the hash-bound CLI. Budget 1.0 GPU-h (expected
≈0.51); prelaunch records recommitted byte-for-byte.

## 7. Next

Narrow changed-lines review of this rev2 → GPU run with the §6
hashes → closeout + selection/disposition review → Unit-B mixture
freeze.
