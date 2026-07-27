# 209_f — Routing-training development charter rev3 (response to 208_s)

Supersedes `207_f`. The six 208_s findings and all lifecycle
clarifications are incorporated; nothing else is redesigned.
**Draft — awaiting sign-off.** On sign-off this charter authorizes
exactly three things: the development INFRASTRUCTURE (§15 step 3),
the SUPPORT-MATERIALIZATION tranche (§4), and the first
ZERO-UPDATE GROUPED PROBE (§5). The P0 launch freeze follows the
probe; it is not pre-filled here.

**The companion B payoff-surface bundle has LANDED in this commit**
(the last sign-off prerequisite): `plans/conductor/evidence/
stage1_b_diagnostic_surface_inputs_c8d78f3019c1/` — the four exact
verifier-read input files at their recorded byte hashes
(`manifest.json` = the launch-profile pin `221a04d5…`,
`payoffs.jsonl` `78dd4503…`, trace `manifest.json` `d831b7f9…`,
trace `steps.jsonl` `82531709…`), a self-hashed
`companion_manifest.json` (`c8d78f30…`) binding the B diagnostic
manifest `973e8adc…` and the archive's evidence manifest
`ea9dfbd2…`, restore instructions, and the recorded exclusion of
`cache.sqlite` (never read by `load_support_surface`; only its
accounting counts, which are verified fields of the surface
manifest). Restore was TESTED this session: the bundle copied into
a fresh directory loads through the full fail-closed loader — 324
re-scored payoff rows, distribution {0.5: 300, 1.0: 24}, exactly
the frozen values. The success archive itself is byte-unchanged.

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
  training runs — at measured cost, and subject to the §10
  cycle-end reserve `R_cycle`.
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
- `routing_dev_val` — **adaptive development validation**:
  consulted BETWEEN runs to inform development choices; natural
  mixture (§6) only, never trained on; retired or rotated at each
  cycle boundary. Cap 500 per cell, batch 250.
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

## 4. Support materialization (surfaces before cohorts)

New `routing_dev` observations have NO precomputed payoff surfaces,
and an observation's payoff direction (w2- vs w3-favoured) is
knowable only AFTER its workers have executed. A finite, locally
frozen **support-materialization tranche** therefore precedes the
grouped-probe freeze:

1. **Freeze, outcome-blind — including the probe-selection rule
   (208_s F4)**: a candidate latent-prefix per cell, the renderer
   schedule, a hard search cap (maximum observations whose surfaces
   may be materialized), AND the exact grouped-probe cohort rule —
   its prefix length and deterministic selection function — all
   content-hashed BEFORE any worker executes on `routing_dev`.
   After materialization, ONLY the surface hashes are filled in;
   the observed direction yields cannot influence the first probe
   cohort, and the freeze makes that mechanically auditable rather
   than a promise.
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
5. **Then freeze the grouped-probe cohort record**: the step-1 rule
   applied verbatim, bound to the exact surface hashes.

Any later direction-enriched P0 curriculum is explicitly
**outcome-conditioned development adaptation**, flagged as such in
its launch freeze and ledger entry (§12). Surface-materialization
worker execution counts against the 60-hour envelope at measured
cost, and its measured timing sizes the §10 `R_cycle` reserve.

## 5. First executable tranche: the zero-update grouped probe

After support materialization AND the §11 GPU resume test, a
separately frozen, finite **zero-update grouped probe** runs
through the ACTUAL training rollout path (204_s §2). The B figures
are singleton plug-ins; the probe measures what real grouped
rollouts contain.

Specification (fixed here; the exact cohort/seeds at its freeze):

- new `routing_dev` identities with §4-materialized, authenticated
  surfaces, the cohort produced by the §4 step-1 frozen rule and
  bound to exact surface hashes;
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
7. node-level family-correct routing rates (C1 view) and the §7
   C2 view on its exact denominator;
