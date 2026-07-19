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
  baselines}.py` — golden §3 fixtures (incl. fork O′), golden seed/ID
  fixture, byte-stability fixture (58 request hashes incl. the 36 shortcut
  requests), IR validation, scheduler balance, routing bijection, every
  rejection code + the §1.6 global procedure order, §1.7 truth table +
  propagation, intervention positional mapping in both fork orders,
  pseudo-workers, B2, collision metadata, invalid-profile and R_MAGNITUDE
  fixtures, metamorphic + distractor invariance, provenance no-leakage,
  strip test (scorer tested separately), split isolation, valid-AST
  fuzzing vs `fuzz_oracle.py`, shallow-predictor golden fixture.
- **Recorded acceptance command** (2026-07-19, pass):

  ```
  uv run python -m tasks.conductor.agreement --cases 10000
  # agreement: 16660/16660 node executions agree (operator × cell strata)
  ```

- **D16 status: DRAFT.** `tasks/conductor/prompts.py`
  (SYSTEM_LOOKUP/MATH/CODE/DIRECT + demonstrations) is a separately
  reviewed 0A freeze artifact — it requires its own review sign-off and
  freezes before the construction screen. Demos are machine-verified
  legal (executes-through-runtime test).
- Deferred to 0B with their modules: cache-isolation and backend-truncation
  tests (`cache.py`, `workers.py`); the canonical rendered request gains
  the chat-template layer there (0A pins system-name + user bytes).

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
