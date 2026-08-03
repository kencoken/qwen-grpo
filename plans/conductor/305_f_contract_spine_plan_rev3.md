# 305_f — Contract-spine plan REV3 (response to 304_s)

The five precise clarifications, added as clauses to the rev2
design (which otherwise stands as written — 304_s: everything else
satisfactorily closed). The C2 inventory hashes cited below are
verified against the committed evidence.

## 1. The identity dependency graph, frozen (304_s §1)

```
authenticated inputs + C2 oracle
    → P0ScienceContract
    → P0LaunchFreeze
    → P0ExecutionIdentity / launch admission
    → closeout
```

The `P0LaunchFreeze` may contain: intrinsic runtime/model/prompt/
worker fields, the seed, and a COMMIT-INDEPENDENT
attested-environment expectation (the `372f958f…`-style attested
hash). **The execution-manifest hash remains an EXTERNAL launch
argument**; the full environment manifest and all terminal hashes
belong in admission and closeout respectively. No preregistration
artifact may contain a hash that depends on the commit that
introduces it — the cycle is excluded by construction, in this
order.

## 2. The complete, authenticated C2 replay source (304_s §2)

Unit 1 requires ALL of:

- the verified ledger chain CONTAINING closeout `2bf50c1e…`;
- its complete terminal inventory, verified BEFORE replay —
  including `actions.jsonl` `8e705317…`, `exposure_report.json`
  `03152f0e…`, `schedule.json` `c2687919…`, and
  `sample_record.json` `cc42c16b…` (all four verified against the
  committed evidence in this revision);
- the reviewed identity (`7b19aeb9…`) and environment
  (`372f958f…`) anchors;
- the locked extension surface (`ccb1c3e2…`) with a CLEAN-CLONE
  restoration path (never depending on an earlier test having
  populated `runs/`);
- the frozen selection/public disclosure (`c6c08775…`);
- the frozen comparator (`9220c2c7…`);
- the newly materialized pinned-mixture artifact (`135a72bf…`).

**The expected compatibility projection is FROZEN before the new
evaluator is implemented.** The evaluator must NOT call
`unit_c2_sample.build_exposure_report` and must NOT read the
expected report: it reparses completion text and independently
rederives assignments and rewards from the locked surface, then
its output is compared against the pre-frozen projection.

## 3. Machine-encoded operative estimands (304_s §3)

`p0_estimands.py` (the narrower name, adopted) carries VERSIONED
rules with typed parameters:

**Q1** — population: Bridge rows in the three direct-Q1 cells;
counted event: within one group, ≥1 VALID reward-1.0 fully
family-correct completion AND ≥1 VALID reward-0.5 completion of
strictly lower family correctness; historical gate: ≥2 counted
groups from ≥2 latents per cell; sizing basis: the authenticated
13/34/13 counts over five C2 epochs. **Counterexample required in
tests**: a group where generic semantic contrast is TRUE but
Q1-counted is FALSE.

**Q2** — FOUR distinct quantities, never conflated:

- marginal authorization: intended-worker selection among VALID
  q2_composite completions, regardless of upstream correctness;
- eligibility: correct non-Code routing AND a Code worker ∈ {2,3};
- the conditional learning estimand:
  `numerator = C2-optimal completions, denominator = C2-eligible
  completions` — **a zero denominator is `None`/undefined, never
  zero performance**;
- the C2 baselines must reproduce: fork_join `8/152` and
  math_code `0/15` (conditional), SEPARATELY from the marginal
  selections `73` and `108`.

**Semantic counterexample required**: intended-worker selection
with INCORRECT upstream routing counts for marginal support but
NOT for conditional success.

## 4. The complete sentinel contract (304_s §4)

At EVERY P0 checkpoint/evaluation, the sentinel block reports:
worker-1 selections and completions; reward-1.0 completions;
reward-varying groups; sentinel Q1-counted groups; **raw group AND
completion denominators**; the signed first-group AND first-update
fields; and the checkpoint + evaluation trajectories. The
population is BOUND to the exact three-observation sentinel set
(the pinned record's ids). The regression that `[2]`/`[3]` is not
Math unlocking merely for differing from `[0]` is RETAINED.

## 5. Nominal vs capacity epochs, frozen before beta timing (304_s §5)

```
nominal_epochs  = 39                      (the C2-derived size)
capacity_epochs = frozen_cap_formula(...)  (beta smoke + reserve inputs)
launch_epochs   = min(nominal_epochs, capacity_epochs)
```

- `capacity_epochs ≤ 0` → stop for a reviewed amendment;
- `0 < capacity_epochs < 39` → the DISCLOSED under-target branch;
- `capacity_epochs ≥ 39` → run exactly 39; **spare capacity does
  not authorize extra training**.

Every cap input and all three values are PERSISTED in the
`P0LaunchFreeze`.

## 6. Unchanged from rev2

Forward-only migration and legacy preservation (the four modules as
compatibility oracle, C1+C2 verifiers as standing gates); the
two-artifact split with terminal hashes in closeouts; the exact C2
parity list with its sensitivity regressions (migration oracle, not
a gate); the strict pinned-schedule loader (no general scheduler,
no rate engine); the distinct Q2 quantities principle (now
machine-encoded per §3); machine-readable scope + the 301_f
trajectory obligations; deep immutability with external expected-
hash authentication; the moderated documentation claim; the
implementation sequence, per-unit gates, source-digest note, and
merge criteria.

## 7. Next

Narrow changed-lines review of this rev3 (304_s closing) →
sign-off → **Unit 1**: the schema, the pinned-mixture artifact
(materialized once, committed, double-bound), and the FROZEN C2
compatibility projection with its authenticated replay source
(§2).
