"""P0 spine, Unit 2 — the P0ScienceContract INSTANCE (303_f §9 step
2; 305_f).

The contract is CONSTRUCTED FROM THE AUTHORITATIVE IN-CODE SOURCES
(`p0_replay.REPLAY_SOURCE`, the artifact pins, the pinned mixture's
sentinel ids) — never hand-transcribed (the Unit-1 disclosure is
the reason). It is frozen once to
`plans/conductor/p0/p0_science_contract.json`; consumers load it
through the STRICT schema loader with the EXTERNALLY REVIEWED
`CONTRACT_SHA256` pin."""
from __future__ import annotations

from pathlib import Path

from tasks.conductor.types import InfrastructureError

from . import p0_schema
from .p0_replay import (
    P0_DIR,
    PINNED_MIXTURE_FILE_SHA256,
    PROJECTION_FILE_SHA256,
    PROJECTION_SHA256,
    REPLAY_SOURCE,
    load_pinned_mixture,
)

CONTRACT_PATH = P0_DIR / "p0_science_contract.json"

# the externally reviewed contract identity (recorded by the Unit-2
# review; set after the one-time freeze)
CONTRACT_SHA256 = \
    "d47a63ff435e3b2964f09f0d97f287ee722cae5bbc7df58104d7e10c6d519517"


def build_p0_science_contract() -> p0_schema.P0ScienceContract:
    """Construct the instance from the authoritative sources. Every
    pin flows from code constants that are themselves review-locked;
    the sentinel ids come from the double-bound pinned mixture."""
    from .p0_mixture_v2 import EXPECTED_MIXTURE_V2_RECORD_SHA256
    mixture = load_pinned_mixture()
    sentinel_ids = tuple(sorted(
        mixture["sentinel"]["observation_ids"]))
    pins = REPLAY_SOURCE
    return p0_schema.P0ScienceContract(
        schema_version=p0_schema.SCHEMA_VERSION,
        input_pins=p0_schema.InputPins(
            extension_surface_lock_sha256=pins[
                "extension_surface_lock_sha256"],
            selection_record_sha256=pins["selection_record_sha256"],
            selection_file_sha256=pins["selection_file_sha256"],
            comparator_record_sha256=pins[
                "comparator_record_sha256"],
            pinned_mixture_record_sha256=
                EXPECTED_MIXTURE_V2_RECORD_SHA256,
            pinned_mixture_file_sha256=PINNED_MIXTURE_FILE_SHA256,
            c2_closeout_entry_sha256=pins[
                "c2_closeout_entry_sha256"],
            c2_actions_file_sha256=pins["c2_actions_file_sha256"],
            c2_report_file_sha256=pins["c2_report_file_sha256"],
            c2_schedule_file_sha256=pins["c2_schedule_file_sha256"],
            c2_record_file_sha256=pins["c2_record_file_sha256"],
            c2_identity_manifest_sha256=pins[
                "identity_manifest_sha256"],
            c2_attested_environment_sha256=pins[
                "attested_environment_sha256"],
            c2_projection_sha256=PROJECTION_SHA256,
            c2_projection_file_sha256=PROJECTION_FILE_SHA256),
        scope=p0_schema.ActiveScope(
            q1_direct_cells=("code_atomic", "fork_join",
                             "math_code"),
            q2_description=("coarse, cell-correlated hierarchical "
                            "unlocking (301_f: authorized to be "
                            "TRAINED, not shown learned; "
                            "asymmetric starting conditions "
                            "disclosed)"),
            q3="out_of_scope",
            sentinel_cell="math_atomic",
            sentinel_observation_ids=sentinel_ids,
            sentinel_excluded_from=("direct_q1_gate",
                                    "sizing_minimum",
                                    "authorization", "headline_q1"),
            sentinel_training_exposed=True),
        q1=p0_schema.Q1Rule(
            version="q1-v2", population="bridge_rows",
            event=p0_schema.Q1CountedEvent(
                rule_id="q1-counted-v1",
                valid_completions_only=True, same_group=True,
                high_reward=1.0, high_family_correctness="full",
                low_reward=0.5,
                low_family_correctness="strictly_lower"),
            min_counted_groups_per_cell=2,
            min_distinct_latents_among_counted=2,
            sizing_counts=(("code_atomic", 13), ("fork_join", 34),
                           ("math_code", 13)),
            sizing_epochs=5),
        q2=p0_schema.Q2Rule(
            version="q2-v2",
            marginal_rule_id="q2-marginal-v1",
            marginal_min_target_selections=8,
            marginal_min_distinct_latents=2,
            marginal_population="valid_q2_composite",
            marginal_upstream_correctness_required=False,
            per_direction_targets=(("math_code|w3_favoured", 3),
                                   ("fork_join|w2_favoured", 2)),
            eligibility=p0_schema.EligibilityRule(
                rule_id="c2-eligibility-v1",
                non_code_routing="family_correct",
                code_worker_in=(2, 3),
                malformed_completions="excluded"),
            conditional_rule_id="q2-conditional-v1",
            conditional_numerator="c2_optimal",
            conditional_denominator="c2_eligible",
            conditional_zero_denominator="undefined",
            conditional_baselines=(
                p0_schema.ConditionalBaseline(
                    direction="fork_join|w2_favoured",
                    numerator=8, denominator=152),
                p0_schema.ConditionalBaseline(
                    direction="math_code|w3_favoured",
                    numerator=0, denominator=15)),
            marginal_baselines=(("fork_join|w2_favoured", 73),
                                ("math_code|w3_favoured", 108))),
        sizing=p0_schema.SizingRule(
            target_q1_counted_groups_per_sizing_cell=100,
            groups_per_epoch=157, nominal_epochs=39,
            operational_ceiling_hours=10.0,
            cap=p0_schema.CapRule(
                rule_id="p0-cap-v1",
                launch_epochs="min_nominal_capacity",
                capacity_inputs=(
                    "operational_ceiling_seconds",
                    "cumulative_consumed_seconds",
                    "measured_finalization_reserve_seconds",
                    "frozen_non_rollout_overhead_seconds",
                    "measured_whole_epoch_seconds"),
                capacity_zero_action="stop_reviewed_amendment",
                under_target_action="disclosed_under_target",
                spare_capacity_action="no_extra_training")),
        diagnostics=p0_schema.RequiredDiagnostics(
            items=("q1_counted_by_cell", "q2_eligibility",
                   "q2_optimality",
                   "q2_choice_conditional_on_eligibility",
                   "q2_marginal_target_selections",
                   "direct_and_semantic_contrasts",
                   "sentinel_block", "zero_variance_rate",
                   "invalid_completion_rate"),
            sentinel=p0_schema.SentinelDiagnostics(
                fields_required=(
                    "worker1_selections", "worker1_completions",
                    "reward1_completions", "reward_varying_groups",
                    "q1_counted_groups", "group_denominator",
                    "completion_denominator", "first_group_indices",
                    "first_update_indices", "checkpoint_trajectory",
                    "evaluation_trajectory"))))


def freeze_contract(out_path: str | Path = CONTRACT_PATH) -> str:
    """One-time freeze; returns the contract hash for the review to
    record externally. Refuses to overwrite."""
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the contract is frozen exactly once")
    contract = build_p0_science_contract()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return p0_schema.save_contract(contract, out_path)


def load_p0_science_contract(path: str | Path = CONTRACT_PATH,
                             expected_sha256: str | None = None
                             ) -> p0_schema.P0ScienceContract:
    """The consuming boundary: the strict schema loader with the
    externally reviewed pin."""
    return p0_schema.load_contract(
        path, expected_sha256 or CONTRACT_SHA256)
