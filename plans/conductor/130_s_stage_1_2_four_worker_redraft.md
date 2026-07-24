# 130_s — Stage 1/2 four-worker redraft

**Status: first draft for review — not frozen and not authorization to run
construction, qualification, cold-start, or Stage-2 training.**

This document revises the active Stage-1 qualification and Stage-2
routing-only design after the four-worker pivot and measured Stage-0 close.
It is intentionally one normative amendment rather than another layer of
implementation abstractions. The experiment remains a small orchestration
laboratory whose purpose is to expose learning dynamics on one RTX 4090.

The review/freeze order is:

1. review this design and resolve every item marked **REVIEW CHOICE**;
2. implement and review the Stage-1 prerequisites in bounded units;
3. append the exact Stage-1 hashes, commands, populations, statistical seeds,
   and approved branch formulas to the CE1 Freeze Record;
4. freeze CE1 before revealing formal construction worker results;
5. stop again after qualification and cold start for the Stage-1→2 verdict;
   and
6. launch one disposable Stage-2 development signal seed only if its
   preregistered branch permits it, followed by three fresh headline seeds
   only if the disjoint pilot gate passes.

Historical Stage-0/`worker_dev` evidence already defined the inherited
few-shot prompt candidate and motivated this four-worker design. It may not
now choose between few-shot and schema-only, tune either candidate further,
select a formal construction example or qualification decision, or enter a
Stage-1/2 estimate, checkpoint decision, or headline claim.

---

## 1. Authority, inherited contracts, and superseded text

### 1.1 Authority

The Stage-0 closure set is:

- `127_f_stage_0_go_no_go_handoff.md`;
- `128_s_stage_0_go_no_go_closure.md`; and
- `129_f_stage_0_completion.md`.

Stage 0 closed GO with the record-only corrections in `129_f`. The selected
execution mode is complete pre-materialization: worker models are not resident
during routing-only GRPO.

The frozen cell specification remains authoritative for cell semantics,
privacy, generation, interventions, weighting, and detailed baseline
definitions. The rev6 plan remains authoritative for stage/action/reward
boundaries where it does not conflict with a **named** amendment below.
Neither a broad sentence in this plan nor in rev6 silently overrides the
cell specification.

The active amendments are exhaustively enumerated:

| frozen source text | active amendment |
|---|---|
| three workers / `3^S` | four logical workers / complete `4^S` |
| best of three one-call candidates | best of four logical worker treatments |
| 18 fork two-call workflows | mechanically generated 32 workflows |
| undifferentiated runner-up | separate family and within-Code model stakes (§6) |
| positions failing effective stakes are fixed/hidden in Stage 2 | a failed family stake excludes a mandatory Core cell; a failed scale stake remains an observable four-action nuisance but is excluded from C2, with no hidden action override (§§6.2, 9) |
| construction indices 0–99 | proposed formal cohort 30–129 (§3.1) |
| namespace list without `policy_dev` | targeted namespace erratum (§10.2) |
| universal parse+truncation <2% | per-cell selected-route syntax and per-`(cell,worker)` truncation rule (§7.1) |
| ordinary/fork inference left for CE1 | exact sequential rules in §8 |
| approximate visible slice | exact first-18-per-cell rule (§4.1) |
| Stage-2 population/schedule unspecified | branch formulas in §§11–13 |

`106_s` governs the frozen four-worker registry/runtime. This document governs
only the named Stage-1/2 amendments above and decisions explicitly deferred
by `106_s` §15. The signed CE1 Freeze Record and Stage-2 Freeze Addendum fill
their respective placeholders; historical three-worker artifacts keep their
original meaning.

### 1.2 Contracts that remain frozen

This redraft does not reopen:

- six cell semantics, reference programs, resource privacy, legal topologies,
  renderer strings, interventions, reward ladder, or reference functions;
- the flat four-logical-worker/two-checkpoint registry and opaque ids;
- worker-side rev10 Lookup/Math/Code prompts;
- `worker-blocks-task-last-v1`;
- worker-2/worker-3 byte-identical Code requests;
- greedy worker decoding, singleton execution, endpoint tools and artifact
  grammars;
- action schema `{"worker_ids": [...]}`, with exact `4^S` support;
- `0 / 0.5 / 1.0` as the only task reward and infrastructure failures aborting
  rather than becoming reward;
- construction-only selection and qualification-only evaluation;
- three renderer variants as repeated observations within one latent cluster;
  or
- pre-materialized Stage-2 payoff surfaces.

Worker, endpoint family, and checkpoint remain distinct concepts. A worker is
the complete frozen treatment:

```text
checkpoint + worker system prompt + request contract + visible local context
+ parser/tool + inference settings
```

### 1.3 Stage-0 evidence carried forward, with limits

Stage 0 established:

- the exact pool can execute and cache complete four-worker payoff surfaces;
- workers 2 and 3 can change terminal reward in both observed directions on
  the small diagnostic support;
- routing-only QLoRA peaked at 14.43 GiB;
- the selected pre-materialized path is feasible on the RTX 4090; and
- the final few-shot prompt is highly parseable.

Stage 0 did **not** establish:

- the prevalence or qualification stability of worker-2/worker-3
  complementarity;
- that the preferred Code worker is predictable from public information;
- that GRPO learns both directions;
- that demonstrations did not already encode most of the policy;
- a final Stage-2 population, schedule, runtime, or first-seed duration; or
- generalization beyond the three frozen renderer grammars.

The CE0 43.4-minute figure is diagnostic-scale only. The 100-latent-per-cell
linear reference is approximately 78 minutes of worker materialization plus
43 minutes for 300 training updates, or about two hours to the **first** seed.
The exact estimate is recomputed from the admitted population and schedule.
This also normalizes two harmless closure-record phrasings: materialization
is shared rather than repaid “per seed,” and the `math_code` difficulty-band
prerequisite is carried normatively by §5.2 here rather than being physically
present in restored `127_f` item 4.

---

## 2. Scientific framing and claim ladder

This is an **orchestration laboratory**, not a miniature frontier-model
benchmark. Heterogeneity is partly constructed: resources are hidden from the
Conductor, tools are endpoint-specific, reference topology and reference
subtasks are supplied, and the action selects fixed opaque worker ids.

The pool has a nested structure:

| worker | endpoint family | checkpoint |
|---:|---|---|
| 0 | Lookup | Qwen2.5-1.5B-Instruct |
| 1 | Math | Qwen2.5-1.5B-Instruct |
| 2 | Code | Qwen2.5-1.5B-Instruct |
| 3 | Code | Qwen2.5-3B-Instruct |

This creates two learning problems that are never collapsed into one
“orchestration” number:

1. **Family routing:** choose Lookup, Math, or Code. This is deliberately
   constructed model-plus-tool heterogeneity.
2. **Within-Code model routing:** choose worker 2 or 3 while Code prompt,
   request bytes, grammar, tool, authorization, and decoding are held fixed.
   Only the checkpoint differs.

A policy may improve substantially by learning only family routing. That is a
valid C1 result, not evidence for C2.

| rung | defensible claim | required evidence |
|---|---|---|
| C0 — integration | Sampled actions reproducibly reach the intended frozen payoff surface on one 4090. | Provenance, complete surfaces, cache/live sentinels, no infrastructure failure scored as reward. Stage 0 established this; new artifacts revalidate it. |
| C1 — family routing | GRPO learns Lookup/Math/Code endpoint-family selection in the constructed typed environment. | Fresh family stakes; trained policy beats its identical untrained-prompt baseline and random controls; family selection and terminal outcome improve on held-out data. |
| C2 — model routing | GRPO learns when to use the 1.5B versus 3B Code checkpoint under an otherwise equal Code interface. | Qualification-stable public scale mapping uses both workers and beats best-fixed Code; the trained policy captures positive incremental scale lift on held-out data. |
| C3 — useful hierarchy | The trained composed workflow adds value beyond one worker/treatment receiving the whole task in one call. | The trained policy, not only the deployable oracle, beats the construction-frozen best one-call worker/treatment on fresh data, with call cost reported. |
| C4 — language-robust routing | Routing reflects semantics beyond renderer/template shortcuts. | Unseen semantic/paraphrase renderer plus shallow, renderer-only, and bag-of-words controls. Deferred. |
| C5 — stronger Conductor analogy | Learned decomposition, instruction writing, pool adaptation, or recursion. | Not tested by Stages 1–2. |

The primary Stage-2 claim remains:

> Under a frozen typed workflow, fixed reference subtasks, and fixed opaque
> worker ids, GRPO learns endpoint selection from terminal reward.

Even C2 establishes conditional selection between two fixed
model–prompt–contract endpoints. It does not establish self-selection,
decomposition, recursion, dynamic pools, or frontier-model efficiency.

C1 and C2 are sibling learned components under C0, not a strict empirical
ladder. A few-shot policy could begin with near-ceiling family routing while
GRPO still learns Code-model routing. In that case C2 may pass while C1's
required improvement does not; the result is reported exactly that way. C3
likewise depends on trained terminal performance, not on relabelling C1/C2.

---

## 3. Phase and namespace hygiene

### 3.1 Consumed construction prefix — **REVIEW CHOICE D4**

Historical D16 work consumed `construction` indices 0–29 before
`worker_dev` existed. They remain permanently development-consumed and may
not enter a construction gate, fitted control, qualification, train, dev, or
test estimate.

**Recommended decision:** retain the namespace but extend its registered cap
from 100 to 130 and define the one formal construction cohort as indices
30–129 inclusive for every cell. The manifest rejects 0–29 and any index
outside 30–129. This is simpler than adding `construction_v2`, keeps exactly
100 consecutive clusters per cell, and preserves the factorial balance rule.

The alternative is a new construction namespace. It is scientifically clean
but adds a second namespace solely to avoid a fail-closed range rule. This
draft recommends 30–129.

### 3.2 Split roles

