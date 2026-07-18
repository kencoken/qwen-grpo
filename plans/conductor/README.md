# Conductor planning archive

The complete planning lineage for the toy-Conductor project (Phase E of the
repo roadmap): a task-preparation brief, a task proposal, and six plan
revisions produced through alternating review rounds between two parties.

**The canonical build specification is [`13_f_plan_rev6.md`](13_f_plan_rev6.md).**
All other documents are context: they record how and why its contracts were
reached. The agreed framing and pre-registered dynamics predictions are in
[`21_f_where_we_landed_synthesis.md`](21_f_where_we_landed_synthesis.md).

## Naming convention

`NN_x_name.md` — `NN` orders the lineage; `x` is authorship: `f` = first
party (implementation side), `s` = second party (external reviewer).

## Lineage

| # | Document | Role |
|---|---|---|
| 00 | `00_f_task_prep.md` | Self-contained briefing: context, objectives, constraints, open forks |
| 01 | `01_s_task_proposal.md` | Task proposal: typed micro-workflow environment, worker pool, staging |
| 02 | `02_f_plan.md` | Plan v1: Stages 0–1 on the proposal |
| 03 | `03_s_plan_critique.md` | Critique 1: runtime lifecycle, causal necessity / opaque payloads, backend discipline, cache-key completeness, executable demos |
| 04 | `04_s_plan_data_proposal_alternative.md` | Alternative data design: anti-shortcut typed workflows (semantics-before-language, payoff vectors, splits, shortcut audit) |
| 05 | `05_f_plan_rev2.md` | Plan v2: adopts the alternative architecture, populated incrementally |
| 06 | `06_s_plan_rev2_critique.md` | Critique 2: vertical-slice staging, tagged worker protocol (not JSON), visibility ≠ authorization, harness-ready vs semantic-claim gate split |
| 07 | `07_f_plan_rev3.md` | Plan v3: vertical slice first; integer-only v0; six cells |
| 08 | `08_s_plan_rev3_critique.md` | Critique 3: Stage 2 = worker_id only; resource limits + legal topologies; artifact-contract completion; reference-free execution; reward-table boundary (0.0 = malformed action, 0.5 = well-formed failure); three direct baselines; payoff enumeration |
| 09 | `09_f_plan_rev4.md` | Plan v4: locked contracts |
| 10 | `10_s_plan_rev4_critique.md` | Critique 4: routing-only output schema (extra fields rejected — credit-assignment leak); executor/scorer split (no gold in executor); deployable vs hindsight oracle; corruption vs counterfactual-consistency; cache fingerprints |
| 11 | `11_f_plan_rev5.md` | Plan v5: final spec pass applied |
| 12 | `12_s_plan_rev5_critique.md` | Critique 5 (sign-off): numeric gate completions; two-phase cell-spec freeze; sequential sampling (optional-stopping protection); never-reselect-oracle |
| 13 | `13_f_plan_rev6.md` | **Plan rev6 — the canonical, signed-off build spec** |
| 20 | `20_s_where_we_landed.md` | Reviewer's answers to the pre-implementation questions (data examples, what is tested, paper mapping, expected dynamics) |
| 21 | `21_f_where_we_landed_synthesis.md` | **Agreed synthesis**: wind-tunnel framing, `SELF(answer)` requirement, relaxation ladder, pre-registered dynamics predictions |
| 30 | `30_f_conductor_cell_specs.md` | Cell specifications v0.1: six executable cell specs, machine-verified fixtures, nine flagged decisions |
| 31 | `31_s_conductor_cell_specs_critique.md` | Cell-spec critique: observation/request contracts, tagged resource layouts, mediator interventions, ablation rejections, failure propagation, distributions |
| 32 | `32_f_conductor_cell_specs_rev2.md` | Cell specifications v0.2: observation/request contracts, tagged layouts, mediator interventions, ablation rejections, replaced modular fixtures |
| 33 | `33_s_conductor_cell_specs_rev2_critique.md` | Rev2 critique: six phase-1 blockers (IR operand refs, scheduler aliasing, semantic fork oracle, baseline executability, single-mutation interventions, audit scope) + pre-screening fixes |
| 34 | `34_f_conductor_cell_specs_rev3.md` | Cell specifications v0.3: operand IR refs, factorial scheduler, semantic oracle, executable baselines, single-mutation interventions, D15 collision flag |
| 35 | `35_s_conductor_cell_specs_rev3_critique.md` | Rev3 critique: four blockers (T3 vs affine schema, block-seed scheduler, six-cell oracle table, node-level collisions) + truncation telemetry split |
| 36 | `36_f_conductor_cell_specs_rev4.md` | Cell specifications v0.4: `mul_add` op; block-seeded scheduler; node-id oracle; node-level collision metadata; truncation telemetry split |
| 37 | `37_s_conductor_cell_specs_rev4_critique.md` | Rev4 critique ("approve after one small rev4.1 patch"): seed-derivation regression, B2 dual channel, intervention position mapping + estimand, executable tie-breaking, cache/visibility contradiction, pseudo-worker contract |
| 38 | `38_f_conductor_cell_specs_rev4_1.md` | Cell specifications v0.4.1: seed derivations restored, B2 dual channel, positional interventions, executable tie-breaking, worker-visible cache fingerprint, pseudo-worker contract |
| 39 | `39_s_conductor_cell_specs_rev4_1_critique.md` | Rev4.1 critique (architecture approved): six final errata — demand-driven resource checks, dual look schedules, restored best-fixed/random/regret controls, sensitivity-score population, profile symbols, edge-label bytes |
| 40 | `40_f_conductor_cell_specs_rev4_2_errata.md` | v0.4.2 errata: demand-driven resource checks, dual look schedules, restored controls, sensitivity-score population, profile symbols, edge-label bytes |
| 41 | `41_s_conductor_cell_specs_rev4_2_errata_critique.md` | Errata critique (architecture approved): six contract interactions — cell-scoped bands, global AST precedence, §1.13 schedule sync, signed gap, detector-proxy wording, predictor feature contract |
| 42 | `42_f_conductor_cell_specs_rev5.md` | Cell specifications rev5 (v0.5): consolidation of 38_f + 40_f with the six 41_s corrections folded in |
| 43 | `43_s_conductor_cell_specs_rev5_critique.md` | Rev5 critique ("approve after two small corrections; targeted diff check sufficient"): observable-subtype provenance leak in B1; profile-domain validation |
| 44 | `44_f_conductor_cell_specs_rev6.md` | **Cell specifications rev6 (v0.6) — phase-1 freeze candidate**: observable-subtype level lists for B1 controls; profile-domain validation + invalid-profile tests; intervention replacements from tunable value bands; awaiting targeted diff check |

## Rule for implementation

The contracts in rev6 (per-stage action spaces, reward table, artifact
protocol, executor/scorer split, cache fingerprints, gates) were negotiated
over these six rounds and **must not drift during implementation** — several
exist precisely to resist implementation-time erosion (e.g. the reward-table
boundary prevents infrastructure failures from being gradually reclassified as
format failures). If a contract seems arbitrary or over-strict, its rationale
is in the critique round listed above. Deviations are design changes requiring
review, not implementation details.

Next step in the sequence: targeted diff check of the cell specifications
rev6 (`44_f_conductor_cell_specs_rev6.md`; the diff vs rev5 is confined to
the `[rev6]` markers). On sign-off, rev6 is copied verbatim to the
repository root as the frozen canonical `conductor_cell_specs.md`, the spec
supersedes the rev6 *plan* contract on the points proposed in its errata
section (§6), and the D15 collision-flag choice freezes with the other
rejection-rule kinds; Stage-0A code then begins, with the endpoint system
prompts (D16) as a separate reviewed freeze before the construction
screen.
