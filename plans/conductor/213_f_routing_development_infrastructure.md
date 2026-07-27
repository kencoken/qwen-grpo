# 213_f — Development infrastructure implemented (211_f §15 step 3)

The signed charter's infrastructure tranche. Full CPU suite:
**955 passed under `-W error`, TRUE process exit 0** (916 prior + 39
new). No GPU work has run; nothing is frozen, smoked, or launched.

## 1. Where the code lives — and the one designed consequence

The three namespaces are registered in the generator
(`program.NAMESPACE_CONFIG` + `types.NAMESPACES` — the only two
frozen-tree files touched; none of the eight Stage-0
`SOURCE_DIGEST_FILES` changed). Everything else is a NEW package
`tasks/routing/`, deliberately outside `tasks/conductor/`, so
development iteration does not churn the Stage-1 source identity
from here on.

**Source-identity retirement (132_s §11.4, expected and verified):**
because `stage1_source_digest` covers `tasks/conductor/*.py`, the
namespace edits retire LIVE verification of the B diagnostic archive
at this and later commits — `validate_env_manifest` now refuses it
with "bound to a different source identity", exactly as designed.
The archive remains byte-unchanged and fully verifiable at any
checkout from the execution commit through **`0f56a65`** (the 212_f
sign-off, the last commit whose conductor sources equal the B
execution identity). The companion bundle's clean-checkout restore
instructions apply at that pinned range; the 210_s worktree restore
test ran at `b1ca18b`, inside it.

## 2. What was implemented (per 211_f §15 step 3)

- **Namespaces** (`program.py`, `types.py`): `routing_dev`
  (2,000/500 per cell), `routing_dev_val` (500/250),
  `routing_dev_cycle` (500/250), all `stopping_rule: fixed`.
  `charter.verify_namespace_registration()` cross-checks the charter
  caps against `NAMESPACE_CONFIG` fail-closed (the stage1
  anti-drift pattern). The 211_f disjointness test regenerates id
  prefixes across ALL ten namespaces and asserts zero intersection;
  `policy_dev` cohort B (24–47) is asserted intact.
- **`tasks/routing/charter.py`**: the frozen budget literals (60
  GPU-h envelope, 10 h run ceiling, 3 h probe ceiling, 10 prompt
  variants); the cycle-wide natural-mixture definition
  (cells equal / latents equal within cell / renderers equal within
  latent) with `natural_mixture_weights` (refuses empty or
  duplicated populations); `routing_execution_digest` — tracked
  `tasks/conductor/*.py` + `tasks/routing/*.py`, name\0bytes\0
  chained, REFUSING any driver whose file is outside the digested
  set (208_s; `train.py` is a refusal test); `claim_run_root`
  (never overwrites); `lightweight_freeze` (config + motivation +
  budget, content-hashed, for smokes / resume validation /
  standalone evaluations).
- **`tasks/routing/dev_support.py`**: the §4 machinery,
  cohort-parameterized — `validate_dev_cohort` /
  `dev_cohort_observations` (dev namespaces only, per-cell caps,
  duplicate-free), `build_dev_declaration` (identities +
  fingerprints + exact cohort spec, before materialization),
  `materialize_dev_support` (identity-checked runtime, v2 trace,
  declaration persisted beside the surface and hash-bound),
  `load_dev_surface` (the full Stage-0 fail-closed contract:
  complete 4^S coverage, every payoff re-scored from its terminal
  value against regenerated gold, content-hash bindings, trace
  completeness + identity equality, accounting invariants),
  `direction_yields` (EVERY materialized observation disclosed as
  w2_favoured / w3_favoured / tied / no_pair, per cell), and
  `select_c_fixed_dev` (210_s issue 1: candidate scores for both
  workers under the equal-weight family-correct criterion,
  renderer→latent→cell, tie → worker 2, persisted with rule +
  surface hashes + `development_only: true`).
- **`tasks/routing/cohorts.py`**: the frozen probe-selection rule as
  a CLOSED schema (kind, namespace, prefix length, renderers,
  visibility, group size, groups/observation — no field can carry an
  outcome, so 210_s issue 4's "mechanically auditable" is enforced
  by schema, with an outcome-smuggling refusal test);
  `probe_cohort_spec`/`apply_probe_rule` are pure functions of the
  frozen rule (under-coverage of the prefix refuses);
  `bind_probe_cohort` adds ONLY surface hashes after
  materialization.
