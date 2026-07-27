## Verdict

[205_f](https://github.com/kencoken/qwen-grpo/blob/conductor_stage1/plans/conductor/205_f_routing_development_charter.md) is a strong redraft and faithfully incorporates most of 203_s/204_s. The adaptive-but-locally-frozen framing, grouped probe, removal of pooled final-third gates, few-shot P0 policy, strict parser, separate P0 freeze, and development/confirmation boundary are all correct.

I would not sign it completely unchanged, but it needs only a focused revision—not another broad redesign.

## Findings to resolve before sign-off

1. **The payoff-surface construction step is missing from the authorized sequence.**

   New `routing_dev` observations do not yet have precomputed payoff surfaces. Moreover, whether an observation favours worker 2 or 3 is known only after those workers have been executed. This makes §§4–5 circular: the cohort is supposed to contain both directions and be frozen before execution, but direction itself requires prior execution.

   Add a finite, locally frozen support-materialization step before the grouped-probe freeze:

   - freeze an outcome-blind candidate prefix, renderer schedule and search cap;
   - freeze the worker pool, prompts, request/cache profile and complete `4^S` surface contract;
   - materialize and authenticate the surfaces;
   - disclose all screened rows and direction yields;
   - then freeze the grouped-probe cohort against exact surface hashes.

   I recommend making the first grouped probe an outcome-blind, factor-balanced prefix. Any later direction-enriched P0 curriculum can be explicitly outcome-conditioned development adaptation. Surface construction must count against the 60-hour envelope.

2. **“Natural mixture” needs a stable definition before P0.**

   The generator has no intrinsic cross-cell prevalence, so “natural” cannot remain an adjective whose weighting changes between launches. The simplest definition is the existing 130_s target:

   - cells equally weighted;
   - latent clusters equally weighted within cell;
   - renderers equally weighted within latent.

   Freeze this cycle-wide before P0 and keep it unchanged across within-cycle comparisons. Require a checkpoint-zero evaluation on the exact `routing_dev_val` cohort, seeds and decoding configuration subsequently used at checkpoints. B is a prior, not that paired baseline.

   `routing_dev_cycle` should be revealed once at synthesis and then permanently retired. A renewed cycle must allocate fresh identities.

3. **The C1/C2 distinction should be explicit in telemetry.**

   The current format/semantic/direct-contrast decomposition is good, but add:

   - node-level family-correct routing and its lift—C1;
   - conditional worker-2 versus worker-3 selection and incremental lift on Code nodes—C2;
   - payoff-direction and tie strata.

   Define “exact w2/w3 direct contrast” using the existing `stage1_replay.family_correct_variants` pair: assignments identical and family-correct elsewhere, differing only by worker 2 versus 3 at the Code node. Generic per-worker frequencies could otherwise hide family-routing progress while model selection remains unchanged.

4. **Bind P0 to the policy measured by its grouped probe.**

   P0 should retain the probe’s conductor checkpoint, prompt bytes and sampling/generation semantics. Changing any of those requires another grouped probe.

   If P0 changes group size from 8 to 16/32, require either a small zero-update sample at the candidate group size or explicitly label the exposure estimate as an iid extrapolation. A memory/throughput smoke alone does not establish actual co-sampling behaviour.

## Smaller corrections

- Section 10’s resume test should have explicit acceptance:

  - checkpoints occur at complete generation/update boundaries;
  - generated and optimizer-consumed group counters are separate;
  - post-checkpoint rows from an aborted segment remain evidence but are excluded from the resumed trajectory;
  - merged segments have no missing or duplicated groups.

  Add the real GPU interrupted-versus-uninterrupted test explicitly to §14 before P0.

- Check the wall-time deadline before starting each generation batch, not merely before an optimizer update. Reserve finalization time using measured worst-case rollout, evaluation, checkpoint and archive duration. The ten-hour ceiling should remain cumulative across engineering resumes.

- Engineering smokes and standalone GPU evaluations should also be lightweight locally frozen, provenance-bound ledger entries.

- Replace “latent/template separation” with the executable intended contract—probably “latent-disjoint, factor-balanced and renderer-crossed.” The current generator does not provide a genuine unseen-template split, and 130_s explicitly avoids that claim.

- Report raw counts and denominators alongside every exposure rate, plus projected informative-group counts under P0’s proposed budget.

- Namespace caps should be stated as per-cell.

- Correct the schema-failure breakdown: it is **1,768 bad-ID/type/domain failures**—1,767 quoted IDs plus one out-of-domain `[3,4]`—plus 440 wrong lengths and two parse failures, totalling 2,210.

- The companion payoff-surface evidence bundle required by §14 step 1 has not yet landed. It remains a prerequisite to final sign-off, although it requires no B rerun.

The 60-hour cycle and ten-hour per-run posture look reasonable for the 4090; existing group-eight NF4/LoRA evidence leaves substantial VRAM headroom. Once the items above are addressed in a narrow revision or signed erratum, I would approve the charter and proceed to the companion bundle and infrastructure implementation.