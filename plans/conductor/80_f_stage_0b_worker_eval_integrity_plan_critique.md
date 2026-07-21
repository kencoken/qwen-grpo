# Critique of 79_s — Stage 0B worker-evaluation integrity plan

**Date:** 2026-07-21

**Review target:** `plans/conductor/79_s_stage_0b_worker_eval_integrity_plan.md`
on `conductor_stage_0b_worker_eval_integrity` at `576f04f`.

**Evidence reviewed:** the plan; `78_s_d16_rev9_review.md` (on
`conductor_stage_0b_d16`); the Stage-0B implementation of `runtime.py`,
`workers.py`, `cache.py`, `executor.py`, `contract.py`, `tools.py`,
`parser.py`, `agreement.py`, `smoke.py`, `prompts.py`, `render.py`,
`types.py`.

## Verdict

The scientific content is correct and well targeted: every §2 "concrete
failure" traces to a verified finding in `78_s`, the isolated-node/composed
split, gold-predecessor construction, renderer crossing, strict external
scoring, prompt/profile binding and the fail-closed singleton probe are the
right corrections, and the plan's own scope discipline (§3.2, §7.4) is
exemplary.

**The risk is not what the plan measures but how much machinery §5–§6 specify
to measure it.** The conductor package is ~7,000 lines total. Implemented as
literally written — a ~30-field-group manifest with embedded ordered row
plans, a status-conditional row schema with a loader that enforces field/null
combinations, parse-stage replay instrumentation, a new canonical binding
type, a run-comparison language — the evaluator plus its validators would
plausibly become the largest subsystem in the repository, in a didactic
codebase whose stated ideal is simplicity. Most of the plan's integrity
guarantees are achievable with mechanisms that already exist (deterministic
regeneration, frozen `Resource` types, pure `parse_envelope`, one-request
batching). The findings below identify where the specified mechanism is
heavier than the guarantee requires. None of them weaken a contract; each
replaces a mechanism with a smaller one that provides the same or strictly
stronger checking.

Recommendation: **approve with the amendments below folded into a rev2 before
Tranche A begins.** Findings 1–6 are plan-text changes; findings 7–8 are open
decisions that should be closed (or explicitly assigned an owner and deadline)
before the tranche they affect.

## Claims verified against the code

