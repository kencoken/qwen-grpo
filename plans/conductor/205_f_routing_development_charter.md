# 205_f — Routing-training development charter (rev2 of 191_f)

Redraft of `191_f` under `203_s` (B-evidence reading) and `204_s`
(design review). **Draft — no authority until reviewed.** On
sign-off it supersedes `191_f` and authorizes exactly two things:
the development INFRASTRUCTURE (§14 step 3) and the first
executable tranche, the zero-update grouped probe (§4). The P0
launch freeze follows the probe (§14); it is not pre-filled here.

Every B figure cited below was re-verified this session directly
against the committed `plans/conductor/b_diagnostic_report.json`
(manifest `973e8adc…`): the equal-cell aggregates, the per-cell
decomposition, the group-size extrapolations, and the renderer
splits all reproduce exactly.

## 1. Framing: adaptively sequenced, locally frozen

The development track is **adaptive** in sequence and **frozen**
per launch (204_s):

- **Adaptive**: an observed run may legitimately motivate the next
  question, prompt, mixture, group size, learning rate, duration,
  or checkpoint continuation. The empirical behaviour is not yet
  understood well enough to specify every useful branch in advance.
- **Locally frozen**: each concrete launch — probe, training run,
  continuation, fork — is specified before it runs. Its question,
  source/configuration identity, cohort, model, prompt, sampling
  parameters, training exposure, evaluation schedule, seed,
  telemetry, and operational budget are reviewed and content-hashed
  before the first relevant sample or optimizer update. Results may
  motivate a later launch; they may not silently alter the launch
  underway.

This separates a **finite authorization** (every launch must have
one) from a **finite research programme** (which need not be fully
bounded today). There is no fixed lifetime number of development
tranches, and no unlimited tranche authorization. Work proceeds in
finite **development cycles**:

- **Initial-cycle envelope: 60 RTX-4090 GPU-hours cumulative**
  (≈ six full-run equivalents at the §9 ten-hour ceiling), counting
  ALL development GPU work in the cycle — probes, engineering
  smokes, training runs, evaluations — at measured cost.
- On exhaustion: a written synthesis, then an explicit reviewed
  decision to renew, change, or stop the cycle. Renewal is never
  retroactive; the envelope is a resource control, not a scientific
  stopping rule, and not advance permission to invent
  configurations after seeing results.

Reviewer involvement makes adaptation visible and auditable; it
does not convert outcome-informed selection into confirmatory
evidence. **Every development run is development data permanently.**
A later claim requires a newly frozen hypothesis and analysis,
fresh training seeds, and disjoint evaluation populations excluding
all development runs (186_s §5, unchanged).

Changes from `191_f`, per 204_s §11: removed — the unspecified P0
mixture (§5), the universal 300-update/8-GPU-hour limit (§9), the
pooled 20%-variance and 5%-co-sampling gates (§6), the implication
that six adaptively chosen configurations were pre-authorized (§1),
holdout-role ambiguity (§3), and the missing checkpoint contract
(§10). Retained — everything in §12.

## 2. Adopted B priors — and their limits

Adopted as development priors (203_s, verified against the report):

| quantity (equal-cell) | few-shot | schema-only |
|---|---:|---:|
| valid-action rate | 0.9974 | 0.5204 |
| mean reward | 0.700 | 0.349 |
| nonzero-variance groups (G=8) | 20.32% | 90.66% |
| w2-favoured exact contrast g8 | 5.35% | 0.00% |
| w3-favoured exact contrast g8 | 1.12% | 0.48% |

Per-cell (few-shot): `lookup_atomic` and `lookup_math` are
near-deterministic and CORRECT (reward-1 rates 1.000 / 0.999);
`math_atomic` is near-deterministic and WRONG at reward 0.5 (0.999);
useful variation concentrates in `code_atomic` (zero-variance 0.35),
`fork_join` (0.63), and `math_code` (0.82). Schema-only's variance
is mostly invalid-0 vs valid-0.5 formatting contrast (2,210 schema
failures: 1,767 quoted IDs, 440 wrong action counts, 2 malformed).
The few-shot policy is strongly demonstration-shaped (32 distinct
outputs / 4,608 samples) and strongly renderer-sensitive
(`code_atomic` Code-worker selection ≈ 1% / 58% / 23% under
`bound_var` / `goal_first` / `resource_first`). Cold-start
preferences point AGAINST the payoff direction in both
distinct-payoff populations.

Consequences adopted: few-shot is the P0 baseline prompt; the
parser stays strict; mean reward can improve while whole cells
(`math_atomic`) stay untouched, so telemetry must be stratified;
pooled aggregates are inadequate.

