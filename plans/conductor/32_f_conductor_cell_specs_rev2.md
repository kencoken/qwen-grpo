# Conductor cell specifications — v0.2 (rev2, awaiting reviewer sign-off)

Revision of [`30_f_conductor_cell_specs.md`](30_f_conductor_cell_specs.md)
addressing every item in
[`31_s_conductor_cell_specs_critique.md`](31_s_conductor_cell_specs_critique.md).
Supersedes v0.1 in full — this document is the phase-1 freeze candidate.
Anatomy still follows the reviewed examples in
[`20_s_where_we_landed.md`](20_s_where_we_landed.md) and the plan contracts in
[`13_f_plan_rev6.md`](13_f_plan_rev6.md) (canonical name: **the rev6
contract** — see errata, §6).

**Two-phase freeze** (unchanged): phase 1 on approval of this file (operator
semantics, artifact grammars, public/private boundaries, observation/request
contracts, reference functions, rejection-rule kinds, intervention semantics,
renderer strings); phase 2 after the 100-example construction screen (every
range marked **(S)**, collectively the *difficulty profile*, §1.14).

All worked examples and rejection/ablation checks in §3 are machine-verified
(129 checks across v0.1 + this revision). Where the critique's new
operand-relevance rules invalidated v0.1 fixtures, the fixtures were replaced
and the replacements re-verified (noted inline).

## Disposition of critique items

| Critique item | Resolution |
|---|---|
| 1. Freeze observations | §1.5 (Stage-2 observation, position map, byte-stable worker request, D10); fork clause order now tracks branch order (§3.6) |
| 2. Schema repairs | §1.2 tagged `keyed`/`operands` union + `E_RESOURCE_KIND`; §1.3 typed IR argument bindings; §2.1 new `seq_at` primitive |
| 3. Identity/split/visibility | §1.13 ids, disjoint seed namespaces, labelled intervention hashes; §1.12 visible condition; clusters = latent programs |
| 4. Executable baselines | §1.11 (all seven arms specified incl. frozen generic-subtask string and the enumerated two-call family; token/tool reporting) |
| 5. Intervention/caching | §1.9 mediator (wire) intervention, 5-step procedure, follow-through metric; §1.10 raw-completion cache, tools re-executed |
| 6. Answer-irrelevant complexity | §3.3 count pipeline loses rotation; primitive-ablation rejection rules added to count, select, and every modular node (§3.2, §3.5) |
| 7. Nuisance gate | §1.8 replaced by exact-balance enforcement + conditional audit + descriptive lexical-router report; no second Lookup→Math resource |
| 8. Distributions | §1.14 proposal distributions, categorical balance, rejection telemetry + 75 % cap, profile hash, no per-instance selection; subtype-stratified reporting |
| 9. Failure/parser contracts | §1.7 `WorkerResult` union + propagation rules; §1.6 uniform limits, tokenization, associativity, `%` edge cases |
| Specific corrections | all applied — see §6 (errata) and inline notes marked **[rev2]** |

---

## 1. Global conventions

### 1.1 Integers and canonical wire form

- All public outputs are integers. Canonical decimal form at text→integer
  boundaries: `0` or `-?[1-9][0-9]*` — applies to terminal answers parsed from
  text (direct baselines, the deferred `<value>` control). `0012`, `+5`,
  `5.0`, `1,000`, internal whitespace are rejected.
- **Artifact grammars admit only nonnegative literals** (`0 | [1-9][0-9]*`);
  there is no negative-literal token and no unary minus (D14, §1.6). Negative
  values may still arise from subtraction and are legal intermediates.
- Digits-with-leading-zero → `E_NONCANONICAL_INT`; any other malformed token →
  `E_PARSE`.
- All internal arithmetic is exact arbitrary-precision, magnitude-capped
  (§1.6); fractions exist only transiently inside exact division.
- Terminal (gold) answers are ≥ 1 in every cell. Intermediates may be 0 where
  noted (`math_code` index).

### 1.2 Resource kinds and handles

Two top-level resource kinds; `integer_record` is a **tagged union** [rev2]:

| kind | layout | payload | bound by |
|---|---|---|---|
| `integer_record` | `keyed` | entity → field → int | Lookup dereferencing only |
| `integer_record` | `operands` | identifier → int (single lowercase letters) | Math identifiers only |
| `integer_list` | — | ordered list of ints | Code `resource` only |

- Dereferencing a wrong layout/kind is the typed rejection `E_RESOURCE_KIND`,
  never an exception. A Math endpoint may still *read* a keyed record
  in-context and emit literals (preserves D1).
- N4 entity/field balancing (§1.8) applies to `keyed` records only.
- `keyed` records: all values pairwise distinct (D3). `operands` records: names
  `a, b, c, d` in order, modulus always `m` (D9).
- **Handles**: `R-` + digit + uppercase letter + digit, uniform, unique within
  an instance, independent of cell/payload/split (N1). Manifest = handles in
  shuffled order (N8).

**Worker-facing payload text** (frozen):

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

Canonical integers; keyed records in stored entity order; operands records in
identifier order; LF newlines; no trailing whitespace.

### 1.3 Stored-instance schema and reference IR

[rev2] adds the identity/visibility fields; argument bindings are now typed
references (`lit` / `res` / `node`), and dependency edges are **derived** from
`node` references, not stored:

