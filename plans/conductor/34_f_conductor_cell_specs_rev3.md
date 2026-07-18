# Conductor cell specifications — v0.3 (rev3, phase-1 freeze candidate)

Revision of [`32_f_conductor_cell_specs_rev2.md`](32_f_conductor_cell_specs_rev2.md)
addressing all six phase-1 blockers, the pre-screening fixes, and the
public-number-coincidence question in
[`33_s_conductor_cell_specs_rev2_critique.md`](33_s_conductor_cell_specs_rev2_critique.md).
Supersedes v0.2 in full; self-contained (no "as v0.1" references remain).
Plan contracts: **the rev6 contract** ([`13_f_plan_rev6.md`](13_f_plan_rev6.md));
errata against it in §6 are **proposed for approval as part of this
sign-off**, not previously approved.

**No worked example changed in this revision** — all §3 fixtures, golds,
rejection/ablation checks, and intervention targets carry over from v0.2
unchanged and remain machine-verified (129 checks). Rev3 is contract closure:
IR semantics, scheduling, oracle definition, baseline executability,
intervention identity, audit scope, and serialization/parsing freezes.

**Two-phase freeze**: phase 1 on approval of this file (everything except
(S) ranges); phase 2 after the 100-example construction screen ((S) ranges =
the difficulty profile, §1.14).

## Disposition of critique items

| Item | Resolution |
|---|---|
| B1 IR operand references + normative schemas | §1.3: `operand` reference kind; `lit` reserved for public constants; normative per-op schema table + IR validity rules; `positions` wording corrected (workflow position → semantic node) |
| B2 renderer crossing vs round-robin | §1.4/§1.14: full 3-way renderer crossing per latent program, renderer removed from the latent-factor scheduler; mixed-radix full-factorial block scheduler with seeded permutation; counts-differ-by-≤1; joint contingency tests |
| B3 fork oracle under reordering | §1.8 (new): construction-frozen **semantic assignment** (lookup_branch / code_branch / join → endpoint), positional conversion via `positions`; used for all oracle-derived quantities |
| B4 baseline executability | §1.11: `GENERIC_SUBTASK` reworded (no format instruction); two-call contracted subtasks frozen verbatim, both orientations; B5 zero/one/many binding rule; plural `Resources:` serialization frozen; B4 aligned to worker blocks |
| B5 one mutation, scored twice | §1.9: replacement keyed by (latent_program_id, edge) only; kind only in result records; old-answer persistence ≤ 10 % restored; follow-through requires *all* non-intervened downstream inputs succeeded |
| B6 nuisance audit scope | §1.15: structural balance = gates; statistical leakage checks only on randomized fields, within latent subtype, defined permutation procedure; prompt length + lexical router descriptive only; no AUC gate |
| Pre-screening fixes | §1.5 (B4 blocks), §1.11 (echo/no-op/telemetry defined), §1.13 (profile hash in identity; PRNG/hash/canonical-JSON freeze; substreams; pre-declared split counts), §1.14 (75 % cap by subtype), §1.2 (ordered record entries), §1.6 (artifact-envelope contract, `E_TRUNCATED`), D16 (system prompts = reviewed 0A freeze artifact), §4 (self-contained test definitions), §6 (wording) |
| Public-number coincidences | §1.16 + D15: flag + pre-register (not rejected); non-collision stratum = the pre-registered clean Stage-3/4 headline |

---

## 1. Global conventions

### 1.1 Integers and canonical wire form

- All public outputs are integers. Canonical decimal form at text→integer
  boundaries: `0` or `-?[1-9][0-9]*` — applies to terminal answers parsed
  from text (direct baselines, the deferred `<value>` control). `0012`,
  `+5`, `5.0`, `1,000`, internal whitespace rejected.
- **Artifact grammars admit only nonnegative literals** (`0 | [1-9][0-9]*`);
  no negative-literal token, no unary minus (D14). Negative intermediates
  from subtraction are legal.
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
  exception. A Math endpoint may still *read* a keyed record in-context and
  emit literals (D1).
- `keyed` values pairwise distinct within a record (D3); `operands` names
  `a, b, c, d` in order, modulus always `m` (D9).
- **Stored as ordered entry arrays** [rev3 — JSON objects are not
  semantically ordered, and payload bytes / cache identity depend on order]:

```json
{"kind": "integer_record", "layout": "keyed",
 "payload": [["Aster", [["crates", 31]]], ["Cedar", [["crates", 17]]]]}

{"kind": "integer_record", "layout": "operands",
 "payload": [["a", 83719], ["b", 43], ["c", 1], ["d", 6]]}

{"kind": "integer_list", "payload": [41, 7, 83]}
```

- **Handles**: `R-` + digit + uppercase letter + digit; uniform, unique per
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

Argument references are typed [rev3 — new `operand` kind]:

| ref | form | meaning |
|---|---|---|
| `lit` | `{"lit": 3}` / `{"lit": "Cedar"}` | **public** constant (p, q, t, k, i, sign, key, field) |
| `res` | `{"res": "R-9V4"}` | whole resource by handle |
| `operand` | `{"operand": {"res": "R-2P6", "name": "a"}}` | one scalar inside an `operands` record — private values live **only** in the registry; the IR points at them, never duplicates them |
| `node` | `{"node": "n1"}` | another node's value; dependency edges are derived from these |

**Normative per-operation schemas** (required args exactly — extra or
missing fields make the IR invalid; allowed ref kinds per slot):

| op | args (allowed refs) | semantics |
|---|---|---|
| `lookup` | `handle` (res, keyed), `key` (lit str), `field` (lit str) | keyed retrieval |
| `affine` | `x` (node), `p` (lit), `sign` (lit `"+"`/`"-"`), `q` (lit) | `p·x ± q` |
| `ratio` | `a, b, c, d` (operand) | `(a·b − c) / d`, exact |
| `modular` | `a, b, c, m` (operand) | `(a·b + c) mod m`, m > 0 |
| `product_affine` | `x` (node), `y` (node), `q` (lit) | `x·y + q` |
| `seq_count` | `xs` (res, list), `t` (lit) | `count_gt(stable_unique(xs), t)` |
| `seq_select` | `xs` (res, list), `k` (lit), `i` (lit) | `at(rotate_left(stable_unique(xs), k), i)` |
| `seq_at` | `xs` (res, list), `i` (node) | `at(xs, i)` |

