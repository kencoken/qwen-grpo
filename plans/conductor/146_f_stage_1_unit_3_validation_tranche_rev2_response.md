# 146_f — Response to 145_s (unit-3 rev-2 critique)

All six blocking findings are implemented and the directed **256**
decision is taken. `144_f` is preserved at its reviewed bytes; the
completed preregistration is reissued forward as
`147_f_stage_1_unit_3_validation_tranche_prereg_rev3.md`. Unit-3 tests:
68; full CPU suite: **729 passed** under `-W error`. Every
145_s-requested refusal probe is a named test: empty B, mixed
manifests, 1/1 agreement, impossible counts, and incomplete replay
outputs all refuse. No frozen grid or GPU replay executed.

## Blocking findings

**1. B executable end-to-end — implemented.** `run_replay()` in
`stage1_replay.py` is the complete GPU driver: environment manifest →
pinned-surface verification (`verify_surface_pin`) → pre-sampling pair
table (`pair_table_from_surface` adapter over the surface mapping) →
candidate-specific chat messages and rendered-request hashes → replay
manifest, all BEFORE sampling → NF4 base + fresh zero-B LoRA loader →
per-completion-seeded singleton generation → `parse_routing_action` +
`positional_to_semantic` classification against the pair table →
raw-completions artifact (content-addressed) → validated B artifact,
persisted and reloaded through `load_b_artifact`. And the specific
failures the review reproduced:

- `summarize_replay` now refuses partial keys (exact
  pair-table × prompt coverage), refuses any `n ≠ 256`, refuses
  impossible or non-integer counts, and requires complete observation
  meta;
- the Bonferroni population `O` is derived structurally from the
  pre-sampling pair table (`2 × distinct-payoff observations`), never
  from caller-supplied counts;
- aggregation is the frozen renderer→latent→equal-cell weighting
  (`_aggregate`), with a test proving it differs from a raw
  observation average exactly when eligibility differs within a cell;
- `aggregate_verdict` no longer accepts a B dictionary: it loads the
  content-addressed B artifact (`load_b_artifact`: hash, execution
  identity, embedded pair table/meta, exact count-key set, n = 256,
  count identities) and RECOMPUTES direction statuses from the integer
  counts; an empty pair table refuses ("B is not evaluable"), so empty
  B can never leave `confirm_possible = True`.

**2. One authoritative execution — implemented.** `finalize_artifact`
validates the execution hash (64 lowercase hex) and refuses `extra`
fields that shadow reserved keys; `load_artifact` now enforces exact
per-artifact row schemas (`_ROW_SCHEMAS`): field sets, frozen trial
counts (10,000 A/C, 5,000 D, 256 B), and count identities
(pass+fail+unresolved = trials for A; error ≤ trials for D;
k2+k3 ≤ n for B) — impossible counts refuse. `aggregate_verdict` binds
all four artifacts to ONE execution identity taken from A and verified
on C, D, and B; the compatibility rule for B's GPU session is identity
(same box, same `stage1-environment-v2` manifest). Mixed-execution
inputs refuse (tested).

**3. Agreement criterion — corrected.** `agreement_passes` now
requires exactly the 1,000 frozen datasets and applies the one-sided
95% Wilson lower bound ≥ 0.995 — the minimum passing count is
**999/1000** (tested: 999 passes, 998 and 995 fail; `1/1` and any
other sample size refuse). The frozen dataset families now cycle
stake-ordinary / equivalence / pilot-unequal-cells / stake-fork, so
the gate represents every reduced-replicate scenario family it
authorizes (D1–D5). The deterministic 10,000-replicate equivalence
check now exists (`run_deterministic_equivalence_set`): six constant
datasets with analytically forced decisions, exact match required,
runs (and must pass) before anything else in the tranche command — and
it already caught a real subtlety: at the exact ±0.10 boundary the
strict-band rule makes non-equivalence conclusively decidable with a
degenerate interval, so the analytically correct decision is `fail`,
not `unresolved`; the frozen set encodes that.

**4. Cluster-level variance — corrected.** `_tp_rows` draws ONE
cluster-level two-point value and carries it through all three
renderer rows (perfect renderer correlation): the cluster-mean SD now
equals the declared σ exactly (tested at σ = 0.75: sample SD ≈ 0.75,
rows identical across renderers). D1 now actually tests its declared
case.

**5. Undefined-replicate equivalence — corrected.**
`paired_cluster_bootstrap` takes a `gate` kind; adverse replicates
contribute −∞ (lower-bound gate), +∞ (upper-bound gate), or the
adverse endpoint ON EACH SIDE for equivalence (LCB = −∞, UCB = +∞ —
tested), with `equivalence_decision` returning `inconclusive` on the
widened interval rather than crashing. Eligibility is modeled
directly: NaN rows are ineligible; a fully ineligible cluster stays in
the sampling population but carries no observations; the tested probe
is the intended one — a NONEMPTY population whose bootstrap replicate
draws zero eligible observations.

**6. The narrow command — implemented.** `run_full_tranche()`: one
environment manifest (dirty tree refused) → deterministic equivalence
set (must pass) → worst-case benchmark → A grids → C grid → agreement
gate (must pass) → D scenarios each under the 4×-projection abort →
artifacts persisted to `runs/stage1-validation/`, reloaded and
re-verified through `load_artifact` against the exact registries. B
runs separately on the GPU under the same environment identity;
`aggregate_verdict` joins all four.

## The 256 decision — taken as directed

`REPLAY_COMPLETIONS = 256`; total completions **9,216**; key format,
accounting, validation, tests, reachability fixture (zero counts at
n = 256 now yield `not_demonstrated` and BLOCK — tested through
`aggregate_verdict`), module documentation, GPU budget, and the
analytic calculation (with `O` frozen structurally) are all updated
consistently in code and in 147_f. `demonstrated` is renamed
**`not_ruled_out`** throughout, and 147_f describes B exactly as
directed: a minimally informative early-warning screen that can rule
out feasibility in sufficiently low-frequency cases, may not catch
one-sided collapse (one assignment absent, the other common), with the
576-draw cold-start gate remaining the definitive signal-density
check. The stale 64/2,304 references live only in the preserved
141_f/144_f records; 147_f carries the amended numbers.

## State

147_f + this response are the preregistration of record. Per 145_s,
the next step is a changed-lines review of this commit, then lock and
launch — the frozen order is unchanged (A → C → agreement → D →
B replay → `aggregate_verdict` → the single reviewed confirm/amend
decision, still predicted amend-once on §8.4C power).
