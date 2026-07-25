# 158_s — Stage-1 Unit 3 amend-once plan

## Status

**Draft for review. Nothing in this document authorizes execution.**

This is the single outcome-driven, pre-construction amendment permitted by
`132_s_stage_1_2_four_worker_redraft_rev2.md` §8.4, approved through
`133_f`. It responds jointly to the two failures recorded by
`157_f_stage_1_unit_3_tranche_outcome.md`:

1. the old-answer-persistence design had inadequate power at a true 5%
   persistence rate; and
2. the 2,000-inner-replicate D approximation failed its frozen agreement
   gate.

`130_s` was an unfrozen first draft and has no separate operative authority.
The concrete executed preregistration was
`153_f_stage_1_unit_3_validation_tranche_prereg_rev5.md`, SHA-256
`235acb78d9b875999ab90ca50a37e9fbe4c208fa2fa92a285c3229ec01748572`,
locked by `156_f` and executed at clean commit `da8424b`. The resulting
execution identity was
`ae26ba5d3ab951ce0a898fcd14b055be144b3a8d642cc3a80e38c433c53d24b1`.

Approval of the final successor to this draft consumes the one §8.4
amendment. The amended validation run may then either confirm the amended
design or stop. It may not trigger another in-tranche adjustment. A stopped
amended run could be followed only by a broader newly reviewed design plan,
not by another attempt to tune this tranche.

No construction registration, construction reveal, qualification,
`policy_dev`, cold start, or training may begin until:

1. this amendment is complete and reviewed;
2. its implementation passes changed-lines review;
3. the amended tranche is separately locked;
4. the amended A/C/D/B evidence is complete under one fresh execution
   identity; and
5. the reviewed terminal decision authorizes CE1.

## 1. Findings of record

The original run was valid and stopped at the correct boundary. It was a
scientific fail-closed stop, not an infrastructure failure.

- The deterministic six-case prerequisite matched exactly.
- All eight gated position cells and all four gated router cells passed.
  The worst gated result was the fork position case at 9,432/10,000,
  one-sided Wilson lower bound 0.9393 against the required 0.80.
- At the applicable terminal eligibility floors, zero persistence passed
  10,000/10,000 for both schedules.
- At true row persistence `theta=0.05`, the ordinary case passed
  5,418/10,000 (Wilson lower bound 0.5336) and fork passed 1,421/10,000
  (Wilson lower bound 0.1365), both below 0.80.
- The corresponding row-dispersed `theta=0.05` cases passed 0/10,000. This
  is evidence that the old `U_A/L_Q` envelope was not merely finite-sample
  conservative: it was poorly aligned with the full eligible-row ratio when
  persistence was spread across renderer rows.
- Agreement was 998/1,000. Its one-sided Wilson lower bound was
  approximately 0.993975, below the frozen 0.995 requirement. D therefore
  refused to start, and B correctly remained unrun.

The near-zero pass rate at `theta=0.10` is not itself treated as a defect.
Exactly 10% is the scientific boundary of the non-strict upper-bound claim;
a valid upper interval will certify it only on its lower-tail realizations.
The amendment is justified by the failed power requirement at 5%, the
row-dispersed pathology, and the failed reduced-replicate authorization.

`aggregate_verdict` did not run because D and B do not exist. The precise
record is therefore “confirmation was blocked on two preregistered
grounds,” not that a formal aggregate emitted `confirm_possible=false`.

## 2. Preserve the original evidence before implementation

The original files currently live under the ignored
`runs/stage1-validation/` directory on `picome`. A hash in an outcome
document is not a recoverable artifact. Before amendment code is merged,
copy the exact bytes—never regenerate or move them—into:

```text
plans/conductor/evidence/stage1_pre_ce1_v1_ae26ba5d/
```

The archive must contain:

| file | SHA-256 | role |
|---|---|---|
| `env_manifest.json` | `caa666660ee4ebbbf88189771fc8f2322799964f891a1a68fbc1fac639c7b189` | frozen |
| `deterministic_equivalence.json` | `12c48da5e2a57e2f2f9a011cd9acbe3d903ee1aaa306fb52b01f9877a3d940cd` | frozen |
| `benchmark.json` | `1fd09bff0b9fc7476b8a72cca2e4700e9af4c8ba30506aa2185b1b4ba5cf07e3` | frozen |
| `artifact_A.json` | `3ad61310142e1c07062e77afff9da764a5fd4d14c0a6b6456efa8359251eae24` | frozen |
| `artifact_C.json` | `eb4c13912f7f4da1f7f7511fb5021852af39367545964efbf3186b652ea900a7` | frozen |
| `agreement.json` | `21f8267c42bf6546b02736b909df37c11660ceda4e2bc2ea67d38a34f806f492` | frozen |
| `run_record.json` | `6a0b6fac3561f45bf439415b5f84a6a1ca1caf05485b1430f251bc6055a71cf0` | frozen |
| `agreement_diagnostic.txt` | `34ec1caa5b7e0e11ec8d5fe5b7fad1da3a65e85db963144ca894dfd2068eb754` | post-hoc descriptive |