```json
{
  "cell_id": "lookup_math",
  "latent_program_id": "lookup_math:qualification:00042:9f3ac1d2",
  "render_instance_id": "lookup_math:qualification:00042:9f3ac1d2:goal_first:private",
  "renderer_id": "goal_first",
  "split_id": "qualification",
  "visibility_condition": "private",
  "difficulty_profile_version": "dp-<sha256-prefix>",
  "generator_version": "specs-v0.2+<code-version>",
  "seed": 18421,
  "public_prompt": "...",
  "public_manifest": ["R-3T5"],
  "private_registry": {
    "R-3T5": {"kind": "integer_record", "layout": "keyed", "payload": {"Aster": {"units": 31}, "Cedar": {"units": 17}, "Grove": {"units": 39}, "Ivory": {"units": 53}}}
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

- `op` ∈ {`lookup`, `affine`, `ratio`, `modular`, `product_affine`,
  `seq_count`, `seq_select`, `seq_at`} (§2.1).
- **`positions`** is the semantic-node → workflow-position map [rev2]: entry
  *k* (1-based) is the node executed as step *k*. For fork/join it records the
  sampled branch order.
- Cluster identity = `latent_program_id`: all renderings and both visibility
  variants of one latent program share it, stay in one split, and count as
  **one** program — "100 qualification programs" means 100 latent clusters,
  not 100 rendered prompts [rev2].
- Reference subtasks and interventions are derived deterministically
  (templates in §3; hashes in §1.13), not stored.
- Strip-test consequence (rev6 contract 5): the execution path never reads
  `reference_program` or `gold_answer`; only the scorer reads `gold_answer`.

### 1.4 Renderers

Three manually authored cosmetic renderers, fully crossed with every cell:
`resource_first` (canonical), `goal_first`, `bound_var`. Renderer template
inputs are only handles and public parameters (structural no-leakage).
Frozen rules: numerals as digits everywhere (D4); display typography
`× − ÷ mod` in prompts, ASCII `* - / %` in artifacts; indexing always
"zero-based"; shared connective vocabulary (N5). **All renderer strings are
fully enumerated in §3** [rev2] — no template is described by delta from
another.

### 1.5 Observation and request contracts [rev2]

**What the Stage-0C/2 routing policy observes** (private condition; frozen
skeleton — the exact system-prompt string is a named constant checked in at
0A, fingerprinted into the runtime profile, and frozen before the construction
screen):

```text
Problem:
{public_prompt}

Resources available: {manifest handles, comma-separated, manifest order}

Steps:
1. (resource: {handle|none}; previous results: {none|all}) {reference subtask 1}
2. ...

Choose one worker for each step.
```

The numbered steps are the reference subtasks in `positions` order, so the
workflow-position → semantic-node mapping is **observable**: for fork/join,
step 1 names whichever branch was sampled first, and the public prompt's
clause order tracks the same order (§3.6). The policy emits
`{"worker_ids": [...]}` only; extra fields are rejected (rev6 contract 1).

**What a worker observes** — the canonical, byte-stable request template. User
message blocks, in this fixed order, each present or omitted as a whole;
exactly one blank line between blocks; LF newlines; no trailing whitespace;
canonical integers:

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

- `Problem` is always present (**D10**: workers receive the original public
  problem, as in the original task proposal. Rationale: it keeps the
  generic-subtask arm §1.11 informative — without it, generic subtasks
  collapse to floor and the Stage-3 reference-vs-generic gate becomes vacuous.
  Payload privacy, not prompt privacy, carries the causal-necessity design:
  a downstream worker still cannot recompute a corrupted predecessor because
  it lacks the upstream payload).
- `Task` = the step's subtask (reference, learned, or the frozen generic
  string).
- `Resource` omitted when the step has no authorized resource.
- `Previous results` present iff access = `all`: one line per predecessor in
  step order, `step_k = {value}`; these lines and the host-side binding are
  the **only** channels for predecessor values.
- The final instruction line is fixed per protocol; direct (non-endpoint)
  baselines replace it with the answer-line protocol of §1.11.
- Endpoint system prompts `SYSTEM_LOOKUP` / `SYSTEM_MATH` / `SYSTEM_CODE`
  (role + grammar description + fixed demos) are frozen named constants
  checked in at 0A, fingerprinted, frozen before the construction screen; any
  later change retires qualification sets (rev6 contract 8).
- **Canonical rendered request** = the chat template applied to (system
  string, user string) — this byte string is the cache-key component (§1.10)
  and the byte-stability test target (§4).

### 1.6 Artifact grammars, limits, typed rejections

Endpoints (unchanged): Lookup = Qwen2.5-1.5B-Instruct + keyed retrieval;
Math = Qwen2.5-Math-1.5B-Instruct + exact calculator;
Code = Qwen2.5-Coder-1.5B-Instruct + whitelist sequence interpreter.
**D1 retained**: authorized payloads are delivered in-context *and* bound
host-side to the tool.

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

**Tokenization and evaluation** [rev2 — frozen edge cases]:

- No negative literals, no unary minus (D14). `-` is always the binary
  operator and only in the Math grammar; `a--5` and `--` sequences →
  `E_PARSE`. Payload values and all artifact-expressible reference programs
  need only nonnegative literals; negative *intermediates* from subtraction
  are legal.
- Precedence `* / %` over `+ -`; all binary operators left-associative;
  parentheses override. Whitespace permitted between tokens.
- `/` exact in ℤ (zero remainder, sign-correct) else `E_INEXACT_DIV`; divisor
  0 → `E_DIV_ZERO`.
- `%` floor-mod. Modulus must evaluate > 0: modulus 0 → `E_DIV_ZERO`,
  negative → `E_BAD_ARG` (reachable via expressions, not literals).
- `resource` binds to the step's authorized payload of the grammar-compatible
  kind/layout (§1.2): none authorized → `E_NO_RESOURCE`; authorized but wrong
  kind/layout → `E_RESOURCE_KIND`. Math single-letter identifiers bind only
  against an `operands` record; unknown/unbound → `E_UNKNOWN_IDENT`.
- `step_k` resolves iff access = `all` and `k <` current step index, else
  `E_UNKNOWN_IDENT`.
- `rotate_left(xs, k)`: `k ≥ 0` (`E_BAD_ARG`), rotates by `k mod len`.
  `at(xs, i)`: zero-based, out of range → `E_INDEX_RANGE`. `count_gt`:
  strict `>`.

**Uniform limits, all grammars** [rev2]:

| Limit | Value | Rejection |
|---|---|---|
| artifact size (after trim) | ≤ 512 bytes | `E_PARSE` |
| AST nodes / depth | ≤ 64 / ≤ 8 | `E_DEPTH` |
| integer-literal digits | ≤ 12 | `E_PARSE` |
| any intermediate or result magnitude | ≤ 10¹² | `E_MAGNITUDE` |

**Typed rejection codes** (complete; all take the contract-4 "well-formed
action that fails in the world" path; unexpected exceptions propagate and
abort): `E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`, `E_UNEXPECTED_TAG`, `E_PARSE`,
`E_NONCANONICAL_INT`, `E_UNKNOWN_IDENT`, `E_NO_RESOURCE`, `E_RESOURCE_KIND`,
`E_UNKNOWN_KEY`, `E_UNKNOWN_FIELD`, `E_INDEX_RANGE`, `E_INEXACT_DIV`,
`E_DIV_ZERO`, `E_BAD_ARG`, `E_DEPTH`, `E_MAGNITUDE`.

**Primitive semantics** (implemented twice, independently — `tools.py` and
`program.py`; the 10k agreement command compares them, stratified by operator
× cell [rev2]): `stable_unique` (first occurrences, order preserved),
`rotate_left`, `at`, `count_gt`, `lookup`, and the numeric ops of §2.1.

### 1.7 WorkerResult and failure propagation [rev2]

Supersedes rev6's `WorkerResult(status, value: Integer, …)` sketch (errata
§6):

```text
status         ∈ {success, typed_failure, dependency_blocked}
value          : int | null      (int iff status = success)
rejection_code : code | null     (set iff status = typed_failure)
artifact_valid : bool
tool_executed  : bool
```

Frozen propagation rules:

1. A step whose status ≠ `success` blocks every later step with access =
   `all` (binary access means such steps depend on *all* predecessors); those
   steps are marked `dependency_blocked` and **no worker call is made** for
   them.
2. Steps with access = `none` are unaffected — independent fork branches
   continue.
3. A join is therefore blocked if either branch fails.
4. The terminal result is the sink step's value; if the sink is not
   `success`, the terminal result is null and the workflow scores 0.5
   (schema-valid action that failed in the world).
5. Only infrastructure failures abort the update (rev6 contract 4).

### 1.8 Balance enforcement and shortcut audit [rev2 — replaces the v0.1 nuisance-classifier gate]

The v0.1 gate ("nuisance features must not predict cell") cannot pass
honestly: resource count separates the composite cells by construction, and
operation vocabulary is the intended routing signal (rev6 explicitly permits
transparent template routing at this stage). Replacement:

1. **Exact balance, generator-enforced and unit-tested**: renderer id, fork
   branch order, formula template, code shape, affine sign, and
   target-position stratum are assigned round-robin over latent index within
   each cell × split (exact counts, not expectation); handle characters
   uniform; manifest order shuffled; splits balanced across all categorical
   factors.
2. **Conditional nuisance audit** at the construction screen: within each
   cell (topology and operation held fixed), the features {renderer id,
   entity/field names, handle strings, prompt length, numeric formatting}
   must not predict the gold answer band or the split (classifier AUC
   compatible with 0.5).
3. **Descriptive shallow lexical-router report**: a bag-of-words router's
   cell-identification and routing accuracy is reported, not gated — expected
   high, and acceptable for the rev6 claim (fixed endpoint selection).
4. The stronger anti-template gate is reserved for the deferred
   semantic/counterfactual renderer.
5. Per the critique: **no second resource is added to Lookup→Math** to
   balance resource count.

Legitimate semantic cues ("retrieve a field", "multiply", "zero-based index",
"remove duplicates") remain by design.

### 1.9 Interventions: mediator (wire) semantics [rev2]

Both kinds per dependency edge *(u → v)*, executed on the deployable-oracle
assignment at calibration time. These are **mediator/wire interventions** —
they replace the transmitted intermediate, not the private resource
(resource-level counterfactuals are deferred and would be the stronger test):

1. Replace step *u*'s recorded value with replacement *r* through a
   calibration-only executor override.
2. The replacement takes effect in **both** channels: the `step_u = r`
   context line and the host-side tool binding.
3. Rerun the downstream worker(s) with a distinct cache identity (automatic:
   the canonical rendered request bytes differ, §1.10; upstream completions
   are reusable).
4. **Corruption**: score against the stored `gold_answer` (expect accuracy to
   fall; gates in rev6 CE1).
5. **Counterfactual consistency**: score against `gold'` = the reference sink
   recomputed **outside the executor** via the reference functions with the
   override applied.

