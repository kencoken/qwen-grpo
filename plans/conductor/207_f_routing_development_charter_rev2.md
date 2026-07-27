# 207_f — Routing-training development charter rev2 (response to 206_s)

Supersedes `205_f`. All four 206_s findings and every smaller
correction are incorporated; nothing else is redesigned. **Draft —
no authority until reviewed.** On sign-off this charter authorizes
exactly three things: the development INFRASTRUCTURE (§15 step 3),
the SUPPORT-MATERIALIZATION tranche (§4), and the first
ZERO-UPDATE GROUPED PROBE (§5). The P0 launch freeze follows the
probe; it is not pre-filled here.

Verification notes for this revision: the corrected schema-failure
breakdown (206_s smaller item) was re-derived this session by
running the frozen `parse_routing_action` over the archived raw
bytes (`raw_completions.json`, sha `afb9d8dc…`): schema-only =
**1,768 bad-ID/type/domain failures (1,767 quoted IDs + one
out-of-domain `[3,4]`) + 440 wrong lengths + 2 JSON-parse failures
= 2,210 exactly** (205_f's "1,767 + 440 + 2" summed to 2,209 and
omitted the out-of-domain row — the reviewer is right). Few-shot's
12 failures decompose as 10 out-of-domain + 1 quoted + 1
JSON-parse. `stage1_replay.family_correct_variants` (finding 3)
verified present and unique-by-construction (single Code node
enforced). The 130_s equal-weighting target (finding 2) verified:
equal latent-cluster weights, renderer-crossed within latents, and
no unseen-template claim.

## 1. Framing: adaptively sequenced, locally frozen

The development track is **adaptive** in sequence and **frozen**
per launch (204_s):

- **Adaptive**: an observed run may legitimately motivate the next
  question, prompt, mixture, group size, learning rate, duration,
  or checkpoint continuation. The empirical behaviour is not yet
  understood well enough to specify every useful branch in advance.
- **Locally frozen**: each concrete launch — support
  materialization, probe, engineering smoke, standalone GPU
  evaluation, training run, continuation, fork — is specified
  before it runs. Its question, source/configuration identity,
  cohort, model, prompt, sampling parameters, training exposure,
  evaluation schedule, seed, telemetry, and operational budget are
  reviewed and content-hashed before the first relevant sample or
  optimizer update. Engineering smokes and standalone GPU
  evaluations use a LIGHTWEIGHT freeze (config hash + motivation +
  budget in the ledger before launch); they are still
  provenance-bound ledger entries (§12). Results may motivate a
  later launch; they may not silently alter the launch underway.

This separates a **finite authorization** (every launch must have
one) from a **finite research programme** (which need not be fully
bounded today). Work proceeds in finite **development cycles**:

- **Initial-cycle envelope: 60 RTX-4090 GPU-hours cumulative**
  (≈ six full-run equivalents at the §10 ten-hour ceiling),
  counting ALL development GPU work in the cycle — support
  materialization, probes, engineering smokes, evaluations,
  training runs — at measured cost.
- On exhaustion: a written synthesis, then an explicit reviewed
  decision to renew, change, or stop the cycle. Renewal is never
  retroactive; the envelope is a resource control, not a
  scientific stopping rule, and not advance permission to invent
  configurations after seeing results.

Reviewer involvement makes adaptation visible and auditable; it
does not convert outcome-informed selection into confirmatory
evidence. **Every development run is development data permanently.**
A later claim requires a newly frozen hypothesis and analysis,
fresh training seeds, and disjoint evaluation populations excluding
all development runs (186_s §5, unchanged).

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
`math_atomic` is near-deterministic and WRONG at reward 0.5
(0.999); useful variation concentrates in `code_atomic`
(zero-variance 0.35), `fork_join` (0.63), and `math_code` (0.82).
Schema-only's variance is mostly invalid-0 vs valid-0.5 formatting
contrast: of its 2,210 schema failures, 1,768 are bad-ID/type/
domain (1,767 quoted IDs + one out-of-domain `[3,4]`), 440 are
wrong action counts, and 2 are malformed JSON. The few-shot policy
is strongly demonstration-shaped (32 distinct outputs / 4,608
samples) and strongly renderer-sensitive (`code_atomic` Code-worker
selection ≈ 1% / 58% / 23% under `bound_var` / `goal_first` /
`resource_first`). Cold-start preferences point AGAINST the payoff
direction in both distinct-payoff populations.

