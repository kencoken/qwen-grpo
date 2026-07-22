# Conductor experiment log

**Payoff question** (from the where-we-landed synthesis): *when does
hierarchical GRPO have enough reward variation and endpoint advantage to
learn routing, when does textual instruction learning become the
bottleneck, and how do the two interfere when optimized jointly.*

Governing documents: the frozen cell specifications
([`conductor_cell_specs.md`](conductor_cell_specs.md), rev8/v0.8, signed
off 2026-07-18) and the rev6 plan contract
([`plans/conductor/13_f_plan_rev6.md`](plans/conductor/13_f_plan_rev6.md)).
Entries `CE0, CE1, …` pre-register every gate before the GPU spend that
tests it. Backlog = Stage-2+ entry gates.

---

## Stage 0A — minimal environment (pure CPU)

- 2026-07-19 — branch `conductor_stage_0a`. Package `tasks/conductor/`
  implementing spec §1–§3: `types` / `profiles` / `render` / `program`
  (identity, samplers, scheduler, six generators, interventions,
  R_MAGNITUDE, loader) / `resources` / `parser` / `contract` / `tools` /
  `executor` (reference-free; worker interface injected, real pool at 0B) /
  `oracle` / `baselines` / `prompts` / `agreement` /
  `gen_byte_fixtures`.
- 0A acceptance battery: `test_conductor_{types,tools,program,executor,
  baselines,estimands}.py` — golden §3 fixtures (incl. fork O′), golden
  seed/ID fixture, byte-stability fixture (58 request hashes incl. the 36
  shortcut requests), IR validation, scheduler balance, routing bijection,
  every rejection code + the §1.6 global procedure order, §1.7 truth table
  + propagation, intervention positional mapping in both fork orders and
  the §1.9 paired estimand (eligibility, shared denominators, eligibility
  rate, `override_applied=false` abort), §1.16 sensitivity-population
  identity, pseudo-workers (incl. `noop_correct` at a true zero index),
  B1–B6, collision metadata, invalid-profile and R_MAGNITUDE fixtures,
  metamorphic + distractor invariance, structural public/private renderer
  boundary, provenance no-leakage, strip test (scorer tested separately),
  split isolation, valid-AST fuzzing vs `fuzz_oracle.py`,
  shallow-predictor golden fixture.
- **Recorded acceptance command** (2026-07-20, pass):

  ```
  uv run python -m tasks.conductor.agreement --cases 10000
  # agreement: 16665/16665 node executions agree over 10000 latent programs
  # (all 13 operator × cell strata exercised; coverage asserted)
  ```

  The command now distributes the remainder across cells and fails on
  incomplete latent or stratum coverage, so a truncated run can no longer
  report success. (The 2026-07-19 figure, 16,660 executions, covered 9,996
  latents because the per-cell split dropped the remainder.)

- **D16 status: DRAFT.** `tasks/conductor/prompts.py`
  (SYSTEM_LOOKUP/MATH/CODE/DIRECT + demonstrations) is a separately
  reviewed 0A freeze artifact — it requires its own review sign-off and
  freezes before the construction screen. Demos are machine-verified
  legal (executes-through-runtime test).
- Deferred to 0B with their modules: cache-isolation and backend-truncation
  tests (`cache.py`, `workers.py`). **The byte-stability fixture is
  provisional**: it pins user-message bytes plus a symbolic system
  identity, *not* chat-template bytes, so it is not yet the
  cache-key fixture and must be regenerated against the real chat template
  at 0B before any cache-key claim rests on it.
- 2026-07-20 — reviewer findings (`plans/conductor/50_s_stage_0a_review.md`)
  addressed: complete-payoff-surface validation before any oracle/control
  selection; model output totalized inside the typed-rejection boundary
  (non-ASCII numerals, lone surrogates); structural public/private renderer
  boundary via a `PublicParams` projection renderers require by type;
  generation/profile domain closure (latent-index and visibility labels,
  derived public index `i`, int64 representability); construction-only
  shallow-predictor and B1 controls on sanitized public feature records;
  the acceptance hooks above; full `WorkerResult` union enforcement;
  agreement-command coverage accounting. 296 tests green
  (223 → 296), byte fixture unchanged.
- 2026-07-20 — second-round findings
  (`plans/conductor/51_s_stage_0a_review.md`) addressed. **One was a
  conformance bug, not a hardening gap**: `intervention_report` applied
  §1.8's cluster weighting to §1.9's estimates, but §1.9 names *full-sample
  (eligible-set) accuracy* as the primary metric, with clustering entering
  through paired comparisons and the cluster bootstrap. The spec is frozen
  and correct; the code now follows it, and reports the equal-cluster
  values alongside so a gate cannot be read off the wrong rule. Two
  eligible correct observations in one cluster against one incorrect in
  another give 2/3, not 1/2. **This changes Stage-1 intervention gate
  values** and is settled before any construction data exists.
  Also: payoff surfaces are observation-keyed
  (`surface[candidate][cluster][observation_id]`), cell-bound, and
  binary-valued, so pairing is checked by observation identity rather than
  equal counts, and a 0.5 world-failure reward can never enter a
  terminal-accuracy surface; a single `build_observation` derives payload
  disclosure from `visibility_condition` alone; UTF-8 validation extended
  to the direct-answer path; profile workload ceilings; sensitivity rows
  checked for replay and cluster-constant collision metadata; `PublicParams`
  genuinely immutable with control features derived from the projection;
  keyed records required to be ordered rectangular grids. 336 tests green
  (296 → 336), byte fixture unchanged.
