# 311_f — Spine Unit 2 REV2 (response to 310_s)

Both P1s and the P2 repaired. **The contract hash is UNCHANGED at
`d47a63ff…`** — exactly as 310_s anticipated ("this need not change
the contract hash because all current values already agree"): the
repairs add enforcement, not new values. Full suite: **1014 passed
under `-W error`, TRUE exit 0** (1013 + one new regression test).

## 1. P1 — `population_of` now goes through the authenticated boundary

`tasks/routing/p0_schedule.py` — the signature changed from
`population_of(contract, mixture, oid)` to
`population_of(contract, oid)`. The mixture is loaded INTERNALLY
through `_validated_mixture(contract)` (both bindings: the
contract's file pin AND record pin) — a caller-supplied mapping has
no path in. The sentinel override (from the contract's frozen ids)
is applied first, then the authenticated `class_assignment`.

**One-field population-substitution regression** (the reviewer's
reproduction, now a permanent test): a forged pinned-mixture file
with one observation flipped `bridge` → `q2_composite`:

- retaining the stale `record_sha256` → `load_pinned_mixture`
  refuses at the file binding;
- even when the caller supplies the forged file's OWN recomputed
  file hash → refuses at the semantic rehash against the stale
  record. Neither variant can reach `population_of`.

## 2. P1 — construction mechanically cross-checks the projection

`tasks/routing/p0_contract.py` — new
`_validate_against_projection(contract)`, invoked at the END of
`build_p0_science_contract()` (so freezing and the
frozen-equals-fresh test both pass through it). It loads the
projection through the Unit-1 authenticated boundary
(`load_projection`, both reviewed hashes) and compares
MECHANICALLY, refusing on any mismatch:

- the contract pins THIS projection
  (`input_pins.c2_projection_sha256` == the projection's
  self-hash) — the "pin projection A, carry values B" channel is
  closed at the root;
- Q1 sizing counts 13/34/13 == `p0_size_derived.sizing_cells`;
- `nominal_epochs` 39 == `derived_epochs`; `groups_per_epoch` ×
  nominal == `derived_groups` 6123; `groups_per_epoch` 157 ==
  `len(epoch_rows)`;
- per-cell count / `sizing_epochs` == the projection's measured
  per-epoch counted rates;
- conditional baselines (8/152, 0/15) == the projection's
  `q2_blocks` eligible/optimal counts;
- marginal baselines (73/108) and target workers == the cold-start
  gate's per-direction `target_selections`/`target_worker`;
- sentinel ids: contract == pinned mixture == projection.

**Regression** (`test_p0_contract_cross_checks_the_projection`):
with `load_projection` monkeypatched to return an altered
projection, the build refuses — demonstrated on three independent
channels (a sizing cell 34→33, a conditional numerator 8→9, a
marginal baseline 108→107).

## 3. P2 — repeated rows no longer share mutable prompts

`build_trainer_rows` appends `copy.deepcopy(...)` of the cached
row. Regression: mutate a duplicate occurrence's prompt content;
the other occurrence is unchanged.

## 4. Scope of change

Only `p0_schedule.py` (P1-1 + P2), `p0_contract.py` (P1-2), and
`test_routing_dev.py` changed. The committed contract JSON, the
pinned mixture, the projection, and all identities are untouched:

- Contract: self `d47a63ff…`, file `8b348b0f…` (both unchanged).
- Pinned mixture: self `135a72bf…`, file `b305d9c8…`.
- Projection: self `f1912078…`, file `41f15c5d…`.

Per 310_s's closing note, pure schedule helpers remain testable
with variant contracts; the requirement that the eventual real
consumer loads through `load_p0_science_contract()` (the
externally reviewed pin) is retained.

## 5. Next

Sign-off on this rev2 → Unit 3: `p0_estimands.py` + exact C2
replay equivalence against the frozen projection, with the carried
reminder (action sensitivity via a COHERENT VALID alternative that
changes a scientific result) and the population-substitution
sensitivity altering the projection's mapping comparison.