8. per-worker and per-assignment frequencies, routing entropy,
   repeated-output concentration;
9. group-construction, cache, worker-execution, and infrastructure
   telemetry.

The probe reports **authenticated rates, counts, and denominators
only** (208_s F5). Projected informative-group counts under the P0
budget are computed at the P0 FREEZE from these authenticated
results — the P0 budget does not exist until after the probe is
reviewed, so the probe cannot project against it.

The three contrast notions in items 4–6 stay separate throughout
the track: exact w2/w3 co-sampling is the cleanest model-selection
contrast but not the only semantic gradient — a reward-1 action can
be reinforced against a valid reward-0.5 assignment even when the
exact paired alternative is absent.

Hard gates for the probe are infrastructure integrity and exact
accounting ONLY. The measured exposure quantities are evidence for
the P0 design, not pass/fail thresholds. **An aborted or incomplete
probe is never reported as the completed exposure estimate**: its
partial evidence is preserved and may motivate a separately frozen
continuation, but only a complete probe yields the exposure record
the P0 freeze consumes. **Probe invalidation rule (208_s F1)**: any
post-probe fix touching rollout generation, sampling, grouping,
parsing, or reward code invalidates the probe's exposure evidence
and reruns the probe before any P0 freeze.

The probe is a development tranche in its own right: P0's mixture
and exposure are chosen after inspecting it, so **P0 receives a new
local freeze** and the two are never described as one preregistered
experiment.

**P0 is bound to the policy the probe measured (206_s F4)**: P0
retains the probe's conductor checkpoint, prompt bytes, and
sampling/generation semantics. Changing ANY of those requires
another grouped probe before the P0 freeze. If P0 proposes a group
size other than 8, its freeze must EITHER include a small
zero-update sample at the candidate group size OR explicitly label
the exposure estimate as an iid extrapolation from group-8
measurements — a memory/throughput smoke alone does not establish
co-sampling behaviour.

## 6. Cohort, mixture, and evaluation-surface design

**"Natural mixture" is a frozen definition, not an adjective.**
Frozen cycle-wide before P0, per the 130_s target:

- task cells equally weighted;
- latent clusters equally weighted within cell;
- renderers equally weighted within latent.

This definition stays unchanged across all within-cycle
comparisons. All evaluation populations (`routing_dev_val`,
`routing_dev_cycle`) use it.

**Evaluation surfaces enter the lifecycle explicitly (208_s F2).**
Mandatory pre-P0 sequence, in order:

1. outcome-blind freeze of the exact `routing_dev_val` cohort,
   renderer schedule, mixture weights, and evaluation seeds;
2. complete `4^S` surface materialization and authentication for
   that cohort (§4 machinery; charged to the envelope);
3. a lock binding the resulting cohort and surface hashes;
4. the checkpoint-zero evaluation (below);
5. only then training.

For `routing_dev_cycle`: its cohort and its
checkpoint-selection/evaluation rule are frozen BEFORE P0, but its
surfaces are materialized only AT cycle synthesis — preserving the
one-reveal discipline — then the evaluation runs once, is archived,
and the population is permanently retired.

**Checkpoint-zero evaluation**: before P0's first optimizer update,
the launch evaluates the untouched conductor checkpoint on the
EXACT `routing_dev_val` cohort, seeds, and decoding configuration
used at every subsequent checkpoint. That paired baseline — not B —
anchors all within-run lift claims. Checkpoint evaluations use
**isolated RNG state** (or save and restore the training RNG
states) so that evaluating never changes subsequent rollout
sampling.

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
- **C2 view** on its exact denominator (below);
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
members of that pair.

