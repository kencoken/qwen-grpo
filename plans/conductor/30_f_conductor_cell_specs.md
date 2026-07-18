# Conductor cell specifications — v0.1 (draft, awaiting reviewer sign-off)

First Stage-0A deliverable per [`plans/conductor/13_f_plan_rev6.md`](plans/conductor/13_f_plan_rev6.md)
("`conductor_cell_specs.md` is the first Stage-0A deliverable — linked, reviewed
before any generator code"). Concrete anatomy follows the reviewed examples in
[`plans/conductor/20_s_where_we_landed.md`](plans/conductor/20_s_where_we_landed.md)
and the adopted positions in
[`plans/conductor/21_f_where_we_landed_synthesis.md`](plans/conductor/21_f_where_we_landed_synthesis.md).

**Two-phase freeze** (per plan / rev5 critique):

1. **Phase 1 — on reviewer approval of this file**: operator semantics, artifact
   grammars, public/private field boundaries, reference functions, rejection-rule
   *kinds*, intervention semantics, renderer inventory.
2. **Phase 2 — after the 100-example construction screen, before fresh
   qualification data**: every numeric range marked **(S)** (screen-tunable)
   below.

Reward table, execution rules, action spaces, and the artifact *protocol*
(exactly one `<artifact>` tag, typed rejections vs. aborts, `WorkerResult`) are
normative in the plan's locked contracts 1–8 and are referenced, not restated.
Every worked example in §3 has been machine-verified (intermediates, gold
answers, rejection compliance, intervention targets — 69 checks); these examples
become the golden pytest fixtures of the 0A acceptance battery.

---

## 1. Global conventions

### 1.1 Integers and canonical wire form

- All public outputs are integers. Canonical decimal form:
  `0` or `-?[1-9][0-9]*`. Rejected wherever an integer is parsed from text
  (artifact literals; the deferred `<value>` control): `0012`, `+5`, `5.0`,
  `1,000`, internal whitespace.
- Terminal scoring compares executed integer values (the tool result is already
  an `int`); canonical-form rejection applies at text→integer boundaries only.
- All internal arithmetic is exact arbitrary-precision; fractions exist only
  transiently inside exact division and must resolve to integers.
- Terminal (gold) answers are ≥ 1 in every cell (0 excluded — avoids collisions
  with default/absent-value conventions). Intermediates may be 0 where noted.

### 1.2 Resource kinds and handles

Two private resource kinds (the `types.py` extension point):

- **`integer_record`** — ordered map *entity → (field → int)*. Entity and field
  names from the shared pools (§1.10). **All values in one record are pairwise
  distinct** (spec decision D3: makes wrong-cell retrievals scoreably wrong and
  guarantees corruption replacements move downstream values).
- **`integer_list`** — ordered list of integers. Two flavors: *dedup-flavor*
  (small band, duplicates required) and *select-flavor* (pairwise distinct).

**Handles**: `R-` + digit + uppercase letter + digit (e.g. `R-7K2`), sampled
uniformly, unique within an instance, independent of cell, payload, and split
(nuisance rule N1). The manifest is the list of instance handles in shuffled
order (N8).

**Worker-facing payload text** (the frozen public/private boundary rendering;
used when a payload is delivered in-context, §1.5):

```text
R-7K2:
Aster.crates = 31
Cedar.crates = 17
...
```

```text
R-9V4:
[41, 7, 83, 22, 65, 14, 39, 90, 56, 11, 72, 28]
```

All integers in canonical form; record lines in stored entity order.

### 1.3 Stored-instance schema

Per the synthesis — logically separated; **no presumed gold worker stored**
(assignments come from the measured payoff surface):

```json
{
  "cell_id": "lookup_math",
  "renderer_id": "goal_first",
  "public_prompt": "...",
  "public_manifest": ["R-3T5"],
  "private_registry": {
    "R-3T5": {"kind": "integer_record", "payload": {...}}
  },
  "reference_program": {
    "nodes": [
      {"id": "n1", "op": "lookup", "args": {"handle": "R-3T5", "key": "Cedar", "field": "units"}, "deps": []},
      {"id": "n2", "op": "affine", "args": {"p": 3, "sign": "-", "q": 4}, "deps": ["n1"]}
    ],
    "sink": "n2"
  },
  "gold_answer": 47,
  "generator_version": "specs-v0.1+codeversion",
  "seed": 18421
}
```

- `reference_program.nodes[*].op` ∈ {`lookup`, `affine`, `ratio`, `modular`,
  `product_affine`, `seq_count`, `seq_select`} (§2.1); `deps` are node ids;
  `sink` names the terminal node.
- Reference subtasks (§ per cell) and interventions (§1.7) are **derived
  deterministically** from `reference_program` + `seed`, not stored.
- Strip-test consequence (plan contract 5): the execution path never reads
  `reference_program` or `gold_answer`; only the scorer reads `gold_answer`.

### 1.4 Renderers

Three manually authored cosmetic renderers, fully crossed with every cell
(N3): `resource_first` (canonical/transparent), `goal_first`, `bound_var`.
Renderings of one latent program share payload, program, interventions, answer
— and count as **one statistical cluster** (paired cluster bootstrap).

Structural no-leakage property (from the synthesis): renderer template inputs
are *only* handles and public parameters — the renderer has no interface
through which to read private values.

Frozen rendering rules:

- All numerals as decimal digits, canonical form, in every renderer (D4 —
  deviation from the planning examples' occasional spelled-out numbers, for
  cross-cell consistency and nuisance control).
- Public formulas display as `` `(a × b − c) ÷ d` `` / `mod` (typography), while
  artifacts use ASCII `* - / %`.
- Indexing is always described as **zero-based**, explicitly.
- Shared connective vocabulary across all cells and directions: "resource",
  "the result", "step_1" (N5).

### 1.5 Endpoints, payload delivery, artifact grammars

Endpoints (framing locked in the plan): endpoint = frozen 1.5B model +
endpoint-specific tool + artifact grammar —

| Endpoint | Model | Tool | Grammar |
|---|---|---|---|
| Lookup | Qwen2.5-1.5B-Instruct | keyed retrieval against authorized payload | retrieval expression |
| Math | Qwen2.5-Math-1.5B-Instruct | exact integer calculator | arithmetic expression |
| Code | Qwen2.5-Coder-1.5B-Instruct | whitelist sequence interpreter | restricted sequence expression |

**Payload delivery (spec decision D1)**: the payload authorized for a step is
delivered **both** in-context to the worker (as §1.2 payload text) **and**
host-side to its tool for identifier resolution. Rationale: the primary causal
condition requires every candidate worker for a node to "receive the same local
payload"; and in-context delivery keeps the one-call whole-task baseline
informative — a strong endpoint may read and inline values, so the composition
advantage must be earned by construction-screen difficulty tuning, not by pure
grammar-gating.

Common lexical rules: whitespace permitted between tokens; artifact content is
trimmed; integer literals must be canonical (§1.1, else `E_NONCANONICAL_INT`).

**Math grammar**

```ebnf
expr   := term (("+" | "-") term)*
term   := factor (("*" | "/" | "%") factor)*
factor := INT | IDENT | "(" expr ")"
IDENT  := [a-z] | "step_" [1-9]
INT    := "0" | "-"? [1-9] [0-9]*
```

Semantics: exact integer arithmetic; `/` must divide exactly
(`E_INEXACT_DIV`), zero divisor `E_DIV_ZERO`; `%` is floor-mod (modulus is > 0
by construction). Single-letter identifiers bind to the fields of the step's
authorized `integer_record` (no authorized record, or unknown name →
`E_UNKNOWN_IDENT`); `step_k` binds per §1.6. No unary minus operator (negative
literals only).

**Lookup grammar**

```ebnf
lexpr := "lookup" "(" "resource" "," STR "," STR ")"
STR   := '"' [A-Za-z] [A-Za-z0-9]* '"'
```

`resource` is a fixed token bound by the host to the step's authorized payload
(none authorized → `E_NO_RESOURCE`). Key and field match exactly
(case-sensitive): `E_UNKNOWN_KEY` / `E_UNKNOWN_FIELD`.

**Code grammar**

```ebnf
int_expr := ("count_gt" | "at") "(" seq_expr "," int_arg ")"
seq_expr := "resource" | "stable_unique" "(" seq_expr ")"
          | "rotate_left" "(" seq_expr "," int_arg ")"
int_arg  := INT | "step_" [1-9]
```

The artifact's top level must be an `int_expr` (the `WorkerResult` value is an
`Integer`); nesting depth ≤ 8 (`E_DEPTH`). `resource` binds to the authorized
`integer_list` (`E_NO_RESOURCE` otherwise). `rotate_left(xs, k)`: `k ≥ 0`
required (`E_BAD_ARG`), rotates by `k mod len(xs)`. `at(xs, i)`: zero-based,
out of range → `E_INDEX_RANGE`. `count_gt(xs, t)`: strict `>`.

