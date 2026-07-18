# Conductor cell specifications — v0.4 (rev4, phase-1 freeze candidate)

Revision of [`34_f_conductor_cell_specs_rev3.md`](34_f_conductor_cell_specs_rev3.md)
addressing the four phase-1 blockers, the pre-screening corrections, the
truncation/telemetry items, and the contract cleanups in
[`35_s_conductor_cell_specs_rev3_critique.md`](35_s_conductor_cell_specs_rev3_critique.md).
Supersedes v0.3 in full; self-contained. Plan contracts: **the rev6 contract**
([`13_f_plan_rev6.md`](13_f_plan_rev6.md)); errata in §6 are proposed for
approval as part of this sign-off.

**No worked example changed in this revision** — all §3 fixtures, golds,
rejection/ablation checks, and intervention targets carry over from v0.2/v0.3
and remain machine-verified, including the two new modular wrong-program
exclusions, which all three modular fixtures pass (verified: T2 O add-error
11 / sign-error 0 vs g = 2; `math_code` O 9 / 10 vs 8; B 0 / 3 vs 7).

**Two-phase freeze**: phase 1 on approval of this file; phase 2 after the
100-example construction screen ((S) ranges = the difficulty profile, §1.14).

## Disposition of critique items

| Item | Resolution |
|---|---|
| B1 T3 invalid under normative IR | §1.3/§2.1: new `mul_add` op (operand refs, `a·b + c`); `affine` keeps its single node-ref signature; all operand refs of one node must point at the same operands record |
| B2 scheduler cannot guarantee crossing | §1.14: block-level seed (`block_index`, not `latent_index`); frozen factor/level orders; partial-block truncation; prefix-balance claim weakened to block boundaries; golden assignment fixture |
| B3 oracle omits cells / self-contradicts | §1.8: node-id mapping table for all six cells; conditioning = (cell_id, node_id) only — **no execution-order conditioning**; deterministic tie-breaking by frozen endpoint index |
| B4 terminal-only collision flag | §1.16: node-level collision metadata (4 fields), provenance-derived, analysis-only; Stage-3 per-node / Stage-4 conservative subtask telemetry; clean stratum = private ∧ no node collision, sample size reported |
| No-op not a guaranteed floor | §1.11: retains value 0; `noop_correct` workflows reported (reachable via `math_code` true index 0); acceptance test added |
| Namespace counts vs sequential sampling | §1.13: predeclared **maxima** + immutable latent-index order + batch sizes + stopping rule; evaluation by deterministic prefixes |
| Target stratum ambiguity | §1.14: keyed-record cells only; `array_split` thirds; uniform within scheduled stratum; global-uniform claim removed |
| Modular error exclusions | §3.2/§3.5: `(a+b+c) mod m ≠ g` and `(a·b−c) mod m ≠ g` added; fixtures pass |
| Intervention edge cases | §1.9: eligibility (all base-run parents succeeded), `override_applied`, frozen denominators |
| B2 scope / guessing baseline / SYSTEM_DIRECT | §1.11: B2 restricted to resource-requiring steps; guessing baseline = declared family, construction-fit, frozen; `SYSTEM_DIRECT` added to the D16 artifact |
| Truncation semantics | §1.6/§1.7: `E_TRUNCATED` renamed **`E_UNCLOSED_ARTIFACT`**; independent per-call backend-truncation telemetry; rev6 truncation gate uses `generation_hit_token_cap`, not the envelope code; envelope-error precedence frozen; `artifact_valid`/`tool_executed` truth table |
| Smaller cleanups | §1.11 (B5 `E_NO_RESOURCE` vs `E_RESOURCE_KIND`), §1.10/§1.12 (visibility cache sharing intentional), §1.13 (UTF-8, digest length, echo token boundaries), §4 (normative load-time validation, named fuzz oracle, new tests) |

---

## 1. Global conventions

### 1.1 Integers and canonical wire form

- All public outputs are integers. Canonical decimal form at text→integer
  boundaries: `0` or `-?[1-9][0-9]*` (terminal answers parsed from text:
  direct baselines, deferred `<value>` control). `0012`, `+5`, `5.0`,
  `1,000`, internal whitespace rejected.
- Artifact grammars admit only nonnegative literals (`0 | [1-9][0-9]*`); no
  negative-literal token, no unary minus (D14). Negative intermediates from
  subtraction are legal.
- Digits-with-leading-zero → `E_NONCANONICAL_INT`; other malformed tokens →
  `E_PARSE`.
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

- Wrong layout/kind dereference → typed `E_RESOURCE_KIND`, never an
  exception. A Math endpoint may still read a keyed record in-context and
  emit literals (D1).
- `keyed` values pairwise distinct within a record (D3); `operands` names
  `a, b, c, d` in order, modulus always `m` (D9).
- Stored as ordered entry arrays (JSON objects are not semantically ordered;
  payload bytes and cache identity depend on order):

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

**Worker-facing payload text** (frozen; canonical integers, stored order, LF
newlines, no trailing whitespace):

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

**Normative per-operation schemas** (required args exactly; extra or missing
fields make the IR invalid; allowed ref kinds per slot; **no other
node/lit/operand mixtures are permitted** [rev4]):

| op | args (allowed refs) | semantics |
|---|---|---|
| `lookup` | `handle` (res, keyed), `key` (lit str), `field` (lit str) | keyed retrieval |
| `affine` | `x` (node), `p` (lit), `sign` (lit `"+"`/`"-"`), `q` (lit) | `p·x ± q` |
| `mul_add` | `a, b, c` (operand) | `a·b + c` [rev4 — T3's op; `affine`'s node-ref signature was unsatisfiable for it] |
| `ratio` | `a, b, c, d` (operand) | `(a·b − c) / d`, exact |
| `modular` | `a, b, c, m` (operand) | `(a·b + c) mod m`, m > 0 |
| `product_affine` | `x` (node), `y` (node), `q` (lit) | `x·y + q` |
| `seq_count` | `xs` (res, list), `t` (lit) | `count_gt(stable_unique(xs), t)` |
| `seq_select` | `xs` (res, list), `k` (lit), `i` (lit) | `at(rotate_left(stable_unique(xs), k), i)` |
| `seq_at` | `xs` (res, list), `i` (node) | `at(xs, i)` |