- 2026-07-20 — third-round findings
  (`plans/conductor/52_s_stage_0a_review.md`) addressed; the theme was that
  the boundaries were right in direction but bypassable at their edges.
  Observations are bound to the **whole** instance identity
  (`render_instance_id` must agree with every field it encodes) and
  disclose payloads from the instance's own registry, so a mutated
  visibility with a stale id, or a same-manifest registry holding different
  values, cannot leak into the private headline stratum. Payoff surfaces
  are bound to their cell **by identity** — cluster ids are
  `latent_program_id`s and observation ids are `render_instance_id`s, both
  of which name their cell, which node arity alone cannot check because the
  three atomic cells all have one node. A `CalibrationBundle` is now the
  only way to take an oracle-versus-control comparison, because each
  surface validated in isolation cannot prove the controls were scored on
  the same population. `ValidatedSurface` re-checks its invariants in
  `__post_init__`, so a forged or deserialized instance is not an unchecked
  back door. T1's constructive `c` is solved analytically instead of
  enumerated: the reviewer's profile that would have run ~1e9 iterations
  after passing validation now fails in 4 ms, and the draw is bit-identical
  (same value from the same RNG call), so no generated data changed.
  Also: public features have a single source of truth (`feature_row` and
  `shallow_predict` no longer take a numeric mapping); `PublicParams`
  type-checks its values and is one-shot; sensitivity rows are totally
  validated before filtering; the normative IR validator applies the same
  manifest discipline as `InstanceRegistry`; and `PublicParams`,
  `ValidatedSurface` and `InterventionReport` carry explicit JSON forms
  because Stage 1 is resumable and mapping proxies defeat generic
  `deepcopy`/`asdict`. The §1.9 bootstrap wording now states that it
  resamples paired clusters and recomputes the full-sample statistic.
  359 tests green (336 → 359), byte fixture unchanged; all fourteen
  residual probes from the review re-run and closed.
- 2026-07-20 — fourth-round findings
  (`plans/conductor/53_s_stage_0a_review.md`) addressed. **The first was a
  regression I introduced in the third round**: the `CalibrationBundle`
  added to fix arm pairing exposed `argmax` on whatever population it was
  handed, so a qualification-only bundle would reselect the deployable
  assignment — violating "selected on construction data, frozen, never
  reselected" (§1.8, plan contract 7). On a probe it picked (2,2) and
  reported a gap of 1.0 where the construction-frozen (0,0) scored 0.0.
  Worse than an optimistic point estimate: qualification uses
  pre-registered sequential looks, so re-maximizing at each look changes
  the hypothesis under test and voids the alpha-spending interpretation.
  Fixed by enforcing the construction namespace inside every argmax and
  splitting selection from evaluation — `freeze_selections()` records the
  deployable assignment, best-fixed, node runner-ups, best one-call and
  best two-call once, and the qualification API evaluates that artifact
  with no argmax reachable.
- 2026-07-20 — seventh-round findings
  (`plans/conductor/56_s_stage_0a_review.md`) addressed, concentrated in
  intervention reporting. **Impossible sufficient-statistic combinations
  are rejected**: the count *definitions* impose relationships
  (`corrupted + counterfactual ≤ followed`, `followed_successes ==
  counterfactual`, `n_total ≥ 1` so an all-zero cluster cannot pad the
  bootstrap population), not just per-count ranges. **Row coherence**:
  `(mutated_terminal is not None) == downstream_path_succeeded` and a base
  terminal implies eligibility — the executor makes these one fact.
  **Identity + per-cluster statistics are the single source of truth**:
  one `_compute_derived_fields` is used by both `_derive` and
  `__post_init__`, so direct construction and `dataclasses.replace`
  validate exactly as `from_json` does, and every redundant scalar is
  recomputed and compared type-exactly (NaN, float-for-count and
  bool-for-0/1 all rejected; OverflowError guarded). **Frozen-selection
  verification moved to the consuming boundary** per the architectural
  note: `VerifiedFrozenSelections` (a publicly constructible, not truly
  unforgeable marker) was removed, and every evaluation method takes the
  construction bundle and calls `verify_against` in the same call.
  `draw_intervention` binds to the latent's own difficulty profile.
  A changed-lines regression review then found no correctness bugs but two
  dead helpers (`_require_rate`, `_RATE_FIELDS`/`_SIGNED_FIELDS`) and a
  hot-loop cost (profile re-hash per intervention edge), all fixed — the
  public `draw_intervention` validates, the internal `_draw_intervention`
  skips the repeat. 454 tests green (440 → 454), byte fixture unchanged.
  Also: payoff-surface deserialization is lossless and fail-closed
  (persisted `0.5`, `"1"`, `True` are no longer coerced into valid-looking
  binary observations, and duplicate candidate entries no longer collapse
  last-write-wins); B3/B5 build their payloads and host-side binding from
  the instance's own registry, which matters because oracle-vs-one-call is
  a cell-admission gate; `ValidatedSurface` re-freezes every nested
  collection, so a caller's backing dict can no longer mutate a validated
  surface after the fact; surfaces cover exactly one split; persisted
  estimand rows are bound to their encoded identities and totally typed
  (`"false"` no longer reads as true); and the report carries per-cluster
  sufficient statistics for the bootstrap. 380 tests green (359 → 380),
  byte fixture unchanged.
