# Conductor Stages 0–1, v4 (implementation-ready)

## Context

Implements Stages 0–1 of `conductor_task_proposal.md` on the `conductor` branch.
v4 = v3 (vertical slice, approved direction) + the specification pass required by
`conductor_plan_v3_critique.md`. Governing principle unchanged: *preserve extension
points for the full architecture; implement one end-to-end vertical slice before
adding another abstraction.* This version locks the contracts; it is the build spec.

## v0 scope

- **Integer-only public outputs.** Private resources: keyed integer records and
  integer lists (a record may hold several named integers, e.g. `Q41: a=83719,
  b=43, c=1`). Fractions internal only when they resolve to integers. Extension
  point: `types.py` (noncanonical integer wire forms like `"0012"` rejected).
- **Six cells**: atomic Lookup, atomic Math, atomic Code, Lookup→Math, Math→Code
  (computed index), fork/join Lookup+Code→Math (diagnostic). Operator set (integer-
  safe): keyed retrieval, affine/ratio/modular numeric, indexed selection,
  stable-dedup, `count_greater_than` (integer predicate — replaces the string-typed
  suffix-count). Hidden-Math cells put operands in a private numeric record with the
  formula public — tool-demand (large operands, modular forms) is tuned *within*
  cells during screening; no separate tool-demanding stratum in v0.
- **Each cell ships an executable specification before coding**: parameter ranges,
  rejection rules, one hand-calculated example, intervention-generation rules
  (replacements constructed to provably change the reference sink), and its
  one-call-shortcut baseline definition.
- **One transparent renderer, two manually authored cosmetic variations.**
- **Model-plus-tool endpoints** (framing locked): each worker endpoint = frozen
  1.5B model + its endpoint-specific tool + artifact grammar. This studies
  endpoint selection, not pure LLM specialization; equalized-tool factorials are a
  deferred extension.

## Locked contracts

### 1. Per-stage action space (what the policy may vary)

| Stage | Learnable | Fixed (supplied by harness) |
|---|---|---|
| 0C smoke | worker_id (one-step) | topology, subtask, resources, access |
| 2 routing-only | **worker_id only** | reference topology, reference subtasks, resource handles, predecessor access, number of calls |
| 3 decomposition-only | subtask wording | oracle workers, topology, resources, access |
| 4 joint | steps, subtasks, worker_ids, resources, access | budgets/limits below |

Stage-2 conclusion, worded precisely: *GRPO learns fixed endpoint selection on a
transparent typed environment with hidden payloads.*

### 2. Execution rules and resource limits (task-independent, enforced by executor)

- Handles must belong to the current instance's public manifest; **registries are
  instance-scoped** (a handle from another example never resolves).
- ≤1 private resource per step (v0); no duplicate handles; fixed caps on total
  calls and total resource requests.
- Downstream aggregation uses predecessor values, never re-requested upstream
  resources.
- **Legal v0 access patterns** (rejected otherwise): `[none]` atomic;
  `[none, all]` two-step chain; `[none, none, all]` fork/join. Patterns like
  `[none, all, none]` are invalid — this keeps wave-batching by depth unambiguous.
- Disclosure is **action-controlled only**: the executor reveals exactly what the
  sampled action requests; it never consults the reference program.

### 3. Worker artifact protocol (single protocol, decided)

- Every tool-required endpoint emits **exactly one** `<artifact>…</artifact>`
  (reasoning allowed outside; last-and-only complete tag; duplicate/mixed/
  unexpected terminal tags invalid). The **selected endpoint determines the
  artifact grammar and tool**:
  - Math: arithmetic expression → exact calculator.
  - Code: restricted sequence expression → whitelist interpreter.
  - Lookup: retrieval expression, e.g. `lookup(Q31, "Cedar", "units")` → host
    executes against the authorized payload (symmetrical with the others).
- Host executes the artifact and constructs
  `WorkerResult(status, value: Integer, artifact_valid, tool_executed)`. **The
  executed tool result is authoritative**; no free-text answer can override it.
- `<value>` responses are reserved for an explicit **answer-only control**
  condition (deferred factorial), not the main protocol.

### 4. Reward table (pre-registered; boundaries may not drift in implementation)

| Outcome | Reward |
|---|---:|
| Malformed workflow / schema violation | 0.0 |
| Structurally valid but: unknown resource, denied access, illegal access pattern, worker parse failure, invalid artifact, tool rejection, or wrong final answer | 0.5 |
| Correct executed terminal result | 1.0 |
| OOM, model failure, cache corruption, trace I/O failure | **abort update** |

