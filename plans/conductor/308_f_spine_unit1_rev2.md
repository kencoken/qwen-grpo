# 308_f — Spine Unit 1 REV2 (response to 307_s)

All four P1s and the P2 repaired; the projection regenerated (v2,
with the exact maps) through the now-authenticated boundary. Full
suite: **1011 passed under `-W error`, TRUE exit 0**.

## 1. P1 — complete-archive replay verification

`verify_c2_replay_source` now enforces **exact file-set equality**
with the closeout inventory (every member must exist and match;
nothing extra, nothing missing) BEFORE any extraction or replay —
the reviewer's deletion reproduction (identity/environment
manifests, checkpoint maps, preflight removed) now refuses at
"missing". The anchors are **validated from the actual manifests**,
not asserted by the sample record: the identity manifest must
rehash to the reviewed anchor; the environment manifest must
self-hash validate AND attest to the reviewed environment; the
sample record must agree with both validated manifests.
Regressions: missing member, extra file, tampered (rehashed)
identity manifest, tampered trace bytes.

## 2. P1 — authenticated projection boundaries

`extract_projection`/`freeze_projection` now call
`verify_c2_replay_source` FIRST — a modified source cannot mint a
projection carrying the frozen source pins (regression: extraction
over a tampered archive refuses). `load_projection` requires BOTH
externally reviewed hashes — the committed file bytes AND the
semantic self-hash — so a coherently rewritten projection with a
recomputed self-hash refuses at the file pin (regression included).

## 3. P1 — the schema is typed, closed, and self-validating

`p0_schema.py` reworked (schema version bumped to
`p0-science-contract-v2`):

- **closed rule identifiers + typed operative fields**:
  `Q1CountedEvent` (valid-only, same-group, reward-1.0/full-fc,
  reward-0.5/strictly-lower — as fields with closed literals),
  `EligibilityRule` (family-correct non-Code routing, specialist
  set (2,3), malformed-excluded), the conditional estimand as
  closed fields (`c2_optimal`/`c2_eligible`/`undefined`),
  `ConditionalBaseline` as NUMERIC numerator/denominator records
  (num ≤ denom enforced), `CapRule` with closed branch actions and
  the exact capacity-input tuple;
- `SentinelDiagnostics` is a CLOSED specification of every signed
  field (counts, both denominators, both first-index families,
  both trajectories); `RequiredDiagnostics` validates against the
  complete 301_f vocabulary — the list is complete, not a menu;
- **validation from construction AND loading**: every dataclass
  validates its invariants in `__post_init__` (exact cell/direction
  sets, positive non-boolean integers, finite numbers — the
  reviewer's `True`-as-integer and NaN reproductions now refuse at
  construction), and the loader reconstructs through the same
  constructors; `allow_nan=False` in canonical serialization;
- `InputPins` gained the reviewed C2 identity and
  attested-environment anchors, and hash-format validation
  (64-hex) on every pin;
- the marginal gate structurally CANNOT become conditional
  (`marginal_upstream_correctness_required` must be False).

## 4. P1 — exact mapping parity in the projection

The projection (now `c2-compatibility-projection-v2`) carries the
exact `class_assignment`, `multiplicities`,
`sentinel_observation_ids`, and the EFFECTIVE
`population_by_observation` map (sentinel override applied) from
the authenticated pinned mixture — the oracle compares mappings
mechanically, and the Unit-3 population-substitution sensitivity
test will alter this comparison. Regenerated identities:

- projection self-hash:
  `f1912078fb27e67c489705737295bac461033324d58600825d944b5a12bf6355`
- projection file hash:
  `41f15c5d27ee1c9867bc82833bd088319c5644f1c0a86096844442b4306446c3`

## 5. P2 — double-binding in code

`load_pinned_mixture` now enforces the reviewed FILE hash
(`b305d9c8…`) in addition to the semantic pin — reformatted JSON
refuses (regression). `load_projection` receives the same
treatment (§2).

## 6. Identities

- Pinned mixture: self `135a72bf…` (unchanged), file `b305d9c8…`
  (unchanged, now enforced in code).
- Projection: self `f1912078…`, file `41f15c5d…` (regenerated —
  the maps entered the body; the underlying scientific values are
  unchanged and re-verified by the tests).
- Schema version: `p0-science-contract-v2`.

## 7. Next

Narrow changed-lines review → Unit 2 (`p0_contract.py` — the
contract instance with its externally reviewed hash — and the
strict schedule loader; the carried reminders: legacy builder
DISABLED and clean-clone-restored surface proofs).