Replacement *r* is drawn from a PRNG seeded by the labelled hash of §1.13
(never Python `hash()`), under the per-cell replacement rule (§3), which
provably changes the sink.

**Reporting** [rev2]: both *full-workflow intervention accuracy* and
*conditional follow-through* — the counterfactual-consistency rate among
examples whose upstream step originally succeeded.

Atomic cells have no edges: interventions N/A (ablation rejection rules and
metamorphic tests cover them). Missing/skip variants prove only tool
input-validation (rev6 contract 7).

### 1.10 Caching rule [rev2]

The cache stores **raw model completions**, keyed by
`runtime-profile fingerprint + endpoint fingerprint + canonical rendered
request bytes` (§1.5). Tools are re-executed on every call against current
bindings (cheap CPU). An executed `WorkerResult` is **never** cached: all
resource and predecessor bindings live in the request bytes, so intervention
variants and visibility conditions get distinct keys by construction, and
tool-version changes are covered by the profile fingerprint (rev6 contract 8).

### 1.11 Baselines — executable definitions [rev2]

Direct (non-endpoint) baselines use the answer-line protocol: the request ends
with the fixed line `Answer with a single integer on the final line.`; the
last non-empty line, trimmed, must parse as a canonical integer, else scored
wrong.

| # | Arm | Model | Input | Notes |
|---|---|---|---|---|
| B1 | Public-only direct | 3B base | `Problem` block only | Reported against **majority-class and public-feature guessing references** (best constant per cell; best answer given public parameters only). Small-support outputs (modular residues, counts) make nonzero accuracy expected; **leakage is decided by provenance (§4), not by accuracy ≈ 0** |
| B2 | Endpoint-without-resource | each endpoint | worker request minus `Resource` | Retained as a typed-rejection diagnostic |
| B3 | Visible direct | 3B base | `Problem` + all payloads (visible rendering, §1.12) | Diagnoses self-solving capability; without a `SELF` action it does **not** test delegation |
| B4 | Local-node | 3B base | node payload + node reference subtask + required predecessor gold values (`step_k = v` lines) | Downstream nodes are now testable [rev2] |
| B5 | One-call whole-task | each endpoint | `Problem` + `Task: Complete the task and return the final result.` + all payloads in manifest order (union payload — harness-only exception, never a policy option) | Host binding is **type-directed**: each grammar slot binds where exactly one compatible resource exists in the authorized set (always the case in v0 cells); incompatible resources remain readable in-context for mental/inlined reasoning |
| B6 | Generic-subtask arm | endpoints per deployable oracle | reference workflow with every subtask replaced by the frozen string below | Gates Stage 3 (rev6: reference ≥ generic + 10 pts) |

