# P0 traceability appendix (GENERATED)

**GENERATED FILE — do not edit.** Every value below is rendered from the authenticated frozen artifacts by `tasks/routing/p0_tables.py`; the committed bytes are compared against a fresh generation in the test suite, so an edited number diverges mechanically (303_f §8).

## 1. Identities

| artifact | semantic sha256 | file sha256 |
| --- | --- | --- |
| P0ScienceContract (`p0_science_contract.json`) | `d47a63ff435e3b2964f09f0d97f287ee722cae5bbc7df58104d7e10c6d519517` | `8b348b0fae433a775e2bcfe4d29a9d7a26a7389ae88b98f5b95a5d0e968de611` |
| compatibility projection (`c2_compatibility_projection.json`) | `f1912078fb27e67c489705737295bac461033324d58600825d944b5a12bf6355` | `41f15c5d27ee1c9867bc82833bd088319c5644f1c0a86096844442b4306446c3` |
| pinned mixture (`pinned_mixture_v2.json`) | `135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f` | `b305d9c808d21ba8ced0c21b01076497160527ba8164d588df35e20417a7deb6` |

Replay-source pins (Unit 1, all verified against the committed C2 evidence):

| pin | sha256 |
| --- | --- |
| `attested_environment_sha256` | `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42` |
| `c2_actions_file_sha256` | `8e705317676134df447b25a72532151c8068bb238a239facc266c1fb5525af34` |
| `c2_closeout_entry_sha256` | `2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558cf36174266fbe` |
| `c2_record_file_sha256` | `cc42c16bd925282477746644e5959a5d5848c47e18308a8fc69a437fac8e27b6` |
| `c2_report_file_sha256` | `03152f0eaa7e83b34110dc6e53be550f0f761d6141861246a70f55f5587e3abe` |
| `c2_schedule_file_sha256` | `c2687919cd8a00768d9f5b148957f2c2013eb1b0a636f13ecb585d6bd5598b25` |
| `comparator_record_sha256` | `9220c2c7a7efe890c60e5abbdcc3b84eecbbb971e75fa69e313e6d61888e5f1f` |
| `extension_surface_lock_sha256` | `ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b` |
| `identity_manifest_sha256` | `7b19aeb9a642478785db1aa0d24e9126cf6d6ad3358c46b6c6a44b4dd82514af` |
| `pinned_mixture_record_sha256` | `135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f` |
| `selection_file_sha256` | `e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724` |
| `selection_record_sha256` | `c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34` |

## 2. Active scope (301_f)

| field | value |
| --- | --- |
| Q1 direct cells | code_atomic, fork_join, math_code |
| Q2 | coarse, cell-correlated hierarchical unlocking (301_f: authorized to be TRAINED, not shown learned; asymmetric starting conditions disclosed) |
| Q3 | out_of_scope |
| sentinel cell | math_atomic |
| sentinel observation ids | `math_atomic:routing_dev:00000:a2799752:bound_var:private` / `math_atomic:routing_dev:00000:a2799752:goal_first:private` / `math_atomic:routing_dev:00000:a2799752:resource_first:private` |
| sentinel excluded from | direct_q1_gate, sizing_minimum, authorization, headline_q1 |
| sentinel training-exposed | True |

## 3. Q1 (rule `q1-v2`, event `q1-counted-v1`)

Counted event: a reward-1.0 completion of full family correctness AND a reward-0.5 completion of strictly_lower family correctness, valid completions only, in the same group.

Gate: >= 2 counted groups AND >= 2 distinct latents per cell.

| cell | C2 counted groups (over 5 epochs) | measured per-epoch rate | bridge draws | distinct latents | pass |
| --- | --- | --- | --- | --- | --- |
| code_atomic | 13 | 2.6 | 30 | 8, 10 | True |
| fork_join | 34 | 6.8 | 195 | 24, 41, 43, 44, 46 | True |
| math_code | 13 | 2.6 | 195 | 11, 15, 16, 19, 20, 21, 27 | True |

## 4. Q2 (rule `q2-v2`) — the four separated quantities

1. **Marginal** (`q2-marginal-v1`): target selections over VALID completions regardless of upstream correctness; gate >= 8 selections from >= 2 distinct latents per direction.
2. **Eligibility** (`c2-eligibility-v1`): family_correct non-Code routing, Code choice in (2, 3), malformed excluded.
3. **Conditional** (`q2-conditional-v1`): c2_optimal / c2_eligible; zero denominator = undefined (never 0.0) — the P0 learning estimand.
4. **Contrasts**: direct (both family-correct variants in one group) and semantic (reward levels 1 and 0.5 co-present).

