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
| 32 | `32_f_conductor_cell_specs_rev2.md` | **Cell specifications v0.2 — phase-1 freeze candidate**: all critique items applied; replaced modular fixtures; errata vs rev6 |

## Rule for implementation

The contracts in rev6 (per-stage action spaces, reward table, artifact
protocol, executor/scorer split, cache fingerprints, gates) were negotiated
over these six rounds and **must not drift during implementation** — several
exist precisely to resist implementation-time erosion (e.g. the reward-table
boundary prevents infrastructure failures from being gradually reclassified as
format failures). If a contract seems arbitrary or over-strict, its rationale
is in the critique round listed above. Deviations are design changes requiring
review, not implementation details.

Next step in the sequence: reviewer sign-off of the cell specifications v0.2
(`32_f_conductor_cell_specs_rev2.md`) under the two-phase freeze, before any
generator code is written. The signed-off spec supersedes rev6 on the points
listed in its errata section (§6).
