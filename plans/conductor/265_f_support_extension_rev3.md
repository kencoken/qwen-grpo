# 265_f — Unit A REV3 (response to 264_s) — prelaunch regenerated

Both P1s repaired; the prelaunch is regenerated at the new reviewed
bytes. Full CPU suite: **995 passed under `-W error`, TRUE exit 0**.
Declaration and scientific design UNCHANGED again (cohort identity
preserved); the manifest moved with the source digest.

## 1. P1-A — the subtype is the frozen public contract

`public_subtype_record` now derives the label through the EXISTING
frozen boundary: `baselines.public_feature_record` (the sanitized
projection, provenance-checked against the generator's own values)
and `baselines.observable_subtype` — so `math_atomic` T1/T2/T3,
`lookup_math` minus/plus, and `fork_join` lookup_first/code_first
are represented, not collapsed, and every label is validated
against `OBSERVABLE_SUBTYPES`. The generator-side collision flags
(`public_numeric_collision`, `sink_public_numeric_collision`) are
NOT observable from the public prompt and no longer touch the
public subtype: they appear only under an explicitly labelled
`generator-side-collision|…` stratum family. Tests now assert the
EXACT permitted subtype levels per cell (subset of the frozen
levels; math_atomic and fork_join must show multiple levels on the
Step-4 surface), and that no collision label appears inside
`cell+renderer+subtype|…`.

## 2. P1-B — the consuming boundary reverifies the original comparator

`validate_extension_comparator_for` no longer trusts the record's
markers: at CONSUMPTION it reverifies the ORIGINAL Step-4
`c_fixed_dev` record — bytes read from the frozen evidence path,
full 216_s F3 rederivation against the ORIGINAL locked surface
(cached once per identity, so group scoring pays it once) — and
requires all three fields to agree with the verified original:
`source_record_sha256`, `original_surface_lock_sha256`, and
`c_fixed_dev` == the derived worker. Selection on the extension is
still never invoked. The reviewer's forgery — a correctly rehashed
record with bogus source/original locks and `c_fixed_dev = 3` — is
now a regression through the REAL `group_stats` and refuses; each
of the three fields is independently load-bearing (three separate
single-field tamper refusals). The positive test asserts an EXACT
nonzero ScaleLift value (a worker-3 group on an observation where
the fixed-w2 collapse pays differently; expected lift computed from
the surface, required nonzero, matched exactly).

## 3. Documentation correction (264_s minor)

263_f's wording is corrected here: the rev2 prelaunch used SOURCE
BYTES from `0213b32` and was PREPARED at `35599ca` (the environment
manifest records the preparing commit). Likewise this rev3
prelaunch uses source bytes from `78a2c28` and is prepared at that
commit's clean tree.

## 4. Frozen identities (FULL — the launch arguments)

- Config (unchanged):
  `22de3e4e72c41c250b0298867956336552e239f7c6aa8a8ce5d790346dacdeef`
- Freeze (unchanged):
  `03f740af3ced6dd7dfccef558b024de23f210e0717560a13b551cbeb435a993e`
- Extension-launch manifest (MOVED — regenerated at reviewed bytes):
  `e4730a196bf6fb4ba7eda1cccb71c1bd52ea8762dc093ea37f435a281db8339b`
- Declaration (unchanged):
  `dba1ccd511d53fb00391d13f459a9f5d03db5b1f91d9c5f4b0460d703627e260`
- Scientific design (unchanged):
  `951e16b9b04fe83ca9f52dba1d60543b99985a293f3c43746e1607897cdd9bdd`
- Environment manifest (moved with the commit):
  `f0278d4dd3704db2378f433029052006b92887bf2e35e00e83ec4c19d6b65e75`
- Original Step-4 surface lock (unchanged):
  `61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b`
- Ledger head (unchanged anchor):
  `88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb`

Launch: `execute_extension(run_dir="runs/routing-dev/support-ext-v1",
expected_manifest_sha256=…e4730a19, expected_head_sha256=…88c037a1)`
— or the hash-bound CLI. Budget 1.0 GPU-h (expected ≈0.51).

## 5. Next

Narrow changed-lines review (264_s closing: the selector
architecture is NOT reopened) → GPU run with the §4 hashes →
closeout + selection/disposition review → Unit-B mixture freeze.
