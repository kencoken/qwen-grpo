# 170_f — Unit-C repair (response to 169_s)

All six P1 findings and the trust-boundary strengthening are
implemented. Focused files: 54 tests; full CPU suite status is in §8
(including the sentencepiece teardown investigation the review asked
for). No frozen scenario ran.

## 1. The amended B replay path exists (finding 1)

`run_amend1_replay(bundle, seed_registry)` is the amended GPU entry
point: it validates the COMMON execution bundle against the finalized
registry (the bundle self-hash is the identity every manifest and
artifact binds), verifies the registry canonical, requires the
registry's B keys to imply exactly the authoritative support ids,
claims `runs/stage1-replay-amend1` atomically, writes the full frozen
§9.4 file set (execution-bundle manifest included), and finalizes the
B artifact under `stage1-replay-amend1-v1`. The generation loop and
frozen replay contract are byte-identical to `run_replay` — only the
identity layer differs. Legacy/amended refusal is bidirectional:
`load_b_artifact` takes a tag, and `verify_replay_evidence` requires
the amend1 replay tag exactly when an `execution_identity` is passed
(the aggregate's path), so the legacy-tagged fixture the review
flagged now refuses — tested both directions.

## 2. Registered seeds are actually consumed (finding 2)

Two complementary mechanisms, both tested:

- **Rederive-and-compare**: `verify_registry_canonical(registry)`
  rebuilds the COMPLETE registry from the frozen derivation over the
  support ids implied by the registry's own B keys and requires exact
  equality. Both formal runners call it after bundle validation — a
  bundle built at lock from a non-canonical registry now refuses even
  though its digest matches (tested).
- **Direct consumption**: `run_d_battery_scenario` and the
  deterministic set take the registry and consume registered values
  via a fail-closed lookup (`no registered seed for …` refuses —
  never a fallback derivation); the amended B loop consumes
  `seed_registry["B|obs|prompt|i"]` through `_generate`'s new
  `seed_of` parameter. A probe scenario records every seed it
  receives and matches the registry exactly.

Because the D/B domain reproduces the v1 `scenario_seed` values by
the §9.3 construction (asserted by test), direct consumption changes
no frozen seed.

## 3. Branch telemetry is exact-set validated (finding 3)

`expected_branch_keys()` derives the exact eight keys from the
scenario registry (D6/D7 at the ordinary looks 100/300/500, D8 at the
amended fork looks 100/500 — the persistence scenarios now carry an
explicit `schedule` field). The aggregate refuses missing rows AND
arbitrary extra schema-valid rows (both tested). The `partial_D_*`
records now carry their scenario id, the execution-bundle identity,
and (D6–D8) their branch counts.

## 4. The successful lifecycle satisfies the frozen contract (finding 4)

`run_record_final.json` is gone — the runner updates
`run_record.json` in place on completion. The new post-B finalizer
`finalize_amend1_run(bundle, seed_registry)`:

1. validates the bundle, then requires BOTH roots' persisted bundle
   manifests to equal it and both env manifests to be the one it
   binds;
2. refuses unless both run records are `complete`;
3. reloads A/C/D and the B evidence from disk and routes them through
   `aggregate_amend1_verdict` (all loader/verifier gates re-run);
4. persists `aggregate.json`, appends the `aggregate` stage and the
   decision to the existing `run_record.json`;
5. checks BOTH roots against `EXPECTED_RUN_FILES` exactly
   (`verify_run_file_set`: missing, extra, and non-file entries all
   refuse).

End-to-end test plus fail-closed probes (aborted record, foreign
bundle on disk, stray file, missing artifact).

## 5. Combined/total deadlines reach the in-loop check (finding 5)

`_d_scenario_deadline` hands each D scenario the MINIMUM remaining
budget — per-scenario 4×-measured, D6–D8 combined 30 min, 12 h total
— which the existing every-50-trial check enforces; a non-positive
remainder refuses before the scenario starts. The runner and the
scenario loop now use the monotonic clock throughout (wall-clock
`started_unix` remains in the record for humans). The lagging
post-scenario checks are deleted.

## 6. `C2_preCE1_available` requires scientific passage (finding 6)

The claim flag is now `scientific_pass AND b_supports_c2`; the B-only
diagnostic survives as `B_supports_C2`. The scientific-stop test
asserts the separation (B support true, availability false); the
decision table itself is unchanged.

## 7. `C_marginal` identity strengthened

Added `denominator_unresolved <= unresolved_count` and
`fail_count + denominator_unresolved <= positive_branch` (both hold
for every row `run_c_path` can produce: a denominator-unresolved look
is always an unresolved decision, and fails arise only in the
positive branch with a resolved denominator). Identities are code,
not schema-digest inputs, so no bundle field changes. Violation
probes added.

## 8. Full-suite status and the sentencepiece teardown

**893 passed under `-W error`, exit 0 — twice consecutively — on the
execution box** (Linux, the environment the manifests pin:
sentencepiece 0.2.1, protobuf 7.35.1, transformers 5.13.0,
tokenizers 0.22.2). The teardown segfault is NOT reproducible here.

Isolation: the reviewer's trace (all tests pass, then exit 139 during
interpreter teardown inside sentencepiece, on their macOS review
checkout) matches the known sentencepiece/protobuf static-destructor-
ordering crash at shutdown — it occurs after the last test completes
and after all artifacts persist, so it cannot alter a test outcome or
a persisted result; and it is specific to the review environment, not
the pinned execution environment. Count reconciliation: 883 (their
run, pre-repair) + 10 tests added by this repair = 893. If the crash
ever appears on the execution box it becomes an environment defect to
resolve before any run; as of this record it does not.

## 9. Boundary

Unchanged from 168_f §6: Unit D remains the changed-lines review, the
final placeholder-free successor (implementation literals: the
augmented-grid inversion rule, the scan-variant tolerance magnitude
set, SciPy/NumPy versions, the measured per-outer deadline literal),
the complete §5.4 probe suite pre-lock, and the separate lock record.
Nothing statistical runs before that lock.
