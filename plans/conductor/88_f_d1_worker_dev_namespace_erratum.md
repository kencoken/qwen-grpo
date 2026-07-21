# D1 erratum — dedicated worker-development namespace `worker_dev`

**Status:** proposed for review as a single unit — at Ken's direction
the erratum and its §4 implementation land in one commit (§6 records
the diff); no run uses the namespace before this document's sign-off.
This is the narrow erratum called for by plan `81_f` §4.6/D1 and
required as a Tranche-D precondition (§8); it discharges the binding
obligation recorded in `86_s`/`87_f`.

**Amends:** the §1.13 predeclared namespace table (root
`conductor_cell_specs.md`, frozen at v0.8). On ratification this
document is the normative record; consolidation into the root
specification is deferred to the next spec revision, alongside the
pending §1.6 Math-endpoint erratum, so the frozen root is amended once,
not piecemeal.

## 1. Motivation

D16 adaptively inspected `construction` indices 0–29 per cell across
nine prompt revisions. Those examples are useful development evidence
but are no longer a fresh post-freeze screen, and `78_s`/`81_f` §4.6
require that this adaptation not be silently laundered into the existing
`dev`, `test`, `train` or `qualification` namespaces — nor quietly back
into `construction`. The worker evaluator and the P0/P1 probes now
merged into the D16 branch need a declared population whose adaptive use
is *explicit and bounded* rather than accidental.

## 2. Normative content

Add one namespace to the §1.13 predeclared table:

```python
# types.NAMESPACES += ("worker_dev",)
# program.NAMESPACE_CONFIG:
"worker_dev": {"max_latent_clusters": 30, "expansion_batch": 30,
               "stopping_rule": "fixed"},
```

- **Cap 30 per cell, every cell including `fork_join`** (no special
  fork entry): exactly the `81_f` §4.6 full-pass universe — 180 latent
  programs, 540 rendered observations, 900 isolated node calls per
  semantic-endpoint pass.
- **Deterministic order:** the standard predeclared-prefix rule,
  indices 0–29; the P1 admissibility sample is the prefix 0–9 per cell
  (300 node cases), a strict subset of the same universe.
- **Seed identity:** automatic and requires no further mechanism — the
  namespace string enters `seed_material(GENERATOR_VERSION, dp_version,
  namespace, cell, index, …)`, so `worker_dev` is a disjoint sampling
  universe by construction, and no existing `(namespace, index) →
  latent` mapping changes by a single byte.
- **Stopping rule = the cap.** Exhausting 30 per cell without a
  decision requires a further erratum; the namespace is deliberately
  too small to sustain unbounded prompt wordsmithing, which `78_s`
  found uninformative.

**Generator version:** `GENERATOR_CODE_VERSION` is *not* bumped.
Rationale: the bump contract exists to retire qualification sets when
generation behavior changes; adding a new namespace leaves every
existing namespace's outputs byte-identical (verified by the golden
byte fixtures and determinism tests, which do not touch `worker_dev`).
The reviewer may override this judgment; if bumped, no qualification
sets exist yet, so the cost is nil.

## 3. Usage contract

1. **Purpose:** D16 worker evaluation only — isolated node runs,
   composed diagnostics, P0/P1 probes, candidate comparisons and §7.4
   confirmations. Private visibility, all three renderers, on-contract
   operator-aligned scheduling.
2. **Adaptive inspection is permitted and expected.** That is the
   namespace's reason to exist. In exchange, `worker_dev` is
   **permanently barred** from the construction screen, qualification,
   and any train/dev/test estimate. No result computed on it can feed a
   Stage-1 gate (consistent with §5.6's gate-scope rule).
3. **Authoritative binding (86_s obligation):** on ratification,
   `worker_dev` becomes the default `--namespace` for the probe `admit`
   and `confirm` commands. Explicit overrides remain possible at the
   function level for CPU tests and diagnostics, but a Gate-D verdict is
   valid only against this namespace.
4. **D4 is not resolved here.** The consumed `construction` prefix 0–29
   remains consumed; how the formal 100-per-cell construction screen
   accounts for it is a separate decision that must be closed before
   Stage 1, and this erratum neither uses nor launders those indices.

## 4. Implementation checklist (landed in this commit at Ken's
direction; §6 records the diff)

1. `types.py`: `NAMESPACES` gains `"worker_dev"`.
2. `program.py`: the `NAMESPACE_CONFIG` entry above.
3. `worker_eval_probe.py`: `admit`/`confirm` CLI `--namespace` defaults
   to `worker_dev` (still recorded in every verdict).
4. Tests: cap enforcement at 30 (index 30 refused); disjointness (same
   cell/index in `worker_dev` vs `construction` yields different latent
   program ids and registries); determinism (regeneration is
   byte-identical); existing-namespace outputs unchanged (existing
   golden fixtures already pin this); CLI defaults.
