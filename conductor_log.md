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

## Backlog (Stage-2+ entry gates)

- CE0 (at 0C): benchmark gates — <22 GB peak, projected seed ≤ overnight,
  sane reward distribution; worst-case throughput prediction incl.
  enumeration cost on the 100-example construction pass.
- CE1 (before qualification data): the Stage-1A gate table (plan §Stage 1A)
  + named unknowns + pre-registered dynamics predictions + alpha-spending
  schedules for both sequential-look plans; one/two-sided boundaries per
  gate.

## Entries

*(CE0, CE1 to be pre-registered here before any GPU spend.)*
