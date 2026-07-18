# Conductor cell specifications — rev8 (v0.8, phase-1 freeze candidate)

The executable specification of the six Conductor cells: resource
schemas, reference programs, renderer strings, artifact grammars,
rejection rules, worked examples, interventions, baselines, and
acceptance hooks — the first Stage-0A deliverable, written and reviewed
before any generator code. This document is self-contained; the
negotiation history lives in the review lineage `30_f…47_s` of this
directory. Plan contracts (per-stage action spaces, reward table,
execution rules, gates) are normative in **the rev6 plan contract**
([`13_f_plan_rev6.md`](13_f_plan_rev6.md)) and are restated here only
where this specification refines them; §6 lists the proposed errata
against it. On sign-off, this file is copied verbatim to the repository
root as the frozen canonical `conductor_cell_specs.md`.

**Two-phase freeze**: phase 1 = this file, on reviewer sign-off; phase 2
= every **(S)** band (the difficulty profile, §1.14), after the
100-example construction screen. The D16 system-prompt artifact is a
separate reviewed freeze at 0A, before the construction screen.

All worked examples are machine-verified: intermediates, gold answers,
rejection/ablation/exclusion compliance, and intervention targets.

---

## 1. Global conventions

### 1.1 Integers and canonical wire form

- All public outputs are integers. Canonical decimal form at text→integer
  boundaries: `0` or `-?[1-9][0-9]*` (terminal answers parsed from text:
  direct baselines, deferred `<value>` control). `0012`, `+5`, `5.0`,
  `1,000`, internal whitespace rejected.
- Artifact grammars admit only nonnegative literals (`0 | [1-9][0-9]*`);
  no negative-literal token, no unary minus (D14). Negative intermediates
  from subtraction are legal.
- Digits-with-leading-zero → `E_NONCANONICAL_INT`; other malformed tokens
  → `E_PARSE`.
- Internal arithmetic exact, magnitude-capped (§1.6); fractions transient
  inside exact division only.
- Terminal (gold) answers ≥ 1 in every cell; intermediates may be 0 where
  noted (`math_code` index).

### 1.2 Resource kinds, handles, serialization

`integer_record` is a tagged union:

| kind | layout | payload | bound by |
|---|---|---|---|
| `integer_record` | `keyed` | ordered entities × ordered fields → int | Lookup dereferencing only |
| `integer_record` | `operands` | ordered identifiers → int | Math identifiers only |
| `integer_list` | — | ordered ints | Code `resource` only |

- Wrong layout/kind dereference → typed `E_RESOURCE_KIND` (global
  precedence, §1.6), never an exception. A Math endpoint may still read a
  keyed record in-context and emit literals (D1).
- `keyed` values pairwise distinct (D3); `operands` names `a, b, c, d` in
  order, modulus always `m` (D9).
- Stored as ordered entry arrays (payload bytes and cache identity depend
  on order):

```json
{"kind": "integer_record", "layout": "keyed",
 "payload": [["Aster", [["crates", 31]]], ["Cedar", [["crates", 17]]]]}

{"kind": "integer_record", "layout": "operands",
 "payload": [["a", 83719], ["b", 43], ["c", 1], ["d", 6]]}

{"kind": "integer_list", "payload": [41, 7, 83]}
```

- Handles: `R-` + digit + uppercase letter + digit; uniform, unique per
  instance, independent of cell/payload/split (N1). Manifest = handles in
  shuffled order (N8).

**Worker-facing payload text** (frozen; canonical integers, stored order,
LF newlines, no trailing whitespace):

```text
R-7K2:
Aster.crates = 31
Cedar.crates = 17
```

```text
R-2P6:
a = 83719
b = 43
```

```text
R-9V4:
[41, 7, 83, 22, 65, 14, 39, 90, 56, 11, 72, 28]
```

### 1.3 Stored-instance schema and normative reference IR

Typed argument references:

| ref | form | meaning |
|---|---|---|
| `lit` | `{"lit": 3}` / `{"lit": "Cedar"}` | **public** constant (p, q, t, k, i, sign, key, field) |
| `res` | `{"res": "R-9V4"}` | whole resource by handle |
| `operand` | `{"operand": {"res": "R-2P6", "name": "a"}}` | one scalar inside an `operands` record — private values live only in the registry |
| `node` | `{"node": "n1"}` | another node's value; dependency edges derived from these |

**Literal typing and operand matching (frozen)**: numeric `lit` values are
JSON integers (never strings or floats); `key`, `field`, `sign` are JSON
strings, `sign` ∈ {`"+"`, `"-"`}; for `ratio`, `modular`, `mul_add`, each
argument slot must reference the operand of the same name (slot `a` →
operand `"a"`, …) — a mismatch is an IR validity error.

**Normative per-operation schemas** (required args exactly; extra or
missing fields invalid; allowed ref kinds per slot; no other mixtures
permitted):

| op | args (allowed refs) | semantics |
|---|---|---|
| `lookup` | `handle` (res, keyed), `key` (lit str), `field` (lit str) | keyed retrieval |
| `affine` | `x` (node), `p` (lit), `sign` (lit), `q` (lit) | `p·x ± q` |
| `mul_add` | `a, b, c` (operand) | `a·b + c` |
| `ratio` | `a, b, c, d` (operand) | `(a·b − c) / d`, exact |
| `modular` | `a, b, c, m` (operand) | `(a·b + c) mod m`, m > 0 |
| `product_affine` | `x` (node), `y` (node), `q` (lit) | `x·y + q` |
| `seq_count` | `xs` (res, list), `t` (lit) | `count_gt(stable_unique(xs), t)` |
| `seq_select` | `xs` (res, list), `k` (lit), `i` (lit) | `at(rotate_left(stable_unique(xs), k), i)` |
| `seq_at` | `xs` (res, list), `i` (node) | `at(xs, i)` |

**IR validity rules** (generator-asserted, load-time validated): unique
node ids; `node` references acyclic, only to declared nodes; all `operand`
references of one node point to the same `operands` record; `positions` is
a topological ordering containing every node exactly once — entry *k*
(1-based) is the semantic node executed as workflow step *k*; `sink` =
`positions[-1]`; every `res`/`operand` handle exists in manifest and
registry with a compatible layout; manifest keys = registry keys exactly.

Instance schema — all id/seed values in this example are **schematic**;
real values come from §1.13 and are pinned by a golden fixture (§4):

```json
{
  "cell_id": "lookup_math",
  "latent_program_id": "lookup_math:qualification:00042:9f3ac1d2",
  "render_instance_id": "lookup_math:qualification:00042:9f3ac1d2:goal_first:private",
  "renderer_id": "goal_first",
  "split_id": "qualification",
  "visibility_condition": "private",
  "difficulty_profile_version": "dp-9a1b2c3d4e5f6071",
  "generator_version": "specs-v0.8+<code-version>",
  "seed": 18421,
  "public_numeric_values": {"p": 3, "q": 4},
  "public_numeric_collision_nodes": {},
  "public_numeric_collision": false,
  "sink_public_numeric_collision": false,
  "public_prompt": "...",
  "public_manifest": ["R-3T5"],
  "private_registry": {
    "R-3T5": {"kind": "integer_record", "layout": "keyed",
              "payload": [["Aster", [["units", 31]]], ["Cedar", [["units", 17]]],
                           ["Grove", [["units", 39]]], ["Ivory", [["units", 53]]]]}
  },
  "reference_program": {
    "nodes": [
      {"id": "n1", "op": "lookup",
       "args": {"handle": {"res": "R-3T5"}, "key": {"lit": "Cedar"}, "field": {"lit": "units"}}},
      {"id": "n2", "op": "affine",
       "args": {"x": {"node": "n1"}, "p": {"lit": 3}, "sign": {"lit": "-"}, "q": {"lit": 4}}}
    ],
    "positions": ["n1", "n2"],
    "sink": "n2"
  },
  "gold_answer": 47
}
```

Cluster identity = `latent_program_id`; "100 programs" = 100 latent
clusters. Reference subtasks and interventions derived deterministically,
not stored. Collision fields are scorer/calibration-only (§1.16).
Strip-test consequence: the execution path never reads
`reference_program`, `gold_answer`, or collision metadata; only the scorer
reads `gold_answer`.

### 1.4 Renderers

`resource_first` (canonical), `goal_first`, `bound_var`. Every latent
program is generated once and rendered in all three forms (one cluster);
renderer is not a scheduler factor. Paired visible renderings only for the
designated visible-slice clusters (§1.12). Frozen rules: template inputs
are handles and public parameters only; digits everywhere (D4); prompt
typography `× − ÷ mod`, artifact ASCII; "zero-based" always; shared
connective vocabulary (N5). All renderer strings enumerated in §3.

### 1.5 Observation and request contracts

**Stage-0C/2 policy observation** (private condition; frozen skeleton;
exact system prompts are the D16 artifact):

```text
Problem:
{public_prompt}

Resources available: {manifest handles, comma-separated, manifest order}

Steps:
1. (resource: {handle|none}; previous results: {none|all}) {reference subtask 1}
2. ...

Choose one worker for each step.
```