**Typed rejection codes** (all map to the plan's contract-4 "well-formed action
that fails in the world" path; unexpected interpreter exceptions propagate and
abort): `E_NO_ARTIFACT`, `E_MULTI_ARTIFACT`, `E_UNEXPECTED_TAG`, `E_PARSE`,
`E_NONCANONICAL_INT`, `E_UNKNOWN_IDENT`, `E_NO_RESOURCE`, `E_UNKNOWN_KEY`,
`E_UNKNOWN_FIELD`, `E_INDEX_RANGE`, `E_INEXACT_DIV`, `E_DIV_ZERO`,
`E_BAD_ARG`, `E_DEPTH`.

**Primitive semantics** (implemented twice, independently — `tools.py`
interpreter and `program.py` reference functions; the 10k reference-vs-tools
agreement command compares them):

- `stable_unique(xs)` — keep first occurrences, preserve order.
- `rotate_left(xs, k)` — `xs[k mod n :] + xs[: k mod n]`.
- `at(xs, i)` — zero-based selection.
- `count_gt(xs, t)` — `|{x ∈ xs : x > t}|`.
- `lookup(rec, key, field)` — keyed retrieval.
- affine / ratio / modular — exact integer arithmetic per §2.1.

### 1.6 Predecessor variables and access patterns