- 2026-07-20 — fifth-round findings
  (`plans/conductor/54_s_stage_0a_review.md`) addressed. The review offered
  two acceptable scopes; **Stage 0A takes the minimal one**, because the
  authoritative provenance layer depends on artifacts that do not exist
  yet (0B fingerprints) and on registration logic that belongs with the
  look schedules in 1A `calibrate.py`. The partial `PopulationManifest`
  added last round was therefore removed rather than extended — it read
  like a provenance check while establishing neither the registered
  population nor a shared execution environment, and its execution fields
  were all `None`. See "Scope of the calibration guarantees" above for
  what is and is not guaranteed, and `GATE_PROVENANCE_REQUIREMENT` in
  `oracle.py` for the same statement in code.
  Persistence and semantics, which the review required under either scope:
  `FrozenSelections` now validates the *meaning* of its fields (constant
  best-fixed, exactly-one-node runner-ups covering every node, two-call
  only for fork/join, finite accuracies), is content-addressed to its
  source bundle with `verify_against()` re-deriving the argmax, renames
  the frozen random control `construction_random_accuracy` (the control is
  defined on the surface being evaluated, so qualification uses
  `CalibrationBundle.random_accuracy()`), and parses JSON totally — an
  overlong `best_two_call` is no longer silently truncated.
  `InterventionReport` is recursively immutable, carries complete
  per-cluster sufficient statistics (including clusters with zero eligible
  observations, which a bootstrap over the latent population needs), and
  recomputes its redundant headline fields at load. Intervention rows must
  name a real *directed* dependency edge — reversed, self and fork-sibling
  pairs are rejected — with required integer golds. 416 tests green
  (380 → 416), byte fixture unchanged.
- 2026-07-20 — sixth-round findings
  (`plans/conductor/55_s_stage_0a_review.md`) addressed; the scope decision
  above was confirmed sound and the remaining work was concentrated in
  intervention reporting.
  **An intervention report now covers exactly one (cell, split, edge)**:
  `lookup_math` and `math_code` both define `n1->n2`, so a shared edge
  tuple was not enough to prove one population, and pooling either two
  cells or two splits silently changed the admission statistic.
  **Causal targets are enforced across renderings**: one replacement is
  drawn per (latent, edge) and each latent is rendered several ways, so
  `gold_answer` and `counterfactual_gold` are latent-level constants, and
  §3's replacements provably change the sink — a report where they were
  equal previously claimed old-answer persistence 1.0 *and* counterfactual
  consistency 1.0 for the same execution. `draw_intervention` now enforces
  the legal directed edge and asserts the moved sink at the source.
  **Identity plus per-cluster sufficient statistics are the persisted
  source of truth**: one `_derive` constructor builds every other field
  and is used by both live computation and `from_json`, which recomputes
  and compares all of them, so no headline value is forgeable; the
  ambiguous `n_clusters` split into `n_population_clusters` and
  `n_eligible_clusters`.
  **Frozen-selection verification is mechanically visible**: evaluation
  accepts only `VerifiedFrozenSelections`, returned by
  `verify_against(construction_bundle)`, since a side-effect-free method a
  caller may forget gives the consuming operation no evidence; the digest
  is renamed `source_surface_digest` with a schema tag, because it hashes
  surface-result content rather than experiment identity. 440 tests green
  (416 → 440), byte fixture unchanged.

### Scope of the calibration guarantees (read before trusting a number)

**Stage 0A ships the structural half of calibration only.** What is
mechanically guaranteed here:

- Selection is construction-only: every argmax refuses a non-construction
  surface, and qualification consumes a persisted `FrozenSelections`
  artifact exposing no argmax (§1.8, plan contract 7 — "frozen, never
  reselected"). Those selections are semantically validated (constant
  best-fixed, one-node runner-ups, two-call only where the family is
  defined) and content-addressed to their source bundle, so a revived
  artifact can be re-derived from the surfaces it claims to come from.
