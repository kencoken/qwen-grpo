# 138_f — Stage-1 unit 2: population and provenance layer

Unit 2 per 132_s §16, including every item queued to it by 129_f, 134_s,
and 136_s. CPU-only; no worker or policy execution; no payoff surface
touched. Full CPU suite: **649 passed** under `-W error`.

## 1. The queued workerpool citation fix (129_f → here)

The three stale `108_f` comment citations in the freeze-digested
`workerpool.py` are corrected to `108_s` (`sed`-exact, comments only,
three occurrences, no executable change). Disclosure:

- Stage-0 `executable_source_digest()` before:
  `688f7e06da6e9ca04b1714663b032efc178d2790ef8859c3275ddd52e276cee8`
- after:
  `9f9fe6f645439554604b34ef26dba512f4cecbbb2b148da322342e1fdaea7f89`

The committed Stage-0 freeze fixture is **not** edited — it remains the
historical record. `verify_freeze()` now correctly **refuses** on
`executable_source_sha256`, which is the designed guard responding to a
disclosed citation-only edit at exactly the queued moment ("when the
successor source digest is issued anyway", 129_f). The freeze-guard test
is rewritten to assert this precise state: refusal on that one field, all
six other frozen fields still byte-matching, and both digests pinned.
Stage-0 recorded runs remain content-addressed and unaffected.

## 2. Successor source/environment identity (`stage1_manifest.py`)

- `stage1_source_files()`: every **tracked** `tasks/conductor/*.py`,
  sorted — the complete source identity closing the 125_s gap
  (`pool_runtime.py`, `executor.py`, etc. were never digest-bound).
  Fails closed unless the list is a strict superset of the historical
  eight plus the 134_s floor (`contract.py`,
  `SUCCESSOR_DIGEST_REQUIRED_ADDITIONS`).
- `stage1_source_digest()`: same `name\0bytes\0` chaining as Stage 0,
  over the complete list. At this commit:
  `f01210980c0f623938c7c4e181f8db39eb6160838607a948b4fc536212a58e48`
  (informational — the CE1 Freeze Record pins the value at the freeze
  commit; the digest legitimately moves with any conductor source
  change).
- `build_stage1_env_manifest()`: `stage1-environment-v1`, the ce0
  environment machinery (127_f prerequisite 1) extended with the
  successor source identity and the historical Stage-0 digest for
  cross-reference. Fails closed if the GPU cannot be queried — on this
  box it currently would, by design, until the recorded NVML mismatch is
  fixed. Not invoked by tests.

## 3. Population registrars

`register_construction_population(profile)` and
`register_qualification_population(profile)` produce canonical-JSON,
SHA-256-identified manifests that bind, per 132_s §4:

- exact latent and render-instance ids, computed **generation-free**
  (the id is a pure function of generator version, profile version,
  namespace, cell, index — registration reveals nothing about instance
  content; equality with full generation is acceptance-tested);
- the D4 cohort (indices 30–129, `validate_construction_cohort`) for
  construction; the **maximum** population (500 ordinary / 200 fork,
  cross-checked against `NAMESPACE_CONFIG` caps = terminal looks) for
  qualification, of which looks reveal immutable prefixes
  (`qualification_prefix`, prefix property acceptance-tested);
- the §4.1 visible slice: exactly the first 18 qualification clusters
  per cell carry paired visible render-instance ids;
- expected counts derived from the frozen `stage1` denominator contract
  — never re-derived: assignment rows (`4^S` per observation), one-call
  rows, the fork 32-workflow shortcut rows, selected-route rows
  (3 × S × clusters), and per-worker truncation strata
  (3 × on-contract nodes × clusters);
- the profile version (`dp-2bcb6373340a8a79` for the registered
  primary) and the successor source digest.

Registration is deterministic: re-running reproduces the identical
manifest hash. Phase-specific look validation
(`validate_qualification_looks`) lives here, completing the 136_s
finding-2 split: the seed serializer stays population-independent, the
manifest layer enforces schedules.

## 4. Fail-closed row verification

`verify_rows(manifest, expected_keys, rows)`: a missing, duplicated,
stale (row bound to a different manifest hash), partial (missing
required fields), or unregistered row raises `ManifestError`; an empty
expected-key set is itself an error (a gate with no registered
denominator is not evaluable). No verification failure can be scored as
reward 0 or 0.5. Each failure mode is exercised by test.

## 5. 136_s follow-through

- `stage1.WORKER_FAMILIES` is now bound by test to the authoritative
  frozen pool map `workerpool.WORKER_TO_ENDPOINT` — the registry is the
  source of truth, the constant is the convenience view.
- `RENDERERS_PER_LATENT` was already derived from `types.RENDERER_IDS`
  (137_f); the binding is asserted here as well.

## 6. Test evidence

- `test_conductor_stage1_manifest.py`: 14 tests — superset/completeness
  of the source list, digest distinctness from both Stage-0 identities,
  registrar determinism, id-equality with generation, exact expected
  counts (fork: 19,200 assignment rows, 9,600 shortcut rows, 900
  selected-route rows, 300 truncation rows per worker; math_code worker
  strata `{0:0, 1:300, 2:300, 3:300}`), visible-slice placement,
  immutable-prefix property, look validation, manifest-hash recompute
  and JSON round-trip, all five row-verification failure modes, and the
  registry cross-check.
- Updated freeze-guard test in `test_conductor_grpo.py` (see §1).
- Full CPU suite: **649 passed**, `-W error`
  (`test_conductor_worker_eval.py` still excluded on this box by the
  recorded NVML driver/library mismatch, to be fixed before unit 3).

## 7. Boundary

This unit registers and verifies identities only. It does not execute a
construction command (the first authorized construction command is a CE1
Freeze Record item), does not build payoff surfaces, and does not
implement estimators — unit 3 is the §8.4 pre-CE1 design-validation
tranche (look-cap power, direct-gradient feasibility replay,
persistence-envelope feasibility — whose preliminary calculation already
predicts the amend-once branch — and the focused coverage battery),
after the NVML reboot.