**IR validity rules** (generator-asserted and load-time validated;
violations are generator errors, never runtime behavior): unique node ids;
`node` references acyclic and only to declared nodes; **`positions` is a
topological ordering containing every node exactly once — entry *k*
(1-based) is the semantic node executed as workflow step *k* (workflow
position → semantic node)** [rev3: direction corrected]; `sink` =
`positions[-1]`; every `res`/`operand` handle exists in both manifest and
registry with a layout compatible with its slot; manifest keys = registry
keys exactly.

Instance schema (identity fields per §1.13):

```json
{
  "cell_id": "lookup_math",
  "latent_program_id": "lookup_math:qualification:00042:9f3ac1d2",
  "render_instance_id": "lookup_math:qualification:00042:9f3ac1d2:goal_first:private",
  "renderer_id": "goal_first",
  "split_id": "qualification",
  "visibility_condition": "private",
  "difficulty_profile_version": "dp-<sha256-prefix>",
  "generator_version": "specs-v0.3+<code-version>",
  "seed": 18421,
  "public_numeric_collision": false,
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

An `operands`-record example (math_atomic T1): `n1 = ratio` with
`args = {"a": {"operand": {"res": "R-2P6", "name": "a"}}, …}` — no private
value appears in the IR.

Cluster identity = `latent_program_id`: all renderings and both visibility
variants of one latent program share it and its split; "100 programs" means
100 latent clusters. Reference subtasks and interventions are derived
deterministically (§3, §1.9/§1.13), not stored. Strip-test consequence (rev6
contract 5): the execution path never reads `reference_program` or
`gold_answer`; only the scorer reads `gold_answer`.

### 1.4 Renderers [rev3 — full crossing, renderer out of the scheduler]

`resource_first` (canonical), `goal_first`, `bound_var`. **Every latent
program is generated once and rendered in all three cosmetic forms**; the
three renderings form one cluster; renderer is **not** a latent-factor
scheduler dimension (§1.14). Paired visible renderings are generated only for
the designated visible-slice clusters (§1.12).

Frozen rules: renderer template inputs are only handles and public
parameters (structural no-leakage); numerals as digits (D4); prompt
typography `× − ÷ mod`, artifact ASCII `* - / %`; indexing always
"zero-based"; shared connective vocabulary (N5). All renderer strings
enumerated in §3.

### 1.5 Observation and request contracts

**Stage-0C/2 policy observation** (private condition; frozen skeleton; exact
system-prompt string is a 0A freeze artifact, D16):

```text
Problem:
{public_prompt}

Resources available: {manifest handles, comma-separated, manifest order}

Steps:
1. (resource: {handle|none}; previous results: {none|all}) {reference subtask 1}
2. ...

Choose one worker for each step.
```

Steps are numbered in `positions` order, so the workflow-position →
semantic-node mapping is observable; for fork/join the public prompt's clause
order tracks the same order (§3.6). The policy emits `{"worker_ids": [...]}`
only; extra fields rejected (rev6 contract 1).

**Worker request template** — canonical and byte-stable. User-message blocks
in this fixed order, each present or omitted as a whole; exactly one blank
line between blocks; LF newlines; no trailing whitespace; canonical
integers:

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

- `Problem` always present (D10 — keeps the generic-subtask arm §1.11
  informative; payload privacy, not prompt privacy, carries causal
  necessity: a downstream worker cannot recompute a corrupted predecessor
  because it lacks the upstream payload).
- `Task` = the step's subtask (reference, learned, or `GENERIC_SUBTASK`).
- `Resource` omitted when no resource is authorized. **Multi-payload
  requests (harness-only, B5/B3) use the plural block** [rev3 — frozen]:

```text
Resources:
{payload text 1}

