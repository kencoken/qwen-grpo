"""0A battery: the paired intervention estimand, collision-sensitivity
population identity, B1 reference controls, and the remaining small
contract surfaces (§1.9, §1.11, §1.16, §4)."""

import warnings

import pytest

from tasks.conductor import (
    baselines, contract, estimands, executor, oracle, parser, program, render,
)
from tasks.conductor.estimands import (
    EdgeOutcome, WorkflowOutcome, intervention_report, sensitivity_scores,
)
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.resources import InstanceRegistry
from tasks.conductor.types import CELL_IDS, CELL_NODES, InfrastructureError

PROF = DEFAULT_PROFILE


def outcome(cluster, observation, *, eligible=True, override=True,
            gold=10, cf=20, base=10, mutated=20, followed=True):
    return EdgeOutcome(cluster_id=cluster, observation_id=observation,
                       edge=("n1", "n2"), eligible=eligible,
                       override_applied=override, gold_answer=gold,
                       counterfactual_gold=cf, base_terminal=base,
                       mutated_terminal=mutated,
                       downstream_path_succeeded=followed)


# --- §1.9 paired estimand ---------------------------------------------------

def test_intervention_report_shares_one_eligible_denominator():
    outcomes = [
        outcome("c1", "o1"),                      # follows to the new answer
        outcome("c1", "o2", mutated=10),          # old answer persists
        outcome("c2", "o3"),
        outcome("c2", "o4", eligible=False, override=False),  # excluded
    ]
    report = intervention_report(outcomes)
    assert report.n_total == 4 and report.n_eligible == 3
    assert report.intervention_ineligible == 1
    assert report.eligibility_rate == pytest.approx(0.75)
    assert report.n_clusters == 2
    # §1.9 primary = full-sample over the 3 eligible observations.
    # base = [1, 1, 1] -> 1.0; corrupted = [0, 1, 0] -> 1/3;
    # counterfactual = [1, 0, 1] -> 2/3.
    assert report.base_accuracy == pytest.approx(1.0)
    assert report.corruption_accuracy == pytest.approx(1 / 3)
    assert report.corruption_drop == pytest.approx(2 / 3)
    assert report.old_answer_persistence == report.corruption_accuracy
    assert report.counterfactual_consistency == pytest.approx(2 / 3)
    # Equal-cluster values are reported alongside for paired comparisons
    # and the cluster bootstrap, never as the gate value.
    assert report.cluster_weighted["corruption_accuracy"] == \
        pytest.approx(0.25)
    assert report.cluster_weighted["counterfactual_consistency"] == \
        pytest.approx(0.75)
    assert dict(report.cluster_observation_counts) == {"c1": 2, "c2": 1}


def test_primary_estimate_is_full_sample_not_equal_cluster():
    """§1.9 names full-sample eligible-set accuracy as the primary metric;
    §1.8's cluster weighting is a different rule for a different purpose.
    Two correct observations in one cluster and one incorrect in another
    give 2/3 full-sample but 1/2 under equal-cluster weighting."""
    outcomes = [
        outcome("A", "o1", base=10, gold=10),
        outcome("A", "o2", base=10, gold=10),
        outcome("B", "o3", base=99, gold=10),
    ]
    report = intervention_report(outcomes)
    assert report.base_accuracy == pytest.approx(2 / 3)
    assert report.cluster_weighted["base_accuracy"] == pytest.approx(0.5)


def test_eligibility_rate_accompanies_every_gate():
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c1", "o2", eligible=False,
                                          override=False)])
    for field in ("eligibility_rate", "intervention_ineligible",
                  "n_eligible", "n_total", "follow_through_rate"):
        assert hasattr(report, field)
    assert 0.0 <= report.eligibility_rate <= 1.0


def test_eligible_without_override_is_infrastructure_abort():
    """§1.9: never an ordinary observation."""
    with pytest.raises(InfrastructureError, match="override_applied"):
        intervention_report([outcome("c1", "o1"),
                             outcome("c1", "o2", override=False)])


def test_ineligible_instances_may_lack_override():
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c2", "o2", eligible=False,
                                          override=False)])
    assert report.n_eligible == 1 and report.intervention_ineligible == 1


def test_follow_through_is_secondary_and_conditioned():
    outcomes = [
        outcome("c1", "o1", mutated=20, followed=True),
        outcome("c1", "o2", mutated=99, followed=False),  # path failed
    ]
    report = intervention_report(outcomes)
    assert report.counterfactual_consistency == pytest.approx(0.5)
    assert report.follow_through == pytest.approx(1.0)  # conditioned
    assert report.follow_through_rate == pytest.approx(0.5)