**IR validity rules** (generator-asserted, load-time validated; violations
are generator errors): unique node ids; `node` references acyclic, only to
declared nodes; **all `operand` references of one node point to the same
`operands` record** [rev4 — preserves one-resource-per-step]; `positions` is
a topological ordering containing every node exactly once — entry *k*
(1-based) is the semantic node executed as workflow step *k*; `sink` =
`positions[-1]`; every `res`/`operand` handle exists in manifest and registry
with a compatible layout; manifest keys = registry keys exactly.

Instance schema (collision block per §1.16 [rev4]):

```json
{
  "cell_id": "lookup_math",
  "latent_program_id": "lookup_math:qualification:00042:9f3ac1d2",
  "render_instance_id": "lookup_math:qualification:00042:9f3ac1d2:goal_first:private",
  "renderer_id": "goal_first",
  "split_id": "qualification",
  "visibility_condition": "private",
  "difficulty_profile_version": "dp-9a1b2c3d4e5f6071",
  "generator_version": "specs-v0.4+<code-version>",
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

Cluster identity = `latent_program_id`; "100 programs" = 100 latent clusters.
Reference subtasks and interventions derived deterministically, not stored.
Collision fields are **scorer/calibration-only metadata** (§1.16). Strip-test
consequence: the execution path never reads `reference_program`,
`gold_answer`, or collision metadata; only the scorer reads `gold_answer`.

### 1.4 Renderers

`resource_first` (canonical), `goal_first`, `bound_var`. Every latent program
is generated once and rendered in all three forms (one cluster); renderer is
not a scheduler factor. Paired visible renderings only for the designated
visible-slice clusters (§1.12). Frozen rules: template inputs are handles and
public parameters only; digits everywhere (D4); prompt typography `× − ÷
mod`, artifact ASCII; "zero-based" always; shared connective vocabulary (N5).
All renderer strings enumerated in §3.

### 1.5 Observation and request contracts

**Stage-0C/2 policy observation** (private condition; frozen skeleton; exact
system prompts are the D16 artifact):

```text
Problem:
{public_prompt}

Resources available: {manifest handles, comma-separated, manifest order}

Steps:
1. (resource: {handle|none}; previous results: {none|all}) {reference subtask 1}
2. ...