Steps numbered in `positions` order (position → node observable; fork
prompt clause order tracks the same order, §3.6).

**Routing-action schema (frozen exactly)**: the policy emits
`{"worker_ids": [w_1, …, w_S]}` and nothing else. `worker_ids` must be a
JSON array of JSON integers, of length exactly S; opaque worker ids are
**0, 1, 2** (the frozen endpoint indices, §1.8); duplicates permitted.
Extra fields, wrong types, wrong length, non-integer entries, or any value
outside {0, 1, 2} are schema violations → reward 0.0 — the action space is
the enumerated assignment set, and the plan contract's bijection acceptance test
(completions ↔ 3^S assignments) requires out-of-range ids to be malformed,
not world-failures.

**Worker request template** — canonical, byte-stable; blocks in fixed
order, each present or omitted whole; one blank line between blocks; LF;
no trailing whitespace; canonical integers:

```text
Problem:
{public_prompt}

Task:
{subtask}

Resource:
{payload text, §1.2}

Previous results:
step_1 = {value}
step_2 = {value}

Respond with exactly one <artifact>...</artifact> containing a single expression.
```

- `Problem` always present (D10). `Task` = the step's subtask. `Resource`
  omitted when nothing authorized. Multi-payload requests (harness-only,
  B3/B5) use the plural block:

```text
Resources:
{payload text 1}

{payload text 2}
```

- `Previous results` iff access = `all`: one `step_k = {value}` line per
  predecessor in step order; these lines and host-side binding are the
  only predecessor channels.
- Direct baselines (B1/B3/B4) use the same blocks under `SYSTEM_DIRECT`,
  replacing only the final line with the answer-line protocol (§1.11).
- `SYSTEM_LOOKUP` / `SYSTEM_MATH` / `SYSTEM_CODE` / `SYSTEM_DIRECT` are
  the separately reviewed 0A freeze artifact (D16), frozen before the
  construction screen, fingerprinted; later change retires qualification
  sets.
- **Canonical rendered request** = chat template over (system, user)
  bytes — cache-key component and byte-stability test target.

### 1.6 Artifact envelope, grammars, limits, typed rejections

**Envelope contract** — tokens are the exact byte strings `<artifact>` and
`</artifact>` (lower-case, no attributes; variants are ordinary text).
With n₀ = count of `<artifact>`, n₁ = count of `</artifact>` (plain
substring count; tag-like text in reasoning counts), frozen precedence:

1. any `<value>` or `</value>` substring → `E_UNEXPECTED_TAG`
2. n₀ = 0 → `E_NO_ARTIFACT`
3. n₀ ≥ 2 ∨ n₁ ≥ 2 → `E_MULTI_ARTIFACT`
4. n₁ = 0 → `E_UNCLOSED_ARTIFACT`
5. close before open → `E_PARSE`
6. else: content **between the tags** is trimmed, parsed by the endpoint
   grammar.

Text before/after the envelope is permitted and ignored.

**Backend truncation recorded independently**: every call logs
`generation_hit_token_cap: bool`, `finish_reason`, `envelope_error: code |
null`. The plan contract's < 2 % truncation gate reads `generation_hit_token_cap`;
the parse-failure gate reads envelope + grammar errors.

Endpoints: Lookup = Qwen2.5-1.5B-Instruct + keyed retrieval; Math =
Qwen2.5-Math-1.5B-Instruct + exact calculator; Code =
Qwen2.5-Coder-1.5B-Instruct + whitelist sequence interpreter. D1: payloads
in-context + host-side.

**Math grammar**

```ebnf
expr   := term (("+" | "-") term)*
term   := factor (("*" | "/" | "%") factor)*
factor := INT | IDENT | "(" expr ")"
IDENT  := [a-z] | "step_" [1-9]
INT    := "0" | [1-9] [0-9]*
```

**Lookup grammar**

```ebnf
lexpr := "lookup" "(" "resource" "," STR "," STR ")"
STR   := '"' [A-Za-z] [A-Za-z0-9]* '"'
```

**Code grammar**

```ebnf
int_expr := ("count_gt" | "at") "(" seq_expr "," int_arg ")"
seq_expr := "resource" | "stable_unique" "(" seq_expr ")"
          | "rotate_left" "(" seq_expr "," int_arg ")"
int_arg  := INT | "step_" [1-9]
```

**Tokenization and evaluation** (frozen): no negative literals / unary
minus (`a--5`, `--` → `E_PARSE`); precedence `* / %` over `+ -`,
left-associative, parentheses; whitespace between tokens; `/` exact in ℤ
else `E_INEXACT_DIV`, divisor 0 → `E_DIV_ZERO`; `%` floor-mod, modulus 0
→ `E_DIV_ZERO`, negative → `E_BAD_ARG`; `rotate_left` k ≥ 0
(`E_BAD_ARG`), rotates by `k mod len`; `at` zero-based (`E_INDEX_RANGE`);
`count_gt` strict.

**Resource-error precedence — global across the AST (frozen;
per-symbol application would make `a + step_9`
iteration-order-dependent)**:

> Resource checks run only when the parsed AST requires a resource-bound
> symbol (Lookup's `resource`, Code's `resource`, or a Math single-letter
> identifier). Procedure: parse the AST; **collect all resource demands
> and all step references**; then apply these global conditions in order:
>
> 1. a resource is demanded and none is authorized → `E_NO_RESOURCE`;
> 2. a resource is demanded and none is grammar-compatible →
>    `E_RESOURCE_KIND`;
> 3. an `operands` record is bound and **any** required identifier is
>    absent → `E_UNKNOWN_IDENT`;
> 4. **any** step reference is unavailable (no access, forward, or out of
>    range) → `E_UNKNOWN_IDENT`;
>
> then evaluate. An expression containing only literals and/or available
> `step_k` values **ignores the authorized resource set entirely and may
> succeed** — with an empty or incompatible binding set alike (this is
> B5's intended in-context capability).

**Uniform limits**: artifact ≤ 512 bytes (trimmed) → `E_PARSE`; AST ≤ 64
nodes, depth ≤ 8 → `E_DEPTH`; literal ≤ 12 digits → `E_PARSE`; any
intermediate/result |v| ≤ 10¹² → `E_MAGNITUDE`.

**Typed rejection codes**: `E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`,
`E_UNCLOSED_ARTIFACT`, `E_UNEXPECTED_TAG`, `E_PARSE`,
`E_NONCANONICAL_INT`, `E_UNKNOWN_IDENT`, `E_NO_RESOURCE`,
`E_RESOURCE_KIND`, `E_UNKNOWN_KEY`, `E_UNKNOWN_FIELD`, `E_INDEX_RANGE`,
`E_INEXACT_DIV`, `E_DIV_ZERO`, `E_BAD_ARG`, `E_DEPTH`, `E_MAGNITUDE`. All
take the contract-4 path; unexpected exceptions propagate and abort.

**Primitive semantics** (independent implementations in `tools.py` and
`program.py`; 10k agreement stratified by operator × cell):
`stable_unique`, `rotate_left`, `at`, `count_gt`, `lookup`, numeric ops of
§2.1.

### 1.7 WorkerResult, flags, failure propagation

```text
status         ∈ {success, typed_failure, dependency_blocked}
value          : int | null      (int iff success)
rejection_code : code | null     (set iff typed_failure)
artifact_valid : bool
tool_executed  : bool
synthetic      : bool            (true iff produced by a pseudo-worker)
```

**Flag truth table (frozen)**:

| outcome | artifact_valid | tool_executed | synthetic |
|---|---|---|---|
| envelope failure (§1.6 cases 1–5) | false | false | false |
| grammar/limit failure (`E_PARSE`, `E_NONCANONICAL_INT`, `E_DEPTH`) | false | false | false |
| semantic tool rejection (remaining codes) | true | true | false |
| success (endpoint) | true | true | false |
| dependency_blocked (no call made) | false | false | false |
| pseudo-worker result (success or typed_failure) | false | false | true |

Per-call telemetry: `generation_hit_token_cap`, `finish_reason`,
`envelope_error` (§1.6); pseudo-worker calls log none of these.

Propagation: a step whose status ≠ `success` blocks every later step with
access = `all` (`dependency_blocked`, no worker call); access = `none`
steps unaffected; a join is blocked if either branch fails; terminal =
sink value, sink not `success` → terminal null → 0.5; only infrastructure
failures abort.

### 1.8 Deployable oracle, controls, and the Stage-2 comparator

Node-id → endpoint mapping covering all six cells:

| cell | mapped nodes |
|---|---|
| `lookup_atomic` | n1 |
| `math_atomic` | n1 |
| `code_atomic` | n1 |
| `lookup_math` | n1, n2 |
| `math_code` | n1, n2 |
| `fork_join` | n1 (lookup branch), n2 (code branch), n3 (join) |

**Executable selection rule (frozen)**:

- Endpoint indices: 0 = Lookup, 1 = Math, 2 = Code (also the opaque
  routing ids, §1.5).
- Objective: over the full enumeration on construction data, the
  deployable assignment is the argmax of **cluster-weighted terminal
  accuracy** (mean over latent clusters of the within-cluster mean).
- An assignment is the tuple of endpoint indices in **stable node order
  (n1, n2, n3)** — never positional order.
- Ties resolve to the lexicographically smallest endpoint-index tuple.
- Node runner-up = the best alternative endpoint at that node with all
  other nodes fixed at the deployable assignment; ties to the lowest
  index.
- The same objective and ordering govern best one-call (argmax over the 3
  endpoints; tie → lowest index) and the 18-workflow two-call shortcut
  (argmax over the family; tie → lexicographic over (orientation,
  endpoint-index tuple), lookup-first < code-first).
- The mapping never conditions on execution order; allowed conditioning:
  (cell_id, node_id) only. Selected per cell on construction data, frozen,
  never reselected; `positions` alone permutes it into positional
  `worker_ids`; hindsight per-example maximum diagnostic only.
- Cold-start arithmetic (96 / 61 / 26 %) is node-level and
  order-invariant.

**Controls (frozen definitions)**:

- **`best_fixed`** — the construction-frozen best of the three constant
  assignments `(0,…,0)`, `(1,…,1)`, `(2,…,2)`, selected under the same
  cluster-weighted objective and tie rule. This is the control that
  distinguishes heterogeneous *selection* from the benefit of simply
  making multiple context-partitioned calls.
- **`random`** — the **exact uniform mean over the enumerated 3^S payoff
  surface** (analytic, never Monte Carlo samples).

**Signed deployable-assignment gap** (the scientific label: the policy
conditions on observable subtype and wording, so it can legitimately beat
the fixed (cell_id, node_id) mapping):

```text
signed_deployable_gap =
    correctness(frozen deployable assignment)
  - correctness(policy assignment)
```

paired, cluster-weighted, on the same examples. Frozen conventions:
malformed policy actions receive policy terminal-correctness 0;
the schema-valid rate is reported alongside; the gap is **not clipped and
may be negative**; it is **not** regret against the best
observation-conditional policy. `routing_regret` is retained as a legacy
metric name only.

### 1.9 Interventions: mediator (wire) semantics

Both kinds per dependency edge *(u → v)*, on the deployable-oracle
assignment at calibration time; mediator/wire interventions
(resource-level counterfactuals deferred). One replacement *r* per
`(latent_program_id, edge)`; one mutated execution scored twice.

**Positional application (frozen)**: `u` and `v` are semantic node ids;
the override applies at workflow position `j = 1 + positions.index(u)` —
replace `step_j` in both channels (the `step_j = r` context line and the
host-side binding). (Code-first fork: overriding `n2` overrides `step_1`.)
Log `override_applied: bool`.

**Paired estimand (frozen)**:

- Eligibility is determined once, from the base execution: every parent of
  the downstream node succeeded. Ineligible instances are excluded from
  all intervention metrics and counted (`intervention_ineligible`).
- Base, corrupted, and counterfactual accuracies are computed on the
  identical eligible edge-instance set; clustered comparisons pair the
  same latent/rendered executions (cluster bootstrap over latent
  programs).
- `override_applied = false` on an eligible execution is a harness failure
  → abort (infrastructure path), never an ordinary observation.
- Scoring: mutated terminal vs stored `gold_answer` → **corruption**
  accuracy and **old-answer persistence** (CE1 ≤ 10 %); same terminal vs
  `gold'` (reference sink recomputed outside the executor) →
  **counterfactual consistency**. `kind` only in result records.
- Full-sample (eligible-set) accuracy is the primary metric.
  *Follow-through* is the secondary diagnostic: counterfactual accuracy
  conditioned on the complete mutated downstream path executing
  successfully — reported alongside, never in place of, the full-sample
  estimate.
- **The intervention eligibility rate is reported alongside every
  intervention gate** (corruption, counterfactual consistency, old-answer
  persistence, follow-through) — these are conditional causal estimates
  and their conditioning fraction is part of the result.

Replacement rules per cell (§3) provably change the sink. Atomic cells: no
edges. Missing/skip variants prove only input-validation.

### 1.10 Caching rule

Cache stores raw model completions, keyed by **worker-visible fingerprint
+ endpoint fingerprint + canonical rendered request bytes**. The
worker-visible fingerprint covers everything a worker call can observe or
depend on — model/tokenizer revisions, chat template, NF4 config, caps,
truncation/stopping rules, tool versions, disclosure/resource policy —
but **not** the Conductor's private/visible observation condition, so
byte-identical worker requests intentionally share completions across
visibility conditions. The full runtime-profile fingerprint (which
includes the observation condition) governs Conductor-side generations and
trace manifests. Cache rows store generation metadata with the raw text —
`finish_reason`, generated-token count, `generation_hit_token_cap` — so
truncation telemetry survives cache hits. Tools re-executed per call;
executed `WorkerResult` never cached; intervention variants get distinct
keys by construction (request bytes differ).

### 1.11 Baselines and diagnostic workers — executable definitions

Direct arms (B1/B3/B4; `SYSTEM_DIRECT`) use the answer-line protocol:
final line `Answer with a single integer on the final line.`; the last
non-empty line, trimmed, must parse as a canonical integer, else scored
wrong.

| # | Arm | Model | Input |
|---|---|---|---|
| B1 | Public-only direct | 3B base | `Problem` only. Reported against majority-class, the public-parameter echo family (per-(cell, **observable subtype**) majority value ∪ each single public parameter, **evaluated only in subtypes where that parameter exists**), and the frozen shallow predictor below. Leakage is decided by provenance, never accuracy ≈ 0 |
| B2 | Endpoint-without-resource | each endpoint | worker request minus the `Resource` block **and with the authorized binding set empty** (both channels). Resource-requiring steps only |
| B3 | Visible direct | 3B base | `Problem` + plural `Resources:`. Diagnoses self-solving; no `SELF` ⇒ not delegation |
| B4 | Local-node | 3B base | same blocks as an endpoint worker (`Problem`, `Task` = node reference subtask, `Resource` = node payload, `Previous results` = gold predecessor values); only the final line differs |
| B5 | One-call whole-task | each endpoint | `Problem` + `Task: Complete the task and return the final result.` + plural `Resources:` (union payload, harness-only). Binding per §1.6's global procedure — a literal-only expression succeeds regardless of authorized resource kinds; more than one compatible payload → harness configuration error in v0. Incompatible payloads remain readable in-context |
| B6 | Generic-subtask arm | endpoints per deployable oracle | reference workflow, every subtask = `GENERIC_SUBTASK` |

- `GENERIC_SUBTASK` (frozen): `Complete the assigned step using the
  problem context, any provided resource, and any previous results.`
- Best one-call and the 18-workflow two-call shortcut: selection and
  tie-breaking per §1.8; contracted two-call subtasks (frozen verbatim):
  - *Lookup-first*: 1. `Retrieve {key}'s {field} value from the requested
    resource.` 2. `Remove later occurrences of repeated values from the
    integer sequence in the requested resource, count the values greater
    than {t}, multiply that count by step_1, and add {q}.`
  - *Code-first*: 1. `Remove later occurrences of repeated values from
    the integer sequence in the requested resource and count the values
    greater than {t}.` 2. `Retrieve {key}'s {field} value from the
    requested resource, multiply it by step_1, and add {q}.`
- **Observable subtype (frozen level lists)** — derivable from the
  public prompt alone: a public-only baseline must never consume private
  generator metadata (`target_stratum`, for instance, is hidden under
  private resources). Levels per cell:

```text
lookup_atomic: constant
math_atomic:   T1 / T2 / T3
code_atomic:   count / select
lookup_math:   minus / plus
math_code:     constant
fork_join:     lookup_first / code_first
```

  `target_stratum`, renderer id, split id, and every other generator-only
  field are **explicitly excluded** from B1 controls. Calibration-side
  usage is distinct: define

```text
full_latent_stratum = the joint categorical-factor assignment in the
§1.14 scheduler table, including target_stratum where applicable.
Renderer is NOT part of it (renderer is fully crossed, not a scheduler
factor — including it would also make the renderer-within-stratum
leakage test degenerate).
```

  Rejection caps and leakage audits use `full_latent_stratum`;
  qualification reports latent-stratum and renderer marginals
  **separately**; B1 controls use the observable subtype only.
- **Frozen shallow predictor**: **one
  classifier per cell**; scikit-learn `DecisionTreeClassifier` (version
  pinned by lockfile), `max_depth=3`, `criterion="gini"`,
  `min_samples_leaf=5`, `random_state=0`; prediction ties → lowest class
  label. Features: **observable subtype one-hot in the frozen level order
  above, then numeric columns exactly `[p, q, t, k, i]` in that order**,
  missing numeric values encoded −1; sign/template/branch order enter only
  through the observable subtype; **keys, fields, handles, entity names,
  and all generator-only fields are excluded**. One training row per
  latent cluster (canonical `resource_first` rendering). Fitted on
  construction data only, then frozen. A golden feature-matrix/prediction
  fixture pins the column order (§4).
- **Diagnostic pseudo-workers** (results carry `synthetic = true`, §1.7):
  - *Echo worker*: value = last canonical-integer token in its `Task`
    block (boundaries §1.13), else `typed_failure(E_PARSE)`.
  - *No-op worker*: value = 0 always. Not a guaranteed floor (`math_code`
    index 0); `noop_correct` workflows reported.
  - Substitution protocol (frozen): a pseudo-worker is substituted at one
    node while all other nodes keep their deployable-oracle workers; each
    node substitution reported separately; an all-pseudo workflow is an
    optional additional arm.
  - *Answer-in-subtask telemetry* (always on, Stages 3–4): node-level per
    §1.16. **The token detector is a restricted proxy with incomplete
    recall and possible false positives; it bounds neither the true
    smuggling-event rate nor genuinely smuggling-free performance**.
- Reporting: prompt tokens and tool-call counts per condition;
  context-partitioning wins identified as such.

### 1.12 Visibility conditions

`visibility_condition` ∈ {`private`, `visible`}. Visible rendering appends
the plural `Resources:` block after the Conductor-side `Problem` block.
Worker-side requests identical in both conditions (completions shared,
§1.10). Visible variants only for the designated visible-slice clusters
(~100 latent programs, pre-registered), paired by `latent_program_id` and
split. Visibility enters `render_instance_id`, observation bytes, and the
Conductor-side profile fingerprint.

### 1.13 Identity, randomness, splits

- **Hash-to-integer**: `h64(s) =` first 8 bytes of `SHA-256(s)`,
  big-endian unsigned; all seed strings UTF-8; separator ␟ = 0x1F.
- **PRNG**: NumPy `Generator(PCG64(seed))`, version pinned by lockfile.
- **Generation identity**: `seed_material = "qwen-grpo-conductor" ␟
  generator_version ␟ difficulty_profile_version ␟ namespace ␟ cell_id ␟
  latent_index` — `latent_index` (and `block_index`, §1.14) rendered as
  canonical unpadded ASCII decimal in hash inputs; the zero-padded
  `{latent_index:05d}` appears only in the display form of
  `latent_program_id`.
- **Derivations**: `seed = h64(seed_material)`; `hex8` = first 8 lowercase
  hexadecimal characters of `SHA-256(seed_material)`. A golden fixture
  pins one full derivation at 0A (§4).
- **Labelled per-instance substreams**: child seed = `h64(seed_material ␟
  label)`, labels `"values"`, `"names"`, `"handles"`, `"manifest"`. The
  factor scheduler uses the block-level seed of §1.14; intervention seeds
  derive from `latent_program_id` + edge (below).
- `latent_program_id = "{cell_id}:{namespace}:{latent_index:05d}:{hex8}"`;
  `render_instance_id = latent_program_id + ":" + renderer_id + ":" +
  visibility_condition`.
- **Intervention replacements**: PRNG seeded by `h64("intervention" ␟
  latent_program_id ␟ edge_label)`; **`edge_label` (frozen) = the
  ASCII/UTF-8 string `"{u}->{v}"` over stable semantic node ids**
  (`"n1->n3"`; no whitespace, lowercase); no scoring kind in the seed.
- **Canonical JSON — scope**: the integers-only rule applies to
  generator/difficulty-profile hashing (UTF-8, sorted keys, separators
  `(",", ":")`, JSON integers only). Other hashed configurations (e.g. the
  runtime profile, which contains β = 1e-3) encode float-valued fields as
  shortest-round-trip decimal strings, never JSON floats.
  `difficulty_profile_version` = `"dp-"` + first 16 hex chars of the
  SHA-256.
- **Echo/collision integer-token boundaries**: matches of
  `(?<![\w-])-?(0|[1-9][0-9]*)(?![\w])`.
- **Namespaces** `construction, qualification, train, dev, test`: disjoint
  generation universes. **Every namespace has its own predeclared maximum
  latent count, immutable latent-index order, expansion batch size, and
  stopping rule; only `qualification` uses the sequential-look schedules
  of §1.14 (ordinary cells 100 / 300 / 500 clusters per cell; fork/join
  100 / 200)**. Evaluation over deterministic prefixes; no latent program
  crosses namespaces (unit-tested).

### 1.14 Distributions and sampling protocol

- **Numeric parameters**: independent integer-uniform on their (S) bands
  unless stated; every band is read from the difficulty profile at
  generation time — none is hard-coded. T1 constructive `c` (uniform on
  `{c ∈ profile band : c ≡ a·b (mod d)}`); if a tuned profile makes a
  constructive feasible set empty, that proposal counts as a rejected
  candidate (toward the 75 % cap); a profile whose `full_latent_stratum` exceeds the cap
  fails construction. Records — entities/fields uniform without
  replacement, values uniform without replacement; dedup lists i.i.d.
  uniform on their band then rules; select lists uniform without
  replacement on their band.
- **Cell-scoped profile schema** (bands are per-cell fields — global
  names would collide: `math_atomic.a_band` = 10⁴–10⁶ vs
  `math_code.a_band` = 10⁸–10⁹):

```text
profile.cells.lookup_atomic:  N_band, F_band, value_band
profile.cells.math_atomic:    a_band, b_band, c_band, t1.d_band, t2.m_band
profile.cells.code_atomic:    L_band, value_band, k_band, t_band
profile.cells.lookup_math:    N_band, F_band, value_band, p_band, q_band
profile.cells.math_code:      a_band, b_band, c_band, L_band, list_value_band
profile.cells.fork_join:      N_band, F_band, value_band, q_band,
                              count.L_band, count.value_band, count.t_band
```

  Every cell has independent fields; profile validation requires all
  fields present (no implicit fallback). Intentional default-copies (the
  fork count branch initializes from `code_atomic`'s defaults) are
  recorded in a `derived_from` annotation — part of the hashed profile,
  no runtime effect. The §3 parameter tables state the **initial
  default-profile values** for these fields (all (S)-marked; frozen at
  phase 2).
- **Profile-domain validation** — field presence alone would let a
  phase-2 tuned profile violate phase-1 semantics without a clean
  rejection. **General rule: every `requires`, "band-guaranteed",
  grammar, intervention-support, and without-replacement assumption in
  this specification is enforced by profile validation** — an offending
  profile is rejected at load, never silently sampled around. At minimum:

  - every band: `band.min ≤ band.max`;
  - keyed records: `N_band` min ≥ 3 (three non-empty target strata),
    `N_band` max ≤ 20; **`1 ≤ F_band.min ≤ F_band.max ≤ 10`** (F = 0
    would leave target-field sampling undefined); `|value_band| ≥` the
    largest admitted `N × F`
    (without-replacement);
  - `math_atomic`: `b_band` min ≥ 10, `c_band` min ≥ 1, `t1.d_band`
    min ≥ 2, `t2.m_band` min ≥ 2 (valid positive modulus with a
    non-empty answer range [1, m−1]);
  - `lookup_math`: `p_band` min ≥ 2, `q_band` min ≥ 1; **minus-form
    intervention support** (p ≥ 2, q ≥ 1 alone is insufficient: with
    value_band = {1, 2, 3}, p = 2, q = 5, the base n1 = 3 is valid but
    no alternative yields a positive counterfactual): with
    `S⁻(p, q) = {x ∈ value_band : p·x − q ≥ 1}`, require
    `|S⁻(p_band.min, q_band.max)| ≥ 2` — S⁻ grows with p and shrinks
    with q, so this single check covers every admitted (p, q);
  - dedup tasks: `L_band` min ≥ 5 (U ≥ 3 requires L ≥ U + 2) and
    `|value_band| ≥ 3` (U ≥ 3 attainable);
  - `math_code`: `L_band` min ≥ 2 (non-empty intervention alternative
    set) and `|list_value_band| ≥` the maximum permitted L
    (pairwise-distinct without replacement);
  - `code_atomic`: **`value_band` min ≥ 1** (the select shape returns
    a band value directly as the terminal answer);
  - every public value inserted as a grammar literal (p, q, t, k, i)
    must be **nonnegative and ≤ 999 999 999 999** (the grammars have
    no negative literals and a 12-digit literal limit);
  - value bands that directly determine terminal answers preserve the
    global `gold ≥ 1` contract (e.g. keyed `value_band` min ≥ 1,
    `list_value_band` min ≥ 1);
  - `fork_join`: positive branch outputs (`value_band` min ≥ 1; count
    branch nondegeneracy via its inherited rules) and `q_band` min ≥ 1.

  Invalid-profile tests accompany the sampler tests (§4).
- **Instance-level pre-admission rejection — not profile-load
  validation** (chosen over analytic per-profile bounds as the more
  robust option): **`R_MAGNITUDE`** rejects a candidate toward its
  `full_latent_stratum` rejection cap if exact, limit-aware evaluation
  of either

  1. the base reference execution, or
  2. any deterministically drawn intervention/counterfactual reference
     execution

  would exceed `|v| ≤ 10¹²` at any checked leaf, intermediate/operator
  result, or terminal result — evaluated with the artifact-level
  operator decomposition (products before add/subtract/mod, as a
  reference artifact would evaluate). Checking the intervention paths
  matters: a magnitude-safe base Lookup→Math instance can still have an
  alternative `n1'` for which `p·n1' ± q` overflows, and analogous cases
  exist for fork replacements and Math→Code's alternative selected
  value. No admitted instance can therefore store a valid-looking gold —
  or produce an intervention variant — whose correct artifact
  deterministically yields `E_MAGNITUDE`. (The default profile satisfies
  the bound analytically: the largest product is `math_code`'s
  a·b ≤ 10⁹ · 99 < 10¹².)
- **Target stratum — keyed-record cells only** (`lookup_atomic`,
  `lookup_math`, `fork_join`): entity indices split by
  `numpy.array_split(range(N), 3)`; target uniform within the scheduled
  stratum; field uniform.
- **Categorical factor scheduler (frozen)**:

```text
factors/levels per cell, frozen order (first factor most significant):
  lookup_atomic: target_stratum (first, middle, last)                 B = 3
  math_atomic:   template (T1, T2, T3)                                B = 3
  code_atomic:   shape (count, select)                                B = 2
  lookup_math:   sign (minus, plus) × target_stratum (f, m, l)        B = 6
  math_code:     — (no categorical factors)                           B = 1
  fork_join:     branch_order (lookup_first, code_first) ×
                 target_stratum (f, m, l)                             B = 6

block_index = latent_index // B     (unpadded ASCII decimal in hash input)
offset      = latent_index %  B
block_seed  = h64("qwen-grpo-conductor" ␟ generator_version ␟
                  difficulty_profile_version ␟ namespace ␟ cell_id ␟
                  "factor_perm" ␟ block_index)
assignment  = permutation(cartesian_product, PCG64(block_seed))[offset]
```

  Partial final block: same permutation, truncated — joint counts differ
  by at most one overall; balance exact at block boundaries, not at
  arbitrary prefixes. Golden assignment fixture (§4).
- **Sequential qualification inference (pre-registered)**: gate CIs use
  alpha spending across pre-registered look schedules — ordinary cells:
  looks at 100, 300, 500 clusters/cell; fork/join: looks at 100, 200 —
  with a separate pre-registered spending function for each schedule, both
  fixed in CE1 before any qualification data, which also specifies one-
  versus two-sided boundaries per gate. Stopping semantics (frozen, per
  schedule): a conclusively failed gate stops as failure; all gates
  conclusively passing stops as pass; unresolved at the respective cap
  means no admission.
- **Telemetry at the construction screen**: rejection counts by rule;
  post-rejection marginals and pre-registered joint distributions —
  `(m, residue)`, `(U, t, answer)`, **proposed and accepted `(N, F,
  N×F)`** (record workload is the primary distractor/context-size
  control), and collision rate by cell × `full_latent_stratum`; 75 %
  rejection cap per `full_latent_stratum` (§1.11); exceeding it fails
  the profile (fix the profile; never hand-prune).
- **Pre-registration rule**: no individual instance is ever retained or
  discarded based on worker performance; only an entire difficulty
  profile or cell passes or fails construction screening.
- **Difficulty profile** = canonical JSON (§1.13 scope) of the full
  `profile.cells.*` structure and distributions; version string per
  §1.13; part of generation identity; frozen at phase 2.
- **Qualification reporting**: stratified by `full_latent_stratum` (T1/T2/T3, count/select,
  plus/minus, fork order, target stratum where applicable), with
  **renderer marginals reported separately** (renderer is fully crossed,
  not a scheduler factor) — including per-stratum payoff surfaces
  (descriptive; the deployable mapping stays fixed).
- Per-instance resampling cap 1000 attempts; rules re-asserted at load
  time.

### 1.15 Balance enforcement and shortcut audit

1. **Structural gates** (generator-enforced, unit-tested): joint
   contingency tables per cell × split (±1); handle characters uniform;
   manifest order shuffled; all three renderings per latent program;
   splits balanced across factors.
2. **Statistical leakage checks — randomized fields only, within
   `full_latent_stratum`**: {handle strings, entity names, field
   names, renderer id, split id} × stratum; cluster-aware permutation
   test (clusters = latent programs; 10,000 permutations) against
   within-stratum answer quartiles; α = 0.01 Holm-corrected. (Renderer id
   is a *tested field*, not part of the stratum — which is what keeps the
   renderer-within-stratum test non-degenerate.) Failures investigated as
   generator defects.
3. **Descriptive diagnostics, not gates**: prompt-length distributions;
   shallow bag-of-words router accuracy (expected high; acceptable for
   the plan contract's stated Stage-2 claim of fixed endpoint
   selection).
4. Anti-template gate reserved for the deferred semantic renderer; no
   second Lookup→Math resource. Legitimate semantic cues remain by
   design.

### 1.16 Public-numeric collision metadata (node-level, analysis-only)

Derived from provenance-tagged semantic parameters (`p, q, t, k, i` as
applicable), never by scanning rendered text. Stored per instance:

```text
public_numeric_values:          parameter name → value
public_numeric_collision_nodes: node_id → [matching parameter names]
public_numeric_collision:       true iff any node matches
sink_public_numeric_collision:  true iff the sink matches
```

- **Stage-3 telemetry**: compare each authored subtask against its node's
  reference value (token boundaries §1.13). **Stage-4**: conservatively
  flag any reference-node value appearing in any authored subtask. All
  collision fields and telemetry are scorer/calibration-only.
- Headline stratum: the **private, no-public-semantic-parameter-collision
  stratum** — it removes pre-existing copying opportunities but cannot
  exclude lucky guesses or encoded answers; sample size (latent clusters)
  reported.
- **Pre-registered reports**: collision rate by cell × `full_latent_stratum`; accuracy
  conditioned on collision vs non-collision; answer-in-subtask rate
  crossed with collision status — counted in latent clusters with
  clustered CIs.
- **Detected-token-penalized sensitivity score**: a secondary scoring
  computed on exactly the headline population — the same private,
  no-collision clusters, the same renderer observations, the same cluster
  weights — in which every workflow with a detected answer-in-subtask
  event is recoded as incorrect. Numerically ≤ the headline by
  construction. **The token detector is a restricted proxy with
  incomplete recall and possible false positives; neither the true
  smuggling-event rate nor genuinely smuggling-free performance is
  bounded**.
- D15 (flag, not reject) applies under exactly this node-level,
  analysis-only construction.

### 1.17 Name pools

20 entities (Aster, Birch, Cedar, Elm, Fern, Grove, Hazel, Ivory,
Juniper, Lark, Maple, Nettle, Onyx, Pine, Quill, Rowan, Slate, Tarn,
Vale, Wren); 10 fields (crates, units, tokens, points, seats, kits,
spools, tiles, flasks, reams); operand identifiers per D9 (D7).

---

## 2. Shared generator machinery

### 2.1 Primitive ops and reference functions

```python
def prim_lookup(rec, key, field) -> int           # keyed retrieval (layout=keyed only)
def prim_affine(x, p, sign, q) -> int             # p*x + q  |  p*x - q
def prim_mul_add(a, b, c) -> int                  # a*b + c
def prim_ratio(a, b, c, d) -> int                 # (a*b - c) / d, exact else raise
def prim_modular(a, b, c, m) -> int               # (a*b + c) % m, m > 0
def prim_product_affine(x, y, q) -> int           # x*y + q
def prim_seq_count(xs, t) -> int                  # count_gt(stable_unique(xs), t)
def prim_seq_select(xs, k, i) -> int              # at(rotate_left(stable_unique(xs), k), i)
def prim_seq_at(xs, i) -> int                     # at(xs, i)
```

### 2.2 Shared samplers

Sampler signatures **require** their band arguments (no Python defaults);
all bands come from `profile.cells.<cell_id>` (§1.14):

```python
integer_record(N, F, value_band, layout)
integer_list_dedup(L, value_band)      # requires 3 <= U <= L - 2
integer_list_select(L, value_band)     # pairwise distinct
```

---

## 3. Cell specifications

Parameter tables state the initial default-profile values for the
cell-scoped fields of §1.14 (all (S)-marked; phase-2 freeze). Conventions:
**O** ordinary, **B** boundary; example artifacts illustrate the grammar
(any grammar-valid artifact whose executed value is correct scores); no
gold worker presumed; reference subtasks tool-neutral; renderer strings
enumerated in full. All fixtures machine-verified.

### 3.1 `lookup_atomic` — atomic Lookup

**Shape**: 1 step, access `[none]`, 1 keyed `integer_record`.

| Parameter | Default profile value |
|---|---|
| entities N | 3–16 **(S)**, `N × F ≤ 60` |
| fields F | 1–5 **(S)** |
| value band | 10–99 **(S)**, pairwise distinct |
| target (key, field) | stratified per §1.14; field uniform |

**Rejection rules**: none beyond record invariants.

**Renderer strings**:

- `resource_first`: `Resource {H} contains keyed integer records. Return
  the {field} value recorded for {key}.`
- `goal_first`: `Return the {field} value that {H} records for {key}.`
- `bound_var`: `Let v be {key}'s {field} in {H}. Output v.`

**Reference program**: `n1 = lookup(handle={res H}, key={lit},
field={lit})`; positions `[n1]`; sink `n1`.

**Reference subtask**: `Retrieve {key}'s {field} value from the requested
resource.`

**Example artifact**: `<artifact>lookup(resource, "Grove", "crates")</artifact>`

**O** — `R-7K2`: Aster.crates = 31, Cedar.crates = 17, Grove.crates = 39,
Ivory.crates = 53; target Grove.crates. Gold: **39**.

**B** — small-N (N = 4; band minimum 3), band-edge values. `R-4H8`:
Lark.units = 99, Onyx.units = 10, Pine.units = 11, Quill.units = 98;
target Quill.units. Gold: **98**.

**Interventions**: none (atomic). **One-call baseline**: B5, the record.

### 3.2 `math_atomic` — atomic Math (hidden operands, public formula)

**Shape**: 1 step, access `[none]`, 1 `operands`-layout record.

| Template | Public formula | IR op | Operands |
|---|---|---|---|
| T1 ratio | `(a × b − c) ÷ d` | `ratio` | a, b, c, d |
| T2 modular | `(a × b + c) mod m` | `modular` | a, b, c, m |
| T3 affine | `a × b + c` | `mul_add` | a, b, c |

| Parameter | Default profile value |
|---|---|
| a | 10⁴–10⁶ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** (T1 constructive) |
| d (T1) | 2–12 **(S)** |
| m (T2) | 5–60 **(S)** |

**Rejection rules**: answer ∈ [1, 10⁹]; T2 answer ∈ [1, m−1]; answer ∉
operand values; **modular checks** (every modular node, here and
`math_code` n1; `g` = residue): relevance — drop-c `(a·b) mod m ≠ g`, a→1
`(b+c) mod m ≠ g`, b→1 `(a+c) mod m ≠ g`; wrong-program exclusions —
mul→add `(a+b+c) mod m ≠ g`, sign-flip `(a·b−c) mod m ≠ g`. (T1/T3
relevance band-guaranteed: b ≥ 10, c ≥ 1, d ≥ 2.)

**Renderer strings** (`{names}` = `a, b, c and d` / `a, b, c and m` /
`a, b and c`):

- `resource_first`: `{H} contains integers {names}. Evaluate`
  `` `{formula}` `` `exactly.`
- `goal_first`: `Return the exact value of` `` `{formula}` `` `, where
  {names} are the integers recorded in {H}.`
- `bound_var`: `Let {names} be the integers in {H}. Output`
  `` `{formula}` `` `.`

**Reference program**: `n1 = ratio | modular | mul_add` with `operand`
references (all into the same record); positions `[n1]`; sink `n1`.

**Reference subtask**: `Evaluate` `` `{formula}` `` `exactly using the
integers in the requested resource.`

**Example artifact**: `<artifact>(a * b - c) / d</artifact>`

**O (T1)** — `R-2P6`: a = 83719, b = 43, c = 1, d = 6. **599986**.

**O (T2)** — `R-7Q4`: a = 999983, b = 89, c = 19, m = 12. Residues 11, 5,
7: g = **2**. (Relevance 7/0/6 ≠ 2 ✓; exclusions: mul→add 11 ≠ 2 ✓,
sign-flip 0 ≠ 2 ✓.)

**O (T3)** — `R-1X5`: a = 524287, b = 83, c = 17. **43515838** (op
`mul_add`).

**B (T1, low edges)** — `R-8B2`: a = 10007, b = 10, c = 2, d = 6.
**16678**.

**Interventions**: none (atomic). **One-call baseline**: B5, operand
record.

### 3.3 `code_atomic` — atomic Code (one call, nested composition)

**Shape**: 1 step, access `[none]`, 1 dedup-flavor `integer_list`.

| Shape | Latent pipeline |
|---|---|
| count | `count_gt(stable_unique(xs), t)` |
| select | `at(rotate_left(stable_unique(xs), k), i)` |

| Parameter | Default profile value |
|---|---|
| L | 8–16 **(S)**, values 1–9 **(S)** |
| U | 3 ≤ U ≤ L − 2 |
| k (select) | 1–9 **(S)**, `k mod U ≠ 0` |
| t (count) | 1–8 **(S)** |
| i (select) | 0…U−1 |

**Rejection rules**: `3 ≤ U ≤ L − 2`; count — `1 ≤ answer ≤ U − 1`, dedup
ablation `count_gt(xs, t) ≠ count_gt(stable_unique(xs), t)`; select —
`k mod U ≠ 0`, dedup ablation `at(rotate_left(xs, k), i) ≠ gold`,
rotation ablation `at(stable_unique(xs), i) ≠ gold`.

**Renderer strings — count**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values and count the values greater than {t}.`
- `goal_first`: `Return how many values exceed {t} in the sequence
  obtained from {H} by removing later occurrences of repeated values.`
- `bound_var`: `Let s be the sequence in {H} after removing later
  occurrences of repeated values. Output the count of values in s greater
  than {t}.`

**Renderer strings — select**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values, rotate the remaining sequence left by
  {k} positions, and return the value at zero-based index {i}.`
- `goal_first`: `Return the value at zero-based index {i} of the sequence
  obtained from {H} by removing later occurrences of repeated values and
  rotating it left by {k} positions.`
- `bound_var`: `Let s be the sequence in {H} after removing later
  occurrences of repeated values and rotating left by {k} positions.
  Output the value of s at zero-based index {i}.`

**Reference program**: `n1 = seq_count(xs={res H}, t={lit})` |
`seq_select(xs={res H}, k={lit}, i={lit})`; positions `[n1]`; sink `n1`.

**Reference subtasks**: count — `Remove later occurrences of repeated
values from the integer sequence in the requested resource and count the
values greater than {t}.`; select — `Remove later occurrences of repeated
values from the integer sequence in the requested resource, rotate the
remaining sequence left by {k} positions, and return the value at
zero-based index {i}.`

**Example artifacts**:
`<artifact>count_gt(stable_unique(resource), 5)</artifact>`;
`<artifact>at(rotate_left(stable_unique(resource), 2), 4)</artifact>`

**O (count)** — `R-8C3`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]`, t = 5.
U = 8; **4**. (Dedup ablation 6 ≠ 4 ✓.)

**O (select)** — `R-5N1`: `[5, 3, 5, 8, 1, 3, 9, 2]`, k = 2, i = 4.
U = 6; `rotate_left(2) → [8, 1, 9, 2, 5, 3]`; **5**. (Ablations 9 ≠ 5,
9 ≠ 5 ✓.)

**B (count, answer = U − 1)** — `R-9E3`: `[9, 8, 9, 7, 6, 8, 5, 9]`,
t = 5. U = 5; **4**. (Dedup ablation 7 ≠ 4 ✓.)

**Interventions**: none (atomic). **One-call baseline**: B5, the list.

### 3.4 `lookup_math` — Lookup → Math

**Shape**: 2 steps, access `[none, all]`; keyed record at step 1; step 2
requests none, consumes `step_1`.

| Parameter | Default profile value |
|---|---|
| record N, F, band | as §3.1; target value n1 ∈ [10, 99] |
| p | 2–9 **(S)** |
| q | 1–20 **(S)** |
| sign | {+, −} scheduled (§1.14) |

**Rejection rules**: answer ≥ 1; answer ∉ record values; answer ≠ n1.

**Renderer strings — minus form**:

- `resource_first`: `Retrieve {key}'s {field} from {H}. Return {p} times
  that value minus {q}.`
- `goal_first`: `Return the number obtained by subtracting {q} from {p}
  times {key}'s {field} recorded in {H}.`
- `bound_var`: `Let x be {key}'s {field} in {H}. Output`
  `` `{p}x − {q}` `` `.`

**Renderer strings — plus form**:

- `resource_first`: `Retrieve {key}'s {field} from {H}. Return {p} times
  that value plus {q}.`
- `goal_first`: `Return the number obtained by adding {q} to {p} times
  {key}'s {field} recorded in {H}.`
- `bound_var`: `Let x be {key}'s {field} in {H}. Output`
  `` `{p}x + {q}` `` `.`

**Reference program**: `n1 = lookup(...)`; `n2 = affine(x={node n1},
p={lit}, sign={lit}, q={lit})`; positions `[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Retrieve {key}'s {field} value from the
requested resource.` 2. `Multiply step_1 by {p}, then subtract {q}.`
(plus: `…, then add {q}.`)

**Example artifacts**:
`<artifact>lookup(resource, "Cedar", "units")</artifact>`;
`<artifact>3 * step_1 - 4</artifact>`

**O** — `R-3T5`: Aster.units = 31, Cedar.units = 17, Grove.units = 39,
Ivory.units = 53; target Cedar.units; p = 3, minus, q = 4. `n1 = 17`;
**47**.

**B (band edges)** — `R-2W9`: Vale.units = 99, Aster.units = 10,
Hazel.units = 23, Tarn.units = 57; target Vale.units; p = 9, minus,
q = 20. **871**.

**Interventions** (edge `n1->n2`; §1.9): minus form — `n1' ~
U(S⁻(p, q) \ {n1})` with `S⁻(p, q) = {x ∈
profile.cells.lookup_math.value_band : p·x − q ≥ 1}` (a direct draw
from the provably non-empty support set, §1.14 validation); plus form — `n1' ~ U(value_band \
{n1})` (always positive). Example (O, default profile): `n1' = 19` —
corruption target 47 (run yields 53, wrong); counterfactual target 53.

**One-call baseline**: B5, the record; screen tunes N/F/distractors for
the +20-point gate.

### 3.5 `math_code` — Math → Code (computed index)

**Shape**: 2 steps, access `[none, all]`; step 1 = operand record; step 2
= list, consumes `step_1`.

| Parameter | Default profile value |
|---|---|
| a | 10⁸–10⁹ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** |
| m = L | 8–16 **(S)** (D6) |
| list | select-flavor, 1–99 **(S)**, pairwise distinct |

**Rejection rules**: list pairwise distinct; answer ≠ n1; answer ∉
{a, b, c, m}; all §3.2 modular checks on n1; intermediate n1 = 0
permitted (terminal ≥ 1 via list band).

**Renderer strings**:

- `resource_first`: `{H1} contains integers a, b, c and m. Compute`
  `` `(a × b + c) mod m` `` `. Use the result as a zero-based index into
  the sequence in {H2} and return the selected integer.`
- `goal_first`: `Return the integer found in {H2} at the zero-based index
  given by` `` `(a × b + c) mod m` `` `, where a, b, c and m are the
  integers in {H1}.`
- `bound_var`: `Let i =` `` `(a × b + c) mod m` `` `, with a, b, c and m
  taken from {H1}. Output the value of the sequence in {H2} at zero-based
  index i.`

**Reference program**: `n1 = modular(a, b, c, m)` (operand refs into H1);
`n2 = seq_at(xs={res H2}, i={node n1})`; positions `[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Evaluate` `` `(a × b + c) mod m` `` `exactly
using the integers in the requested resource.` 2. `Return the value at
zero-based index step_1 in the integer sequence from the requested
resource.`

**Example artifacts**: `<artifact>(a * b + c) % m</artifact>`;
`<artifact>at(resource, step_1)</artifact>`

**O** — `R-6D1`: a = 314159265, b = 55, c = 17, m = 12; `R-9V4`: `[41, 7,
83, 22, 65, 14, 39, 90, 56, 11, 72, 28]`. Residues 9, 7, 5: n1 = 8;
**56**. (Relevance 3/0/2 ≠ 8 ✓; exclusions: mul→add 9 ≠ 8 ✓, sign-flip
10 ≠ 8 ✓.)

**B (index = m − 1)** — `R-3F7`: a = 123456789, b = 45, c = 6, m = 8;
`R-6M2`: `[17, 64, 80, 23, 46, 91, 12, 58]`. Residues 5, 5, 6: n1 = 7;
**58**. (Relevance 1/3/3 ≠ 7 ✓; exclusions: mul→add 0 ≠ 7 ✓, sign-flip
3 ≠ 7 ✓.)

**Interventions** (edge `n1->n2`): `i' ~ U([0, m−1] \ {n1})`; one mutated
execution scored twice. Example (O): `i' = 3` — corruption target 56 (run
yields 22, wrong); counterfactual target 22.

**One-call baseline**: B5, record + list.

### 3.6 `fork_join` — Lookup + Code → Math (diagnostic)

**Shape**: 3 steps, access `[none, none, all]`; branch steps request one
resource each; join requests none, consumes `step_1`, `step_2`.
Diagnostic-only in v0; qualification looks at 100 and 200 latent clusters
(§1.14 fork/join schedule). If admitted to Stage-2 routing after its
gates, fork/join tests endpoint selection within a fixed parallel DAG;
topology construction remains a Stage-4 claim.

**Branch order**: scheduled 50/50 (§1.14); `positions` records it; the
Stage-2 observation and public prompt clause order track it. The
deployable oracle maps node ids and is order-invariant (§1.8).

| Parameter | Default profile value |
|---|---|
| record N, F, band | as §3.1; n_lk ∈ [10, 99] |
| code branch | count shape of §3.3 (U ≥ 3, ablation rules); `derived_from: code_atomic` (§1.14) |
| q | 1–20 **(S)** |

Join skeleton (D8): `step_1 × step_2 + q`.

**Rejection rules**: both branch rule-sets; answer ∉ {n_lk, n_code} ∪
record values ∪ list values; strict monotonicity makes either branch
corruption move the sink; U ≥ 3 keeps the code-branch counterfactual pool
nonempty.

**Renderer strings — lookup-first**:

- `resource_first`: `Retrieve {key}'s {field} from {H1}. Separately,
  remove later occurrences of repeated values from the integer sequence
  in {H2} and count the values greater than {t}. Return the product of
  the two results plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: {key}'s
  {field} recorded in {H1}, and the count of values greater than {t}
  after removing later occurrences of repeated values from the sequence
  in {H2}.`
- `bound_var`: `Let x be {key}'s {field} in {H1}. Let y be the count of
  values greater than {t} in the sequence from {H2} after removing later
  occurrences of repeated values. Output` `` `x × y + {q}` `` `.`

**Renderer strings — code-first**:

- `resource_first`: `Remove later occurrences of repeated values from the
  integer sequence in {H2} and count the values greater than {t}.
  Separately, retrieve {key}'s {field} from {H1}. Return the product of
  the two results plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: the count of
  values greater than {t} after removing later occurrences of repeated
  values from the sequence in {H2}, and {key}'s {field} recorded in
  {H1}.`
- `bound_var`: `Let x be the count of values greater than {t} in the
  sequence from {H2} after removing later occurrences of repeated values.
  Let y be {key}'s {field} in {H1}. Output` `` `x × y + {q}` `` `.`

**Reference program** (node ids order-independent): `n1 = lookup(H1, key,
field)`; `n2 = seq_count(xs={res H2}, t={lit})`; `n3 =
product_affine(x={node n1}, y={node n2}, q={lit})`; positions `[n1, n2,
n3]` (code-first: `[n2, n1, n3]`); sink `n3`.

**Reference subtasks**: branch subtasks of §3.1/§3.3; join — `Multiply
step_1 by step_2, then add {q}.`

**Example artifacts**: branches as §3.1/§3.3; join
`<artifact>step_1 * step_2 + 3</artifact>`.

**O (lookup-first)** — `R-5A8`: Aster.units = 31, Cedar.units = 14,
Grove.units = 39 (target Cedar); `R-1J7`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2,
7, 4]`, t = 5; q = 3. n1 = 14; n2 = 4; **59**. Counterfactuals: 14 → 15 ⇒
63; 4 → 3 ⇒ 45.

**O′ (code-first)** — same latent payloads/parameters, positions `[n2,
n1, n3]`: step 1 = count → 4; step 2 = lookup → 14; step 3 = **59**.
Code-first renderer strings; identical semantic oracle mapping. (Under
§1.9, an intervention on `n2` here overrides `step_1`.)

**B (minimum code count)** — `R-8D4`: Wren.crates = 99, Slate.crates =
10, Fern.crates = 57 (target Wren); `R-2K9`: `[4, 2, 4, 3, 1, 2, 3, 4]`,
t = 3; q = 20. U = 4; n2 = 1; n1 = 99; **119**. Counterfactuals: 99 → 98
⇒ 118; 1 → 2 ⇒ 218.

**Interventions** (edges `n1->n3`, `n2->n3`; one replacement each, scored
twice; eligibility per §1.9): `n1' ~
U(profile.cells.fork_join.value_band \ {n1})`; `n2' ~ U([1, U−1] \ {n2})`. Fork gate: per-branch corruption
drop ≥ 20 pts, paired clustered lower CI; old-answer persistence ≤ 10 %.