Add a small `evidence_manifest.json` recording byte lengths, these hashes,
the `153_f` preregistration hash, the reviewed executable commit
`75b852ff3bc3bd5671352451bfc60eae161b4370`, lock commit
`da8424bcf27dd59ad4c4e3fc32cb4edef6ba090a`, source digest
`8034178f00d952e4f8952dc511a79ac8fc7e36fa58b46e523d47964a9cc4470b`,
execution identity
`ae26ba5d3ab951ce0a898fcd14b055be144b3a8d642cc3a80e38c433c53d24b1`,
and outcome commit `20507e6d9f4573746813a47349e11cb227a42b9b`.

The disagreement diagnostic was produced after the formal stop. It did not
enter the 998/1,000 gate and may be cited only as descriptive localization of
the two disagreements. Record its regenerating command or script now and
label its directionality retrospective; `157_f` already cited it, so it
cannot be described as prospectively frozen evidence. The frozen agreement
failure itself does not depend on that diagnostic.

Archive verification is an entry gate for the amended lock. The amended
runner must use new run directories and must never overwrite or consume the
old artifacts as current-run inputs.

## 3. Exhaustive amendment table

Anything not named in this table is unchanged.

| component | locked v1 | amendment | mechanically affected checks |
|---|---|---|---|
| Persistence point estimand | full eligible-observation ratio `sum(J_c)/sum(K_c)` | unchanged | none |
| Persistence upper interval | cluster-any CP bound divided by Hoeffding lower eligibility bound | branch-safe cluster-score interval for the full ratio in §4 | C; qualification inference; D6–D8 |
| Ordinary schedule | `(100,300,500)` | unchanged | rerun under fresh identity |
| Fork schedule | `(100,200)` | `(100,500)` | population cap; fork sequential A/C/D checks |
| Overall look alpha spending | `0.05/3` ordinary; `0.05/2` fork | unchanged because the number of looks remains three/two | fork cap rerun |
| Persistence within-look alpha | old zero-event envelope used its look budget directly | pre-split `a_zero=a/2`, `a_ratio=a/2`; variable-eligibility zero branch splits `a_zero` again | C; qualification inference; D6–D8 |
| Persistence conclusive fail | impossible under the old `L=0` envelope | positive-score `G_L>0` can stop a persistence path | C path simulation; qualification stopping; D6–D8 |
| C power distributions | cluster-correlated primary gated; row-dispersed descriptive | both distributions gated on the coupled hard paths | amended C |
| C formal simulation | old exact envelope, 10,000 trials over 120 look cells | exact implementation of the amended asymptotic score/envelope hybrid on coupled paths, 10,000 trials per path and 120 marginal look summaries | C |
| A/C design seed domain | `stage1-validation-v1` | `stage1-validation-amend1-v1` | amended A/C only |
| D bootstrap inner count | 2,000 after agreement authorization | 10,000 production replicates | D1–D5 |
| Agreement gate | 2,000 versus 10,000 authorization | deleted; no reduced-replicate implementation remains | runner, artifacts, aggregate |
| D persistence scenarios | exact old CP/Hoeffding gate | exercise the amended closed-form score/envelope hybrid | D6–D8 |
| B consequence | represented `not_demonstrated` globally blocked confirmation; `unknown` could be accepted later | ex-ante C2/C1 matrix in §7 | aggregate and CE1 claim state |
| Artifact/run identity | validation/replay v1 fixed directories | amend1 tags and non-overwriting directories | loaders, manifests, runners |

This is one amendment package addressing two already observed grounds. It is
not a sequence in which the C result is used to choose D or the D result is
used to revise C.

## 4. Amended persistence interval

### 4.1 Data and target

For one cell, one directed intervention edge, and one registered look:

- `N` is the number of latent clusters;
- `m=3` is the frozen renderer count;
- `K_c in {0,...,m}` is the number of eligible renderer observations in
  cluster `c`;
- `J_c in {0,...,K_c}` is the number retaining the old answer;
- `K=sum_c K_c`, `J=sum_c J_c`;
- `A_c=1[J_c>0]`; and
- `Qbar=sum_c K_c/(mN)`.

The registered-sample full-eligible-observation statistic remains:

```text
p_hat = J / K
```

The repeated-cluster inferential target is:

```text
p_star = E[J_c] / E[K_c]
```

C/D `theta` denotes `p_star`. Neither quantity is
`mean(J_c/K_c | K_c>0)`.