Choose one worker for each step.
```

Steps numbered in `positions` order (position → node observable; fork prompt
clause order tracks the same order, §3.6). Policy emits
`{"worker_ids": [...]}` only; extra fields rejected.

**Worker request template** — canonical, byte-stable; blocks in fixed order,
each present or omitted whole; one blank line between blocks; LF; no trailing
whitespace; canonical integers:

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
  predecessor in step order; these lines and host-side binding are the only
  predecessor channels.
- Direct baselines (B1/B3/B4) use the same blocks, replacing only the final
  line with the answer-line protocol (§1.11), under `SYSTEM_DIRECT` [rev4].
- `SYSTEM_LOOKUP` / `SYSTEM_MATH` / `SYSTEM_CODE` / **`SYSTEM_DIRECT`**
  [rev4] are the separately reviewed 0A freeze artifact (D16): checked in,
  reviewed, frozen before the construction screen, fingerprinted; later
  change retires qualification sets.
- **Canonical rendered request** = chat template over (system, user) bytes —
  cache-key component and byte-stability test target.

### 1.6 Artifact envelope, grammars, limits, typed rejections

**Envelope contract** — tokens are the exact byte strings `<artifact>` and
`</artifact>` (lower-case, no attributes; variants are ordinary text). With
n₀ = count of `<artifact>`, n₁ = count of `</artifact>` (plain substring
count; tag-like text in reasoning counts), **frozen precedence order**
[rev4]:

1. any `<value>` substring → `E_UNEXPECTED_TAG`
2. n₀ = 0 → `E_NO_ARTIFACT`
3. n₀ ≥ 2 ∨ n₁ ≥ 2 → `E_MULTI_ARTIFACT`
4. n₁ = 0 → `E_UNCLOSED_ARTIFACT` [rev4 — renamed from `E_TRUNCATED`: an
   unclosed tag does not prove backend truncation]
5. close before open → `E_PARSE`
6. else: content between tags trimmed, parsed by the endpoint grammar.

Text before/after the envelope is permitted and ignored.

**Backend truncation is recorded independently of envelope syntax** [rev4]:
every worker call logs `generation_hit_token_cap: bool`, `finish_reason`,
and `envelope_error: code | null`. **The rev6 < 2 % truncation gate is
computed from `generation_hit_token_cap`**, never from the envelope code;
the parse-failure gate uses envelope + grammar errors.

Endpoints (unchanged): Lookup = Qwen2.5-1.5B-Instruct + keyed retrieval;
Math = Qwen2.5-Math-1.5B-Instruct + exact calculator; Code =
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

**Tokenization and evaluation** (frozen): no negative literals / unary minus
(`a--5`, `--` → `E_PARSE`); precedence `* / %` over `+ -`, left-associative,
parentheses; whitespace between tokens; `/` exact in ℤ else
`E_INEXACT_DIV`, divisor 0 → `E_DIV_ZERO`; `%` floor-mod, modulus 0 →
`E_DIV_ZERO`, negative → `E_BAD_ARG`; `resource` binds the authorized
payload of the grammar-compatible kind/layout — nothing authorized →
`E_NO_RESOURCE`, authorized but incompatible → `E_RESOURCE_KIND`; Math
identifiers bind only against an `operands` record → `E_UNKNOWN_IDENT`
otherwise; `step_k` resolves iff access = `all` and `k <` step index;
`rotate_left` k ≥ 0 (`E_BAD_ARG`), rotates by `k mod len`; `at` zero-based
(`E_INDEX_RANGE`); `count_gt` strict.

**Uniform limits**: artifact ≤ 512 bytes (trimmed) → `E_PARSE`; AST ≤ 64
nodes, depth ≤ 8 → `E_DEPTH`; literal ≤ 12 digits → `E_PARSE`; any
intermediate/result |v| ≤ 10¹² → `E_MAGNITUDE`.

**Typed rejection codes**: `E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`,
`E_UNCLOSED_ARTIFACT`, `E_UNEXPECTED_TAG`, `E_PARSE`, `E_NONCANONICAL_INT`,
`E_UNKNOWN_IDENT`, `E_NO_RESOURCE`, `E_RESOURCE_KIND`, `E_UNKNOWN_KEY`,
`E_UNKNOWN_FIELD`, `E_INDEX_RANGE`, `E_INEXACT_DIV`, `E_DIV_ZERO`,
`E_BAD_ARG`, `E_DEPTH`, `E_MAGNITUDE`. All take the contract-4 path;
unexpected exceptions propagate and abort.

**Primitive semantics** (independent implementations in `tools.py` and
`program.py`; 10k agreement stratified by operator × cell): `stable_unique`,
`rotate_left`, `at`, `count_gt`, `lookup`, numeric ops of §2.1.

### 1.7 WorkerResult, flags, failure propagation

```text
status         ∈ {success, typed_failure, dependency_blocked}
value          : int | null      (int iff success)
rejection_code : code | null     (set iff typed_failure)
artifact_valid : bool
tool_executed  : bool
```

**Flag truth table (frozen)** [rev4]:

| outcome | artifact_valid | tool_executed |
|---|---|---|
| envelope failure (codes 1–5 of §1.6) | false | false |
| grammar/limit failure (`E_PARSE`, `E_NONCANONICAL_INT`, `E_DEPTH`) | false | false |
| semantic tool rejection (`E_UNKNOWN_IDENT`, `E_NO_RESOURCE`, `E_RESOURCE_KIND`, `E_UNKNOWN_KEY`, `E_UNKNOWN_FIELD`, `E_INDEX_RANGE`, `E_INEXACT_DIV`, `E_DIV_ZERO`, `E_BAD_ARG`, `E_MAGNITUDE`) | true | true |
| success | true | true |
| dependency_blocked (no call made) | false | false |

Per-call telemetry record: `generation_hit_token_cap`, `finish_reason`,
`envelope_error` (§1.6).

Propagation: a step whose status ≠ `success` blocks every later step with
access = `all` (`dependency_blocked`, no worker call); access = `none` steps
unaffected; a join is blocked if either branch fails; terminal = sink value,
sink not `success` → terminal null → 0.5; only infrastructure failures abort.

### 1.8 Deployable oracle: semantic assignment

The deployable oracle is a **node-id → endpoint mapping covering all six
cells** [rev4]:

| cell | mapped nodes |
|---|---|
| `lookup_atomic` | n1 |
| `math_atomic` | n1 |
| `code_atomic` | n1 |
| `lookup_math` | n1, n2 |
| `math_code` | n1, n2 |
| `fork_join` | n1 (lookup branch), n2 (code branch), n3 (join) |

Rules (frozen):

- Node ids are stable IR identifiers; `positions` alone permutes the mapping
  into positional `worker_ids`. **The mapping never conditions on execution
  order** [rev4 — the node id already carries branch identity; order
  conditioning is unnecessary and forbidden]. Allowed conditioning fields:
  **(cell_id, node_id) only** — no latent-subtype conditioning in v0
  (subtype payoff heterogeneity is reported descriptively in qualification,
  §1.14, but the deployable mapping stays fixed).
- Selected **jointly per cell** on construction performance, frozen,
  evaluated on fresh qualification data, never reselected.
- **Deterministic tie-breaking** [rev4]: endpoints carry frozen indices
  0 = Lookup, 1 = Math, 2 = Code; ties in construction accuracy (oracle or
  runner-up selection) resolve to the lowest index.
- All oracle-derived quantities are node-level and converted positionally:
  Stage-2 targets, runner-up substitutions, effective-routing-stakes gate,
  routing regret, best-fixed and random controls, cold-start arithmetic
  (96 / 61 / 26 %, order-invariant).
- Hindsight per-example maximum: diagnostic only.

### 1.9 Interventions: mediator (wire) semantics

Both kinds per dependency edge *(u → v)*, on the deployable-oracle
assignment at calibration time; mediator/wire interventions (resource-level
counterfactuals deferred). One replacement *r* per `(latent_program_id,
edge)` (seed omits scoring kind, §1.13); **one mutated execution scored
twice**:

1. Override step *u*'s recorded value with *r* (calibration-only), in both
   channels (`step_u = r` context line and host-side binding); log
   **`override_applied: bool`** [rev4].
2. Rerun downstream worker(s); distinct cache identity automatic; upstream
   completions reusable.
3. Score vs stored `gold_answer` → **corruption** accuracy and **old-answer
   persistence** (mutated runs still producing original gold; CE1 ≤ 10 %).
4. Score the same terminal vs `gold'` (reference sink recomputed outside the
   executor) → **counterfactual consistency**.
5. `kind` only in result records.

**Eligibility and denominators (frozen)** [rev4]:

- An edge instance is **intervention-eligible** iff **every parent of the
  downstream node succeeded in the base execution** (intervened parent
  included). Ineligible instances are excluded from both metrics and
  counted/reported (`intervention_ineligible`).
- Full-sample metrics: over all eligible edge instances.
- **Conditional follow-through**: over eligible instances whose mutated run
  has the intervened parent and every other required parent `success`
  (reused completions make non-intervened parents match the base run).

Replacement rules per cell (§3) provably change the sink. Atomic cells: no
edges. Missing/skip variants prove only input-validation.

### 1.10 Caching rule

Cache stores raw model completions, keyed by `runtime-profile fingerprint +
endpoint fingerprint + canonical rendered request bytes`. Tools re-executed
per call; executed `WorkerResult` never cached. **Visibility note** [rev4]:
worker-side requests are byte-identical across private/visible conditions,
so worker completions are **intentionally shared** across visibility; the
"distinct keys" guarantee applies to Conductor-side generations and to
intervention variants (whose worker request bytes differ).

### 1.11 Baselines and diagnostic workers — executable definitions

Direct arms (B1/B3/B4; system prompt `SYSTEM_DIRECT` [rev4]) use the
answer-line protocol: final line `Answer with a single integer on the final
line.`; the last non-empty line, trimmed, must parse as a canonical integer,
else scored wrong.

