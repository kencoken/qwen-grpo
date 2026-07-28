# 215_f — Infrastructure repair (response to 214_s)

All five P1 findings and the reporting repairs are implemented at
their consuming boundaries, each with the reviewer's reproduction as
a regression test. Full CPU suite: **960 passed under `-W error`,
TRUE process exit 0** (44 in the routing battery). No GPU work has
run; nothing is frozen or launched.

## 1. The surface lock (P1: surface not bound to a pre-execution lock)

`build_surface_lock(out_dir, routing_source_sha256, driver,
environment_manifest_sha256)` derives ONE closed artifact
(`surface_lock.json`, exact key schema, self-hashed) from the
persisted files plus the launch identity: declaration / manifest /
payoffs / both trace hashes, worker-visible + runtime-profile + pool
fingerprints, request contract, cache identity
(`worker_completions/slw/<request_contract>`), the routing source
digest with its driver, and the environment manifest hash. Built
exactly once per surface.

Everything downstream REQUIRES it:

- `load_dev_surface(out_dir, expected_lock_sha256=…)` — the
  externally frozen hash is a required argument; the lock must
  rehash to it, use the exact schema, and every file binding must
  recompute from the bytes on disk (a truncated `payoffs.jsonl` is a
  regression test).
- `select_c_fixed_dev(loaded)` now takes the lock-validated loader
  RESULT — arbitrary hashes cannot reach it; the record binds
  `surface_lock_sha256`, and `validate_c_fixed_record` (rehash +
  `{2,3}` + development_only) is the consumer-side gate.
- `bind_probe_cohort(frozen_rule, surface_dir, expected_lock_sha256)`
  consumes the DIRECTORY under its lock — the caller-supplied-hash
  parameter is gone.

The reviewer's reproduction is closed at the front too:
`build_dev_declaration` now takes the RUNTIME and records
`runtime_profile_fingerprint` + `request_contract` +
`cache_identity`, and `materialize_dev_support` verifies all of them
against the executing runtime — the tampered-request-contract
declaration now refuses (regression test).

## 2. Ledger lifecycle (P1)

- **Launch/closeout linkage**: new `closeout` entry kind naming
  `closes_entry_sha256`; `envelope_state` charges every launch its
  allocation UNTIL a linked closeout replaces it with the measured
  cost — never both (regression: 3.0 h allocation → closeout 1.25 h
  → consumed exactly 1.25). A closeout must name a recorded,
  not-yet-closed launch; measured consumption on a non-closeout
  entry refuses.
- **Initial-support admission**: `check_launch_admissible(...,
  initial_support=True)` admits the ONE launch that creates the
  provisional reserve against the bare envelope; it refuses once any
  reserve exists, and the ordinary rule still refuses reserve-less
  launches.
- **Suffix deletion**: `ledger_head()` / `verify_ledger_head()` bind
  the chain to an EXTERNALLY committed head (each tranche's lineage
  document records it); the regression test shows a deleted suffix
  passing the chain check and being caught only by the head.
  `append_ledger_entry` optionally takes the expected head.

## 3. Checkpoint state binding (P1)

- `build_checkpoint_record` requires `state_artifact_hashes` over
  exactly {adapter, optimizer, scheduler, rng, scaler-or-None};
  `hash_state_artifacts` hashes the bundle files (missing required
  file refuses); `validate_resume` re-verifies recomputed disk
  hashes against the bound ones (altered-bundle regression).
- `capture_rng_state` is COMPLETE and restorable: python's
  (version, internal state, gauss_next), numpy's full 5-tuple
  (name, keys, pos, has_gauss, cached_gaussian), torch CPU/CUDA.
  The reviewer's reproduction — numpy states at positions 2 vs 4 —
  now captures differently (regression), and
  `restore_rng_state(capture())` replays identical draws on every
  stream. `GroupAccountant.restore(validated_counters)` is the only
  restoration path and re-checks the boundary + impossibility.
- `merge_segments` is identity/parent/cutoff-aware: one run_id and
  one config (a config change refuses as a FORK), parent-checkpoint
  linkage in order with resume counters equal to the parent
  checkpoint's consumed counter, per-segment contiguity from the
  resume point, COMPLETE segments refusing rows beyond their own
  cutoff (the impossible-history reproduction), aborted tails
  excluded-but-preserved, and the zero-based global contiguity
  checks retained.

