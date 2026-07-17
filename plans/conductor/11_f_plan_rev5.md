# Conductor Stages 0–1, v5 (final — signed-off spec)

## Context

Implements Stages 0–1 of `conductor_task_proposal.md` on the `conductor` branch.
v5 = v4 + the final specification patch from `conductor_plan_v4_critique.md`
(reviewer: implementation-ready subject to these fixes). Governing principle:
*preserve extension points for the full architecture; implement one end-to-end
vertical slice before adding another abstraction.* One recorded deviation from the
critique: the launch profile keeps **β=1e-3 log-only** (house convention — KL drift
gauge on the dashboard) instead of the suggested β=0.

## v0 scope

- **Integer-only public outputs.** Private resources: keyed integer records and
  integer lists (a record may hold several named integers, e.g. `Q41: a=83719,
  b=43, c=1`). Fractions internal only when they resolve to integers.
  Noncanonical integer wire forms (`"0012"`) rejected. Extension point: `types.py`.
- **Six cells**: atomic Lookup, atomic Math, atomic Code, Lookup→Math, Math→Code
  (computed index), fork/join Lookup+Code→Math (diagnostic). Operators (integer-
  safe): keyed retrieval, affine/ratio/modular numeric, indexed selection,
  stable-dedup, `count_greater_than`. Hidden-Math cells: operands in a private
  numeric record, formula public; tool-demand (operand size, modular forms) tuned
  *within* cells during screening.
- **`conductor_cell_specs.md` is the first Stage-0A deliverable** (frozen, linked):
  per cell — private resource schema; public instruction/formula; artifact
  grammar; predecessor variable names (`step_1`, …); parameter ranges + rejection
  sampling; direct reference function; ordinary + boundary hand-calculated
  examples; intervention generation (both kinds, below); one-call baseline prompt
  and payload. **Reference subtasks are tool-neutral** (describe the semantic
  operation; never name a worker or endpoint-specific syntax).
- **One transparent renderer, two manually authored cosmetic variations** —
  variants of one latent program are one statistical cluster (paired
  cluster-bootstrap intervals).
- **Model-plus-tool endpoints** (framing locked): endpoint = frozen 1.5B model +
  endpoint-specific tool + artifact grammar. Equalized-tool factorial deferred.

## Locked contracts

### 1. Per-stage action space and output format

| Stage | Learnable | Policy emits | Fixed (harness-supplied) |
|---|---|---|---|
| 0C smoke | worker_id (one step) | routing schema | topology, subtask, resources, access |
| 2 routing-only | **worker_id only** | **routing schema** | reference topology, reference subtasks, resource handles, predecessor access, number of calls |
| 3 decomposition-only | subtask wording | subtask schema | oracle workers, topology, resources, access |
| 4 joint | steps, subtasks, worker_ids, resources, access | full workflow JSON | budgets/limits (contract 2) |

**Routing schema** (Stages 0C/2): `{"worker_ids": [1, 2]}` — extra fields are
**rejected, not ignored** (no credit assignment to tokens outside the action
space). Acceptance test: bijection between routing completions and the enumerated
3/9/27 worker assignments. (Side benefit: Stage-2 completions are ~a dozen tokens
→ fast routing-only training.)

### 2. Execution rules and resource limits (task-independent, executor-enforced)

- Handles must belong to the instance's public manifest; **registries are
  instance-scoped** (foreign handles never resolve).
- ≤1 private resource per step (v0); no duplicate handles; fixed caps on total
  calls and resource requests.
- Downstream aggregation uses predecessor values, never re-requested resources.
- **Legal v0 access patterns**: `[none]` atomic; `[none, all]` two-step;
  `[none, none, all]` fork/join. Anything else is a schema violation (reward 0.0).
- Disclosure is **action-controlled only**; the executor never consults the
  reference program.

### 3. Worker artifact protocol