Consequences adopted: few-shot is the P0 baseline prompt; the
parser stays strict; mean reward can improve while whole cells
(`math_atomic`) stay untouched, so telemetry must be stratified;
pooled aggregates are inadequate. **B is a prior, not a paired
baseline**: the paired baseline for P0 is the checkpoint-zero
evaluation of §6.

B does NOT demonstrate (204_s §1): that `routing_dev` has the same
action distribution; that real grouped GRPO rollouts reproduce
iid-singleton plug-ins; that group 8 gives adequate exposure under
the eventual mixture; that every cell has an accessible
reward-improving action; that any update count / wall time /
learning rate / mixture suffices; that GRPO will learn routing,
reverse the preference, generalize across renderers, or avoid
collapse; or that the 4090 can train a given configuration because
it completed B inference. The old 20% variance floor is NOT read as
a passed feasibility gate.

## 3. Namespaces (three, genuinely new, disjoint from everything)

Added to `NAMESPACE_CONFIG` at implementation. **All caps are
PER-CELL** (latent clusters per task cell):

- `routing_dev` — training/iteration populations; MAY be
  direction-enriched under §6's outcome-conditioned rule. Cap 2,000
  latent clusters per cell, expansion batch 500.
- `routing_dev_val` — **adaptive development validation** (renamed
  from 191_f's `routing_dev_holdout` to say what it is): consulted
  BETWEEN runs to inform development choices; natural mixture (§6)
  only, never trained on; retired or rotated at each cycle
  boundary. Cap 500 per cell, batch 250.
- `routing_dev_cycle` — **cycle-end holdout**: revealed ONCE at
  cycle synthesis (§1), then PERMANENTLY RETIRED; never consulted
  during within-cycle iteration; natural mixture only, never
  trained on. A renewed cycle allocates fresh identities. Cap 500
  per cell, batch 250.

Disjointness is BY CONSTRUCTION (namespace string in every latent
identity) from ALL existing identities — `construction`,
`qualification`, `train`, `dev`, `test`, `worker_dev`, `policy_dev`
— and from each other, and is asserted by a test regenerating id
prefixes across all namespaces with zero intersection. `policy_dev`
cohort B 24–47 remains never-reassign and untouched. The 18-obs
B support is development data reserved for descriptive comparison
only; it is never trained on. **None of the three namespaces may
ever become confirmatory data.**

## 4. Support materialization (surfaces before cohorts — 206_s F1)

New `routing_dev` observations have NO precomputed payoff surfaces,
and an observation's payoff direction (w2- vs w3-favoured) is
knowable only AFTER its workers have executed. Without this step,
§§5–6 would be circular — a cohort frozen "with both directions"
before the execution that defines direction. Therefore a finite,
locally frozen **support-materialization tranche** precedes the
grouped-probe freeze:

1. **Freeze, outcome-blind**: a candidate latent-prefix per cell,
   the renderer schedule, and a hard search cap (maximum
   observations whose surfaces may be materialized), all
   content-hashed BEFORE any worker executes on `routing_dev`.
2. **Freeze the surface machinery**: worker pool
   `wp-197e286115f56e4a` at the frozen launch profile, frozen
   worker prompts, request/cache profile, and the complete `4^S`
   surface contract (every observation's full assignment space, the
   same contract the 18-obs support satisfied).
3. **Materialize and authenticate**: build the surfaces
   deterministically, content-hash them, and verify coverage
   (every `4^S` row present; missing rows are errors, never silent
   skips).
4. **Disclose everything screened**: ALL materialized rows and the
   resulting direction yields (w2-favoured / w3-favoured / tied per
   cell) are disclosed — no silent discards.
5. **Then freeze the grouped-probe cohort** against the exact
   surface hashes.

The first grouped probe uses an **outcome-blind, factor-balanced
prefix** — its cohort is selected by the frozen prefix rule, NOT by
the observed direction yields. Any later direction-enriched P0
curriculum is explicitly **outcome-conditioned development
adaptation**, flagged as such in its launch freeze and ledger entry
(§12). Surface-materialization worker execution counts against the
60-hour envelope at measured cost.

## 5. First executable tranche: the zero-update grouped probe

After support materialization, a separately frozen, finite
**zero-update grouped probe** runs through the ACTUAL training
rollout path (204_s §2). The B figures are singleton plug-ins; the
probe measures what real grouped rollouts contain.

Specification (fixed here; the exact cohort/seeds at its freeze):

- new `routing_dev` identities with §4-materialized, authenticated
  surfaces, the cohort frozen against exact surface hashes;
- an outcome-blind, factor-balanced, renderer-crossed prefix
  cohort (§4);
- the exact proposed P0 conductor checkpoint and the frozen
  few-shot prompt bytes;
- the real renderer, parser, semantic-assignment, payoff-surface,
  reward, group-construction, and cache paths;
- group size 8;
- ZERO optimizer updates, zero model mutation;
- operational ceiling 3 GPU-hours (deadline checked before every
  generation batch on the monotonic clock; partial evidence
  preserved on abort), charged to the §1 envelope.

Reported per cell × renderer × payoff direction (tied rows a
separate stratum), every rate accompanied by its **raw count and
denominator**:

1. parse rate and full-schema valid-action rate;
2. reward-level frequencies;
3. zero-variance groups split into all-0 / all-0.5 / all-1;
4. groups containing invalid-vs-valid FORMAT contrast;
5. groups containing valid 0.5-vs-1 SEMANTIC contrast;
6. groups containing the exact w2/w3 direct contrast (§7
   definition);
7. node-level family-correct routing rates (C1 view) and
   conditional w2-vs-w3 selection on Code nodes (C2 view);
8. per-worker and per-assignment frequencies, routing entropy,
   repeated-output concentration;
9. group-construction, cache, worker-execution, and infrastructure
   telemetry;
10. **projected informative-group counts under the proposed P0
    budget** (probe rates × proposed groups per stratum), labelled
    as projections.

The three contrast notions in items 4–6 stay separate throughout
the track: exact w2/w3 co-sampling is the cleanest model-selection
contrast but not the only semantic gradient — a reward-1 action can
be reinforced against a valid reward-0.5 assignment even when the
exact paired alternative is absent.

Hard gates for the probe are infrastructure integrity and exact
accounting ONLY. The measured exposure quantities are evidence for
the P0 design, not pass/fail thresholds. The probe is a development
tranche in its own right: P0's mixture and exposure are chosen
after inspecting it, so **P0 receives a new local freeze** and the
two are never described as one preregistered experiment.

**P0 is bound to the policy the probe measured (206_s F4)**: P0
retains the probe's conductor checkpoint, prompt bytes, and
sampling/generation semantics. Changing ANY of those requires
another grouped probe before the P0 freeze. If P0 proposes a group
size other than 8, its freeze must EITHER include a small
zero-update sample at the candidate group size OR explicitly label
the exposure estimate as an iid extrapolation from group-8
measurements — a memory/throughput smoke alone does not establish
co-sampling behaviour.

## 6. Cohort and mixture design

**"Natural mixture" is a frozen definition, not an adjective
(206_s F2).** Frozen cycle-wide before P0, per the 130_s target:

- task cells equally weighted;
- latent clusters equally weighted within cell;
- renderers equally weighted within latent.

This definition stays unchanged across all within-cycle
comparisons. All evaluation populations (`routing_dev_val`,
`routing_dev_cycle`) use it.

**Checkpoint-zero evaluation**: before P0's first optimizer update,
the launch evaluates the untouched conductor checkpoint on the
EXACT `routing_dev_val` cohort, seeds, and decoding configuration
used at every subsequent checkpoint. That paired baseline — not B —
anchors all within-run lift claims.

The development data has two separated roles; all reports show them
separately:

- a **contrast-aware training/development population**
  (`routing_dev`), permitted to enrich rare task/payoff directions
  so the learning mechanism is actually exercised. Enrichment is
  outcome-conditioned development adaptation (§4) and is flagged as
  such. It must: include all task cells; include enough Code-family
  observations favouring worker 2 AND worker 3 for both directions
  to receive deliberate exposure; cross or balance renderers so a
  renderer token cannot stand in for the routing decision; keep
  tied Code rows a separate category, never direction-bearing; be
  **latent-disjoint, factor-balanced, and renderer-crossed**
  between training and evaluation (the generator provides no
  genuine unseen-template split and 130_s makes no such claim —
  none is made here); and bind every observation to the exact
  authenticated payoff surface used for reward.
- a **natural-mixture evaluation population** (`routing_dev_val`,
  and `routing_dev_cycle` once at cycle end), showing what the
  enriched curriculum does under the intended task distribution.

Enrichment is a legitimate development curriculum, not evidence
that the natural distribution contains the same signal. This
charter fixes NO training-mixture proportions: the grouped-probe
freeze defines its exact cohort (outcome-blind, §4); the P0 launch
record defines its exact training and evaluation cohorts.

## 7. Online telemetry and continuation decisions

Pooled mean reward and pooled variance are inadequate (B showed the
same aggregate movement can be formatting repair, semantic routing,
convergence, a wrong deterministic basin, or a renderer shortcut).
Online and checkpoint reports include, each rate with raw count and
denominator:

- parse rate and full-schema valid-action rate;
- invalid/valid FORMAT-contrast rate;
- valid 0.5/1 SEMANTIC-contrast rate;
- exact w2/w3 direct-contrast rate;
- **C1 view**: node-level family-correct routing rate and its lift
  over checkpoint zero;
- **C2 view**: conditional worker-2 vs worker-3 selection on Code
  nodes and incremental lift, given family-correct routing
  elsewhere;
- zero-variance groups split by constant reward level;
- mean reward and reward-level frequencies;
- per-worker, per-assignment, and routing-entropy trajectories;
- all of the above by cell, renderer, and payoff direction, with
  tied rows a separate stratum;
- cache/infrastructure accounting and complete workflow traces;
- natural-mixture evaluation alongside any enriched training view.

**Exact w2/w3 direct contrast is DEFINED via
`stage1_replay.family_correct_variants`**: the unique pair of
assignments that are identical and family-correct at every non-Code
node and differ only by worker 2 vs worker 3 at the (unique) Code
node. A group exhibits the direct contrast when it contains BOTH
members of that pair. Generic per-worker frequencies do not
substitute — they can hide family-routing progress while model
selection stays unchanged, which is exactly what the C1/C2 split
exposes.

Co-sampling and nonzero variance are **early exposure diagnostics,
not success criteria**: successful convergence to the favoured
route SHOULD reduce co-sampling and reward variance. An
all-reward-1 group is convergence; an all-reward-0.5 group may be a
stuck policy. The former final-third gates (≥20% nonzero variance,
≥5% pooled co-sampling) remain REMOVED; direction-stratified
reporting replaces them.

The 90% valid-action threshold remains a conspicuous ENGINEERING
warning (few-shot starts near 100%; a large regression is itself a
finding), not a scientific learning threshold. Fail-closed
infrastructure/accounting violations stop a run automatically —
zero infrastructure failures represented as reward, audited from
traces, unchanged from 191_f. Scientific continuation is a reviewed
judgement on the full trajectory and stratified evidence; nothing
auto-continues.

## 8. Prompt policy

- **P0 uses the frozen few-shot prompt, unmodified.** Its strong
  demonstration prior is one of the phenomena P0 studies; it is not
  repaired in response to B before the baseline.
- **The parser stays strict.** Quoted worker IDs, out-of-domain
  IDs, and wrong action counts are invalid actions, not near-misses
  to repair silently.
- A later bounded candidate minimally repairs the schema-only
  prompt by stating ONLY that worker IDs are JSON integers in 0–3
  and that there is exactly one ID per listed step — targeting the
  verified format defect (1,768 + 440 of 2,210 failures) without
  supplying routing examples. It is content-hashed and launched as
  a separately frozen development comparison, never selected
  retrospectively into P0.
- Every prompt variant is logged BEFORE first use with its exact
  bytes and motivation. The cap of **10 conductor prompt variants**
  is retained as an initial-cycle resource control (renewable only
  by the §1 cycle mechanism), not a scientifically meaningful
  lifetime maximum. `worker_dev` prompts remain CLOSED (103_s);
  worker-prompt work requires fresh worker instances under a new
  reviewed plan.

## 9. Group size: a bounded development lever

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
cost with unknown training memory/throughput impact. Before
freezing either for training: a tightly budgeted engineering smoke
through the ACTUAL training path on the 4090 (memory/throughput),
AND the §5 exposure requirement — a small zero-update sample at the
candidate group size, or an explicit iid-extrapolation label on the
exposure estimate. One major lever changes at a time where
practical.

## 10. Exposure-derived budgets (replaces 300 updates / 8 GPU-hours)

The universal update/hour contract is removed: 300 updates has no
stable meaning until batch structure, mixture, and cohort are
fixed, and B measured no optimizer throughput. Instead, EVERY
training launch freezes:

1. rollout groups / sampled prompts per stratum;
2. the corresponding maximum optimizer updates;
3. expected informative-group exposure under the grouped-probe
   estimates (with raw projected counts, §5 item 10);
4. checkpoint/evaluation cadence;
5. cumulative token / worker-call (or equivalent) compute
   accounting;
6. an operational wall-time ceiling.

Operational ceiling: **10 hours total on the RTX 4090, cumulative
across engineering resumes of the same launch**, as an engineering
safeguard, not a scientific stopping rule. The deadline is checked
on the monotonic clock **before starting each generation batch**,
not merely before an optimizer update. The finalization reserve is
sized from MEASURED worst-case durations of a rollout batch,
evaluation pass, checkpoint write, trace flush, and archival (from
the probe and engineering smokes), and no new generation batch
starts inside the reserve — the 9.5-hour figure from 205_f is the
default only until those measurements exist. A run stops at the
earlier of its frozen exposure budget and the ceiling. A learning
curve still rising at the budget is not a failure — it may justify
a separately reviewed adaptive continuation (§11) from the
checkpoint. All spend is charged to the §1 cycle envelope.

## 11. Checkpointing and resumption

Resumability is a LAUNCH REQUIREMENT. Checkpoint artifacts bind and
preserve at least: conductor/adapter weights; optimizer, scheduler,
and mixed-precision/scaler state as applicable; global
optimizer/update and sampling counters — with **generated and
optimizer-consumed group counters tracked separately**; CPU and
CUDA RNG states; dataloader/sampler order and position (or state
sufficient to reconstruct them exactly); training cohort, renderer
schedule, and configuration identity; prompt, worker pool, payoff
surface, parser, reward, and cache identities; source/environment
digest; and parent checkpoint, run, and segment identifiers. The
consuming resume path fails closed on any identity mismatch.

**Resume-test acceptance criteria (206_s)** — the pre-P0 test
passes only if:

1. checkpoints occur at complete generation/update boundaries
   (never mid-group, never between generation and its consuming
   update without recording which);
2. generated and optimizer-consumed group counters are separate
   and both restored exactly;
3. post-checkpoint rows from an aborted segment remain preserved
   evidence but are EXCLUDED from the resumed trajectory;
4. merged segments have no missing and no duplicated groups.

The test runs through the REAL training stack on the GPU,
including an interrupted-vs-uninterrupted comparison to the degree
determinism permits; it is an explicit §15 step before P0.

Three distinct continuations:

1. **Engineering resume** — an operational interruption inside the
   authorized budget, no result-dependent change: may continue the
   same launch from its last valid checkpoint; the §10 ceiling is
   cumulative across such resumes.
2. **Adaptive continuation** — results inspected, training extended
   beyond the frozen budget: a NEW reviewed development segment
   with a new budget, linked to the parent checkpoint.
3. **Fork** — any training parameter (learning rate, prompt,
   mixture, group size, …) changes: labelled a checkpoint fork,
   never a pure resume.

## 12. Provenance and the development ledger

Every support materialization, probe, engineering smoke, standalone
GPU evaluation, training run, resume, and fork receives: a unique
run/segment root under `runs/routing-dev/`; exact source and
environment identity; configuration, prompt, cohort,
payoff-surface, and seed hashes; complete training/evaluation and
checkpoint identities; W&B identity (entity `kencoken`,
`WANDB_LOG_MODEL=false`) where applicable; cumulative and
segment-local resource accounting; a complete trace archive; and a
terminal complete/aborted record. Engineering smokes and standalone
evaluations use the lightweight freeze of §1 but are never
unlogged.

The append-only ledger (`plans/conductor/routing_dev_ledger.md`)
records, per entry: the question asked; the evidence motivating the
launch; the exact prelaunch freeze (hashes); parent run/checkpoint
if any; allocated and consumed budget; outcome pointer; post-run
interpretation; the next decision, flagged as outcome-informed or
not; and — for cohorts — whether selection was outcome-blind or
outcome-conditioned (§4). This replaces the appearance of a fixed
adaptive algorithm with a reconstructable chain of development
decisions.

## 13. Retained machinery (unchanged from 191_f)

Deterministic pre-materialized payoff surfaces (now §4-materialized
for `routing_dev`); request/cache identity (slw-keyed worker
cache); complete v2 workflow traces; worker pool
`wp-197e286115f56e4a` at the frozen launch profile; frozen worker
prompts; single 0/0.5/1 reward mapping with `INFRA_RETRY_CODES`
accounting (infrastructure failures retried or excluded, NEVER
represented as zero reward); one-seed P0 as the first real training
run; ollama VRAM check before every GPU session; protection of all
formal and prior development identities.

## 14. Boundaries

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
  its regenerated manifest (204_s §10). No rerun of B. **This
  bundle remains a prerequisite to final sign-off (206_s).**

## 15. Order of operations

1. Companion evidence bundle for the payoff-surface inputs
   (evidence preservation only; no smoke, lock, or rerun;
   prerequisite to final sign-off).
2. Reviewer sign-off of this charter.
3. Implement: the three namespaces + disjointness test, surface
   materialization + authentication, cohort builders, stratified
   telemetry incl. C1/C2 views, natural-mixture definition,
   append-only ledger, checkpoint/resume with fail-closed identity
   checks and separate generated/consumed counters, provenance and
   accounting; full CPU suite under `-W error`.
4. Freeze the outcome-blind support-materialization tranche (§4:
   candidate prefix, renderer schedule, search cap, surface
   contract); materialize and authenticate the surfaces; disclose
   screened rows and direction yields.
5. Freeze the exact grouped-probe cohort (outcome-blind,
   factor-balanced prefix against exact surface hashes),
   configuration, seeds, and finite budget (content-hashed).
6. Run and review the zero-update grouped probe.
7. Checkpoint save/resume test on the real GPU training stack
   against the §11 acceptance criteria, including the
   interrupted-vs-uninterrupted comparison.
8. Freeze the exact P0 launch record: cohort/mixture (natural
   mixture frozen cycle-wide; any enrichment flagged
   outcome-conditioned), group size (bound to §5's probe policy),
   model and prompt (identical to the probe's), optimizer
   parameters, exposure budget with projected informative-group
   counts, ten-hour cumulative operational ceiling with measured
   finalization reserve, evaluation/checkpoint cadence incl. the
   checkpoint-zero evaluation, seed, provenance.
9. Run one-seed few-shot P0.
10. Review the complete stratified learning dynamics.
11. Stop, resume, fork, or launch a bounded next comparison under a
    new local freeze and the remaining cycle envelope.