- `CalibrationBundle` proves its assignment and control arms carry the
  same cluster and observation identities, and each surface is bound by
  identity to one cell and one split.

What is **not** established, and is therefore deferred:

- That a surface is the *registered* population — namespace caps,
  deterministic prefixes, the pre-registered look schedule, three-renderer
  crossing, the scheduled visible slice. That registration logic belongs
  with the look schedules in Stage-1A `calibrate.py`.
- That the arms ran under one *execution* environment — runtime-profile
  fingerprint, endpoint fingerprints, D16 prompt revision. Those artifacts
  do not exist until Stage 0B.

A partial manifest was implemented and then removed: it read like a
provenance check while establishing none of those properties, which is
worse than its absence. Consequently every accuracy and difference
`CalibrationBundle` returns is **descriptive** (and named so —
`descriptive_deployable_minus_one_call`), and `gate_report()` raises
`GATE_PROVENANCE_REQUIREMENT` rather than dressing a provenance-free float
as a Stage-1 gate result.

The same scope statement applies to the other pure estimators:
`estimands.intervention_report` and `oracle.signed_deployable_gap` are
structural point estimators. Both enforce the invariants Stage 0A *can*
enforce — one (cell, split, edge) population per report, identity-bound
rows, cluster-constant causal targets — but neither is a Stage-1 or
Stage-2 result until the 1A layer supplies the registered population, the
execution provenance, the paired clustered interval, and (for the Stage-2
comparator) the schema-valid rate §1.8 requires alongside it.

### Must block the construction screen

- **D16 review and freeze** against the real 1.5B workers
  (`tasks/conductor/prompts.py`, `D16_STATUS = "DRAFT"`).
- **B1 controls frozen before construction outcomes are inspected** — the
  fitting and selection rules are implemented and frozen in code
  (`fit_majority_class`, `echo_family`, the shallow predictor); the fitted
  models must be recorded here before anyone looks at construction
  accuracy.
- Replacement of the provisional request hashes with actual chat-template
  bytes during Stage 0B.
- **A canonical population + execution manifest bound to every calibration
  artifact** before the construction screen or the first qualification
  look — a Stage-1A `calibrate.py` deliverable, deliberately not stubbed
  at 0A. It must establish: registered latent/render ids including
  renderer crossing and visible-slice support, namespace caps and
  deterministic prefixes, the pre-registered look schedule, generator and
  difficulty-profile versions, plus the runtime-profile fingerprint,
  endpoint fingerprints and D16 prompt revision (Stage 0B), compared
  **across arms** so assignment and control surfaces cannot come from
  different environments. Until it exists, `CalibrationBundle.gate_report()`
  raises and no Stage-1 gate may be reported.

### Stage 0A close-out (2026-07-20)

