# 315_f — Unit 3 LOCKED; Spine Unit 4: registered sizing/cap arithmetic + generated freeze tables (for review)

Unit 3 is locked at its signed rev2 state (§1). Unit 4 implements
303_f §9 step 4 — "add ONLY the registered sizing/cap arithmetic
and the generated freeze tables". Full suite: **1020 passed under
`-W error`, TRUE exit 0** (1018 + two new tests; the legacy C1/C2
verifiers and the C2 equivalence oracle pass inside it).

## 1. Unit-3 locked identities (the signed pins)

- Code state: 314_f @f8119b2 (`p0_estimands.py` with the shared
  `valid_assignment` gate; `p0_c2_equivalence.py` with the
  physical-row-position binding).
- Every artifact identity unchanged through rev2: contract
  `d47a63ff…`/`8b348b0f…`, projection `f1912078…`/`41f15c5d…`,
  mixture `135a72bf…`/`b305d9c8…`; the equivalence oracle PASS
  25/25 at the reviewed pin.

## 2. `tasks/routing/p0_cap.py` — the registered arithmetic (305_f §5)

```
nominal_epochs  = contract.sizing.nominal_epochs   (C2-derived, 39)
capacity_epochs = frozen cap formula (beta smoke + reserve inputs)
launch_epochs   = min(nominal_epochs, capacity_epochs)
```

- `derive_capacity(contract, ...)`: the frozen V1 formula over the
  REGISTERED input tuple — the ceiling comes from the CONTRACT
  (never the caller); the four measured inputs are validated
  (finite, non-boolean, non-negative; whole-epoch strictly
  positive), echoed, and returned for persistence. An
  unregistered cap rule refuses before any arithmetic; the input
  record's names must equal the contract CapRule's closed
  `capacity_inputs` tuple.
- `derive_launch_plan(contract, ...)`: the complete 305_f §5
  record — every input AND all three values — with the closed
  branches from the contract:
  - `capacity <= 0` → `stop_reviewed_amendment`, launchable
    False;
  - `0 < capacity < nominal` → `disclosed_under_target`, with the
    QUANTIFIED disclosure: projected Q1 counted groups per cell =
    launch_epochs × the measured per-epoch rate, next to the
    100-group target (claims based on achieved projected
    exposure, per 290_f — the capped branch is EXPECTED);
  - `capacity >= nominal` → `no_extra_training`, launch exactly
    nominal, `spare_epochs_not_trained` recorded.
- `require_launchable(plan)`: the consuming boundary — a
  stop-branch plan refuses; a reviewed amendment is a human
  decision, never an automatic launch.
- **Parity with the frozen legacy formula**: `derive_capacity`
  equals `derive_p0_cap_v2` (capped epochs AND available seconds)
  on a shared input grid including boundary cases — permanent
  test. Branch coverage: 60→39 (spare 21), 13 (under-target with
  projections 33.8/88.4/33.8 vs target 100), 0 (stop; the
  `min()` identity asserted on every branch).

The later `P0LaunchFreeze` (Unit 5, constructed only after the
val/cycle/beta inputs exist) persists the `derive_launch_plan`
record verbatim.

## 3. `tasks/routing/p0_tables.py` — the generated freeze tables (303_f §8)

`generate_traceability_appendix()` renders
`plans/conductor/p0/p0_traceability_appendix.md` (committed,
6,814 bytes) ENTIRELY from the authenticated artifacts — the
contract under its reviewed pin, the projection under both pins,
the pinned mixture, the replay-source constants. No number is
hand-transcribed. Sections: identities (all three artifacts +
every replay-source pin); active scope; the Q1 rule with the
C2-measured per-cell table; the four Q2 quantities with the
per-direction baseline table (73/108 marginal, 8/152 + 0/15
conditional, asymmetry carried as context); the sentinel
checkpoint-zero block; sizing and the cap (branches + registered
inputs); the C2 measured results (draws 75/420/25/90/160/15,
6242/38, 662/0.8433, both gates, the decision); and the
supersession/lineage references (the 303_f §7 home for historical
prose).

`verify_appendix()` — the mechanical gate: the committed bytes
must equal a fresh generation. Tests: PASS on the committed file;
an edited number (6123→6124) refuses; a diverging artifact value
(monkeypatched projection, 662→663) changes the generation and
refuses — the numbers COME from the artifacts, mechanically
detectable per the MODERATED 303_f §8 claim (detectable for
generated numerical fields — independent invariants and human
review remain in force).

## 4. Scope of change

New: `p0_cap.py`, `p0_tables.py`, the committed generated
appendix, two tests. Nothing else changed; no frozen artifact
touched; all identities unchanged. (The source digest changes by
the registered addition of routing files, per the 303_f note —
historical identity remains established by the archived
manifests.)

## 5. Next

Reviewer pass on this unit → Unit 5 (the first real consumer;
`P0LaunchFreeze` only after the routing_dev_val lock, cycle/
R_cycle, and beta smoke inputs exist) → the merge gate (full
suite + every archive reverifies + the equivalence oracle + the
traceability appendix review + sign-off).