{payload text 2}
```

  (manifest order, one blank line between payloads, replacing the singular
  block.)
- `Previous results` present iff access = `all`: one `step_k = {value}` line
  per predecessor in step order; these lines and the host-side binding are
  the only predecessor channels.
- Direct (non-endpoint) baselines — **including B4** [rev3] — use the same
  blocks and replace only the final instruction line with the answer-line
  protocol (§1.11).
- Endpoint system prompts `SYSTEM_LOOKUP` / `SYSTEM_MATH` / `SYSTEM_CODE`
  (role + grammar description + fixed demos) are **a separately reviewed 0A
  freeze artifact** (D16): checked in, reviewed, and frozen before the
  construction screen; fingerprinted into the runtime profile; later change
  retires qualification sets (rev6 contract 8).
- **Canonical rendered request** = chat template applied to (system, user)
  byte strings — the cache-key component (§1.10) and byte-stability test
  target (§4).

### 1.6 Artifact envelope, grammars, limits, typed rejections

**Envelope contract** [rev3 — frozen]:

- Envelope tokens are the exact byte strings `<artifact>` and `</artifact>`
  (lower-case, no attributes); any variant (`<Artifact>`, `<artifact x=1>`)
  is ordinary text, not a tag.
- Let n₀ = occurrences of `<artifact>`, n₁ = occurrences of `</artifact>` in
  the completion (plain substring count — tag-like text in reasoning
  **counts**; disciplined output is part of the protocol, per rev6
  "duplicate/mixed/unexpected terminal tags invalid").
- n₀ = 0 → `E_NO_ARTIFACT`; n₀ ≥ 2 or n₁ ≥ 2 → `E_MULTI_ARTIFACT`;
  n₀ = 1 ∧ n₁ = 0 → `E_TRUNCATED` [rev3: new code — separates
  truncation-before-close in the parse-failure telemetry];
  n₀ = 1 ∧ n₁ = 1 with the close before the open → `E_PARSE`.
- Any `<value>` substring anywhere → `E_UNEXPECTED_TAG` (reserved for the
  deferred answer-only control).
- Text before and after the envelope is permitted and ignored (reasoning);
  the content between the tags is trimmed, then parsed by the endpoint
  grammar.

Endpoints (unchanged): Lookup = Qwen2.5-1.5B-Instruct + keyed retrieval;
Math = Qwen2.5-Math-1.5B-Instruct + exact calculator; Code =
Qwen2.5-Coder-1.5B-Instruct + whitelist sequence interpreter. D1: authorized
payloads delivered in-context *and* bound host-side.

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
(D14; `a--5`, `--` → `E_PARSE`); precedence `* / %` over `+ -`, left-
associative, parentheses; whitespace between tokens allowed; `/` exact in ℤ
else `E_INEXACT_DIV`, divisor 0 → `E_DIV_ZERO`; `%` floor-mod, modulus 0 →
`E_DIV_ZERO`, negative → `E_BAD_ARG`; `resource` binds the step's authorized
payload of the grammar-compatible kind/layout — none authorized →
`E_NO_RESOURCE`, wrong kind/layout → `E_RESOURCE_KIND`; Math single-letter
identifiers bind only against an `operands` record, unknown/unbound →
`E_UNKNOWN_IDENT`; `step_k` resolves iff access = `all` and `k <` step index,
else `E_UNKNOWN_IDENT`; `rotate_left(xs, k)` requires `k ≥ 0` (`E_BAD_ARG`),
rotates by `k mod len`; `at` zero-based, out of range → `E_INDEX_RANGE`;
`count_gt` strict `>`.

**Uniform limits, all grammars**:

| Limit | Value | Rejection |
|---|---|---|
| artifact size (after trim) | ≤ 512 bytes | `E_PARSE` |
| AST nodes / depth | ≤ 64 / ≤ 8 | `E_DEPTH` |
| integer-literal digits | ≤ 12 | `E_PARSE` |
| any intermediate or result magnitude | ≤ 10¹² | `E_MAGNITUDE` |

**Typed rejection codes** (complete; contract-4 path; unexpected exceptions
propagate and abort): `E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`, `E_TRUNCATED`,
`E_UNEXPECTED_TAG`, `E_PARSE`, `E_NONCANONICAL_INT`, `E_UNKNOWN_IDENT`,
`E_NO_RESOURCE`, `E_RESOURCE_KIND`, `E_UNKNOWN_KEY`, `E_UNKNOWN_FIELD`,
`E_INDEX_RANGE`, `E_INEXACT_DIV`, `E_DIV_ZERO`, `E_BAD_ARG`, `E_DEPTH`,
`E_MAGNITUDE`.

**Primitive semantics** (implemented independently in `tools.py` and
`program.py`; 10k agreement command stratified by operator × cell):
`stable_unique` (first occurrences, order preserved), `rotate_left`, `at`,
`count_gt`, `lookup`, numeric ops of §2.1.

### 1.7 WorkerResult and failure propagation

```text
status         ∈ {success, typed_failure, dependency_blocked}
value          : int | null      (int iff status = success)
rejection_code : code | null     (set iff status = typed_failure)
artifact_valid : bool
tool_executed  : bool
```

1. A step whose status ≠ `success` blocks every later step with access =
   `all` (binary access ⇒ dependence on all predecessors); blocked steps are
   `dependency_blocked`, **no worker call is made**.
2. Steps with access = `none` are unaffected — independent branches
   continue.
3. A join is blocked if either branch fails.
4. Terminal result = sink step's value; sink not `success` → terminal null →
   0.5 (schema-valid action failing in the world).
5. Only infrastructure failures abort (rev6 contract 4).

### 1.8 Deployable oracle: semantic assignment [rev3 — new]

The deployable oracle is a **semantic-node → endpoint mapping**, per cell:

```text
lookup_atomic:  {node}          → endpoint
lookup_math:    {lookup, affine} → endpoints
math_code:      {modular, select} → endpoints
fork_join:      {lookup_branch, code_branch, join} → endpoints
```

The harness converts it to positional `worker_ids` through `positions`
(fork lookup-first `[Lookup*, Code*, Math*]` and code-first
`[Code*, Lookup*, Math*]` are the *same* oracle). Rules:

- Selected on construction data, frozen, evaluated on fresh qualification
  data; never reselected (rev6 contract 7).
- The mapping may condition on observable branch identity/order, **not** on
  renderer id, private values, qualification outcomes, or realized worker
  success.
- **All oracle-derived quantities are defined over semantic nodes** and
  converted positionally: Stage-2 targets, runner-up substitutions, the
  effective-routing-stakes gate, routing regret, best-fixed and random
  controls, and the cold-start best-assignment-in-group arithmetic
  (96 / 61 / 26 %, unchanged by reordering).
- Hindsight per-example maximum remains diagnostic only.

### 1.9 Interventions: mediator (wire) semantics

Both kinds per dependency edge *(u → v)*, on the deployable-oracle
assignment at calibration time; mediator/wire interventions (resource-level
counterfactuals deferred).

**One mutation, scored twice** [rev3]: a single replacement *r* per
`(latent_program_id, edge)` — the PRNG seed omits the scoring kind
(§1.13) — and **one mutated execution** is scored against both targets:

1. Replace step *u*'s recorded value with *r* via a calibration-only
   executor override, in **both** channels (the `step_u = r` context line
   and the host-side binding).
2. Rerun the downstream worker(s); distinct cache identity is automatic
   (request bytes differ; upstream completions reusable).
3. Score the mutated terminal against the stored `gold_answer` →
   **corruption** accuracy and **old-answer persistence** (fraction of
   mutated runs still producing the original gold; CE1 gate: ≤ 10 %,
   restored from rev6 [rev3]).
4. Score the same terminal against `gold'` (reference sink recomputed
   **outside the executor** with the override) → **counterfactual
   consistency**.
5. `kind` appears only in result records, never in replacement generation.

**Conditional follow-through** [rev3]: computed over mutated runs in which
**every non-intervened input of the affected downstream node succeeded**
(in fork/join: the other branch too, not merely the intervened one).

Replacement rules per cell (§3) provably change the sink. Atomic cells have
no edges (ablation rejections + metamorphic tests cover them). Missing/skip
variants prove only tool input-validation (rev6 contract 7).

### 1.10 Caching rule

Cache stores **raw model completions**, keyed by `runtime-profile
fingerprint + endpoint fingerprint + canonical rendered request bytes`.
Tools re-executed on every call against current bindings; an executed
`WorkerResult` is never cached. Intervention variants and visibility
conditions get distinct keys by construction; tool versions live in the
profile fingerprint (rev6 contract 8).

### 1.11 Baselines and diagnostic workers — executable definitions

Direct (non-endpoint) arms use the answer-line protocol: final instruction
line `Answer with a single integer on the final line.`; the last non-empty
line, trimmed, must parse as a canonical integer, else scored wrong.