def test_follow_through_uses_the_same_weighting_rule_as_the_primary():
    outcomes = [
        outcome("A", "o1", mutated=20, followed=True),   # consistent
        outcome("A", "o2", mutated=20, followed=True),   # consistent
        outcome("B", "o3", mutated=99, followed=True),   # inconsistent
    ]
    report = intervention_report(outcomes)
    assert report.follow_through == pytest.approx(2 / 3)         # full-sample
    assert report.cluster_weighted["follow_through"] == pytest.approx(0.5)


def test_report_rejects_degenerate_inputs():
    with pytest.raises(InfrastructureError):
        intervention_report([])
    with pytest.raises(InfrastructureError):  # all ineligible
        intervention_report([outcome("c1", "o1", eligible=False,
                                     override=False)])
    with pytest.raises(InfrastructureError):  # duplicate records
        intervention_report([outcome("c1", "o1"), outcome("c1", "o1")])
    mixed = [outcome("c1", "o1"),
             EdgeOutcome("c1", "o2", ("n2", "n3"), True, True,
                         10, 20, 10, 20, True)]
    with pytest.raises(InfrastructureError):  # several edges
        intervention_report(mixed)


def test_base_eligibility_reads_the_base_execution_only():
    latent = program.generate_latent("fork_join", "construction", 0,
                                     PROF).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    steps = [{"subtask": s["subtask"], "resource": s["resource"],
              "access": s["access"]} for s in program.workflow_steps(latent)]
    from test_conductor_executor import perfect_worker
    worker_ids, worker_call = perfect_worker(latent)
    action = parser.routing_to_workflow(worker_ids, steps)
    good = executor.execute_workflow(action, inst["public_prompt"], registry,
                                     worker_call)
    assert estimands.base_eligibility(latent["reference_program"], "n3",
                                      good.steps)

    def fail_first(worker_id, request):
        if steps[0]["subtask"] in request:
            return "no artifact"
        return worker_call(worker_id, request)

    bad = executor.execute_workflow(action, inst["public_prompt"], registry,
                                    fail_first)
    assert not estimands.base_eligibility(latent["reference_program"], "n3",
                                          bad.steps)


# --- §1.16 sensitivity population identity ----------------------------------

def _workflow(cluster, obs, *, correct=True, detected=False,
              visibility="private", collision=False):
    return WorkflowOutcome(cluster_id=cluster, observation_id=obs,
                           visibility_condition=visibility,
                           public_numeric_collision=collision,
                           correct=correct,
                           answer_in_subtask_detected=detected)


def test_sensitivity_uses_the_identical_headline_population():
    outcomes = [
        _workflow("c1", "o1", correct=True, detected=False),
        _workflow("c1", "o2", correct=True, detected=True),   # recoded
        _workflow("c2", "o3", correct=False, detected=False),
        _workflow("c3", "o4", collision=True),                # not headline
        _workflow("c4", "o5", visibility="visible"),          # not headline
    ]
    scores = sensitivity_scores(outcomes)
    assert scores.n_clusters == 2 and scores.n_observations == 3
    assert scores.detected_observations == 1
    assert scores.headline == pytest.approx(0.5)    # c1 = 1.0, c2 = 0.0
    assert scores.penalized == pytest.approx(0.25)  # c1 = 0.5, c2 = 0.0
    assert scores.penalized <= scores.headline      # monotone by construction


def test_sensitivity_equals_headline_without_detections():
    outcomes = [_workflow("c1", "o1"), _workflow("c2", "o2", correct=False)]
    scores = sensitivity_scores(outcomes)
    assert scores.penalized == scores.headline
    assert scores.detected_observations == 0


def test_sensitivity_requires_a_non_empty_headline_stratum():
    with pytest.raises(InfrastructureError):
        sensitivity_scores([_workflow("c1", "o1", visibility="visible")])


def test_sensitivity_rejects_replayed_rows():
    """A duplicated trace would move the cluster mean and n_observations
    while every same-population assertion still passed."""
    duplicated = [_workflow("c1", "o1"), _workflow("c1", "o1"),
                  _workflow("c2", "o2", correct=False)]
    with pytest.raises(InfrastructureError, match="duplicate"):
        sensitivity_scores(duplicated)


def test_sensitivity_rejects_cluster_inconsistent_collision_metadata():
    """Collision status is latent-level: renderings of one cluster cannot
    disagree, or part of a no-collision cluster enters the headline."""
    inconsistent = [_workflow("c1", "o1", collision=False),
                    _workflow("c1", "o2", collision=True),
                    _workflow("c2", "o3")]
    with pytest.raises(InfrastructureError, match="collision metadata"):
        sensitivity_scores(inconsistent)