Clusters with `K_c=0` remain in the cluster-score population. Edges and
cells are never pooled. For real qualification surfaces, persist latent
identity and `(J_c,K_c)`. C/D simulation artifacts follow §9.4 and do not
persist every synthetic cluster row.

If observed `K=0`, the gate is unresolved and the cell cannot be admitted at
that look.

### 4.2 Threshold-score identity

Let the scientific boundary be `r=0.10` and define one cluster-level score:

```text
D_c(r) = J_c - r K_c
```

When `E[K_c]>0`:

```text
E[J_c]/E[K_c] <= r  iff  E[D_c(r)] <= 0.
```

The positive-event branch therefore tests the same full eligible-row ratio
without the loose cluster-any surrogate and without a nested bootstrap. It
is a cluster-level score/Fieller construction: renderer dependence is
carried inside `(J_c,K_c)`, and the cluster remains the inferential unit.

### 4.3 Tail allocation across the hybrid

Let the one-look persistence tail allocation be:

```text
a = 0.05 / number_of_registered_looks
```

Thus `a=0.05/3` for ordinary cells and `a=0.05/2` for fork.

Because the procedure selects a zero-event or positive-event branch from
the observed data, divide that tail budget before observing data:

```text
a_zero  = a/2
a_ratio = a/2
```

This Bonferroni split prevents the hybrid from silently spending up to
`2a`. It is deliberately conservative. No branch may borrow unused alpha
from the other.

### 4.4 Zero-event branch

When `J=0`, a plug-in or ordinary asymptotic interval can return a falsely
sharp upper endpoint of zero. Retain the exact rare-event safeguard, now
inside the preallocated `a_zero` budget:

For structurally guaranteed full eligibility (`K_c=m` for every cluster):

```text
L = 0
U = CP_upper(sum A_c, N, tail=a_zero)
```

Otherwise:

```text
U_A = CP_upper(sum A_c, N, tail=a_zero/2)
L_Q = max(0, Qbar - sqrt(log(2/a_zero)/(2N)))
L   = 0
U   = min(1, U_A/L_Q)  if L_Q>0
      +inf              otherwise
```

The branch trigger is exactly `J==0`, not a tunable “small count” rule.

### 4.5 Positive-event branch

When `J>0`, use the actual ratio estimand rather than the cluster-any
surrogate. Compute:

```text
Dbar = mean_c D_c(0.10)
s_D  = sample standard deviation of D_c(0.10), ddof=1
q    = StudentT.ppf(1-a_ratio, df=N-1)
s_K  = sample standard deviation of K_c, ddof=1
denominator_L = mean(K_c) - q s_K/sqrt(N)

G_L = Dbar - q s_D/sqrt(N)
G_U = Dbar + q s_D/sqrt(N)
```

The optimized integer-sufficient-statistic calculation is:

```text
S_D  = S_J - r S_K
S_D2 = S_J2 - 2r S_JK + r^2 S_K2
V_D  = S_D2 - S_D^2/N
s_D^2 = V_D/(N-1)
```

Use NumPy `float64` in exactly that evaluation order. Let
`tol_D=64*eps64*max(1,abs(S_D2),abs(S_D^2/N))`. Clamp `V_D` to zero only
when `-tol_D<=V_D<0`; a more negative or non-finite value is an
infrastructure error. `s_D=0` is valid and gives `G_L=G_U=Dbar`. Compute
`s_K` by the analogous `S_K2-S_K^2/N` rule, tolerance and `ddof=1`.

If `denominator_L<=0`, the ratio interval is `[0,1]` and the gate is
unresolved. This is a fail-closed Fieller denominator check, not a switch
back to the old eligibility envelope.

The score interval is asymptotic rather than exact. Its finite-sample
operating characteristics are therefore load-bearing outputs of C and D.
No renderer row is treated as an independent draw.

For reporting, invert the same score equation over `r in [0,1]`. For each
candidate `r`, recompute `Dbar(r)`, `s_D(r)`, `G_L(r)` and `G_U(r)`, and
define:

```text
C = {r in [0,1] : G_L(r) <= 0 <= G_U(r)}
L_p = inf C
U_p = sup C
```

After the positive-denominator check, `C` is non-empty because it contains
`p_hat`. Find its boundaries outward from `p_hat` with one deterministic
bracket/bisection implementation, 80-iteration count and endpoint
convention; use 0 or 1 where the set reaches that boundary. Do not use an
optimizer-dependent root choice. A deterministic reference test must
establish that `C` is a single interval on every accepted positive-
denominator input and that threshold decisions from `(G_L,G_U)` agree with
the inverted ratio interval at `r=0.10`; otherwise the implementation
refuses rather than selecting a component.

