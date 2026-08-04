# 303_f — Contract-spine plan REV2 (the focused successor design; response to 302_s)

287_f remains the rationale; THIS document is the design to sign
before implementation commits. It incorporates all eight 302_s
amendments and the 300_s/301_f obligations, and it is the first
document of the `conductor_spine` branch. Smaller and strictly
forward-only, per the review.

## 1. Strictly P0-forward (302_s §1)

- **No retrofits.** `p0_mixture.py`, `p0_mixture_v2.py`,
  `unit_c_sample.py`, `unit_c2_sample.py` are NOT touched — they
  are the historical compatibility oracle, and every spine unit
  runs their C1 and C2 verifiers as a standing gate. The new
  definitions are canonical for P0-FORWARD work only.
- **Names keep their meanings**: `bridge_eligible` is a
  SURFACE-LEVEL schedule-feasibility predicate (with the
  tied-worker condition); `q1_counted` is the OBSERVED group
  estimand. They are conceptually distinct, separately named, and
  never merged into "one implementation" of each other. "One
  implementation consumed everywhere" applies WITHIN each concept
  for P0-forward code, not across concepts and not retroactively.

## 2. Two artifacts, not one (302_s §2)

| Artifact | Contents | Frozen when |
|---|---|---|
| **`P0ScienceContract`** | input pins (locks, selection, comparator, C2 evidence); active scope; the ONE-EPOCH schedule identity; estimand definitions (by reference); gate definitions; the registered sizing + cap RULES; required diagnostics (the 301_f trajectory list) | at spine implementation |
| **`P0LaunchFreeze`** | the science-contract hash; val/cycle reviewed outputs; beta-smoke + finalization inputs; the ACTUAL epoch cap from the frozen formula; runtime/seed/environment identities | immediately before P0 |

Terminal output hashes live in CLOSEOUTS only — neither
preregistration artifact carries expected-terminal identities (no
circular hashes). The precursor val/cycle/beta units keep their own
small freezes; the launch freeze pins their reviewed outputs.

## 3. Exact C2 equivalence — the migration oracle (302_s §3; 288_s/300_s)

The spine independently rederives a **canonical scientific
projection** from the RAW committed C2 trace, the locked extension
surface, and the frozen comparator, and must reproduce EXACTLY:

- the ordered 157-row epoch and the 785-row C2 schedule;
- class assignments, multiplicities, populations, sentinel IDs;
- population draws: Anchor 75, Bridge 420, direct control 25,
  goal-first control 90, Q2 160, sentinel 15;
- complete Q1 counts, denominators, latent IDs, renderer coverage,
  and gate outcomes;
- complete Q2 blocks, the target-selection gate, and all
  sufficient statistics;
- the direct-control block and the full strata;
- sentinel counts and every first-occurrence field;
- nominal sizing: 39 epochs / 6,123 groups;
- 662 zero-variance groups and 38 invalid completions;
- the exact authorization decision.

Excluded: only identity fields expected to change under new source
(config/source digests). **Sensitivity regressions** prove the
comparison bites: a row reorder, a population substitution, and an
action alteration must each break equivalence. The fixture is an
outcome-informed MIGRATION ORACLE — never a new scientific gate,
never a source of design choices.

## 4. No general scheduler; the pinned artifact is the schedule (302_s §4)

1. Materialize the complete legacy B2 mixture record ONCE from its
   authenticated inputs (through the legacy builder, unchanged).
2. Commit it; bind BOTH its file hash and its self-hash
   (`135a72bf…`).
3. `p0_schedule.py` is a STRICT LOADER/VALIDATOR of that artifact —
   no cohort-building framework, no re-derivation logic beyond
   validation against the pins.
4. The `P0LaunchFreeze` specifies how many complete epochs execute.

No per-latent/per-stratum rate ENGINE: the transport lesson is
preserved as heterogeneous DIAGNOSTICS and the prohibition on
homogeneous claims; P0 sizing remains the registered calculation
over the three C2 cell counts (13/34/13) and the EXACT existing cap
formula.

## 5. The Q2 quantities are distinct estimands (302_s §5)

`estimands.py` names them separately:

- checkpoint-zero **marginal-support authorization** (the
  historical cold-start gate: ≥8 target-worker selections from ≥2
  latents among VALID `q2_composite` completions, regardless of
  upstream correctness — it must never silently become the
  conditional learning estimand);
- **C2 eligibility**;
- **target-worker choice CONDITIONAL on eligibility** (the P0
  learning estimand);
- **optimal completions**;
- **direct contrast**; **semantic contrast**.

## 6. Scope and trajectory obligations, machine-readable (302_s §6; 301_f)

The `P0ScienceContract` encodes: Q1-direct = {`code_atomic`,
`fork_join`, `math_code`}; Q2 = coarse, cell-correlated
hierarchical unlocking; Q3 = OUT OF SCOPE; `math_atomic` =
training-exposed sentinel (not held out), excluded from Q1 gates,
sizing, authorization, and headline Q1 aggregates. Required P0
diagnostics (raw numerators AND denominators): Q1 counted exposure
by cell; Q2 eligibility, optimality, and target choice conditional
on eligibility; direct + semantic contrast groups; sentinel first
occurrences (group + update); zero-variance and invalid-completion
rates — with the materially asymmetric fork-vs-math starting
conditions carried as context.

## 7. Real immutability and real authentication (302_s §7)

Nested FROZEN dataclasses with tuples (no shallowly mutable
dicts/lists), canonical serialization, an explicit
`schema_version`, and a strict persisted loader. **The consuming
command receives an externally reviewed expected hash — a
self-hash alone is never authentication.** Historical supersession
prose lives in the GENERATED traceability appendix; only active
executable rules and identity-bearing provenance enter the
science-contract hash.

## 8. The documentation claim, moderated (302_s §8)

Generated freeze tables make prose/number divergence
**mechanically detectable for generated numerical fields** — not
"structurally impossible." Independent invariants and human review
remain necessary and remain in the process.

## 9. Implementation sequence (302_s, adopted; one review per unit)

1. Freeze the schema, the pinned-mixture artifact, and the exact
   C2 compatibility projection.
2. Implement `p0_contract.py` and the strict schedule loader.
3. Implement the P0-forward estimands and prove exact C2 replay
   equivalence (with the §3 sensitivity regressions).
4. Add only the registered sizing/cap arithmetic and the generated
   freeze tables.
5. Integrate the first real consumer; construct the
   `P0LaunchFreeze` only after the val/cycle/beta inputs exist.

Per-unit gates: the legacy C1 AND C2 verifiers run in every unit's
test set, plus that unit's focused equivalence tests. **Source
digest note**: adding routing files intentionally changes the
current source digest; historical identity remains established by
the archived manifests and signed commits — old manifests are
NEVER regenerated at the new HEAD.

## 10. Branch and merge (from 287_f, unchanged)

Work on `conductor_spine` (this branch); merge to
`conductor_stage1` gated on: full suite green under `-W error`;
every committed archive reverifying; the §3 equivalence oracle
passing; the traceability appendix reviewed; reviewer sign-off.
After merge: `routing_dev_val`, cycle/`R_cycle`, the beta smoke,
and the `P0LaunchFreeze` — all built against the
`P0ScienceContract` — then checkpoint-zero eval and P0.

## 11. Next

Reviewer sign-off on THIS design → implementation unit 1 (§9).