- **Best one-call** = the endpoint selected on construction data and frozen
  for qualification; the per-example hindsight maximum is diagnostic only
  (mirrors the deployable-oracle rule).
- **`GENERIC_SUBTASK` (frozen now)**: `Complete your part of the task using
  the provided resource and any previous results, and return a single
  integer.`
- **Fork two-call shortcut family (defined)** [rev2]: all two-step `[none,
  all]` chains in which step 1 is assigned one manifest resource and step 2
  the other (both orientations), endpoints ranging over the 3 × 3
  assignments — **18 workflows**, fully enumerated on the construction
  screen; "best two-call shortcut" = the best of these, frozen from
  construction data.
- **Reporting**: every condition reports prompt tokens and tool-call counts.
  If hierarchy wins primarily by partitioning a long union context into short
  local contexts, that is a valid systems result and will be identified as
  such.

### 1.12 Visibility conditions [rev2]

`visibility_condition` ∈ {`private`, `visible`}. The visible rendering
appends, after the `Problem` block of the *Conductor-side* observation:

```text
Resources:
{payload text of each manifest handle, manifest order, blank line between}
```

Worker-side requests are identical in both conditions. Visible instances share
`latent_program_id` (and split) with their private counterparts — the
pre-registered ~100-program visible qualification slice is paired by
construction. Visibility enters `render_instance_id`, the observation bytes
(hence cache identity), and the runtime profile's visibility policy
fingerprint.

### 1.13 Identity, seeds, splits [rev2]

- **Seed namespaces** (disjoint by construction):
  `construction, qualification, train, dev, test`.
  `seed64(...) = first 8 bytes of SHA-256("qwen-grpo-conductor" ␟
  generator_version ␟ namespace ␟ cell_id ␟ latent_index)` (␟ = 0x1F
  separator).
- `latent_program_id = "{cell_id}:{namespace}:{latent_index:05d}:{hex8}"`
  (hex8 = first 4 bytes of the same hash).
- `render_instance_id = latent_program_id + ":" + renderer_id + ":" +
  visibility_condition`.
- `split_id`: construction and qualification are namespaces of their own;
  train/dev/test partition latent programs — **no latent program ever crosses
  a split** (unit-tested, §4).
- **Intervention identity**: replacement PRNG seeded by
  `first 8 bytes of SHA-256("intervention" ␟ latent_program_id ␟ edge_label ␟
  kind)` with textual `edge_label` like `"n1->n3"` and `kind` ∈
  {`corruption`, `counterfactual`}. Executable, stable, never Python
  `hash()`.

### 1.14 Distributions and sampling protocol [rev2]

- **Numeric parameters**: independent integer-uniform on their (S) bands
  unless stated otherwise below.
- **T1 exact division is constructive**, not rejection-based: sample `a, b,
  d`, then `c` uniform on `{c ∈ [1, 20] : c ≡ a·b (mod d)}` (nonempty since
  d ≤ 12 < 20).
- **Records**: entities and fields uniform without replacement from the
  pools; values uniform without replacement from the band; **target-position
  strata** (target entity in first/middle/last third of the record) assigned
  round-robin.
- **Lists**: dedup-flavor — i.i.d. uniform on [1, 9], then flavor + cell
  rejection rules; select-flavor — uniform without replacement on [1, 99].
- **Categorical factors** (formula template, code shape, sign, renderer, fork
  branch order, target stratum): round-robin over latent index → exact
  balance per cell × split (§1.8).
- **Telemetry at the construction screen**: rejection counts by rule;
  post-rejection marginal distributions per parameter; **maximum acceptable
  rejection rate 75 % per cell** — exceeding it fails the difficulty profile
  (fix the profile; never hand-prune instances).
- **Pre-registration rule (verbatim from the critique)**: no individual
  instance is ever retained or discarded based on worker performance; only an
  entire difficulty profile or cell passes or fails construction screening.
- **Difficulty profile** = the canonical JSON of every (S) band and
  distribution; `difficulty_profile_version` = its SHA-256 prefix, stored per
  instance, frozen at phase 2.
- **Qualification reporting is stratified by latent subtype** — T1/T2/T3,
  count/select, plus/minus, renderer, fork order — not only pooled by cell.
- Per-instance resampling cap stays at 1000 attempts (generator error, never
  a silent band change); rules re-asserted at load time.

### 1.15 Name pools

Unchanged from v0.1 (D7): 20 entities (Aster, Birch, Cedar, Elm, Fern, Grove,
Hazel, Ivory, Juniper, Lark, Maple, Nettle, Onyx, Pine, Quill, Rowan, Slate,
Tarn, Vale, Wren); 10 fields (crates, units, tokens, points, seats, kits,
spools, tiles, flasks, reams); operand identifiers per D9.

---

## 2. Shared generator machinery

### 2.1 Primitive ops and reference functions

[rev2]: `seq_count` loses rotation; `seq_at` added (the v0.1
`seq_select_by_step` was undefined).

```python
def prim_lookup(rec, key, field) -> int           # keyed retrieval (layout=keyed only)
def prim_affine(x, p, sign, q) -> int             # p*x + q  |  p*x - q
def prim_ratio(a, b, c, d) -> int                 # (a*b - c) / d, exact else raise
def prim_modular(a, b, c, m) -> int               # (a*b + c) % m, m > 0
def prim_product_affine(x, y, q) -> int           # x*y + q
def prim_seq_count(xs, t) -> int                  # count_gt(stable_unique(xs), t)
def prim_seq_select(xs, k, i) -> int              # at(rotate_left(stable_unique(xs), k), i)
def prim_seq_at(xs, i) -> int                     # at(xs, i)  — no dedup, no rotation
```

A cell's direct reference function composes these over the registry and
public parameters; it is the source of `gold_answer` and of counterfactual
recomputation, and one side of the 10k agreement command.

### 2.2 Shared samplers

As §1.14: `integer_record(N, F, band, layout)`;
`integer_list_dedup(L, band=[1,9])` with `3 ≤ U ≤ L − 2` [rev2: `U ≥ 3` added
— at U = 2 the fork counterfactual replacement pool `[1, U−1] \ {n2}` is
empty, and count answers become forced];
`integer_list_select(L, band=[1,99])` pairwise distinct.

---

## 3. Cell specifications