Steps are numbered 1…S by position in the workflow JSON. Identifier `step_k`
resolves to the executed value of step *k* iff the current step's access is
`all` and `k <` current step index; otherwise `E_UNKNOWN_IDENT`. Legal v0
access patterns (plan contract 2): `[none]` atomic; `[none, all]` two-step;
`[none, none, all]` fork/join.

### 1.7 Intervention semantics (global)

Both kinds, per dependency edge *(u → v)* of the reference topology, executed
on the deployable-oracle assignment at calibration time:

- **Mechanics**: after step *u* executes, the executor substitutes its recorded
  value with replacement *r* before step *v* binds identifiers; everything else
  (disclosure, access, prompts) is unchanged.
- **Corruption**: score against the stored `gold_answer`. Expectation:
  accuracy falls (gate thresholds in the plan's CE1 table).
- **Counterfactual consistency**: same substitution; score against
  `gold' =` reference sink recomputed with the override. Expectation: execution
  follows to the *new* answer.
- *r* is sampled deterministically from `seed ⊕ edge_id` under the per-cell
  replacement rule (§3), which must provably change the sink; each cell's rule
  guarantees this by construction.
- Atomic cells have no dependency edges: interventions are N/A there
  (metamorphic and distractor-invariance tests cover them instead).
- Missing/skip variants are reported but prove only tool input-validation
  (plan contract 7).

### 1.8 Per-cell baselines: prompts and payloads

Per plan contract 6, each cell defines three direct baselines (echo worker,
no-op worker, and answer-in-subtask telemetry are harness-global):

1. **Public-prompt-only** (leakage check): the instance's `public_prompt`
   verbatim to each endpoint, **no payload authorized**. Expected ≈ 0 by the
   rejection rules; any material success is investigated as leakage.
2. **Local capability**: the 3B base model given one node's payload text +
   that node's rendered reference subtask, asked for the node value.
3. **Best one-call whole-task**: the instance's `public_prompt` verbatim to a
   single endpoint with the **union of all instance payloads** authorized
   (in-context + host-side). The union payload is a **harness-only exception**
   to the one-resource-per-step rule and is never available to the policy.
   "Best" = max over the three endpoints. This is the only baseline that speaks
   to hierarchy's value.

### 1.9 Nuisance controls

Checked by the nuisance-only classifier at the construction screen (renderer,
domain, length, resource count, numeric formatting as features; must not
predict cell):

- **N1** one handle format everywhere (§1.2).
- **N2** integer outputs in every cell.
- **N3** renderer × cell fully crossed.
- **N4** one shared entity pool and one shared field pool for every
  record-bearing cell, balanced across cells and splits.
- **N5** identical connective vocabulary across cells and directions.
- **N6** numerals as digits everywhere.
- **N7** prompt-length and answer-range bands recorded per cell at the screen
  and matched **where practical** — divergence driven by tool demand
  (e.g. `math_atomic`'s large answers) is inherent and acknowledged.
- **N8** manifest order shuffled; fork/join branch order balanced (§3.6).

Legitimate semantic cues ("retrieve a field", "multiply", "zero-based index",
"remove duplicates") are the intended routing signal and stay.

### 1.10 Name pools

Shared by all record-bearing cells (N4); sampled without replacement within a
record.

- **Entities (20)**: Aster, Birch, Cedar, Elm, Fern, Grove, Hazel, Ivory,
  Juniper, Lark, Maple, Nettle, Onyx, Pine, Quill, Rowan, Slate, Tarn, Vale,
  Wren.
- **Fields (10)**: crates, units, tokens, points, seats, kits, spools, tiles,
  flasks, reams.
- **Hidden-Math operand names**: single lowercase letters `a, b, c, d` in
  order; the modulus operand is always named `m` (D9).

---

## 2. Shared generator machinery

### 2.1 Primitive ops and reference functions

`program.py` implements per-primitive direct reference functions with exact
integer arithmetic:

```python
def prim_lookup(rec, key, field) -> int          # keyed retrieval
def prim_affine(x, p, sign, q) -> int            # p*x + q  or  p*x - q
def prim_ratio(a, b, c, d) -> int                # (a*b - c) / d, exact else raise
def prim_modular(a, b, c, m) -> int              # (a*b + c) % m, m > 0
def prim_product_affine(x, y, q) -> int          # x*y + q
def prim_seq_count(xs, k, t) -> int              # count_gt(rotate_left(stable_unique(xs), k), t)
def prim_seq_select(xs, k, i) -> int             # at(rotate_left(stable_unique(xs), k), i)
```

A cell's direct reference function composes these over the instance registry
and public parameters; it is the source of `gold_answer` and of counterfactual
recomputation, and one side of the 10k agreement command.

### 2.2 Shared samplers

- `integer_record(N, F, band)` — N entities × F fields from the pools, values
  pairwise distinct within `band`.
- `integer_list_dedup(L, band=[1,9])` — must satisfy
  `len(stable_unique(xs)) ≤ L − 2` (at least two removals, so deduplication is
  consequential).
- `integer_list_select(L, band=[1,99])` — pairwise distinct values.

### 2.3 Rejection sampling

Rejection rules are per-cell (§3). The generator resamples the whole instance
until all rules pass; after 1000 attempts it raises (a generator error, never a
silent band change). All sampling flows from the instance `seed`
(reproducible); rejection rules are asserted again at load time.

---

## 3. Cell specifications

Conventions for this section: **O** = ordinary worked example, **B** = boundary
worked example; every example lists its rejection-rule check; "example
artifacts" illustrate the grammar — any grammar-valid artifact whose executed
value is correct scores (e.g. a Math worker may inline literals it read from
its in-context payload). Node ops imply a natural endpoint family, but **no
gold worker is presumed anywhere** — assignments come from the measured payoff
surface. Reference subtasks are **tool-neutral**: they describe the semantic
operation and never name a worker, tool, or endpoint-specific syntax.

### 3.1 `lookup_atomic` — atomic Lookup

**Shape**: 1 step, access `[none]`, 1 resource (`integer_record`).

**Private schema / parameters**

| Parameter | Range | Notes |
|---|---|---|
| entities N | 3–16 **(S)** | `N × F ≤ 60` |
| fields F | 1–5 **(S)** | |
| value band | 10–99 **(S)** | pairwise distinct |
| target (key, field) | uniform over record | |

**Rejection rules**: pairwise-distinct values (generator-enforced, §1.2);
otherwise none — difficulty lives in N, F, and distractor count.

**Public prompt (renderer templates)**

- `resource_first`: "Resource {H} contains keyed integer records. Return the
  {field} value recorded for {key}."
- `goal_first`: "Return the {field} value that {H} records for {key}."
- `bound_var`: "Let v be {key}'s {field} in {H}. Output v."

**Reference program**: `n1 = lookup(H, key, field)`; sink `n1`.

**Reference subtask** (tool-neutral): "Retrieve {key}'s {field} value from the
requested resource."

**Example artifact**: `<artifact>lookup(resource, "Grove", "crates")</artifact>`

**O** — `R-7K2`: Aster.crates = 31, Cedar.crates = 17, Grove.crates = 39,
Ivory.crates = 53; target Grove.crates. Gold: **39**. (Distinct values ✓.)

**B** — minimum size, band edges. `R-4H8`: Lark.units = 99, Onyx.units = 10,
Pine.units = 11, Quill.units = 98; target Quill.units. Gold: **98**.
(N = 4, F = 1; values at/near band edges; distinct ✓.)

**Interventions**: none (atomic). Metamorphic/distractor-invariance:
resampling non-target entities and values leaves the gold unchanged.

**One-call baseline**: `public_prompt` verbatim; union payload = the record
(identical to the cell's own single payload for atomic cells).

### 3.2 `math_atomic` — atomic Math (hidden operands, public formula)

**Shape**: 1 step, access `[none]`, 1 resource (`integer_record` of operands).
Operands are private; the formula is public (hidden-Math principle). Operand
sizes create tool demand — tuned within the cell at the screen.

**Formula templates** (sampled uniformly; frozen at phase 1):

| Template | Public formula | Operands |
|---|---|---|
| T1 ratio | `(a × b − c) ÷ d` | a, b, c, d |
| T2 modular | `(a × b + c) mod m` | a, b, c, m |
| T3 affine | `a × b + c` | a, b, c |

**Parameters**

| Parameter | Range | Notes |
|---|---|---|
| a | 10⁴–10⁶ **(S)** | large: mental arithmetic fails, calculator exact |
| b | 10–99 **(S)** | |
| c | 1–20 **(S)** | |
| d (T1) | 2–12 **(S)** | |
| m (T2) | 5–60 **(S)** | |

**Rejection rules**: T1 division exact (else resample — never rounded);
answer ∈ [1, 10⁹]; T2 answer ∈ [1, m−1] (0 rejected); **answer ∉ operand
values** (echoing an operand can never score 1.0); non-triviality is
band-enforced (b ≥ 10, c ≥ 1, d ≥ 2).

**Public prompt (renderer templates)** — `{names}` = comma-list of operand
names:

- `resource_first`: "{H} contains integers {names}. Evaluate `{formula}`
  exactly."
- `goal_first`: "Return the exact value of `{formula}`, where {names} are the
  integers recorded in {H}."
- `bound_var`: "Let {names} be the integers in {H}. Output `{formula}`."

**Reference program**: `n1 = ratio|modular|affine(a, b, c[, d|m])`; sink `n1`.

**Reference subtask**: "Evaluate `{formula}` exactly using the integers in the
requested resource."

**Example artifact**: `<artifact>(a * b - c) / d</artifact>`

**O (T1)** — `R-2P6`: a = 83719, b = 43, c = 1, d = 6.
`83719 × 43 = 3599917`; `− 1 = 3599916`; `÷ 6 =` **599986**.
(Exact ✓; ∈ [1, 10⁹] ✓; ∉ {83719, 43, 1, 6} ✓.)

**O (T2)** — `R-7Q4`: a = 999983, b = 97, c = 19, m = 12.
`999983 × 97 + 19 = 96998370`; `mod 12 =` **6**. (∈ [1, 11] ✓.)

**O (T3)** — `R-1X5`: a = 524287, b = 83, c = 17.
`524287 × 83 + 17 =` **43515838**. (∈ [1, 10⁹] ✓; ∉ operands ✓.)

**B (T1, low edges)** — `R-8B2`: a = 10007, b = 10, c = 2, d = 6.
`(100070 − 2) ÷ 6 = 100068 ÷ 6 =` **16678**. (Exact ✓; ∉ operands ✓.)

**Interventions**: none (atomic).

**One-call baseline**: `public_prompt` verbatim; union payload = the operand
record.

### 3.3 `code_atomic` — atomic Code (one call, nested composition)

**Shape**: 1 step, access `[none]`, 1 resource (dedup-flavor `integer_list`).
One worker *call*, several primitives nested in a single artifact (locked
principle: an atomic cell is one call, not one primitive).

**Pipeline shapes** (sampled 50/50 **(S)**; D2):

| Shape | Latent pipeline | Public integer |
|---|---|---|
| count | `count_gt(rotate_left(stable_unique(xs), k), t)` | count |
| select | `at(rotate_left(stable_unique(xs), k), i)` | selected value |

Known property, acknowledged: in the **count** shape the rotation is
answer-invariant (`count_gt` doesn't depend on order). It is retained from the
reviewed example as workload for the worker and exploited as a metamorphic
test (vary k → answer must not change). The **select** shape makes rotation
answer-relevant (rejection rule below), so rotation competence is exercised
with stakes in half the instances.

**Parameters**

| Parameter | Range | Notes |
|---|---|---|
| L | 8–16 **(S)** | dedup-flavor, values 1–9 **(S)** |
| U = len(stable_unique) | ≤ L − 2 | ≥ 2 removals (sampler-enforced) |
| k | 1–9 **(S)** | `k mod U ≠ 0` |
| t (count) | 1–8 **(S)** | |
| i (select) | 0…U−1 | |

**Rejection rules**: duplicates consequential (`U ≤ L − 2`); rotation
non-trivial (`k mod U ≠ 0`); **count**: `1 ≤ answer ≤ U − 1` (degenerate
zero/full counts rejected); **select**: `i` valid and
`rotated[i] ≠ deduped[i]` (rotation must change the selected value).

**Public prompt (renderer templates)** — count shape shown; select shape
replaces the final clause with "and return the value at zero-based index {i}":

- `resource_first`: "From the integer sequence in {H}, remove later
  occurrences of repeated values, rotate the remaining sequence left by {k}
  positions, and count the values greater than {t}."
- `goal_first`: "Return how many values exceed {t} in the sequence obtained
  from {H} by removing later occurrences of repeated values and rotating it
  left by {k} positions."
- `bound_var`: "Let s be the sequence in {H} after removing later occurrences
  of repeated values and rotating left by {k} positions. Output the count of
  values in s greater than {t}."

**Reference program**: `n1 = seq_count(xs, k, t)` or `seq_select(xs, k, i)`;
sink `n1`.

**Reference subtasks**: count — "Remove later occurrences of repeated values
from the integer sequence in the requested resource, rotate the remaining
sequence left by {k} positions, and count the values greater than {t}.";
select — same head, "…and return the value at zero-based index {i}."

**Example artifact**:
`<artifact>count_gt(rotate_left(stable_unique(resource), 3), 5)</artifact>`

**O (count)** — `R-8C3`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]`, k = 3, t = 5.
`stable_unique → [6, 1, 9, 4, 8, 3, 2, 7]` (U = 8);
`rotate_left(3) → [4, 8, 3, 2, 7, 6, 1, 9]`; `count_gt(5) =` **4**.
(U = 8 ≤ 10 ✓; 3 mod 8 ≠ 0 ✓; 1 ≤ 4 ≤ 7 ✓.)

**O (select)** — `R-5N1`: `[5, 3, 5, 8, 1, 3, 9, 2]`, k = 2, i = 4.
`stable_unique → [5, 3, 8, 1, 9, 2]` (U = 6);
`rotate_left(2) → [8, 1, 9, 2, 5, 3]`; `at(4) =` **5**.
(U = 6 ≤ 6 ✓; 2 mod 6 ≠ 0 ✓; rotated[4] = 5 ≠ deduped[4] = 9 ✓.)

**B (count, answer = U − 1)** — `R-9E3`: `[9, 8, 9, 7, 6, 8, 5, 9]`, k = 2,
t = 5. `stable_unique → [9, 8, 7, 6, 5]` (U = 5);
`rotate_left(2) → [7, 6, 5, 9, 8]`; `count_gt(5) =` **4** = U − 1.
(U = 5 ≤ 6 ✓; 2 mod 5 ≠ 0 ✓; boundary of the nondegeneracy band.)

**Interventions**: none (atomic). Metamorphic: count shape invariant under
k → k + U; both shapes invariant under `stable_unique` idempotence.

**One-call baseline**: `public_prompt` verbatim; union payload = the list.

### 3.4 `lookup_math` — Lookup → Math

**Shape**: 2 steps, access `[none, all]`; 1 resource (`integer_record`),
requested by step 1; step 2 requests none and consumes `step_1`.

**Parameters**

| Parameter | Range | Notes |
|---|---|---|
| record N, F, band | as §3.1 | target value = n1 ∈ [10, 99] |
| p | 2–9 **(S)** | public coefficient |
| q | 1–20 **(S)** | public offset |
| sign | {+, −} 50/50 | |

**Rejection rules**: answer ≥ 1; **answer ∉ record values**; **answer ≠ n1**
(reachable, e.g. p = 2, q = n1 with minus — rejected so echoing the lookup
never scores); non-triviality band-enforced (p ≥ 2, q ≥ 1).

**Public prompt (renderer templates)** — minus form shown:

- `resource_first`: "Retrieve {key}'s {field} from {H}. Return {p} times that
  value minus {q}."
- `goal_first`: "Return the number obtained by subtracting {q} from {p} times
  {key}'s {field} recorded in {H}."
- `bound_var`: "Let x be {key}'s {field} in {H}. Output `{p}x − {q}`."

**Reference program**: `n1 = lookup(H, key, field)`;
`n2 = affine(n1, p, sign, q)`; sink `n2`.

**Reference subtasks**: 1. "Retrieve {key}'s {field} value from the requested
resource." 2. "Multiply step_1 by {p}, then subtract {q}." (or "…then add
{q}").

**Example artifacts**:
step 1 `<artifact>lookup(resource, "Cedar", "units")</artifact>`;
step 2 `<artifact>3 * step_1 - 4</artifact>`.

**O** — `R-3T5`: Aster.units = 31, Cedar.units = 17, Grove.units = 39,
Ivory.units = 53; target Cedar.units; p = 3, minus, q = 4.
`n1 = 17`; `n2 = 3 × 17 − 4 =` **47**.
(47 ∉ {31, 17, 39, 53} ✓; 47 ≠ 17 ✓.)

**B (band edges)** — `R-2W9`: Vale.units = 99, Aster.units = 10,
Hazel.units = 23, Tarn.units = 57; target Vale.units; p = 9, minus, q = 20.
`n2 = 9 × 99 − 20 =` **871**. (871 ∉ record ✓; ≠ 99 ✓.)

**Interventions** (edge n1 → n2): replacement `n1' ~ U([10, 99] \ {n1})`,
resampled until `gold' = affine(n1') ≥ 1` (sink change is automatic: affine
with p ≥ 2 is injective).
Example (O): `n1' = 19` → corruption keeps target 47 (execution now yields 53
→ scored wrong); counterfactual recomputes target `3 × 19 − 4 = 53`.

**One-call baseline**: `public_prompt` verbatim; union payload = the record.
Note: with in-context delivery (D1) a one-call Math endpoint may read the
record and inline the value — the screen must tune record size/distractors
until the deployable oracle clears the +20-point gate.

### 3.5 `math_code` — Math → Code (computed index)

**Shape**: 2 steps, access `[none, all]`; 2 resources — step 1 requests the
operand record, step 2 requests the list and consumes `step_1` (≤ 1 resource
per step holds).

**Parameters**

| Parameter | Range | Notes |
|---|---|---|
| a | 10⁸–10⁹ **(S)** | larger than §3.2: index must be uncomputable mentally |
| b | 10–99 **(S)** | |
| c | 1–20 **(S)** | |
| m = L | 8–16 **(S)** | modulus equals list length (D6) → index always valid |
| list | select-flavor, values 1–99 **(S)** | pairwise distinct |

**Rejection rules**: list pairwise distinct (⇒ every counterfactual index
changes the answer — the plan's "answer-preserving counterfactual indices"
rejection is discharged structurally); **answer ≠ n1** (index echo never
scores); **answer ∉ {a, b, c, m}**; `n1 ∈ [0, m−1]` holds by construction
(intermediate 0 permitted; terminal answer ≥ 1 by the list band).

**Public prompt (renderer templates)**:

- `resource_first`: "{H1} contains integers a, b, c and m. Compute
  `(a × b + c) mod m`. Use the result as a zero-based index into the sequence
  in {H2} and return the selected integer."
- `goal_first`: "Return the integer found in {H2} at the zero-based index
  given by `(a × b + c) mod m`, where a, b, c and m are the integers in {H1}."
- `bound_var`: "Let i = `(a × b + c) mod m`, with a, b, c and m taken from
  {H1}. Output the value of the sequence in {H2} at zero-based index i."

**Reference program**: `n1 = modular(a, b, c, m)`;
`n2 = seq_select_by_step(list, step_1)` (i.e. `at(list, n1)`, no dedup/rotate);
sink `n2`.

**Reference subtasks**: 1. "Evaluate `(a × b + c) mod m` exactly using the
integers in the requested resource." 2. "Return the value at zero-based index
step_1 in the integer sequence from the requested resource."

**Example artifacts**: step 1 `<artifact>(a * b + c) % m</artifact>`;
step 2 `<artifact>at(resource, step_1)</artifact>`.

**O** — `R-6D1`: a = 982451653, b = 37, c = 7, m = 12;
`R-9V4`: `[41, 7, 83, 22, 65, 14, 39, 90, 56, 11, 72, 28]`.
`n1 = (982451653 × 37 + 7) mod 12 = 8`; `n2 = list[8] =` **56**.
(Distinct ✓; 56 ≠ 8 ✓; 56 ∉ {a, b, c, m} ✓.)

**B (index = m − 1)** — `R-3F7`: a = 100000037, b = 41, c = 2, m = 8;
`R-6M2`: `[17, 64, 80, 23, 46, 91, 12, 58]`.
`n1 = (100000037 × 41 + 2) mod 8 = 7`; `n2 = list[7] =` **58**.
(Distinct ✓; 58 ≠ 7 ✓; 58 ∉ operands ✓.)

**Interventions** (edge n1 → n2): replacement `i' ~ U([0, m−1] \ {n1})` —
always a valid index; sink change guaranteed by distinctness.
Example (O): `i' = 3` → corruption keeps target 56 (execution yields
`list[3] = 22` → scored wrong); counterfactual recomputes target **22**.

**One-call baseline**: `public_prompt` verbatim; union payload = record +
list (harness-only exception). Composition advantage is driven by a's size: a
one-call Code endpoint must compute `(a × b + c) mod m` without a calculator;
a one-call Math endpoint has no selection operator, so it must read the list
in-context and index it mentally after computing n1.

### 3.6 `fork_join` — Lookup + Code → Math (diagnostic)

**Shape**: 3 steps, access `[none, none, all]`; 2 resources — the two branch
steps each request one; the join step requests none and consumes `step_1` and
`step_2`. **Diagnostic-only in v0**: not in the training mixture (admission
gates deferred); qualification slice 100–200 programs if paired CIs are
decisive. First topology beyond a linear chain; Stage-2 use tests endpoint
selection *within a fixed parallel DAG* (topology construction is Stage 4).

**Branch order**: which branch is step 1 is sampled 50/50 (N8); the join
formula is symmetric so numbering is immaterial.

**Parameters**

| Parameter | Range | Notes |
|---|---|---|
| record N, F, band | as §3.1 | branch value n_lk ∈ [10, 99] |
| code branch | count shape of §3.3 | n_code ∈ [1, U−1] |
| q | 1–20 **(S)** | public join offset |

Join skeleton (frozen, D8): `step_1 × step_2 + q`.

**Rejection rules**: branch rules of §3.1 and §3.3 (count shape) apply;
**answer ∉ {n_lk, n_code} ∪ record values ∪ list values**. Corruption of
either branch provably moves the sink: `n_code ≥ 1` and `n_lk ≥ 10` make the
product strictly monotone in each argument.

**Public prompt (renderer templates)**:

- `resource_first`: "Retrieve {key}'s {field} from {H1}. Separately, remove
  later occurrences of repeated values from the integer sequence in {H2},
  rotate it left by {k} positions, and count the values greater than {t}.
  Return the product of the two results plus {q}."
- `goal_first`: "Return {q} plus the product of two values: {key}'s {field}
  recorded in {H1}, and the count of values greater than {t} after removing
  later occurrences of repeated values from the sequence in {H2} and rotating
  it left by {k} positions."
- `bound_var`: "Let x be {key}'s {field} in {H1}. Let y be the count of values
  greater than {t} in the sequence from {H2} after removing later occurrences
  of repeated values and rotating left by {k} positions. Output `x × y + {q}`."

**Reference program**: `n1 = lookup(H1, key, field)`;
`n2 = seq_count(list, k, t)`; `n3 = product_affine(n1, n2, q)`; sink `n3`;
deps(n3) = [n1, n2].

**Reference subtasks**: 1. "Retrieve {key}'s {field} value from the requested
resource." 2. count subtask of §3.3. 3. "Multiply step_1 by step_2, then add
{q}."

**Example artifacts**: branches as §3.1/§3.3;
join `<artifact>step_1 * step_2 + 3</artifact>`.

**O** — `R-5A8`: Aster.units = 31, Cedar.units = 14, Grove.units = 39 (target
Cedar); `R-1J7`: `[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]`, k = 3, t = 5; q = 3.
`n1 = 14`; `n2 = 4` (as §3.3 O); `n3 = 14 × 4 + 3 =` **59**.
(59 ∉ {14, 4} ∪ record ∪ list ✓.)
Branch counterfactuals: `14 → 15` gives `15 × 4 + 3 = 63`;
`4 → 3` gives `14 × 3 + 3 = 45`.

**B (minimum code count)** — `R-8D4`: Wren.crates = 99, Slate.crates = 10,
Fern.crates = 57 (target Wren); `R-2K9`: `[4, 2, 4, 3, 1, 2, 3, 4]`, k = 1,
t = 3; q = 20.
`n1 = 99`; `stable_unique → [4, 2, 3, 1]` (U = 4 ≤ 6 ✓; 1 mod 4 ≠ 0 ✓);
`rotate_left(1) → [2, 3, 1, 4]`; `n2 = count_gt(3) = 1` (= U − 3 lower bound
✓); `n3 = 99 × 1 + 20 =` **119**. (119 ∉ values ✓.)
Branch counterfactuals: `99 → 98` → 118; `1 → 2` → 218.

**Interventions** (two edges: n1 → n3, n2 → n3, each with both kinds — the
fork gate requires per-branch corruption drops ≥ 20 points, paired lower CI):
replacements `n1' ~ U([10, 99] \ {n1})`, `n2' ~ U([1, U−1] \ {n2})`; sink
change automatic (strict monotonicity above); counterfactual recomputes
`gold' = n1' × n2 + q` (resp. `n1 × n2' + q`).

**One-call baseline**: `public_prompt` verbatim; union payload = record +
list. The fork gate additionally compares against the **best two-call
shortcut** (plan CE1 table: oracle ≥ +15 vs best two-call).

---

## 4. Acceptance hooks (what the 0A battery consumes from this file)

- **Golden fixtures**: every §3 worked example (O and B) becomes a pytest
  fixture asserting intermediates, gold answer, rejection compliance, and
  intervention targets (the numbers above are machine-verified).
- **Metamorphic tests**: count-shape rotation invariance (k → k + U);
  `stable_unique` idempotence; distractor invariance (resampling non-target
  record entries / renaming entities leaves gold unchanged); handle-renaming
  invariance; renderer invariance (three renderers of one program share gold
  and interventions).
- **Provenance-based no-leakage**: every private value is tagged at
  generation; assert no private-value provenance reaches renderer inputs
  (structural, §1.4) and that `public_prompt` string-contains no private value
  except by proven coincidence with a public parameter (provenance, not string
  match, decides).
- **Strip test / bijection test**: plan-level (contract 5 / contract 1);
  this file contributes the instances.
- **10k agreement command**: reference functions (§2.1) vs tool interpreter
  (§1.5) on 10k sampled artifacts — recorded acceptance command, not pytest.

## 5. Decisions taken in this spec (flagged for reviewer sign-off)

| # | Decision | Rationale |
|---|---|---|
| D1 | Payloads delivered in-context to the authorized worker **and** host-side to its tool | "Every candidate worker receives the same local payload" (primary causal condition); keeps the one-call baseline informative rather than trivially grammar-gated |
| D2 | `code_atomic` gets a second (select) pipeline shape; count-shape rotation-invariance acknowledged and used as a metamorphic test | In the reviewed count-only example, rotation can never affect the answer; the select shape gives rotation stakes without new operators |
| D3 | All values within a record pairwise distinct | Wrong-entity retrievals are scoreably wrong; corruption replacements always move the sink |
| D4 | Numerals rendered as digits everywhere (planning examples sometimes spelled numbers out) | Cross-cell consistency; one fewer nuisance dimension |
| D5 | Terminal answers ≥ 1 in every cell; `math_atomic` answers additionally ∉ operands; `lookup_math` answers ∉ record ∪ {n1}; `math_code` answers ∉ {index, operands}; `fork_join` answers ∉ branch/payload values | Echo/coincidence answers can never score 1.0 |
| D6 | `math_code`: modulus m = list length L | Index validity by construction; the plan's invalid-index rejection becomes a generator assert |
| D7 | Fixed name pools (20 entities, 10 fields) shared across all record-bearing cells | Nuisance control N4 |
| D8 | Single fork/join skeleton `step_1 × step_2 + q` | Matches the reviewed example; symmetric under branch reordering |
| D9 | Operand naming fixed: `a, b, c, d` in order; modulus always `m` | Stable identifier grammar; no name/cell correlation |

## 6. Freeze record

| Phase | Scope | Status |
|---|---|---|
| 1 | Operator semantics, artifact grammars, public/private boundaries, reference functions, rejection-rule kinds, intervention semantics, renderers | **pending reviewer sign-off of this file** |
| 2 | All ranges marked **(S)** | after the 100-example construction screen, before fresh qualification data |

Any post-qualification change to generator, renderer, prompt, tool, parser, or
profile retires the affected qualification set (plan contract 8).