- `E_PARSE` is genuinely stage-ambiguous: `contract.parse_envelope` raises it
  for close-before-open, and `tools.py` raises it from ~20 grammar sites
  (§5.3's premise holds).
- `Runtime.__init__` shallow-copies the profile
  (`runtime.py:239`) and `WorkerPool.render_request` reads the module-global
  `SYSTEM_PROMPTS` (`workers.py:83`); both §2 rows are real.
- `Runtime.worker_call_batch` deduplicates byte-identical misses
  (`runtime.py:274–295`), confirming the need for §6.2's
  one-generation-per-case requirement.
- `IntegerRecord`/`IntegerList` are `frozen=True` dataclasses with tuple
  payloads; only `Binding` holds mutable dicts (relevant to finding 4).
- §4.6 arithmetic checks out: 30 latents × 6 cells = 180; ×3 renderers = 540;
  nodes per renderer = 30·(1+1+1) + 30·(2+2) + 30·3 = 300; ×3 = 900.
- The branch base matches the stated `conductor_stage_0b` @ `365f2dd`.

## Finding 1 — the manifest's embedded row plan duplicates loader regeneration

§5.1 requires the manifest to embed "the exact ordered scheduled-row keys
`(evaluation_mode, case_id, position)` and their SHA-256", §5.3 requires every
call row to validate its "global schedule ordinal" against that plan, and §5.6
*separately* requires the loader to regenerate the entire population from the
manifest's population identity and require exact key agreement with
`calls.jsonl`.

The §5.6 regeneration check is the strong one — it re-derives the ground truth
from the frozen generator and catches a planner bug, a truncated file, and a
tampered file alike. Once it exists, the embedded ordered-key list, its
SHA-256, and the per-row schedule-ordinal cross-check add no detection power:
any row set that passes regeneration-equality has exactly the planned keys,
and order within `calls.jsonl` is already fixed by append order plus the
file hash.

**Amend:** drop the embedded ordered-key list, its hash, and the per-row
"global schedule ordinal validated against the manifest" from §5.1/§5.3. Keep:
population identity (namespace, range, renderers, visibility, schedule
version) in the manifest; expected/written row counts; payload-file SHA-256s;
loader regeneration with exact key-set equality. Same guarantee, one mechanism
instead of three.

The same trimming instinct should govern loader implementation: §5.6's checks
should be one hand-written `load_run()` with explicit `if` statements, not a
schema-validation layer. (The plan does not mandate a validator framework, but
§5.3's "the loader enforces these combinations" language invites one; the
rev2 should say "hand-written checks" explicitly.)

## Finding 2 — two overlapping trace formats are specified but not reconciled

The executor already has a per-step JSONL trace (`TraceWriter` +
`steps.jsonl` + its own manifest) carrying most of §5.3's fields. The plan
adds `calls.jsonl` with a superset of those fields plus a different identity
scheme, and §6.4 adds "only the call telemetry needed by §5.3" to the
executor — but never states what happens to `TraceWriter` during an evaluator
run. The likely drift outcome is two nearly-identical formats maintained
forever, which is the opposite of didactic.

**Amend:** state explicitly that evaluator runs do **not** use `TraceWriter`;
`calls.jsonl` is the evaluator's sole trace. Isolated mode writes rows
directly from its own loop. Composed mode wraps `execute_workflow_batch` with
a callback/adapter that converts each `StepRecord` + `CallRecord` into a
`calls.jsonl` row. `TraceWriter` remains what it is today: the Stage-0B smoke
trace. If a `StepRecord` field addition is needed for §5.3 (e.g. carrying the
`Binding` hash out of the executor), add the field; do not add a second
writer.

## Finding 3 — parse-stage attribution needs six lines, not instrumentation

§5.3: "Instrument/replay the existing envelope parser and then the existing
grammar/tool path, without changing acceptance." This over-specifies.
`parse_envelope` is a pure string function with no tool side effects, and the
terminal `WorkerResult` already distinguishes grammar-stage from tool-stage
via `SYNTAX_REJECTION_CODES` / `SEMANTIC_REJECTION_CODES` (enforced by the
`WorkerResult` flag truth table). So stage attribution for a called row is:

1. call `contract.parse_envelope(completion)` in the evaluator, catching
   `ToolRejection` → envelope-stage outcome;
2. if the envelope passed and the authoritative `run_worker_output` result
   carries a syntax code → grammar-stage;
3. a semantic code or success → tool executed.

The authoritative path runs exactly once; nothing in `parser.py`, `tools.py`
or `contract.py` changes; the §5.3 requirement that the staged record agree
with the terminal `WorkerResult` becomes a two-line assertion.

**Amend:** replace the "instrument/replay" language with this construction so
an implementer does not build parser hooks.

## Finding 4 — `CanonicalBindingPayload` is an unnecessary new type

§4.1/§4.2 introduce a named canonical binding payload with its own
canonicalization and reconstruction rules, motivated by `Binding` holding
caller-owned dicts. But the payloads inside those dicts —
`IntegerRecord`/`IntegerList` — are already frozen dataclasses over tuples,
i.e. already immutable and hashable. The only mutable containers are the two
dicts on `Binding` itself.

**Amend:** give `WorkerEvalCase` primitive fields instead of a new type:

```python
resources: tuple[tuple[str, Resource], ...]   # ≤1 entry in v0
steps: tuple[tuple[int, int], ...]            # (position, gold value)
```

Build a fresh `Binding(resources=dict(...), steps=dict(...))` at tool
execution, and compute `binding_sha256` with the existing
`profiles.canonical_json` over a plain dict rendered from those tuples. This
satisfies every §4.2 requirement (immutability, no retained caller dicts,
hashability, fresh reconstruction) with zero new classes.

## Finding 5 — `call_role` is anticipatory abstraction by the plan's own rule

§4.4 defines a two-value `call_role` enum derived "from the declared logical
endpoint/node-family schedule". In this change every scheduled call is
operator-aligned: `off_contract_diagnostic` cannot occur, because payoff-
surface/misroute work is explicitly out of scope (§3.2). An enum plus
derivation logic for a value that has exactly one inhabitant is the
"generalized arm type system" §1 forswears, in miniature.

**Amend:** keep the *column* (it future-proofs the file format cheaply) but
write the constant `on_contract_reference` and delete the derivation
machinery from the plan. When a future change introduces off-contract calls,
it adds the derivation with its own review.

## Finding 6 — singleton + cache-disabled needs no new Runtime generation path

§6.2/§6.3 list several runtime/pool changes ("expose cache-disabled calls",
"an explicit singleton generation method", "do not apply the current
duplicate-request miss deduplication"). The existing code makes almost all of
this structural rather than additive:

- **Cache-disabled:** `build_runtime(profile, cache=NullCache())` where
  `NullCache.lookup` returns `None` and `store` is a no-op (~8 lines, can
  live in `worker_eval.py`). Every row then trivially has
  `cache_source=disabled`.
- **Singleton:** the evaluator calls `worker_call_batch(endpoint, [one
  message])` once per case. With one request per call, the miss-dedup dict is
  vacuous (test 9.1.18 passes structurally), `pool.generate` receives a
  single request, the microbatch chunk is size 1, and — because a batch of
  one left-padded sequence has no padding — the padding-induced batch
  sensitivity P1 probes is removed by construction on the scientific path.

The genuinely required runtime changes reduce to three: deep-copy the profile
in `Runtime.__init__` (one `copy.deepcopy`), thread a resolved prompt mapping
into `WorkerPool.render_request` and the fingerprints, and add the rendered
request text (not just its SHA) to `CallRecord`. `worker_call_batch`'s logic
is untouched.

**Amend:** rewrite §6.2/§6.3 to this shorter list so an implementer does not
add a parallel generation method. The P0 diagnostic batched probe (§7.2) still
needs a way to run frozen physical chunks; that belongs in the probe script,
driving `pool.generate` directly with recorded chunk lists, not in `Runtime`.

## Finding 7 — the deterministic-backend setting is recorded but never decided

§5.1 records "seed policy and Torch/CUDA deterministic-backend flags" and §7.3
freezes cost limits, but no section decides *which* flag setting P1 actually
runs under (`torch.use_deterministic_algorithms`,
`CUBLAS_WORKSPACE_CONFIG`, cuDNN flags). P1's admissibility verdict can differ
across these settings, and admitting `singleton-v1` under a configuration
Stage 1/2 will not use would invalidate the gate's transfer.

**Amend:** state that P1 runs under the default (non-forced) backend settings
— the configuration the training stages will actually use — with the flags
recorded in the manifest; a P1 failure may then motivate testing the forced-
deterministic setting as part of the §7.4 follow-up plan, not silently.

## Finding 8 — the double 900-case confirmation cost should be scoped

§7.4/§9.2.10 require every *accepted* candidate's full 900-case run to be
repeated in a fresh process with exact equality. Per candidate that is
≤2 hours under the frozen gate, plus P1's three 300-case passes. `78_s`
already names at least four Code-model candidates, before request-scope
variants multiply. The requirement is scientifically sound but the plan
should say whether "accepted" means *every candidate whose numbers are cited*
(expensive) or *the finalists that survive comparison* (cheaper, with the
risk that a losing candidate's single run contained a nondeterministic
artifact — acceptable, since losing candidates are not frozen).

**Decision for Ken:** recommend the narrower reading — double-run only
candidates advanced to final comparison/freeze — recorded as an explicit
amendment either way.

## Minor notes

1. §5.4: repeating the full call-file SHA-256 on every score row is
   redundant with the manifest's file hashes; `run_id` + `case_id` suffices.
2. §6.1 `compare_worker_eval_runs`: correctly narrow; implement as a manifest
   dict-diff against a per-enum allowlist and nothing more. Tranche C is the
   right home; do not build it earlier.
3. §5.1 "dirty-state/diff digest" plus "retained GPU comparison runs require
   a clean committed worktree" is the right pairing — keep both.
4. The plan correctly leaves D1 (the `worker_dev` namespace erratum) outside
   this branch; note that Tranche B/C CPU tests must therefore run on fakes
   and existing namespaces, and the 180/540/900 counts of §9.2.1 are
   validated only in Tranche D.
5. Naming: §6.1's caution against "oracle assignment" language matches the
   existing `_ENDPOINT_FOR_OP` in `agreement.py`; moving it to a shared
   reference utility (with `reference_artifact`) is the right call — suggest
   `reference_eval.py` or extending `agreement.py`'s public surface rather
   than a new module if the move stays under ~40 lines.

## Conclusion

Approve with rev2 amendments: findings 1–6 shrink specified mechanism without
weakening any contract; finding 7 closes a gap that could silently
invalidate the P1 gate; finding 8 is a cost-policy decision to record before
Tranche D. The contracts in §4, the four-file artifact set, the tranche
gates, and the acceptance battery are sound as written. With the amendments,
the implementation should land well under half the size the literal §5–§6
text implies, which is the difference between an evaluator a reader can audit
in one sitting and a second framework.
