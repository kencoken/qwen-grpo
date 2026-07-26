# 186_s — Stage-1 attempt-1 disposition and routing-training development pivot

**Status:** draft for review; no authority until accepted. This record is not
a formal aggregate, does not authorize CE1 under the existing plan, and does
not itself authorize a B diagnostic or GRPO launch. Those receive separate
source-frozen plans before execution.

## 1. Decision

Two outcomes are recorded separately.

1. **Physical attempt 1 ended in an infrastructure abort at B.** The CPU
   tranche completed, but the B replay failed on its first generation call
   before producing any completion. B is therefore unmeasured and no formal
   aggregate result exists.
2. **The amended conjunctive design failed its registered D5 screen.**
   Independently of B, D5 exceeded its frozen ceiling. Unit 3 is stopped, the
   amend-once allowance is consumed, and the present plan supplies neither
   global C1 nor global C2 authorization for CE1. This is not re-described as
   a completed `aggregate_amend1_verdict`; it is the reviewed design
   disposition entailed by valid D5 evidence from the interrupted attempt.

The global disposition does not erase component evidence. The next phase
therefore carries a component ledger, not the claim that the whole
pre-construction apparatus yielded no useful information. Ledger entries
are scoped design evidence, not component-level GO decisions or automatic
authorization for reuse.

## 2. Evidence identity and execution state

- Lock: `184_f` at `2aa2332`.
- Execution bundle:
  `9b5f1ab85f26c256897f7619b5386ddd776e00683cc9f800c3e24158635bd195`.
- Immutable abort archive:
  `plans/conductor/evidence/stage1_pre_ce1_amend1_9b5f1ab85f26/`.
- Archive manifest SHA-256:
  `114cf207dd98e8578b814602e109a5261ce2ddf1454d5ace185dd388380d31c1`.
- D artifact SHA-256:
  `3afcd6727baebb5270c10eb92e579ca17e5af3a482085f13c8149163594f9683`.
- CPU tranche: complete in 9,672 seconds.
- B replay: infrastructure-aborted after one second; zero completions.
- Aggregate: absent by construction because verified B evidence is absent.

The original roots and archive remain immutable. Nothing from attempt 1 may
be silently resumed, moved aside and treated as a fresh formal attempt, or
combined with a later diagnostic into the missing aggregate.

## 3. Component evidence ledger

| component | disposition | evidence and scope |
|---|---|---|
| A | **component criterion met** | No registered gated cell failed. The worst gated one-sided Wilson lower bound was 0.98996 against the frozen 0.80 criterion. This supports the registered sample-size power calculation on the specified effect/noise grid. |
| C | **component criterion met** | The amended persistence guard had no hard-path failure on its registered operating-characteristic grid. |
| D1–D4 | **component criteria met in their registered scenarios** | The ordinary/fork sequential-null and ±0.10 equivalence components remained within their frozen operational-error ceilings. |
| D5 | **component criterion failed** | 157/5,000 false passes; one-sided Wilson upper 3.57% exceeded the 3.125% ceiling. The small-sample, heterogeneous, unequal-effective-cell percentile-bootstrap geometry is not validated. |
| D6–D8 | **component criteria met in their registered scenarios** | The amended persistence statistic met the registered calibration screen in the structural, row-dispersed and fork scenarios; D8 also reached both registered branches at both looks. |
| B | **unmeasured** | The runtime path aborted before the first completion. No cold-start/direct-gradient conclusion follows from attempt 1. |
| learned routing | **unmeasured** | No GRPO training has run. There is no evidence yet about learned routing, generalization, collapse, shortcutting or empirical training effect size. |

These ledger values are read-only re-derivations from the immutable archive
using the frozen evaluators. They are not a substitute formal aggregate.