| # | Arm | Model | Input |
|---|---|---|---|
| B1 | Public-only direct | 3B base | `Problem` only. Reported against majority-class and the **frozen public-feature guessing baseline** [rev4]: family = {per-(cell, subtype) majority value} ∪ {each single public parameter as the answer}; the best member per cell selected on **construction data only**, then frozen for qualification. Leakage is decided by provenance, never accuracy ≈ 0 |
| B2 | Endpoint-without-resource | each endpoint | worker request minus `Resource` — **resource-requiring steps only** [rev4] (steps that request none are out of scope; removing a nonexistent block changes nothing) |
| B3 | Visible direct | 3B base | `Problem` + plural `Resources:`. Diagnoses self-solving; no `SELF` ⇒ not delegation |
| B4 | Local-node | 3B base | same blocks as an endpoint worker (`Problem`, `Task` = node reference subtask, `Resource` = node payload, `Previous results` = gold predecessor values); only the final line differs |
| B5 | One-call whole-task | each endpoint | `Problem` + `Task: Complete the task and return the final result.` + plural `Resources:` (union payload, harness-only). Binding: exactly one grammar-compatible payload → bind; **no authorized resource at all → `E_NO_RESOURCE` on tool use; authorized but none compatible → `E_RESOURCE_KIND`** [rev4]; more than one compatible → harness configuration error in v0. Incompatible payloads remain readable in-context |
| B6 | Generic-subtask arm | endpoints per deployable oracle | reference workflow, every subtask = `GENERIC_SUBTASK` |

- `GENERIC_SUBTASK` (frozen): `Complete the assigned step using the problem
  context, any provided resource, and any previous results.`
- Best one-call: endpoint selected on construction data, frozen; hindsight
  max diagnostic only.
- Fork two-call shortcut family: 18 two-step `[none, all]` chains (both
  resource orientations × 3 × 3 endpoints), enumerated at construction; best
  frozen. Contracted subtasks (frozen verbatim):
  - *Lookup-first*: 1. `Retrieve {key}'s {field} value from the requested
    resource.` 2. `Remove later occurrences of repeated values from the
    integer sequence in the requested resource, count the values greater
    than {t}, multiply that count by step_1, and add {q}.`
  - *Code-first*: 1. `Remove later occurrences of repeated values from the
    integer sequence in the requested resource and count the values greater
    than {t}.` 2. `Retrieve {key}'s {field} value from the requested
    resource, multiply it by step_1, and add {q}.`
- **Diagnostic pseudo-workers**:
  - *Echo worker*: value = last canonical-integer token in its `Task` block
    (token boundaries per §1.13), else `typed_failure(E_PARSE)`.
  - *No-op worker*: value = 0 always. **Not a guaranteed floor** [rev4]:
    `math_code` permits true intermediate index 0, so a no-op upstream can
    yield a correct workflow; `noop_correct` workflows are reported, and the
    acceptance battery includes a true-index-zero case. (Golds ≥ 1 keep
    no-op-as-sink always wrong.)
  - *Answer-in-subtask telemetry* (always on, Stages 3–4): node-level per
    §1.16.
- Reporting: prompt tokens and tool-call counts per condition;
  context-partitioning wins identified as such.

### 1.12 Visibility conditions

`visibility_condition` ∈ {`private`, `visible`}. Visible rendering appends
the plural `Resources:` block after the Conductor-side `Problem` block.
Worker-side requests identical in both conditions (completions shared,
§1.10). Visible variants only for the designated visible-slice clusters
(~100 latent programs, pre-registered), paired by `latent_program_id` and
split. Visibility enters `render_instance_id`, observation bytes, and the
profile's visibility policy fingerprint.

### 1.13 Identity, randomness, splits

- **Hash-to-integer**: `h64(s) =` first 8 bytes of `SHA-256(s)`, big-endian
  unsigned; **all seed strings UTF-8** [rev4]; separator ␟ = 0x1F.
- **PRNG**: NumPy `Generator(PCG64(seed))`, version pinned by lockfile.
- **Generation identity**: `seed_material = "qwen-grpo-conductor" ␟
  generator_version ␟ difficulty_profile_version ␟ namespace ␟ cell_id ␟
  latent_index` — a profile change changes every derived id.
- **Labelled per-instance substreams**: child seed = `h64(seed_material ␟
  label)`, labels `"values"`, `"names"`, `"handles"`, `"manifest"`,
  `"intervention"`. **The factor scheduler uses a block-level seed, not a
  per-instance substream** [rev4] (§1.14).
- `latent_program_id = "{cell_id}:{namespace}:{latent_index:05d}:{hex8}"`;
  `render_instance_id = latent_program_id + ":" + renderer_id + ":" +
  visibility_condition`.
- **Intervention replacements**: PRNG seeded by `h64("intervention" ␟
  latent_program_id ␟ edge_label)`; no scoring kind in the seed.
- **Canonical JSON** (profile hash, hashed configs): UTF-8, sorted keys,
  separators `(",", ":")`, integers only. **`difficulty_profile_version` =
  `"dp-"` + first 16 hex chars (8 bytes) of the SHA-256** [rev4].
- **Echo/collision integer-token boundaries** [rev4]: canonical integer
  tokens are matches of `-?(0|[1-9][0-9]*)` not adjacent to a digit or word
  character (regex `(?<![\w-])-?(0|[1-9][0-9]*)(?![\w])`), applied to
  subtask text.
- **Namespaces** `construction, qualification, train, dev, test`: disjoint
  generation universes. **Sequential-sampling compatibility** [rev4]:
  pre-declare per namespace the **maximum** latent count, the immutable
  latent-index order (0…max−1), the expansion batch size, and the stopping
  rule (rev6: start 100, +200 batches, cap ≈ 500/cell). Generation may
  materialize the maximum pool upfront; evaluation proceeds over
  **deterministic prefixes** of the latent-index order, so expanding never
  changes which programs would have been evaluated. No latent program
  crosses namespaces (unit-tested).

### 1.14 Distributions and sampling protocol

- **Numeric parameters**: independent integer-uniform on (S) bands unless
  stated; T1 constructive `c` (uniform on `{c ∈ [1,20] : c ≡ a·b (mod d)}`);
  records — entities/fields uniform without replacement, values uniform
  without replacement; dedup lists i.i.d. uniform [1, 9] then rules; select
  lists uniform without replacement [1, 99].
- **Target stratum — keyed-record cells only** [rev4] (`lookup_atomic`,
  `lookup_math`, `fork_join`): entity indices 0…N−1 split into thirds by
  `numpy.array_split(range(N), 3)` (first/middle/last); the scheduled
  stratum picks the third; **the target entity is uniform within its
  scheduled stratum and the target field is uniform** — there is no
  competing global-uniform-position claim.
- **Categorical factor scheduler (frozen)** [rev4 — block-level seeding;
  the v0.3 per-instance `factor_perm` substream could not produce one shared
  permutation per block]:

```text
factors/levels per cell, in frozen order (first factor most significant;
cartesian product in lexicographic order over the frozen level orders):
  lookup_atomic: target_stratum (first, middle, last)                 B = 3
  math_atomic:   template (T1, T2, T3)                                B = 3
  code_atomic:   shape (count, select)                                B = 2
  lookup_math:   sign (minus, plus) × target_stratum (f, m, l)        B = 6
  math_code:     — (no categorical factors)                           B = 1
  fork_join:     branch_order (lookup_first, code_first) ×
                 target_stratum (f, m, l)                             B = 6

block_index = latent_index // B
offset      = latent_index %  B
block_seed  = h64("qwen-grpo-conductor" ␟ generator_version ␟
                  difficulty_profile_version ␟ namespace ␟ cell_id ␟
                  "factor_perm" ␟ block_index)
assignment  = permutation(cartesian_product, PCG64(block_seed))[offset]
```

  Partial final block: the same permutation, truncated — joint counts differ
  by at most one overall. **Balance guarantee: exact at block boundaries and
  ±1 overall; arbitrary sequential prefixes are *not* guaranteed balanced**
  [rev4 — weakened as required]. A golden fixture pins expected assignments
  for a known seed (§4).
- **Telemetry at the construction screen**: rejection counts by rule;
  post-rejection marginals; maximum acceptable rejection rate 75 % **per
  latent subtype**; exceeding it fails the difficulty profile (fix the
  profile; never hand-prune).
- **Pre-registration rule**: no individual instance is ever retained or
  discarded based on worker performance; only an entire difficulty profile
  or cell passes or fails construction screening.
- **Difficulty profile** = canonical JSON of every (S) band and
  distribution; version string per §1.13; part of generation identity;
  frozen at phase 2.
- **Qualification reporting stratified by latent subtype**: T1/T2/T3,
  count/select, plus/minus, renderer, fork order — including per-subtype
  payoff surfaces (descriptive; the deployable mapping stays fixed, §1.8).
- Per-instance resampling cap 1000 attempts; rules re-asserted at load time.

### 1.15 Balance enforcement and shortcut audit

1. **Structural gates** (generator-enforced, unit-tested): joint contingency
   tables per cell × split (counts ±1); handle characters uniform; manifest
   order shuffled; all three renderings per latent program; splits balanced
   across factors.
2. **Statistical leakage checks — randomized fields only, within latent
   subtype**: {handle strings, entity names, field names, renderer id,
   split id} × subtype; cluster-aware permutation test (clusters = latent
   programs; 10,000 permutations) against within-subtype answer quartiles;
   α = 0.01 Holm-corrected. Failures are investigated as generator defects.
3. **Descriptive diagnostics, not gates**: prompt-length distributions
   (length legitimately tracks workload); shallow bag-of-words router
   accuracy (expected high; acceptable for the rev6 claim).
4. Anti-template gate reserved for the deferred semantic renderer; no second
   Lookup→Math resource. Legitimate semantic cues remain by design.

### 1.16 Public-numeric collision metadata [rev4 — node-level, analysis-only]

Derived from **provenance-tagged semantic parameters** (the applicable
public parameters `p, q, t, k, i` per cell), never by scanning rendered
text. Stored per instance:

```text
public_numeric_values:          parameter name → value
public_numeric_collision_nodes: node_id → [matching parameter names]
                                (node's reference value equals the public value)
public_numeric_collision:       true iff any node matches
sink_public_numeric_collision:  true iff the sink matches
```