**One-call baseline**: B5, record + list. **Two-call baseline**: the
18-workflow family with frozen contracted subtasks (§1.11), best frozen
on construction data (§1.8 ordering).

---

## 4. Acceptance hooks (0A battery)

- **Golden fixtures**: every §3 worked example (incl. fork O′) —
  intermediates, gold, rejection/ablation/exclusion compliance,
  intervention targets.
- **Golden seed/ID fixture**: one full derivation pinned — seed_material
  bytes → `seed`, `hex8`, `latent_program_id`, `render_instance_id`, a
  block-seed/assignment pair, and an intervention seed + drawn
  replacement for one edge.
- **Byte-stability fixtures**: canonical rendered requests, one per cell
  × step × access pattern, incl. plural `Resources:` and all 18 shortcut
  workflows × 2 calls = 36 requests.
- **Normative load-time validation**: the loader recomputes and verifies
  ids, profile hash, public prompt bytes, gold, collision metadata,
  graph/resource shape, rejection invariants, and renderer identity —
  mismatch = load error.
- **Metamorphic tests**: `stable_unique` idempotence; count invariance
  under permutation of the deduplicated list; renderer invariance (three
  renderings share gold, interventions, reference program);
  handle-renaming invariance; distractor invariance (resampling
  non-target entities/fields/values leaves gold unchanged).
