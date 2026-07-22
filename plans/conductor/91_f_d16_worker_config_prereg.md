# Preregistration — D16 scope × model experiment (draft for freeze)

**Status: DRAFT.** Every rule and number below must be frozen — Ken's
sign-off, with reviewer check if desired — **before any P1 output or arm
result is inspected** (the §7.3 freeze discipline: a reviewer may
replace a number before the run, never after seeing outcomes). The §5
prerequisites land first; nothing here runs until they do.

## 1. Objective and conclusion condition

Per Ken's direction and the 78_s/89_s orientation: **select the worker
model for each endpoint, and the shared request contract (scope), before
any further prompt-text iteration.** The rev1–9 cycle is development
history and P0 regression evidence, not selection evidence; this
experiment produces the selection evidence on the corrected evaluator.

The experiment concludes when:

1. each endpoint (Lookup, Math, Code) has a frozen **model checkpoint**,
   and all three share one frozen **request contract**, adequate under
   the §3 rules on the corrected 900-case crossing — or the escalation
   budget is exhausted and work stops with a documented decision;
2. the freeze actions land together: the Code model and scope, the
   pending §1.6 Math-endpoint erratum ratification, and the `math_code`
   index-band ruling (with 78_s's caution: the band is decided on this
   crossed evidence, never narrowed post hoc to fit observed failures);
3. **prompt texts are held fixed throughout** — the registry-resolved
   rev9 bundle in every arm. If residual inadequacy remains after
   selection, prompt iteration restarts *afterwards* on the frozen
   model/scope, under its own bounded plan.

Position going in (78_s §endpoint recommendation, 89_s closing note):
Lookup = generic-1.5B (closed; re-confirmed in passing), Math =
generic-1.5B (provisional, ratification bundled with conclusion 2),
Code = open — jointly with scope, the experiment's question. No 7B, no
retries, no constrained decoding, no parser normalization, no new
prompt prose until this design says what residue remains.

## 2. Arms and escalation budget (89_s design)

- **Stage 1 — four arms:** {`current`, `task_last`} × {Coder-1.5B
  @`2e1fd397…`, generic-1.5B @`989aa798…`} for the Code endpoint;
  Lookup and Math run generic-1.5B in every arm. Estimated ≤8 GPU-hours
  under the frozen worst-case timing gate.
- **Escalation A:** both Code models favor the same scope but neither
  is adequate → {that scope} × {Coder-3B, generic-3B} (two arms).
- **Escalation B:** scope rankings conflict across the 1.5B anchors →
  the clean 2 scopes × 4 models factorial (four further arms), never a
  post-hoc scope choice.
- **`local_only` scope:** diagnostic probes only; never freeze-eligible.
- **Budget (frozen):** at most 8 arms total; no arms, models, scopes or
  prompt edits beyond the rules above without a new preregistration
  document. Arm results are inspected only after that arm's full
  crossing completes. The `worker_dev` cap bounds the examples; this
  budget bounds the iterations over them — both are needed (89_s).

## 3. Adequacy, ranking and tie-breaks (numbers proposed for freeze)

Denominators per arm: the full `worker_dev` crossing — 900 isolated
calls; Code-endpoint calls 270 (30 per renderer × cell; strata are
renderer × node operator, the finest cut with n ≥ 15).

- **Code adequacy:** every renderer × operator stratum ≥ 90%
  `node_correct`, and endpoint-wide envelope+grammar failures ≤ 2%
  (matching the 1A parse-gate posture 78_s cited).
- **Lookup/Math adequacy under a scope:** every stratum ≥ 29/30. A
  scope that breaks Lookup/Math adequacy is inadmissible regardless of
  Code gains — the contract is shared, so its cost is charged to every
  worker.
- **Ranking among adequate Code arms:** maximize the *minimum* stratum
  proportion (78_s: the smallest model satisfying the worst stratum,
  not the best pooled mean). Ties break in order: higher total strict
  correct (of 270); fewer envelope+grammar failures; smaller model;
  `current` scope over `task_last` (fewer contract changes).
- **Selection outputs are descriptive point estimates** (81_f §4.5);
  no bootstrap or Stage-1 gate is emitted.

## 4. Held fixed across every arm

One clean commit for the whole stage (89_s advice adopted: any commit
difference between arms requires human verification that it is
documentation-only); the rev9 prompt bundle, registry-resolved; pinned
model revisions, chat templates and tokenizer facts; NF4 config; 256
token caps; greedy decoding; the frozen generator and difficulty
profile; the operator-aligned endpoint schedule; `singleton-v1`
generation (post-admission); private visibility, all three renderers.

## 5. Prerequisites, in order (89_s steps 2–6)

1. **P0 cohort freeze** from the retained rev9 traces: exact request
   hashes, ordering, and the physical 16/16/13 chunks. Then the **P0
   replay** on `picome`: original grouping twice, reversed, singleton —
   evidence preservation; P0 admits nothing.
2. **Implement and version the `task_last` request contract**: a scope
   option on `build_worker_request`/`build_worker_call`, a second
   `REQUEST_CONTRACTS` key resolving to exact content, byte fixtures,
   CPU tests — and only then re-enable the `request_contract`
   comparison dimension with byte-level must-differ (per 84_s, it stays
   disabled until the key configures the builder).
3. **Freeze this document** (arms, budget, §3 numbers, §6 policy).
4. **P1 admission per exact configuration** — each of the four
   model × scope configurations is its own candidate configuration
   (request bytes differ), so each gets its three fresh-process runs
   and its own admit verdict against the hard-bound `worker_dev` plan.
   Fail closed per §7.4.
5. **Support manifests recorded**: the P1 and full-population manifests
   enter the D16 log with the first runs (88_f checklist 5).
6. **Operational gate (89_s):** every real probe/evaluator command must
   finish with a valid artifact *and* exit code zero; the known
   `picome` pytest-teardown exit-139 is tracked separately and must not
   be allowed to blur that requirement.

## 6. Run matrix and comparisons

Per arm: one 900-case isolated crossing (RunWriter artifact, loader-
verified). **Composed workflow diagnostics run for finalists only**
(proposed for freeze — compounding evidence informs the freeze record,
not the selection rule). Model contrasts compare via
`compare_worker_eval_runs(..., "model", model_endpoint="code")`; scope
contrasts via the re-enabled `request_contract` dimension (same model,
scopes differ). Each finalist gets the §7.4 two-run confirmation before
its numbers enter the decision record.

## 7. Output

One decision-record document: the selected (model, scope) per endpoint
with the §3 rule applied mechanically to the recorded runs, the freeze
actions from §1.2, and — if escalation was triggered — which rule fired
and why. Any outcome outside the preregistered rules is a stop, not an
improvisation.