B does NOT demonstrate (204_s §1): that `routing_dev` has the same
action distribution; that real grouped GRPO rollouts reproduce
iid-singleton plug-ins; that group 8 gives adequate exposure under
the eventual mixture; that every cell has an accessible
reward-improving action; that any update count / wall time /
learning rate / mixture suffices; that GRPO will learn routing,
reverse the preference, generalize across renderers, or avoid
collapse; or that the 4090 can train a given configuration because
it completed B inference. The old 20% variance floor is NOT read as
a passed feasibility gate — the B estimate sits on that arbitrary
boundary, averages radically different cells, and comes from a
different support and sampling path.

## 3. Namespaces (three, genuinely new, disjoint from everything)

Added to `NAMESPACE_CONFIG` at implementation:

- `routing_dev` — training/iteration populations; MAY be
  contrast-enriched (§5). Cap 2,000 latent clusters, expansion
  batch 500.
- `routing_dev_val` — **adaptive development validation** (renamed
  from 191_f's `routing_dev_holdout` to say what it is): consulted
  BETWEEN runs to inform development choices; natural mixture only,
  never trained on; retired or rotated at each cycle boundary.
  Cap 500, batch 250.
- `routing_dev_cycle` — **cycle-end holdout**: consulted ONLY at
  cycle synthesis (§1), never during within-cycle iteration; natural
  mixture only, never trained on. Cap 500, batch 250.

Disjointness is BY CONSTRUCTION (namespace string in every latent
identity) from ALL existing identities — `construction`,
`qualification`, `train`, `dev`, `test`, `worker_dev`, `policy_dev`
— and from each other, and is asserted by a test regenerating id
prefixes across all namespaces with zero intersection. `policy_dev`
cohort B 24–47 remains never-reassign and untouched. The 18-obs
B support is development data reserved for descriptive comparison
only; it is never trained on. **None of the three namespaces may
ever become confirmatory data** — a later confirmatory design
draws fresh, disjoint populations.

## 4. First executable tranche: the zero-update grouped probe

Before any P0 freeze, a separately frozen, finite **zero-update
grouped probe** runs through the ACTUAL training rollout path
(204_s §2). The B figures are singleton plug-ins; the probe
measures what real grouped rollouts contain.

Specification (fixed here; the exact cohort/seeds at its freeze):

- new `routing_dev` identities;
- the exact proposed P0 conductor model and the frozen few-shot
  prompt bytes;
- the real renderer, parser, semantic-assignment, payoff-surface,
  reward, group-construction, and cache paths;
- group size 8;
- an exact renderer-crossed cohort whose composition and seeds are
  content-hashed before execution;
- ZERO optimizer updates, zero model mutation;
- operational ceiling 3 GPU-hours (in-loop monotonic deadline,
  partial evidence preserved on abort), charged to the §1 envelope.

Reported per cell × renderer × payoff direction:

1. parse rate and full-schema valid-action rate;
2. reward-level frequencies;
3. zero-variance groups split into all-0 / all-0.5 / all-1;
4. groups containing invalid-vs-valid FORMAT contrast;
5. groups containing valid 0.5-vs-1 SEMANTIC contrast;
6. groups containing the exact payoff-distinct w2/w3 alternatives;
7. per-worker and per-assignment frequencies, routing entropy,
   repeated-output concentration;
8. group-construction, cache, worker-execution, and infrastructure
   telemetry.

The three contrast notions in items 4–6 stay separate throughout
the track: exact w2/w3 co-sampling is the cleanest model-selection
contrast but not the only semantic gradient — a reward-1 action
can be reinforced against a valid reward-0.5 assignment even when
the exact paired alternative is absent.

Hard gates for the probe are infrastructure integrity and exact
accounting ONLY. The measured exposure quantities are evidence for
the P0 design, not pass/fail thresholds. The probe is a development
tranche in its own right: P0's group size, mixture, and exposure
are chosen after inspecting it, so **P0 receives a new local
freeze** and the two are never described as one preregistered
experiment.

## 5. Cohort and mixture design

The development data has two separated roles; all reports show them
separately:

- a **contrast-aware training/development population**
  (`routing_dev`), permitted to enrich rare task/payoff directions
  so the learning mechanism is actually exercised. It must: include
  all task cells; include enough Code-family observations favouring
  worker 2 AND worker 3 for both directions to receive deliberate
  exposure; cross or balance renderers so a renderer token cannot
  stand in for the routing decision; keep tied Code rows a separate
  category, never direction-bearing; preserve latent/template
  separation between training and evaluation; and bind every
  observation to the exact payoff surface used for reward.
- a **natural-mixture evaluation population** (`routing_dev_val`,
  and `routing_dev_cycle` at cycle end), showing what the enriched
  curriculum does under the intended task distribution.

Enrichment is a legitimate development curriculum, not evidence
that the natural distribution contains the same signal. This
charter fixes NO mixture proportions: the grouped-probe freeze
defines its exact cohort; the P0 launch record defines its exact
training and evaluation cohorts.

## 6. Online telemetry and continuation decisions

Pooled mean reward and pooled variance are inadequate (B showed the
same aggregate movement can be formatting repair, semantic routing,
convergence, a wrong deterministic basin, or a renderer shortcut).
Online and checkpoint reports include:

- parse rate and full-schema valid-action rate;
- invalid/valid FORMAT-contrast rate;
- valid 0.5/1 SEMANTIC-contrast rate;
- exact w2/w3 direct-contrast rate;
- zero-variance groups split by constant reward level;
- mean reward and reward-level frequencies;
- per-worker, per-assignment, and routing-entropy trajectories;
- all of the above by cell, renderer, and payoff direction;
- cache/infrastructure accounting and complete workflow traces;
- natural-mixture evaluation alongside any enriched training view.

Co-sampling and nonzero variance are **early exposure diagnostics,
not success criteria**: successful convergence to the favoured
route SHOULD reduce co-sampling and reward variance. An all-reward-1
group is convergence; an all-reward-0.5 group may be a stuck
policy. The former final-third gates (≥20% nonzero variance, ≥5%
pooled co-sampling) are REMOVED — the w3 direction is already
demonstrably below 5% at cold start, and a final-third variance
floor penalizes success while hiding failure. Direction-stratified
reporting replaces them.

The 90% valid-action threshold remains a conspicuous ENGINEERING
warning (few-shot starts near 100%; a large regression is itself a
finding), not a scientific learning threshold. Fail-closed
infrastructure/accounting violations stop a run automatically —
zero infrastructure failures represented as reward, audited from
traces, unchanged from 191_f. Scientific continuation is a reviewed
judgement on the full trajectory and stratified evidence; nothing
auto-continues.

## 7. Prompt policy

- **P0 uses the frozen few-shot prompt, unmodified.** Its strong
  demonstration prior is one of the phenomena P0 studies; it is not
  repaired in response to B before the baseline.
- **The parser stays strict.** Quoted worker IDs and wrong action
  counts are invalid actions, not near-misses to repair silently.
- A later bounded candidate minimally repairs the schema-only
  prompt by stating ONLY that worker IDs are JSON integers and that
  there is exactly one ID per listed step — targeting the observed
  format defect (1,767 + 440 of 2,210 failures) without supplying
  routing examples. It is content-hashed and launched as a
  separately frozen development comparison, never selected
  retrospectively into P0.
- Every prompt variant is logged BEFORE first use with its exact
  bytes and motivation. The cap of **10 conductor prompt variants**
  is retained as an initial-cycle resource control (renewable only
  by the §1 cycle mechanism), not a scientifically meaningful
  lifetime maximum. `worker_dev` prompts remain CLOSED (103_s);
  worker-prompt work requires fresh worker instances under a new
  reviewed plan.

## 8. Group size: a bounded development lever

Group size 8 is the baseline for the probe and — unless the probe
shows the rare direction effectively absent — for P0, preserving
the simplest comparison with the existing GRPO setup. Verified
plug-in priors for the exact direct contrast:

| group size | w2-favoured | w3-favoured |
|---:|---:|---:|
| 8 | 5.35% | 1.12% |
| 16 | 11.49% | 3.77% |
| 32 | 21.59% | 10.19% |

(Computed nonlinearly per observation × prompt before equal-cell
aggregation; they do not replace the probe, and exact contrast is
not all available semantic gradient.) Group 16/32 are reasonable
later configurations if exposure is too thin, at ≈2×/4× generation
cost with unknown training memory/throughput impact — before
freezing either for training, a tightly budgeted engineering smoke
runs through the ACTUAL training path on the 4090. One major lever
changes at a time where practical.

## 9. Exposure-derived budgets (replaces 300 updates / 8 GPU-hours)

The universal update/hour contract is removed: 300 updates has no
stable meaning until batch structure, mixture, and cohort are
fixed, and B measured no optimizer throughput. Instead, EVERY
training launch freezes:

1. rollout groups / sampled prompts per stratum;
2. the corresponding maximum optimizer updates;
3. expected informative-group exposure under the grouped-probe
   estimates;
4. checkpoint/evaluation cadence;
5. cumulative token / worker-call (or equivalent) compute
   accounting;
6. an operational wall-time ceiling.

Operational ceiling: **10 hours total overnight on the RTX 4090**
as an engineering safeguard, not a scientific stopping rule; no new
optimizer update starts after 9.5 hours, reserving time for final
evaluation, checkpointing, trace flushing, and archival. A run
stops at the earlier of its frozen exposure budget and the ceiling.
A learning curve still rising at the budget is not a failure — it
may justify a separately reviewed continuation (§10) from the
checkpoint. All spend is charged to the §1 cycle envelope.

## 10. Checkpointing and resumption

Resumability is a LAUNCH REQUIREMENT. Checkpoint artifacts bind and
preserve at least: conductor/adapter weights; optimizer, scheduler,
and mixed-precision/scaler state as applicable; global
optimizer/update and sampling counters; CPU and CUDA RNG states;
dataloader/sampler order and position (or state sufficient to
reconstruct them exactly); training cohort, renderer schedule, and
configuration identity; prompt, worker pool, payoff surface,
parser, reward, and cache identities; source/environment digest;
and parent checkpoint, run, and segment identifiers. The consuming
resume path fails closed on any identity mismatch.

Before P0: checkpoint save/resume is tested through the real
training stack, including a small interrupted-vs-uninterrupted
comparison to the degree determinism permits.

Three distinct continuations:

1. **Engineering resume** — an operational interruption inside the
   authorized budget, no result-dependent change: may continue the
   same launch from its last valid checkpoint.
2. **Adaptive continuation** — results inspected, training extended
   beyond the frozen budget: a NEW reviewed development segment
   with a new budget, linked to the parent checkpoint.
3. **Fork** — any training parameter (learning rate, prompt,
   mixture, group size, …) changes: labelled a checkpoint fork,
   never a pure resume.

## 11. Provenance and the development ledger

Every probe, training run, resume, and fork receives: a unique
run/segment root under `runs/routing-dev/`; exact source and
environment identity; configuration, prompt, cohort,
payoff-surface, and seed hashes; complete training/evaluation and
checkpoint identities; W&B identity (entity `kencoken`,
`WANDB_LOG_MODEL=false`); cumulative and segment-local resource
accounting; a complete trace archive; and a terminal
complete/aborted record.

The append-only ledger (`plans/conductor/routing_dev_ledger.md`)
records, per entry: the question asked; the evidence motivating the
launch; the exact prelaunch freeze (hashes); parent run/checkpoint
if any; allocated and consumed budget; outcome pointer; post-run
interpretation; and the next decision, flagged as outcome-informed
or not. This replaces the appearance of a fixed adaptive algorithm
with a reconstructable chain of development decisions.

## 12. Retained machinery (unchanged from 191_f)

Deterministic pre-materialized payoff surfaces; request/cache
identity (slw-keyed worker cache); complete v2 workflow traces;
worker pool `wp-197e286115f56e4a` at the frozen launch profile;
frozen worker prompts; single 0/0.5/1 reward mapping with
`INFRA_RETRY_CODES` accounting (infrastructure failures retried or
excluded, NEVER represented as zero reward); one-seed P0 as the
first real training run; ollama VRAM check before every GPU
session; protection of all formal and prior development identities.

## 13. Boundaries

- Development data may never enter a confirmatory estimate. Any
  claim-bearing result requires a NEW reviewed design with a frozen
  hypothesis/estimand/analysis, analysis validation on fresh Monte
  Carlo seeds against the observed geometry, and testing with fresh
  GRPO seeds on disjoint populations excluding every development
  run (186_s §5).
- The D5-affected inferential scope stays isolated: no
  percentile-bootstrap pilot claims from this track; D5 follow-up
  method work (186_s §6) is separate and may not be validated by
  its ability to reverse D5.
- No frozen Stage-0/Stage-1 artifact is modified. The B success
  archive is immutable: the missing pinned payoff-surface inputs
  (203_s closure item) are preserved as a SEPARATE content-addressed
  companion input bundle — exact original files, their existing
  expected byte hashes, a manifest binding them to the B manifest
  and archive, and clean-checkout restore instructions — referenced
  from an addendum, never added retrospectively to the archive or
  its regenerated manifest (204_s §10). No rerun of B.

## 14. Order of operations (204_s §12)

1. Companion evidence bundle for the payoff-surface inputs
   (evidence preservation only; no smoke, lock, or rerun).
2. Reviewer sign-off of this charter.
3. Implement: the three namespaces + disjointness test, cohort
   builders, stratified telemetry, append-only ledger,
   checkpoint/resume with fail-closed identity checks, provenance
   and accounting; full CPU suite under `-W error`.
4. Freeze the exact grouped-probe cohort, configuration, seeds, and
   finite budget (content-hashed).
5. Run and review the zero-update grouped probe.
6. Freeze the exact P0 launch record: cohort/mixture, group size,
   model and prompt, optimizer parameters, exposure budget,
   ten-hour operational ceiling, evaluation/checkpoint cadence,
   seed, provenance.
7. Run one-seed few-shot P0.
8. Review the complete stratified learning dynamics.
9. Stop, resume, fork, or launch a bounded next comparison under a
   new local freeze and the remaining cycle envelope.