### 5. Reference-free execution

- The execution contract is **globally integer-valued** in v0 — no per-node
  expected-type lookup. The reference program is used only for dataset generation,
  final-answer verification, and reference workflows/diagnostics.
- **Strip test (acceptance battery)**: delete all reference-node metadata after
  generation and confirm an arbitrary sampled workflow executes identically from
  only {public prompt + manifest, instance registry, sampled action, endpoint
  definitions, final answer}.

### 6. Information conditions and baselines

- Conditions: *primary causal* (payloads hidden from Conductor; every candidate
  worker for a node receives the same local payload); *hard-routing control*
  (exclusive authorization); *visible* (payloads exposed).
- Visible mode is a **paired observation condition over the same latent programs**,
  not a flag to casually evaluate across: a private-trained policy on visible
  prompts is an OOD transfer test. The paired-policy visibility experiment is
  deferred; a **small visible qualification slice ships in Stage 1** so the direct
  and echo baselines are informative.
- **Three separated direct baselines** (recorded per cell):
  1. public-prompt-only direct model — leakage check;
  2. local capability baseline — 3B given the same single-node payload and
     instruction as a worker;
  3. **best one-call whole-task baseline** — one endpoint given the union of
     relevant payloads attempts the composite task. Only this one speaks to
     hierarchy's value.
  Plus echo worker and no-op worker rows (informative on the visible slice), and
  answer-in-subtask telemetry always on.

### 7. Runtime profile and persistence

- **Versioned runtime profile** (dataclass, serialized into every trace manifest
  and W&B config): worker model ids + revisions, tools + versions, visibility
  policy, token caps, resource rules, cell mixture, cache path, batch shape,
  `workflow_max_steps`. `build_runtime(profile)` / `close()`.
- **SQLite write-through cache from Stage 0B** (Stage 1A is a thousands-of-calls
  workload; resumability is required, not optional), keyed by the complete rendered
  request hash. `calibrate.py` is **resumable**: per-example outcomes, payoff
  surfaces, and gate reports as write-through artifacts.
- Worst-case throughput benchmark includes a **per-worker inference microbatch
  cap** (a first wave of 2 groups × 8 rollouts × 2 fork leaves = 32 calls can all
  route to one worker).

### 8. Payoff surfaces by enumeration

For the six cells, enumerate the **complete worker-assignment payoff surface**
(atomic: 3; two-step: 9; fork/join: 27 assignments) on qualification samples —
exact oracle, best-fixed, random, shortcut, and interaction effects, rather than
node-margin estimates.

## Stage 0A — minimal environment (pure CPU)

`types.py`, `program.py` (six cells + per-primitive **direct reference functions**
— no second DAG interpreter), `render.py` (transparent + 2 variants; explicit
zero-based indexing; split-id bookkeeping), `resources.py` (manifests,
instance-scoped registries, action-controlled disclosure), `parser.py` (Conductor
JSON, ≤3 steps, legal-pattern validation), `contract.py` (artifact protocol),
`tools.py` (three endpoint tools), `prompts.py` (demos, all legal, with the
executes-through-runtime test). Acceptance battery: golden fixtures (ordinary +
boundary) per primitive and cell; metamorphic tests; distractor invariance;
**provenance-based no-leakage** (renderers structurally cannot read private
payloads or derived values); ~10k-case reference-function vs runtime-tool
agreement per cell; **strip test**. Mock executor + fake pool for CPU tests.

## Stage 0B — runtime (first GPU)

`workers.py` (NF4 pool, lazy load, per-worker batched generation + caps,
parse/truncation telemetry), `executor.py` (wave batching by worker×depth, typed
threading, JSONL traces under `runs/<run_name>/traces/` with manifest + stable
ids, **infra failures raise**), `cache.py` (SQLite write-through), `runtime.py`
(profile lifecycle). Offline executor smoke: hand-written plans end-to-end on the
real pool.

## Stage 0C — trainer integration

Registry + `reward_funcs` exports (gsm8k/countdown unchanged in behavior);
`train.py` runtime hooks + profile plumbing; W&B `qwen-grpo-conductor`.
**Policy-dependent GRPO smoke** (~20 steps, 3B QLoRA, one-step workflows, sampled
output determines reward). **Worst-case benchmark** (forced-valid, cache-disabled,
microbatch-capped): gates <22 GB peak, projected seed ≤ overnight, reward
distribution sane. Infra-failure paths tested **mocked** (no live-CUDA OOM). CE0.

