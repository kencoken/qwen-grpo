# 191_f — Routing-training development-track launch plan (draft for review)

First draft under the signed-off Route B package (186_s §5 + 187_f
§4 + 189_f §3; Ken signed off 2026-07-26). **Draft — no authority
until reviewed; no optimizer update runs before this plan's
sign-off and its provenance freeze.** This is a DEVELOPMENT track:
discovery, not confirmation. Its runs are development data forever;
they may never enter a confirmatory estimate; it inherits no global
GO and confers none.

## 1. Namespaces (genuinely new, disjoint from everything)

Two NEW namespaces are added to `NAMESPACE_CONFIG` at
implementation:

- `routing_dev` — training/iteration populations.
  Cap 2,000 latent clusters, expansion batch 500.
- `routing_dev_holdout` — descriptive held-out evaluation only;
  never trained on, never used for iteration decisions within a
  run.
  Cap 500 latent clusters, expansion batch 250.

Disjointness is BY CONSTRUCTION (the namespace string is part of
every latent identity) from ALL existing identities —
`construction`, `qualification`, `train`, `dev`, `test`,
`worker_dev`, `policy_dev` — and is additionally asserted by a
test that regenerates id prefixes across all namespaces and checks
zero intersection (189_s/188_s requirement: not merely cohort-B
protection; policy_dev cohort B 24–47 remains never-reassign and
untouched). The 18-obs formal support and its namespace are not
used for training; after the 190_f diagnostic they are development
data but remain reserved for descriptive comparison only.

## 2. Frozen numerical budgets (the two 188_s limits)

- **Initial training budget (pilot P0): one seed, at most 300
  optimizer updates OR 8 GPU-hours on the RTX 4090, whichever
  first.** No second seed, longer run, or second configuration
  before the §5 checkpoint review.
- **Prompt-iteration budget: at most 10 CONDUCTOR prompt variants
  across the entire development phase** (variant = any change to
  the conductor system/user template bytes; each is content-hashed
  and logged with its motivation BEFORE its first run).
  `worker_dev` prompts remain CLOSED (103_s): any worker-prompt
  work requires fresh worker instances under a new reviewed plan —
  it is out of scope here.
- Auxiliary caps: at most 6 configuration variants (mixture /
  topology subset / group size / learning rate / checkpoint
  cadence) within P0's compute budget; every variant logged with
  config hash, budget consumed, and result pointer. Exhausting a
  budget STOPS the phase and returns to review — budgets never
  extend retroactively.

## 3. What is retained from the existing machinery (unchanged)

Deterministic pre-materialized payoff surfaces; request/cache
identity (slw-keyed worker cache); complete v2 workflow traces;
worker pool `wp-197e286115f56e4a` at the frozen launch profile;
frozen worker prompts; single 0/0.5/1 reward mapping with
INFRA_RETRY_CODES accounting so infrastructure failures are retried
or excluded, NEVER represented as zero reward; W&B entity
`kencoken` with `WANDB_LOG_MODEL=false`; ollama VRAM check before
every GPU session.

## 4. Provenance freeze before the first optimizer update

Committed before any training: env manifest (source digest,
uv.lock, numerical stack), the pilot's full configuration (content-
hashed), the two namespace definitions, the §2 budget literals, and
the trace/telemetry schema. Each run gets a run root under
`runs/routing-dev/` with config hash, W&B id, seed, per-update
telemetry (reward mean/variance, routing entropy, valid-action
rate, per-worker selection frequencies, cache hit rates), and a
complete trace archive. Every development run is APPEND-ONLY
logged in a `routing_dev_log.md` ledger (config hash → budget →
outcome pointer).

## 5. Pilot P0 and descriptive continuation checks

P0: single-seed GRPO on `routing_dev` populations, group size 8,
conductor prompt v0 = the pinned few-shot prompt as starting point,
mixture/topology per the launch config (frozen at the provenance
freeze). Purpose: observe gradient availability, routing-entropy
trajectory, collapse modes, worker specialization, renderer
sensitivity, and the raw scale of any learning effect.

Continuation is decided at a REVIEWED checkpoint after P0 against
deliberately engineering/descriptive checks (186_s §5), reported
with their measured values — no inferential machinery, no D5-style
geometry:

1. zero infrastructure failures represented as reward (audited
   from traces);
2. valid-action rate ≥ 0.90 sustained over the final third of
   updates (Stage-0C smoke measured 0.9965 untrained — a large
   regression is itself a finding);
3. within-group reward variance nonzero in ≥ 20% of groups over
   the final third (the gradient-availability floor);
4. payoff-distinct worker choices both sampled within ≥ 5% of
   groups on distinct-payoff observations;
5. observed reward trend and routing lift vs the untrained
   baseline on `routing_dev_holdout` — REPORTED with no numeric
   gate; the checkpoint review judges it.

Checks 1–4 failing ⇒ the checkpoint review decides between a
logged configuration/prompt iteration (within §2 budgets) and
stopping the phase. Nothing auto-continues.

## 6. Boundaries

- Development data may never enter a later confirmatory estimate;
  any claim-bearing result requires a NEW reviewed design with a
  frozen hypothesis/estimand/analysis, analysis validation on
  fresh Monte Carlo seeds against the empirically observed
  geometry, and testing with fresh GRPO seeds on disjoint
  populations excluding every development run (186_s §5).
- The D5-affected inferential scope stays isolated: no percentile-
  bootstrap pilot claims are made from this track; D5 follow-up
  method work (186_s §6) is separate and may not be validated by
  its ability to reverse D5.
- This plan does not authorize the 190_f diagnostic (its own plan
  governs it) and does not modify any frozen Stage-0/Stage-1
  artifact.

## 7. Order of operations

1. Reviewer sign-off of this draft (with 190_f).
2. Implement: namespaces + disjointness test, budget literals,
   telemetry/ledger scaffolding; full suite under `-W error`.
3. 190_f diagnostic runs first (its report sets cold-start
   priors); its exposure consequence is already accepted.
4. Provenance freeze commit → P0 → checkpoint review with the §5
   measured checks → iterate within budgets or stop.
