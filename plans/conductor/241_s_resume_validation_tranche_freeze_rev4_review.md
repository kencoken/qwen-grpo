One narrow verifier repair remains before Step 5. The live execution path itself now looks ready.

### Blocking trust-boundary issue

[`verify_resume_validation()`](/private/tmp/review240/tasks/routing/resume_validation.py:1070) still accepts two self-consistent but scientifically invalid archives:

- It compares only `config_sha256` and `training_cohort_sha256` from the ten-field checkpoint identity contract. Prompt, source, environment, renderer, surface, worker-pool, cache and seed identities can still be relabelled while verification returns `PASS`.
- It verifies that the preflight file and record agree, but not that the preflight actually passed: the frozen floor and `free_mib >= floor_mib` are not rechecked.

The minimal repair is:

1. Compare the complete `ckpt.IDENTITY_KEYS` mapping against the archived identity/environment manifests.
2. Recheck the preflight schema, frozen floor, `free_mib >= floor_mib`, and `total_mib >= free_mib`.
3. Also cross-check the duplicated validation-record `tranche`, config and freeze fields.
4. Add regressions using self-consistently rehashed malformed artifacts.

Everything else is correctly closed:

- A/B/C checkpoint-zero equality is independently reproducible.
- Schedule, trace cardinality, counters and next cursor are rederived.
- HF adapter comparison is required, normalized per tensor name and fail-closed.
- Required RNG streams are enforced.
- All four documented hashes rederive.
- Ledger head matches and the run root is absent.
- `972` tests pass under warnings-as-errors; diff check is clean.

Writing the run root before admission could leave an orphan after a stale-head refusal, but current admission state is valid, so I consider that a nonblocking operational caveat.

After the small verifier patch and focused regressions, I recommend locking and launching without another broad review.

::code-comment{title="[P1] Validate the complete checkpoint identity" body="The verifier compares only config_sha256 and training_cohort_sha256. Construct the complete expected mapping for every ckpt.IDENTITY_KEYS field from identity_manifest plus the archived environment hash, and require exact key/value equality; otherwise prompt, source, renderer, surface, worker-pool, cache, seed, or environment provenance can be relabelled while the archive still verifies." file="/private/tmp/review240/tasks/routing/resume_validation.py" start=1091 end=1096 priority=1}

::code-comment{title="[P1] Recheck preflight semantics" body="File/record hash agreement proves only that the preflight was duplicated consistently. Also validate its exact schema and integer values, require floor_mib to equal the frozen min_free_vram_mib, free_mib >= floor_mib, and total_mib >= free_mib so an archived failed preflight cannot verify as PASS." file="/private/tmp/review240/tasks/routing/resume_validation.py" start=1070 end=1077 priority=1}