- **Provenance-based no-leakage**: private values provenance-tagged;
  renderer inputs contain no private-value provenance (structural); any
  prompt integer matching a private value must trace to a public
  parameter by provenance — using the frozen token boundaries of §1.13
  and excluding intentionally visible payload blocks.
- **IR validation tests**: every §1.3 rule violated once and rejected —
  incl. `mul_add` well-formedness, mixed-reference/cross-record
  rejections, literal-type and operand-name-matching violations.
- **Scheduler tests**: golden assignment fixture; joint contingency
  tables (±1); no aliasing; renderer crossing complete; block-boundary
  balance.
- **Oracle/comparator tests**: semantic→positional conversion for all six
  cells, fork in both orders; tie-breaking fixtures; **`best_fixed`,
  exact-uniform `random`, and signed deployable-assignment gap verified
  against a hand-enumerated toy payoff surface**.
- **Routing-schema tests**: length, type, duplicate, and out-of-range
  cases; bijection with the 3^S assignment set.
- **Grammar/limit tests**: every rejection code exercised; the global
  resource-error procedure in order, incl. **mixed-demand (`a + step_9`)
  and unavailable-step-only fixtures** and literal-only success
  with empty and incompatible binding sets; `E_RESOURCE_KIND` both
  directions; `E_UNCLOSED_ARTIFACT`; `E_MAGNITUDE`; `a--5`; envelope
  precedence cases incl. `</value>`.