| namespace/population | permitted use | forbidden use |
|---|---|---|
| `worker_dev`, Stage-0 support, Stage-0 smoke | historical prompt/model/runtime development evidence | every gate, fitted control, train/dev/test estimate |
| formal construction 30–129 | profile screening, fitting controls, choosing and freezing mappings/baselines | qualification claims or final evaluation |
| `qualification` | evaluating construction-frozen choices at registered sequential looks | refitting, reselection, prompt/profile edits |
| `policy_dev` (new) | reward-blind format probe and reward-bearing cold-start/prompt-treatment decision | Stage-1 gate estimates, training, checkpoint selection, test |
| `train` | GRPO prompt schedule | control fitting, checkpoint selection |
| `dev` | checkpoint selection and pilot continuation | headline result |
| `test` | one final evaluation after checkpoints and seeds are frozen | tuning, stopping, checkpoint selection |

All three renderings of one latent stay in the same namespace. No latent
identity crosses populations.

### 3.3 Executable phase state machine

1. **CE1 freeze:** sign this plan; freeze source/environment manifest schema,
   exact `SYSTEM_DIRECT`, profile candidates, statistical rules, visible
   slice, cascade codes, and population registrars.
2. **Construction registration:** register exact clusters/renderings and
   expected candidate/control supports before worker execution.
3. **Reference/control fitting:** fit B1 controls from gold/reference
   construction records before revealing worker or control accuracy.
4. **Construction reveal:** inspect construction performance, apply only the
   frozen whole-profile rule, and freeze the final difficulty profile,
   deployable mappings, controls, and qualification hypotheses.
5. **Qualification registration:** register the maximum qualification
   population and all execution fingerprints before its first worker call.
6. **Qualification:** evaluate immutable prefixes; never refit or reselect.
7. **Stage-1 verdict:** classify cells/positions as failed, family-only, or
   family+scale.
8. **Policy development:** use fresh `policy_dev` observations to select one
   already-frozen prompt treatment by the cold-start rule.
9. **Stage-2 freeze:** register train/dev/test schedules, surfaces, launch
   profile, seeds, checkpoint rule, and compute projection.
10. **Development signal:** run one disposable seed; select its checkpoint on
    `dev_select`; continue only under the frozen disjoint pilot rule.
11. **Headline seeds and test:** run three fresh seeds without changing
    configuration; reveal test once after every checkpoint is selected.

Any material change to worker, prompt, request contract, parser/tool,
generator/renderer, difficulty profile, cache policy, direct prompt, scorer,
or inference code retires every affected qualification or Stage-2 surface.

---

## 4. Provenance and population manifests

Stage-1 and Stage-2 gate reports are valid only when one authoritative
manifest binds:

- exact latent and render-instance ids;
- namespace cap, allowed prefix, renderer crossing, and visible-slice rule;
- generator, renderer, and difficulty-profile versions;
- executable commit, complete source digest, lockfile and environment;
- four-worker registry, logical/physical mapping, checkpoint and tokenizer
  revisions;
- chat template, worker prompts, `SYSTEM_DIRECT`, policy prompt, and request
  contract hashes as applicable;
- NF4, decoding, batch, token-cap, stopping, and singleton settings;
- tool, parser, scorer, reward, cache, and trace schema identities;
- visibility/disclosure condition;
- expected candidate, call, payoff-row, and observation counts;
- sequential look schedule and statistical-code hash; and
- every subordinate payoff, completion, trace, fitted-control, and selection
  artifact hash.

Compared arms must have exactly the same registered observation keys and
execution fingerprints except for the treatment explicitly named by the
contrast. `gate_report` fails closed on a missing, duplicated, stale, or
partial row. No surface miss becomes reward 0 or 0.5.

The current source includes post-Stage-0 citation-only changes. A new complete
source/environment manifest is therefore mandatory before the first Stage-1
GPU execution; Stage-0 source digests are historical evidence, not a Stage-1
execution identity.

### 4.1 Visible slice — **REVIEW CHOICE**

**Recommended decision:** the first 18 qualification clusters per cell,
108 latent programs if all six cells enter qualification. Eighteen is
divisible by every frozen factor-block size in `{1,2,3,6}`. Generate paired
private and visible observations for these identities under all three
renderers. The private observations remain part of the primary qualification
population; visible variants support B3/echo/no-op diagnostics only.

No approximate “~100” slice remains in executable configuration.

---

## 5. Construction screen and difficulty-profile discipline

### 5.1 Entry requirements

Before construction worker accuracy is revealed:

- D4 and the exact 100-cluster cohort are implemented and tested;
- `SYSTEM_DIRECT` bytes and answer-line parser are reviewed and hashed;
- B1 majority, public-parameter echo, and shallow predictor rules are frozen;
- exact infrastructure retry codes/limits and cascade trigger codes are
  separately frozen;
- profile candidates and their selection order are registered;
- the complete `4^S` and control support plan is registered;
- the CE1 gate table, intervals, bootstrap seeds, and degeneracy rules are
  frozen; and
- construction and qualification cost predictions pass their tranche gates.

### 5.2 Difficulty profiles — **REVIEW CHOICE**

The original two-phase contract remains: cell semantics are frozen, while
fields marked `(S)` may be selected after the construction screen and before
qualification.

To prevent open-ended fitting, this draft recommends:

1. one primary profile per cell, initially the current complete profile;
2. an optional fully specified fallback only for a cell with a concrete
   pre-CE1 reason—there is no requirement to invent six fallbacks;
3. a frozen ordered “first whole profile satisfying the construction screen”
   rule;
4. no prompt, model, parser, or request-contract change between profiles;
5. no retaining or discarding individual instances based on worker outcomes;
   and
6. failure of both candidates excludes the cell until a new reviewed plan.

Each profile has its own version/digest and complete 100-cluster run. Prior
attempts remain construction data and are never laundered into qualification.

The construction screen first applies the frozen structural/rejection gates,
then the point-estimate versions of the core capability, family, hierarchy,
and intervention thresholds in §7. Confidence intervals and admission claims
belong to qualification. Model-scale point estimates classify headroom but do
not cause an otherwise core-viable profile to be skipped for a later profile;
this prevents a fallback ladder from becoming a search for accidental
worker-2/worker-3 disagreements.

For `math_code`, no post-hoc `step_1 ≤ 8` filter is permitted. The primary
profile retains the current full `L_band=[8,16]`. If a bounded-index fallback
is wanted, its exact complete profile and trigger must be approved in CE1.
The retained D16 evidence already contains a low-index semantic failure, so
an index cap is not assumed to solve the protocol issue.

This resolves the apparent wording tension in `129_f`: the **candidate set
and selection rule** freeze before construction; the selected `(S)` profile
freezes after the screen and before qualification.

### 5.3 Construction execution and outputs

For each profile/cell:

- 100 latent clusters, all three private renderers;
- complete assignment surfaces: 4 atomic, 16 two-step, 64 fork assignments;
- one-call support over four workers;
- the mechanically generated 32-workflow fork two-call control;
- independent reference-node scoring against the intended node answer,
  terminal-gold-coincidence telemetry at nonterminal nodes, renderer-crossed
  worker/node results, and full composed outcomes;
- protocol, tool, truncation, dependency-blocking, and call telemetry;
- rejection/marginal/collision checks required by the cell specification; and
- exact costs, physical generations, cache events, traces, and disk.

B1 fitted artifacts use one canonical `resource_first` row per construction
cluster and are content-addressed before their accuracy is revealed.

Construction then jointly argmaxes the complete assignment surface for each
cell and persists the resulting tuple under semantic node keys. It does
**not** independently maximize each node. Without any qualification argmax,
construction also persists:

- jointly selected deployable assignment tuple per cell, exposed as the
  frozen mapping `(cell_id,node_id) → worker_id`;
- family comparators;
- Code model comparators and best-fixed Code worker;
- best-fixed assignment;
- best one-call worker/treatment among the four logical workers;
- the best 32-workflow two-call shortcut;
- semantic, compatibility, renderer-only, and shallow routers;
- B1 fitted controls; and
- cascade behavior and expected physical-call cost.

Construction point estimates choose frozen treatments. They are not passing
claims.

---

## 6. Four-worker estimands

Let `Y_i(a)` be terminal correctness for rendered observation `i` and
semantic worker assignment `a`. Selection occurs on construction only.
Qualification evaluates frozen choices without an argmax path.

Renderer-crossed observations are paired within latent programs. Oracle,
control, and terminal policy means use equal latent-cluster weights. The
intervention estimand deliberately differs as specified in §8.3.

Let `family(w)` map workers 0/1/2/3 to Lookup/Math/Code/Code, and let
`F(c,j)` be the reference endpoint family for node `j` of cell `c`. Other
nodes are held at the construction-frozen deployable assignment `d`.

### 6.1 Family stake

For each node, construction freezes:

```text
w_family(c,j) = best worker whose family equals F(c,j)
w_wrong(c,j)  = best worker whose family differs from F(c,j)
```

Qualification evaluates:

```text
Delta_family(c,j)
  = Acc_Q(d with node j := w_family)
  - Acc_Q(d with node j := w_wrong)
```

This replaces the old undifferentiated “best versus runner-up” rule, under
which the other Code worker could make a strongly learnable
Code-versus-non-Code decision appear stake-free.

A composite position is family-qualified when the point difference is at
least 10 percentage points and its paired sequential confidence lower bound
is above zero, alongside the cell-level gates.

### 6.2 Within-Code model stake

For every Code node, construction freezes:

```text
w_scale(c,j) = best of workers {2,3}
w_alt(c,j)   = the other Code worker
```

Qualification evaluates the frozen direction:

```text
Delta_scale(c,j)
  = Acc_Q(d with node j := w_scale)
  - Acc_Q(d with node j := w_alt)
```

For C2-compat, construction additionally freezes the same comparison within
each public renderer stratum:

```text
Delta_scale_compat(c,j,r)
  = Acc_Q,r(d with node j := w_scale(c,j,r))
  - Acc_Q,r(d with node j := w_alt(c,j,r))
```