Conventions: **O** = ordinary, **B** = boundary worked example; every example
lists its rejection/ablation checks; example artifacts illustrate the grammar
(any grammar-valid artifact whose executed value is correct scores). No gold
worker is presumed; assignments come from the measured payoff surface.
Reference subtasks are tool-neutral. All renderer strings are enumerated in
full.

### 3.1 `lookup_atomic` — atomic Lookup

**Shape**: 1 step, access `[none]`, 1 keyed `integer_record`.

| Parameter | Range |
|---|---|
| entities N | 3–16 **(S)**, `N × F ≤ 60` |
| fields F | 1–5 **(S)** |
| value band | 10–99 **(S)**, pairwise distinct |
| target (key, field) | uniform; position stratified (§1.14) |

**Rejection rules**: none beyond the record invariants — difficulty lives in
N, F, distractors.

**Renderer strings**:

- `resource_first`: `Resource {H} contains keyed integer records. Return the
  {field} value recorded for {key}.`
- `goal_first`: `Return the {field} value that {H} records for {key}.`
- `bound_var`: `Let v be {key}'s {field} in {H}. Output v.`

**Reference program**: `n1 = lookup(H, key, field)`; positions `[n1]`; sink
`n1`.

**Reference subtask**: `Retrieve {key}'s {field} value from the requested
resource.`

**Example artifact**: `<artifact>lookup(resource, "Grove", "crates")</artifact>`

**O** — `R-7K2`: Aster.crates = 31, Cedar.crates = 17, Grove.crates = 39,
Ivory.crates = 53; target Grove.crates. Gold: **39**.

**B** — small-N, band-edge values [rev2: relabelled — N = 4 is not the band
minimum of 3]. `R-4H8`: Lark.units = 99, Onyx.units = 10, Pine.units = 11,
Quill.units = 98; target Quill.units. Gold: **98**.

**Interventions**: none (atomic). Distractor invariance: resampling
non-target entities/values leaves gold unchanged.

**One-call baseline**: B5 with the record as the single payload.

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
operand values; **modular operand-relevance checks** [rev2] — every modular
node (here and `math_code` step 1) must satisfy, writing `g` for the residue:

- drop-c: `(a·b) mod m ≠ g` (⇔ `c mod m ≠ 0`)
- a→1: `(b + c) mod m ≠ g`
- b→1: `(a + c) mod m ≠ g`

(T1/T3 operand relevance is band-guaranteed: b ≥ 10, c ≥ 1, d ≥ 2.)