## 4. Telemetry authenticates (P1)

`group_stats(group, surface=…, c_fixed_record=…)`:

- observation identity (cell, renderer, latent) is PARSED from the
  observation id — caller metadata is gone;
- a valid completion's reward must equal the authenticated surface
  payoff (the reviewer's 1.0-reported-as-0.5 reproduction refuses);
  an invalid completion's reward must be 0; valid⇒parseable;
- assignments are schema-checked (exact arity, workers 0–3);
- the w2/w3 pair, payoffs and direction are DERIVED from the surface
  via the frozen `family_correct_variants` (flipped-winner and
  cross-observation-metadata attacks are structurally gone);
- the comparator arrives only as a rehashing `c_fixed_dev-v1`
  record.

**ModelAcc added** per the exact 130_s §6.5 slot rule: mean over
eligible Code slots of 1[choice == surface-derived target];
malformed scores 0 and stays in the denominator; wrong-family and
wrong-specialist Code choices score 0; tied observations have no
eligible unit and are absent from the denominator. Reported with
raw numerator/denominator alongside conditional C2 (which is
unchanged: non-Code family-correct AND Code ∈ {2,3}, tied never
scored).

## 5. First-probe enforcement (P1)

`freeze_first_probe_rule` (kind `routing-dev-first-probe-v1`)
enforces the signed shape: `routing_dev`, group size 8, ALL
renderers in canonical order, prefix divisible by 6 (the generator's
factor blocks are 1/2/3/6). A hand-built first-probe rule with the
wrong shape refuses even correctly hashed. The generic builder is
now explicitly `freeze_reprobe_rule` (kind
`routing-dev-reprobe-v1`) for later separately frozen reprobes.
`validate_dev_cohort` requires all six cells and the complete
canonical renderer crossing; `natural_mixture_weights` refuses any
population that is not a full-crossing natural-mixture population
(missing cell, missing renderer, duplicates — all regression
tests).

## 6. Reporting repairs

Aggregates now include per-worker frequencies, per-assignment
frequencies, and repeated-output concentration (raw counts);
`group_stats` keeps `latent_program_id`, and `equal_cell_view`
implements the registered hierarchical weighting
(renderer-within-latent, latent-within-cell, equal cells) for the
headline metrics — a synthetic test shows it differing from the
pooled mean exactly where the hierarchy demands.

## 7. B-archive preservation commands (non-blocking item)

Exact verification from a clean clone, recorded here per 214_s:

```
git clone <repo> qwen-grpo-b-verify && cd qwen-grpo-b-verify
git checkout 0f56a65   # last commit at the B execution source identity
# restore step 1 — surface inputs from the companion bundle:
mkdir -p runs/stage0-support/traces/traces
cp plans/conductor/evidence/stage1_b_diagnostic_surface_inputs_098c90cc9647/surface/manifest.json runs/stage0-support/
cp plans/conductor/evidence/stage1_b_diagnostic_surface_inputs_098c90cc9647/surface/payoffs.jsonl runs/stage0-support/
cp plans/conductor/evidence/stage1_b_diagnostic_surface_inputs_098c90cc9647/surface/traces/traces/*.json* runs/stage0-support/traces/traces/
# restore step 2 — run root from the archive:
mkdir -p runs/stage1-b-diagnostic
cp plans/conductor/evidence/stage1_b_diagnostic_973e8adc316e/{artifact_B_diagnostic.json,diagnostic_manifest.json,env_manifest.json,raw_completions.json,run_record.json} runs/stage1-b-diagnostic/
uv sync
uv run python -m tasks.conductor.stage1_b_diagnostic report
# output is byte-identical to plans/conductor/b_diagnostic_report.json
```

## 8. Next

Reviewer confirmation of this repair, then 211_f §15 step 4: the
support-materialization freeze (first-probe rule via
`freeze_first_probe_rule`, candidate prefix, search cap, surface
contract), whose ledger entries — the freeze and, post-run, the
provisional reserve and closeout — start the committed chain with
its externally recorded head.
