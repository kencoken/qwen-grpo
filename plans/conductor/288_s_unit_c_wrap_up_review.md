## Verdict

I approve the overall route and the proposed sequencing, but `286_f` needs one narrow revision before sign-off. The remaining points are load-bearing rather than review expansion.

### 1. Preserve the C1 verifier, not only its files

The current C1 verifier rederives results through live `p0_mixture` and Unit-C configuration globals. Editing those in place for B2/C2 could make the committed C1 archive unverifiable even though its evidence directory remains untouched.

Require either a versioned B2/C2 path or explicit contract/config parameters, with the V1 path retained unchanged. Reverification of the committed C1 archive should be a hard gate:

- at the B2 freeze;
- immediately before C2 launch;
- after C2 implementation.

### 2. Do not repeat the homogeneous-transport assumption as a validated projection

The B2 arithmetic is correct and the 6/39/39 schedule is mechanically feasible. Under the old homogeneous model, prospective pass probabilities are approximately 1.000/.9993/.9987.

But C1 just demonstrated that homogeneous per-cell transport is unreliable, and `fork_join` was strongly renderer-heterogeneous. Therefore:

- bind the C1 rates to the exact C1 report/archive/closeout hashes and rederive them;
- use the 32/60, 3/60 and 7/150 figures as disclosed, outcome-informed design heuristics;
- do not call the resulting ≥0.9 probabilities validated;
- explicitly supersede the prospective-probability refusal and make fresh C2 the empirical exposure gate.

This is not weakening the empirical gate: C2 still requires ≥2 counted groups from ≥2 latents in every direct-Q1 cell.

### 3. Explicitly amend the sizing population

The existing sizing implementation takes the minimum over all four original critical cells. Unless explicitly changed, `math_atomic = 0` will keep sizing non-derivable even after C2 passes.

Freeze:

- sizing cells = `code_atomic`, `fork_join`, `math_code`;
- sizing rates = authenticated C2 measured rates;
- target remains 100 counted groups per direct-Q1 cell;
- `math_atomic` is excluded from the minimum;
- the arithmetic and cap formula otherwise remain unchanged;
- C2 persists the derivation inputs and result.

At the projected slow-cell rate of approximately 1.82 per epoch, the nominal target is 55 epochs/8,635 groups—about 10.74 hours even at C1’s beta-zero throughput, before reserve and beta overhead. The capped, explicitly under-target branch should therefore be described as expected, not merely possible.

### 4. Preserve or explicitly supersede the Q2 decision matrix

`286_f` currently makes any C2 gate failure a stop. The frozen C1 rule instead allowed:

- Q1 fail → stop;
- Q1 pass + Q2 pass → Q1+Q2 scope;
- Q1 pass + Q2 fail → maximum scope becomes Q1-only, with the later P0 freeze deciding whether launch remains worthwhile.

I recommend retaining that matrix. If Q2 is now intended to be mandatory, that is defensible, but it must be an explicit prospective supersession.

Also distinguish a scientific gate failure from an infrastructure abort. An abort produces no scientific outcome and follows the existing repair/relaunch protocol; it should not consume the “no third scientific iteration” branch.

### 5. Make the sentinel estimand executable

“First non-`[0]` action” is insufficient: `[2]` or `[3]` is different but is not Math unlocking. Record `math_atomic` in a separate training-exposed-sentinel block with:

- worker-1 selections/completions;
- reward-1 completions;
- reward-varying groups;
- Q1-counted groups;
- first occurrence/update for each;
- checkpoint and evaluation trajectories.

Exclude it mechanically from the direct-Q1 gate, sizing minimum, authorization decision and headline Q1 aggregates. Continue to describe it as training-exposed—not held out—because its Anchor groups can begin self-reinforcing after transfer.

### 6. Repeat the trainer-path invalidation audit

Before C2 freezes, repeat the existing audit over rollout generation, sampling/grouping, parsing, reward and trainer construction. Schedule/report-only changes should pass mechanically; any material trainer-path change requires smoke/revalidation rather than silently inheriting C1’s validation.

Smaller corrections:

- Change “added multiplicity would buy identical groups” to “would be expected mostly to buy identical groups and is not supported as a remedy.”
- Qualify selection as “independent of C1 rollout outcomes within the already payoff-surface-informed eligible pools.”
- Use approximately 0.98–1.0 GPU-hours as the C2 expectation, reflecting C1’s measured runtime.
- Put the `282_f` corrections into a dedicated immutable erratum/closure record rather than relying on an iterative plan as the durable erratum.
- Omit the explanation that 24,079 MiB came from `nvidia-smi` unless that observation is retained; the authenticated archive only proves the admitted figures.

## Contract-spine approach

Yes, I approve the high-level approach and sequencing in `284_s`/`285_f`/`287_f`:

> finish a passing B2/C2 on the validated legacy machinery → implement the spine additively on a separate branch → merge it before val/cycle/beta/P0 freezes.

This cleanly separates the scientific change from the architectural change.

One requirement should be carried into the later detailed `287_f` review: the new spine must reproduce the legacy C2 schedule, classes, multiplicities, estimand counts, gates and decision on the frozen C2 inputs/traces. Merely verifying C2 through untouched legacy code does not prove that P0 will consume the same experiment C2 authorized.

Mechanically, the current commit is documentation-only, the diff is clean, and all 1,002 tests pass under warnings-as-errors. After the targeted `286_f` revision above, I would sign it and proceed to B2.