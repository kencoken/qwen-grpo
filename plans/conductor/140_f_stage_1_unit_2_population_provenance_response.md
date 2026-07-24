# 140_f — Response to 139_s (unit-2 critique)

All four blocking findings are implemented; all three smaller corrections
are made. The unit-2 module was substantially rewritten rather than
patched: consumption-time validation is now the spine everything else
hangs from. Focused unit-2 tests: 26; full CPU suite: **661 passed**
under `-W error`; the worker-evaluation suite now also runs on this box
(**79 passed**) following the NVML fix.

## Blocking findings

**1. Authoritative validator at consumption — implemented.**
`validate_population_manifest(manifest, kind=...)` recomputes the
canonical-JSON hash, then re-derives everything the hash alone cannot
protect: exact manifest kind (a construction manifest presented as a
qualification manifest is the reviewer's reproduction, now a named
test), registered profile candidate, generator version, current source
identity (retirement fail-closed at load, 132_s §11.4), renderer list,
cell set, D4 cohort/maximum-population completeness, look schedules,
**first-principles regeneration of every latent/render id** (a mutated
id fails even after re-hashing — tested both ways), visible-slice
placement and regeneration, and recomputation of every expected-count
block from the denominator contract. Every public consumer
(`qualification_prefix`, `expected_row_keys`, `verify_gate_rows`,
`register_qualification_population`) invokes it; truncated support,
tampered counts, and misplaced visible slices are each rejected by
test.

**2. Frozen profile and phase order enforced — implemented.**
`REGISTERED_PROFILE_VERSIONS` is derived from the unit-1
`PROFILE_CANDIDATES` freeze (currently exactly
`{dp-2bcb6373340a8a79}`); `register_construction_population` rejects
any other profile, schema-valid or not (the reviewer's modified-profile
reproduction is a named test). `register_qualification_population` no
longer takes a profile at all: it consumes the **validated construction
manifest**, inherits its profile identity, and embeds
`construction_manifest_sha256` — matching the §3.3 phase order in which
qualification registration follows the construction reveal. Binding the
construction-frozen deployable/control artifact is added when unit 4
defines that artifact; the manifest field it will anchor to (the
construction hash) exists now.

**3. Derived denominators + content-addressed execution identity —
implemented.** The caller-attested `verify_rows` is deleted. Its
replacement, `verify_gate_rows`, derives expected row identities
internally via `expected_row_keys(manifest, kind, cell, gate, ...)` —
structured keys (`{render_instance_id}|{node}|w{worker}|{gate}` /
`{rid}|{src}->{dst}|intervention`) computed from the validated manifest
plus the frozen `stage1` denominator functions for the four gate
families now derivable (truncation per worker; the full independent
node-execution grid; selected-route given the frozen `d`; intervention
edges), with optional immutable look-prefix restriction. Duplicate
expected keys cannot exist by construction (set-of-derived), and an
empty denominator is itself an error. Every row must now bind **both**
identities: the population hash and a 64-hex
`execution_manifest_sha256`; `build_stage1_env_manifest` (now
`stage1-environment-v2`) content-addresses itself so that identity
exists. The remaining join — per-row request/worker/pool fingerprints
and the exception-to-code mapping — is the unit-4 execution layer; the
docstring states that boundary explicitly rather than claiming
coverage, per the review's alternative.

**4. Support/count contract completed where deterministic —
implemented.** Expected counts now additionally register:

- `independent_node_execution_rows` = observations × S × 4 (the full
  `(observation, node, logical worker)` grid);
- `intervention_rows_by_edge` (one corrupted execution per private
  observation per directed edge, from the authoritative
  `CELL_INTERVENTION_EDGES`);
- `per_look` denominator blocks for every registered qualification
  look (with visible-slice counts clipped to the prefix);
- `b1_fitting_rows` (one canonical `resource_first` row per
  construction cluster, §5.3).

What is *not* deterministic at registration is now recorded in the
manifest itself (`support_deferred`): per-selected-worker route counts
(deterministic only once `d` is frozen — computed then via the
already-tested `stage1.selected_route_rows_per_worker` and bound in the
unit-4 selection artifact), outcome-dependent cache/physical-generation
counts (materialization manifest), and the B2/B3/B4/B6/echo/no-op
execution support (unit-4 harness registration; B3 consumes the visible
slice named here). Absence is an explicit decision, not an omission.

## Smaller corrections

1. `validate_qualification_looks` now requires a non-empty mapping and
   plain positive ints — `100.0` and `True` are rejected by test.
2. Dirty trees: `build_stage1_env_manifest` **refuses** a dirty tree by
   default; the development-only `allow_dirty=True` escape
   content-addresses the complete uncommitted diff
   (`git_diff_sha256`) and marks `git_dirty: 1` in the hashed record.
3. The infrastructure exception-to-code mapping deferral is corrected:
   the `stage1.py` comment now names the **unit-4** execution layer and
   records (per this review) that the mapping must exist before the
   first construction call. 133_f §4 item 7's "unit 2" reference is
   superseded by this note; 133_f itself is closed history and is not
   re-edited.

## Test evidence

26 unit-2 tests, including one named test per reviewer reproduction:
wrong-kind acceptance, post-hash id mutation (caught by re-hash AND by
first-principles regeneration after re-hashing), truncated support,
modified-but-valid profile, caller-attestation removal (keys derived,
counts cross-checked against the registered expectation), stale/foreign
/partial/duplicated/unregistered/short-hash row handling, and
empty-denominator refusal. Full CPU suite 661; worker-evaluation suite
79 (NVML mismatch resolved — ollama had pinned `nvidia_uvm`; driver
595.84 now live; the exit-139 teardown remains the recorded
pre-existing sentencepiece issue). Unit 3's §8.4B GPU replay is
unblocked.
