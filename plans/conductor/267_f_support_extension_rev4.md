# 267_f — Unit A REV4 (response to 266_s) — prelaunch regenerated

The single narrow P1 repaired; prelaunch regenerated at the new
reviewed bytes (@3eb44c4). Full CPU suite: **995 passed under
`-W error`, TRUE exit 0**. Declaration and scientific design
UNCHANGED for the third consecutive repair (cohort identity
preserved); the manifest moved with the source digest.

## 1. P1 — the public numeric factors are disclosed, losslessly

The selection record now carries `public_factor_disclosure`: one
identity-bound row per observation (keyed by observation id, all
observations of the surface), each with the exact closed key set

- `cell_id`, `renderer_id`, `latent_index`, `latent_program_id` —
  the identity;
- `subtype` — the exact frozen `baselines.observable_subtype`
  label;
- `public_numeric_values` — the frozen public numeric factors
  (p/q/t/k/i as applicable), derived through the sanitized
  `baselines.public_feature_record` (which itself provenance-checks
  them against the generator), LOSSLESS — no bins invented;
- `direction` — from the authenticated surface geometry.

Collision and all other generator-derived fields remain ONLY in the
separately labelled `generator-side-collision|…` strata — they
never enter the disclosure. Later analysis can therefore
distinguish genuine instance-level routing from routing keyed to
public numeric features, exactly as the signed design requires.

The regression verifies, for every row: the exact closed key set;
`subtype` and `public_numeric_values` equal to a freshly derived
`baselines.public_feature_record` (and `observable_subtype`) for
that latent; the latent identity; and the absence of any
generator-derived field. The disclosure is part of the selection
record, so it is covered by the record's self-hash, the byte-exact
rederivation verifier, and the closeout's terminal inventory.

## 2. Frozen identities (FULL — the launch arguments)

- Config (unchanged):
  `22de3e4e72c41c250b0298867956336552e239f7c6aa8a8ce5d790346dacdeef`
- Freeze (unchanged):
  `03f740af3ced6dd7dfccef558b024de23f210e0717560a13b551cbeb435a993e`
- Extension-launch manifest (MOVED — regenerated at reviewed bytes):
  `bd8f90ca23383312f66951fc49639aa8573eb895d88ecee9dbad19d340a555f7`
- Declaration (unchanged):
  `dba1ccd511d53fb00391d13f459a9f5d03db5b1f91d9c5f4b0460d703627e260`
- Scientific design (unchanged):
  `951e16b9b04fe83ca9f52dba1d60543b99985a293f3c43746e1607897cdd9bdd`
- Environment manifest (moved with the commit):
  `57562b9e4bef65d25de0ebd4bcbaae1b2129bdc2123493e982a3ecdb1608fa0f`
- Original Step-4 surface lock (unchanged):
  `61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b`
- Ledger head (unchanged anchor):
  `88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb`

Launch: `execute_extension(run_dir="runs/routing-dev/support-ext-v1",
expected_manifest_sha256=…bd8f90ca, expected_head_sha256=…88c037a1)`
— or the hash-bound CLI. Budget 1.0 GPU-h (expected ≈0.51). This
rev4 prelaunch uses source bytes from `3eb44c4` and is prepared at
that commit's clean tree.

## 3. Next

Final narrow mechanical review (266_s closing) → GPU run with the
§2 hashes → closeout + selection/disposition review → Unit-B
mixture freeze (whose extraction now has the lossless public-factor
disclosure to bind against).
