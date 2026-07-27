# 204_s — Routing-training development-track launch-plan review

## High-level framing change

The development track should be **adaptively sequenced and locally
frozen**.

“Adaptive” means that an observed run may legitimately motivate the
next question, prompt, mixture, group size, learning rate, training
duration or checkpoint continuation. This is the purpose of a
development programme: the empirical behaviour is not yet understood
well enough to specify every useful branch in advance.

“Locally frozen” means that each concrete launch is specified before
it runs. Its question, source/configuration identity, cohort, model,
prompt, sampling parameters, training exposure, evaluation schedule,
seed, telemetry and operational budget are reviewed and content-hashed
before the first relevant sample or optimizer update. Results may
motivate a later launch, but may not silently alter the launch already
underway.

This separates two ideas which `191_f` currently conflates:

1. a **finite authorization**, which every probe, run or continuation
   must have; and
2. a **finite research programme**, which need not be fully bounded
   today.

There should be no permanently fixed number of development tranches.
There should also be no unlimited tranche authorization. Work proceeds
in finite development cycles, each with an explicit cumulative resource
envelope and a mandatory synthesis/review before renewal. A provision
such as six full-run equivalents can be a reasonable initial-cycle
budget; it is not a scientific stopping rule, a lifetime cap, or
advance permission to invent six configurations after seeing results.

Reviewer involvement makes adaptation visible and auditable. It does
not turn outcome-informed selection into confirmatory evidence. Every
development run remains development data permanently. A later claim
requires a newly frozen hypothesis and analysis, fresh training seeds,
and disjoint evaluation populations which exclude all development
runs.

This is deliberately not a rigid preregistered adaptive-search
algorithm. Development remains judgement-led. The safeguards are local
freeze, finite spend, complete provenance, an append-only decision
ledger, and a later discovery/confirmation boundary.

This document is a companion to
`203_s_b_diagnostic_execution_record_review.md`. `203_s` records the B
evidence and its immediate scientific interpretation; this document
states how that evidence and the framing above should change the
development-track design in `191_f`.

## 1. What B establishes — and what it does not

The authenticated B diagnostic provides a credible cold-start prior:

- the few-shot prompt produced a 99.74% valid-action rate, mean reward
  about 0.700, and a plug-in prediction that 20.32% of groups of eight
  would have nonzero reward variance;
- the schema-only prompt produced a 52.04% valid-action rate and much
  more apparent variance, but most of that variance was invalid
  reward-0 output versus valid reward-0.5 output;
- under few-shot, exact worker-2/worker-3 contrast appeared with
  plug-in probabilities of about 5.35% on worker-2-favoured rows and
  1.12% on the worker-3-favoured row;
- cold-start preferences pointed in the wrong payoff direction in both
  distinct-payoff populations;
- useful reward variation was concentrated in `code_atomic`,
  `fork_join` and `math_code`;
- `lookup_atomic` and `lookup_math` were nearly deterministic and
  correct, while `math_atomic` was nearly deterministic and wrong at
  reward 0.5;
- the few-shot policy was strongly demonstration-shaped (32 distinct
  output strings across 4,608 samples) and strongly renderer-sensitive;
- no systematic direct-answer output or general truncation/runtime
  pathology appeared.

These observations make few-shot the appropriate **P0 baseline**. Its
near-perfect syntax lets P0 study semantic routing rather than mostly
learning the output grammar, while its strong wrong priors create a
meaningful opportunity to observe whether GRPO moves beyond
demonstration retrieval.

B does **not** demonstrate that:

- the new `routing_dev` population has the same action distribution;
- actual grouped GRPO rollouts reproduce iid-singleton plug-in
  predictions;
- group size eight gives adequate exposure under the eventual training
  mixture;
- every cell has an accessible reward-improving action at cold start;
- a particular update count, wall time, learning rate or mixture is
  sufficient;
- GRPO will learn routing, reverse the worker preference, generalize
  across renderers, or avoid collapse;
- the 4090 can train a proposed group size/configuration merely because
  it completed the B inference diagnostic.

The old 20% variance floor should therefore not be read as a passed
training-feasibility gate. The B estimate is almost exactly on that
arbitrary boundary, is averaged across radically different cells, and
comes from a different support and sampling path.

## 2. The next executable tranche: a zero-update grouped probe