D5 is retained as failed evidence; it is not dropped or renamed. Its
consequence is localized: the current percentile-bootstrap regime is not
validated for D5-like small, heterogeneous, unequal-effective-cell
geometry and is therefore unavailable for the planned pilot claim without
new analysis/sample-size validation. That result is not evidence against the
payoff surface, worker heterogeneity, routing task, C2 behavior, or the
possibility of learning useful orchestration.

The D5 count is unlikely under an exactly nominal 2.5% operational error
rate (`P[K >= 157] ≈ 0.0029`), but it does not by itself prove that the true
error exceeds the 3.125% tolerance. The correct conclusion is that the
registered validation screen failed, not that the method has been shown
catastrophically invalid.

## 4. B repair and separate feasibility diagnostic

The `BatchEncoding` failure is a legitimate implementation defect in a
previously unexecuted runtime path. Correcting broken tensor plumbing is not
a scientific amendment or outcome-driven model/prompt optimization. The
freeze prohibited silent adaptive scientific changes; it did not require a
known-broken driver to remain broken.

Attempt 1 is nevertheless not resumed in place. Before any new B generation:

1. correct the driver;
2. add a regression using the real `BatchEncoding` return shape;
3. run a tiny reward-blind GPU smoke through the real tokenizer/model path,
   using throwaway/OOD input and a nonformal seed, disclosing only
   shape/runtime validity and no routing or reward outcome;
4. preregister a separate diagnostic root, tag, source identity and seed
   domain; and
5. preserve the original formal B seeds for any future confirmatory design.

The diagnostic should retain the frozen model, prompts, request scope,
support and singleton execution unless its own plan explicitly records a
different scoped question. It should report, by prompt, renderer and
observation:

- valid and correct-length action rate;
- worker-2 and worker-3 selection probabilities;
- probability that a group of eight contains both payoff-distinct choices;
- predicted zero-variance-group fraction; and
- expected reward-level diversity.

A separately preregistered repaired B diagnostic may support the scoped
claim that the retained support has cold-start action/reward diversity
compatible with nonzero within-group routing advantage. Actual gradient
availability remains a training-path observation. The diagnostic does not
complete attempt 1, enter its aggregate, restore the unavailable global GO,
or establish generalization beyond that support.

If the diagnostic is claim-bearing rather than descriptive, its plan must
freeze an affirmative lower-bound/group-level feasibility criterion; the
inherited `not_ruled_out` upper-sensitivity label is not evidence of
existence.

Once diagnostic outcomes on the retained support are inspected, that
support is development data. Preserving the original formal seeds does not
restore its blindness; any later confirmatory B claim requires disjoint
support/populations and fresh seeds.

## 5. Routing-training development track

The recommended pivot is a clearly labelled **routing-training development
track**, distinct from the existing plan's unavailable global GO.

It requires the broader newly reviewed plan permitted after the Unit-3 stop,
runs outside CE1, and receives no authorization from the component ledger.

Its launch plan must freeze a development-only namespace, one initial
compute budget and complete execution provenance before the first optimizer
update. It retains deterministic payoff surfaces, request/cache identity,
complete workflow traces, held-out namespaces and worker telemetry.

The initial run is a short, single-seed RTX 4090 pilot; multi-seed or longer
runs are not committed until its descriptive continuation checks pass.

The initial continuation criteria are deliberately engineering/descriptive:

- no infrastructure failure represented as reward;
- acceptable valid-action rate;
- observed reward and routing lift;
- nonzero within-group reward variance; and
- sufficient sampling of payoff-distinct worker choices.

The first real training run is not burdened with the failed D5 inferential
geometry. During development, prompt, mixture, topology, group size,
learning rate and checkpoint choice may be iterated, provided every change,
budget and result is logged. These runs are development data and may not
enter a later confirmatory estimate.

The purpose is to observe the training regime directly: gradient
availability, routing-entropy change, collapse modes, worker specialization,
renderer sensitivity and the scale of any learning effect. Those
observations then define a precise hypothesis and realistic variance/sample
geometry.