**Signed off** in `plans/conductor/57_s_stage_0a_review.md` ("I recommend
Stage 0A sign-off after the small remaining changes below"), after eight
review rounds (`50_s`–`57_s`). The three remaining P3 items were
implemented in the final commit:

1. `draw_intervention` requires a self-consistent latent identity — the
   current `generator_version`, and a `latent_program_id`/`seed` that
   re-derive from the latent's own cell/namespace/index — since the
   intervention seed derives from that id.
2. `InterventionReport` canonicalizes every derived field after the
   tolerance comparison, so a within-tolerance float perturbation cannot
   survive a round-trip or retain an accuracy fractionally above 1.
3. `validate_instance` validates the exact §1.3 record shape and parsed
   identity first, and translates every failure (missing fields, malformed
   ids, renderer errors, regeneration failures) into `LoadError` — the
   persisted-artifact boundary the resumable Stage-1 loader relies on.

**Final acceptance evidence** (close-out procedure from `57_s`, all on the
closing commit):

```
uv run pytest -q -W error            # 463 passed (50 pre-existing + 413 conductor)
uv run python -m tasks.conductor.agreement --cases 10000
# agreement: 16665/16665 node executions agree over 10000 latent programs
# (all 13 operator × cell strata exercised; exit 0)
uv run python -m tasks.conductor.gen_byte_fixtures   # 58 hashes, no diff
git diff --check                     # clean
```

Per the reviewer's guidance, no further Stage 0A adversarial audits: the
next scientifically valuable review runs against real Stage 0B/1 execution
(worker/runtime fingerprints, real chat-template bytes, cache keys, trace
persistence, execution provenance, calibration integration). From here,
any change to frozen generation, rendering, prompt, parser or tool
behavior is a **versioned experiment change** (bump
`GENERATOR_CODE_VERSION`; after qualification data exists it retires the
affected qualification set), never an informal cleanup. The
construction-screen blockers above remain the gating items before
qualification.

## Stage 0B — runtime (first GPU)

### Implementation (2026-07-20, branch `conductor_stage_0b`)

Deliverables per the rev6 plan (Stage 0B + §8):

- `tasks/conductor/runtime.py` — versioned runtime profile
  (`DEFAULT_RUNTIME_PROFILE`, schema-validated at load like the
  difficulty profile; repo defaults are not the experiment — the named
  Stage-0C launch profile is a separate 0C artifact) and the three §1.10
  fingerprint scopes: `rtp-` (full profile incl. observation condition —
  Conductor-side generations and trace manifests), `wv-` (worker-visible:
  model/tokenizer revisions, per-endpoint chat-template SHAs, NF4 config,
  caps, truncation/stopping, greedy decoding, grammar/tool versions,
  resource policy — observation condition excluded, D11), `ep-`
  (selected endpoint). Float-valued fields encode as shortest-round-trip
  decimal strings (§1.13); `canonical_json` rejects raw floats/bools.
  `build_runtime(profile)` / `Runtime.close()`; `worker_call_batch`
  renders through the chat template, consults the cache, dedupes
  byte-identical in-flight misses (one generation, one stored row), and
  returns records in input order.
- `tasks/conductor/workers.py` — `WorkerPool`: the three frozen 1.5B
  endpoints (§1.6) at pinned revisions (Instruct 989aa798…, Math
  aafeb0fc…, Coder 2e1fd397…), NF4 (double-quant, bf16 compute),
  tokenizers eager (the chat template is a fingerprint input), models
  lazy, per-worker microbatched greedy generation under per-worker token
  caps, §1.6 telemetry (`finish_reason`, generated tokens,
  `generation_hit_token_cap`); the eos set is read from the model's
  generation config (Qwen2.5 lists both `<|im_end|>` and
  `<|endoftext|>`).
- `tasks/conductor/cache.py` — SQLite write-through completion cache,
  key = worker-visible fp + endpoint fp + SHA-256 of the canonical
  rendered request bytes; full request bytes stored and compared on every
  hit; telemetry columns survive hits (§1.10); a same-key store with a
  different completion raises (greedy precondition), identical re-store
  is idempotent; executed `WorkerResult`s never cached.
- `tasks/conductor/executor.py` — `execute_workflow_batch`: wave
  batching by worker × depth (depth = workflow position) with per-item
  §1.7/§1.9 semantics unchanged; `execute_workflow` is now the
  single-item case of the same code path, so the signed-off 0A battery
  pins both. `TraceWriter`: JSONL step traces under
  `runs/<run_name>/traces/` (`steps.jsonl` + `manifest.json` embedding
  the full profile and all three fingerprint scopes; stable `item_id` =
  `render_instance_id`; refuses to overwrite an existing trace file).
  Infrastructure failures raise.
- `tasks/conductor/gen_chat_fixtures.py` +
  `fixtures/chat_template_bytes.json` — the promised replacement for the
  provisional request hashes: SHA-256 of the real chat-template-rendered
  request bytes (69 hashes: 3 template SHAs; every cell × step × all
  three endpoints; the 18 two-call shortcut workflows × 2 calls through
  their pair endpoints). **The Math tokenizer ships a different chat
  template from Instruct/Coder**, confirming per-endpoint template SHAs
  in the cache key. Direct-arm (B1/B3/B4/B5) rendering runs on the
  policy model and is fixed at Stage 1A with `calibrate.py`; its user
  bytes remain pinned by the 0A fixture.
- `test_conductor_runtime.py` (25 tests): profile schema + float
  encoding; fingerprint scopes (visibility/mixture/cache-path/batch/
  policy-cap changes leave `wv-` fixed and move `rtp-`; revision/NF4/
  tool/policy/template/cap changes move `wv-`); write-through then hit
  with telemetry survival; duplicate-miss dedup; endpoint and
  worker-visible cache isolation; a visibility flip shares completions
  across conditions (D11); persistence across reopen; greedy-violation
  and corrupted-row guards; batch-vs-sequential equivalence (all six
  cells reference-routed; all 9 routings of a lookup_math instance with
  overrides); wave grouping by worker × depth; duplicate item_id
  rejection; trace manifest/steps content; overwrite refusal;
  chat-template fixture stability. Full suite: **488 passed** (463
  pre-existing + 25 new) under `-W error`.

### Recorded smoke command (2026-07-20, RTX 4090, pass)

```
uv run python -m tasks.conductor.smoke --per-cell 2 --run-name stage0b-smoke
# 12 workflows (2/cell x 6 cells), profile rtp-9c5bce7af62279ff,
#   worker-visible wv-18e02c2032fd9069
# pass 1: calls {'lookup': 6, 'math': 4, 'code': 4}, cache hits 0, truncated 4
# pass 1: step statuses {'typed_failure': 14, 'dependency_blocked': 6};
#   terminal correct (descriptive) 0/12
# pass 2: calls {'lookup': 6, 'math': 4, 'code': 4}, cache hits 14/14
# smoke OK
```

The smoke gates machinery only: real NF4 pool end-to-end, traces +
manifest written, second pass fully cache-served, replayed completions
identical. It is not an accuracy gate (no registered population, no
execution manifest comparison across arms).

### D16 findings from the smoke traces (input to the D16 review)

Zero-shot with the DRAFT D16 system prompts, 0/14 worker calls produced
an executable artifact:

- Lookup and Math emit the **correct expression without the
  `<artifact>` envelope** (`E_NO_ARTIFACT`), e.g.
  `lookup(R-5E8, "Rowan", "seats")` as plain text.
- Code emits the envelope but writes the **resource handle instead of
  the literal identifier `resource`**
  (`<artifact>count_gt(stable_unique(R-3B8), 8)</artifact>` →
  `E_PARSE`).
- 4 of 14 calls hit the 256-token cap (`generation_hit_token_cap`).

These are exactly the failure modes the D16 review-and-freeze against the
real workers exists to address (envelope emphasis, `resource` identifier
emphasis, cap sizing) — now reproducible end-to-end through the runtime
before the construction screen. Any D16 prompt change re-fingerprints
requests and regenerates `chat_template_bytes.json` by construction.

### D16 revision cycle (2026-07-21, branch `conductor_stage_0b_d16`)

Five refine→critique iterations against the real pool, recorded in
`plans/conductor/60_f`–`69_f` (revision + evidence docs even, critiques
odd; paired construction instances throughout; qualification untouched;
`D16_STATUS` still DRAFT). Outcome at the pause point
(`68_f_d16_rev5.md` consolidates):

- **Lookup 45/45 (100%)** — fixed at rev1 (worked example + duplicated
  envelope contract), stable since.
- **Code 26/30 (86.7%)** — envelope fixed at rev1, count-shape
  identifier at rev2, select nesting at rev3, layout regression
  recovered at rev4 (rule first + last); the four residual failures are
  ALL fork_join count-branch handle substitutions (two-handle problem
  contexts) — the one remaining prompt-side lever if a further cycle is
  authorized.
- **Math 0/56 — endpoint-model question, escalated.** Probe 1 (`64_f`):
  three maximally different system prompts all 0/20 (content
  irrelevant); probe 2: base Qwen2.5-1.5B-Instruct with the same prompt,
  same requests: 20/20 legal, 0 truncated. No prompt makes
  Qwen2.5-Math-1.5B-Instruct emit the envelope; it solves and boxes
  regardless. **Blocking D16-review decision**: §1.6 endpoint swap
  (versioned experiment change) vs accepting Math-cell qualification
  failure (which would gut four of six cells' reference paths).
- Mechanistic account the trail supports: worked examples teach
  structure, layout position teaches priority, prose rules teach almost
  nothing (rev3→rev4 is the controlled comparison).
- `D16_REVISION` provenance now in the runtime profile (worker-visible);
  `chat_template_bytes.json` regenerated per revision; 488 tests
  `-W error` throughout.

### D16 cycle continuation: revs 6–9 and close (2026-07-21)

Ken provisionally signed off the Math endpoint swap to base
Qwen2.5-1.5B-Instruct (recorded in `70_f`, spec §1.6 erratum deferred to
the D16/third-party review; critiques thereafter address prompts only).
Continuation trail `70_f`–`77_f`; iteration ran until ideas were
exhausted or a model limit dominated, per instruction. Final state
(rev9 texts, per-cell-30 confirmation incl. 15 unseen instances/cell —
first out-of-tuning-set evaluation, no overfit cliff):

- **Lookup 90/90, Math 116/116** — both closed at 100%; Math correct in
  value everywhere, zero truncation anywhere after the swap.
- **Code 78/90 (86.7%)** — code_atomic 29/30, fork_join 26/30,
  math_code 23/30. **Model-limit verdict** (pre-registered rule, 75_f)
  on the dominant residual: a value-triggered index-safety guard
  (`step_1 % length(resource)`) fired for step_1 ≳ 9–11, surviving
  four treatments; a matched-regime demo cleared only its literal value
  (step_1 = 10) — anchoring without abstraction. Mitigation flagged for
  the construction screen: the phase-2 (S) band choice can keep
  math_code indexes ≤ 8 and sidestep the trigger (`76_f`).
- New transferable findings: concrete wrong exemplars backfire when
  they flatter the model's prior (rev7→rev8 controlled pair);
  demonstrations anchor to literals at 1.5B (rev9).
- Terminal correct 167/180 (92.8%), from 17% at rev1. Descriptive gate
  outlook: math_code E_PARSE 23% would fail the 1A <2% parse gate
  absent the index-band mitigation or cell failure — both priced in.

### Still blocking the construction screen (unchanged from 0A close-out)

D16 review + freeze against the real workers (evidence package
`60_f`–`77_f` complete; blocking decisions now: ratify the §1.6 Math
endpoint erratum, freeze rev9 texts, rule on the math_code index band);
B1 controls frozen before construction outcomes are inspected; the
canonical population + execution manifest (Stage-1A `calibrate.py`).

## Backlog (Stage-2+ entry gates)

- CE0 (at 0C): benchmark gates — <22 GB peak, projected seed ≤ overnight,
  sane reward distribution; worst-case throughput prediction incl.
  enumeration cost on the 100-example construction pass.
- CE1 (before qualification data): the Stage-1A gate table (plan §Stage 1A)
  + named unknowns + pre-registered dynamics predictions + alpha-spending
  schedules for both sequential-look plans; one/two-sided boundaries per
  gate. **Also pre-register the cluster-bootstrap degenerate cases**: how a
  replicate that draws zero eligible observations is handled, and the same
  for zero *followed* observations in the secondary follow-through
  diagnostic. `InterventionReport.cluster_successes` retains zero-eligible
  clusters precisely so those replicates are drawable rather than silently
  absent, but the resampling rule itself is a CE1 decision.

## Entries

*(CE0, CE1 to be pre-registered here before any GPU spend.)*

### 2026-07-22 — D1 ratified; 92_s frozen; Tranche A authorized

- **D1 ratification (Ken):** the `worker_dev` namespace erratum `88_f`
  (as amended per 89_s) is ratified; `worker_dev` commands are
  authorized from this commit forward. Usage contract: adaptive
  inspection permitted; permanently barred from construction,
  qualification, train, dev and test; cap 30/cell is the stopping rule.
- **92_s frozen (Ken):** the scope × model × prompt preregistration is
  FROZEN with its Freeze Record (prompt shas incl. `code_local_v1`
  `17a05a19…`, both contract digests, cohort `c0f53203…`, support
  registry `84b4baa3…`, retained P0 artifact hashes, frozen cost gate,
  `EXPERIMENT_DEVICE`). The executable commit for Tranche A is the
  commit carrying this entry; screen/reveal verify it. Review chain:
  92_s → 94_s/95_f → 96_s/97_f; reviewer committed to changed-lines
  re-checks only.
- **P0 record:** replays at `20dc20c` — original ×2 bit-identical
  (0/90), reversed-within-chunk 0/90 (sensitivity = batch composition,
  not position), singleton 2/90 reproducing 78_s microbatch-1 exactly;
  raw artifacts retained in `runs/p0-rev9-replay/` (hashes in the
  Freeze Record).
- **Executable-commit addendum (2026-07-22):** the post-freeze rename
  of the 91–97 cycle docs (`81b7ec6`, zero content change) moved HEAD;
  the commit carrying THIS addendum is the executable commit for
  Tranche A. Nothing else lands before launch; the screening/reveal
  checkout guard verifies against the P1 artifacts' recorded commit.
- **2026-07-22 106_s UNIT 2 — FOUR-WORKER RUNTIME + RECORDED SMOKE
  (112_f):** v2 profile embeds the ordered WorkerSpecs (re-derived and
  compared against the frozen registry; microbatch frozen at 1;
  task_last required); FourWorkerPool shares physical objects by
  derived weights key, verifies registered prompt SHAs at construction
  and NF4-unpacked parameter counts at load; FourWorkerRuntime cache
  key = wv + slw (selected-logical-worker execution fingerprint) +
  request in the new worker_completions table (§8.5: no v1 field
  carries the new identity); PoolTraceWriter = trace schema v2 binding
  pool fingerprint + logical-to-physical mapping. Smoke re-enabled on
  the four-worker pool and recorded: 19 workflows (reference + :w3 +
  :wf), pass 1 33 calls wall 10.5s, worker 3 6/6 success on the real
  3B checkpoint, wrong-family item typed 0.5 no abort, pass 2 33/33
  cache-served byte-identical, peak reserved VRAM 3.18 GiB. 615 tests;
  agreement 16,665/16,665 unchanged.
- **2026-07-22 106_s FROZEN — STAGE 0 FOUR-WORKER ORCHESTRATION
  PIVOT (Ken sign-off, all five §0 decisions):** the universal-Code-
  worker search stops; Stage 0 finishes around a flat four-worker /
  two-checkpoint pool (lookup_1p5b, math_1p5b, code_1p5b, code_3b; one
  rev10 bundle, task_last, NF4, singleton-v1), motivated by the
  verified 235/22/13/0 rev10 overlap (union 270/270, selection
  evidence only). 4^S action space (4/16/64), Coder checkpoints
  retired, universal-worker acceptance requirement retired (§6.4),
  cascade + router analysis deferred to Stage 1, pre-materialized
  outcomes the preferred Stage-0C path. Freeze Record appended
  (approved draft @08ae2a1 sha 73f30391…; identity hashes recorded).
  Implementation proceeds in the §13 review units: (1) registry +
  schema erratum + CPU fixtures, (2) 0B runtime, (3) evaluation
  support, (4) 0C integration, (5) CE0 + handoff.
- **2026-07-22 3B SCREEN OUTCOME — ALL FOUR ARMS MISS (105_f):**
  generic_3b 878 (rev10) / 869 (rev11); coder_3b 741 / 752. Guard held
  everywhere (4×630 Lookup/Math records byte-identical to 99_f). Scale
  is non-monotonic: generic_3b fixed ALL 13 characterized 1.5B
  residual cases under both prompts but introduced global composition
  (solves the whole Problem in one node, fork_join goal_first 15/30)
  and the first legal-but-wrong-value Code outputs in the D16 record.
  Instruction-capacity hypothesis refuted (rev11@3B < rev10@3B; handle
  substitution reappears at scale). Coder prior = anti-protocol prior:
  ~150 handle-substitution failures per coder_3b arm; every coder
  variant loses to its generic sibling at both scales. Admission
  incident disclosed: coder_3b-rev10 attempt 1 refused by the frozen
  cost gate (P1 #1 wall included the one-time checkpoint download);
  clean re-attempt under the unchanged gate admitted at ~300s
  projected (P0-precedent, flagged for ratification). Best known
  remains generic_1p5b/task_last/rev10 at 887/900. All dominant modes
  are Problem-visibility failures → local_only is the evidenced next
  probe; orchestration pivot case now "considerably stronger" (103_s
  criterion). Next decision is Ken + reviewer's.
- **2026-07-22 103_s REVIEW + 104_f 3B SCREEN PREREG:** reviewer
  verified all rev10/rev11 figures and added the union analysis — no
  Code case is missed by all three 1.5B policies (A∪B∪C = 270/270
  oracle; cell×renderer routing perfect, held-out 135/135, but
  renderer-conditioned). Two 102_f claims corrected by addendum:
  conservation-of-failures is a hypothesis (three rules changed
  jointly), and the recency mechanism is wrong (the final
  handle-substitution sentence stayed literally last) — the defensible
  framing is prompt interference/instruction load. 104_f preregisters
  the 103_s course: {generic_3b, coder_3b} × task_last × {rev10,
  rev11}, tranche F3, generic arms first (rev11-at-3B unconditional as
  the instruction-capacity test), coder arms only if both generic arms
  miss; frozen gates unamended; 630 Lookup/Math records byte-identity
  guard vs the 99_f run (F3 support digests are byte-identical to the
  1.5B counterparts — one shared Qwen2.5 chat template, so the screen
  swaps weights only). Prompt editing on the current worker_dev
  population is closed; the complementary 1.5B policies are preserved
  for a separate orchestration prereg.
- **2026-07-22 rev11 FOLLOW-UP OUTCOME (101_f/102_f):** both arms
  admitted; both MISS; stop rule applied. rev11 fixed 10/13 targeted
  cases but induced 19 regressions (handle substitution returned —
  rule-dilution reproducing the rev3/rev4 layout sensitivity): net
  878/900 vs rev10's 887/900. Conditional coder arm 844/900 (fork_join
  goal_first 1/30 — composition mode) closes the 1.5B model switch on
  full evidence. Conservation-of-failures at 1.5B demonstrated = the
  properly-measured model-limit signature. Best known remains
  generic/task_last/rev10 at 887/900; fails both the 30/30 target and
  the §4.2 floor → next step is a new decision (102_f: 3B escalation
  under task_last+rev10 is the evidenced option).
- **2026-07-22 rev10 FOLLOW-UP OUTCOME (99_f/100_f):** ADMITTED;
  the Math parenthesis fix landed completely — math_code × bound_var
  0/30 → 30/30, Math perfect 360/360, zero regressions, and all 540
  Lookup/Code records byte-identical to the Tranche A sentinel (the
  amendment provably touched Math only). Target not reached (Code
  residual 13/270 unchanged, all protocol-class, three characterized
  modes) → one-revision stop rule applied. task_last is now viable
  (Lookup+Math perfect under it); next decision: a Code-targeted
  preregistration on the anchor generic_1p5b/task_last/rev10.
- **2026-07-22 TRANCHE A OUTCOME — TERMINAL STOP (98_f):** all eight
  arms ADMITTED (singleton-v1 bit-stable everywhere, within the cost
  gate); no clean prefix anywhere; both contract sentinels executed;
  both contracts `proven_non_target` on full validated Lookup/Math
  evidence (current: Lookup/Math imperfect on fresh instances;
  task_last: Lookup perfect but Math 0/30 on math_code × bound_var);
  `selected: None`; Tranche B never opened per §5/§11. Key findings:
  task_last dominates current in every paired contrast; rev9 dominates
  code_local_v1 in every paired contrast (retire it); best arm
  generic_1p5b-task_last-rev9 at 285/300 blocked by exactly one
  localized Math interaction. Continuation requires a new
  preregistration (98_f records the decision inputs).
- **Next (superseded by the terminal stop):** Tranche A in the frozen `arm_order` — eight candidate P1
  triplets (three fresh processes each), `screen`, launched full runs
  under append-only `selection-r1` receipts, `reveal`. The worktree
  stays clean; all outputs land under `runs/` until the experiment
  closes.
