# 219_f — Infrastructure rev4 (response to 218_s)

All four findings and both minor items are implemented, each with
the reviewer's reproduction as a regression test. Full CPU suite:
**960 passed under `-W error`, TRUE process exit 0** (44 in the
routing battery). No GPU work has run; nothing is frozen or
launched.

## 1. The support-launch manifest (F1)

The execution lock is replaced by ONE pre-launch
`routing-dev-support-launch-v1` manifest binding EVERY prelaunch
input: the exact declaration (by content hash, carrying cohort +
runtime/pool/cache identity), the frozen probe rule
(`probe_rule_sha256`), the search cap (validated against the
declared screen size), the finite budget, the RECOMPUTED routing
source digest with the actual driver, and the environment identity.

- **Canonical environment**: `validate_environment_manifest_binding`
  now delegates to the Stage-1 `validate_env_manifest` — manifest
  kind, required fields, canonical self-hash, AND the source
  identity bound to the current tree. The reviewer's fictional
  self-hashing mapping refuses (regression), as does a manifest
  carrying a foreign source identity.
- **Consumption**: `materialize_dev_support(..., launch_manifest,
  environment_manifest, expected_manifest_sha256)` consumes the
  EXTERNALLY frozen hash, revalidates the manifest against the
  declaration and the live tree, verifies the environment is the
  bound one, and PERSISTS both `support_launch.json` and
  `env_manifest.json` beside the surface.
- **Extension**: the surface lock (`v3`) is built solely from the
  persisted, revalidated launch manifest plus output hashes —
  `support_launch_sha256` and `probe_rule_sha256` are now lock
  fields re-derived at every consumption.
- The driver named in the freeze must be the actual runner: the
  digest set covers `tasks/routing/*.py`, so the support-run driver
  module will exist and be digested before the step-4 freeze names
  it (the freeze cannot pass `build_support_launch_manifest`
  otherwise).

## 2. The launch boundary (F2)

`admit_and_append_launch(entry, expected_head_sha256, path)` is THE
launch boundary: it verifies the PERSISTED ledger against the
externally committed head, derives admission from that verified
state and the prospective entry ITSELF (its kind and allocated
budget — the checked launch IS the recorded launch), and appends the
same entry. The 60-hour envelope is fixed inside. The
caller-supplied `entries` parameter is gone — the reviewer's
`entries=[]` repeated-first-support spoof is structurally
impossible, and the regression shows the second support refusing
from the persisted chain while a replay of the empty-ledger
admission dies on the head check. `append_ledger_entry` now REFUSES
launch kinds, so admission cannot be bypassed.

**Finiteness**: `_finite_number` (math.isfinite) guards every
budget, consumption, reserve value, multiplier, and timing — the
reviewer's NaN launch maximum and NaN reserve both refuse
(regressions) — plus the charter's lightweight-freeze budget.

## 3. The report boundary (F3)

`telemetry.probe_report(groups, loaded=…, bound_cohort=…,
frozen_rule=…)` consumes the frozen bound cohort and rule and
requires the groups to BE the frozen design: the cohort record must
rehash and bind this surface's lock and this rule; observation ids
must match exactly; every bound observation must appear exactly
`groups_per_observation` times; every group must have exactly the
frozen `group_size`. The reviewer's extra-authenticated-group
reproduction (which shifted hierarchical ModelAcc 1.0 → 0.9444)
now refuses, as do missing groups, wrong sizes, tampered cohort
records, and foreign rules. The report embeds its design identity
(rule/cohort/lock hashes, counts).

## 4. Aborted segments carry their checkpointed groups (F4)

`merge_segments` requires EVERY segment to contain
`[resume_from, cutoff)` in full — a checkpoint cannot have consumed
groups the segment does not carry. The reviewer's aborted-cutoff-3-
with-rows-`[0,1]` reproduction refuses ("omits checkpointed
groups"); only the post-cutoff aborted tail is optional (excluded
as preserved evidence).

## 5. Minor items

- **Reserve rounding recomputed exactly**: the rounding field is
  the frozen policy literal `ceil_to_whole_gpu_hours`, and
  `r_cycle_gpu_hours` must equal `ceil(cohort × multiplier ×
  seconds / 3600)` exactly — below-basis, above-ceil, non-literal
  policy, and non-finite values all refuse (regressions, including
  the 4.3 s case where the exact ceil moves 7 → 8).
- Trailing whitespace stripped from the committed `216_s` review
  document; `git diff --check` clean.

## 6. Next

Reviewer sign-off, then 211_f §15 step 4: the
support-materialization freeze — the freeze document commits the
support-launch manifest hash (built against the actual runner
module and the run's canonical environment manifest) and the ledger
head; the support launch is admitted and appended through
`admit_and_append_launch` as the chain's first launch entry.