The final successor freezes SciPy's exact `t.ppf` version and arguments,
80 `float64` bisection iterations, inclusive set membership, and
conservative outer-bracket reporting (`L_p` from the lower outside bracket,
`U_p` from the upper outside bracket). Scalar/vectorized endpoint agreement
uses `rtol=0`, `atol=1e-12`; decisions must be bit-identical. The upper
endpoint has the one-sided `a_ratio` guarantee used by the gate and D.
Because both tails are shown, `[L_p,U_p]` must not be labelled a
`1-a_ratio` two-sided interval.

### 4.6 Gate rule and telemetry

Preserve the non-strict 10% upper-bound claim:

```text
zero branch:
  pass       iff U <= 0.10
  fail       never from J=0

positive branch:
  pass       iff denominator_L > 0 and G_U <= 0
  fail       iff denominator_L > 0 and G_L >  0

unresolved   otherwise
```

Report at every look:

- `N`, `m`, `K`, `J`, `Qbar`, `sum A_c`;
- `p_hat`;
- selected branch and positive-branch denominator check;
- zero-branch `L,U` or positive-branch `G_L,G_U,L_p,U_p`;
- tail allocations, Student-t implementation/version and inversion rule;
- full eligible-row, equal-cluster and cluster-any descriptive rates; and
- renderer-conditioned descriptive values.

No descriptive rate may replace `p_hat` or the amended interval.

## 5. Schedules, C validation and the pre-lock compute gate

### 5.1 Schedules

The common qualification schedules become:

```text
ordinary: 100, 300, 500
fork:     100, 500
```

They remain immutable registered prefixes of a maximum population generated
before the first qualification worker call. Ordinary is unchanged. Fork's
terminal look changes globally from 200 to 500; it is not a
persistence-only top-up. All **per-cell sequential** fork gates use the same
two looks and the existing two-look overall alpha spending. The Core and
Core+fork aggregate `Delta_router` hypotheses, and every other contrast
frozen to the first 100 per cell by `132_s` §8.2, remain single tests on
exactly that support and are never recomputed at N=500.

An idealized conditional-binomial sizing calculation—not an acceptance
result—shows that fork 200 is underpowered even for a sharper interval,
whereas fork 500 has useful margin. The score construction is expected to
make the unchanged ordinary 500 cap adequate. The amended C artifact, not
those calculations, decides adequacy.

Every population manifest, expected-count formula, namespace cap check,
worker-call projection and Stage-1 wall-time projection must be recomputed
for the fork cap before lock.

### 5.2 Full sequential C grid

For each schedule, eligibility `{0.60,0.65,0.80,1.00}`, theta
`{0,0.05,0.10}`, and both frozen joint distributions, generate exactly
10,000 fresh-seed **maximum-cap paths**:

```text
2 schedules × 4 eligibilities × 3 theta values × 2 distributions
= 48 paths × 10,000 outer trials.
```

Each path RNG uses §9.3 with the exact key:

```text
C|{schedule}|{eligibility}|{theta}|{distribution}|10000|coupled-path-v1
```

There is no look-size component in that key.

Within each `(schedule, eligibility, theta, distribution, outer_trial)`,
draw one maximum-cap `(J_c,K_c)` vector and evaluate only its immutable
registered prefixes. The generator is prefix-valid by construction: every
prefix has exactly the frozen cumulative eligibility total and joint-
distribution rule. For cluster-correlated paths, each look has exactly
`eligibility*N` full-eligibility clusters, nested by look. For
row-dispersed paths, each look has exactly
`round(eligibility*3*N)` eligible rows distributed as evenly as possible
over its clusters. Construct and independently randomize the incremental
blocks needed to meet each cumulative target; do not generate an N=500
arrangement and hope its prefixes land at the floor, and do not regenerate
looks independently.

Apply §4.6 in order and record the first terminal persistence-gate decision.
An early fail stops the operational path; unresolved expands; unresolved at
cap is non-pass. Marginal decisions may still be computed from the same
coupled prefixes as telemetry. They give the same 120 registered-look
summaries:

```text
(3 ordinary looks + 2 fork looks)
× 4 eligibilities
× 3 theta values
× 2 distributions
= 120 marginal look summaries.
```

Each prefix computes the exact implementation of the amended asymptotic
production statistic from cluster-level sufficient statistics. There is no
inner bootstrap. A vectorized implementation may derive `Dbar` and `s_D`
from
`sum(J)`, `sum(K)`, `sum(J^2)`, `sum(K^2)` and `sum(JK)`, but it must agree
bit-for-bit on decisions and within the §4.5 tolerance on endpoints with a
scalar row-level reference.

Required deterministic tests additionally:

- validate `(J_c,K_c)` support and the full-ratio point estimand;
- validate the branch trigger and alpha arithmetic;
- evaluate the zero-event branch exactly where `theta=0`;
- prove permutation invariance within latent clusters;
- prove renderer rows travel with their latent;
- prove zero-eligible clusters remain in the population;
- prove every maximum-cap draw meets every prefix target;
- prove early pass/fail and cap-unresolved stopping on coupled prefixes;
- prove score sufficient statistics match row-level computation;
- prove the score decision and inverted ratio interval agree at 10%; and
- refuse any missing, duplicated or out-of-grid path or marginal summary.

### 5.3 Acceptance

```text
ordinary hard path: looks=(100,300,500), eligibility=0.65
fork hard path:     looks=(100,500),     eligibility=0.60
```

At each hard path and for both cluster-correlated and row-dispersed
distributions:

- `theta=0`: every trial must first-pass the 10% gate by the cap;
- `theta=0.05`: the one-sided 95% Wilson lower bound on **operational
  persistence-gate pass probability**—first pass by the cap—must be at least
  0.80; early fail and cap-unresolved both count as non-pass; and
- `theta=0.10`: boundary first-pass, first-fail and cap-unresolved rates,
  per-look marginal decisions and branch frequencies are mandatory
  non-gating disclosures. Passing at the non-strict boundary is not
  labelled a false scientific claim; D tests interval undercoverage
  separately.

All other paths and marginal summaries are mandatory disclosures. Any
failure of a hard criterion stops after the amended run; it cannot select
another interval or cap.

### 5.4 Load-bearing timing/reference probe before final lock

Before the final amendment is lockable, the implementation record must:

1. compare the optimized implementation bit-for-bit with a small scalar
   reference over fixed throwaway cases;
2. benchmark the complete vectorized C registry, or a conservative
   throwaway projection of it, without retaining statistical outputs;
3. benchmark the actual 10,000-inner worst-case D path;
4. project the complete amended CPU tranche, including D6–D8; and
5. demonstrate C wall time no greater than 30 minutes and complete amended
   CPU-tranche wall time no greater than 12 hours, with preregistered
   per-component and total abort rules.

The runner freezes these abort rules:

- A: 30 minutes;
- C: 30 minutes;
- each D1–D5 scenario:
  `4 * measured_worst_case_seconds_per_outer * 5,000`, checked every 50
  outer trials;
- D6–D8 combined: 30 minutes; and
- complete CPU tranche: 12 hours.

The measured per-outer literal is persisted by the pre-lock 10,000-inner
benchmark and copied verbatim into the final successor/lock. B retains its
already frozen GPU replay budget and abort behavior.

The timing probe may reveal only timings, shapes and reference agreement.
Its statistical outputs are discarded and may not select a method, cap,
threshold or interval. If the specified hybrid implementation
cannot fit the budget, this draft returns for review before amendment lock;
the runner may not silently reduce replicates or substitute a different
interval.

## 6. D amendment

The reduced-replicate approximation and its agreement authorization are
removed together.

- D has no 2,000-inner path.
- D has no agreement gate in its execution order or aggregate.
- Every D1–D5 scenario whose production statistic uses a bootstrap uses
  exactly 10,000 inner replicates.
- All eight scenarios retain 5,000 frozen outer trials.
- The deterministic equivalence set remains an entry gate.
- Existing DGP families, per-trial seed derivation, truth definitions,
  operational-error definition, allocated alpha and Wilson-upper acceptance
  ceiling remain frozen except where schedules or the persistence statistic
  are mechanically amended here.

Schedule-based D1–D4 use the amended ordinary/fork looks and their unchanged
look-count alpha totals.

D6–D8 are reissued to exercise the amended persistence procedure:

| id | frozen DGP | error at any registered look | allocated operational alpha |
|---|---|---|---:|
| `D6_persist_const_theta10` | ordinary; structural `K_c=3`; cluster-correlated `J_c=3×Bernoulli(0.10)` | reported ratio upper endpoint `<0.10` | `0.05` |
| `D7_persist_rowdispersed_theta10` | ordinary; eligibility `0.65`; row-dispersed Bernoulli persistence `theta=0.10` | reported ratio upper endpoint `<0.10` | `0.05` |
| `D8_persist_hybrid_theta01_fork` | fork; eligibility `0.60`; cluster-correlated persistence `theta=0.01` | reported ratio upper endpoint `<0.01` | `0.05` |

These are undercoverage errors, not “false pass” labels. At the non-strict
boundary, `U_p==theta` covers the truth and is not an error. D8 is designed
to exercise both the zero-event and positive-event branches. Each outer
trial draws one maximum-length vector and carries its immutable prefixes
through every look, using the same prefix-valid eligibility construction as
§5.2. Persist per-look zero/positive/denominator-unresolved branch counts
for D6–D8. D8 must reach both zero and positive branches at each registered
look; otherwise that scenario is unsupported and D does not pass.