The renderer-aggregated positions can establish task/node C2 directions.
Renderer-stratified positions can establish only C2-compat directions.

**Recommended materiality rule — REVIEW CHOICE:** a Code position is
scale-qualified when the point difference is at least 10 points and the
paired sequential lower bound is above zero.

If family stake passes but scale stake does not, the cell may remain in C1.
Worker 2 versus 3 is then a nuisance/equivalent choice at that position and
is excluded from C2 metrics. The full four-id action contract remains
unchanged; there is no hidden action override.

### 6.3 Best-fixed Code and public model router

The Stage-2 mixture is not chosen opportunistically from qualification.
Construction freezes controls for both preregistered possible mixtures:

1. the five-cell Core mixture (all atomic cells plus both chains); and
2. the same Core mixture plus fork/join.

Qualification may activate the second branch only by the frozen fork gates.
For each possible mixture, construction computes:

- `c_fixed ∈ {2,3}`: one construction-selected Code worker used at every
  Code position, with Lookup/Math family routing fixed correctly;
- `s(c,j) ∈ {2,3}`: construction-selected `(cell_id,node_id)` Code mapping,
  forbidden from conditioning on renderer, private values, qualification
  outcomes, or realized success;
- `s_compat(c,j,r)`: construction-selected compatibility mapping that may
  additionally condition on one of the three public renderer grammars; and
- a renderer-only ablation and one frozen shallow public/text router.

Thus the applicable `c_fixed` and router are already persisted before
qualification; qualification selects a preregistered branch, never causes an
argmax to be recomputed on a newly chosen support.

The construction rules are exact:

```text
s(c,j)          := w_scale(c,j)
s_compat(c,j,r) := w_scale(c,j,r)
```

Each right-hand side is the winner of the paired terminal contrast in §6.2
with every other node held at `d`; it is not a joint search over arbitrary
router tables. `c_fixed` is the argmax over exactly two candidates—use worker
2 at every Code position or worker 3 at every Code position—under the
mixture objective below. All ties go to worker 2. Construction persists
separate Core and Core+fork artifacts containing their candidate scores,
tie decision, mapping, source bundle, and recomputable argmax. The fitted
shallow tree and renderer-only table never enter this argmax.

Mixture objectives weight cells equally, latent clusters equally within
cell, and renderers equally within latent. The Stage-2 sampler implements the
same equal-cell target.

Qualification reports:

```text
Delta_router
  = Acc_Q(family-correct routing + s(c,j))
  - Acc_Q(family-correct routing + c_fixed)

Delta_compat
  = Acc_Q(family-correct routing + s_compat(c,j,r))
  - Acc_Q(family-correct routing + s(c,j))

Delta_compat_fixed
  = Acc_Q(family-correct routing + s_compat(c,j,r))
  - Acc_Q(family-correct routing + c_fixed)
```

C2/C2-compat headroom exists only if:

1. at least one qualified public context favours worker 2 and another favours
   worker 3;
2. the relevant construction-frozen mapping uses both workers and beats
   `c_fixed` with the multiplicity-adjusted paired lower bound above zero;
   and
3. scale-specific cold start later contains direct gradient-bearing groups
   in both admitted directions.

Qualification records task/node environmental headroom when `s(c,j)` meets
these conditions and compatibility environmental headroom when `s_compat`
meets them. The learned branch is activated later by the selected prompt's
claim-specific headroom under §9's fixed priority. C2-compat is therefore
available only when the full task/node learned-claim branch is not activated.
It means renderer-conditioned model compatibility within the three tested
grammars. It is still model selection from public language, but it does not
support a semantic or unseen-template claim. Renderer-only/shallow controls
determine how elementary that compatibility rule is; they do not erase an
honestly labelled C2-compat result. Compatibility environmental headroom
specifically requires `Delta_compat_fixed`—not merely `Delta_compat`—to have
lower bound above zero.

The shallow routing control is frozen before construction: one
`DecisionTreeClassifier` with the repository-pinned scikit-learn version,
`max_depth=3`, `criterion="gini"`, `min_samples_leaf=5`, and
`random_state=0`.

For every Code position and construction observation, its training label is
the winner of the paired terminal contrast in which only that position
changes from worker 2 to worker 3 and every other node remains at `d`. Ties
go to the lower worker id. Local-node correctness is retained as a
diagnostic but cannot replace this terminal-effect label.

The semantic shallow router is renderer-free. Its exact input columns and
one-hot level order are `cell_id`, semantic `node_id`, observable subtype,
then public numeric `[p,q,t,k,i]` with missing value `-1`. Separate Core and
Core+fork fitted artifacts are frozen. `renderer_id`, handles, names,
private strata/values, split id, and realized qualification outcomes are
excluded. The compatibility router `s_compat` is the explicit
`(cell_id,node_id,renderer_id)` table. The renderer-only ablation uses only
`renderer_id` with the same construction-only label/tie rule.

Only renderer-free `s` can activate task/node-conditioned C2.
`s_compat` can activate only C2-compat. The renderer-only and shallow routers
are explanatory controls: they may show that an admitted mapping is simple,
but cannot independently activate a learned claim or become an alternative
post-qualification selection path. No additional router is invented after
construction output.

### 6.4 Stage-2 policy scale lift

For each sampled or deterministic policy action, construct its paired
best-fixed-Code collapse: replace every selected worker 2/3 at a Code
position with `c_fixed`, leaving wrong-family selections and all other
positions unchanged.

```text
ScaleLift(policy)
  = E[Y(action_policy)
      - Y(collapse_code(action_policy, c_fixed))]
```

The complete cached surface makes this counterfactual observable without
another worker call. It isolates the incremental value of the policy's
2-versus-3 decisions from family routing. It uses the full admitted
Stage-2 mixture with renderer-within-latent, latent-within-cell, and equal
cell weights; it is not restricted to model-accuracy-eligible observations.

Malformed actions contribute terminal correctness 0 to the full-population
policy metric and 0 to both members of this paired scale contrast; they never
enter a schema-valid-only denominator silently. Family/model selection
accuracy likewise counts malformed or wrong-length actions as incorrect, with
schema validity reported separately.

### 6.5 Active target and selection-accuracy denominators

The Stage-2 Addendum freezes exactly one target function when model routing
is eligible:

```text
target_model(i,j) =
  s(cell(i),j)                         under ModelGO_tasknode
  s_compat(cell(i),j,renderer(i))      under ModelGO_compat
```

The eligible units are qualification-passed Code positions in the first
case and qualification-passed Code-position×renderer strata in the second.
This same function defines cold-start directions, direct-gradient groups,
pilot accuracy, headline accuracy, and all model-selection cuts.

For one policy completion on observation `i`:

```text
FamilyAcc_i =
  0, if malformed or wrong length;
  mean_j 1[family(action_j) = F(cell(i),j)], otherwise.

ModelAcc_i =
  0, if malformed or wrong length and i contains an eligible model unit;
  mean over eligible Code slots j in i of
      1[action_j = target_model(i,j)], otherwise.
```

Observations with no eligible model unit are absent from the model-accuracy
denominator, not scored as successes. Aggregate each metric renderer-within-
latent, latent-within-cell, then equally across eligible cells. Cold-start
completion means use the same rule before group and cell averaging. A raw
slot denominator is forbidden because it would overweight fork and cells
with more eligible Code slots.

The deployable family target and active model target have selection accuracy
1 by definition. Thus the prompt headroom quantities in §10.3 are `1 -
untrained selection accuracy`; terminal headroom remains deployable terminal
accuracy minus untrained terminal accuracy.

### 6.6 Hierarchy

The best one-call whole-task worker/treatment among the four logical workers
is construction-selected and frozen:

```text
Delta_hierarchy(policy)
  = Acc(trained composed policy)
  - Acc(frozen best one-call worker/treatment)
```

The deployable-oracle-versus-one-call gate establishes environmental
headroom. Only the trained-policy gap supports C3. Calls, tokens, latency,
and the harness-only union-payload advantage are disclosed. C3 averages only
the admitted composite cells—both mandatory chains and fork if admitted—
with equal cell weights; atomic cells do not enter a hierarchy estimand.

---

## 7. Gate table and four-worker deltas

All inherited numeric cell gates remain unless explicitly amended here.
Qualification always evaluates construction-frozen candidates.

| gate | active threshold/interpretation |
|---|---|
| untyped infrastructure, request-binding, cache, or trace failures | exactly 0; abort rather than reward |
| generation token-cap truncation | sequential upper bound <2% per `(cell, logical worker)` on that cell's on-contract reference calls |
| selected-route syntax/artifact failure | construction-frozen deployable route sequential upper bound <2% per cell overall and per selected logical worker within cell |
| unselected-route syntax and semantic tool failures | ordinary payoff outcomes; report per worker/cell/node/renderer/subtype |
| atomic correct-family accuracy | ≥75% |
| atomic family margin | frozen correct-family worker minus frozen best wrong-family worker: lower bound ≥20 points |
| two-step deployable success | ≥65% |
| deployable vs best one-call worker/treatment among four | lower bound ≥+20 points |
| corruption intervention | baseline minus corrupted lower bound ≥20 points per edge |
| counterfactual consistency | recomputed-sink accuracy equivalent to unmutated within ±10 points |
| old-answer persistence | sequential upper bound ≤10% |
| composite family stake | point ≥10 points and lower bound >0 per learnable position |
| Code model stake | recommended point ≥10 points and lower bound >0 per C2 position |
| reference vs generic subtasks | ≥+10 points; gates Stage 3, not Stage 2 |
| fork leaf capability | ≥80% |
| fork deployable success | ≥60% |
| fork deployable vs best 32-workflow two-call shortcut | ≥+15 points |
| fork branch corruption | baseline minus corrupted lower bound ≥20 points per branch |

### 7.1 Gate applicability and denominators — **REVIEW CHOICE**

“All required gates” means the following fixed matrix, not every row of the
table applied to every cell:

| cell | mandatory admission gates | C1 positions | C2 positions |
|---|---|---|---|
| `lookup_atomic` | atomic capability, family margin, selected-route protocol | `n1` | none |
| `math_atomic` | atomic capability, family margin, selected-route protocol | `n1` | none |
| `code_atomic` | atomic capability, family margin, selected-route protocol | `n1` | optional `n1` |
| `lookup_math` | two-step deployable, deployable versus best one-call worker/treatment, selected-route protocol, `n1→n2` corruption/consistency/persistence | `n1,n2` | none |
| `math_code` | two-step deployable, deployable versus best one-call worker/treatment, selected-route protocol, `n1→n2` corruption/consistency/persistence | `n1,n2` | optional `n2` |
| `fork_join` | fork leaf capability, fork deployable, deployable versus 32-workflow shortcut, selected-route protocol, both branch corruption/consistency/persistence gates | all three nodes | optional Code leaf |

Every named C1 position must also pass its family-stake rule. An optional C2
position affects only C2 eligibility, never C1 admission. Atomic cells have
no hierarchy or intervention gate. Reference-versus-generic subtasks remains
a Stage-3 diagnostic, not a Stage-2 admission gate. Failure of any mandatory
gate excludes that cell; failure of any of the five mandatory Core cells
makes Core NO-GO. Fork failure leaves the five-cell Core branch intact.

Protocol-gate rows have one scientific denominator:

```text
one registered private observation
× one intended semantic reference node
× one logical worker
× one independent reference-node execution
```

The predecessor context, when needed, is the reference-gold predecessor
output—not output from a candidate whole workflow. Each row counts once
irrespective of cache reuse, request de-duplication, control membership, or
the number of complete assignments that consume it. The latent program is
the resampling unit. “On-contract” means the logical worker family matches
the intended node family; all on-contract rows feed per-worker truncation
telemetry. “Selected route” substitutes the jointly construction-frozen
deployable worker for that node.

Protocol gates never pool cells. At each cell's own look schedule:

- truncation is gated per logical worker that has on-contract nodes in that
  cell, with exactly `3 × number_of_on_contract_nodes` rows per latent;
- selected-route syntax is gated once for the cell overall, with exactly
  `3 × S` rows per latent, and once for every logical worker selected by `d`
  in that cell, with exactly `3 × selected_nodes_for_worker` rows per latent;
  and
- cross-cell/global rates and renderer marginals are descriptive only.

This keeps the cluster-any exact bound in §8.3 tied to a fixed registered
row count per latent and prevents ordinary/fork look schedules or topology
arity from changing its estimand.

Qualification artifacts must retain, for every such row, intended
reference-node correctness, whether a nonterminal output coincidentally
equals the final answer, renderer, public subtype, and terminal composition
result. This preserves the distinction between executing the assigned node
and solving the whole problem accidentally.

### 7.2 Parse-gate amendment — **REVIEW CHOICE**

The old `<2% artifact parse failure/truncation per endpoint` rule is not
silently pooled or waived. The pivot intentionally retained two Code workers
whose typed protocol failures may be complementary and therefore part of the
routing treatment.

This draft recommends:

1. untyped infrastructure and binding failures must be zero;
2. token-cap truncation remains below 2% per `(cell, logical worker)` with
   on-contract support;
3. on the jointly selected construction-frozen deployable route, syntax and
   artifact failure has sequential upper bound below 2% for the cell overall
   and for every logical worker selected within that cell;
4. typed failures on candidates/strata the frozen route does not select
   remain visible `0.5` payoff evidence and may constitute routing signal;
5. semantic tool rejections remain under terminal capability/stake gates
   rather than the syntax gate; and
6. every logical worker's full on-contract failure telemetry is reported
   regardless of selection.

This means C2 may be learned partly as prompt/protocol compatibility. That is
consistent with a worker as a model–prompt–contract endpoint, but must not be
reported as pure reasoning-capability selection.

The rejected alternatives are a pool-wide average, which can hide a broken
selected worker, and a universal per-worker syntax gate on strata where that
worker is deliberately not deployed, which can exclude the complementarity
the pivot was created to study.

### 7.3 Infrastructure retries and descriptive cascade

Infrastructure retries and semantic cascade calls are different operations.
Before CE1, freeze `INFRA_RETRY_CODES`, maximum attempts, backoff, and trace
identity for transport/OOM/incomplete-call failures. An exhausted
infrastructure retry aborts the affected gate surface; it never becomes a
model outcome. The exact list is deliberately not guessed in this draft.

The descriptive cascade executes worker 2 first and retries worker 3 exactly
once only for the frozen `SYNTAX_REJECTION_CODES` set:

```text
E_NO_ARTIFACT, E_MULTI_ARTIFACT, E_UNCLOSED_ARTIFACT,
E_UNEXPECTED_TAG, E_PARSE, E_NONCANONICAL_INT, E_DEPTH
```

It never retries a successfully executed but wrong result or a semantic tool
rejection. Both calls, fingerprints, cache events, wall time, and physical
call cost are retained. It is not a fifth worker, is not reachable through
the routing schema, and cannot establish one-shot public predictability.

---

## 8. Qualification inference

### 8.1 Registered populations and looks

Generate/register the maximum deterministic population before the first
qualification worker call, then reveal only immutable prefixes:

- ordinary cells: 100, 300, 500 latent clusters;
- fork/join: 100, 200 latent clusters;
- all three private renderers at every look; and
- the exact paired visible slice in §4.1.

At a look:

- a conclusively failed required gate stops that cell as failed;
- all required gates conclusively passing admits it;
- otherwise expand to the next look; and
- unresolved at the cap means no admission.

No partial-look peeking, outcome-driven retry, model rerun, refit, or
reselection is permitted. Only preregistered infrastructure retry codes may
repeat a call; model outcomes are immutable under greedy decoding.

### 8.2 Sequential alpha spending — **REVIEW CHOICE**

For didactic simplicity, this draft recommends Bonferroni spending within
each gate:

- ordinary schedule: one-look tail alpha `0.05 / 3`;
- fork schedule: one-look tail alpha `0.05 / 2`;
- one-sided gates use that tail alpha;
- two-sided descriptive/equivalence intervals divide it across both tails;
  and
- family position-classification gates additionally divide their one-look
  alpha by the number of positions tested within that cell;
- model-position classification splits its tail alpha across semantic and
  compatibility claim families. Within the semantic family it then
  Bonferroni-divides across every preregistered Code position: two for Core
  and three for Core+fork. Within the compatibility family it divides across
  every Code-position×renderer stratum: six for Core and nine for Core+fork.
  This protects the bidirectional “at least one worker-2 and one worker-3
  public region exists” claim across cells rather than correcting only
  within a favourable cell or renderer.

Admission is an intersection-union decision—every required component must
pass—so no extra correction is applied across distinct required gates.

The aggregate Core or Core+fork router contrast is evaluated once, only after
every applicable cell has reached its terminal look. It uses the
construction-frozen artifact for the activated branch, equal cell weights,
and a one-sided `0.05/2` tail for each of `s` and `s_compat`. It is not
repeatedly tested at the incompatible ordinary/fork look schedules. Only one
of Core and Core+fork is activated by the already-frozen fork branch; the
other stays descriptive. `s` has semantic priority; `s_compat` can activate
only the separately labelled compatibility claim.

Decision rules:

- lower-bound gate passes iff `LCB ≥ threshold`, fails iff
  `UCB < threshold`, otherwise inconclusive;
- strict upper-bound gate passes iff `UCB < threshold`, fails iff
  `LCB ≥ threshold`, otherwise inconclusive;
- non-strict upper-bound gate uses `≤`/`>`;
- equivalence within ±10 points passes only when the full sequential interval
  lies inside `[-0.10, 0.10]`, fails when it lies wholly outside, otherwise
  inconclusive.

### 8.3 Intervals, cluster bootstrap, and weighting

Except for the rare-event upper bounds below, use a 10,000-replicate paired
percentile cluster bootstrap. For a single-cell statistic, a replicate
samples that cell's `N_c` latent ids with replacement and carries every
renderer and compared-arm row. For any equal-cell mixture statistic, it
independently resamples `N_c` latents **within each cell**, computes the
cell-level statistic, then equally averages cells. It never pools latent ids
across cells with different look sizes or topology arities. This same
cell-stratified construction governs aggregate routers, policy-dev headroom,
the pilot, final C1/C2/C2-compat/C3 contrasts, and equal-cell controls.
Endpoints use `numpy.quantile(method="linear")` at the tail levels in §8.2.
Seed:

```text
SHA256(population_manifest_sha256 | gate_id
       | canonical_cell_look_vector | "bootstrap-v1")
```

Pin NumPy/Python versions, `PCG64`, implementation source hash, and quantile
method in the execution manifest. Never redraw or omit a replicate. Before
CE1 can freeze, a deterministic simulation battery spanning the planned
qualification looks, cell-stratified aggregate-router path, `pilot_gate`
`n=12/cell`, final test `n=56/67 per cell`, three-policy within-observation
mean, renderer correlations, gate boundaries, unequal intervention
eligibility, and zero/near-zero event rates must be reviewed. Each frozen
scenario uses 10,000 Monte Carlo trials and passes only when the 95% Wilson
upper bound on miscoverage is no greater than
`nominal_alpha + max(0.005, 0.25 × nominal_alpha)`. This is a bounded
catastrophic-undercoverage screen, not a claim that simulation proves the
interval exact. The scenario grid, seed,
acceptance result, and any exact-method exemption are review artifacts, not
an invitation to choose whichever method passes observed construction data.

Ordinary percentile bootstrap gives a false upper endpoint of zero when no
rare event was observed. Therefore:

- truncation and selected-route syntax use a one-sided exact
  Clopper–Pearson upper bound on the latent-level indicator that **any**
  registered denominator row in that cluster failed; because each row-level
  failure fraction is no greater than this indicator, the bound is a
  conservative upper bound for the registered row rate;
