# 287_f — Contract-spine cleanup plan (pre-P0; runs after the 286_f wrap-up)

The high-level plan for the targeted restructuring recommended in
284_s and accepted (with refinements) in 285_f — both written
BEFORE the Unit-C execution; this document synthesizes them with
what Unit C added. It executes on a dedicated branch after the
286_f wrap-up completes (B2/C2 passed), and merges before any
further pre-P0 freeze. It is a plan, not a freeze.

## 1. What we are fixing (284_s diagnosis, confirmed in 285_f)

The review-cycle volume traces to structural causes, not mainly
authoring error: the ACTIVE specification is distributed across
many Markdown revisions (clauses inherited/superseded/reworded —
how the renderer requirement silently vanished); scientific
concepts live in untyped dicts (why `semantic_contrast` could stand
in for the Q1 event); `p0_mixture.py`-class modules combine
authentication, schedule, estimands, power and reporting;
executable global config + import-time hashes invited identity
drift (then MORE guards — 271_s/273_s/280_s — of exactly the kind
the diagnosis criticizes); the preregistration posture makes every
correction expensive; and reviews broadened rather than converged.
The prescription accepted in 285_f: a small contract spine before
P0, not a rewrite.

## 2. What Unit C added (material evidence for the design)

- **The estimand was the fragile point, empirically.** The
  Q1-counted event and its gate statistic took three review rounds
  (276_s→280_s) to converge and exists today in four places kept
  aligned by tests (`bridge_eligible`,
  `q1_counted_rates_from_archive`, `unit_c_sample.q1_counted`, the
  synthetic-archive test helper). `estimands.py` as the single
  definition consumed by simulation, execution, reporting AND
  tests is the highest-leverage cut.
- **Transport heterogeneity is real**: the homogeneous per-cell
  projection did not reproduce for `math_atomic` (283_s wording).
  `design.py` must therefore support per-latent/per-stratum rate
  bases with the basis disclosed — not only per-cell homogeneous
  rates.
- **The guards-on-guards pattern hit its ceiling**: three
  generations of live-config hash guards exist because the config
  is mutable global state. The immutable-contract refinement
  (285_f) deletes that defect class and the guards with it — tests
  construct variant contracts instead of monkeypatching module
  globals (the test suite currently monkeypatches EXTENSION_CONFIG
  / MIXTURE_CONFIG / UNIT_C_CONFIG in fixtures; each is a live
  demonstration of the problem).
- **The scope now composes MORE, not less**: the P0 freeze must
  compose the 269_s scope, the 283_s amendment (Q1-direct set,
  math_atomic sentinel), the frozen sizing + cap formulas, and the
  Q2 gate — precisely the distributed-spec load the spine exists
  to carry.

## 3. The deliverable (284_s structure + 285_f refinements)

```
P0Contract (immutable, constructed once)
├── authenticated input identities      (locks, selections, comparators)
├── exact schedule specification        (classes, quotas, seeds)
├── active scientific objectives        (Q1-direct set, Q2, sentinel)
├── estimand definitions                (by reference to estimands.py)
├── gate definitions                    (Q1 criterion, Q2 cold-start,
│                                        sizing + cap formulas)
├── superseded requirements             (explicit, with provenance)
└── expected artifact identities
```

Four pure components extracted from the current modules:

- `contract.py` — the frozen active specification. IMMUTABLE (the
  285_f refinement): a frozen dataclass built once; variant
  contracts in tests replace global monkeypatching; the live-config
  hash guards become structurally unnecessary and are removed.
- `estimands.py` — the Q1-counted event, the Q2 event/gate
  definitions, ONE implementation each, consumed everywhere.
- `schedule.py` — deterministic cohort/mixture construction from
  (contract, surface, selection).
- `design.py` — power/exposure calculations and acceptance checks,
  with heterogeneous rate bases (§2).

API shape (284_s): `build_schedule(contract, surface, selection)` →
`evaluate_design(contract, schedule, evidence)` →
`verify_contract(contract, schedule, report)`. Verification stays
at the consuming boundary; NO proof-marker type hierarchy.

**Generated-or-checked freeze documents** (the 285_f
highest-value item, adopted unconditionally): the numerical tables
of every future freeze doc are emitted from — or mechanically
checked in tests against — the same contract object the code
executes. Prose-vs-executable divergence (the largest single
finding class: 271_s B1, 273_s block-occupancy, 276_s population)
becomes structurally impossible.

## 4. Hard constraints (what the cleanup must NOT touch)

- The worker runtime, provenance system, and evidence machinery
  stay as they are (284_s: the next failures are execution-side).
- **No retroactive identity changes.** Every frozen archive (Step
  4/5/6, extension, C1) keeps verifying exactly as committed; the
  existing modules and their verifiers REMAIN for their archives.
  The spine is for P0-FORWARD artifacts only.
- Identity impact disclosed up front: the routing source digest
  moves with any source change, so P0-forward freezes get new
  identities — nothing already frozen is invalidated.
- The preregistration discipline itself is retained in full
  (285_f: it caught the dtype divergence, the legacy-index leak,
  and the forgeable comparator before they touched a result).

## 5. Process (284_s process changes, adopted for the spine itself and after)

1. Design review of component boundaries (this plan's successor).
2. Implementation with the machine-readable contract and a
   traceability table (requirement → field → enforcement →
   regression → artifact).
3. Implementation review; ONE repair pass.
4. Changed-lines + mechanical verification (hashes, full suite).
5. The stopping rule: sign off unless a remaining issue can
   plausibly change results, identity, privacy, or phase
   separation. Wording and exotic malformed-object cases do not
   trigger further rounds.

## 6. Branch and merge mechanics

- Work happens on a dedicated branch off `conductor_stage1`
  (proposed: `conductor_spine`), so the wrap-up lineage stays
  linear while the restructuring iterates.
- Merge criteria: full suite green under `-W error`; every
  committed archive re-verifies on the branch (the frozen-evidence
  regression set is the merge gate); the traceability table
  reviewed; reviewer sign-off.
- After merge, the deferred pre-P0 units (286_f §5:
  `routing_dev_val`, cycle/`R_cycle`, beta smoke, the P0 freeze)
  are built AS contract-spine artifacts — the P0 freeze is the
  spine's first full consumer, exactly where 285_f aimed it.

## 7. Sequencing (relative to 286_f)

286_f wrap-up (erratum → B2 → C2 pass) → THIS plan's design review
→ spine implementation on `conductor_spine` → merge → val/cycle/
`R_cycle`/beta smoke/P0 freeze on the spine → checkpoint-zero
eval → P0. References: 283_s (Unit-C review), 284_s (diagnosis +
proposal), 285_f (response + refinements + timing), 282_f/286_f
(Unit-C record + erratum).
