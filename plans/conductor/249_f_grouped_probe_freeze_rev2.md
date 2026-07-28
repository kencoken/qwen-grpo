# 249_f — Step-6 grouped-probe freeze REV2 (response to 248_s)

All four P1 findings and all three smaller items repaired; the
contract is amended and re-frozen per 248_s F1 (the design is no
longer described as the "unchanged" 211_f wording). Full CPU suite:
**982 passed under `-W error`, TRUE exit 0** (66 in the routing
battery, 3 new). No Step-6 run root exists — these repairs remain
fully pre-outcome.

## 1. F1 — the zero-update contract, amended and re-frozen

`PROBE_CONFIG["zero_update_mechanism"]` now freezes the reviewer's
wording: **"432 real trainer optimizer-step calls at
learning_rate=0 and beta=0; zero effective parameter updates; exact
checkpoint-zero adapter equality."** The module docstring and this
freeze describe the design as *211_f §5 as amended by 248_s F1*:
optimizer/scheduler/RNG state evolve through the REAL trainer loop
(deliberately — the probe exercises P0's real between-generation
training path); what is proven is zero *effective* parameter
mutation, via exact adapter-map equality. The signed cohort and
sampling design are unchanged.

## 2. F2 — report reconstruction authenticates what the policy selected

`groups_from_trace()` now trusts NOTHING persisted: every completion
text is re-parsed with the frozen `parse_routing_action`, its
semantic assignment re-derived through the frozen positional mapping
(positions regenerated per observation via `program.generate_latent`
and cached), and its reward re-derived from the locked surface; the
stored action, assignment, and reward must MATCH the re-derivation
or the rebuild refuses (error text cites 248_s F2). Malformed
completions recorded as valid refuse; unequal parallel-array lengths
refuse instead of `zip()` truncation. The reviewer's reproduction —
a completion selecting worker 2 recorded as worker 3 with worker 3's
authenticated reward — is now a regression
(`test_probe_groups_rebuild_from_trace_rows`) and refuses.

## 3. F3 — the archive verifier is independent

`verify_probe_run()` now rehashes and cross-binds, from persisted
bytes alone: the archived environment (self-hash + attested
identity), the execution-identity manifest (rehash + record binding
+ frozen rule/cohort/surface/config fields), the preflight (exact
schema, frozen floor, acceptance semantics via
`_verify_probe_preflight`), the bound cohort (rehash to the frozen
binding) and the fully rederived 432-row schedule, the exact trace
cardinality / order / observation ids / global indices, the record
headers and frozen identities, the design-derived counters, the
execution-telemetry rederivable parts, and the exact rederivation of
the persisted report. The zero-mutation gate is proven over TWO
PERSISTED maps: `execute_probe` now writes
`checkpoint_final_hashes.json` beside `checkpoint_zero_hashes.json`,
and the verifier compares the maps themselves (and only then their
record digests) — not digest strings copied into
`probe_record.json`.

## 4. F4 — the signed execution-telemetry block

`probe_record.json` now carries `execution_telemetry`:
group-accounting counters, `surface_reward_lookups` (== the count of
valid completions, which the verifier rederives from the traces),
`live_worker_calls: 0` with the worker cache explicitly
not-applicable (rewards derive from the locked payoff surface; no
worker executes during the probe), wall/deadline seconds, peak
reserved VRAM, and the session preflight.

## 5. Smaller items

- **Support matrix**: `support_matrix()` emits the COMPLETE cell ×
  renderer × direction grid (6 × 3 × 4 = 72 strata) including
  zero-denominator combinations, appended to the probe report — so
  the later P0 transport gate can mechanically reject unmeasured
  strata.
- **Head binding**: `execute_probe` refuses unless
  `expected_head_sha256` equals the lineage parent frozen in
  `PROBE_CONFIG` — the reviewed head cannot be substituted at the
  command line (regression: refuses before any environment build).
- **Regressions added** (66 in the battery): semantic trace
  mismatch, malformed-recorded-as-valid, unequal parallel-array
  lengths, head-must-be-lineage-parent, preflight acceptance
  semantics, complete support matrix, and a full synthetic-archive
  verifier lifecycle (`test_probe_archive_verifier_lifecycle`):
  built from the committed evidence, `verify_probe_run` PASSES, then
  refuses schedule tampering, identity-manifest (provenance)
  tampering, and a persisted final-map mismatch, then PASSES again
  after restore.

## 6. Frozen identities (FULL — the launch arguments)

F1 moved the config, so config/freeze/identity all move; the
cohort/rule bindings, attested environment, and ledger head are
unchanged.

- Config:
  `4acf08f3f34acf7f46236b29259a5a0cabaa2b20e4a2169c3fcd68ca9ecc3b53`
- Freeze:
  `88fee9217e79ef261468387f1bcafc7b2a50f07eccbd04ebc4abf86f7e0fae6b`
- Static execution-identity manifest:
  `8ebd87062f11e11b3e146617411baf4c722e452e6fb2105c0ee4a62c905df1ab`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged):
  `1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a`
- Bound cohort (unchanged):
  `7f31bd091aaa97664e71ecb86b17078861b4e28af284162ee6ac50338d661e3b`
- Probe rule (unchanged):
  `0b616b8863bf73263c11c63cd8cc1572b880e6586f15059bde642c2a397c9f7b`

Launch: `execute_probe(expected_freeze_sha256,
expected_identity_sha256, expected_environment_sha256,
expected_head_sha256)` — where `expected_head_sha256` must now equal
the frozen lineage parent above.

## 7. Registered-measurement discipline (unchanged from 247_f §3)

Stage 5's six groups are NOT used to estimate routing exposure or
size P0. The 432-group probe is the registered exposure measurement;
its denominators for review remain 432 total / 216 Code-bearing / 24
on direction-bearing observations (16 w2-favoured, 8 w3-favoured) —
opportunities, not thresholds.

## 8. Next

Changed-lines review plus hash/test/ledger check (248_s closing
paragraph), then the GPU run with the §6 hashes, its close-out and
report review — and P0 designed from MEASURED exposure.