- old-answer persistence retains the full eligible-observation ratio as its
  primary estimand. Its upper gate uses a conservative exact envelope:
  Clopper–Pearson bounds the probability of any persistence event and, where
  eligibility is not structurally constant, the probability of any eligible
  row. With at most `m` eligible rows per cluster, the envelope is
  `min(1, m × U_CP(any_event) / L_CP(any_eligible))`; when every cluster has
  exactly `m` eligible rows it simplifies to `U_CP(any_event)`. The tail
  alpha is split across numerator and denominator bounds; and
- the original row/eligible-observation rate, counts, and cluster-any rate
  are always reported alongside the operational bound.

If the conservative envelope is unresolved at the cap, the gate is
unresolved. It is never replaced by a zero-width bootstrap interval.

Weighting:

- oracle/control terminal accuracy: mean within latent across renderers,
  then equal mean across latent clusters within cell; any mixture then
  equally averages cells;
- paired terminal contrasts: identical clusters/observations and weights;
- interventions (§1.9): primary statistic is the full eligible-observation
  ratio; the bootstrap resamples latent clusters and recomputes that ratio;
  equal-cluster values are reported only as the frozen secondary quantity;
- intervention eligibility fraction accompanies every estimate;
- follow-through remains secondary and never replaces full-sample
  counterfactual consistency; and
- collision/sensitivity uses the headline population and its frozen cluster
  weights.

Undefined-replicate rules:

- retain zero-eligible clusters in the sampling population;
- observed zero eligibility makes the gate non-estimable and therefore
  non-admitted;
- a bootstrap replicate with zero eligible observations receives the
  gate-adverse extreme and is counted/reported, never redrawn;
- zero-followed replicates are counted; conservative follow-through bounds
  complete the undefined lower ratio as 0 and upper ratio as 1; and
- for a lower-bound success/difference/corruption gate an undefined
  replicate contributes `-∞`; for an upper-bound failure gate it contributes
  `+∞`; and for an equivalence interval it contributes the adverse endpoint
  on each side.

Persist per-cluster sufficient statistics so every interval can be
re-derived from the artifact.

---

## 9. Stage-1 verdict and branch rules

Qualification first produces a headroom verdict, not the final cold-start
verdict. After the terminal qualification look, classify:

- **failed cell:** a core capability, hierarchy, causal-use, or family gate
  fails;
- **family-only position/cell:** core and family gates pass, but Code model
  stake fails;
- **family+scale position/cell:** core, family, and frozen-direction model
  gates pass.

```text
Core mixed GO
  iff the preregistered minimum cells/topologies pass C1 gates.

Task/node model headroom
  iff Core mixed GO
  and renderer-aggregated qualified positions favour both workers
  and s uses both
  and Delta_router has its adjusted lower bound > 0.

Compatibility model headroom
  iff Core mixed GO
  and renderer-stratified qualified positions favour both workers
  and s_compat uses both
  and Delta_compat_fixed has its adjusted lower bound > 0.
```

After the reward-bearing cold start selects prompt treatment `t*`, apply the
frozen priority using the complete prompt-specific predicates in §10.3:

```text
ModelGO_tasknode
  iff C2_headroom(t*).

ModelGO_compat
  iff not ModelGO_tasknode
  and C2compat_headroom(t*).
```

Exactly one of `ModelGO_tasknode`, `ModelGO_compat`, or model NO-GO is carried
into the Stage-2 Freeze Addendum. If model NO-GO, the experiment proceeds
only when `C1_headroom(t*)` supplies the C1 branch. C2-compat is never
shortened to C2.

### 9.1 Minimum mixed cell set — **REVIEW CHOICE**

Recommended minimum:

- all three atomic cells;
- both two-step cells; and
- fork/join optional, admitted only if every fork gate passes.

This preserves the intended family composition and hierarchy question.
Failure of either two-step cell is Core NO-GO rather than silently changing
the mixed task after qualification. Fork remains a separately reported
parallel-DAG extension.

### 9.2 Branches

1. **Core + `ModelGO_tasknode`:** run the four-worker Stage-2 development
   signal; C1 and C2 are eligible subject to prompt-specific headroom.
2. **Core + `ModelGO_compat`:** run the same design with renderer-stratified
   truth labels; C1 and C2-compat are eligible subject to prompt-specific
   headroom.
3. **Core GO, model NO-GO:** retain the four-worker schema and permit one
   explicitly C1-only development signal. Worker-2/worker-3 behavior is
   reported as a null/nuisance; aggregate gain cannot support C2. The clean
   follow-up is the deferred `107_s` Code-only discovery/positive-control
   branch.
4. **Core NO-GO:** stop before Stage 2. Any redesign gets a new plan and new
   qualification population.

**REVIEW CHOICE:** the alternative for branch 3 is a new three-worker launch.
This draft recommends the honest four-worker C1 path: one disposable
development seed and, if its C1 pilot passes, three fresh C1 headline seeds.
Worker 2/3 remains a measured nuisance. `107_s` is the separate model-routing
follow-up; it does not replace the C1 replication rule.

Qualification never selects a more favourable branch after seeing Stage-2
training.

---

## 10. Stage-2 prompt treatment and cold start

Stage 2 remains routing-only. The policy sees the fixed reference workflow
and emits only:

```json
{"worker_ids": [0, 3, 1]}
```

It never emits subtasks, topology, resources, or access. Worker ids remain
opaque; model names, sizes, and family labels are absent.

### 10.1 Frozen prompt candidates

Before `policy_dev` output:

1. **few-shot:** exact Stage-0 prompt and four executable demonstrations;
2. **schema-only:** identical instructions, observation skeleton, and output
   contract with the demonstrations removed—no replacement task examples.

Both prompt bytes, the comparison schedule, tokenizer/chat template,
generation seeds, and decision rule are frozen first.

This document makes the targeted cell-spec erratum that registers
`policy_dev` with deterministic indices 0–999 per cell and a fail-closed cap
of 1,000. Its cohorts are disjoint:

| indices per cell | role |
|---:|---|
| 0–23 | reward-blind format cohort A |
| 24–47 | fresh reward-blind cohort B, used only after the one permitted format repair |
| 48–999 | reward-bearing cold-start candidates |

One deterministically balanced renderer is used per format latent. The
format path draws exactly one sampled completion per observation per prompt
candidate—never a group of eight—using the frozen policy sampling settings
and seeds. It does not load a payoff surface and may report only JSON/schema
validity and action-array length. Cohort A therefore costs `24 × C × 2`
policy generations: 288 for six cells or 240 for five. A candidate may
receive only the exact
`FORMAT_REPAIR_V1` transformation whose bytes, trigger, and bounded
text-to-text operation are included in the CE1 freeze; if none is frozen, no
repair is allowed. A repaired candidate is rehashed and reruns the complete
paired probe on fresh cohort B at the same additional cost, with cohort A
retained. No routing choice,
worker result, terminal, or reward may inform that repair.

### 10.2 Cold-start population

Use a dedicated `policy_dev` namespace and the exact Stage-2 model,
tokenizer, untrained QLoRA initialization, parser, temperature 1.0, group
size 8, and pre-materialized outcomes. Perform no optimizer updates.

Before any reward-bearing policy output is generated, select and hash the
support from indices 48–999 using only cell, topology, renderer, semantic
node, and the already-frozen public scale-direction strata. Individual rows
may not be selected because their payoff surface happens to disagree.

For each prompt treatment, schedule 72 unique one-group-per-observation rows
per admitted topology class. Then, for each admitted model-stake direction,
add unique rows until that direction has 72 groups. A row may count toward
both its topology and direction target, but is executed once; the support
manifest records every overlap. Every group uses a distinct latent cluster
within a treatment. Renderer variants are balanced across different latents
rather than treating three renderings of one latent as independent groups.
The same observation identities, payoff surface, group order, and sampling
seeds are used for both prompt treatments. A group is one observation with
eight sampled completions.

The minimum reward-bearing comparison therefore costs:

```text
admitted topology classes × 72 groups × 2 prompts × 8 completions
```

before unique rows added for a direction not already covered. With atomic,
chain, and fork admitted, the minimum is 3,456 policy generations.

Per treatment/topology/direction report:

- schema validity and correct action length;
- reward frequencies;
- non-zero-variance groups;
- groups containing both 1.0 and a lower reward;
- direct model-gradient groups containing worker-2 and worker-3 actions under
  the same otherwise family-correct assignment with distinct payoff;
- worker frequency and entropy by position;
- family and model selection;
- terminal reward and signed deployable gap; and
- renderer, cell, and semantic-subtype cuts.

Inherited gates:

| property | gate |
|---|---:|
| schema validity | ≥80% |
| non-zero-variance groups | ≥25% |
| groups containing 1.0 and lower | ≥10% |

For each candidate and each applicable active-target direction from §6.5,
require both Code workers to appear and at least 10% of groups to be direct
model-gradient groups. Family variance cannot substitute for model variance.
Every inherited gate is evaluated separately within each prompt candidate,
admitted topology, and target direction; pooled success cannot rescue a
failing stratum. A failing non-selected prompt does not veto a different
candidate that independently passes and is selected by §10.3.

### 10.3 Prompt-selection rule — **REVIEW CHOICE**

Recommended rule:

For each treatment `t` that passes every applicable cold-start variance and
format gate, derive its eligible **learning-claim** set:

```text
C1_headroom(t)
  iff Core mixed GO
  and deployable terminal accuracy - untrained_t terminal accuracy ≥ 0.05
  and 1 - untrained_t family selection accuracy ≥ 0.10.

C2_headroom(t)
  iff Task/node model headroom
  and both task/node cold-start directions pass for t
  and 1 - untrained_t task/node model selection accuracy ≥ 0.10.

C2compat_headroom(t)
  iff Compatibility model headroom
  and both renderer-stratified cold-start directions pass for t
  and 1 - untrained_t compatibility model selection accuracy ≥ 0.10.
```