**Renderer strings** (`{names}` = `a, b, c and d` / `a, b, c and m` /
`a, b and c`; `{formula}` = the template's public formula):

- `resource_first`: `{H} contains integers {names}. Evaluate` `` `{formula}` ``
  `exactly.`
- `goal_first`: `Return the exact value of` `` `{formula}` `` `, where {names}
  are the integers recorded in {H}.`
- `bound_var`: `Let {names} be the integers in {H}. Output` `` `{formula}` ``
  `.`

**Reference program**: `n1 = ratio|modular|affine(a, b, c[, d|m])` with `lit`
bindings; positions `[n1]`; sink `n1`.

**Reference subtask**: `Evaluate` `` `{formula}` `` `exactly using the
integers in the requested resource.`

**Example artifact**: `<artifact>(a * b - c) / d</artifact>`

**O (T1)** — `R-2P6`: a = 83719, b = 43, c = 1, d = 6.
`83719 × 43 = 3599917; − 1 = 3599916; ÷ 6 =` **599986**. (Exact ✓; ∉ operands
✓.)

**O (T2)** — [rev2: replaced — the v0.1 fixture (999983, 97, 19, 12 → 6)
fails the b→1 check since 999983 + 19 ≡ 6 (mod 12).] `R-7Q4`: a = 999983,
b = 89, c = 19, m = 12. Residues 11, 5, 7: `(11·5 + 7) mod 12 =` **2**.
(drop-c 7 ≠ 2 ✓; a→1 (89+19) mod 12 = 0 ≠ 2 ✓; b→1 (999983+19) mod 12 = 6 ≠ 2
✓; c mod m = 7 ≠ 0 ✓; ∈ [1, 11] ✓; ∉ operands ✓.)

**O (T3)** — `R-1X5`: a = 524287, b = 83, c = 17.
`524287 × 83 + 17 =` **43515838**. (∈ [1, 10⁹] ✓; ∉ operands ✓.)

**B (T1, low edges)** — `R-8B2`: a = 10007, b = 10, c = 2, d = 6.
`(100070 − 2) ÷ 6 =` **16678**. (Exact ✓; ∉ operands ✓.)

**Interventions**: none (atomic).

**One-call baseline**: B5 with the operand record as the single payload.

### 3.3 `code_atomic` — atomic Code (one call, nested composition)

**Shape**: 1 step, access `[none]`, 1 dedup-flavor `integer_list`.

**Pipeline shapes** (round-robin 50/50; [rev2: **rotation removed from the
count pipeline** per critique §6 — it could never affect `count_gt`, so a
worker ignoring it earned full reward, which would contaminate Stage 3 where
incomplete instructions must not look successful. Rotation is retained only
where it has stakes: the select shape. All four count-shape fixtures keep
their gold answers under the simplified pipeline — verified]):

| Shape | Latent pipeline |
|---|---|
| count | `count_gt(stable_unique(xs), t)` |
| select | `at(rotate_left(stable_unique(xs), k), i)` |

| Parameter | Range |
|---|---|
| L | 8–16 **(S)**, values 1–9 **(S)** |
| U = len(stable_unique) | **3** ≤ U ≤ L − 2 [rev2: lower bound added] |
| k (select) | 1–9 **(S)**, `k mod U ≠ 0` |
| t (count) | 1–8 **(S)** |
| i (select) | 0…U−1 |

**Rejection rules** (incl. the [rev2] primitive-ablation rules):

- both: `3 ≤ U ≤ L − 2`;
- count: `1 ≤ answer ≤ U − 1`; **dedup ablation**: `count_gt(xs, t) ≠
  count_gt(stable_unique(xs), t)` (counting the raw list must differ);
- select: `k mod U ≠ 0`; **dedup ablation**:
  `at(rotate_left(xs, k), i) ≠ gold`; **rotation ablation**:
  `at(stable_unique(xs), i) ≠ gold`.

**Renderer strings — count shape**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values and count the values greater than {t}.`
- `goal_first`: `Return how many values exceed {t} in the sequence obtained
  from {H} by removing later occurrences of repeated values.`
- `bound_var`: `Let s be the sequence in {H} after removing later occurrences
  of repeated values. Output the count of values in s greater than {t}.`

**Renderer strings — select shape**:

- `resource_first`: `From the integer sequence in {H}, remove later
  occurrences of repeated values, rotate the remaining sequence left by {k}
  positions, and return the value at zero-based index {i}.`
- `goal_first`: `Return the value at zero-based index {i} of the sequence
  obtained from {H} by removing later occurrences of repeated values and
  rotating it left by {k} positions.`
- `bound_var`: `Let s be the sequence in {H} after removing later occurrences
  of repeated values and rotating left by {k} positions. Output the value of
  s at zero-based index {i}.`

**Reference program**: `n1 = seq_count(xs, t)` | `seq_select(xs, k, i)`;
positions `[n1]`; sink `n1`.

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
(U ✓; 1 ≤ 4 ≤ 7 ✓; dedup ablation: raw count 6 ≠ 4 ✓.)

**O (select)** — `R-5N1`: `[5, 3, 5, 8, 1, 3, 9, 2]`, k = 2, i = 4.
`stable_unique → [5, 3, 8, 1, 9, 2]` (U = 6); `rotate_left(2) → [8, 1, 9, 2,
5, 3]`; `at(4) =` **5**. (2 mod 6 ≠ 0 ✓; dedup ablation
`at(rotate_left(raw, 2), 4) = 9 ≠ 5` ✓; rotation ablation `deduped[4] = 9 ≠ 5`
✓.)

**B (count, answer = U − 1)** — `R-9E3`: `[9, 8, 9, 7, 6, 8, 5, 9]`, t = 5.
`stable_unique → [9, 8, 7, 6, 5]` (U = 5); `count_gt(5) =` **4** = U − 1.
(Dedup ablation: raw count 7 ≠ 4 ✓.)

**Interventions**: none (atomic). Metamorphic: `stable_unique` idempotence;
count invariance under any permutation of the deduplicated list.

**One-call baseline**: B5 with the list as the single payload.

### 3.4 `lookup_math` — Lookup → Math

**Shape**: 2 steps, access `[none, all]`; keyed record requested by step 1;
step 2 requests none and consumes `step_1`.

| Parameter | Range |
|---|---|
| record N, F, band | as §3.1; target value n1 ∈ [10, 99] |
| p | 2–9 **(S)** |
| q | 1–20 **(S)** |
| sign | {+, −} round-robin |

**Rejection rules**: answer ≥ 1; answer ∉ record values; answer ≠ n1.

**Renderer strings — minus form**:

- `resource_first`: `Retrieve {key}'s {field} from {H}. Return {p} times that
  value minus {q}.`
- `goal_first`: `Return the number obtained by subtracting {q} from {p} times
  {key}'s {field} recorded in {H}.`
- `bound_var`: `Let x be {key}'s {field} in {H}. Output` `` `{p}x − {q}` ``
  `.`

**Renderer strings — plus form**:

- `resource_first`: `Retrieve {key}'s {field} from {H}. Return {p} times that
  value plus {q}.`
- `goal_first`: `Return the number obtained by adding {q} to {p} times
  {key}'s {field} recorded in {H}.`
- `bound_var`: `Let x be {key}'s {field} in {H}. Output` `` `{p}x + {q}` ``
  `.`

**Reference program**: `n1 = lookup(H, key, field)`;
`n2 = affine(x={node n1}, p, sign, q)`; positions `[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Retrieve {key}'s {field} value from the requested
resource.` 2. `Multiply step_1 by {p}, then subtract {q}.` (plus form:
`…, then add {q}.`)

**Example artifacts**:
`<artifact>lookup(resource, "Cedar", "units")</artifact>`;
`<artifact>3 * step_1 - 4</artifact>`

**O** — `R-3T5`: Aster.units = 31, Cedar.units = 17, Grove.units = 39,
Ivory.units = 53; target Cedar.units; p = 3, minus, q = 4.
`n1 = 17`; `n2 = 3 × 17 − 4 =` **47**. (∉ record ✓; ≠ n1 ✓.)

**B (band edges)** — `R-2W9`: Vale.units = 99, Aster.units = 10,
Hazel.units = 23, Tarn.units = 57; target Vale.units; p = 9, minus, q = 20.
`n2 = 9 × 99 − 20 =` **871**. (∉ record ✓.)

**Interventions** (edge `n1->n2`, mediator semantics §1.9): replacement
`n1' ~ U([10, 99] \ {n1})`, resampled until `affine(n1') ≥ 1`; sink change
automatic (affine injective, p ≥ 2). Example (O): `n1' = 19` → corruption
keeps target 47 (execution yields 53, scored wrong); counterfactual target
`3 × 19 − 4 = 53`.

**One-call baseline**: B5 with the record as payload. With D1 a one-call Math
endpoint may read the record and inline the value — the construction screen
tunes N/F/distractors until the deployable oracle clears the +20-point gate.

### 3.5 `math_code` — Math → Code (computed index)

**Shape**: 2 steps, access `[none, all]`; step 1 requests the operand record,
step 2 requests the list and consumes `step_1`.

| Parameter | Range |
|---|---|
| a | 10⁸–10⁹ **(S)** |
| b | 10–99 **(S)** |
| c | 1–20 **(S)** |
| m = L | 8–16 **(S)** (D6: index always valid) |
| list | select-flavor, values 1–99 **(S)**, pairwise distinct |

**Rejection rules**: list pairwise distinct (⇒ every counterfactual index
changes the answer — the rev6 "answer-preserving counterfactual indices"
rejection is discharged structurally); answer ≠ n1 (index echo); answer ∉
{a, b, c, m}; **modular operand-relevance checks of §3.2 on node n1** [rev2];
intermediate n1 = 0 permitted (terminal ≥ 1 via the list band).

**Renderer strings**:

- `resource_first`: `{H1} contains integers a, b, c and m. Compute`
  `` `(a × b + c) mod m` `` `. Use the result as a zero-based index into the
  sequence in {H2} and return the selected integer.`
- `goal_first`: `Return the integer found in {H2} at the zero-based index
  given by` `` `(a × b + c) mod m` `` `, where a, b, c and m are the integers
  in {H1}.`
- `bound_var`: `Let i =` `` `(a × b + c) mod m` `` `, with a, b, c and m
  taken from {H1}. Output the value of the sequence in {H2} at zero-based
  index i.`

**Reference program**: `n1 = modular(a, b, c, m)`;
`n2 = seq_at(xs={res H2}, i={node n1})` [rev2: `seq_at` replaces the
undefined `seq_select_by_step`]; positions `[n1, n2]`; sink `n2`.

**Reference subtasks**: 1. `Evaluate` `` `(a × b + c) mod m` `` `exactly
using the integers in the requested resource.` 2. `Return the value at
zero-based index step_1 in the integer sequence from the requested
resource.`

**Example artifacts**: `<artifact>(a * b + c) % m</artifact>`;
`<artifact>at(resource, step_1)</artifact>`

**O** — [rev2: replaced — in the v0.1 fixture a = 982451653 ≡ 1 (mod 12), a
modularly inert operand that fails the a→1 check.] `R-6D1`: a = 314159265,
b = 55, c = 17, m = 12; `R-9V4`: `[41, 7, 83, 22, 65, 14, 39, 90, 56, 11, 72,
28]`. Residues 9, 7, 5: `n1 = (9·7 + 5) mod 12 = 8`; `n2 = list[8] =` **56**.
(drop-c 3 ≠ 8 ✓; a→1 0 ≠ 8 ✓; b→1 2 ≠ 8 ✓; c mod m = 5 ≠ 0 ✓; 56 ≠ 8 ✓; ∉
operands ✓; distinct ✓.)

**B (index = m − 1)** — [rev2: replaced — v0.1's b = 41 ≡ 1 (mod 8) fails the
b→1 check.] `R-3F7`: a = 123456789, b = 45, c = 6, m = 8; `R-6M2`: `[17, 64,
80, 23, 46, 91, 12, 58]`. Residues 5, 5, 6: `n1 = (5·5 + 6) mod 8 = 7`;
`n2 = list[7] =` **58**. (drop-c 1 ≠ 7 ✓; a→1 3 ≠ 7 ✓; b→1 3 ≠ 7 ✓; c mod
m = 6 ≠ 0 ✓; 58 ≠ 7 ✓; ∉ operands ✓.)

**Interventions** (edge `n1->n2`): replacement `i' ~ U([0, m−1] \ {n1})` —
always valid; sink change guaranteed by distinctness. Example (O): `i' = 3` →
corruption keeps target 56 (execution yields `list[3] = 22`, scored wrong);
counterfactual target **22**.

**One-call baseline**: B5 with record + list. Composition advantage is driven
by a's size: a one-call Code endpoint must compute the index without a
calculator; a one-call Math endpoint has no selection operator and must index
the in-context list mentally.

### 3.6 `fork_join` — Lookup + Code → Math (diagnostic)

**Shape**: 3 steps, access `[none, none, all]`; the two branch steps each
request one resource; the join requests none and consumes `step_1`, `step_2`.
**Diagnostic-only in v0**: not in the training mixture (admission gates
deferred); qualification slice 100–200 latent programs if paired CIs are
decisive. **If admitted to Stage-2 routing after its gates** [rev2:
conditional wording], fork/join tests endpoint selection *within a fixed
parallel DAG*; topology construction remains a Stage-4 claim.

**Branch order**: sampled round-robin 50/50. `positions` records it, the
Stage-2 observation numbers the subtasks in that order, and **the public
prompt's clause order tracks the same order** [rev2] — the position → node
map is observable end to end. The join formula is symmetric, so both orders
share reference semantics.

| Parameter | Range |
|---|---|
| record N, F, band | as §3.1; branch value n_lk ∈ [10, 99] |
| code branch | count shape of §3.3 (incl. U ≥ 3 and ablation rules) |
| q | 1–20 **(S)** |

Join skeleton (frozen, D8): `step_1 × step_2 + q`.

**Rejection rules**: both branch rule-sets apply; answer ∉ {n_lk, n_code} ∪
record values ∪ list values. Corruption of either branch provably moves the
sink (n_code ≥ 1, n_lk ≥ 10 ⇒ strict monotonicity in each argument).
**U ≥ 3** guarantees a nonempty counterfactual pool for the code branch
[rev2].

**Renderer strings — lookup-first order**:

- `resource_first`: `Retrieve {key}'s {field} from {H1}. Separately, remove
  later occurrences of repeated values from the integer sequence in {H2} and
  count the values greater than {t}. Return the product of the two results
  plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: {key}'s {field}
  recorded in {H1}, and the count of values greater than {t} after removing
  later occurrences of repeated values from the sequence in {H2}.`
- `bound_var`: `Let x be {key}'s {field} in {H1}. Let y be the count of
  values greater than {t} in the sequence from {H2} after removing later
  occurrences of repeated values. Output` `` `x × y + {q}` `` `.`

**Renderer strings — code-first order**:

- `resource_first`: `Remove later occurrences of repeated values from the
  integer sequence in {H2} and count the values greater than {t}. Separately,
  retrieve {key}'s {field} from {H1}. Return the product of the two results
  plus {q}.`
- `goal_first`: `Return {q} plus the product of two values: the count of
  values greater than {t} after removing later occurrences of repeated values
  from the sequence in {H2}, and {key}'s {field} recorded in {H1}.`
- `bound_var`: `Let x be the count of values greater than {t} in the sequence
  from {H2} after removing later occurrences of repeated values. Let y be
  {key}'s {field} in {H1}. Output` `` `x × y + {q}` `` `.`

**Reference program** (lookup-first shown): `n1 = lookup(H1, key, field)`;
`n2 = seq_count(xs={res H2}, t)`; `n3 = product_affine(x={node n1},
y={node n2}, q)`; positions `[n1, n2, n3]` (code-first: `[n2, n1, n3]`);
sink `n3`.

**Reference subtasks**: branch subtasks of §3.1/§3.3; join — `Multiply step_1
by step_2, then add {q}.`

**Example artifacts**: branch artifacts as §3.1/§3.3; join
`<artifact>step_1 * step_2 + 3</artifact>`.

**O (lookup-first)** — `R-5A8`: Aster.units = 31, Cedar.units = 14,
Grove.units = 39 (target Cedar); `R-1J7`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7,
4]`, t = 5; q = 3. `n1 = 14`; `n2 = 4`; `n3 = 14 × 4 + 3 =` **59**. (∉ values
✓; dedup ablation on branch: 6 ≠ 4 ✓.)
Branch counterfactuals: `14 → 15` ⇒ 63; `4 → 3` ⇒ 45.

**O′ (code-first golden fixture)** [rev2 — added per critique]: same latent
payloads and parameters, branch order swapped. Positions `[n2, n1, n3]`:
step 1 = count branch (`R-1J7`) → 4; step 2 = lookup branch (`R-5A8`) → 14;
step 3 join `step_1 × step_2 + 3 = 4 × 14 + 3 =` **59**. Public prompt uses
the code-first renderer strings; the Stage-2 observation lists the count
subtask as step 1.

**B (minimum code count)** — `R-8D4`: Wren.crates = 99, Slate.crates = 10,
Fern.crates = 57 (target Wren); `R-2K9`: `[4, 2, 4, 3, 1, 2, 3, 4]`, t = 3;
q = 20. `stable_unique → [4, 2, 3, 1]` (U = 4); `n2 = count_gt(3) = 1`;
`n1 = 99`; `n3 = 99 × 1 + 20 =` **119**. (U ≥ 3 ✓ so the counterfactual pool
`[1, 3] \ {1}` is nonempty; dedup ablation 3 ≠ 1 ✓; ∉ values ✓.)
Branch counterfactuals: `99 → 98` ⇒ 118; `1 → 2` ⇒ 218.

**Interventions** (edges `n1->n3`, `n2->n3`, both kinds each; fork gate:
per-branch corruption drop ≥ 20 pts, paired clustered lower CI):
`n1' ~ U([10, 99] \ {n1})`; `n2' ~ U([1, U−1] \ {n2})`; counterfactual
targets recomputed via `product_affine`.

**One-call baseline**: B5 with record + list. **Two-call baseline**: the
enumerated 18-workflow contraction family of §1.11, best frozen on
construction data (rev6 CE1: oracle ≥ +15 vs best two-call).

---

## 4. Acceptance hooks (0A battery consumes this file)

- **Golden fixtures**: every §3 worked example — including the code-first
  fork O′ [rev2] — asserting intermediates, gold, rejection/ablation
  compliance, intervention targets.
- **Byte-stability fixtures**: golden canonical rendered requests (§1.5) for
  one instance per cell × step × access pattern; byte-for-byte comparison.
- **Grammar/limit tests**: every typed rejection code exercised at least once
  [rev2], incl. `E_RESOURCE_KIND` (wrong kind and wrong layout),
  `E_MAGNITUDE`, future/unavailable `step_k`, `a--5`-style token streams,
  depth/size caps.
- **Failure propagation**: each rule of §1.7 (blocked chain step, surviving
  independent branch, blocked join, sink-failure scoring).
- **Fork orders**: both orders execute and score identically on shared latent
  programs; position map honored by the executor.
- **Cache isolation**: intervention variants and visibility conditions hit
  distinct keys; raw-completion reuse across intervention variants of the
  *upstream* step verified safe.
- **Split isolation**: no `latent_program_id` crosses construction /
  qualification / train / dev / test.
- **Random valid-AST fuzzing**: sampled grammar-valid artifacts evaluated by
  tool vs reference evaluator (agreement + no unexpected exceptions).
- **Metamorphic/distractor/renderer invariance** as in §3; provenance-based
  no-leakage as v0.1 (structural + provenance check, §1.11 B1 note).
- **10k agreement command**: stratified by operator × cell [rev2]; recorded
  acceptance command, not pytest.

## 5. Decision register

| # | Decision | Status |
|---|---|---|
| D1 | Payloads in-context + host-side | retained (critique concurs) |
| D2 | ~~50/50 count/select with rotation in both~~ | **superseded**: rotation removed from count (critique §6); select retains rotation |
| D3 | Keyed-record values pairwise distinct | retained |
| D4 | Digits everywhere | retained |
| D5 | Answer-coincidence rejections | **narrowed** [rev2]: the claim is only that the *enumerated prohibited coincidences* (operand echo, index echo, record/list-value collisions listed per cell) can never score — not that echoes in general cannot; Lookup and Code-select answers necessarily occur in their payloads (they are private; that is the design) |
| D6 | m = L in `math_code` | retained |
| D7 | Fixed name pools | retained |
| D8 | Join skeleton `step_1 × step_2 + q` | retained |
| D9 | Operand naming a, b, c, d / m | retained |
| D10 | Workers receive the original public problem (`Problem` block) | **new** [rev2] — see §1.5 rationale |
| D11 | Cache stores raw completions; tools re-executed per call | **new** [rev2] |
| D12 | Fork two-call shortcut = enumerated 18-workflow contraction family | **new** [rev2] |
| D13 | `GENERIC_SUBTASK` string frozen (§1.11) | **new** [rev2] |
| D14 | No negative literals / unary minus in any artifact grammar | **new** [rev2] |

## 6. Errata against the rev6 contract

Recorded here so the archived plan is not edited; each is approved by this
review round:

1. **`WorkerResult` typing**: rev6 contract 3's `value: Integer` is
   superseded by the §1.7 union (a rejected call has no integer value).
2. **Lookup artifact form**: rev6's illustrative `lookup(Q31, …)` is
   superseded by `lookup(resource, …)` with `R-`-format handles (reviewer
   preference; demos and 0A prompts follow this spec).
3. **Naming**: the plan file `13_f_plan_rev6.md` titles itself "v5"; the
   contract's single unambiguous name is **the rev6 contract**, and all
   documents reference it as such.
4. **"Best two-call shortcut"** in the rev6 CE1 fork gate is now defined
   (§1.11 / D12).
5. **"100 programs"** in rev6 Stage-1A sample sizes means 100 latent clusters
   (§1.3).

## 7. Freeze record

| Phase | Scope | Status |
|---|---|---|
| 1 | Operator semantics, grammars + limits, public/private boundaries, observation/request contracts, reference functions, rejection-rule kinds, intervention semantics, renderer strings, baseline definitions, decision register | **pending reviewer sign-off of this file (v0.2)** |
| 2 | All **(S)** ranges = the difficulty profile (§1.14) | after the construction screen, before fresh qualification data |

Any post-qualification change to generator, renderer, prompt, tool, parser,
or profile retires the affected qualification set (rev6 contract 8).