## Stage 1A — qualification (live NF4 backend; vLLM screening diagnostic-only)

Two-phase sampling: **100 examples/cell for construction screening** (tune operand
sizes, list lengths, distractors), then **fresh frozen qualification samples** for
passing cells (≈500/cell). Gates (pre-registered in CE1):

| Gate | Threshold |
|---|---|
| artifact parse failure / truncation (per worker) | < 2% each |
| best endpoint accuracy (atomic cells) | ≥ 75% |
| best-vs-runner-up payoff margin | lower CI bound ≥ 20 pts |
| two-step oracle success | ≥ 65% |
| oracle vs best one-call whole-task baseline | ≥ +20 pts |
| dependency-preserving vs each intervention | ≥ +20 pts |
| reference vs generic subtasks (gates Stage 3, not 2) | ≥ +10 pts |
| fork/join: each leaf endpoint ≥80%; oracle ≥60%; ≥+15 vs best two-call shortcut; corrupting either branch | ≥ −20 pts effect |

Cold start (training backend, few-shot prompt): per stratum (atomic / two-step /
fork-join) with **≥64 groups within each reported stratum** — validity ≥80%;
non-zero-variance groups ≥25%; groups containing a 1.0 and a lower reward ≥10%;
plus effective-routing-stakes measurement. Includes the small **visible
qualification slice** for the direct/echo baselines. CE1 + Stage-1→2 verdict:
qualifies **Stage-2 harness-readiness** only (Stage-3/4 semantic claims await the
deferred semantic renderer + shortcut audit).

## Deferred (named extension points)

Fork/join into training mixture (admission gates) · semantic/rule-induction
renderer (worker pilot first) · full shallow-router audit (gates Stage-3/4
claims) · answer-only-control and equalized-tool factorials · paired-policy
visibility experiment · distinct hard/tool-demanding stratum · three-step linear ·
remaining public types · subprocess/vLLM eval integration · test_render /
test_compose splits.

## What each experiment will establish

| Experiment | Defensible conclusion |
|---|---|
| Stage 2, primary condition | GRPO learns fixed endpoint selection on a transparent typed environment with hidden payloads |
| Stage 2, exclusive authorization | GRPO learns permission/endpoint routing |
| Stage 3 (only if reference > generic subtasks) | GRPO improves subtask instructions |
| Stage 4, private condition | joint routing + workflow formulation under partial observability |
| Paired visible experiment (deferred) | whether the policy delegates when it could self-solve; answer smuggling |
| Fork/join | constructing/executing a fixed parallel DAG (not dynamic adaptation) |

## `conductor_log.md`

Created at 0A; conventions from `experiment_log.md`; entries `CE0, CE1…` with
pre-registration before GPU spend; backlog holds Stage-2+ entry gates. CE0 =
0C benchmark gates + throughput prediction (incl. worst case). CE1 = the Stage-1A
gate table above + named unknowns (effective routing stakes; 3B cold start under
opaque handles; 1.5B rule induction as the deferred question). Pointer lines in
`experiment_log.md`, `stages.md`, `README.md`.

## Files touched

| file | change |
|---|---|
| `tasks/conductor/` (~11 modules; small ones may merge) | new package per spec |
| `tasks/__init__.py` | registry + runtime-aware contract |
| `tasks/gsm8k.py`, `tasks/countdown.py` | export `reward_funcs` (no behavior change) |
| `train.py` | runtime/profile hooks |
| `test_conductor_*.py` | CPU suites: adversarial parser, contract, acceptance battery incl. strip test, mock executor |
| `conductor_log.md` | new log, CE0/CE1 pre-registered |
| `experiment_log.md`, `stages.md`, `README.md` | pointers only |

(`eval.py` untouched this tranche.)

## Verification

1. `uv run pytest` green throughout (existing 50 + conductor suites, CPU).
2. 0A acceptance battery incl. strip test and provenance no-leakage; demos execute.
3. 0B offline executor smoke; 0C policy-dependent smoke + worst-case benchmark vs
   CE0 gates.
4. 1A payoff surfaces + gate table vs CE1; Stage-1→2 verdict recorded before any
   Stage-2 work.

Effort: 0A ≈ 2–3 sessions (CPU); 0B+0C ≈ 1–2 sessions (GPU ~1–2 h); 1A GPU ≈ hours,
analysis-bound. Commits at each milestone (0A env+tests; 0B runtime; 0C
wiring+smokes+CE0; 1A CE1).