- Every tool-required endpoint emits **exactly one** `<artifact>…</artifact>`
  (reasoning allowed outside; duplicate/mixed/unexpected terminal tags invalid).
  Endpoint determines grammar and tool: Math → arithmetic expression → exact
  calculator; Code → restricted sequence expression → whitelist interpreter;
  Lookup → retrieval expression (`lookup(Q31, "Cedar", "units")`) → host executes
  against the authorized payload.
- Host constructs `WorkerResult(status, value: Integer, artifact_valid,
  tool_executed)`. **Executed tool result is authoritative.** Tools return
  **typed rejections** for expected artifact errors; unexpected exceptions
  propagate (abort).
- `<value>` responses reserved for the deferred answer-only control.

### 4. Reward table (pre-registered; the boundary principle: 0.0 = the action
string is malformed; 0.5 = a well-formed action that fails in the world)

| Outcome | Reward |
|---|---:|
| Invalid JSON/schema, wrong field types, step-count violation, illegal topology/access pattern, duplicate resources, over-budget request | 0.0 |
| Schema-valid action with unknown handle, denied hard-control authorization, worker parse failure, invalid artifact, typed tool rejection, or wrong final answer | 0.5 |
| Correct executed terminal result | 1.0 |
| Unexpected infrastructure exception (OOM, model failure, cache corruption, trace I/O) | **abort update** |

### 5. Reference-free execution, executor/scorer split

- `terminal_result = executor.execute(action, public_context, registry,
  endpoints)`; `reward = scorer.compare(terminal_result, gold_answer)`. The
  executor receives **neither the reference graph nor the final answer**.
- Execution contract is globally integer-valued (no per-node type lookup).
- **Strip test**: delete all reference metadata *and the gold answer*; an
  arbitrary sampled workflow must execute identically from {public prompt +
  manifest, instance registry, sampled action, endpoint definitions}. Scoring is
  tested separately against the gold.

### 6. Information conditions and baselines

- Conditions: *primary causal* (payloads hidden from Conductor; every candidate
  worker for a node receives the same local payload); *hard-routing control*
  (exclusive authorization); *visible* (paired observation condition over the same
  latent programs — paired-policy experiment deferred; a **pre-registered ~100-
  program visible qualification slice** ships in Stage 1 so direct/echo baselines
  are informative).
