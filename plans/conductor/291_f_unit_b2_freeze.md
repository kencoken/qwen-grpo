# 291_f — Unit B2: the amended mixture, implemented + FROZEN (for review)

The 290_f-signed B2, implemented as the VERSIONED module
`tasks/routing/p0_mixture_v2.py` (the V1 path byte-untouched) and
frozen here. CPU-only. Full suite: **1006 passed under `-W error`,
TRUE exit 0**. **The C1-archive hard gate ran at this freeze and
PASSED** (the committed C1 archive reverifies through the untouched
V1 path with its real frozen identities; the gate is also a
permanent regression, order-hardened).

## 1. The B2 schedule (157 rows/epoch; only Bridge moved)

| Class | Rows | vs V1 |
|---|---:|---|
| Q2 composite | 32 (18 w2 : 14 w3) | UNCHANGED |
| direct-specialist control | 5 | UNCHANGED |
| goal_first controls | 18 | UNCHANGED |
| **Bridge** | **84 = ca 6 (2 latents) + fj 39 (13) + mc 39 (13)** | reallocated; `math_atomic` ZERO |
| Anchor | 18 (incl. the 3 sentinel rows) | UNCHANGED |

Selection canonical ascending within the frozen predicate pools —
independent of C1 rollout outcomes within the already
payoff-surface-informed eligible pools. Shuffle seed 20260802.
714 observations screened at zero multiplicity; latent 42 screened.

**The sentinel** is declared in the record: `math_atomic`,
training-exposed, 3 rows/epoch (its latent-0 Anchor rows),
mechanically excluded from {direct-Q1 gate, sizing minimum,
authorization, headline Q1}. Its estimand is the executable
`sentinel_block` (ONE definition for the C2 report and every P0
checkpoint): worker-1 selections/completions, reward-1.0
completions, reward-varying groups, Q1-counted groups, FIRST
occurrence indices for each, with `[2]`/`[3]` explicitly not
counting as Math unlocking (regression-tested, including the
worker-3 non-event and a crafted unlock with firsts recorded).

## 2. Heuristics, supersession, gates (288_s §2 as signed)

The C1 rates are BOUND to the exact C1 evidence
(`exposure_report.json` `3e708f67…`, `sample_record.json`
`7f52e420…`, closeout `9f4661a8…`) and REDERIVED from the archive
at build time (frozen literals 32/60, 3/60, 7/150 must match).
They enter as disclosed, outcome-informed design heuristics —
projected 3.2 / 1.95 / 1.82 counted groups per epoch — and the
record's basis text says NOT validated. **The V1
prospective-probability refusal is EXPLICITLY SUPERSEDED in the
frozen config** (`prospective_probability_refusal.superseded:
true`); nothing gates on projections. The empirical gates are
UNCHANGED in strength and frozen for C2: per direct-Q1 cell ≥2
counted groups from ≥2 latents; the per-direction Q2 cold-start
gate as in V1; the §5 decision matrix per the approved 290_f
(direct-Q1 fail → stop; Q1+Q2 → both; Q1-only on Q2 fail, P0
freeze decides worth).

## 3. Sizing amendment (288_s §3 as signed)

`derive_p0_size_v2`: sizing cells = the three direct-Q1 cells;
rates = authenticated C2 measured counted groups; target 100 per
sizing cell; **the sentinel is excluded from the minimum**
(regression: `math_atomic = 0` no longer blocks derivation);
integer arithmetic and the finalization-aware cap formula
(`derive_p0_cap_v2`) unchanged in form, both re-tested. The capped
under-target branch remains EXPECTED per 290_f.

## 4. Traceability (284_s process, adopted)

| Requirement | Config field | Enforcement | Regression | Artifact field |
|---|---|---|---|---|
| V1 untouched + C1 hard gate | — (versioned module) | `reverify_c1_archive` | `test_b2_freeze_v1_untouched_and_c1_hard_gate` (pristine-pinned) | C1 archive verdict |
| Bridge 6/39/39, sentinel 0 | `quotas.bridge_latents` | build refusal on under-quota | `test_b2_mixture_is_the_290f_schedule` | `class_assignment`, per-cell rows |
| Outcome-independent selection | frozen predicate + ascending order | deterministic builder | same (latent counts 2/13/13) | `record_sha256` rederivation |
| C1 rates as bound heuristics | `c1_evidence`, `c1_rate_heuristics` | `c1_rates_rederived` (sha + equality) | same test | `heuristic_projections` |
| Prospective refusal superseded | `prospective_probability_refusal` | no gate exists on projections | basis-text assertion | `heuristic_projections.basis` |
| Sentinel estimand executable | `sentinel` record block | `sentinel_block` (single definition) | `test_b2_sentinel_block_is_executable` | C2/P0 sentinel blocks |
| Sentinel excluded from sizing | `p0_sizing_rule.sizing_cells` | `derive_p0_size_v2` | `test_b2_sizing_excludes_the_sentinel` | `p0_size_derived` (C2) |
| Q2/controls/anchor unchanged | `quotas.*` (V1 values) | exact-quota refusals | schedule test (class rows) | `class_assignment` |

**Inherited (unchanged):** Q2 composite quotas + per-renderer fj
allocation; direct-specialist control; goal_first controls; anchor
identity subset; constraints (ratio/minimum/P(w3|gf)); latent-42
screening; Q1 counted event; per-direction Q2 gate; cap formula;
10-h operational ceiling. **Superseded (explicit):** the V1
prospective-probability refusal (by fresh-C2 empirical gating);
the V1 four-cell sizing minimum (by the three-cell sizing
population); the V1 `math_atomic` Bridge quota (by the sentinel).

## 5. Frozen identities

- Config:
  `32b04bbf8a3250e55d023debedb7827caf64e9273f0e2b422b126c87e2c8d26e`
- Freeze:
  `023c374b38a71fde3d240504e993692d8b2570ea917eba0c727f5359b611cc15`
- Mixture record (deterministic from locked surface + frozen
  selection):
  `592f1e81b6edb351f2ecf06c809e27243bd9395bd6947c0dc5215b8f20b026e4`
- Inputs: extension lock `ccb1c3e2…`; selection `c6c08775…` (file
  `e0bbb75d…`); C1 evidence `3e708f67…`/`7f52e420…`/closeout
  `9f4661a8…` (= lineage parent).
- V1 identities UNTOUCHED (asserted in tests): `p0_mixture` config
  `92f933e8…`; `unit_c_sample` config `69f73a58…`.

## 6. Next

Reviewer pass on this freeze → C2 freeze (repeat the trainer-path
invalidation audit; the C1 hard gate again immediately before
launch; fresh seed; the B2 schedule `592f1e81…` at 5 epochs;
sentinel block in the report) → C2 run → decision per the 290_f
matrix → the 287_f spine branch.