# --- §1.11 B1 reference controls --------------------------------------------

def _rows(cell, namespace="construction", count=12):
    return [baselines.public_feature_record(
        program.generate_latent(cell, namespace, i, PROF).latent)
        for i in range(count)]


def test_majority_class_control_is_deterministic_and_frozen():
    rows = _rows("code_atomic")
    model_a = baselines.fit_majority_class("code_atomic", rows)
    model_b = baselines.fit_majority_class("code_atomic", rows)
    assert model_a == model_b
    assert set(model_a) <= set(baselines.OBSERVABLE_SUBTYPES["code_atomic"])
    for row in rows:
        prediction = baselines.majority_class_predict(
            model_a, "code_atomic", row.params)
        assert isinstance(prediction, int)


def test_majority_class_tie_rule_prefers_the_lowest_gold():
    rows = _rows("lookup_atomic", count=6)
    tied = [baselines.PublicFeatureRecord(
        cell_id=r.cell_id, latent_program_id=r.latent_program_id,
        namespace=r.namespace, params=r.params, gold_answer=g)
        for r, g in zip(rows, [50, 50, 20, 20, 90, 90])]
    model = baselines.fit_majority_class("lookup_atomic", tied)
    assert model["constant"] == 20  # counts tie at 2 -> lowest value


def test_majority_class_unseen_subtype_is_not_imputed():
    rows = [r for r in _rows("code_atomic", count=12)
            if baselines.observable_subtype("code_atomic", r.params)
            == "count"]
    model = baselines.fit_majority_class("code_atomic", rows)
    select = next(r for r in _rows("code_atomic", count=12)
                  if baselines.observable_subtype("code_atomic", r.params)
                  == "select")
    assert baselines.majority_class_predict(
        model, "code_atomic", select.params) is None


def test_echo_family_only_where_the_parameter_exists():
    assert baselines.echo_family("lookup_math") == ("p", "q")
    assert baselines.echo_family("fork_join") == ("q", "t")
    assert set(baselines.echo_family("code_atomic")) == {"i", "k", "t"}
    assert baselines.echo_family("math_atomic") == ()
    count_row = next(r for r in _rows("code_atomic", count=12)
                     if baselines.observable_subtype("code_atomic", r.params)
                     == "count")
    # `k` does not exist in the count subtype: excluded, never scored.
    assert baselines.echo_predict("k", count_row.public_numeric_values) is None
    assert baselines.echo_predict("t", count_row.public_numeric_values) == \
        count_row.public_numeric_values["t"]


def test_b1_controls_are_construction_only():
    rows = _rows("lookup_math")[:11] + _rows("lookup_math", "qualification", 1)
    with pytest.raises(InfrastructureError):
        baselines.fit_majority_class("lookup_math", rows)


# --- remaining small contract surfaces --------------------------------------

def test_semantic_to_positional_covers_all_six_cells():
    for cell in CELL_IDS:
        nodes = CELL_NODES[cell]
        assignment = tuple(i % 3 for i in range(len(nodes)))
        # Canonical order is the identity permutation.
        assert oracle.semantic_to_positional(assignment, cell, list(nodes)) \
            == list(assignment)
        # Every legal permutation of positions maps node-wise, never by
        # execution order.
        for index in range(4):
            latent = program.generate_latent(cell, "construction", index,
                                             PROF).latent
            positions = latent["reference_program"]["positions"]
            mapped = oracle.semantic_to_positional(assignment, cell,
                                                   positions)
            expected = [assignment[nodes.index(node)] for node in positions]
            assert mapped == expected
        with pytest.raises(ValueError):
            oracle.semantic_to_positional(assignment, cell,
                                          list(nodes) + ["n9"])


def test_noop_correct_at_a_true_zero_index():
    """§1.11/D17: the no-op is not a guaranteed floor — `math_code` permits
    a true intermediate index of 0, and such workflows are reported as
    noop_correct rather than excluded."""
    from test_conductor_executor import make_env, perfect_worker
    found = None
    for index in range(program.namespace_cap("train", "math_code")):
        latent = program.generate_latent("math_code", "train", index,
                                         PROF).latent
        if latent["node_values"]["n1"] == 0:
            found = index
            break
    assert found is not None, "no true-zero index in the math_code namespace"

    latent, inst, registry, steps = make_env("math_code", found,
                                             namespace="train")
    worker_ids, worker_call = perfect_worker(latent)
    action = parser.routing_to_workflow(worker_ids, steps)
    result = executor.execute_workflow(
        action, inst["public_prompt"], registry, worker_call,
        pseudo_workers={1: baselines.noop_worker})
    assert result.steps[0].result.synthetic
    assert result.steps[0].result.value == 0
    noop_correct = result.terminal == inst["gold_answer"]
    assert noop_correct is True  # the substituted zero is the true index