**C2 denominator (208_s F6)**: C2 is optimal specialist selection
CONDITIONAL on (a) every non-Code node being family-correct AND
(b) the Code choice lying in `{2, 3}`. Wrong-family Code choices
remain INCORRECT in the broader model-accuracy view (the 130_s §6.5
`ModelAcc` rule: malformed or wrong-family selections score 0, they
never vanish from the denominator); the conditional C2 view is
reported alongside, never instead. **C2 incremental lift uses the
existing best-fixed-Code `ScaleLift` comparison** (130_s §6.4: the
paired collapse of every selected worker-2/3 Code position to
`c_fixed`, observable from the cached surface without extra worker
calls) — not generic checkpoint-to-checkpoint reward lift, which
confounds model selection with format and family progress.

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
3. expected informative-group exposure, computed at the P0 freeze
   from the probe's authenticated rates (with raw projected
   counts);
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
checkpoint.

**Cycle-end reserve (208_s F3)**: once support-materialization
timing is measured, a reserve `R_cycle` is recorded in the ledger,
sized for cycle-surface materialization (`routing_dev_cycle`),
selected-checkpoint inference, and verification/trace/archival
cost. **A new launch is admissible only if
`remaining envelope ≥ launch maximum + R_cycle`.** The envelope can
therefore never be exhausted before the cycle holdout is
materialized and evaluated. All spend is charged to the §1 cycle
envelope.

## 11. Checkpointing and resumption

Resumability is a LAUNCH REQUIREMENT. **v1 checkpoint boundary
(208_s F1): checkpoints are taken ONLY after the optimizer has
consumed the complete generation buffer** — never mid-group and
never between generation and its consuming update. The current
GRPOTrainer does not checkpoint buffered rollout inputs and would
regenerate them after resume, so a between-boundary checkpoint
cannot be made sound by recording identities; persisting the full
completions, token IDs, masks, log-probabilities, rewards, and
buffer cursor is explicitly OUT of the v1 contract and would
require its own review.

Checkpoint artifacts bind and preserve at least: conductor/adapter
weights; optimizer, scheduler, and mixed-precision/scaler state as
applicable; global optimizer/update and sampling counters — with
**generated and optimizer-consumed group counters tracked
separately**; CPU and CUDA RNG states; dataloader/sampler order and
position (or state sufficient to reconstruct them exactly);
training cohort, renderer schedule, and configuration identity;
prompt, worker pool, payoff surface, parser, reward, and cache
identities; source/environment digest; and parent checkpoint, run,
and segment identifiers. The consuming resume path fails closed on
any identity mismatch.

**Resume-test acceptance criteria** — the pre-probe GPU test (§15
step 5) passes only if:

1. checkpoints occur only at the v1 boundary above;
2. generated and optimizer-consumed group counters are separate
   and both restored exactly;
3. post-checkpoint rows from an aborted segment remain preserved
   evidence but are EXCLUDED from the resumed trajectory;
4. merged segments have no missing and no duplicated groups;
5. the interrupted and uninterrupted runs agree on: final adapter,
   optimizer, and scheduler state — exactly, or under a tolerance
   frozen BEFORE the test; the next sampler/renderer identity to
   be consumed; and counters plus merged trace cardinality.

The test runs through the REAL training stack on the GPU. It is
scheduled BEFORE the grouped probe (208_s), so that any fix it
forces in rollout generation, sampling, grouping, parsing, or
reward code lands before the probe rather than invalidating it;
the §5 invalidation rule covers any such fix made later anyway.

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
environment identity — **the execution digest covers the actual
training driver and entry-point files, not only
`tasks/conductor/*.py`** (208_s); configuration, prompt, cohort,
payoff-surface, and seed hashes; complete training/evaluation and
checkpoint identities; W&B identity (entity `kencoken`,
`WANDB_LOG_MODEL=false`) where applicable; cumulative and
segment-local resource accounting incl. the §10 `R_cycle`
admissibility check; a complete trace archive; and a terminal
complete/aborted record. Engineering smokes and standalone
evaluations use the lightweight freeze of §1 but are never
unlogged.

