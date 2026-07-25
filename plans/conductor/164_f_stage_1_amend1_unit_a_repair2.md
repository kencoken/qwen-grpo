# 164_f — Second Unit-A repair (response to 163_s)

The final narrow repair 163_s requested. Full CPU suite: **754 passed**
under `-W error`. Nothing statistical ran.

**The blocker — bundle provenance is now derived or pinned, never
caller-asserted.**

- Three new required bundle fields per the review:
  `request_contract_sha256`, `artifact_schema_sha256`, and
  `expected_file_set_sha256` — each compared inside
  `_check_bundle_semantics` (build AND load) against values DERIVED
  from the authoritative sources: the frozen `REPLAY_CONTRACT`
  literal, a canonical description of the frozen amended schemas
  (row field sets + trial counts, the persistence branch field tuples,
  the version tags), and the newly frozen `EXPECTED_RUN_FILES` sets
  for both run roots (158_s §11's archive list, including the eight
  `partial_D_*.json` records).
- `scenario_grid_sha256` and `v1_evidence_manifest_sha256` are
  likewise now compared against the derived grid digest and the PINNED
  archive-manifest hash — the reviewer's fabricated-evidence-hash
  reproduction refuses at build and (self-rehashed) at load.
- The registry trio (`seed_registry_sha256`, `seed_registry_entries`,
  `b_support_sha256`) is COMPUTED by `build_execution_bundle` from a
  mandatory `seed_registry` argument that must be the finalized
  49,342-entry registry; a caller-supplied disagreeing value refuses.
  `validate_execution_bundle` likewise takes the finalized registry
  (deterministically regenerable by every consumer), recomputes its
  digest, and re-derives `b_support_sha256` from the observation ids
  IMPLIED by the registry's own B keys — so the reviewer's second
  reproduction (partial 40,126-entry digest paired with a claimed
  count of 49,342) is structurally impossible: the count, digest and
  support binding all come from the same supplied-and-verified object.
  Validating against a different registry than the bundle bound also
  refuses (tested).

**Small fixes:**

- `validate_env_manifest` now requires the `numpy` and `scipy` fields;
  the remove-and-rehash reproduction refuses (and the tranche test
  helper carries the fields).
- The archived diagnostic's command now includes
  `PYTHONPATH=/tmp/v1-checkout` with a comment explaining why (python
  puts the script's directory on `sys.path`, not the cwd). The script
  and manifest hashes were re-pinned for the corrected bytes
  (script `85f7f26b…`, manifest `b01b7060…`); the seven frozen v1
  payload files remain byte-identical.

Noted for Unit B, per the review's closing line: the amended C loaders
will enforce the exact 48-path/120-marginal key sets when they land.

Proceeding to Unit B.