- **Failure propagation**: each §1.7 rule; flag truth table asserted per
  outcome class, incl. the pseudo-worker row.
- **Intervention tests**: positional mapping in both fork orders;
  ineligibility handling; `override_applied` abort path; denominators;
  eligibility-rate reporting.
- **Pseudo-worker tests**: node-wise substitution protocol; no-op at true
  index zero recorded as `noop_correct`; echo token boundaries.
- **B2 tests**: payload block absent and binding set empty — resource-
  demanding artifacts draw the §1.6 typed errors, never payload values.
- **Collision tests**: node-level collisions (lookup value = q; fork
  count = t); sink-only vs node flags; provenance-derived values;
  sensitivity-score population identity (same clusters/observations/
  weights; only detected workflows recoded).
- **Shallow-predictor tests**: **golden feature-matrix/prediction
  fixture** (pins column order); refit determinism on identical
  construction data.
- **Sampler tests**: calls without explicit band arguments rejected;
  bands read from `profile.cells.*`; profile validation rejects missing
  cell fields; **invalid-profile fixtures — expect rejection at load**:
  each §1.14 profile-domain rule violated once (N < 3, undersized
  value-band cardinality, b < 10, m < 2, p < 2, L < 5 dedup, negative
  public literal, gold-≥-1-violating value band, min > max band,
  F_band.min = 0, `code_atomic.value_band.min` = 0, 13-digit public
  literal, `|S⁻(p_min, q_max)| < 2`); **`R_MAGNITUDE` fixtures — expect
  candidate rejection during generation, not load failure**: base-path
  and intervention-path overflow variants each rejected toward the
  stratum cap; **construction-inviable profile test**: a profile whose
  candidates all fail the exclusion rules (e.g. a degenerate
  modulus-only domain) reaches the resampling cap and returns a clean
  profile-screen failure, never an infrastructure exception;
  **S⁻ direct-draw test**: minus-form replacement pool is
  `S⁻(p, q) \ {n1}`, non-empty for every admitted instance.