The append-only ledger (`plans/conductor/routing_dev_ledger.md`)
records, per entry: the question asked; the evidence motivating the
launch; the exact prelaunch freeze (hashes); parent run/checkpoint
if any; allocated and consumed budget (and remaining envelope after
`R_cycle`); outcome pointer; post-run interpretation; the next
decision, flagged as outcome-informed or not; and — for cohorts —
whether selection was outcome-blind or outcome-conditioned (§4).

## 13. Retained machinery (unchanged from 191_f)

Deterministic pre-materialized payoff surfaces (now §4/§6
materialized for the development namespaces); request/cache
identity (slw-keyed worker cache); complete v2 workflow traces;
worker pool `wp-197e286115f56e4a` at the frozen launch profile;
frozen worker prompts; single 0/0.5/1 reward mapping with
`INFRA_RETRY_CODES` accounting (infrastructure failures retried or
excluded, NEVER represented as zero reward); one-seed P0 as the
first real training run; ollama VRAM check before every GPU
session; protection of all formal and prior development identities.

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
  archive is immutable and byte-unchanged; its portability gap is
  closed by the companion input bundle
  `stage1_b_diagnostic_surface_inputs_c8d78f3019c1` (header), which
  binds the archive by content hash and was restore-tested through
  the full fail-closed loader. No rerun of B occurred or was
  needed.

## 15. Order of operations

1. ~~Companion evidence bundle~~ — **DONE in this commit** (header;
   restore-tested).
2. Reviewer sign-off of this charter.
3. Implement: the three namespaces + disjointness test, surface
   materialization + authentication, cohort builders (incl. the
   frozen probe-selection rule machinery), stratified telemetry
   incl. C1/C2 on the §7 denominators, natural-mixture definition,
   append-only ledger with `R_cycle` accounting, checkpoint/resume
   at the v1 boundary with fail-closed identity checks and separate
   generated/consumed counters, isolated evaluation RNG, provenance
   incl. the training-driver digest; full CPU suite under
   `-W error`.
4. Freeze the outcome-blind support-materialization tranche (§4:
   candidate prefix, renderer schedule, search cap, probe-selection
   rule, surface contract); materialize and authenticate the
   surfaces; disclose screened rows and direction yields; record
   measured timing → size `R_cycle`.
5. Checkpoint save/resume test on the real GPU training stack
   against the §11 acceptance criteria, including the
   interrupted-vs-uninterrupted comparison (BEFORE the probe).
6. Freeze the grouped-probe cohort record (§4 step-5) plus
   configuration, seeds, and finite budget (content-hashed).
7. Run and review the zero-update grouped probe (complete probes
   only yield exposure records; §5 invalidation rule in force from
   here).
8. Pre-P0 evaluation sequence (§6): outcome-blind
   `routing_dev_val` freeze → surface materialization +
   authentication → cohort/surface lock → checkpoint-zero
   evaluation; freeze the `routing_dev_cycle` cohort and its
   checkpoint-selection/evaluation rule (surfaces deferred to
   synthesis).
9. Freeze the exact P0 launch record: cohort/mixture (natural
   mixture frozen cycle-wide; any enrichment flagged
   outcome-conditioned), group size (bound to §5's probe policy),
   model and prompt (identical to the probe's), optimizer
   parameters, exposure budget with projected informative-group
   counts computed from the probe's authenticated rates, ten-hour
   cumulative operational ceiling with measured finalization
   reserve, evaluation/checkpoint cadence, seed, provenance;
   admissibility per §10 (`remaining ≥ maximum + R_cycle`).
10. Run one-seed few-shot P0.
11. Review the complete stratified learning dynamics.
12. Stop, resume, fork, or launch a bounded next comparison under a
    new local freeze and the remaining cycle envelope.
13. At cycle end: materialize `routing_dev_cycle` surfaces, run the
    one-reveal evaluation, archive, retire the population, write
    the synthesis, and explicitly renew, change, or stop.