| # | Arm | Model | Input |
|---|---|---|---|
| B1 | Public-only direct | 3B base | `Problem` block only. Reported against majority-class and public-feature guessing references; small-support outputs make nonzero accuracy expected; **leakage is decided by provenance (§4), never by accuracy ≈ 0** |
| B2 | Endpoint-without-resource | each endpoint | worker request minus `Resource` — typed-rejection diagnostic |
| B3 | Visible direct | 3B base | `Problem` + plural `Resources:` block (§1.5). Diagnoses self-solving; without `SELF` it does not test delegation |
| B4 | Local-node | 3B base | **same blocks as an endpoint worker** [rev3]: `Problem` + `Task` (node reference subtask) + `Resource` (node payload) + `Previous results` (gold predecessor values); only the final line differs |
| B5 | One-call whole-task | each endpoint | `Problem` + `Task: Complete the task and return the final result.` + plural `Resources:` (union payload — harness-only exception). **Binding rule** [rev3]: exactly one grammar-compatible payload → bind it; zero → bind none (`E_NO_RESOURCE`/`E_UNKNOWN_IDENT` on tool use; in-context reading and literal Math expressions remain possible); more than one compatible → **harness configuration error in v0** (never occurs in v0 cells) |
| B6 | Generic-subtask arm | endpoints per deployable oracle | reference workflow with every subtask replaced by `GENERIC_SUBTASK` |

- **`GENERIC_SUBTASK` (frozen)** [rev3 — reworded; artifact formatting
  belongs to the fixed final instruction and system prompt, so the generic
  arm cannot fail on a formatting conflict]:
  `Complete the assigned step using the problem context, any provided
  resource, and any previous results.`
- **Best one-call** = endpoint selected on construction data, frozen for
  qualification; per-example hindsight maximum diagnostic only.
- **Fork two-call shortcut family**: all two-step `[none, all]` chains,
  step 1 assigned one manifest resource and step 2 the other, both
  orientations, endpoints over 3 × 3 — 18 workflows, enumerated on the
  construction screen; best frozen from construction data. **Contracted
  subtasks (frozen verbatim)** [rev3]:
  - *Lookup-first*: step 1 = `Retrieve {key}'s {field} value from the
    requested resource.` step 2 = `Remove later occurrences of repeated
    values from the integer sequence in the requested resource, count the
    values greater than {t}, multiply that count by step_1, and add {q}.`
  - *Code-first*: step 1 = `Remove later occurrences of repeated values
    from the integer sequence in the requested resource and count the
    values greater than {t}.` step 2 = `Retrieve {key}'s {field} value from
    the requested resource, multiply it by step_1, and add {q}.`
- **Diagnostic pseudo-workers** [rev3 — now defined]:
  - *Echo worker*: no model, no tool; value = the last canonical-integer
    token in its `Task` block, else `typed_failure(E_PARSE)`. Lower-bounds
    the exploitability of the subtask channel (answer smuggling); primary
    use on the visible slice and Stages 3–4.
  - *No-op worker*: no model, no tool; value = 0 always (never correct —
    golds ≥ 1). Floor reference and scoring-defect canary.
  - *Answer-in-subtask telemetry* (always on, Stages 3–4): flag any
    policy-authored subtask containing the instance's gold answer as a
    canonical integer token; rate logged per cell/stage; feeds the D15
    collision analysis (§1.16).
- **Reporting**: every condition reports prompt tokens and tool-call
  counts. If hierarchy wins primarily by partitioning a long union context
  into short local contexts, that is a valid systems result and will be
  identified as such.

### 1.12 Visibility conditions

`visibility_condition` ∈ {`private`, `visible`}. Visible rendering appends
the plural `Resources:` block (§1.5) after the Conductor-side `Problem`
block. Worker-side requests are identical in both conditions. Visible
variants are generated **only for the designated visible-slice clusters**
(~100 latent programs, pre-registered), paired by `latent_program_id` and
split. Visibility enters `render_instance_id`, the observation bytes (hence
cache identity), and the runtime profile's visibility policy fingerprint.

### 1.13 Identity, randomness, splits [rev3 — executable freezes]

- **Hash-to-integer**: `h64(s) =` first 8 bytes of `SHA-256(s)`,
  **big-endian unsigned**. Field separator ␟ = byte 0x1F.
- **PRNG (frozen)**: NumPy `Generator(PCG64(seed))`, NumPy version pinned by
  the repo lockfile; `seed = h64(...)`.
- **Generation identity includes the difficulty profile** [rev3]:
  `seed_material = "qwen-grpo-conductor" ␟ generator_version ␟
  difficulty_profile_version ␟ namespace ␟ cell_id ␟ latent_index` —
  changing an (S) band changes every derived id, so no two profiles share a
  `latent_program_id`.
- **Labelled substreams** [rev3]: child seed = `h64(seed_material ␟ label)`
  with labels `"values"` (payload sampling), `"names"` (entities/fields),
  `"handles"`, `"manifest"` (order), `"factor_perm"` (§1.14 block
  permutation), `"intervention"` — sampling one stream never perturbs
  another.
- `latent_program_id = "{cell_id}:{namespace}:{latent_index:05d}:{hex8}"`
  (hex8 = first 4 bytes of `SHA-256(seed_material)`, hex).
- `render_instance_id = latent_program_id + ":" + renderer_id + ":" +
  visibility_condition`.
- **Intervention replacements**: PRNG seeded by
  `h64("intervention" ␟ latent_program_id ␟ edge_label)` with textual
  `edge_label` (`"n1->n3"`); **no scoring kind in the seed** (§1.9).
- **Canonical JSON** (for `difficulty_profile_version` and any hashed
  config): UTF-8, sorted keys, separators `(",", ":")`, integers only, no
  floats.
- **Namespaces** `construction, qualification, train, dev, test` are
  disjoint generation universes (no partition of a shared pool); **counts
  per namespace are pre-declared in the CE-logged run configuration before
  any generation in that namespace** [rev3]; no latent program ever crosses
  namespaces (unit-tested).

### 1.14 Distributions and sampling protocol

- **Numeric parameters**: independent integer-uniform on their (S) bands
  unless stated; T1 exact division constructive (`c` uniform on
  `{c ∈ [1,20] : c ≡ a·b (mod d)}`, nonempty since d ≤ 12); records —
  entities/fields uniform without replacement from pools, values uniform
  without replacement from band; dedup-flavor lists i.i.d. uniform [1, 9]
  then rules; select-flavor uniform without replacement [1, 99].