If a result becomes worth claiming:

1. freeze the hypothesis, configuration, estimand and analysis;
2. validate that analysis using fresh Monte Carlo seeds and the actually
   relevant sample geometry; and
3. test with fresh GRPO seeds and disjoint evaluation populations, excluding
   every development run.

Heavy bootstrap/calibration work is therefore deferred until a real
learning signal makes its target estimand and geometry concrete. Existing
provenance, trace and held-out-population machinery is retained.

## 6. D5 follow-up

D5 remains useful evidence about where the current analysis is fragile.
Focused post-hoc work may compare larger or equalized per-cell pilot sizes,
studentized or wild-cluster procedures, conservative cellwise bounds, or an
engineering-only pilot followed by inference on a larger disjoint test.
Pooling clusters or weighting cells by their observed sample sizes is not an
inference repair because it changes the frozen equal-cell estimand.

Candidate development may use the observed D5 failure as motivation, but a
future claim-bearing method must be chosen on development simulations and
assessed jointly on preregistered null-size and meaningful-effect power
grids, then pass a fresh sealed validation battery. The method, sample-size
rule and acceptance criterion freeze before that battery. They may not be
selected merely because they reverse the recorded D5 result.

## 7. Methodological posture

The original pre-construction apparatus followed a prospective
registered-report philosophy: validate power, guard behavior and
inferential calibration before model training so the first formal training
experiment could be claim-bearing. That posture was motivated by the many
adaptive choices—prompt, mixture, topology, checkpoint, worker direction and
claim selection—and by the need to prevent outcome-driven redesign.

The routing-training development track adopts a discovery-then-confirmation
philosophy. No GRPO run has completed, empirical effect sizes and variance
are unknown, B's real runtime path had never executed, and D5 demonstrated
that one analysis geometry was specified before sufficient empirical
understanding. Provenance and component validation remain; only the boundary
for model-learning confirmation moves to a later fresh-seed replication.

This track does not inherit the unavailable global GO. A broader future plan
may use each ledger entry as scoped design evidence and must decide what
requires fresh validation; the ledger itself authorizes nothing. The
D5-affected inferential scope remains isolated rather than being silently
discarded.

## 8. Decision fork: formal recovery or development pivot

The following routes are mutually exclusive and must be chosen before any B
diagnostic reveals outcomes on the retained support.

### Route A — formal attempt 2

Choose this only if process completeness is itself valuable. It requires a
new preregistration, lock, attempt id, roots, tags and bundle; the attempt-1
roots/evidence remain untouched; the scientific choices and unexposed seeds
remain unchanged; and A, B, C and D all rerun under the new common identity.
No diagnostic or development exposure occurs first.

Its current incremental decision value is low: B cannot rescue D5's
conjunctive global failure, while unchanged registered CPU streams are
expected to reproduce the existing component results. It would primarily
produce a complete formal aggregate and exercise the recovery machinery,
not provide a route around D5.

### Route B — accept the stop and pivot (**recommended**)

Accept the attempt/global disposition, decline original-plan attempt 2, then
run the separately planned B diagnostic and routing-training development
track. Once diagnostic/development outcomes are exposed, clean recovery
under the original formal design is foreclosed. Any later confirmation is a
broader new plan using fresh/disjoint confirmatory populations and seeds.

## 9. Next actions

1. Review this draft and explicitly choose Route A or Route B.
2. Under the recommended Route B, record acceptance of the attempt/global
   disposition and that original-plan attempt 2 is declined.
3. Draft and review the narrow B repair-and-diagnostic plan.
4. Implement the fix, real-shape regression and reward-blind GPU smoke.
5. Run and archive the separately identified B feasibility diagnostic.
6. Draft the routing-training development-track launch plan with its fixed
   initial budget, namespaces, traces and descriptive continuation rules.
7. Use development results to decide whether a later claim-bearing
   confirmatory design is warranted.