| direction | target worker | C2 marginal selections (baseline) | distinct latents | conditional baseline (optimal/eligible) | gate pass |
| --- | --- | --- | --- | --- | --- |
| math_code\|w3_favoured | 3 | 108 | 7 | 0/15 | True |
| fork_join\|w2_favoured | 2 | 73 | 14 | 8/152 | True |

The asymmetric starting conditions (301_f) are carried as context: the conditional baselines above are materially different between directions.

## 5. Sentinel — the COMPLETE signed obligation set (305_f §4)

Every field of `contract.diagnostics.sentinel.fields_required`, with its C2 checkpoint-zero value where the frozen projection carries it (316_s: nothing omitted — deferred fields are named as deferred, never dropped):

| required field | C2 checkpoint-zero value | source |
| --- | --- | --- |
| `worker1_selections` | 0 | frozen projection |
| `worker1_completions` | 0 | frozen projection |
| `reward1_completions` | 0 | frozen projection |
| `reward_varying_groups` | 0 | frozen projection |
| `q1_counted_groups` | 0 | frozen projection |
| `group_denominator` | 15 | frozen projection (`groups`) |
| `completion_denominator` | computed by `sentinel_checkpoint_block` (the legacy C2 block does not persist it) | every P0 checkpoint |
| `first_group_indices` | worker1=None; reward1=None; varying=None; q1_counted=None | frozen projection |
| `first_update_indices` | worker1=None; reward1=None; varying=None; q1_counted=None | frozen projection |
| `checkpoint_trajectory` | assembled across checkpoints by `p0_launch.assemble_sentinel_trajectories` | instance at the P0 run |
| `evaluation_trajectory` | assembled across checkpoints by `p0_launch.assemble_sentinel_trajectories` | instance at the P0 run |

## 6. Sizing and the cap (rule `p0-cap-v1`)

| field | value |
| --- | --- |
| target Q1 counted groups per sizing cell | 100 |
| groups per epoch | 157 |
| nominal epochs (C2-derived) | 39 |
| derived groups | 6123 |
| minimum cell | code_atomic |
| operational ceiling (hours) | 10.0 |
| launch rule | `min_nominal_capacity` (launch = min(nominal, capacity)) |
| capacity <= 0 | `stop_reviewed_amendment` |
| capacity < nominal | `disclosed_under_target` |
| capacity >= nominal | `no_extra_training` |
| registered capacity inputs | `operational_ceiling_seconds` / `cumulative_consumed_seconds` / `measured_finalization_reserve_seconds` / `frozen_non_rollout_overhead_seconds` / `measured_whole_epoch_seconds` |

## 7. C2 measured results (from the frozen projection)

| population | draws |
| --- | --- |
| anchor | 75 |
| bridge | 420 |
| direct_specialist_control | 25 |
| goal_first_control | 90 |
| q2_composite | 160 |
| sentinel | 15 |

| quantity | value |
| --- | --- |
| valid completions | 6242 |
| invalid completions | 38 |
| zero-variance groups | 662 |
| zero-variance fraction | 0.8433 |
| Q1 gate (all cells) | True |
| Q2 cold-start gate | True |
| preregistered decision | **Q1 + Q2 hierarchical-unlocking authorized** |

## 8. Signed traceability matrix (316_s)

The merge-gated mapping: requirement → contract field → enforcement → regression → artifact. Deferred obligations are NAMED with their owner, never dropped.