- **Categorical latent factors** [rev3 — replaces naive round-robin, which
  aliases equal-cardinality factors]: per cell, the factors are — target
  stratum (3: first/middle/last third) for record cells; formula template
  (3) for `math_atomic`; shape (2) for `code_atomic`; sign (2) for
  `lookup_math`; branch order (2) for `fork_join`. **Renderer is not a
  factor** (§1.4: every program gets all three renderings). Assignment uses
  a **mixed-radix full-factorial block scheduler**: consecutive blocks of
  size ∏(levels) contain each joint combination exactly once, in an order
  given by a seeded permutation per block (substream `"factor_perm"`);
  where the sample size is not a multiple of the block size, joint counts
  differ by **at most one**. Acceptance checks test **joint contingency
  tables**, not only marginals.
- **Telemetry at the construction screen**: rejection counts by rule;
  post-rejection marginals per parameter; **maximum acceptable rejection
  rate 75 %, applied per latent subtype** [rev3] (a pathological
  Code-select or modular subtype must not hide behind easier instances) —
  exceeding it fails the difficulty profile (fix the profile; never
  hand-prune).
- **Pre-registration rule**: no individual instance is ever retained or
  discarded based on worker performance; only an entire difficulty profile
  or cell passes or fails construction screening.
- **Difficulty profile** = canonical JSON of every (S) band and
  distribution; `difficulty_profile_version` = its SHA-256 prefix; stored
  per instance; part of generation identity (§1.13); frozen at phase 2.
- **Qualification reporting stratified by latent subtype**: T1/T2/T3,
  count/select, plus/minus, renderer, fork order.
- Per-instance resampling cap 1000 attempts (generator error, never a
  silent band change); rules re-asserted at load time.

### 1.15 Balance enforcement and shortcut audit [rev3 — audit scope fixed]

1. **Structural gates** (generator-enforced, unit-tested): exact factor
   balance per §1.14 (joint tables, ±1); handle characters uniform;
   manifest order shuffled; all three renderings present per latent
   program; splits balanced across factors.
2. **Statistical leakage checks — randomized fields only, within latent
   subtype** [rev3]: for each of {handle strings, entity names, field
   names, renderer id, split id} × each latent subtype: cluster-aware
   permutation test (clusters = latent programs; 10,000 permutations) of
   association with the gold answer binned into within-subtype quartiles;
   α = 0.01, Holm-corrected across field × subtype tests. These fields are
   independent of values by construction, so any failure is investigated
   as a **generator defect**, not treated as a scientific gate.
3. **Descriptive diagnostics, not gates**: prompt-length distributions per
   cell/subtype (length legitimately tracks semantic workload — within
   `math_atomic`, T1/T2/T3 differ in formula length and answer scale, and
   public `p, q, t, i` legitimately correlate with answers); shallow
   bag-of-words router accuracy on cell identity and routing (expected
   high; acceptable for the rev6 claim of fixed endpoint selection).
4. The stronger anti-template gate is reserved for the deferred
   semantic/counterfactual renderer. No second resource is added to
   Lookup→Math.

