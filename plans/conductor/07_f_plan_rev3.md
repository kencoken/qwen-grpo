# Conductor Stages 0–1, v3: vertical slice first

## Context

Implements Stages 0–1 of `conductor_task_proposal.md` on the `conductor` branch.
Supersedes v2 of this plan per `conductor_plan_v2_critique.md`: the conceptual design
(typed reference programs, causal isolation, common executor-level results, runtime
lifecycle, live-backend qualification) is kept, but the implementation is staged as
**one end-to-end vertical slice with named extension points** — not fourteen modules
before the first routing signal. Governing principle: *preserve extension points for
the full architecture; implement only one vertical slice before adding another
abstraction.* (The engineering form of the E10/C1 lesson.)

## v0 scope (the vertical slice)

- **Integer-only public outputs.** Private resources: keyed integer records +
  integer lists. Fractions internal only when they resolve to integers. No
  Boolean/Rational/Text/IntegerList public types yet (extension point: `types.py`).
- **Six cells**: atomic Lookup, atomic Math, atomic Code, Lookup→Math, Math→Code
  (computed index), and fork/join Lookup+Code→Math as the one diagnostic topology.
- **One transparent renderer, two manually authored cosmetic variations.** Semantic
  (rule-induction) and counterfactual renderers are deferred behind gates.
- **Tagged worker protocol, decided now (no pilot)**: workers emit
  `<value>…</value>` or `<artifact>…</artifact>` (last complete tag wins; reasoning
  allowed outside tags). The host wrapper parses/executes and constructs the
  structured `WorkerResult(status, value, artifact_valid, tool_executed)`. The
  **executed tool result is authoritative** — a claimed value never overrides it.
  Expected type comes from the workflow node. The 3B Conductor keeps JSON workflows
  (its format learning is part of the experiment).
- **Three-condition information design** (visibility ≠ authorization):
  1. *Primary causal condition*: payloads hidden from the Conductor; **every
     candidate worker for a node receives the same local payload** (requested
     resource, assigned subtask, authorized predecessor values) → tests empirical
     model/tool selection without self-solving or tautological routing.
  2. *Hard-routing control*: exclusive authorization → tests permission routing.
  3. *Paired visible mode*: same programs + rendering with payloads visible —
     an **execution flag, not a separate distribution** (deferred, cheap by design).
  Workflow actions carry an explicit `"resources": [...]` field; the executor
  discloses **only what the sampled action requests** — never by consulting the
  reference DAG.
- **Tool-demanding stratum** (small, visible-safe): big-integer/modular arithmetic,
  50–100-element sequence transforms, distractor-heavy computed-key lookups — the
  counterweight to soft routing margins: genuine capability gaps for honest reasons.

## Stage 0A — minimal environment (pure CPU)

- `types.py`: Integer (+ internal Rational), Key for resource addressing; canonical
  wire forms (noncanonical integer forms like "0012" rejected).
- `program.py`: reference-program DAGs for the six cells; operator set only as
  needed (keyed retrieval, affine/ratio/modular numeric, indexed selection,
  stable-dedup, suffix-count); **per-primitive direct reference functions**
  (hand-written, one-liner style) — no second DAG interpreter.
- `render.py`: transparent renderer + 2 cosmetic variants; explicit zero-based
  indexing language; split bookkeeping (construction/qualification/train/dev held
  as ids from day 1 — extension point for test_render/test_compose).
- `resources.py`: opaque handles (neutral names), manifests, action-controlled
  disclosure.
- **No-leakage invariant by provenance**: renderers structurally cannot read
  private payloads or derived node values (enforced by interface, tested), not by
  substring checks.
- Acceptance tests: hand-checked golden fixtures (ordinary + boundary) per
  primitive and per cell; metamorphic tests; distractor invariance; reference
  functions vs runtime tools agreement on ~10k generated cases per cell.
- `parser.py` (Conductor JSON workflows, ≤3 steps, `resources` field) +
  adversarial tests; `contract.py` (tagged worker protocol) + tests;
  `prompts.py` demos with the executes-through-runtime test (all demos legal).
- Mock executor: full DAG execution + traces against a fake worker pool (CPU).

## Stage 0B — runtime (first GPU)

- `workers.py`: frozen 1.5B pool (Instruct/Math/Coder), NF4, lazy load, per-worker
  batched generation + token caps, parse/truncation telemetry.
- `executor.py`: wave batching by worker×depth; typed value threading; JSONL traces
  under `runs/<run_name>/traces/` with manifest + stable ids; **infra failures
  raise** (never become policy reward).
- **In-memory cache** with the full-request key semantics (complete rendered
  request hash) so SQLite is a later drop-in, not a redesign.
- `runtime.py`: `build_runtime(config)` / `close()`; offline executor smoke (run
  hand-written plans end-to-end on the real pool).

## Stage 0C — trainer integration

- `tasks/__init__.py` registry + runtime-aware contract; `reward_funcs` export on
  gsm8k/countdown (no behavior change); `train.py` runtime hooks +
  `workflow_max_steps`; W&B project auto-derivation (`qwen-grpo-conductor`).
