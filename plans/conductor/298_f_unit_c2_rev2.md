# 298_f — Unit C2 REV2 (response to 297_s)

The provenance fix applied and the audit wording corrected.
Config, freeze, mixture pin, thresholds, and schedule UNCHANGED;
the identity manifest moved with the source bytes. Full suite:
**1009 passed under `-W error`, TRUE exit 0**.

## 1. Blocking fix — mixture provenance is verified

`verify_unit_c2_run` now requires
`sample_record["mixture_record_sha256"]` to equal BOTH the frozen
`UNIT_C2_CONFIG["mixture_record_sha256"]` AND the identity
manifest's `mixture_record_sha256` — a closeout-bound artifact can
no longer carry false mixture provenance. The reviewer's exact
reproduction is a regression: a complete synthetic pass archive
verifies PASS, the single-field `deadbeef` tamper refuses
("mixture provenance"), and the restored record passes again. (The
new test also gives C2 the full anchored-verifier lifecycle
coverage over a complete archive, matching C1's.)

## 2. Audit wording correction (296_f §1 amended by this record)

296_f §1's "the ONLY change under `tasks/` since C1 is
`p0_mixture_v2.py`" was imprecise — `unit_c2_sample.py` is itself a
new executable GPU driver. The corrected, defensible evidence:

- **no inherited trainer-path file changed** (the 0-diff table
  stands);
- **C2's trainer constructor and preflight are MECHANICALLY
  EQUIVALENT to C1's** — verified by AST comparison after
  normalizing the config name and stripping docstrings:
  `_build_sample_trainer` and `_preflight` are node-for-node
  identical between `unit_c_sample` and `unit_c2_sample`; the
  admitted GPU execution block follows the same validated shape
  with only names/config source differing;
- therefore **no additional GPU smoke is required**.

## 3. Identities

- Config (unchanged):
  `5b47ada33a0223c1d8322846e536cc95285d950fb8076635008b803e49dcfb1c`
- Freeze (unchanged):
  `ae51bc57476ed1a9729bd949c1651d4c88a0cbb62e310179e30af415b0fa8420`
- Static execution-identity manifest (MOVED — binds source bytes):
  `7b19aeb9a642478785db1aa0d24e9126cf6d6ad3358c46b6c6a44b4dd82514af`
- Attested environment: `372f958f…`; head anchor: `9f4661a8…`;
  pinned mixture: `135a72bf…` — all unchanged.

Launch: `execute_unit_c2(expected_freeze_sha256=…ae51bc57,
expected_identity_sha256=…7b19aeb9,
expected_environment_sha256=…372f958f,
expected_head_sha256=…9f4661a8)`.

## 4. Next

Narrow mechanical review (297_s closing) → launch OK → GPU run with
the §3 hashes → closeout + exposure-report review → the frozen
decision → the 287_f spine branch.