def test_observation_contract_and_visibility_coupling():
    latent = program.generate_latent("fork_join", "construction", 0,
                                     PROF).latent
    private = program.render_instance(latent, "resource_first", "private")
    steps = program.workflow_steps(latent)
    registry = InstanceRegistry(private["public_manifest"],
                                private["private_registry"])
    observation = program.observation_for(latent, private, registry)
    assert observation.startswith("Problem:\n")
    assert f"Resources available: {', '.join(private['public_manifest'])}" \
        in observation
    assert observation.endswith("Choose one worker for each step.")
    # Steps numbered in `positions` order, with resource/access disclosed.
    for position, step in enumerate(steps, start=1):
        resource = step["resource"] or "none"
        previous = "all" if step["access"] == "all" else "none"
        assert (f"{position}. (resource: {resource}; previous results: "
                f"{previous}) {step['subtask']}") in observation

    # Disclosure is derived from visibility_condition alone: passing the
    # registry to a private instance cannot leak payloads into it.
    assert "Resources:\n" not in observation
    for payload in registry.union_payload_texts():
        assert payload not in observation

    visible = program.render_instance(latent, "resource_first", "visible")
    visible_observation = program.observation_for(latent, visible, registry)
    assert "Resources:\n" in visible_observation
    for payload in registry.union_payload_texts():
        assert payload in visible_observation


def test_visible_instance_cannot_omit_its_payloads():
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    visible = program.render_instance(latent, "resource_first", "visible")
    with pytest.raises(InfrastructureError):
        program.observation_for(latent, visible, None)


def test_observation_rejects_mismatched_instance_and_registry():
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    other = program.generate_latent("lookup_math", "construction", 1,
                                    PROF).latent
    visible = program.render_instance(latent, "resource_first", "visible")
    other_instance = program.render_instance(other, "resource_first",
                                             "visible")
    other_registry = InstanceRegistry(other_instance["public_manifest"],
                                      other_instance["private_registry"])
    with pytest.raises(InfrastructureError):
        program.observation_for(latent, visible, other_registry)
    with pytest.raises(InfrastructureError):  # instance/latent mismatch
        program.observation_for(other, visible, other_registry)


def test_observation_requires_a_valid_visibility_condition():
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    instance = program.render_instance(latent, "resource_first", "private")
    tampered = dict(instance, visibility_condition="bogus")
    with pytest.raises(InfrastructureError):
        render.build_observation(tampered, None,
                                 program.workflow_steps(latent))


def test_b4_local_node_request_shape():
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    steps = program.workflow_steps(latent)
    # B4 gives the 3B the same blocks as an endpoint worker, with gold
    # predecessor values; only the final line differs.
    request = baselines.build_b4_request(
        inst, steps[1]["subtask"], None,
        {1: latent["node_values"]["n1"]})
    assert f"Task:\n{steps[1]['subtask']}" in request
    assert f"Previous results:\nstep_1 = {latent['node_values']['n1']}" \
        in request
    assert request.endswith(render.DIRECT_FINAL_LINE)
    assert render.ARTIFACT_FINAL_LINE not in request
    worker = render.build_worker_request(
        inst["public_prompt"], steps[0]["subtask"],
        resource_text=registry.payload_text(steps[0]["resource"]))
    b4_first = baselines.build_b4_request(
        inst, steps[0]["subtask"],
        registry.payload_text(steps[0]["resource"]), None)
    assert b4_first.replace(render.DIRECT_FINAL_LINE, "") == \
        worker.replace(render.ARTIFACT_FINAL_LINE, "")


@pytest.mark.parametrize("completion,expected", [
    ("The answer is\n42", 42),
    ("42\n\n", 42),
    ("  -7  ", -7),
    ("0", 0),
    ("reasoning\n0012", None),      # non-canonical
    ("reasoning\n+5", None),
    ("reasoning\n5.0", None),
    ("reasoning\n1,000", None),
    ("no digits here", None),
    ("", None),
    ("42\nthe end", None),          # last non-empty line wins
])
def test_direct_answer_line_protocol(completion, expected):
    assert contract.parse_answer_line(completion) == expected