Selection is a frozen priority over claim sets, not a generic family-ceiling
test:

1. prefer a treatment with C2 headroom;
2. otherwise prefer one with C2-compat headroom;
3. otherwise prefer one with C1 headroom;
4. within the same highest rung, prefer few-shot as the paper-like treatment;
   and
5. if neither treatment retains any eligible claim, stop for a new
   launch-profile review.

Thus near-ceiling family routing does not disqualify few-shot when it still
has model-routing headroom. Conversely, a treatment from which none of the
registered learning claims can improve is not trained merely because its
JSON is valid. The selected treatment's complete eligible learning-claim
set—not only its highest-priority claim—is frozen in the Stage-2 Addendum;
C3 eligibility is added deterministically by §12.4. Do not tune
demonstrations on these rewards.

The matching untrained prompt is mandatory for the trained condition. If
few-shot is primary, trained few-shot versus untrained few-shot is the
paper-like comparison. If schema-only is primary, trained versus untrained
schema-only is primary and untrained few-shot quantifies the demonstration
prior on policy-dev and as a descriptive extra pass on the same final test.
V1 does **not** train the non-primary prompt. A later prompt-treatment
ablation requires its own reviewed plan and fresh headline seeds.

Every headroom statistic uses every sampled completion: mean within group,
equal mean over distinct policy-dev latents within cell, then equal mean over
the five Core cells (and over six only in the preregistered Core+fork branch).
It is not an equal-topology mean, which would overweight fork relative to the
Stage-2 target.

---

## 11. Stage-2 populations and immutable payoff surfaces

### 11.1 Population formula

Under the minimum-set rule in §9, `C=5` for the Core mixture or `C=6` when
fork/join is separately admitted. No other qualification-selected subset is
an active Stage-2 mixture.

Recommended allocation:

| split | latent clusters | rendered observations used | purpose |
|---|---:|---:|---|
| train | 100 per admitted cell | one deterministically balanced renderer per cluster, `100C` total | one prompt group per cluster |
| `dev_select` | first 24 dev clusters per cell | all three renderers, `72C` total | checkpoint selection only |
| `pilot_gate` | next 12 dev clusters per cell | all three renderers, `36C` total | one continuation decision only |
| test | `ceil(1000/(3C))` per admitted cell | all three renderers, approximately 1,000 total | one final evaluation |

The train renderer scheduler is frozen and gives each renderer counts
differing by at most one within cell. Unused renderings of a training latent
do not enter dev/test. Dev/test full crossing supports renderer cuts and
clustered inference.

The two dev cohorts are disjoint, registered before training, and together
use 36 latent clusters per cell. `pilot_gate` is not inspected at any
checkpoint-selection step.

With all six cells:

- train: 600 observations;
- `dev_select`: 432 observations;
- `pilot_gate`: 216 observations;
- test: 1,008 observations; and
- training updates: `ceil(600/2) = 300`.

With the five-cell Core branch:

- train: 500 observations;
- `dev_select`: 360 observations;
- `pilot_gate`: 180 observations;
- test: 1,005 observations; and
- training updates: 250.

The formulas—not an ad-hoc sample size—determine the exact population and
update count for the already-preregistered Core or Core+fork branch.

These splits measure fresh latent values inside the same three renderer
grammars. They do not support C4.

### 11.2 Complete surfaces

For every scheduled observation, materialize all valid actions:

| topology | rows per observation |
|---|---:|
| atomic | 4 |
| two-step | 16 |
| fork/join | 64 |

The surface manifest binds all identities in §4 plus expected and observed
rows, terminal values, raw completions, trace hashes, physical generation
counts, cache events, wall, VRAM, and disk.

Raw-completion caches and payoff surfaces are distinct artifacts. Surfaces
are immutable and shared read-only across seeds. Re-scoring must reproduce
every terminal payoff before launch.

Train, `dev_select`, and sealed `pilot_gate` surfaces are prepared before the
development signal seed. `pilot_gate` may be read only once, after the
signal checkpoint has been selected on `dev_select`. The test population may
be registered earlier, but its payoff surface and aggregates remain sealed
from human inspection and model-selection code until every headline
checkpoint is frozen. Automated identity/completeness checks may run without
revealing pilot or test performance.

### 11.3 Cached/live parity

Before training, execute a registered stratified sample live—covering all
workers, cells, renderers, topology depths, and both Code-model directions—
and require exact equality with the corresponding cached completion,
WorkerResult, terminal, and reward. This is a parity/sentinel run, not 20
live GRPO updates.

Any return to live Stage-2 workers requires a new benchmark that explicitly
executes worker 3; CE0's reference-route live timing cannot authorize it.

### 11.4 Artifact retirement

| changed dependency | artifacts retired |
|---|---|
| worker checkpoint/prompt/request contract/tool/parser/inference | affected raw completions, node results, payoff surfaces, qualification and Stage-2 results |
| generator/renderer/profile/direct prompt/statistical code | affected populations, controls, selection artifacts, qualification reports, and surfaces |
| policy prompt/parser/format repair | `policy_dev` and Stage-2 policy completions only; it does not retire frozen worker qualification |
| policy training code/hyperparameters | adapters and every policy evaluation from that launch |
| evaluation backend/decoding contract | policy action/result artifacts, but not immutable worker payoffs |

Retirement is transitive through manifest hashes and fail-closed at load.

---

## 12. Stage-2 launch, training, and checkpoint selection

### 12.1 Launch profile

Carry the measured Stage-0 profile unless this plan explicitly changes it:

- `Qwen/Qwen2.5-3B-Instruct` at the frozen revision;
- NF4 double quantization, BF16 compute, gradient checkpointing;
- LoRA rank 16, alpha 32, dropout 0.05, frozen target modules;
- beta `1e-3`, acknowledged as a small objective contribution as well as KL
  telemetry;
- group size 8, rollout temperature 1.0;
- per-device batch 2, gradient accumulation 8, two prompt groups/update;
- learning rate `1e-5`, ten-step warmup, constant schedule;
- current DAPO-normalized GRPO loss and `adamw_torch`;
- policy completion cap 128;
- exactly one scalar `0/0.5/1` reward;
- immutable precomputed-surface outcome mode; and
- complete action/scoring traces with W&B limited to the four online metrics:
  parse rate, reward-level frequencies, zero-variance groups, and
  worker-selection entropy.

No repository default silently supplies a scientific setting.

### 12.2 Schedule

One deterministic pass over the `100C` training observations:

```text
prompt_groups = 100C
groups_per_update = 2
updates = ceil(100C / 2)
```

For six cells this is 600 groups and 300 updates. Each headline seed uses the
same prompt order and payoff surfaces but a different frozen policy
sampling/training seed. Every run starts from the same content-addressed
untrained adapter bytes, which is why the deterministic untrained pilot/test
baseline is one shared condition rather than a seed-specific refit.

Save update 0 and every 25 updates. After training, evaluate those snapshots
on the complete `dev_select` cohort only. Evaluation uses deterministic
policy decoding and cached payoffs.

Primary checkpoint criterion on `dev_select`:

1. lowest full-precision mean signed deployable gap on `dev_select`; and
2. exact tie: earlier checkpoint.

The signed gap is `deployable accuracy - policy accuracy`: lower is better,
and a negative value means the policy outperformed the frozen deployable
mapping. A terminal-accuracy tie-break would be redundant on the same
`dev_select`
population and is therefore not used.

Never select a checkpoint on train reward, qualification, `pilot_gate`, or
test.

If the best `dev_select` checkpoint is the final scheduled checkpoint and the
curve is still improving, report the run as **schedule-censored**. Extending the
schedule is a changed configuration and requires a new development signal
plus three fresh headline seeds. Existing runs remain disclosed but cannot
be relabelled as headline evidence for the extension.

### 12.3 Evaluation path — **REVIEW CHOICE**

Recommended simple path:

1. save the untrained adapter and adapter snapshots every 25 updates;
2. do not interleave `dev_select` generation with training, so evaluation cannot
   perturb rollout RNG, optimizer state, or memory;
3. after training closes, load one policy checkpoint at a time in a fresh
   single-GPU process and evaluate all snapshots sequentially on
   `dev_select`;
4. freeze the best checkpoint by §12.2; and
5. after all headline checkpoints are frozen, evaluate those adapters
   sequentially on the sealed test surface.

The first implementation unit probes the training-compatible Transformers
loader against a vLLM-served LoRA on the frozen Stage-0 observations.
Choose the simpler Transformers path if it passes exact parsed-action parity,
reward parity, <22 GiB, and the dev-evaluation budget. Otherwise select vLLM
in the Stage-2 Freeze Addendum; do not maintain two headline engines.

The selected evaluation contract explicitly pins:

- backend/library versions and adapter hash;
- `world_size=1` and no second resident model;
- `do_sample=False`;
- top-p/top-k/temperature disabled rather than inherited;
- max prompt tokens and `max_new_tokens=128`;
- EOS, PAD, chat template, stop behavior, and left/right padding;
- inference dtype, batch cap, and deterministic settings; and
- the exact parser/reward/surface manifests.

The matching untrained baseline uses the same evaluator. An acceptance test
also requires exactly `updates × 2 × 8` training completion traces under the
single-GPU TRL configuration.

### 12.4 Development signal and headline seeds — **REVIEW CHOICE**

Before this seed, the Stage-2 Freeze Addendum deterministically activates
every eligible claim:

- C1 iff the selected prompt has `C1_headroom`;
- C2 iff it has `C2_headroom` and the branch is `ModelGO_tasknode`;
- C2-compat iff it has `C2compat_headroom` and the branch is
  `ModelGO_compat`; and
- C3 iff Core mixed GO passed its mandatory composite hierarchy gates.

It binds that complete set and the resulting final-test multiplicity `K`.
C2 and C2-compat are mutually exclusive. No eligible claim may be omitted to
reduce `K`. The pilot controls continuation only; it cannot add, remove, or
swap an active claim.