Before P0, run a separately reviewed, finite **zero-update grouped
probe** through the actual training rollout path.

The probe should use:

- new `routing_dev` identities;
- the exact proposed P0 conductor model and frozen few-shot prompt;
- the real renderer, parser, semantic-assignment, payoff-surface,
  reward, group-construction and cache paths;
- group size eight initially;
- an exact, renderer-crossed cohort whose composition and seeds are
  frozen before execution;
- no optimizer update and no model mutation.

It should report, per cell, renderer and payoff direction:

1. parse and full-schema validity;
2. reward-level frequencies;
3. zero-variance groups split into all-0, all-0.5 and all-1;
4. groups containing invalid-versus-valid-format contrast;
5. groups containing valid reward-0.5 versus reward-1 semantic
   contrast;
6. groups containing the exact payoff-distinct worker-2 and worker-3
   alternatives;
7. per-worker and per-assignment frequencies, routing entropy and
   repeated-output concentration;
8. group construction, cache, worker-execution and infrastructure
   telemetry.

The three contrast notions must remain separate. Exact worker-2 versus
worker-3 co-sampling is the cleanest model-selection contrast, but it is
not the only semantic gradient: a reward-1 action can be reinforced
against another valid reward-0.5 assignment even when the exact paired
alternative is absent.

The grouped probe is a development tranche in its own right. Its
results may inform the subsequent P0 configuration, but P0 must then
receive a new local freeze. Do not describe the probe and P0 as one
preregistered experiment if P0's group size, mixture or exposure is
chosen after inspecting the probe.

Infrastructure integrity and exact accounting are hard gates for the
probe. The measured gradient/exposure quantities are evidence for the
P0 design, not arbitrary pass/fail thresholds.

## 3. Cohort and mixture design

`191_f` should no longer defer the mixture to an unspecified launch
configuration. The grouped-probe plan must define its exact cohort, and
the later P0 launch record must define its exact training and
evaluation cohorts.

The development data should have at least two clearly separated roles:

- a **contrast-aware training/development population**, permitted to
  enrich rare task/payoff directions so that the learning mechanism is
  actually exercised; and
- a **natural-mixture evaluation population**, used to show what the
  enriched curriculum does under the intended task distribution.

The contrast-aware population should:

- include all task cells;
- include enough Code-family observations favouring worker 2 and
  worker 3 for both directions to receive deliberate exposure;
- cross or balance renderers so that a renderer token cannot silently
  stand in for the routing decision;
- retain tied Code rows as a separate category rather than treating
  them as direction-bearing;
- preserve latent/template separation between training and evaluation;
- bind every observation to the exact payoff surface used for reward.

Enrichment is a legitimate development curriculum, not evidence that
the natural task distribution contains the same signal. Accordingly,
all reports must show enriched-training and natural-mixture evaluation
results separately.

The role of `routing_dev_holdout` also needs sharper wording. If its
results influence between-run choices, it is an adaptive development
validation set, not a pristine holdout. Either label it accordingly and
retire/rotate it by development cycle, or add a cycle-end holdout which
is not consulted during within-cycle iteration. Neither population may
later become confirmatory data.

## 4. Online telemetry and continuation decisions

Pooled mean reward and pooled reward variance are inadequate. B showed
that identical aggregate movement can correspond to formatting repair,
useful semantic routing, convergence, a wrong deterministic basin, or a
renderer shortcut.

Online and checkpoint reports should include:

- parse rate and full-schema valid-action rate;
- invalid/valid-format contrast rate;
- valid 0.5/1 semantic-contrast rate;
- exact worker-2/worker-3 direct-contrast rate;
- zero-variance groups split by their constant reward level;
- mean reward and reward-level frequencies;
- per-worker, per-assignment and routing-entropy trajectories;
- the above by cell, renderer and payoff direction;
- cache/infrastructure accounting and complete workflow traces;
- natural-mixture evaluation alongside any contrast-enriched training
  view.

Co-sampling and nonzero variance should be treated as **early exposure
diagnostics**, not final success criteria. If learning converges to the
favoured route, reward variance and direct co-sampling should decline.
An all-reward-1 group is successful convergence; an all-reward-0.5
group may be a stuck policy. A final-third requirement such as “at
least 20% nonzero variance” can therefore penalize success while hiding
failure.

