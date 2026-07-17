# Conductor Stages 0–1: harness + calibration (revised after external review)

## Context

Implements Stages 0–1 of `conductor_task_proposal.md` on the `conductor` branch,
revised per two review rounds: `conductor_plan_critique.md` (runtime/cache/eval/demo
fixes, causal necessity, backend discipline) and
`conductor_plan_data_proposal_alternative.md` (anti-shortcut typed-workflow data
design). Agreed synthesis: **adopt the alternative's architecture wholesale, populate
it incrementally** — the factored semantics/rendering skeleton from day 1, minimal
cells first, expansions gated. Exit of this tranche: Stage-1→2 gate verdict + cold
start measurement, recorded in a new `conductor_log.md`.

## Architecture: `tasks/conductor/` package

Module roles (small ones may merge at implementation time; roles are the contract):

```
types.py      exact typed values: Integer|Rational|Boolean|Text|Key|IntegerList;
              canonical per-type comparison (NO float normalization; "0012" ≠ 12)
program.py    typed reference-program DAGs; operator library (relational/numeric/
              sequence per the alternative's table); INDEPENDENT reference evaluator
              (second implementation of every primitive, used in tests + acceptance)
render.py     renderer layer, factored from semantics: rendering tiers
              (transparent → semantic → counterfactual), domains, clause orders,
              dependency-language styles; counterbalancing rules; split bookkeeping
resources.py  opaque handles (neutral names, no type leakage), manifests, payload
              authorization (worker sees only authorized payloads + canonical
              predecessor outputs — never raw reasoning)
parser.py     conductor <workflow> parsing/validation, ≤3 steps supported from the
              outset (mixture admission of 3-step is separately gated)
contract.py   common outer worker result contract + layered validity (outer /
              artifact / tool / semantic); flat-tagged vs JSON variant piloted
tools.py      calculator, sequence interpreter, relational store (worker-internal;
              artifacts are telemetry, never outer-parse gates)
workers.py    frozen 1.5B pool (Instruct/Math/Coder), NF4, lazy load, per-worker
              batched generation + token caps, telemetry (parse/truncation)
cache.py      SQLite exact cache keyed on hash of the COMPLETE rendered worker
              request (problem, subtask, authorized deps, model+tokenizer revision,
              chat template, backend+quant+decoding+stop, truncation policy);
              hit-rate is telemetry, never assumed
executor.py   wave-batched DAG execution with typed value threading; JSONL traces
              under runs/<run_name>/traces/ with manifest + stable ids;
              INFRA FAILURES ABORT the update (OOM/cache corruption/trace-write
              errors raise — they must never become a 0.0 policy reward)
runtime.py    build_runtime(config) lifecycle: wires workers+cache+traces+caps,
              exposes reward_funcs/execute_and_score, close() releases models
prompts.py    conductor system prompt + few-shot demos — every demo must EXECUTE
              through the real parser+runtime (unit test), all ≤ max steps
calibrate.py  python -m tasks.conductor.calibrate: worker pilot, capability matrix,
              paraphrase/cluster stats, interface controls, counterfactual battery,
              oracle ceilings, decomposition headroom, CIs, gate report
audit.py      shortcut audit: CPU baselines (keyword/regex, TF-IDF, nearest-
              template, cheap-feature router, template-copy decomposer), each
              judged by EXECUTING its workflows; gate report
```

### Design decisions (locked)

1. **Semantics before language.** Every instance is a typed reference program
   evaluated by the independent evaluator before rendering. "Reference program",
   not gold workflow: after calibration, store the empirical payoff vector per
   worker; routing quality is measured as achieved-vs-max payoff, not
   match-to-a-presumed-gold.
2. **Common outer contract + layered validity.** Specialist tools/artifacts stay
   internal; whether an answer parses never depends on a private grammar.
3. **Opaque private resources are the primary environment** (causal necessity by
   construction: the conductor cannot answer-smuggle; single workers cannot solve
   alone). `test_soft` keeps a visible-payload slice where direct baselines bite.