- **Three direct baselines per cell**: (1) public-prompt-only (leakage check);
  (2) local capability (3B given a worker's single-node payload + instruction);
  (3) **best one-call whole-task** (one endpoint, union of relevant payloads) —
  the only one that speaks to hierarchy's value. Plus echo worker, no-op worker
  (informative on the visible slice), answer-in-subtask telemetry always on.

### 7. Oracle and intervention semantics

- **Deployable cell oracle**: assignment selected on construction data, frozen,
  evaluated on fresh qualification data — used for all gates and Stage-2 targets.
  **Hindsight per-example maximum** is diagnostic only (it exploits realized
  worker noise). Also record best-fixed and random assignments.
- **Two intervention tests per dependency edge**: *corruption* (mutate
  intermediate, keep original target; correctness must fall) and **counterfactual
  consistency** (mutate intermediate, recompute the reference sink; execution must
  follow to the *new* answer — the stronger evidence the dependency is used).
  Replacements constructed to provably change the sink. Missing/skip variants are
  reported but prove only tool input-validation.
- Fork gate wording: *baseline accuracy minus corrupted-branch accuracy ≥20
  points for each branch*, paired lower confidence bound.

### 8. Runtime profile, cache, calibration persistence

- **Versioned runtime profile** (serialized into every trace manifest and W&B
  config): worker model ids + revisions, tokenizer/chat template, NF4 config,
  tools + versions, visibility/resource policy, token caps + truncation/stopping
  rules, cell mixture, cache path, batch shape, `workflow_max_steps`.
  `build_runtime(profile)` / `close()`.
- **Named Stage-0C launch profile checked in** (repo defaults are not the
  experiment): 3B QLoRA rank 16, **β=1e-3 log-only** (house convention; recorded
  deviation from review's β=0), group size 8, two prompt groups/update, policy
  completion limit, per-worker token caps, **per-worker inference microbatch cap**.
- **SQLite write-through cache from Stage 0B**, key =
  `runtime-profile fingerprint + selected-endpoint fingerprint + canonical
  rendered request` (fingerprints cover model/tokenizer revisions, chat template,
  NF4 config, caps, truncation, stopping, `do_sample=False`, artifact grammar,
  tool version, visibility/resource policy).
- **`calibrate.py`** (in the file inventory): resumable; per-call and per-example
  write-through records; payoff surfaces; gate report. Any generator, renderer,
  prompt, tool, parser, or profile change after qualification **retires that
  qualification set**.

## Stage 0A — minimal environment (pure CPU)

`conductor_cell_specs.md` first. Then `types.py`, `program.py` (six cells +
per-primitive direct reference functions), `render.py` (transparent + 2 variants,
explicit zero-based indexing, split-id bookkeeping), `resources.py` (manifests,
instance-scoped registries, action-controlled disclosure), `parser.py` (routing
schema + full workflow JSON, ≤3 steps, legal-pattern validation, extra-field
rejection), `contract.py` (artifact protocol, typed rejections), `tools.py`,
`prompts.py` (demos, all legal, executes-through-runtime test). Acceptance
battery: golden fixtures per primitive and cell; metamorphic tests; distractor
invariance; provenance-based no-leakage; routing-schema↔assignment bijection;
**strip test (no reference graph, no gold)**; scorer tested separately. The
10k-case reference-vs-tools agreement runs as a **recorded acceptance command**
(not pytest). Mock executor + fake pool for CPU tests.

## Stage 0B — runtime (first GPU)

`workers.py` (NF4 pool, lazy load, per-worker batched generation + caps + micro-
batch cap, parse/truncation telemetry), `executor.py` (wave batching by
worker×depth, typed threading, JSONL traces under `runs/<run_name>/traces/` with
manifest + stable ids, infra failures raise), `cache.py` (SQLite write-through,
three-part key), `runtime.py` (profile lifecycle). Offline executor smoke on the
real pool.

## Stage 0C — trainer integration

Registry + `reward_funcs` exports; `train.py` runtime/profile hooks; W&B
`qwen-grpo-conductor`. **Policy-dependent GRPO smoke** (~20 steps, launch profile,
one-step routing schema — sampled output determines reward). **Worst-case
benchmark** (forced-valid, cache-disabled, microbatch-capped; includes enumeration
throughput measured on the 100-example construction pass): gates <22 GB peak,
projected seed ≤ overnight, sane reward distribution. Infra-failure paths tested
mocked. CE0.

## Stage 1A — qualification (live NF4 backend; vLLM screening diagnostic-only)

**100 examples/cell construction screening** (tune operand sizes, list lengths,
distractors; benchmark payoff-surface enumeration cost here), then **fresh frozen
qualification samples** for passing cells (≈500/cell; fork/join 100–200 fresh
programs if paired CIs are decisive; expand only marginal cells). Payoff surfaces
by full enumeration (3/9/27). Gates (pre-registered in CE1):

| Gate | Threshold |
|---|---|
| artifact parse failure / truncation — per endpoint, **on-contract reference calls only** | < 2% each |
| best endpoint accuracy (atomic) | ≥ 75% |
| best-vs-runner-up payoff margin | lower CI bound ≥ 20 pts |
| two-step deployable-oracle success | ≥ 65% |
| deployable oracle vs best one-call whole-task baseline | ≥ +20 pts |
| corruption intervention (per edge) | ≥ +20 pts effect |
| counterfactual consistency (per edge) | execution follows the new sink |
| **effective routing stakes (gate)** | minimum conditional payoff loss when each best endpoint is replaced, others fixed |
| reference vs generic subtasks (gates Stage 3) | ≥ +10 pts |
| fork/join: leaf endpoints ≥80%; deployable oracle ≥60%; ≥+15 vs best two-call shortcut; per-branch corruption | ≥ −20 pts, paired lower CI |

Cold start (training backend, few-shot prompt): **≥64 groups within each stratum**
(atomic / two-step / fork-join): validity ≥80%; non-zero-variance ≥25%; groups
containing a 1.0 and a lower reward ≥10%. Includes the ~100-program visible slice.
CE1 + Stage-1→2 verdict: **Stage-2 harness-readiness only**.

## Deferred (named extension points)

Fork/join into training mixture (admission gates) · semantic/rule-induction
renderer (worker pilot first) · full shallow-router audit (gates Stage-3/4
claims) · answer-only-control and equalized-tool factorials · paired-policy
visibility experiment · distinct hard stratum · three-step linear · remaining
public types · subprocess/vLLM eval integration · test_render / test_compose.

## What each experiment will establish

| Experiment | Defensible conclusion |
|---|---|
| Stage 2, primary condition | GRPO learns fixed endpoint selection on a transparent typed environment with hidden payloads |
| Stage 2, fork/join | endpoint selection **within a fixed parallel DAG** (topology construction is tested only in Stage 4) |
| Stage 2, exclusive authorization | permission/endpoint routing |
| Stage 3 (only if reference > generic) | GRPO improves subtask instructions |
| Stage 4, private condition | static joint workflow formulation under partial observability |
| Paired visible experiment (deferred) | delegation vs self-solving; answer smuggling |

## `conductor_log.md`

Created at 0A; entries `CE0, CE1…`; pre-registration before GPU spend; backlog =
Stage-2+ entry gates. CE0 = 0C benchmark gates + throughput prediction (worst case
+ enumeration cost). CE1 = the Stage-1A gate table + named unknowns (effective
routing stakes; 3B cold start under opaque handles; 1.5B rule induction deferred).
Pointers in `experiment_log.md`, `stages.md`, `README.md`.

## Files touched

| file | change |
|---|---|
| `conductor_cell_specs.md` | new — frozen executable cell specifications (first deliverable) |
| `tasks/conductor/` (~11 modules incl. `calibrate.py`; small ones may merge) | new package per spec |
| `tasks/__init__.py` | registry + runtime-aware contract |
| `tasks/gsm8k.py`, `tasks/countdown.py` | export `reward_funcs` (no behavior change) |
| `train.py` | runtime/profile hooks |
| `profiles/` or in-package launch profile | named Stage-0C profile, checked in |
| `test_conductor_*.py` | CPU suites: adversarial parser, contract, acceptance battery incl. strip + bijection tests, mock executor |
| `conductor_log.md` | new log, CE0/CE1 pre-registered |
| `experiment_log.md`, `stages.md`, `README.md` | pointers only |

(`eval.py` untouched this tranche.)

## Verification

1. `uv run pytest` green throughout (existing 50 + conductor suites, CPU).
2. 0A acceptance battery (fixtures, metamorphic, distractor-invariance, provenance
   no-leakage, strip test, bijection test); 10k agreement command recorded; demos
   execute.
3. 0B offline executor smoke; 0C policy-dependent smoke + worst-case benchmark vs
   CE0 gates.
4. 1A payoff surfaces + gate table vs CE1 (deployable-oracle semantics; clustered
   CIs); Stage-1→2 verdict recorded before any Stage-2 work.

Effort: 0A ≈ 2–3 sessions (CPU; cell specs first); 0B+0C ≈ 1–2 sessions (GPU
~1–2 h); 1A GPU ≈ hours, analysis-bound. Commits at each milestone (cell specs;
0A env+tests; 0B runtime; 0C wiring+smokes+CE0; 1A CE1).