For each of D6–D8, the one-sided 95% Wilson upper bound on ever-error must
be no greater than:

```text
0.05 + max(0.005, 0.25*0.05) = 0.0625
```

The inherited scenario-specific ceilings for D1–D5 remain unchanged.

The ids, error labels and alphas in the table are proposed literals, frozen
only by the approved final successor. Its implementation record must bind
their exact DGP code and seeds before output; none may be chosen after
seeing amended results. All eight rows continue to use
`scenario_seed("{id}|{trial}")`.

The measured v1 998/1,000 agreement result remains a historical disclosure.
The post-hoc direction of its two mismatches may motivate the full-count
choice but is not a new acceptance input. The obsolete agreement calculation
is not rerun formally.

## 7. B remains unseen: freeze its consequence now

B keeps its complete scientific and execution contract:

- retained 18-observation Stage-0 support;
- both pinned policy prompts;
- exact model/tokenizer/QLoRA construction;
- 256 singleton completions per observation per prompt, 9,216 total;
- original unexposed completion seed recipe;
- regenerated request hashes and raw-completion recount;
- renderer-within-latent, latent-within-cell and equal-cell weighting;
- direction-specific 10% conservative sensitivity screen; and
- no prompt selection or prompt alteration.

B's result changes only the claim state:

| verified B result | amended consequence |
|---|---|
| directions 2 and 3 both `not_ruled_out` | C2 remains provisional and must still pass construction, qualification and the disjoint cold-start gate |
| either represented direction is `not_demonstrated` | freeze `C2_preCE1_available=false`; C2 is unavailable in v1 and the later Stage-2 branch must carry model NO-GO; continue only through the already approved C1 scale-null path if all other amended checks pass |
| either direction is `unknown` | same conservative C1-only consequence; no post-result risk acceptance |
| malformed, incomplete, foreign-identity or unreproducible evidence | infrastructure abort; neither C1 nor C2 is authorized |

`not_ruled_out` is not renamed “demonstrated.” In the C1-only branch all
four actions remain visible and scale evidence remains descriptive; there
is no hidden worker override, no C2 claim and no semantic-direction top-up.
`ModelGO_tasknode` is ordinarily derived only after qualification; the
pre-CE1 flag does not pretend that derivation has run. It instead makes its
confirmatory C2 outcome unavailable and forces the later model-NO-GO branch.

This is a material amendment to the v1 global-blocking B consequence and
must be implemented in the aggregate decision table, not only described in
prose.

## 8. Everything else remains frozen

The amendment does not change:

- the six cell semantics, reference programs, private/public information
  boundary, renderers, node families, topology or intervention targets;
- the four logical worker treatments and their physical sharing;
- rev10 worker prompts, task-last request contract, tokenizer/checkpoint
  revisions, NF4 settings, greedy singleton worker execution or cache keys;
- parser, tool, scorer, `4^S` action schema, opaque worker ids or
  `0/0.5/1` reward;
- construction-only selection versus qualification-only evaluation;
- difficulty-profile order, controls, visible slice or fixed B1 fitting
  rules;
- full-sample intervention estimands and shared eligible denominator;
- the 10% old-answer-persistence scientific boundary;
- eligibility floors 0.60 fork and 0.65 ordinary;
- the requirement for at least 80% Wilson-lower power at true 5%
  persistence;
- A's effect/sigma grid, point materiality, acceptance threshold and router
  hypotheses;
- D's deterministic prerequisites, 5,000 outer trials, coverage ceiling and
  non-persistence DGP meanings;
- B prompts, support, model, sample count, estimator or screen; or
- any Stage-2 population, prompt candidate, update, checkpoint, pilot or
  test rule.

The schedule/cap change does require mechanical expected-count and cost
updates. It does not authorize new cell types, outcome-driven top-ups or
instance filtering.

## 9. Versioning, seeds and artifact identity

Use exactly these amended identities:

```text
stage1-validation-amend1-v1
stage1-replay-amend1-v1
stage1-tranche-artifact-amend1-v1
```

Old v1 artifacts must fail amended loaders.

### 9.1 One lock-specific execution bundle

Before either CPU or GPU execution, atomically create one canonical
`execution_bundle_manifest.json`. Its self-hash is the amended execution
identity consumed by the CPU runner, B replay, every artifact, every loader
and the aggregate. It binds:

- the final amendment-preregistration file hash;
- the lock-record file hash and the clean Git commit at execution;
- the executable source digest and locked environment-manifest hash;
- the archived-v1 `evidence_manifest.json` hash;
- exact A/C/D/B seed-registry digest;
- exact A/C/D scenario-grid, B support, prompt and request-contract
  digests;
- artifact schema/version tags and exact expected file sets;
- the two run-root paths; and
- the literal physical attempt id `stage1-pre-ce1-amend1-attempt-1`.