Legitimate semantic cues ("retrieve a field", "multiply", "zero-based
index", "remove duplicates") remain by design.

### 1.16 Public-numeric collisions [rev3 — new; D15]

`public_numeric_collision` (stored per instance): true iff `gold_answer`
equals any integer rendered in `public_prompt` (the applicable public
parameters `p, q, t, k, i` — private operands never render). Collisions are
**flagged, not rejected**: answer-smuggling via public numbers is one of the
project's named failure modes, and observing it is an experimental result.
Pre-registered analyses (carried into CE1):

- collision frequency by cell and latent subtype;
- accuracy conditioned on collision vs non-collision;
- answer-in-subtask telemetry crossed with collision status;
- **the non-collision stratum is the pre-registered clean headline for
  Stage-3/4 instruction-learning claims.**

(The reviewer left flag-vs-reject open; flagging is chosen because the
project treats named failure modes as pre-registered experimental results,
and the clean headline is preserved by stratification. Reversing this
choice — rejection — must happen at phase-1 sign-off since rejection-rule
kinds freeze then.)

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
def prim_ratio(a, b, c, d) -> int                 # (a*b - c) / d, exact else raise
def prim_modular(a, b, c, m) -> int               # (a*b + c) % m, m > 0
def prim_product_affine(x, y, q) -> int           # x*y + q
def prim_seq_count(xs, t) -> int                  # count_gt(stable_unique(xs), t)
def prim_seq_select(xs, k, i) -> int              # at(rotate_left(stable_unique(xs), k), i)
def prim_seq_at(xs, i) -> int                     # at(xs, i)
```

A cell's direct reference function composes these over the registry and
public parameters; source of `gold_answer` and counterfactual recomputation;
one side of the 10k agreement command.

### 2.2 Shared samplers

`integer_record(N, F, band, layout)` (ordered entries, §1.2);
`integer_list_dedup(L, band=[1,9])` with `3 ≤ U ≤ L − 2`;
`integer_list_select(L, band=[1,99])` pairwise distinct.

---

## 3. Cell specifications

Unchanged from v0.2 except: IR examples use `operand` references (§1.3);
`positions` wording corrected; the fork oracle note points to §1.8; the
two-call subtask strings live in §1.11. **All fixtures, golds, rejection and
ablation checks, and intervention targets are identical to v0.2** and remain
machine-verified. Conventions: **O** ordinary, **B** boundary; example
artifacts illustrate the grammar (any grammar-valid artifact whose executed
value is correct scores); no gold worker presumed; reference subtasks
tool-neutral; renderer strings enumerated in full.

### 3.1 `lookup_atomic` — atomic Lookup

**Shape**: 1 step, access `[none]`, 1 keyed `integer_record`.

| Parameter | Range |
|---|---|
| entities N | 3–16 **(S)**, `N × F ≤ 60` |
| fields F | 1–5 **(S)** |
| value band | 10–99 **(S)**, pairwise distinct |
| target (key, field) | uniform; position stratified (§1.14) |

**Rejection rules**: none beyond the record invariants.

**Renderer strings**:

- `resource_first`: `Resource {H} contains keyed integer records. Return the
  {field} value recorded for {key}.`
- `goal_first`: `Return the {field} value that {H} records for {key}.`
- `bound_var`: `Let v be {key}'s {field} in {H}. Output v.`

**Reference program**: `n1 = lookup(handle={res H}, key={lit}, field={lit})`;
positions `[n1]`; sink `n1`.

**Reference subtask**: `Retrieve {key}'s {field} value from the requested
resource.`

**Example artifact**: `<artifact>lookup(resource, "Grove", "crates")</artifact>`

**O** — `R-7K2`: Aster.crates = 31, Cedar.crates = 17, Grove.crates = 39,
Ivory.crates = 53; target Grove.crates. Gold: **39**.

**B** — small-N (N = 4; band minimum 3), band-edge values. `R-4H8`:
Lark.units = 99, Onyx.units = 10, Pine.units = 11, Quill.units = 98; target
Quill.units. Gold: **98**.

**Interventions**: none (atomic). Distractor invariance per §4.

**One-call baseline**: B5, the record as sole payload.

### 3.2 `math_atomic` — atomic Math (hidden operands, public formula)

**Shape**: 1 step, access `[none]`, 1 `operands`-layout record.

| Template | Public formula | Operands |
|---|---|---|
| T1 ratio | `(a × b − c) ÷ d` | a, b, c, d |
| T2 modular | `(a × b + c) mod m` | a, b, c, m |
| T3 affine | `a × b + c` | a, b, c |

| Parameter | Range |
|---|---|
| a | 10⁴–10⁶ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** (T1: constructive, §1.14) |
| d (T1) | 2–12 **(S)** |
| m (T2) | 5–60 **(S)** |

**Rejection rules**: answer ∈ [1, 10⁹]; T2 answer ∈ [1, m−1]; answer ∉
operand values; **modular operand-relevance checks** (every modular node,
here and `math_code` n1; `g` = residue): drop-c `(a·b) mod m ≠ g`; a→1
`(b + c) mod m ≠ g`; b→1 `(a + c) mod m ≠ g`. (T1/T3 relevance is
band-guaranteed: b ≥ 10, c ≥ 1, d ≥ 2.)

**Renderer strings** (`{names}` = `a, b, c and d` / `a, b, c and m` /
`a, b and c`):

- `resource_first`: `{H} contains integers {names}. Evaluate` `` `{formula}` ``
  `exactly.`
- `goal_first`: `Return the exact value of` `` `{formula}` `` `, where
  {names} are the integers recorded in {H}.`
- `bound_var`: `Let {names} be the integers in {H}. Output` `` `{formula}` ``
  `.`

**Reference program**: `n1 = ratio|modular|affine` with **`operand`
references into the record** (§1.3) and no private value in the IR;
positions `[n1]`; sink `n1`.

**Reference subtask**: `Evaluate` `` `{formula}` `` `exactly using the
integers in the requested resource.`

**Example artifact**: `<artifact>(a * b - c) / d</artifact>`

**O (T1)** — `R-2P6`: a = 83719, b = 43, c = 1, d = 6.
`83719 × 43 = 3599917; − 1 = 3599916; ÷ 6 =` **599986**.

**O (T2)** — `R-7Q4`: a = 999983, b = 89, c = 19, m = 12. Residues 11, 5, 7:
`(11·5 + 7) mod 12 =` **2**. (drop-c 7 ≠ 2 ✓; a→1 0 ≠ 2 ✓; b→1 6 ≠ 2 ✓;
c mod m = 7 ≠ 0 ✓.)

**O (T3)** — `R-1X5`: a = 524287, b = 83, c = 17. **43515838**.

**B (T1, low edges)** — `R-8B2`: a = 10007, b = 10, c = 2, d = 6.
`(100070 − 2) ÷ 6 =` **16678**.

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
| U = len(stable_unique) | 3 ≤ U ≤ L − 2 |
| k (select) | 1–9 **(S)**, `k mod U ≠ 0` |
| t (count) | 1–8 **(S)** |
| i (select) | 0…U−1 |

**Rejection rules**: `3 ≤ U ≤ L − 2` (both shapes); count —
`1 ≤ answer ≤ U − 1`, dedup ablation `count_gt(xs, t) ≠
count_gt(stable_unique(xs), t)`; select — `k mod U ≠ 0`, dedup ablation
`at(rotate_left(xs, k), i) ≠ gold`, rotation ablation
`at(stable_unique(xs), i) ≠ gold`.

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

**Reference subtasks**: count — `Remove later occurrences of repeated values
from the integer sequence in the requested resource and count the values
greater than {t}.`; select — `Remove later occurrences of repeated values
from the integer sequence in the requested resource, rotate the remaining
sequence left by {k} positions, and return the value at zero-based index
{i}.`

**Example artifacts**:
`<artifact>count_gt(stable_unique(resource), 5)</artifact>`;
`<artifact>at(rotate_left(stable_unique(resource), 2), 4)</artifact>`

**O (count)** — `R-8C3`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]`, t = 5.
`stable_unique → [6, 1, 9, 4, 8, 3, 2, 7]` (U = 8); `count_gt(5) =` **4**.
(Dedup ablation: raw count 6 ≠ 4 ✓.)

**O (select)** — `R-5N1`: `[5, 3, 5, 8, 1, 3, 9, 2]`, k = 2, i = 4.
`stable_unique → [5, 3, 8, 1, 9, 2]` (U = 6); `rotate_left(2) → [8, 1, 9, 2,
5, 3]`; `at(4) =` **5**. (Dedup ablation 9 ≠ 5 ✓; rotation ablation 9 ≠ 5 ✓.)

**B (count, answer = U − 1)** — `R-9E3`: `[9, 8, 9, 7, 6, 8, 5, 9]`, t = 5.
`stable_unique → [9, 8, 7, 6, 5]` (U = 5); `count_gt(5) =` **4**. (Dedup
ablation 7 ≠ 4 ✓.)

**Interventions**: none (atomic). **One-call baseline**: B5, the list.

### 3.4 `lookup_math` — Lookup → Math

**Shape**: 2 steps, access `[none, all]`; keyed record requested by step 1;
step 2 requests none, consumes `step_1`.

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

**Reference program**: `n1 = lookup(...)`;
`n2 = affine(x={node n1}, p={lit}, sign={lit}, q={lit})`; positions
`[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Retrieve {key}'s {field} value from the
requested resource.` 2. `Multiply step_1 by {p}, then subtract {q}.` (plus
form: `…, then add {q}.`)

**Example artifacts**:
`<artifact>lookup(resource, "Cedar", "units")</artifact>`;
`<artifact>3 * step_1 - 4</artifact>`

**O** — `R-3T5`: Aster.units = 31, Cedar.units = 17, Grove.units = 39,
Ivory.units = 53; target Cedar.units; p = 3, minus, q = 4. `n1 = 17`;
`n2 = 3 × 17 − 4 =` **47**.

**B (band edges)** — `R-2W9`: Vale.units = 99, Aster.units = 10,
Hazel.units = 23, Tarn.units = 57; target Vale.units; p = 9, minus, q = 20.
**871**.

**Interventions** (edge `n1->n2`; §1.9 single-mutation semantics):
replacement `n1' ~ U([10, 99] \ {n1})`, resampled until `affine(n1') ≥ 1`;
sink change automatic (affine injective, p ≥ 2). Example (O): `n1' = 19` —
one mutated execution; corruption target stays 47 (run yields 53, wrong);
counterfactual target 53.