The existing 90% validity threshold may remain a conspicuous
engineering warning because few-shot starts near 100%, but it should
not masquerade as a scientific learning threshold. Fail-closed
infrastructure/accounting violations may stop a run automatically.
Scientific continuation should be a reviewed judgement based on the
full trajectory and stratified evidence.

## 5. Prompt policy

Use the frozen few-shot prompt for P0. Do not modify it in response to B
before the baseline: its strong demonstration prior is one of the
phenomena P0 is intended to study.

Keep the parser strict. Quoted worker IDs and wrong action counts are
invalid actions, not near-misses to be silently repaired.

A later, bounded prompt candidate should minimally repair the
schema-only prompt by stating only that:

- worker IDs are JSON integers; and
- there is exactly one ID per listed step.

That candidate directly targets the observed format defect without
supplying worker-routing examples. It should be content-hashed and
launched as a separately frozen development comparison. It should not
be selected retrospectively as though it had been part of P0.

Prompt variants should be logged before first use with their exact
bytes and motivation. A finite prompt budget can be retained as an
initial-cycle resource control, but not as a scientifically meaningful
lifetime maximum.

## 6. Group size as a bounded development lever

Retain group size eight for the baseline probe and, unless the new
cohort evidence clearly makes the rare direction effectively absent,
for P0. This preserves the simplest comparison with the existing
GRPO setup.

The B plug-in calculations give useful priors:

| group size | worker-2-favoured exact contrast | worker-3-favoured exact contrast |
|---:|---:|---:|
| 8 | 5.35% | 1.12% |
| 16 | about 11.5% | about 3.8% |
| 32 | about 21.6% | about 10.2% |

These quantities were correctly formed by computing the nonlinear
probability per observation/prompt before aggregation. They do not
replace the real grouped probe, and the exact direct contrast should
not be confused with all available semantic gradient.

Group 16 and 32 are reasonable later configurations if exposure is too
thin. Each costs approximately 2×/4× conductor generation relative to
group eight and may change training memory and throughput. Before
freezing either for a training run, execute a tightly budgeted
engineering smoke through the actual training path on the 4090. Change
one major lever at a time where practical so that the resulting
training dynamics remain interpretable.

## 7. Replace arbitrary update limits with exposure-derived budgets

Remove the universal “300 optimizer updates or eight GPU-hours”
contract.

Three hundred updates has no stable meaning until the batch structure,
mixture and cohort are fixed. It may correspond to ample exposure in
one design and almost no rare-direction signal in another. B also does
not measure optimizer-step throughput.

For every concrete training launch, freeze:

- the number of rollout groups or sampled prompts per stratum;
- the corresponding maximum optimizer updates;
- the expected informative-group exposure under the grouped-probe
  estimates;
- checkpoint/evaluation cadence;
- the cumulative token/worker-call or equivalent compute accounting;
- an operational wall-time ceiling.

Use a **ten-hour total overnight ceiling** on the RTX 4090 as an
engineering safeguard, not a scientific stopping rule. Stop starting
new updates sufficiently early (for example at 9–9.5 hours) to reserve
time for final evaluation, checkpointing, trace flushing and archival.
The run stops at the earlier of its frozen exposure budget and the
operational ceiling.

If a learning curve is still rising at the budget, that is not a
failure. It may justify a separately reviewed continuation from the
checkpoint.

The initial development cycle should have a finite cumulative budget,
preferably expressed as full-run equivalents, GPU-hours and/or rollout
groups rather than a literal count of process invocations. On
exhaustion, write a synthesis and explicitly renew, change or stop the
cycle. Future cycles are allowed but never authorized retroactively.

## 8. Checkpointing and resumption

Resumability is a launch requirement, not an optional convenience.
Checkpoint artifacts should bind and preserve at least:

- conductor/adapter weights;
- optimizer, scheduler and mixed-precision/scaler state as applicable;
- global optimizer/update and sampling counters;
- CPU and CUDA RNG states;
- dataloader/sampler order and position, or sufficient state to
  reconstruct them exactly;
- training cohort, renderer schedule and configuration identity;
- prompt, worker pool, payoff surface, parser, reward and cache
  identities;
- source/environment digest;
- parent checkpoint, run and segment identifiers.