This avoids circularly embedding the lock commit in the lock document: the
lock freezes the executable commit and lock-record bytes, while manifest
creation also records the clean current commit that contains that lock.
After atomic creation, the bundle is immutable. A byte difference between
CPU and B provenance refuses; matching only an environment/configuration
hash is insufficient.

The attempt id affects identity and ownership only, never a statistical
seed. If this physical attempt aborts, it is archived as aborted and may not
be recreated or resumed. Any authorized infrastructure recovery requires a
separate reviewed lock/attempt id, without changing scientific choices. A
new attempt must rerun A, C, all D rows and B under its new common bundle;
no artifact from a prior partial attempt can enter the new aggregate.

### 9.2 Run-root ownership

Use exactly these non-overwriting roots:

```text
runs/stage1-validation-amend1/
runs/stage1-replay-amend1/
```

Each root is claimed by atomic directory creation. **Any** pre-existing
path, including an empty directory, refuses. The claimed root records the
common execution-bundle identity before any result file. An aborted amended
run is never deleted or resumed as though it were fresh.

### 9.3 Seed policy

Replace the current single implicit global seed tag with explicit
component-domain inputs to the same frozen derivation:

```text
seed(domain, key)
  = uint64_big_endian(
      SHA256(utf8(domain + U+001F + key))[0:8])

A/C domain = "stage1-validation-amend1-v1"
D/B domain = "stage1-validation-v1"
```

- A and C keys begin with the component literal `A|` or `C|` and use the
  fresh domain because the remedy was selected after inspecting v1 C;
- D1–D5 retain their exact original scenario ids and previously unexposed
  per-trial seeds while increasing the deterministic inner prefix from
  2,000 to 10,000;
- the materially redefined D6–D8 rows use the unchanged D seed-derivation
  recipe with the new frozen ids in §6; no D outcome was exposed, so no
  result-conditioned seed choice is possible;
- B retains its previously unexposed completion seeds; and
- no seed search, redraw or outcome-based seed replacement is permitted.

Before lock, generate and content-address the canonical registry of every
expected seed key and unsigned-64-bit result. Tests must establish that A/C
keys differ from v1, D1–D5 and B equal their frozen v1 results, and all keys
are complete and unique. D6–D8 are bound to their new ids. Neither the
execution attempt id nor machine state enters the registry.

### 9.4 Environment and artifact trust

The final lock binds one clean executable commit, source digest, lockfiles,
environment, exact amendment bytes, archived-parent evidence manifest,
scenario registries, seed recipes, prompts/support and acceptance criteria.
CPU and B evidence must share the same fresh execution identity. No commit,
dependency or source change may occur between them.

The load-validated environment must record the actual Python, NumPy and
SciPy versions used by `PCG64`, Student-t/Beta endpoints and score
inversion, in addition to the existing model/runtime stack. The lock also
binds the numeric dtype, quantile conventions retained by D1–D5, bisection
iteration/endpoint convention and platform/runtime profile used for the
CPU calculation.

Before lock, freeze exact amended artifact schemas and exact key/count
identities. C persists per-path integer outer-trial, first-pass, first-fail
and cap-unresolved counts; per-look marginal pass/fail/unresolved,
zero-branch, positive-branch and denominator-unresolved counts; and the
exact 48-path/120-summary key sets. D persists per-scenario integer
trial/error counts and D6–D8 per-look branch counts. Qualification
persistence later persists `(J_c,K_c)` by cluster. Wilson bounds, score
bounds, branch rates, acceptance statuses and the C1/C2 consequence are
re-derived at load or aggregate rather than trusted as supplied floats. B
remains acceptable only through its pinned support/request hashes and raw-
completion recount, not a structural summary loader. Unknown, extra or
missing keys, impossible count identities and mixed execution identities
refuse.

The amended outcome must preserve every verifying byte, not hashes alone:
manifests, deterministic results, benchmark, A/C/D artifacts, per-scenario
records, B replay manifest, raw completions, B artifact, aggregate output and
run records. Post-hoc diagnostics remain separately labelled.

## 10. Implementation units and review gates

### Unit A — evidence and contract

- archive and verify v1 evidence;
- add amendment constants, schedules, versions and expected registries;
- implement the common execution-bundle manifest and atomic run-root claim;
- split and freeze component seed domains and their registry digest;
- update population/count/cost formulas;
- add the exact persistence branch contract and serialization fields; and
- test old-artifact refusal.

### Unit B — persistence statistic and C runner

- implement scalar-reference and vectorized cluster-score calculations;
- implement the zero-event safeguard and split alpha;
- add deterministic branch/degeneracy/permutation tests;
- implement the complete 48-path/120-summary C registry and its hard-path
  evaluator;