- **Backend truncation**: cap-hit with and without envelope errors; gate
  metric reads `generation_hit_token_cap`; metadata survives cache hits.
- **Cache isolation**: intervention variants distinct; private/visible
  worker-side sharing asserted intentional under the worker-visible
  fingerprint; upstream completion reuse safe.
- **Split isolation**: no `latent_program_id` across namespaces; prefix
  evaluation deterministic.
- **Random valid-AST fuzzing**: `tools.py` vs `fuzz_oracle.py`
  (independent recursive AST evaluator in the test suite).
- **10k agreement command**: stratified by operator × cell; recorded
  acceptance command.

## 5. Decision register

| # | Decision | Rationale |
|---|---|---|
| D1 | Authorized payloads delivered in-context to the worker **and** bound host-side to its tool | Every candidate worker for a node receives the same local payload (primary causal condition); keeps the one-call baseline informative rather than trivially grammar-gated |
| D2 | No rotation in the count pipeline; the select shape retains it | Rotation can never affect `count_gt`, so a worker ignoring it would earn full reward — in Stage 3 an incomplete instruction would look successful; select gives rotation stakes |
| D3 | Keyed-record values pairwise distinct | Wrong-entity retrievals are scoreably wrong; corruption replacements always move downstream values |
| D4 | Numerals as digits in every renderer | Cross-cell consistency; one fewer nuisance dimension |
| D5 | Only the enumerated coincidences are rejection-guarded (operand echo, index echo, listed value collisions) | Lookup and Code-select answers necessarily occur in their payloads — the payloads are private; that is the design |
| D6 | m = L in `math_code` | Index validity by construction; the invalid-index rejection becomes a generator assert |
| D7 | Fixed name pools (20 entities, 10 fields), shared by all keyed cells | Nuisance control N4 |
| D8 | Single symmetric join skeleton `step_1 × step_2 + q` | Branch order immaterial to join semantics |
| D9 | Operand names `a, b, c, d` in order; modulus always `m` | Stable identifier grammar; no name/cell correlation |
| D10 | Workers receive the original public problem (`Problem` block) | Keeps the generic-subtask arm informative (without it, generic subtasks collapse to floor and the Stage-3 gate is vacuous); payload privacy, not prompt privacy, carries causal necessity |
| D11 | Cache stores raw completions under the worker-visible fingerprint; tools re-executed per call | Intervention and visibility variants safe by construction; byte-identical worker requests intentionally share completions across visibility conditions |
| D12 | Fork two-call shortcut = the enumerated 18-workflow contraction family with frozen contracted subtasks | Keeps the "best two-call" gate implementation-independent |
| D13 | `GENERIC_SUBTASK` carries no format instruction | Formatting lives in the fixed final line and system prompt, so the generic arm cannot fail on a formatting conflict |
| D14 | No negative literals / unary minus in any artifact grammar | Payloads and reference artifacts never need them; `a--5` becomes a clean `E_PARSE` |
| D15 | Public-numeric collisions flagged node-level, analysis-only — never rejected | Answer smuggling is a named failure mode worth observing; the clean headline is preserved by stratification (private, no-collision stratum) with the detected-token-penalized sensitivity score as secondary |
| D16 | System prompts (`SYSTEM_LOOKUP/MATH/CODE/DIRECT`) + demonstrations are a separately reviewed 0A freeze artifact | Prompt strings must be frozen against the real models, before the construction screen, under their own review |
| D17 | No-op pseudo-worker keeps value 0; `noop_correct` reported; node-wise substitution protocol | A pseudo-worker that always fails could not serve as a well-formed-wrong-value control; `math_code` permits true index 0, so 0 is not a guaranteed floor |