4. **Renderer tiers, populated incrementally**: v0 = transparent only; semantic
   (rule-induction) gated on the worker pilot; counterfactual gated on the shortcut
   audit. Matched pairs stay within one split; five renderings of a program = one
   statistical cluster.
5. **Splits**: construction / qualification (one-shot gate, retired if a redesign
   follows) / train / dev / test_render / test_compose / test_soft. Selection is
   cell-level (operator × renderer), never instance-level.
6. **Backend discipline** (E3/E7 doctrine): vLLM for screening only; every decisive
   qualification set re-run on the live NF4 transformers backend; gates ≥98%
   per-example reward agreement, ≤2pt cell shift. Cold-start gate runs on the
   training backend. Subprocess boundary between vLLM plan generation and worker
   execution (no in-process vLLM teardown).
7. **Traces are the source of truth, W&B for learning dynamics** (as amended in the
   proposal).

## Shared-infra changes

- `tasks/__init__.py` contract: tasks may export `build_runtime(config)` (conductor)
  or plain module-level functions (gsm8k/countdown unchanged); registry adapts.
  All tasks export `reward_funcs` (or runtime equivalent).
- `train.py`: thin — task runtime construction/close, `workflow_max_steps` (default 3
  supported; mixture caps live in data config), existing W&B project derivation.
- `eval.py`: two-phase for execution-backed tasks via subprocess boundary; phase-2
  returns execution-result objects (parse_valid, executed answer, correctness, trace
  id, calls, latency, failure kind) feeding the existing per-problem JSONs.
- Tests: `test_conductor_{types,program,render,parser,contract,tools,executor}.py` —
  CPU-only via mock pool; adversarial parser cases; demos-execute test.

## v0 population (ugly-and-small applied to cells, not architecture)

Transparent renderings only; 2 domains; core operator table; compositions =
causal LOOKUP→MATH, MATH→CODE (computed index), fork/join (two leaves → aggregate);
plus ONE matched rule-induction pair authored as the pilot probe. Sizes per the
alternative's compute table (CPU stress 10k/schema; ~64 hand-audited fixtures;
train pool ~2,048 / dev 300 / test 1,000 when frozen — freezing happens only after
Stage-1 gates).

## Stage 0 — harness

1. `types.py` + `program.py` + independent evaluator + property/acceptance tests:
   10k-case agreement per operator/composition; hand-checked golden fixtures
   (ordinary + boundary values); metamorphic tests (e.g. rotate-n then rotate-back);
   distractor-invariance; no intermediate/final answer appears in the public prompt.
2. `render.py` v0 (transparent, 2 domains) + `resources.py`; manual review of every
   template × rendering before marking construction-complete; explicit indexing
   language everywhere ("zero-based index 2").
3. `parser.py`, `contract.py`, `tools.py` (+reference impls) + test suites; demos in
   `prompts.py` with the executes-through-runtime test.
4. `workers.py`, `cache.py`, `runtime.py`, `executor.py`; CPU tests via mock pool;
   one real-pool GPU load check.
5. Wiring (`train.py`/`eval.py`) + **two smokes** replacing the old fixed-plan idea:
   (a) non-training executor smoke (run plans through the runtime offline);
   (b) one-step-workflow GRPO smoke where the sampled conductor output genuinely
   determines reward (~20 steps, 3B, `qwen-grpo-conductor`).
6. **Feasibility benchmark** with pre-registered gates: real GRPO batch → parse all →
   wave-batch by worker/depth → peak memory <22 GB; projected seed ≤ overnight;
   sane 0/0.5/1 distribution; infra-failure paths verified (induced cache/trace
   faults abort). Include the **forced-valid, cache-disabled worst case** so cheap
   malformed cold-start workflows can't flatter the projection.

## Stage 1 — calibration + qualification (inference-only GPU; authoring-bound)

1. **Worker pilot** (100 programs/capability × 3 workers × 3 surface forms, live
   backend). Primary pre-registered question: **can 1.5B workers do rule induction?**
   Secondary: flat-tagged vs JSON outer contract parse reliability; Math-1.5B
   truncation under terse-output prompting.