5. Generate and record the population manifest for the first candidate
   runs (180 latents, 540 observations, 900 cases) in the D16 log.

## 5. Acceptance

The erratum is discharged when the checklist lands with tests green and
the first P1 run against `worker_dev` passes its coverage assertion
(every cell, node family, and declared generator factor level present in
the 10-per-cell prefix — the factorial scheduler should guarantee this;
if it does not, that is a finding about the schedule, not a reason to
resample).

**Pre-registration check (2026-07-21, before approval, no generator
change committed):** simulating exactly the §2 entry in-process, the
`worker_dev` 10-per-cell prefix passes `assert_probe_coverage` (cells,
node families, all declared factor levels), the 30-per-cell universe
passes likewise, and `math_code:19` yields a different latent program id
and private registry than its `construction` counterpart — the seed
identity separates the universes as claimed. The acceptance criterion is
therefore expected to hold mechanically once the checklist lands.

## 6. Implementation record (same commit)

Deliberately small — the document is heavier than the diff because the
namespace table is frozen §1.13 surface:

- `types.py`: `NAMESPACES` gains `"worker_dev"` (checklist 1).
- `program.py`: the §2 `NAMESPACE_CONFIG` entry, verbatim (checklist 2).
- `worker_eval_probe.py`: `admit`/`confirm` `--namespace` now defaults
  to `worker_dev` (checklist 3; the 86_s obligation discharged — a
  green verdict against any other namespace requires an explicit
  override and is diagnostics, not Gate D). The `confirm_repeat_run`
  docstring notes the binding.
- Tests (checklist 4, three tests): cap refusal at index 30 and
  namespace-cap 30 for every cell including `fork_join`; disjointness
  from `construction` (different latent program id and registry at the
  same cell/index) and byte-identical regeneration; the 10-per-cell P1
  prefix clears `assert_probe_coverage`; the admit CLI without
  `--namespace` holds runs to `worker_dev`. Existing golden fixtures
  already pin that no prior namespace's outputs moved. Full suite: 551.
- Checklist 5 (the recorded population manifest) is deferred to the
  first candidate run's D16 log entry, where it belongs.

## 7. What this unlocks — the remainder of Tranche D

Tranche D is the GPU-evidence phase of the worker-eval integrity plan
(`81_f` §8): everything before it built and reviewed the measurement
instrument on CPU; Tranche D establishes that the *generation policy the
instrument assumes* is real on the actual hardware, preserves the
batching regression that motivated it, and only then lets the corrected
instrument re-measure the D16 candidates. Gate D has exactly two
outcomes: `singleton-v1` admitted with retained evidence, or work stops
with the §7.4 follow-up decision plan — no fallback to the dynamic
cache, no quietly selected draw.

In order:

1. **P0 cohort construction from the retained rev9 traces** (no
   dependency on this erratum — `construction`-namespace cases by
   definition, startable immediately): the batch-sensitive rev9 Code
   requests and the per-cell-15/30 Math request, as case references
   with pinned request hashes and the exact recorded physical chunks
   (the 16/16/13 split), so the replay reconstructs the real
   `model.generate` batches or refuses.
2. **P0 replay on `picome`**: original grouping twice, reversed
   within-chunk order, singleton — cache-disabled, compared with the
   header-validating comparator. Differences across conditions are the
   retained regression evidence (78_s finding 6), pinned against any
   future backend change.
3. **P1 singleton admissibility on `worker_dev`**: per candidate
   configuration, three fresh-process 300-case passes (canonical,
   canonical, reversed) under default backend flags; `admit` requires
   exact generation-field equality and the frozen cost gate (≤3600 s
   projected 900-case run, <22 GiB). Fail closed per §7.4.
4. **The crossed candidate re-testing** (the bounded comparison `78_s`
   called for instead of further wordsmithing): Code endpoint
   candidates (Coder-1.5B, generic-1.5B, Coder-3B, generic-3B) run
   cache-disabled on the full 30-per-cell `worker_dev` population,
   isolated scoring plus composed diagnostics, all three renderers;
   compared only via `compare_worker_eval_runs(..., "model",
   model_endpoint="code")` — selecting on the worst renderer/node-
   operator stratum, not the pooled mean. The request-scope arm
   (Problem/Task salience) follows once a scope option parameterizes
   `build_worker_request`, which also re-enables the disabled
   request-contract comparison dimension.
5. **§7.4 confirmation for finalists**: each candidate advanced to the
   final comparison gets its full 900-case run repeated in a fresh
   process with exact generation equality (`confirm`, bound to
   `worker_dev`).
6. **Freeze decisions on corrected metrics**: the Code endpoint and
   prompt revision, ratification of the pending §1.6 Math-endpoint
   erratum, and the `math_code` index-band ruling (with 78_s's caution
   against narrowing to `step_1 ≤ 8` as a first remedy). Then D4
   (consumed construction prefix) and D5 (`SYSTEM_DIRECT`) before the
   formal construction screen.
