# Unit 3 — evaluation support: 4^S diagnostic surface, canary, sentinels

106_s §§9.4–9.5 / §13.3. Battery: **641 CPU tests** under
warnings-as-errors; agreement unchanged at **16,665/16,665**. Fixtures
committed at `530a151` BEFORE any GPU call (per §0); GPU results below.

## Committed before GPU (unit 3a, `530a151`)

- **`stage0_support.json`** — the identity-selected declaration: first
  `worker_dev` latent by frozen generator ordinal in each of the six
  cells × three private renderers = 18 observations; 9×4 + 6×16 + 3×64
  = 324 assignments; 804 planned step executions; bound to
  `wv-4e196a1c467d108b` and `wp-197e286115f56e4a`, `task_last`, rev10,
  cuda. No new generator namespace; ordinal 0 lies inside the consumed
  D16 prefix.
- **`stage0_canary.json`** — the first sorted `code_atomic` w2/w3
  node-correctness disagreement from the retained rev10 runs
  (`worker_dev:00001`, `goal_first`; w2 wrong, w3 correct). Atomic
  cell ⇒ node reward = terminal reward. Ordinal 1 is outside the
  ordinal-0 support by construction; excluded from every aggregate
  summary; source artifacts hashed in the fixture.
- **`stage0_sentinels.json`** — six first-latent Code-node cases
  (code_atomic n1, fork_join n2 × three renderers) with both workers'
  retained completions and telemetry from `99_f`/`104_f`; a CPU
  continuity test proves the retained rendered-request hashes are
  byte-identical to what the pool renders today.
- `payoff_support.py`: materializer (context-aware 4^S execution
  through `execute_batch` with a v2 trace, wrong-family calls
  included), fail-closed loader (missing/duplicated/foreign/
  wrong-profile rows abort; declaration bytes and execution identity
  verified), canary and sentinel runners. **No adaptive execution
  path.**

## GPU results (RTX 4090)

**Materialization** (`runs/stage0-support`):

```text
payoff_rows 324 (complete; verify OK)
planned_step_executions 804
executed_step_records   560   (dependency blocking saved 244)
unique_singleton_generations 124   (in-flight dedup, counted at the pool)
cache_hits 0 (cold), wall 47.5s
declaration_sha 6df4c42b…, wv-4e196a1c…, wp-197e2861…
```

**Accounting disclosure:** the first materialization run mislabeled
"unique_singleton_generations" — it counted records not served by the
persistent cache (560), not physical generations; in-flight dedup makes
those differ. The counter now lives at the pool where generation
happens, the manifest carries both quantities, and the artifact was
deleted and re-materialized under the corrected accounting (identical
payoffs; 124 actual generations ≈ 0.38 s each).

**Canary:** worker 2 → 0.5, worker 3 → 1.0; rewards differ, matching
the registered expectation — model-scale selection demonstrably reaches
the terminal-reward path.

**Sentinels:** all 6 retained requests reproduced **bit-for-bit**
(completion, finish_reason, token counts, cap flag) by both workers in
fresh singleton processes, in both worker orders (`23` and `32`) —
the §9.5 model-order and fresh-process stability checks.

## What the surface contains (diagnostic, not a population estimate)

24 of 324 assignments reach payoff 1.0. Family structure is exact:
Lookup/Math strata admit only the family-correct assignment (1/4,
1/16). The Code strata carry **bidirectional model-scale stakes**:

| observation | winning assignments |
|---|---|
| code_atomic × all renderers | `(2,)` and `(3,)` — both Code workers |
| math_code × resource_first, bound_var | `(1,2)` and `(1,3)` |
| **math_code × goal_first** | **`(1,3)` only — worker 3 required** |
| **fork_join × bound_var, goal_first** | **`(0,2,1)` only — worker 2 required** |
| fork_join × resource_first | `(0,2,1)` and `(0,3,1)` |

The reference (family-canonical, worker-2) routing scores 17/18; its
single miss is exactly `math_code × goal_first` — worker 2's known
goal-first local-task mode, repaired by worker 3, while worker 3's
composition mode costs it both hard `fork_join` renderers. The
renderer-conditional, bidirectional complementarity 103_s/106_s built
the pivot on is present *inside* the frozen 18-observation support —
the §10.3 smoke will have real routing stakes at Code positions in
both directions.

## §9.5 acceptance status after unit 3

Complete: CPU tests green; four workers produce bound requests and v2
traces; w2/w3 same-case request bytes identical (fixture + runtime
tests); committed sentinels reproduced bit-for-bit in fresh singleton
processes; model-order stability; cold/warm cache isolation (unit-2
smoke); the diagnostic support is complete over every valid assignment
with a fail-closed loader; wrong-family outcomes are typed, never
aborts; VRAM/latency recorded; no construction examples beyond the
consumed prefix and no qualification examples touched.

Carried note: the family-typed `run_worker_output` boundary remains
deferred with the 112_f rationale (frozen worker-eval machinery calls
it with family indices; the executor resolves workers through the
registry before that boundary).

Next: unit 4 — Stage-0C trainer integration (task registration, the
single 0/0.5/1 reward, the named §10.1 launch profile, and the frozen
18-update policy-dependent smoke over this support).
