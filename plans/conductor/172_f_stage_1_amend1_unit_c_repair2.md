# 172_f — Unit-C second repair (response to 171_s)

Both P1 blockers are implemented, the teardown segfault is root-caused
and RESOLVED (not carried), and 170_f §8 is corrected by erratum
below. 169_s trailing whitespace removed as requested
(`git diff --check` clean). Full CPU suite: **894 passed under
`-W error`, TRUE process exit 0** (unpiped; measured twice
consecutively; 893 prior tests + 1 bypass-refusal test added here).

## 1. B support is bound at consumption (finding 1)

`verify_replay_evidence` now takes the finalized `seed_registry` and
repeats the amended driver's generation-time check at the consuming
boundary: the registry's B keys must imply exactly the support ids
the evidence is scored over. Amended consumption (an
`execution_identity` passed) REQUIRES the registry — omitting it
refuses — so the chain bundle → registry (canonical) → support ids →
scored evidence is closed where persisted evidence is read, not only
where it is produced. `aggregate_amend1_verdict` passes its registry
through.

The review's demonstrated bypass is now a named refusal test: the
170_f fixtures (bundle/registry over `o00…o17`, B scored over
different render-instance ids) raise at the support check instead of
confirming. The aggregate fixtures were rebuilt over the matching
registry (`_REGISTRY_S` on the actual support ids), and two further
probes cover missing-registry and foreign-support-registry refusals
at `verify_replay_evidence` directly.

## 2. The persisted lifecycle is fail-closed end to end (finding 2)

**Runner**: `run_amend1_tranche` now RELOADS every artifact from its
persisted bytes through the same fail-closed loader the aggregate
uses, before the run may complete — A via `load_artifact` (amend1
tag, exact key set), C via `load_amended_c_artifact` (48/120), D via
`load_artifact` plus branch-row validation and the exact 8-key
telemetry set.

**Finalizer**: `finalize_amend1_run` is restructured so NOTHING is
written unless every gate passes:

1. **Preflight before mutation** — the replay root must hold its
   exact frozen file set; the validation root exactly the frozen set
   minus `aggregate.json`; a pre-existing `aggregate.json` refuses
   (a run finalizes once, never overwrites). The stray-file scenario
   the review described now refuses BEFORE any write, leaving no
   apparently-successful aggregate behind (asserted by test).
2. **Full environment validation** — both roots' env manifests go
   through `validate_env_manifest` (recomputed content hash, never a
   trusted field) and must be the one manifest the bundle binds; the
   registry is verified canonical here too.
3. **Partial-D reconciliation** — every `partial_D_*` record is
   validated (exact field set, scenario id, execution identity) and
   reconciled against `artifact_D`: error/trial counts equal, and
   persistence rows' branch counts equal the artifact's per-scenario
   subset. A tampered partial refuses pre-mutation (tested).
4. Aggregate computed (all loader/verifier gates re-run), then
   `aggregate.json` and the updated `run_record.json` written
   ATOMICALLY (temp file + `os.replace`), then the final exact-set
   check on both roots.

## 3. The teardown segfault: root cause, resolution, and erratum

**Erratum for 170_f §8 (record-only; 170_f stands at reviewed
bytes):** the claim that the segfault was macOS-specific and absent
on the execution box was WRONG, and the reviewer's exit-139
observation on `picome` is confirmed. The measurement error was mine:
`pytest … | tail -N; echo EXIT=$?` captures the exit status of
`tail`, not pytest. With the pipeline removed the pre-fix suite
reproduces exactly the reviewer's result: **893 passed, exit 139**,
crash after the summary with no Python frame.

**Root cause** (isolated this session):

- The only importer of sentencepiece in the entire suite is
  transformers' optional-dependency probe
  (`is_sentencepiece_available()` in the AutoTokenizer machinery),
  confirmed by an import-hook trace. No test, and no pinned
  tokenizer (Qwen2 = BPE via `tokenizers`), uses it.
- sentencepiece's SWIG-generated C extension emits cosmetic
  DeprecationWarnings ("builtin type SwigPyPacked/SwigPyObject/
  swigvarlink has no `__module__` attribute") during its own init
  and again at interpreter finalization. Under `-W error` — bisected
  to exactly `error::DeprecationWarning`; `error::UserWarning` and
  `error::FutureWarning` are clean — this poisons the extension's
  lifecycle and the process segfaults inside CPython finalization,
  after every test has passed and every byte is flushed. Minimal
  repro: `python -W error -c "import sentencepiece"` → exit 139.
- Intermediate findings recorded for completeness: pytest restores
  benign warning filters before exit (probed at atexit), the loaded
  module sets of crashing and clean runs are identical, and
  filter-level remedies (pytest ini `filterwarnings`, an
  atexit-installed ignore) do NOT prevent the crash — the
  interaction is inside the C extension's init/finalization, not in
  Python-visible filter state.

**Resolution**: a root `conftest.py` sets
`sys.modules["sentencepiece"] = None`, so the availability probe
takes transformers' designed sentencepiece-not-installed path and
the SWIG extension never loads in the test process. This is the
narrowest correct exclusion: the suite runs exactly as if the
optional package were absent, which for these models it functionally
is. Formal (non-pytest) runs load no conftest and run under no
`-W error`; the pinned tokenizers never touch sentencepiece either
way. With the fix, previously-crashing files and the full suite exit
0 under `-W error` with identical pass counts.

## 4. Boundary

Unchanged (168_f §6 / 170_f §9): Unit D remains the changed-lines
review, the final placeholder-free successor freezing the
implementation literals, the complete §5.4 probe suite pre-lock, and
the separate lock record. Nothing statistical runs before that lock.