## 6. Errata against the rev6 plan contract — proposed for approval

1. `WorkerResult` typing superseded by the §1.7 union (incl. `synthetic`).
2. Lookup artifact form `lookup(resource, …)` with `R-` handles supersedes
   `lookup(Q31, …)`.
3. Canonical name of the plan: **the rev6 plan contract** (the file
   self-titles "v5").
4. "Best two-call shortcut" defined (§1.8/§1.11/D12).
5. "100 programs" = 100 latent clusters.
6. Deployable oracle is a semantic node-id mapping with the §1.8
   executable selection rule; the plan contract's positional phrasing is
   interpreted semantically.
7. Truncation split: `E_UNCLOSED_ARTIFACT` is syntax-only; the plan
   contract's < 2 % truncation gate reads `generation_hit_token_cap`; the
   parse-failure gate reads envelope + grammar errors.
8. Sequential qualification looks use pre-registered alpha spending (two
   schedules, §1.14); the plan contract's interval language is
   implemented with coverage-valid sequential inference.
9. **The primary Stage-2 comparator is the signed deployable-assignment
   gap** (§1.8); the plan contract's "routing regret" is retained as a legacy
   alias for the same quantity, which is unclipped and may be negative.

## 7. Freeze record

| Phase | Scope | Status |
|---|---|---|
| 1 | This file: operator semantics; grammars + envelope + global resource procedure + limits; public/private boundaries; observation/request + routing-schema contracts; IR schemas + validity rules; identity/seed derivations; reference functions; rejection-rule kinds (incl. modular exclusions, D15); intervention semantics + positional mapping + paired estimand; oracle/controls/comparator + selection rules; scheduler + profile-domain validation; renderer strings; baseline + pseudo-worker definitions incl. the shallow-predictor feature contract; caching fingerprints; telemetry contracts; decision register | **pending reviewer sign-off of this file (rev8 / v0.8)**; on sign-off, copied verbatim to the repository root as the frozen canonical reference |
| 2 | Every **(S)** band = the `profile.cells.*` difficulty profile (§1.14) | after the construction screen, before fresh qualification data |

The D16 system-prompt artifact freezes as a reviewed 0A artifact before
the construction screen. Any post-qualification change to generator,
renderer, prompt, tool, parser, or profile retires the affected
qualification set (plan contract 8).