- **`tasks/routing/telemetry.py`**: per-group stats and stratified
  aggregation (cell × renderer × direction, ties a separate
  stratum) — parse/valid, reward levels, zero-variance split by
  constant level, the three contrasts kept separate (format,
  semantic 0.5-vs-1, exact w2/w3 direct via the
  `family_correct_variants` pair — a group must contain BOTH
  members), C1 node-level family-correct (malformed scores 0 and
  stays in the denominator, 130_s §6.5), C2 on its exact 209_s→211_f
  denominator (all non-Code nodes family-correct AND Code ∈ {2,3};
  optimal = per-observation payoff winner; tied observations
  reported but never scored), ScaleLift against `c_fixed_dev`
  (130_s §6.4 collapse from the cached surface; malformed
  contributes 0 to both members; a missing collapse row refuses),
  routing entropy and repeated-assignment concentration. Every rate
  is `{count, denominator, rate}`.
- **`tasks/routing/ledger.py`**: the append-only ledger
  (`plans/conductor/routing_dev_ledger.md`) as self-hashed,
  hash-chained fenced JSON entries — `read_ledger` re-derives the
  chain and refuses edited, reordered, or removed entries;
  `append_ledger_entry` re-verifies before every append. Entry
  schema enforces the 211_f §12 fields incl. `outcome_informed` and
  `cohort_selection` (outcome_blind / outcome_conditioned). Reserve
  records REQUIRE the full numerical basis (212_f reminder 1:
  assumed cohort size, evaluation multiplier, measured
  seconds/observation, rounding). `envelope_state` charges a
  launch its allocation until its measured cost is recorded.
  `check_launch_admissible`: ordinary launches need
  `remaining ≥ max + R_cycle`; closure CONSUMES the reserve
  (`max ≤ R_cycle` and `remaining ≥ max`) — the 210_s issue-4
  no-double-count rule, both directions tested.
- **`tasks/routing/checkpoint.py`**: the v1 contract —
  `GroupAccountant` tracks generated vs optimizer-consumed group
  counters separately and is the ONLY source of checkpoint
  counters (`authorize_checkpoint` refuses off the v1 boundary;
  consuming never-generated groups refuses);
  `build_checkpoint_record` binds the ten identity keys (routing
  source digest, env manifest, config, prompt, cohort, renderer
  schedule, surface, worker pool, cache identity, seed) + counters
  + RNG-state hash + sampler position, self-hashed;
  `validate_resume` fails closed on ANY identity mismatch (naming
  the keys — a changed parameter is a fork) and on tampered
  records; `merge_segments` excludes an aborted segment's
  post-checkpoint rows from the trajectory while preserving them as
  evidence, and refuses duplicated, missing, or non-zero-based
  group indices; `isolated_rng` snapshots/restores python + numpy +
  torch (+ CUDA when present) so checkpoint evaluations never
  perturb rollout sampling; `capture_rng_state` is the serializable
  snapshot the record hashes.

## 3. Deliberately NOT in this tranche

The GPU drivers (the resume-validation run and the grouped-probe
executor) are built with their own tranche freezes — the
resume-validation launch freeze must state its exact ceiling (212_f
reminder 2) and the probe freeze binds surface hashes that do not
exist until support materialization. The contract layer they must
satisfy (accountant, checkpoint records, merge rules, telemetry,
ledger admissibility) is what this tranche implements and tests.
No probe rule, cohort, or reserve has been frozen; the ledger file
does not exist yet — its first entry is the support-materialization
freeze.

## 4. Tests

39 new tests in `test_routing_dev.py`, all refusal paths exercised:
namespace disjointness across all ten namespaces; digest
driver-outside-set refusal; dev-cohort validation (9 refusal
cases); materialize→load roundtrip on a CPU fake pool with a
sabotaged worker 3 (yields w2-favoured directions end-to-end
through `direction_yields` and a non-tied `c_fixed_dev` = 2 with
candidate scores 1.0 / 0.5); loader payoff-tamper and
declaration-swap refusals; probe-rule determinism,
outcome-smuggling and under-coverage refusals, bind-adds-only-
hashes; telemetry contrasts / C1 malformed-in-denominator / C2
conditional denominator with tied-never-scored / ScaleLift incl.
missing-collapse-row and off-ladder-reward refusals; stratified
rates carry count+denominator; ledger chain edit/removal refusals,
schema refusals, reserve numerical-basis refusal, envelope
allocation-until-closeout, ordinary + closure admissibility both
ways; accountant boundary refusals; checkpoint roundtrip, identity
mismatch (named key), tamper, off-boundary refusals; segment merge
exclusion + gap/duplicate/start refusals; isolated-RNG restoration
across all three streams. Full suite: 955 passed, `-W error`, TRUE
exit 0.

## 5. Next (211_f §15)

Step 4: freeze the outcome-blind support-materialization tranche —
candidate prefix, renderer schedule, search cap, the probe-selection
rule (via `freeze_probe_rule`), and the surface contract; the
ledger's first entries (the freeze + the provisional reserve with
its numerical basis) go through `append_ledger_entry`. Then the GPU
resume-validation tranche (exact ceiling in its lightweight
freeze), then the probe freeze and run.
