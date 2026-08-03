# 312_f — Unit 2 LOCKED; Spine Unit 3: typed estimands + the exact C2 replay equivalence oracle (for review)

Unit 2 is locked at its signed rev2 state (§1). Unit 3 implements
303_f §9 step 3 under the 305_f clauses, with the carried
action-sensitivity reminder PROVEN. Full suite: **1018 passed under
`-W error`, TRUE exit 0** (1014 + four new tests).

**Headline: the independent raw-trace rederivation reproduces the
frozen compatibility projection EXACTLY — all 25 fields equal,
self-hash equal to the reviewed pin `f1912078…` — on the first
run, under guards proving the evaluator never invoked the legacy
report builder, never read the source report's values, and never
consumed the frozen projection.**

## 1. Unit-2 locked identities (the signed pins)

- Contract: self `d47a63ff…` (the externally recorded pin), file
  `8b348b0f…` — UNCHANGED through rev2, as 310_s anticipated.
- Code state: 311_f @9236a59 (`p0_contract.py` with the mechanical
  projection cross-check; `p0_schedule.py` with the authenticated
  `population_of` boundary and deep-copied trainer rows).
- Unit-1 pins unchanged: mixture `135a72bf…`/`b305d9c8…`,
  projection `f1912078…`/`41f15c5d…`, schema
  `p0-science-contract-v2`.

## 2. `tasks/routing/p0_estimands.py` — the versioned typed rules

Every scientific quantity of P0 (and of the oracle) is computed
here, driven by the TYPED rule objects of the frozen contract —
the closed rule literals are operative (an unknown rule refuses,
never silently computes something else). Ground-truth primitives
are shared with the legacy path by design (the frozen parser, the
node/worker family tables, the authenticated surface, the pair
structure); the ESTIMAND layer is implemented independently.

- **Q1**: `q1_counted_event` (q1-counted-v1: high-reward FULLY
  family-correct AND low-reward STRICTLY-LOWER, valid-only, same
  group), `evaluate_q1_gate`, and the sizing basis
  (`derive_sizing`, sentinel structurally excluded — it is never
  in the cells argument).
- **Q2 — the four quantities, structurally distinct (305_f §3)**:
  (1) `marginal_target_selection` + `evaluate_q2_cold_start_gate`
  (over VALID completions regardless of upstream correctness);
  (2) `c2_eligible_completion` (c2-eligibility-v1; malformed
  EXCLUDED); (3) `conditional_choice` — the P0 learning estimand,
  zero denominator = None, NEVER 0.0; (4) `group_contrasts`
  (direct + semantic).
- **Both 305_f counterexamples are permanent tests**: a semantic
  contrast (levels 1 + 0.5 with the 0.5 fully family-correct) is
  NOT a Q1 counted event; a target-worker selection with a
  family-wrong non-Code slot is marginal support but NOT eligible
  (so never conditional success).
- **The sentinel contract (305_f §4)**:
  `sentinel_checkpoint_block` — counts, BOTH raw denominators
  (groups AND completions), both first-index families (group and
  update), population BOUND to the contract's frozen ids (an id
  outside the sentinel cell refuses; the trajectories are
  assembled by the consumer across checkpoints). The [2]/[3]
  regression is retained: specialist selections in a sentinel
  group produce ZERO worker-1 events while staying in every
  denominator. `sentinel_legacy_view` maps to the exact frozen C2
  field shape.
- `decide_outcome` — the pure four-branch decision over a matrix
  supplied as data (all four branches tested).

## 3. `tasks/routing/p0_c2_equivalence.py` — the oracle

`derive_c2_projection`: Unit-1 authentication first
(`verify_c2_replay_source`), every input loaded through its
reviewed pin (contract `d47a63ff…`, mixture double-bound, surface
lock, selection record), then the RAW trace is handed to
`derive_from_trace` — the PURE layer (no file access): every
completion text re-parsed with the frozen parser, its semantic
assignment re-derived through the frozen positional mapping, its
reward re-derived from the locked surface; stored fields must
agree exactly or the replay refuses. All estimands via
`p0_estimands` under the contract's rules.

`verify_c2_equivalence`: the rederivation must equal the frozen
projection FIELD FOR FIELD (`compare_projections` returns every
differing field) and rehash to the reviewed pin. **Result: PASS —
25/25 fields, `f1912078…`.**

Independence, proven in-test with guards active during the full
derivation: `unit_c2_sample.build_exposure_report` monkeypatched
to raise (never invoked); `load_projection` monkeypatched to raise
in the evaluator's namespace (the frozen projection is consumed
only by the comparator); `Path.read_text` guarded to refuse any
read of `exposure_report.json` (its BYTES are hashed by the Unit-1
inventory check; its values are never read).

Disclosed config echoes: the cap-formula prose and the
decision-matrix strings enter the derived projection from the
hash-guarded `MIXTURE_V2_CONFIG` constant (refuses if mutated) —
frozen config DATA reproduced verbatim, not measured results;
every numerical field is generated from the trace.

## 4. Sensitivity (the 305_f set + the carried reminder)

- **Row reorder**: two swapped trace rows refuse at the
  pinned-schedule identity.
- **Population substitution**: one observation's class flipped
  (`goal_first_control` → `anchor`) in the derivation inputs —
  the projection MAPPING comparison itself changes
  (`population_by_observation`, `class_assignment`) alongside
  `per_population_draws`; the comparator refuses.
- **CARRIED REMINDER — coherent valid alternative**: in the real
  trace, the single reward-1.0 fully-family-correct completion of
  a counted `code_atomic` bridge group (row 51) is replaced by a
  COPY of a coherent 0.5 completion from the same group — text,
  action, assignment and reward all consistent, so every
  consistency check passes and the derivation SUCCEEDS — and a
  scientific result changes: `q1_gate.code_atomic.counted_groups`
  13 → 12, `q1_counted_per_epoch_measured` moves, and the sizing
  minimum itself moves (`derived_epochs` 39 → 42). The comparator
  refuses on exactly those fields.
- **The contrast**: corrupting ONLY the stored reward of that same
  completion (text untouched) refuses at the
  stored-vs-rederivation check — "a corrupted redundant field is
  not an alternative result". Corruption and alternatives are
  distinguished, as the reminder required.

## 5. Scope of change

New: `p0_estimands.py`, `p0_c2_equivalence.py`, four tests. The
four legacy modules remain byte-untouched (the compatibility
oracle); no committed artifact changed; all Unit-1/Unit-2
identities unchanged.

## 6. Next

Reviewer pass on this unit → Unit 4 (sizing/cap arithmetic + the
generated freeze tables; 303_f §9 step 4), then the first real
consumer and the merge gate.