Run one disposable development signal seed first. It is **never** a headline
seed, even if the configuration remains unchanged. Select its checkpoint
only on `dev_select`, then reveal that checkpoint once on disjoint
`pilot_gate` together with the matching untrained policy. At one-sided alpha
`0.05 / K_pilot`, where `K_pilot` is the number of active learning claims
among C1 and the one model-routing claim (one or two), continue only when all
common requirements and at least one **active** sibling learning-signal rule
passes. Intervals use the §8.3 cell-stratified paired bootstrap; common
requirements are conjunctive and do not create an additional union test.

Common requirements:

- zero infrastructure failure represented as reward; and
- schema-valid, correct-length actions ≥80% on `pilot_gate`.

C1 signal, only when C1 is active:

- terminal accuracy minus the matching untrained policy has paired LCB >0;
  and
- family-selection accuracy improves by at least 10 points.

C2 signal, only under active `ModelGO_tasknode`, uses renderer-aggregated
qualified positions and target `s(c,j)`. C2-compat signal, only under active
`ModelGO_compat`, uses renderer-stratified qualified positions and target
`s_compat(c,j,r)`. Either requires:

- `ScaleLift` has paired LCB >0; and
- model-selection accuracy against the active §6.5 target improves by at
  least 10 points over the matching untrained policy.

If neither sibling rule passes, stop before headline training. If either
passes and the launch remains byte-for-byte unchanged, run **three fresh,
preregistered headline seeds**. A positive active C1 pilot therefore
authorizes a properly replicated active C2/C2-compat null; a positive active
model-routing pilot likewise permits active C1 to remain null. An inactive
claim stays descriptive and is not retroactively called a replicated null.
No subjective curve shape, “unexplained collapse,” topology anecdote, prompt
edit, or replacement seed can rescue the gate. Report the development seed
and every launched headline seed, including failures.

---

## 13. Compute plan on the RTX 4090

Stage 0 measured 14.43 GiB peak for routing-only QLoRA and 8.51 seconds per
optimizer update. The diagnostic complete surface used 124 physical
generations, 51.1 seconds full-command time, and approximately 3.6 MB for one
latent per cell crossed over three renderers.

The retained CE0 trace had no request-SHA overlap between renderers for any
worker. Its measured physical-generation units per latent were 12 for each
atomic cell across three renderers, 24 for each chain, and 40 for fork
(`12/12/16` by renderer). Therefore renderer crossing must not be treated as
free de-duplication. Applying those measured units to §11 gives the
**routing-surface-only** projection:

| branch/split | payoff rows | projected physical worker generations |
|---|---:|---:|
| six-cell train | 10,800 | 4,132–4,136, pending the frozen fork renderer balance |
| six-cell dev (`dev_select` + `pilot_gate`) | 11,664 | 4,464 |
| six-cell test | 18,144 | 6,944 |
| **six-cell total** | **40,608** | **15,540–15,544** |
| five-cell train | 4,400 | 2,800 |
| five-cell dev (`dev_select` + `pilot_gate`) | 4,752 | 3,024 |
| five-cell test | 8,844 | 5,628 |
| **five-cell total** | **17,996** | **11,452** |

At the CE0 rate, the six-cell total is approximately 97.5 minutes of
in-process materialization or 106.7 minutes at full-command wall, with
roughly 451 MB from linear artifact scaling before extra controls. Test work
occurs only after headline checkpoints freeze; train+dev preparation is
approximately 54 minutes in-process. The five-cell total is approximately
72/78 minutes in-process/full-command. These are projections, not a licence
to skip the exact support-plan count and benchmark.

The minimum cold-start support also needs a complete payoff surface before
the policy comparison:

| branch | minimum cold-start payoff rows | physical worker generations | projected in-process/full-command wall |
|---|---:|---:|---:|
| six cells / three topology classes | 6,048 | 1,824 | 11.5 / 12.5 min |
| five cells / atomic + chain | 1,440 | 864 | 5.4 / 5.9 min |

Direction top-ups add unique rows/calls and are counted from the frozen
support manifest. This policy-dev preparation is a separate pre-signal
tranche; workers are unloaded before policy cold start.

If C3 is active, the frozen best one-call B5 treatment adds one union-payload
worker call for each test observation: 1,008 calls in the six-cell branch or
1,005 in Core. These calls are not hidden inside the routing-surface table.
Construction/qualification B1–B6 and cascade arms are likewise outside that
table and must appear explicitly in each Stage-1 support-plan projection.

Training at the measured rate:

| updates | projected training wall |
|---:|---:|
| 250 | 35 min |
| 300 | 43 min |
| 350 | 50 min |

For six admitted cells, total worker preparation plus one 300-update seed is
therefore roughly 97 minutes before policy-evaluation overhead when only the
required train+dev surfaces are prepared. Worker preparation is shared across
seeds; additional seeds pay training/evaluation, not materialization again.

Policy-generation budgets are separate from worker materialization:

| branch | training completions per seed | saved snapshots | `dev_select` greedy generations per seed | paired pilot reveal (trained + untrained) | required final test (3 trained + 1 shared untrained) |
|---|---:|---:|---:|---:|---:|
| six cells | 4,800 | 13 (`0,25,…,300`) | 5,616 | 432 | 4,032 |
| five cells | 4,000 | 11 (`0,25,…,250`) | 3,960 | 360 | 4,020 |

The cold-start minimum is another 3,456 sampled policy completions when all
three topology classes are admitted, before additional direction rows. The
format probe adds 288/240 generations for six/five cells and the same again
only if the frozen repair path runs. When schema-only is selected, the
untrained few-shot demonstration-prior control receives one additional
descriptive test pass, bringing final policy generations to 5,040 or 5,025.

Stage 1 is budgeted separately. The formal 100-per-cell, fully crossed
construction surface is approximately 100 times the diagnostic surface
before baselines. The first 100-cluster qualification look is similar.
Every CE1 tranche records expected and actual calls, wall, VRAM, cache reuse,
and disk before expansion. Do not hide construction/qualification inference
cost inside the Stage-2 per-seed number.

Before the development signal, benchmark the exact registered
train/`dev_select`/`pilot_gate` schedule and recompute:

- first-seed wall including required surface preparation;
- steady additional-headline-seed wall;
- `dev_select` and one-time `pilot_gate` evaluation overhead;
- final test preparation/evaluation;
- peak VRAM by phase;
- physical generations and disk by split; and
- expected total for one development signal seed and three fresh headline
  seeds.

The 4090 execution order is sequential:

1. materialize policy-dev worker surfaces, unload workers, run cold start;
2. materialize train/dev/pilot surfaces, unload workers, train the
   development seed and evaluate snapshots one adapter at a time;
3. reveal trained+untrained pilot together;
4. run and select three fresh headline adapters one at a time; and
5. only after all checkpoints freeze, materialize sealed test routing/B5
   worker results, unload workers, then evaluate untrained and trained policy
   adapters sequentially.

No phase assumes policy and worker models are co-resident.

Gate remains <22 GiB and ≤12 hours for any single required run/tranche.

---

## 14. Controls, metrics, and claim decisions

### 14.1 Required routing controls

All applicable controls use the same observations and cached surface:

1. matching untrained Conductor;
2. exact-uniform four-worker routing;
3. frequency-matched random routing;
4. construction-frozen deployable assignment `d`;
5. family-correct routing with best-fixed Code `c_fixed`, explicitly an
   oracle-family diagnostic rather than a deployable policy baseline;
6. construction-frozen task/node model router `s`;
7. renderer-conditioned compatibility router `s_compat`;
8. renderer-only table;
9. the single frozen depth-3 renderer-free public-feature tree;
10. trained Conductor; and
11. hindsight per-observation oracle, diagnostic only.

For each seed, frequency matching is fixed on `dev_select`, before test. Let
`q_invalid` be the global malformed-action frequency and let `p_0…p_3` be
the global worker marginals over node slots in valid actions, with no
cell/node/renderer conditioning. On each test observation the control is
computed analytically from the complete surface:

```text
(1 - q_invalid) × Σ_valid assignments a [ Π_j p_(a_j) × Y_i(a) ]
```

There is no Monte Carlo noise and no test-set fitting. The same construction
is applied separately to the matching untrained policy.

### 14.2 Carried execution/hierarchy controls

- one constant-assignment control (the historically named “best single
  worker” and “best-fixed assignment” are the same quantity, not two
  baselines);
- best one-call whole-task worker/treatment among four;
- mechanically generated 32-workflow fork two-call shortcut;
- parser-gated worker-2→worker-3 cascade with call cost;
- B1 public-only direct plus majority/echo/shallow controls;
- B2 endpoint without resource;
- B3 visible direct;
- B4 local-node capability;
- B6 generic-subtask workflow where relevant to Stage 3; and
- compute-matched best-of-N where the comparison is well-defined.

Four-worker candidate scope is explicit. B5 selects among all four logical
worker/treatments on construction and evaluates only that frozen winner
thereafter. B2 runs all four logical workers—including both Code
checkpoints—without the resource. B6 changes the subtask wording while using
the construction-frozen four-worker deployable route `d`; it does not
reselect workers under generic instructions. B1, B3, and B4 retain their
cell-spec single-direct-model definitions and are not silently expanded into
new four-candidate searches.

### 14.3 Primary Stage-2 metrics

For every checkpoint/condition:

1. terminal accuracy and mean reward;
2. signed deployable gap;
3. family-selection accuracy;
4. model-selection accuracy against the active §6.5 target on its qualified
   task/node positions or position×renderer strata;
5. ScaleLift relative to best-fixed Code collapse;
6. unique-win capture, clearly labelled hindsight-conditioned unless the
   region was frozen from public factors;
7. selection frequency and entropy by position/stratum;
8. renderer, cell, topology, subtype, and predecessor-access cuts;
9. `0/0.5/1` frequencies and typed failure modes;
10. zero-variance, mixed, and direct model-gradient groups;
11. physical-call cost and cascade cost; and
12. complete train/dev dynamics: reward, regret, KL, loss, gradient norm,
    parse rate, entropy, and schedule index.