2. **Capability matrix**: 500/capability (100-subset rendered five ways, analyzed as
   clusters), on the live backend (vLLM screening allowed first); worker
   parse-fail/truncation <2% gates.
3. **Interface controls**: one general model behind all three tool interfaces vs
   specialists behind the common interface — attributes "specialization" to LLM vs
   tool vs parser; ≥10pt intended-margin must survive the common-interface control.
4. **Causal-necessity battery** per dependency edge (remove / replace-with-valid /
   mutate / skip-upstream / echo-worker / direct-3B): correct dependency beats
   counterfactuals by ≥20pt; retention decided per cell.
5. **Oracle ceilings + decomposition headroom**: oracle ≥15–20pt over best fixed
   worker; reference subtasks ≥~10pt over generic "solve the relevant part" (else
   Stage 3 lacks headroom and is descoped consciously).
6. **Shortcut audit** (`audit.py`): pre-registered gates — best shallow router
   ≥10–15pt below oracle on qualification; nuisance-only features ≤ chance+5. If
   TF-IDF lands within 5pt of oracle, the distribution is labeled a routing-
   mechanics harness, not semantic-orchestration evidence.
7. **Cold-start gate** on the training backend (32×8): ≥80% valid; ≥10% of groups
   contain a 1.0 and a lower outcome; ≥25% non-zero-variance; plus measure
   **effective routing stakes** (payoff delta between chosen and best worker per
   decision — the new pre-registered unknown: soft margins may leave routing
   under-incentivized).
8. **Three-node strata** (linear + fork/join, 100–200 each) calibrated now; admission
   to the Stage-2 mixture only per the alternative's criteria (oracle ≥~60%, ≥15pt
   over best two-call shortcut, dependency interventions bite, reward diversity in
   cold-start samples).
9. **CE1 write-up + Stage-1→2 verdict**; freeze train/dev/test pools only on a pass.

## `conductor_log.md`

Same conventions as `experiment_log.md`, entries `CE0, CE1…`; cross-links to the
proposal, critiques, and main log. Seeded with pre-registrations: **CE0** (Stage-0
benchmark gates + throughput prediction incl. worst case) and **CE1** (all Stage-1
gates above, plus the three named unknowns: 1.5B rule induction, effective routing
stakes under soft margins, 3B cold-start on the opaque-handle regime). Backlog holds
the Stage-2–4 entry gates. Pointer entries in `experiment_log.md`, `stages.md`,
`README.md`.

## Files touched

| file | change |
|---|---|
| `tasks/conductor/` (~14 modules per above) | new package |
| `tasks/__init__.py` | registry + runtime-aware contract note |
| `tasks/gsm8k.py`, `tasks/countdown.py` | export `reward_funcs` (no behavior change) |
| `train.py` | runtime lifecycle hooks, `workflow_max_steps` |
| `eval.py` | two-phase execution-backed mode (subprocess boundary) |
| `test_conductor_*.py` | CPU suites incl. adversarial + acceptance batteries |
| `conductor_log.md` | new log, CE0/CE1 pre-registered |
| `experiment_log.md`, `stages.md`, `README.md` | pointers only |

## Verification

1. `uv run pytest` green throughout (existing 50 + conductor suites, CPU).
2. Acceptance battery passes: 10k/operator evaluator agreement, fixtures, metamorphic,
   distractor-invariance, no-leakage; demos execute through the runtime.
3. Smokes (a) and (b) pass; W&B `qwen-grpo-conductor` populates; traces re-scorable.
4. CE0 benchmark vs pre-registered gates; CE1 calibration/audit/cold-start vs gates;
   Stage-1→2 verdict recorded before any Stage-2 work.

Effort, honestly revised: Stage 0 ≈ 4–6 working sessions (GPU ~1–2 h);
Stage 1 is authoring/audit-bound (GPU: hours of batched inference). Commits per repo
style at each milestone (types/program+tests; render+resources; runtime/executor;
wiring+smokes; CE0; CE1).