- **Policy-dependent GRPO smoke**: ~20 steps, 3B QLoRA, one-step workflows where
  the sampled Conductor output genuinely determines reward.
- **Throughput benchmark**: forced-valid, cache-disabled worst case; gates <22 GB
  peak, projected seed ≤ overnight, sane 0/0.5/1 distribution.
- Infrastructure-failure tests **mocked** (induced cache/trace faults in tests —
  no deliberate live-CUDA OOM).
- CE0 entry: benchmark vs pre-registered gates.

## Stage 1A — minimum qualification (live backend; inference-only GPU)

All on the live NF4 transformers backend (vLLM screening optional and *diagnostic
only* — the bar is that screening never changes a cell-level conclusion):

1. **100 examples per cell**, expanding to 500 only for passing cells.
2. **Capability matrix including the direct-3B-Conductor row per cell**, plus echo
   worker, no-op worker, answer-in-subtask telemetry. If direct-Conductor or echo
   approaches oracle on a cell, that cell does not establish orchestration.
3. **Dependency interventions** per edge: remove / replace-with-valid / mutate /
   skip-upstream; correct dependency ≥20pt over counterfactuals; cell-level
   retention only.
4. **Generic-subtask and random/fixed-routing controls** (the decomposition- and
   routing-headroom checks).
5. **Stratified cold-start gate, ≥64 groups** (atomic / two-step / fork-join
   reported separately): ≥80% valid; groups containing a 1.0 and a lower outcome;
   non-zero-variance fraction; plus **effective routing stakes** (payoff delta
   between chosen and best endpoint per decision).
6. CE1 entry + **Stage-1→2 verdict**. Gate meaning per the two-decision split:
   this qualifies the environment as **Stage-2 harness-ready**. It does *not*
   license Stage-3/4 semantic-orchestration claims — those await the deferred
   semantic/counterfactual renderers + full shortcut audit.

## Deferred (named extension points, in likely order)

Fork/join into training mixture (per admission gates) · semantic/rule-induction
renderer (gated on a worker pilot for 1.5B rule induction) · full shallow-router
audit (gates Stage-3/4 claims) · specialist-vs-general interface factorial ·
paired visible mode (execution flag — cheap) · tool-demanding stratum expansion ·
three-step linear · remaining public types · SQLite cache · subprocess/vLLM eval
integration · test_render/test_compose splits.

## What each experiment will establish (naming discipline, carried from review)

| Experiment | Defensible conclusion |
|---|---|
| Stage 2, primary causal condition | GRPO learns an empirical worker/tool payoff mapping from terminal reward |
| Stage 2, exclusive authorization | GRPO learns permission/endpoint routing |
| Stage 3 (only if reference beats generic subtasks) | GRPO improves subtask instructions |
| Stage 4, private condition | joint routing + workflow formulation under partial observability |
| Paired visible mode | whether the policy delegates when it could self-solve; answer smuggling |
| Fork/join | constructing/executing a fixed parallel DAG (not dynamic adaptation) |

## `conductor_log.md`

Created at Stage 0A with conventions from `experiment_log.md` (entries `CE0, CE1…`,
pre-registration before GPU spend, backlog with Stage-2+ entry gates). CE0/CE1
seeded as above with the three named unknowns (1.5B rule induction — deferred
question, effective routing stakes, 3B cold start under opaque handles). Pointer
lines in `experiment_log.md`, `stages.md`, `README.md`.

## Files touched

| file | change |
|---|---|
| `tasks/conductor/` (~10 modules, roles above; small ones may merge) | new package |
| `tasks/__init__.py` | registry + runtime-aware contract |
| `tasks/gsm8k.py`, `tasks/countdown.py` | export `reward_funcs` |
| `train.py` | runtime hooks, `workflow_max_steps` |
| `test_conductor_*.py` | CPU suites: adversarial parser, contract, acceptance battery, mock-executor |
| `conductor_log.md` | new log, CE0/CE1 pre-registered |
| `experiment_log.md`, `stages.md`, `README.md` | pointers only |

(`eval.py` untouched in this tranche — conductor evaluation runs through the
runtime's offline scoring; vLLM two-phase integration is a deferred extension.)

## Verification

1. `uv run pytest` green throughout (existing 50 + conductor suites, all CPU).
2. Stage-0A acceptance battery passes (fixtures, metamorphic, distractor-invariance,
   provenance no-leakage, 10k-case reference-vs-tools agreement, demos execute).
3. Stage-0B offline executor smoke on the real pool; Stage-0C policy-dependent GRPO
   smoke + worst-case benchmark vs CE0 gates.
4. Stage-1A matrices/interventions/controls/cold-start vs CE1 gates; Stage-1→2
   verdict recorded before any Stage-2 work.

Effort: 0A ≈ 2–3 sessions (CPU); 0B+0C ≈ 1–2 sessions (GPU ~1–2 h); 1A GPU ≈ hours
(batched inference), analysis-bound. Commits per repo style at each milestone
(0A env+tests; 0B runtime; 0C wiring+smokes+CE0; 1A CE1).