The consuming resume path must fail closed on an identity mismatch.
Before P0, test checkpoint save/resume through the real training stack,
including a small interrupted-versus-uninterrupted comparison to the
degree determinism permits.

Distinguish:

1. **Engineering resume** — an operational interruption occurs inside
   the already authorized budget and no result-dependent change is
   made. It may continue the same launch from its last valid checkpoint.
2. **Adaptive continuation** — results or the learning curve are
   inspected and additional training is chosen beyond the frozen
   budget. It is a new, reviewed development segment with a new budget,
   linked to the parent checkpoint.

If learning rate, prompt, mixture, group size or another training
parameter changes, label the result a checkpoint **fork**, not a pure
resume.

## 9. Provenance and the development ledger

Retain `191_f`'s provenance and trace requirements, strengthened so
that each probe, training run, resume and fork receives:

- a unique run/segment root;
- an exact source and environment identity;
- configuration, prompt, cohort, payoff-surface and seed hashes;
- complete training/evaluation and checkpoint identities;
- W&B identity;
- cumulative and segment-local resource accounting;
- a complete trace archive and terminal complete/aborted record.

The append-only development ledger should record:

- the question asked;
- the evidence which motivated the launch;
- the exact prelaunch freeze;
- parent run/checkpoint, if any;
- allocated and consumed budget;
- outcome pointer;
- post-run interpretation;
- the next decision and whether it was outcome-informed.

This replaces the appearance of a fixed adaptive algorithm with an
honest, reconstructable chain of development decisions.

## 10. Evidence self-containment

`203_s` correctly identifies that the diagnostic verifier's exact
pinned Stage-0 payoff-surface inputs remain outside the committed
success archive. A clean checkout therefore contains the diagnostic
outputs but not every byte needed to rerun their verification.

Close this as an evidence-preservation task without rerunning B.
Preserve the existing successful content-addressed diagnostic archive
unchanged. Do **not** add files retrospectively and regenerate its
evidence manifest.

Instead create a separate content-addressed companion input bundle
containing:

- the exact original payoff-surface files;
- their existing expected byte hashes;
- a manifest binding them to the B diagnostic manifest and archive;
- restore/path instructions for rerunning the verifier from a clean
  checkout.

Reference that companion from an addendum. This closes portability
without rewriting historical evidence.

## 11. What should remain from `191_f`

The following parts of `191_f` remain sound:

- genuinely new, disjoint development namespaces;
- protection of all formal and prior development identities;
- frozen Stage-0 worker pool and worker prompts;
- the existing parser/reward boundary and infrastructure retry
  accounting;
- deterministic payoff surfaces, request/cache identity and complete
  workflow traces;
- one-seed P0 as the first real training run;
- W&B and GPU/VRAM operational controls;
- the permanent development-data label and fresh-confirmation
  boundary.

The redraft should remove or replace:

- the unspecified P0 mixture;
- the universal 300-update/eight-hour limit;
- the pooled 20% variance and 5% direct-co-sampling gates;
- the implication that up to six adaptively chosen configurations are
  already authorized;
- any ambiguity about whether a holdout is used for development
  selection;
- the absence of an exact checkpoint/resume contract.

## 12. Recommended order

1. Preserve the missing payoff-surface inputs in the separate companion
   evidence bundle.
2. Redraft and review the development charter using `203_s` and this
   document.
3. Implement namespaces, cohort builders, stratified telemetry,
   append-only ledger, checkpoint/resume, provenance and accounting;
   run the full CPU suite.
4. Freeze the exact zero-update grouped-probe cohort/configuration and
   its finite budget.
5. Run and review the grouped probe.
6. Using that development evidence, freeze an exact P0 launch record:
   cohort/mixture, group size, model and prompt, optimizer parameters,
   exposure budget, ten-hour operational ceiling, evaluation/checkpoint
   cadence, seed and provenance.
7. Run one-seed few-shot P0.
8. Review the complete stratified learning dynamics.
9. Stop, resume, fork or launch a bounded next comparison under a new
   local freeze and the remaining development-cycle budget.

The redrafted `191_f` can therefore be both scientifically disciplined
and genuinely useful for discovery. It should act as the development
charter and authorize the infrastructure plus the first grouped probe.
The exact P0 launch freeze should follow the probe rather than being
silently filled in afterward.