- run only the disclosed timing/reference probes; and
- freeze every implementation literal in the final amendment successor.

No formal C grid runs in this unit.

### Unit C — D and aggregate

- remove the agreement authorization path;
- make 10,000 the only bootstrap inner count for D1–D5;
- update schedule-based scenarios and D6–D8;
- implement the full-count benchmark/deadline;
- implement the B C2/C1 decision matrix; and
- test complete, C1-only, scientific-stop and infrastructure-abort outcomes.

### Unit D — changed-lines review and lock

- run deterministic and full CPU tests under warnings-as-errors;
- verify frozen source/support/prompt hashes and exact registries;
- verify exact artifact schemas, load-time re-derivation and
  cross-artifact bundle binding;
- verify the complete cost projection is at most 12 hours;
- review every change against this amendment;
- issue the final amendment preregistration with no placeholders; and
- create a separate lock record. No formal statistical run occurs before
  that lock.

## 11. Amended execution order

After lock:

1. verify the immutable v1 evidence archive;
2. verify clean amended source/environment identity, validate the seed
   registry, atomically claim absent run roots and create the common
   execution-bundle manifest;
3. run the deterministic equivalence/correctness set under that bundle;
4. run and persist the full-10,000 worst-case benchmark; stop on the frozen
   budget rule;
5. run fresh-seed A and persist/reload artifact A;
6. run fresh-seed amended C and persist/reload artifact C;
7. run all eight D scenarios at the amended production policy, persisting
   each scenario immediately, then persist/reload artifact D;
8. only after CPU completion, run B once on the GPU under the same execution
   identity;
9. verify B from pinned inputs and raw completions;
10. compute and persist the fail-closed aggregate; and
11. copy the exact immutable execution bytes into
    `plans/conductor/evidence/stage1_pre_ce1_amend1_{first12(bundle_sha256)}/`,
    generate an exact-file-set manifest with byte lengths and SHA-256s, and
    verify it byte-for-byte against the run roots; and
12. commit that archive and make the reviewed terminal decision below,
    citing its manifest hash.

The archive includes the common bundle/environment manifests, commands and
logs, deterministic results, benchmark, A/C/D records and artifacts, B
replay manifest, raw B completions, B artifact, aggregate and run records.
`first12` means the first 12 lowercase hexadecimal characters of the
bundle-manifest SHA-256.
An infrastructure abort archives the same exact partial/aborted evidence
before any recovery decision. Post-hoc diagnostics live in a separate
manifest section and are never silently promoted to gate inputs.

Scientific failure in A, C, D or B does not become an infrastructure
exception and does not silently suppress later already-authorized
measurements unless an explicit runtime/budget/identity prerequisite fails.
This ensures the single amended run returns the complete decision vector
rather than creating another information-gathering cycle.

## 12. Terminal decision

| evidence state | decision |
|---|---|
| A, amended C and D pass; B directions 2 and 3 are both `not_ruled_out` | confirm amended design with C2 provisional; proceed to CE1 |
| A, amended C and D pass; B is `not_demonstrated` or `unknown` | confirm amended design for C1 only; freeze C2 unavailable; proceed to CE1 |
| A, amended C or D fails scientifically | stop Unit 3; no second in-tranche amendment |
| deterministic, budget, identity, schema, accounting, request, replay or runtime prerequisite fails | infrastructure abort; no scientific decision and no downstream authorization |

The terminal record must contain exact commands, hashes, sufficient
statistics, bounds, runtime, committed archive-manifest hash and the
resulting C1/C2 claim state. CE1 may use only that recorded state and is not
authorized while amended evidence exists solely under ignored run roots.

## 13. Review choices required before the final successor locks

This draft recommends and provisionally fixes:

1. the branch-safe direct cluster-ratio interval in §4;
2. ordinary `(100,300,500)` and fork `(100,500)`;
3. both cluster-correlated and row-dispersed power as hard C criteria;
4. full 10,000-inner D with no agreement gate;
5. conservative C1-only treatment of B `not_demonstrated` and `unknown`;
   and
6. fresh A/C seeds while retaining the unseen D/B seed recipes.

There are no outcome-dependent numerical placeholders. The complete C grid
uses 10,000 outer trials per coupled path, including non-gating
`theta=0.10` disclosures. The final successor must record the exact
lock-selected Python/NumPy/SciPy versions, source/artifact-schema digests and
the measured benchmark-derived D1–D5 deadline literal. These are
provenance/timing resolutions under already frozen rules, not scientific
choices. The pre-lock timing/reference probe may confirm feasibility or
return the draft for review, but it may not choose another statistic,
schedule, threshold or trial count.

Reviewer sign-off is required on the six choices above and the measured cost
projection. Until then this document remains a draft and authorizes no run.