**One-call baseline**: B5, the record. Screen tunes N/F/distractors until
the deployable oracle clears the +20-point gate (D1 makes inlining
possible).

### 3.5 `math_code` — Math → Code (computed index)

**Shape**: 2 steps, access `[none, all]`; step 1 requests the operand
record; step 2 requests the list, consumes `step_1`.

| Parameter | Range |
|---|---|
| a | 10⁸–10⁹ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** |
| m = L | 8–16 **(S)** (D6) |
| list | select-flavor, values 1–99 **(S)**, pairwise distinct |

**Rejection rules**: list pairwise distinct (every counterfactual index
changes the answer — structural discharge of the rev6 rejection); answer ≠
n1; answer ∉ {a, b, c, m}; modular operand-relevance checks (§3.2) on n1;
intermediate n1 = 0 permitted (terminal ≥ 1 via list band).

**Renderer strings**:

- `resource_first`: `{H1} contains integers a, b, c and m. Compute`
  `` `(a × b + c) mod m` `` `. Use the result as a zero-based index into the
  sequence in {H2} and return the selected integer.`
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
83, 22, 65, 14, 39, 90, 56, 11, 72, 28]`. Residues 9, 7, 5:
`n1 = (9·7 + 5) mod 12 = 8`; `n2 = list[8] =` **56**. (drop-c 3 ≠ 8 ✓; a→1
0 ≠ 8 ✓; b→1 2 ≠ 8 ✓.)

**B (index = m − 1)** — `R-3F7`: a = 123456789, b = 45, c = 6, m = 8;
`R-6M2`: `[17, 64, 80, 23, 46, 91, 12, 58]`. Residues 5, 5, 6:
`n1 = (5·5 + 6) mod 8 = 7`; `n2 = list[7] =` **58**. (drop-c 1 ≠ 7 ✓; a→1
3 ≠ 7 ✓; b→1 3 ≠ 7 ✓.)

**Interventions** (edge `n1->n2`): replacement `i' ~ U([0, m−1] \ {n1})`;
one mutated execution scored twice (§1.9). Example (O): `i' = 3` —
corruption target 56 (run yields 22, wrong); counterfactual target 22.

**One-call baseline**: B5, record + list. Composition advantage driven by
a's size (one-call Code must compute the index without a calculator;
one-call Math has no selection operator).

### 3.6 `fork_join` — Lookup + Code → Math (diagnostic)

**Shape**: 3 steps, access `[none, none, all]`; branch steps request one
resource each; join requests none, consumes `step_1`, `step_2`.
**Diagnostic-only in v0** (admission gates deferred); qualification slice
100–200 latent clusters if paired CIs are decisive. If admitted to Stage-2
routing after its gates, fork/join tests endpoint selection *within a fixed
parallel DAG*; topology construction remains a Stage-4 claim.

**Branch order**: scheduled 50/50 (§1.14). `positions` records it; the
Stage-2 observation numbers subtasks in that order; the public prompt's
clause order tracks it. The join formula is symmetric. **The deployable
oracle is order-invariant by construction: it maps semantic branches, not
positions (§1.8).**

| Parameter | Range |
|---|---|
| record N, F, band | as §3.1; branch value n_lk ∈ [10, 99] |
| code branch | count shape of §3.3 (U ≥ 3, ablation rules) |
| q | 1–20 **(S)** |

Join skeleton (D8): `step_1 × step_2 + q`.

**Rejection rules**: both branch rule-sets; answer ∉ {n_lk, n_code} ∪
record values ∪ list values; strict monotonicity (n_code ≥ 1, n_lk ≥ 10)
makes either branch corruption move the sink; U ≥ 3 keeps the code-branch
counterfactual pool nonempty.

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

**Reference program** (lookup-first): `n1 = lookup(H1, key, field)`;
`n2 = seq_count(xs={res H2}, t={lit})`; `n3 = product_affine(x={node n1},
y={node n2}, q={lit})`; positions `[n1, n2, n3]` (code-first:
`[n2, n1, n3]`); sink `n3`.

**Reference subtasks**: branch subtasks of §3.1/§3.3; join — `Multiply
step_1 by step_2, then add {q}.`

**Example artifacts**: branches as §3.1/§3.3; join
`<artifact>step_1 * step_2 + 3</artifact>`.

