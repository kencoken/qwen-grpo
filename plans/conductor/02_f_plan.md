# Conductor Stages 0–1: harness + capability calibration

## Context

`conductor_task_proposal.md` (+ its post-review amendments) defines the toy-Conductor
program. This plan implements **Stage 0 (harness)** and **Stage 1 (capability
calibration)** on the `conductor` branch — the tranche we committed to — while
structuring the code so Stages 2–7 (routing-only, decomposition-only, joint, ablations,
7B, external validity) slot in without rework. A new experiment log for the conductor
work is created alongside. Nothing trains for real in this tranche; its exit is the
Stage-1→2 gate verdict plus the cold-start gate measurement.

## Architecture: `tasks/conductor/` package

Follows the tasks/ growth rule (package with contract re-exports; callers can't tell).
Every component below is used by later stages, not just 0–1:

```
tasks/conductor/
├── __init__.py    # contract re-exports: load_train/load_eval/reward_funcs/verify(canonical=None)
├── generator.py   # typed micro-workflow environment (the new "verifier project")
├── parser.py      # <workflow> JSON parsing + validation
├── tools.py       # calculator / restricted executor / lookup checking (CPU, pure)
├── workers.py     # frozen 1.5B pool: lazy NF4 load, batched generate, exact-key cache, telemetry
├── executor.py    # wave-batched orchestration: plans → worker calls → answers + JSONL traces
└── prompts.py     # conductor system prompt + 4 few-shot workflow demos; worker prompts
```

### Key design decisions (locked here, consistent with proposal + amendments)

1. **Single-turn workers with typed output contracts; tools evaluate worker output.**
   No interactive tool-calling loops (1.5B function-calling is fragile and multiplies
   cost). The Math worker emits an arithmetic expression → `tools.calculator` evaluates
   it exactly (Fraction, reusing the countdown AST-eval pattern); the Coder worker
   emits a restricted expression/short transform → `tools.executor` applies it (no
   sandbox — a typed whitelist interpreter like countdown's); the Lookup worker answers
   from the in-context passage (its "tool" is extraction + normalization). This keeps
   workers batchable single generations and *enforces* heterogeneity via output
   interface, per the "heterogeneity by construction" framing.
2. **Reward is one composite function returning 0 / 0.5 / 1.0** (paper-matching), not
   the shared format+correctness pair. Requires a small contract change (below).
3. **Traces are the source of truth, W&B for learning dynamics.** `executor` writes
   complete workflow traces (JSONL: plan, subtasks, worker ids, contexts, raw
   outputs, tool results, final answer, reward, cache hits, truncations) to
   `data/conductor/traces/`; all post-experiment analysis, claims, and debugging run
   off them, and anything not logged live is recoverable from them. W&B metrics are
   the live window: monitoring runs, catching failure modes mid-flight, and watching
   learning dynamics unfold; log whatever is useful for that (via existing
   `log_metric`). Complex derived diagnostics (e.g. confusion matrices,
   counterfactual replay) are offline analysis over traces. Claims come from traces
   + proper statistics.
4. **Exact-key worker cache** (reviewer spec): SHA of {model id+revision, quant config,
   worker system prompt, subtask, dependency context, decoding params, tool version} →
   output, persisted as JSONL under `data/conductor/cache/`; hit-rate is telemetry, not
   an assumed saving.
5. **Generator carries the gold spine for all later stages**: each instance stores gold
   operation graph, gold subtask wordings (+5 deterministic paraphrase variants), gold
   worker family, intermediate values, final answer. That is what Stage 2 (cached
   outcomes vs gold subtasks), Stage 3 (oracle workers/topology), and Stage 5
   (counterfactual replay) consume. Rewards use only format + terminal correctness.
6. **Three template-level splits** baked into the generator: `calibration` / `dev` /
   `test`, holding out both surface templates and some operation compositions. v1
   mixture: 40% atomic / 60% two-step (three-step deferred to Stage 5).

## Shared-infra changes (small, deliberate)

- **`tasks/__init__.py` contract**: each task module now exports `reward_funcs`
  (list). `gsm8k.py`/`countdown.py` set `[format_reward, correctness_reward]` — no
  behavior change; conductor sets `[conductor_reward]`. `train.py` uses
  `task.reward_funcs` instead of hard-coding the pair.
- **`train.py`**: nothing else structural. New config fields kept minimal:
  `workflow_max_steps` (default 2) — worker ids/caps/paths live as constants in
  `tasks/conductor/workers.py` (nano-style). W&B project auto-derives to
  `qwen-grpo-conductor` via the existing rule.
- **`eval.py`**: two-phase mode for execution-backed tasks — if the task exposes
  `execute_and_score(completions, metas)`, eval generates conductor plans with the
  existing vLLM path, then calls it (phase 2 loads workers after freeing the vLLM
  engine). Per-problem JSONs unchanged in shape (`n_correct` from executed outcome);
  pass@k machinery reused; maj@k naturally off (`canonical=None`).
- **Tests**: `test_conductor_parser.py`, `test_conductor_tools.py`,
  `test_conductor_generator.py`, `test_conductor_executor.py` (mock worker pool — CPU,
  no GPU needed). Adversarial parser cases (malformed JSON, bad ids, wrong access,
  step-count violations, injection in subtasks) and generator property tests
  (gold graph executes via tools to gold answer, for every family × split × paraphrase).

## Stage 0 — harness (mostly CPU; GPU only for smokes + benchmark)

Build order, each with tests green before the next:

1. `parser.py` + adversarial tests. `tools.py` + tests (calculator exactness incl.
   division; executor whitelist rejects names/imports/pow like countdown's verifier;
   lookup normalization via existing `rewards.normalize_number`).
2. `generator.py` + property tests: 3 op families; atomic + two-step templates; splits;
   paraphrase variants; render check via `python -m tasks.conductor.generator`.
3. `prompts.py`: conductor system prompt (workflow format spec) + 4 hand-written
   out-of-domain demos (one-step direct; two-step dependency; independent→final;
   specialist+verification). Worker prompts demanding terse typed outputs.
4. `workers.py` + `executor.py`: lazy NF4 pool, per-worker batched generation with
   per-worker token caps (Math worker prompted terse; cap raised only if truncation
   telemetry demands), exact-key cache, wave-batched execution, JSONL traces. CPU tests
   via a mock pool; a small GPU check loads the real pool once.
5. Wiring: contract re-exports, `reward_funcs` contract change (+ green existing
   suites), eval two-phase mode.
6. **GSM8K forced-one-worker regression smoke** (the degenerate conductor): fixed
   trivial plan → one worker solves whole problem → existing GSM8K verifier. Confirms
   the full loop inside GRPO training on a known task. ~20 steps, 3B conductor.
7. **The Stage-0 feasibility benchmark** (reviewer's five steps, pre-registered gates):
   real GRPO completion batch on the real environment → parse all plans → wave-batch
   first/second-wave calls → measure peak memory, cache behavior, calls/hour, s/step.
   **Gates: <22 GB peak; projected seed ≤ overnight (~12 h absolute ceiling); reward
   path produces sane 0/0.5/1 distributions.** ~20-step smoke run to
   `qwen-grpo-conductor`. If wave-batching can't be achieved inside the reward function
   at this granularity, stop and reconsider the architecture before continuing.

## Stage 1 — capability calibration (GPU: inference only, vLLM per worker)

1. **Capability matrix**: 3 workers × 3 families × ≥500 atomic calibration-split
   examples, batched via vLLM (one engine per worker sequentially; ~minutes each),
   temp 0, through the same tools/scoring as training will use. Per-worker parse-fail
   and truncation telemetry (<2% gate each).
2. **Wording-sensitivity probe**: same matrix over the 5 paraphrase variants of each
   gold subtask. Gate on *specialist advantage surviving paraphrase* (≥20-point lead on
   intended operation across held-out paraphrases); record within-worker variance as an
   outcome (per the refined three-way interpretation).
3. **Oracle-workflow ceiling**: execute gold two-step workflows end-to-end on
   calibration split; gate: materially beats best direct worker; establishes the
   compounding ceiling empirically (no independence assumptions).
4. **Difficulty tuning loop**: retain/adjust templates against the gates (intended
   ≥70%; oracle two-step ≥70%-ish; headroom vs best single worker). First lever is tool
   permissions and task construction, per the proposal.
5. **Cold-start gate measurement** (after tuning): 32 prompts × 8 conductor samples
   with the few-shot prompt (untrained 3B, vLLM): ≥80% valid; ≥10% of groups contain a
   1.0 and a lower outcome; ≥25% non-zero-variance groups. One prompt revision allowed;
   SFT fallback only per the proposal's rule.
6. **Tranche verdict**: Stage-1→2 gate table filled in; go/no-go recorded.

## New experiment log: `conductor_log.md`

Same conventions as `experiment_log.md` (chronological entries, pre-registration before
GPU spend, backlog at bottom), fresh numbering `CE0, CE1…` to avoid collision with the
main log's E-numbers; cross-links to `experiment_log.md`, `concepts.md`, and the
proposal. Seeded at creation with:
- **CE0 (pre-registered)**: Stage-0 feasibility benchmark — gates, predictions
  (throughput ~6–9 h/seed if wave-batching works; cache hit-rate unknown → measured).
- **CE1 (pre-registered)**: capability matrix + paraphrase probe — gates and the
  three-way wording-sensitivity interpretation.
- Backlog: Stages 2–4 skeleton with their entry gates (from the amendments), so
  go/no-go verdicts have a place to land.
Main `experiment_log.md` gets a one-line pointer entry; `stages.md` Phase E section
gets a link. README file-map row added for the package + log.

## Files touched

| file | change |
|---|---|
| `tasks/conductor/` (7 modules) | new package per architecture above |
| `tasks/__init__.py` | register conductor; `reward_funcs` in contract doc |
| `tasks/gsm8k.py`, `tasks/countdown.py` | export `reward_funcs = [format_reward, correctness_reward]` |
| `train.py` | use `task.reward_funcs`; `workflow_max_steps` config |
| `eval.py` | two-phase execution-backed eval mode |
| `test_conductor_*.py` (4 files) | CPU test suites incl. adversarial parser + generator properties |
| `conductor_log.md` | new log, CE0/CE1 pre-registered |
| `experiment_log.md`, `stages.md`, `README.md` | pointer entries only |

## Verification

1. `uv run pytest` green throughout (existing 50 + new conductor suites, all CPU).
2. `python -m tasks.conductor.generator` renders an example per family incl. gold
   spine; parser/tools round-trip the few-shot demos.
3. GSM8K forced-one-worker smoke: trains ~20 steps without error; W&B
   `qwen-grpo-conductor` populates; traces JSONL written and re-scorable offline.
4. Stage-0 benchmark numbers recorded in CE0 against pre-registered gates.
5. Stage-1 matrix/probe/oracle/cold-start numbers recorded in CE1; Stage-1→2 gate
   verdict written before any Stage-2 work is considered.

Rough effort: Stage 0 ≈ 2–3 working sessions (GPU: ~1–2 h total for smokes+benchmark);
Stage 1 ≈ ~2–4 h GPU inference + analysis/write-up. Commits per repo style at each
coherent milestone (package skeleton+tests; wiring+smoke; benchmark CE0; calibration
CE1).