Rationale (v0.3's terminal-only flag was insufficient): in composed cells an
*intermediate* can equal a public number (lookup value = `q`; fork count =
`t`) and be smuggled through a learned subtask while the final answer shows
no collision — the "clean" stratum would not have been clean.

- **Stage-3 telemetry**: compare each authored subtask against **its node's
  reference value** (token boundaries §1.13).
- **Stage-4 telemetry** (positions not fixed): conservatively flag **any
  reference-node value appearing in any authored subtask**.
- All collision fields and telemetry are **scorer/calibration-only** —
  invisible to the policy, workers, and the normal executor path.
- **Clean headline stratum** = `private` ∧ `public_numeric_collision =
  false` (no node-level match), with its **sample size reported**. D15
  (flag, not reject) stands as endorsed by the reviewer under exactly this
  node-level, analysis-only construction.

### 1.17 Name pools

20 entities (Aster, Birch, Cedar, Elm, Fern, Grove, Hazel, Ivory, Juniper,
Lark, Maple, Nettle, Onyx, Pine, Quill, Rowan, Slate, Tarn, Vale, Wren);
10 fields (crates, units, tokens, points, seats, kits, spools, tiles,
flasks, reams); operand identifiers per D9 (D7).

---

## 2. Shared generator machinery

### 2.1 Primitive ops and reference functions

```python
def prim_lookup(rec, key, field) -> int           # keyed retrieval (layout=keyed only)
def prim_affine(x, p, sign, q) -> int             # p*x + q  |  p*x - q
def prim_mul_add(a, b, c) -> int                  # a*b + c            [rev4]
def prim_ratio(a, b, c, d) -> int                 # (a*b - c) / d, exact else raise
def prim_modular(a, b, c, m) -> int               # (a*b + c) % m, m > 0
def prim_product_affine(x, y, q) -> int           # x*y + q
def prim_seq_count(xs, t) -> int                  # count_gt(stable_unique(xs), t)
def prim_seq_select(xs, k, i) -> int              # at(rotate_left(stable_unique(xs), k), i)
def prim_seq_at(xs, i) -> int                     # at(xs, i)
```

(`prim_mul_add` may share an arithmetic helper with `prim_modular`'s
numerator; the distinct op exists for IR validation and provenance.)

### 2.2 Shared samplers

`integer_record(N, F, band, layout)` (ordered entries);
`integer_list_dedup(L, band=[1,9])` with `3 ≤ U ≤ L − 2`;
`integer_list_select(L, band=[1,99])` pairwise distinct.

---

## 3. Cell specifications

Unchanged from v0.3 except: `math_atomic` T3 uses `mul_add` (§3.2); the two
modular wrong-program exclusions are added (§3.2, inherited by §3.5); the
oracle pointer is §1.8. **All fixtures, golds, rejection and ablation
checks, and intervention targets are identical to v0.2/v0.3** and remain
machine-verified. Conventions: **O** ordinary, **B** boundary; example
artifacts illustrate the grammar; no gold worker presumed; reference
subtasks tool-neutral; renderer strings enumerated in full.

### 3.1 `lookup_atomic` — atomic Lookup

**Shape**: 1 step, access `[none]`, 1 keyed `integer_record`.

| Parameter | Range |
|---|---|
| entities N | 3–16 **(S)**, `N × F ≤ 60` |
| fields F | 1–5 **(S)** |
| value band | 10–99 **(S)**, pairwise distinct |
| target (key, field) | stratified per §1.14; field uniform |

**Rejection rules**: none beyond record invariants.

**Renderer strings**:

- `resource_first`: `Resource {H} contains keyed integer records. Return the
  {field} value recorded for {key}.`
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
Lark.units = 99, Onyx.units = 10, Pine.units = 11, Quill.units = 98; target
Quill.units. Gold: **98**.

**Interventions**: none (atomic). **One-call baseline**: B5, the record.

### 3.2 `math_atomic` — atomic Math (hidden operands, public formula)

**Shape**: 1 step, access `[none]`, 1 `operands`-layout record.

| Template | Public formula | IR op | Operands |
|---|---|---|---|
| T1 ratio | `(a × b − c) ÷ d` | `ratio` | a, b, c, d |
| T2 modular | `(a × b + c) mod m` | `modular` | a, b, c, m |
| T3 affine | `a × b + c` | `mul_add` [rev4] | a, b, c |

| Parameter | Range |
|---|---|
| a | 10⁴–10⁶ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** (T1 constructive) |
| d (T1) | 2–12 **(S)** |
| m (T2) | 5–60 **(S)** |

**Rejection rules**: answer ∈ [1, 10⁹]; T2 answer ∈ [1, m−1]; answer ∉
operand values; **modular checks** (every modular node, here and `math_code`
n1; `g` = residue):

- operand relevance: drop-c `(a·b) mod m ≠ g`; a→1 `(b+c) mod m ≠ g`; b→1
  `(a+c) mod m ≠ g`;
- **wrong-program exclusions** [rev4]: mul→add `(a+b+c) mod m ≠ g`;
  sign-flip `(a·b−c) mod m ≠ g` — common wrong programs must not earn full
  reward.

(T1/T3 relevance band-guaranteed: b ≥ 10, c ≥ 1, d ≥ 2.)

**Renderer strings** (`{names}` = `a, b, c and d` / `a, b, c and m` /
`a, b and c`):

- `resource_first`: `{H} contains integers {names}. Evaluate`
  `` `{formula}` `` `exactly.`
- `goal_first`: `Return the exact value of` `` `{formula}` `` `, where
  {names} are the integers recorded in {H}.`
- `bound_var`: `Let {names} be the integers in {H}. Output`
  `` `{formula}` `` `.`

**Reference program**: `n1 = ratio | modular | mul_add` with `operand`
references (all into the same record, §1.3); positions `[n1]`; sink `n1`.

**Reference subtask**: `Evaluate` `` `{formula}` `` `exactly using the
integers in the requested resource.`

**Example artifact**: `<artifact>(a * b - c) / d</artifact>`

**O (T1)** — `R-2P6`: a = 83719, b = 43, c = 1, d = 6. **599986**.

**O (T2)** — `R-7Q4`: a = 999983, b = 89, c = 19, m = 12. Residues 11, 5, 7:
g = **2**. (Relevance: drop-c 7, a→1 0, b→1 6 — all ≠ 2 ✓. Exclusions
[rev4]: mul→add 11 ≠ 2 ✓; sign-flip 0 ≠ 2 ✓.)

**O (T3)** — `R-1X5`: a = 524287, b = 83, c = 17. **43515838** (op
`mul_add`; value unchanged).

**B (T1, low edges)** — `R-8B2`: a = 10007, b = 10, c = 2, d = 6.
**16678**.

**Interventions**: none (atomic). **One-call baseline**: B5, operand record.

### 3.3 `code_atomic` — atomic Code (one call, nested composition)

**Shape**: 1 step, access `[none]`, 1 dedup-flavor `integer_list`.

| Shape | Latent pipeline |
|---|---|
| count | `count_gt(stable_unique(xs), t)` |
| select | `at(rotate_left(stable_unique(xs), k), i)` |

| Parameter | Range |
|---|---|
| L | 8–16 **(S)**, values 1–9 **(S)** |
| U | 3 ≤ U ≤ L − 2 |
| k (select) | 1–9 **(S)**, `k mod U ≠ 0` |
| t (count) | 1–8 **(S)** |
| i (select) | 0…U−1 |

**Rejection rules**: `3 ≤ U ≤ L − 2`; count — `1 ≤ answer ≤ U − 1`, dedup
ablation `count_gt(xs, t) ≠ count_gt(stable_unique(xs), t)`; select —
`k mod U ≠ 0`, dedup ablation `at(rotate_left(xs, k), i) ≠ gold`, rotation
ablation `at(stable_unique(xs), i) ≠ gold`.

**Renderer strings — count**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values and count the values greater than {t}.`
- `goal_first`: `Return how many values exceed {t} in the sequence obtained
  from {H} by removing later occurrences of repeated values.`
- `bound_var`: `Let s be the sequence in {H} after removing later
  occurrences of repeated values. Output the count of values in s greater
  than {t}.`

**Renderer strings — select**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values, rotate the remaining sequence left by {k}
  positions, and return the value at zero-based index {i}.`
- `goal_first`: `Return the value at zero-based index {i} of the sequence
  obtained from {H} by removing later occurrences of repeated values and
  rotating it left by {k} positions.`
- `bound_var`: `Let s be the sequence in {H} after removing later
  occurrences of repeated values and rotating left by {k} positions. Output
  the value of s at zero-based index {i}.`

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

**O (select)** — `R-5N1`: `[5, 3, 5, 8, 1, 3, 9, 2]`, k = 2, i = 4. U = 6;
`rotate_left(2) → [8, 1, 9, 2, 5, 3]`; **5**. (Ablations 9 ≠ 5, 9 ≠ 5 ✓.)

**B (count, answer = U − 1)** — `R-9E3`: `[9, 8, 9, 7, 6, 8, 5, 9]`, t = 5.
U = 5; **4**. (Dedup ablation 7 ≠ 4 ✓.)

**Interventions**: none (atomic). **One-call baseline**: B5, the list.

### 3.4 `lookup_math` — Lookup → Math

**Shape**: 2 steps, access `[none, all]`; keyed record at step 1; step 2
requests none, consumes `step_1`.

| Parameter | Range |
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
- `bound_var`: `Let x be {key}'s {field} in {H}. Output` `` `{p}x − {q}` ``
  `.`

**Renderer strings — plus form**:

- `resource_first`: `Retrieve {key}'s {field} from {H}. Return {p} times
  that value plus {q}.`
- `goal_first`: `Return the number obtained by adding {q} to {p} times
  {key}'s {field} recorded in {H}.`
- `bound_var`: `Let x be {key}'s {field} in {H}. Output` `` `{p}x + {q}` ``
  `.`

**Reference program**: `n1 = lookup(...)`; `n2 = affine(x={node n1},
p={lit}, sign={lit}, q={lit})`; positions `[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Retrieve {key}'s {field} value from the
requested resource.` 2. `Multiply step_1 by {p}, then subtract {q}.` (plus:
`…, then add {q}.`)

**Example artifacts**:
`<artifact>lookup(resource, "Cedar", "units")</artifact>`;
`<artifact>3 * step_1 - 4</artifact>`

**O** — `R-3T5`: Aster.units = 31, Cedar.units = 17, Grove.units = 39,
Ivory.units = 53; target Cedar.units; p = 3, minus, q = 4. `n1 = 17`;
**47**.

**B (band edges)** — `R-2W9`: Vale.units = 99, Aster.units = 10,
Hazel.units = 23, Tarn.units = 57; target Vale.units; p = 9, minus, q = 20.
**871**.

**Interventions** (edge `n1->n2`; §1.9): `n1' ~ U([10, 99] \ {n1})`,
resampled until `affine(n1') ≥ 1`. Example (O): `n1' = 19` — corruption
target 47 (run yields 53, wrong); counterfactual target 53.

**One-call baseline**: B5, the record; screen tunes N/F/distractors for the
+20-point gate.

### 3.5 `math_code` — Math → Code (computed index)

**Shape**: 2 steps, access `[none, all]`; step 1 = operand record; step 2 =
list, consumes `step_1`.

| Parameter | Range |
|---|---|
| a | 10⁸–10⁹ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** |
| m = L | 8–16 **(S)** (D6) |
| list | select-flavor, 1–99 **(S)**, pairwise distinct |

**Rejection rules**: list pairwise distinct (counterfactual indices always
change the answer); answer ≠ n1; answer ∉ {a, b, c, m}; **all §3.2 modular
checks on n1** (relevance + mul→add and sign-flip exclusions [rev4]);
intermediate n1 = 0 permitted (terminal ≥ 1 via list band).

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
**56**. (Relevance 3/0/2 ≠ 8 ✓; exclusions [rev4]: mul→add 9 ≠ 8 ✓,
sign-flip 10 ≠ 8 ✓.)

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
Diagnostic-only in v0; qualification slice 100–200 latent clusters if paired
CIs are decisive. If admitted to Stage-2 routing after its gates, fork/join
tests endpoint selection within a fixed parallel DAG; topology construction
remains a Stage-4 claim.

**Branch order**: scheduled 50/50 (§1.14); `positions` records it; the
Stage-2 observation and public prompt clause order track it. The deployable
oracle maps node ids and is order-invariant (§1.8).

| Parameter | Range |
|---|---|
| record N, F, band | as §3.1; n_lk ∈ [10, 99] |
| code branch | count shape of §3.3 (U ≥ 3, ablation rules) |
| q | 1–20 **(S)** |

Join skeleton (D8): `step_1 × step_2 + q`.

**Rejection rules**: both branch rule-sets; answer ∉ {n_lk, n_code} ∪
record values ∪ list values; strict monotonicity makes either branch
corruption move the sink; U ≥ 3 keeps the code-branch counterfactual pool
nonempty.

**Renderer strings — lookup-first**:

- `resource_first`: `Retrieve {key}'s {field} from {H1}. Separately, remove
  later occurrences of repeated values from the integer sequence in {H2}
  and count the values greater than {t}. Return the product of the two
  results plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: {key}'s {field}
  recorded in {H1}, and the count of values greater than {t} after removing
  later occurrences of repeated values from the sequence in {H2}.`
- `bound_var`: `Let x be {key}'s {field} in {H1}. Let y be the count of
  values greater than {t} in the sequence from {H2} after removing later
  occurrences of repeated values. Output` `` `x × y + {q}` `` `.`

**Renderer strings — code-first**:

- `resource_first`: `Remove later occurrences of repeated values from the
  integer sequence in {H2} and count the values greater than {t}.
  Separately, retrieve {key}'s {field} from {H1}. Return the product of the
  two results plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: the count of
  values greater than {t} after removing later occurrences of repeated
  values from the sequence in {H2}, and {key}'s {field} recorded in {H1}.`
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

**O′ (code-first)** — same latent payloads/parameters, positions `[n2, n1,
n3]`: step 1 = count → 4; step 2 = lookup → 14; step 3 = **59**. Code-first
renderer strings; identical semantic oracle mapping.

**B (minimum code count)** — `R-8D4`: Wren.crates = 99, Slate.crates = 10,
Fern.crates = 57 (target Wren); `R-2K9`: `[4, 2, 4, 3, 1, 2, 3, 4]`, t = 3;
q = 20. U = 4; n2 = 1; n1 = 99; **119**. Counterfactuals: 99 → 98 ⇒ 118;
1 → 2 ⇒ 218.

**Interventions** (edges `n1->n3`, `n2->n3`; one replacement each, scored
twice; eligibility and follow-through per §1.9 — the other branch must have
succeeded): `n1' ~ U([10, 99] \ {n1})`; `n2' ~ U([1, U−1] \ {n2})`. Fork
gate: per-branch corruption drop ≥ 20 pts, paired clustered lower CI;
old-answer persistence ≤ 10 %.

**One-call baseline**: B5, record + list. **Two-call baseline**: the
18-workflow family with frozen contracted subtasks (§1.11), best frozen on
construction data.

---

## 4. Acceptance hooks (0A battery)

- **Golden fixtures**: every §3 worked example (incl. fork O′) —
  intermediates, gold, rejection/ablation/exclusion compliance, intervention
  targets.
- **Byte-stability fixtures**: canonical rendered requests, one per cell ×
  step × access pattern, incl. plural `Resources:` and **all 18 two-call
  shortcut requests** [rev4].
- **Normative load-time validation** [rev4]: the loader recomputes and
  verifies ids, profile hash, public prompt bytes, gold, collision metadata,
  graph/resource shape, rejection invariants, and renderer identity —
  any mismatch is a load error.
- **Metamorphic tests**: `stable_unique` idempotence; count invariance under
  permutation of the deduplicated list; renderer invariance (three
  renderings share gold, interventions, reference program); handle-renaming
  invariance; distractor invariance (resampling non-target entities/fields/
  values leaves gold unchanged).
- **Provenance-based no-leakage**: private values provenance-tagged;
  (a) renderer inputs contain no private-value provenance (structural);
  (b) any prompt integer matching a private value must trace to a public
  parameter by provenance.
- **IR validation tests**: every §1.3 rule violated once and rejected —
  incl. **T3 `mul_add` well-formedness and the mixed-reference/cross-record
  rejections** [rev4].
- **Scheduler tests** [rev4]: golden fixture of exact assignments for a
  known seed; joint contingency tables (±1); no aliasing; renderer crossing
  complete; block-boundary balance.
- **Oracle tests** [rev4]: semantic→positional conversion for **all six
  cells**, fork in both orders; deterministic tie-breaking.
- **Grammar/limit tests**: every rejection code exercised, incl.
  `E_RESOURCE_KIND` (both directions of the B5 zero-case split),
  `E_UNCLOSED_ARTIFACT`, `E_MAGNITUDE`, future/unavailable `step_k`,
  `a--5`, envelope precedence cases (`<value>` + no artifact, attributes,
  case variants, close-before-open, tag text in reasoning).
- **Failure propagation**: each §1.7 rule; flag truth table asserted per
  outcome class.
- **Intervention tests** [rev4]: ineligibility handling (failed base-run
  parent → excluded and counted); `override_applied` logging; denominators.
- **Collision tests** [rev4]: node-level collisions (lookup value = q; fork
  count = t); sink-only vs node flags; provenance-derived values (no text
  scanning).
- **No-op at true index zero** [rev4]: `math_code` instance with n1 = 0 —
  no-op upstream yields a correct workflow; recorded as `noop_correct`.
- **Backend truncation** [rev4]: token-cap hit with and without envelope
  errors; gate metric reads `generation_hit_token_cap`.
- **Cache isolation**: intervention variants distinct; **private/visible
  worker-side sharing asserted intentional** [rev4]; upstream completion
  reuse safe.
- **Split isolation**: no `latent_program_id` across namespaces; prefix
  evaluation deterministic.
- **Random valid-AST fuzzing**: grammar-valid artifacts evaluated by
  `tools.py` vs **`fuzz_oracle.py`** [rev4] — an independently implemented
  recursive AST evaluator living in the test suite (distinct code path from
  both `tools.py` and `program.py`; the per-cell reference functions do not
  evaluate arbitrary ASTs).
- **10k agreement command**: stratified by operator × cell; recorded
  acceptance command.

## 5. Decision register

| # | Decision | Status |
|---|---|---|
| D1 | Payloads in-context + host-side | retained |
| D2 | Rotation removed from count pipeline; select retains rotation | retained |
| D3 | Keyed-record values pairwise distinct | retained |
| D4 | Digits everywhere | retained |
| D5 | Enumerated prohibited coincidences only | retained |
| D6 | m = L in `math_code` | retained |
| D7 | Fixed name pools | retained |
| D8 | Join skeleton `step_1 × step_2 + q` | retained |
| D9 | Operand naming a, b, c, d / m | retained |
| D10 | Workers receive the original public problem | retained |
| D11 | Raw-completion cache; tools re-executed; worker completions shared across visibility | clarified [rev4] |
| D12 | Two-call family (18 workflows) with frozen contracted subtasks | retained |
| D13 | `GENERIC_SUBTASK` frozen, no format instruction | retained |
| D14 | No negative literals / unary minus | retained |
| D15 | Public-numeric collisions flagged, **node-level, analysis-only** (§1.16); clean stratum = private ∧ no node collision | **endorsed by reviewer; implemented node-level [rev4]** |
| D16 | System prompts (`SYSTEM_LOOKUP/MATH/CODE` + **`SYSTEM_DIRECT`**) + demos = separately reviewed 0A freeze artifact | extended [rev4] |
| D17 | No-op worker retains value 0; `noop_correct` workflows reported (not a guaranteed floor) | **new [rev4]** |

## 6. Errata against the rev6 contract — proposed for approval

1. `WorkerResult` typing superseded by the §1.7 union.
2. Lookup artifact form `lookup(resource, …)` with `R-` handles supersedes
   `lookup(Q31, …)`.
3. Canonical name: **the rev6 contract** (file self-titles "v5").
4. "Best two-call shortcut" defined (§1.11/D12).
5. "100 programs" = 100 latent clusters.
6. Deployable oracle is a semantic node-id mapping (§1.8); rev6's positional
   phrasing interpreted semantically.
7. **Truncation split** [rev4 — replaces the v0.3 `E_TRUNCATED` erratum]:
   the envelope code is `E_UNCLOSED_ARTIFACT` (syntax only); rev6's < 2 %
   truncation gate is computed from independent backend telemetry
   (`generation_hit_token_cap`), and the parse-failure gate from envelope +
   grammar errors.

## 7. Freeze record

| Phase | Scope | Status |
|---|---|---|
| 1 | Operator semantics (incl. `mul_add`); grammars + envelope precedence + limits; public/private boundaries; observation/request contracts; IR schemas + validity rules; reference functions; rejection-rule kinds (incl. modular exclusions and D15); intervention semantics + eligibility; oracle definition + tie-breaking; scheduler; renderer strings; baseline definitions; identity/PRNG/serialization freezes; telemetry contracts; decision register | **pending reviewer sign-off of this file (v0.4)** |
| 2 | All **(S)** ranges = the difficulty profile (§1.14) | after the construction screen, before fresh qualification data |

System prompts (D16, incl. `SYSTEM_DIRECT`) freeze as a reviewed 0A artifact
before the construction screen. Any post-qualification change to generator,
renderer, prompt, tool, parser, or profile retires the affected
qualification set (rev6 contract 8).