**O (lookup-first)** — `R-5A8`: Aster.units = 31, Cedar.units = 14,
Grove.units = 39 (target Cedar); `R-1J7`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2,
7, 4]`, t = 5; q = 3. `n1 = 14`; `n2 = 4`; `n3 =` **59**. Branch
counterfactuals: 14 → 15 ⇒ 63; 4 → 3 ⇒ 45.

**O′ (code-first)** — same latent payloads/parameters, order swapped;
positions `[n2, n1, n3]`: step 1 = count (`R-1J7`) → 4; step 2 = lookup
(`R-5A8`) → 14; step 3 `= 4 × 14 + 3 =` **59**. Code-first renderer strings;
Stage-2 observation lists the count subtask first; **the semantic oracle
mapping is identical to O** (§1.8).

**B (minimum code count)** — `R-8D4`: Wren.crates = 99, Slate.crates = 10,
Fern.crates = 57 (target Wren); `R-2K9`: `[4, 2, 4, 3, 1, 2, 3, 4]`, t = 3;
q = 20. `stable_unique → [4, 2, 3, 1]` (U = 4); `n2 = 1`; `n1 = 99`;
`n3 =` **119**. Branch counterfactuals: 99 → 98 ⇒ 118; 1 → 2 ⇒ 218.

**Interventions** (edges `n1->n3`, `n2->n3`; one replacement per edge,
scored twice, §1.9; follow-through conditions on the *other* branch's
success): `n1' ~ U([10, 99] \ {n1})`; `n2' ~ U([1, U−1] \ {n2})`;
counterfactual targets via `product_affine`. Fork gate: per-branch
corruption drop ≥ 20 pts, paired clustered lower CI; old-answer persistence
≤ 10 %.

**One-call baseline**: B5, record + list. **Two-call baseline**: the
18-workflow family with the frozen contracted subtasks (§1.11), best frozen
on construction data (rev6 CE1: oracle ≥ +15).

---

## 4. Acceptance hooks (0A battery; self-contained definitions [rev3])

- **Golden fixtures**: every §3 worked example (incl. fork O′) — asserting
  intermediates, gold, rejection/ablation compliance, intervention targets.
- **Byte-stability fixtures**: golden canonical rendered requests (§1.5),
  one per cell × step × access pattern, incl. a plural-`Resources:` case;
  byte-for-byte.
- **Metamorphic tests** (defined here): `stable_unique` idempotence
  (`su(su(xs)) = su(xs)` and pipeline value unchanged); count invariance
  under any permutation of the deduplicated list; renderer invariance (all
  three renderings of one latent program share gold, interventions,
  reference program); handle-renaming invariance (re-drawing handles changes
  no semantic value); **distractor invariance**: resampling non-target
  entities/fields/values (lookup cells) or non-selected list positions'
  order (where semantics permit) leaves the gold unchanged.
- **Provenance-based no-leakage** (defined here): every private value is
  provenance-tagged at generation; assert (a) structurally, renderer inputs
  contain no private-value provenance; (b) as a test, any integer token in
  `public_prompt` matching a private value must trace to a public parameter
  by provenance (string coincidence allowed, provenance leak fatal).
- **IR validation tests**: every §1.3 validity rule violated once and
  rejected (extra arg, missing arg, wrong ref kind, cycle, bad positions,
  bad sink, unknown handle, manifest/registry mismatch).
- **Grammar/limit tests**: every typed rejection code exercised at least
  once, incl. `E_RESOURCE_KIND` (wrong kind and wrong layout),
  `E_TRUNCATED`, `E_MAGNITUDE`, future/unavailable `step_k`, `a--5`,
  envelope edge cases (attributes, case variants, `<value>`, close-before-
  open, tag text in reasoning).
- **Failure propagation**: each §1.7 rule (blocked chain, surviving
  independent branch, blocked join, sink-failure scoring).
- **Fork orders**: both orders execute and score identically on shared
  latent programs; positions honored; **semantic-oracle conversion tested in
  both orders** [rev3].
- **Scheduler tests** [rev3]: joint contingency tables per cell × split
  (counts differ ≤ 1); no factor aliasing (all joint combos realized);
  renderer crossing complete.
- **Cache isolation**: intervention variants and visibility conditions hit
  distinct keys; upstream raw-completion reuse across intervention variants
  verified safe.
- **Split isolation**: no `latent_program_id` across namespaces.
- **Random valid-AST fuzzing**: grammar-valid artifacts, tool vs reference
  evaluator (agreement; no unexpected exceptions).
- **10k agreement command**: stratified by operator × cell; recorded
  acceptance command, not pytest.

## 5. Decision register

| # | Decision | Status |
|---|---|---|
| D1 | Payloads in-context + host-side | retained |
| D2 | Rotation removed from count pipeline; select retains rotation | retained (v0.2) |
| D3 | Keyed-record values pairwise distinct | retained |
| D4 | Digits everywhere | retained |
| D5 | Only the enumerated prohibited coincidences are rejection-guarded (operand echo, index echo, listed value collisions); Lookup/Code-select answers necessarily occur in payloads | retained (narrowed v0.2) |
| D6 | m = L in `math_code` | retained |
| D7 | Fixed name pools | retained |
| D8 | Join skeleton `step_1 × step_2 + q` | retained |
| D9 | Operand naming a, b, c, d / m | retained |
| D10 | Workers receive the original public problem | retained |
| D11 | Cache stores raw completions; tools re-executed per call | retained |
| D12 | Fork two-call shortcut = 18-workflow contraction family, **with frozen contracted subtasks** | extended [rev3] |
| D13 | `GENERIC_SUBTASK` frozen — **reworded, no format instruction** (§1.11) | revised [rev3] |
| D14 | No negative literals / unary minus in artifact grammars | retained |
| D15 | Public-numeric collisions **flagged + pre-registered, not rejected**; non-collision stratum = clean Stage-3/4 headline (§1.16) | **new [rev3] — explicit sign-off requested** (rejection instead must be chosen now: rejection-rule kinds freeze at phase 1) |
| D16 | Endpoint system prompts + demonstrations = separately reviewed 0A freeze artifact, before construction screening | **new [rev3]** |

## 6. Errata against the rev6 contract — proposed for approval [rev3 wording]

Recorded so the archived plan is not edited; **each is proposed for approval
as part of this phase-1 sign-off**:

1. `WorkerResult` typing: rev6 contract 3's `value: Integer` superseded by
   the §1.7 union.
2. Lookup artifact form: rev6's illustrative `lookup(Q31, …)` superseded by
   `lookup(resource, …)` with `R-` handles.
3. Naming: `13_f_plan_rev6.md` titles itself "v5"; the single unambiguous
   name is **the rev6 contract**.
4. "Best two-call shortcut" (rev6 CE1 fork gate) defined in §1.11/D12.
5. "100 programs" (rev6 Stage-1A) means 100 latent clusters (§1.3).
6. The deployable oracle is a semantic-node mapping (§1.8); rev6's
   positional phrasing ("assignment") is interpreted semantically
   [rev3 — new].
7. `E_TRUNCATED` added to the typed-rejection enum so rev6's parse-vs-
   truncation telemetry split is exact [rev3 — new].

## 7. Freeze record

| Phase | Scope | Status |
|---|---|---|
| 1 | Operator semantics; grammars + envelope + limits; public/private boundaries; observation/request contracts; IR schemas; reference functions; rejection-rule kinds (incl. D15 choice); intervention semantics; oracle definition; renderer strings; baseline definitions incl. frozen subtask strings; identity/PRNG/serialization freezes; decision register | **pending reviewer sign-off of this file (v0.3)** |
| 2 | All **(S)** ranges = the difficulty profile (§1.14) | after the construction screen, before fresh qualification data |

Endpoint system prompts and demonstrations (D16) freeze as a reviewed 0A
artifact before the construction screen. Any post-qualification change to
generator, renderer, prompt, tool, parser, or profile retires the affected
qualification set (rev6 contract 8).
