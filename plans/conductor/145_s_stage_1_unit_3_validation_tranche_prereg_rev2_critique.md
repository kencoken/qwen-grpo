## Verdict

Choose **256 completions per observation per prompt**, but do **not lock or execute `144_f` yet**. The statistical design is substantially improved, but several real pipeline paths remain fail-open.

### Blocking findings

1. **Check B is not yet executable or trustworthy end-to-end.**

   `stage1_replay.py` stops at manifest/count helpers. It lacks the actual model/adapter loader, message rendering, seeded singleton generation, parsing/scoring, raw completion artifact, completeness verification, and validated B loader.

   More importantly:

   - `summarize_replay()` accepts partial keys and arbitrary `n`;
   - its Bonferroni population is derived from caller-supplied counts;
   - it averages represented observations directly, which is not equivalent to renderer→latent→equal-cell weighting when eligibility differs by cell;
   - `aggregate_verdict()` accepts an unverified B dictionary—even an empty `directions` mapping can leave `confirm_possible=True`.

2. **A/C/D artifacts are not bound to one authoritative execution.**

   `finalize_artifact()` accepts an arbitrary execution hash, while `load_artifact()` checks only the self-hash, name and key set. The aggregate can therefore combine artifacts from different executions.

   The loaders also permit wrong trial counts and impossible sufficient statistics. For example, counts need not sum to 10,000, and `extra` can overwrite reserved artifact fields.

   Require exact per-artifact schemas, exact trial counts and count identities, plus a validated common `stage1-environment-v2` identity—or an explicit compatibility rule for B’s GPU environment.

3. **The agreement prerequisite does not implement the frozen criterion.**

   `agreement_passes()` currently checks only the observed fraction, accepts arbitrary sample sizes, and even `1/1` passes. Rev2 freezes an exact 1,000-dataset gate using a one-sided Wilson lower bound ≥0.995. That criterion requires at least **999/1,000**, not 995/1,000.

   The agreement datasets also cover only ordinary stake decisions, yet their result authorizes reduced replicates for stake, equivalence and unequal-cell scenarios. The frozen set should represent D1–D5, including equivalence and unequal-cell aggregation. The required deterministic 10,000-replicate equivalence check is also still absent.

4. **The D scenarios do not have their documented cluster-level variance.**

   `_tp_rows()` samples the three renderer rows independently with SD `sigma`, after which the bootstrap averages them. The resulting cluster-mean SD is approximately `sigma/√3`, and no renderer correlation is exercised. Thus, for example, D1 is not actually testing the declared cluster-level σ=0.75 case.

   The simplest correction is to draw one cluster-level two-point value and carry it through all renderer rows, explicitly making the renderer dependence perfectly correlated.

5. **Undefined-replicate equivalence remains incorrect.**

   An empty cell currently makes both endpoints `-∞`. For equivalence, the frozen adverse rule is `LCB=-∞, UCB=+∞`. The tests also exercise an entirely empty cell rather than the intended nonempty population whose bootstrap replicate has zero eligible observations.

6. **The promised execution-order and timing enforcement is absent.**

   The component runners return dictionaries, but no narrow command constructs one environment manifest, enforces the frozen order, persists/reloads artifacts, and applies the stated four-times-runtime abort. This can remain simple; it does not require additional architecture.

### The 256 decision

Amend to 256. At 64, `not_demonstrated` is mathematically unreachable even with zero observed target assignments, so Check B cannot perform its intended blocking role. Increasing to 256 costs only about 45–60 minutes and makes the branch meaningfully reachable.

However, describe 256 accurately:

- it is a **minimally informative early-warning screen**;
- it can rule out feasibility in sufficiently low-frequency cases;
- it still may not rule out one-sided collapse where one Code assignment is absent but the other is common;
- therefore the later 576-draw cold-start gate remains the definitive signal-density check.

I would also rename `demonstrated` to `not_ruled_out`: a conservative upper bound above 10% does not demonstrate feasibility.

The amendment must be issued forward and applied consistently to:

- `REPLAY_CONTRACT`;
- total completions: **9,216**;
- exact key/count validation;
- tests and reachability fixture;
- module documentation;
- the stale 64/2,304 references in `144_f`;
- the GPU budget;
- the analytic calculation using the exact frozen definition of `O`.

### What is ready

The 48/24/120/8 registries, A/C formulas, stopping interpretation, one-sided Wilson helpers, D alpha allocations and broad scenario families are now in good shape. The focused tests pass, but they do not cover the fail-open paths above.

After one targeted correction commit, rerun probes showing that empty B, mixed manifests, `1/1` agreement, impossible counts and incomplete replay outputs all refuse. Then perform a changed-lines review and lock—another open-ended audit should not be necessary.