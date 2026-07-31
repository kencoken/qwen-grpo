## Verdict

Do not launch Unit C yet. The execution machinery is sound, but three preregistration/reporting issues should be repaired before reward-bearing results are revealed. This needs a narrow Rev2, not a Unit-B redesign or Unit-A rerun.

### Blocking findings

1. **The reported Q2 eligibility uses the wrong population.**

   [`build_exposure_report()`](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:286) sums `c2_eligible` across every scheduled class, rather than only `q2_composite` rows.

   I reproduced the consequence using the test archive:

   - reported eligibility: **1,080 completions**
   - eligibility on the 160 Q2-composite groups: **0**
   - all 1,080 came from Bridge rows

   This can invert the checkpoint-zero Q2 interpretation and contaminate P0 sizing.

   Restrict the Q2 starting-condition statistic to Q2 composites and report `math_code → w3` and `fork_join → w2` separately, including ModelAcc, C2 eligibility/optimality, worker-2/worker-3 selections, distinct-latent support, and reward/direct contrasts. Keep the direct-specialist control excluded. Add a regression where non-Q2 eligibility is positive but Q2 eligibility is zero.

2. **Q2 is currently authorized by deterministic schedule delivery alone.**

   Under the anchored verifier, exact schedule delivery is mandatory, so [`q2_schedule_delivered_exactly`](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:355) cannot meaningfully fail on a completed run. Consequently, the decision at [lines 383–388](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:383) does not evaluate the conditional worker-choice opportunity required by `269_s`, and the signed Q2-fail → maximum-Q1-only branch is unreachable.

   Zero C2 eligibility may still be a valid hierarchical-unlocking starting condition. Before launch, choose explicitly between:

   - a measurable cold-start Q2 support gate with the Q1-only fallback; or
   - an amendment saying the null-capable unlocking experiment is authorized without a cold-start Q2 gate.

   Either is defensible. What should change is calling schedule delivery itself empirical Q2 validation.

3. **The promised stratified controls and sizing rule are absent.**

   `275_f` promises renderer/subtype-stratified yields, while the report only stores the set of renderers represented among successful Q1 groups. It has no renderer denominators, no subtype results, no public-feature shortcut control, and only a total Anchor count rather than sampled Anchor/stability behaviour.

   This is especially important because renderer-stratified reporting was the explicit replacement for the renderer gate in `274_f`. Add raw-denominator reporting for:

   - Bridge/Q1 by cell × renderer and cell × subtype;
   - Q2 metrics by direction × renderer/subtype;
   - Anchor coverage and stability outcomes;
   - the registered cell + renderer + subtype/public-feature controls.

   Separately, the reviewed lifecycle said Unit C would determine P0 duration through a preregistered rule. The freeze currently says measured rates will become later “sizing inputs” without defining their mapping to updates. Either freeze that deterministic mapping now or explicitly amend the lifecycle to permit a separately reviewed, outcome-informed development sizing decision.

## What checked out

- Full suite: **1,002 passed under warnings-as-errors**.
- Worktree and changed-range diff checks are clean.
- Config, freeze and identity hashes reproduce exactly.
- The schedule rederives as **157 × 5 = 785 groups / 6,280 completions**.
- The real Step-6 archive confirms the one-group-per-optimizer-step accounting assumption.
- Q1 implements the correct event and requires all four cells plus two distinct latents.
- No comparator reselection is reachable.
- Zero-update equality, environment/identity anchoring, trace authentication and abort/complete lifecycle are strong.
- The 1.25-hour ceiling is prospective, enforced, and adequately supported.

After the three targeted repairs, regenerate the freeze/identity hashes and perform a narrow changed-lines review. Unit C should then be ready to launch.