| requirement | field | enforcement | regression | artifact |
| --- | --- | --- | --- | --- |
| Q1 counted event (305_f §3) | `q1.event` (`q1-counted-v1`) | `p0_estimands.q1_counted_event` (closed literals operative) | `test_p0_estimand_rules` incl. the semantic-not-Q1 counterexample | contract |
| Q1 direct gate | `q1.min_counted_groups_per_cell` = 2; `q1.min_distinct_latents_among_counted` = 2 | `p0_estimands.evaluate_q1_gate` | `test_p0_estimand_rules`; oracle `q1_gate` equality | contract + projection |
| Q1 population = bridge rows | `scope.q1_direct_cells`; mixture `class_assignment` | `derive_from_trace` population binding; `p0_schedule.population_of` (authenticated internal load) | `test_p0_c2_replay_sensitivity` population substitution; 310_s forged-mixture regression | mixture |
| Q2 marginal cold-start gate | `q2.marginal_*` (`q2-marginal-v1`) | `marginal_target_selection` + `evaluate_q2_cold_start_gate` (structurally never conditional) | `test_p0_estimand_rules` incl. the marginal-not-conditional counterexample | contract |
| Q2 eligibility | `q2.eligibility` (`c2-eligibility-v1`) | `c2_eligible_completion` + `valid_assignment` | 313_s malformed-assignment regressions | contract |
| Q2 conditional choice | `q2.conditional_*` (`q2-conditional-v1`); zero denominator = undefined | `conditional_choice` (None, never 0.0) | `test_p0_estimand_rules` | contract |
| Q2 contrasts | `diagnostics.items` | `group_contrasts` (cell-aware, valid assignments only) | `test_p0_estimand_rules` | contract |
| Sentinel complete block (305_f §4) | `diagnostics.sentinel.fields_required` (see §5) | `sentinel_checkpoint_block` + `sentinel_legacy_view` | `test_p0_sentinel_estimand` ([2]/[3]; population bound; forged index) | contract + projection |
| Schedule identity | `sizing.groups_per_epoch` = 157; mixture pins | `p0_schedule` double bindings; `derive_from_trace` physical-position binding | `test_p0_schedule_loader_reminders`; 313_s same-id swap | mixture |
| Exact C2 equivalence (303_f §3) | every projection field | `verify_c2_equivalence` (field-for-field + pin rehash) | `test_p0_c2_replay_equivalence` under independence guards | projection |
| Sizing derivation | `q1.sizing_counts`; `sizing.nominal_epochs` = 39 | `p0_estimands.derive_sizing`; `_validate_against_projection` | `test_p0_estimand_rules`; `test_p0_contract_cross_checks_the_projection` | contract + projection |
| Cap + launch (305_f §5) | `sizing.cap` (`p0-cap-v1`) | `p0_cap.derive_launch_plan`; `require_launchable` (rederive-and-compare, type-sensitive) | `test_p0_cap_arithmetic` (branches; legacy parity; forged plans) | contract |
| Launch-freeze persistence (all cap inputs + all three values) | the `derive_launch_plan` record | `p0_launch.build_p0_launch_freeze` (admits through `require_launchable`; typed `LaunchPlan` must round-trip to the record VERBATIM; stop branch unfreezable) | `test_p0_launch_freeze_schema` | P0LaunchFreeze schema (instance frozen post-merge, after val/cycle/beta) |
| Checkpoint/evaluation trajectories | `diagnostics.sentinel.fields_required` trajectories | `p0_launch.assemble_sentinel_trajectories` (exact frozen index sets w/ mandatory checkpoint zero and final; semantic counter/denominator/first-index validation; deep-copied blocks; producer invariants under the canonical profile; explicit infrastructure-abort prefixes). The EXPECTED INDEX SETS themselves remain DEFERRED: bound through the authenticated P0ExecutionIdentity (post-merge) | `test_p0_sentinel_trajectories` | P0 run record (instance at the P0 run) |
| Dataset preparation (the first real consumer) | `P0LaunchFreeze` (all fields; execution-manifest hash and terminal hashes excluded by the closed schema) | `p0_launch.prepare_p0_dataset` (freeze under its REQUIRED reviewed hash; contract pin equality; plan REDERIVED; runtime BOUND to the canonical profile + the ACTUAL prompt; fresh `verify_c2_equivalence` + `verify_appendix`; strict schedule loader) | `test_p0_first_consumer_prepare` | dataset bundle (runtime; never an authorization) |
| Launch admission (execution + precursor binding) | precursor pins; `runtime.attested_environment_sha256`; the EXTERNAL execution-manifest argument (305_f §1); cadence/eval/telemetry identity | **DEFERRED** to the post-merge unit constructing the real `P0LaunchFreeze` instance and its authenticated `P0ExecutionIdentity` (the home for cadence/eval/telemetry binding) — the precursor artifacts do not exist yet, so their resolution cannot be genuinely enforced and is NOT marked complete (321_s/323_s) | DEFERRED (post-merge) | P0LaunchFreeze instance + admission record (future) |
| Appendix divergence gate (303_f §8) | this file | `verify_appendix` (raw byte equality) | `test_p0_traceability_appendix` (edited number; CRLF rewrite; diverging artifact) | appendix |

## 9. Supersession and lineage (references)

- Formal Q3 is out of scope (269_s; closed in 301_f); Q2 is authorized to be TRAINED, not shown learned (300_s/301_f).
- math_atomic is the training-exposed sentinel (283_s route; 290_f signed wrap-up; erratum 289_f) — excluded from gates, sizing, authorization, and headline Q1.
- The Unit-B mixture (274_f) is superseded by the B2 mixture (291_f-295_f); the C1 exposure sample (281_f) is superseded as the sizing basis by C2 (296_f-299_f, closed 300_s/301_f).
- The spine artifacts derive from the signed plan chain 287_f -> 303_f (rev2) -> 305_f (rev3); units 306_f/308_f, 309_f/311_f, 312_f/314_f.