Exact worker-id route accuracy is secondary because tied/equivalent workers
can make it misleading.

### 14.4 Headline evaluation and claims

Use each headline seed's best-on-`dev_select` checkpoint and reveal test
exactly once. Report each seed, seed mean/range, and every curve. Do not
present a three-seed asymptotic CI as though `n=3` were large.

The active claim family and `K` were already fixed deterministically in the
Stage-2 Addendum before the development signal (§12.4), not chosen from
headline dev curves. Every claim uses one-sided tail alpha `0.05/K`.
Components within a claim form an intersection-union decision—all must
pass—so they receive no further multiplicity division. Inactive claims
remain descriptive and cannot be added after pilot or test.

Test differences use the §8.3 10,000-replicate paired percentile latent-
cluster bootstrap. The primary multi-seed statistic first averages the three
frozen seed policies within each observation, then resamples latent clusters.
Every learned claim also requires at least two of three seeds to have the
claimed positive point direction.

C1 requires:

- trained versus matching untrained terminal improvement with lower bound >0;
- family-selection improvement of at least 10 points;
- trained terminal accuracy beating exact-uniform and the `dev_select`-frozen
  analytic frequency-matched control, each with lower bound >0; and
- no claim beyond model-plus-tool family routing.

C2 requires:

- `ModelGO_tasknode`;
- trained model-selection improvement of at least 10 points over the matching
  untrained policy against `target_model(i,j)=s(c,j)` on the qualified
  task/node positions;
- ScaleLift lower bound >0 on test; and
- positive ScaleLift in at least two of three seeds.

C2-compat requires:

- `ModelGO_compat`;
- trained model-selection improvement of at least 10 points over the matching
  untrained policy against
  `target_model(i,j)=s_compat(c,j,renderer(i))` on the qualified
  position×renderer strata;
- ScaleLift lower bound >0 on test; and
- positive ScaleLift in at least two of three seeds.

C3 requires trained composed accuracy minus frozen best one-call accuracy to
have lower bound >0, with cost reported. The comparator is the
construction-frozen best one-call worker/treatment among four, evaluated on
the identical test observations. The qualification deployable gap alone is
not C3.

C1's per-seed direction is trained-minus-untrained terminal accuracy; C3's
is trained-composed minus frozen-one-call accuracy. C2/C2-compat use
ScaleLift as stated above. C2-compat is reported only as renderer-conditioned
model compatibility. C4 remains deferred.

---

## 15. Expected learning dynamics and failure modes

Predictions:

1. JSON/action validity saturates first.
2. Large Lookup/Math/Code family margins create the earliest learning signal.
3. Atomic family routing improves before two-step routing; fork is latest and
   may remain sparse at group size 8.
4. Worker entropy falls first at Lookup/Math positions and remains localized
   at qualified Code positions.
5. The most likely intermediate failure is strongest-worker or
   best-fixed-Code collapse.
6. Model routing appears only after family-correct actions are common enough
   for worker-2/worker-3 differences to affect group-relative reward.
7. Gradient-bearing groups rise during acquisition and fall again near the
   plateau.
8. A few-shot prompt may begin closer to the deployable policy but leave less
   observable learning headroom than schema-only.

Named failures:

- uniform `0.5` plateau from valid but wrong assignments;
- zero-variance groups overwhelming group size 8;
- learning family routing while model selection remains null;
- renderer lookup rather than semantic selection;
- collapse to worker 2 or 3 regardless of public task;
- demonstrations encoding most of the measured policy;
- parse/protocol quirks dominating C2;
- fork reward too sparse for a signal seed;
- dev selection noise or late overfitting;
- stale/incomplete payoff surface;
- construction/qualification reselection leakage; and
- treating cached deterministic mistakes as publicly predictable when they
  depend on hidden values.

No result is rescued in place. A frozen branch rule either proceeds, records
the null, or stops for a new design.

---

## 16. Implementation and review units

1. **Plan freeze and targeted specification errata**
   - resolve REVIEW CHOICE items;
   - D4 and `policy_dev` cap/ranges;
   - active four-worker Stage-1 restatement;
   - profile candidates;
   - `SYSTEM_DIRECT`;
   - gate applicability/denominators;
   - exact statistics, two retry lists, and visible slice.
2. **Population and provenance layer**
   - canonical manifests;
   - registered construction/qualification prefixes;
   - complete source/environment binding;
   - fail-closed gate report.
3. **Construction calibration**
   - complete surfaces and independent node scoring;
   - B1 fitting;
   - controls/routers/cascade;
   - cost and profile selection;
   - frozen selection artifacts.
4. **Qualification**
   - immutable look execution;
   - sequential intervals and gate report;
   - Core and model-headroom verdict.
5. **Policy development and Stage-2 freeze**
   - policy prompt candidates;
   - disjoint format cohorts and cold start;
   - prompt decision;
   - train/`dev_select`/`pilot_gate`/test schedules and surfaces;
   - launch profile and compute benchmark.
6. **Development signal**
   - one disposable seed, complete traces, checkpoint selection, one sealed
     pilot verdict.
7. **Headline replication and test**
   - three fresh unchanged seeds if authorized;
   - checkpoint lock;
   - one test reveal and final report.

Each unit receives a conformance/changed-lines review. Critical issues in
identity, privacy, reward, estimands, phase separation, reproducibility, or a
supported public workflow remain in scope. Do not repeat open-ended
Stage-0A internal-object hardening.

---

## 17. Review choices to sign

Recommended defaults in this draft:

1. **D4:** construction indices 30–129; cap extended to 130.
2. **Visible slice:** first 18 qualification clusters per cell.
3. **Profile discipline:** current primary plus at most one predeclared
   fallback per cell; first whole profile passing; no instance filtering.
4. **`math_code`:** current full band primary; no silent ≤8 cap.
5. **Parse gate:** zero untyped infrastructure failures; <2% truncation per
   `(cell, worker)`; selected-route syntax/artifact UCB <2% per cell overall
   and selected worker; unselected-route typed failures remain payoff
   evidence.
6. **Retry taxonomy:** infrastructure codes/limits are frozen separately;
   the descriptive cascade triggers exactly on `SYNTAX_REJECTION_CODES`.
7. **Sequential inference:** Bonferroni alpha spending by look and by
   learnable position; terminal aggregate router test; 10,000 paired
   cell-stratified percentile cluster bootstraps, exact rare-event envelopes,
   conservative undefined-replicate handling, and the frozen pre-CE1
   coverage-simulation acceptance rule.
8. **Scale materiality:** ≥10-point frozen per-position difference plus lower
   bound >0; multiplicity-adjusted aggregate `Delta_router` or
   `Delta_compat_fixed` lower bound >0 under the fixed priority.
9. **Minimum cells:** all three atomic + both chains; fork optional.
10. **Scale-null branch:** retain the four-worker C1 path—one disposable
    development signal and three fresh C1 headline seeds if its pilot
    passes; `107_s` is a separate model-routing follow-up.
11. **Prompt:** select by claim-headroom priority
    C2→C2-compat→C1, preferring few-shot only within the same highest rung;
    matching untrained baseline mandatory; no non-primary prompt training in
    v1.
12. **Cold start:** 72 unique groups per topology/treatment plus unique rows
    until every active-target direction reaches 72; per-candidate inherited
    gates plus ≥10% direct model-gradient groups.
13. **Stage-2 population:** 100 clusters/admitted cell with one balanced
    renderer for train; 24/cell fully crossed `dev_select`; disjoint 12/cell
    fully crossed `pilot_gate`; approximately 1,000 fully crossed test
    observations.
14. **Training:** one pass, two prompt groups/update—300 updates with six
    admitted cells; save every 25 updates and evaluate `dev_select`
    post-training.
15. **Pilot:** one disposable development seed; one paired disjoint pilot
    reveal with sibling-test multiplicity; three fresh headline seeds after
    the objective continuation gate.

Still required before CE1 freeze:

- exact `SYSTEM_DIRECT` bytes and digest;
- exact primary/fallback profile JSON and digests;
- exact manifest schemas and expected counts;
- exact infrastructure retry codes/limits and distinct cascade trigger codes;
- exact per-cell protocol-gate strata and fixed row counts;
- exact statistical implementation/RNG/quantile identifiers and passing
  coverage-simulation artifact;
- exact policy prompt **candidate** bytes and the cold-start/branch formulas;
- `policy_dev` registrar and disjoint cohort/support formulas;
- Stage-2 population, pilot, final-inference, and update-count formulas; and
- the first authorized construction command.

Required only in the later Stage-2 Freeze Addendum, after qualification and
cold start:

- selected Core/Core+fork and C1/C2/C2-compat branch;
- selected policy prompt and matching untrained condition;
- deterministic complete active-claim set, `target_model`, `K_pilot`, and
  final-test `K`;
- concrete `policy_dev`, train, `dev_select`, `pilot_gate`, and test
  population manifests;
- materialized surface and parity hashes;
- exact training/evaluation seeds and prompt order; and
- complete Stage-2 launch-profile hash and first authorized signal command.

---

## CE1 Freeze Record

*Intentionally empty in this first draft. Append only after review resolves
the Stage-1 choices in §17. This record must name the approved draft commit
and SHA-256, exact Stage-1 decisions, executable implementation commit,
population/profile/statistical hashes, and first authorized construction
command. Until then no formal construction worker result may be revealed.*

## Stage-2 Freeze Addendum

*Intentionally empty until the frozen Stage-1 qualification and policy-dev
decision complete. It records the already-permitted branch, selected prompt,
concrete train/`dev_select`/`pilot_gate`/test manifests, surfaces, launch
profile, seeds,
checkpoint rule, compute projection, and first signal-seed command. No
Stage-2 training may begin before this addendum is reviewed and signed.*
