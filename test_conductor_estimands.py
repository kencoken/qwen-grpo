"""0A battery: the paired intervention estimand, collision-sensitivity
population identity, B1 reference controls, and the remaining small
contract surfaces (§1.9, §1.11, §1.16, §4)."""

import copy
import dataclasses
import json
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


# Persisted rows carry canonical identities, and their encoded metadata is
# checked against the row, so tests use real ids rather than toy labels.
_CLUSTERS: dict[str, str] = {}


def cluster(label, cell="lookup_math", namespace="construction"):
    """A stable real `latent_program_id` per short test label."""
    key = (label, cell, namespace)
    if key not in _CLUSTERS:
        index = len(_CLUSTERS)
        _CLUSTERS[key] = program.generate_latent(
            cell, namespace, index, PROF).latent["latent_program_id"]
    return _CLUSTERS[key]


def observation(cluster_id, renderer="resource_first", visibility="private"):
    return f"{cluster_id}:{renderer}:{visibility}"


_RENDERERS = ("resource_first", "goal_first", "bound_var")


_AUTO = object()


def outcome(cluster_label, observation_label, *, eligible=True, override=True,
            gold=10, cf=20, base=_AUTO, mutated=_AUTO, followed=True,
            cell="lookup_math"):
    cluster_id = cluster(cluster_label, cell)
    # Deterministic across runs (unlike hash()): distinct labels within a
    # cluster map onto distinct real renderings.
    renderer = _RENDERERS[sum(map(ord, observation_label)) % len(_RENDERERS)]
    # Defaults respect the executor's coherence contract: an ineligible row
    # has no base terminal, and a row's mutated terminal is present exactly
    # when its downstream path succeeded.
    if base is _AUTO:
        base = gold if eligible else None
    if mutated is _AUTO:
        mutated = cf if followed else None
    return EdgeOutcome(cluster_id=cluster_id,
                       observation_id=observation(cluster_id, renderer),
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
    assert report.n_eligible_clusters == 2
    assert report.n_population_clusters == 2
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
    assert dict(report.cluster_observation_counts) == {
        cluster("c1"): 2, cluster("c2"): 1}


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
        outcome("c1", "o2", followed=False),  # path failed -> no terminal
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


@pytest.mark.parametrize("field,value", [
    ("eligible", "false"),                  # truthy string reads as True
    ("override_applied", "false"),
    ("downstream_path_succeeded", "false"),
    ("eligible", 1),                        # int standing in for a bool
    ("gold_answer", True),                  # bool standing in for an int
    ("gold_answer", "10"),
    ("base_terminal", 1.5),
    ("edge", ["n1", "n2"]),                 # list instead of a tuple
    ("edge", ("n1",)),
    ("edge", ("n1", "n9")),                 # node outside the cell
    ("edge", ("n2", "n1")),                 # reversed: direction matters
    ("edge", ("n1", "n1")),                 # self-edge
    ("gold_answer", None),                  # golds are always recorded
    ("counterfactual_gold", None),
])
def test_edge_rows_are_totally_validated(field, value):
    """Without this, `"false"` for the three booleans reports an
    eligibility rate and follow-through of 1.0."""
    rows = [outcome("c1", "o1"), outcome("c1", "o2")]
    bad = dataclasses.replace(rows[0], **{field: value})
    with pytest.raises(InfrastructureError):
        intervention_report([bad] + rows[1:])


def test_fork_sibling_and_reversed_edges_are_not_intervention_edges():
    """fork_join's dependency edges are n1->n3 and n2->n3; a sibling pair
    or a reversed edge is not an edge an intervention can target."""
    rows = [outcome("f1", "o1", cell="fork_join"),
            outcome("f1", "o2", cell="fork_join")]
    for bad_edge in (("n1", "n2"), ("n3", "n1"), ("n2", "n2")):
        bad = dataclasses.replace(rows[0], edge=bad_edge)
        with pytest.raises(InfrastructureError, match="not a dependency edge"):
            intervention_report([bad] + rows[1:])
    for good_edge in (("n1", "n3"), ("n2", "n3")):
        intervention_report([dataclasses.replace(r, edge=good_edge)
                             for r in rows])


def test_atomic_cells_have_no_intervention_edges():
    row = outcome("a1", "o1", cell="lookup_atomic")
    with pytest.raises(InfrastructureError, match="not a dependency edge"):
        intervention_report([row])


def test_report_covers_one_cell_and_split():
    """Stage-1 intervention gates are per cell and edge. `lookup_math` and
    `math_code` both define n1->n2, so a shared edge tuple is not enough to
    prove one population."""
    lm = outcome("c1", "o1", cell="lookup_math")
    mc = outcome("m1", "o2", cell="math_code")
    with pytest.raises(InfrastructureError, match="one \\(cell, split\\)"):
        intervention_report([lm, mc])

    qual_cluster = program.generate_latent(
        "lookup_math", "qualification", 0, PROF).latent["latent_program_id"]
    cross_split = dataclasses.replace(
        lm, cluster_id=qual_cluster,
        observation_id=observation(qual_cluster, "goal_first"))
    with pytest.raises(InfrastructureError, match="one \\(cell, split\\)"):
        intervention_report([lm, cross_split])

    report = intervention_report([lm, outcome("c1", "o2")])
    assert (report.cell_id, report.namespace) == ("lookup_math",
                                                  "construction")


def test_causal_targets_are_cluster_constant():
    """One replacement is drawn per (latent, edge) and each latent is
    rendered several ways, so both targets are latent-level constants."""
    rows = [outcome("c1", "o1", gold=10, cf=20),
            outcome("c1", "o2", gold=11, cf=21)]
    with pytest.raises(InfrastructureError, match="latent-level constant"):
        intervention_report(rows)
    intervention_report([outcome("c1", "o1", gold=10, cf=20),
                         outcome("c1", "o2", gold=10, cf=20)])


def test_replacement_must_change_the_sink():
    """§3 replacements provably change the sink. Equal targets would count
    one execution as both preserving the old answer and following the
    counterfactual, making the diagnostic uninterpretable."""
    with pytest.raises(InfrastructureError, match="must change the sink"):
        intervention_report([outcome("c1", "o1", gold=10, cf=10)])


def test_path_success_and_terminal_availability_must_agree():
    # The executor makes these one fact, so a row where they disagree in
    # either direction is rejected.
    succeeded_no_terminal = dataclasses.replace(
        outcome("c1", "o1", followed=True), mutated_terminal=None)
    with pytest.raises(InfrastructureError,
                       match="must match downstream_path_succeeded"):
        intervention_report([succeeded_no_terminal])
    failed_with_terminal = dataclasses.replace(
        outcome("c1", "o1", followed=False), mutated_terminal=20)
    with pytest.raises(InfrastructureError,
                       match="must match downstream_path_succeeded"):
        intervention_report([failed_with_terminal])
    # A failed path with no terminal is consistent and allowed.
    report = intervention_report([outcome("c1", "o1", followed=False)])
    assert report.follow_through is None


def test_ineligible_row_cannot_have_a_base_terminal():
    """A successful base sink entails its required parents succeeded, so
    such a row cannot be ineligible."""
    bad = dataclasses.replace(
        outcome("c1", "o1", eligible=False, override=False),
        base_terminal=10)
    with pytest.raises(InfrastructureError, match="base_terminal present"):
        intervention_report([bad, outcome("c1", "o2")])


def test_edge_rows_reject_misfiled_identities():
    good = outcome("c1", "o1")
    misfiled = dataclasses.replace(
        good, observation_id=observation(cluster("c2"), "resource_first"))
    with pytest.raises(InfrastructureError, match="filed under"):
        intervention_report([misfiled, outcome("c1", "o2")])


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

def _workflow(cluster_label, obs_label, *, correct=True, detected=False,
              visibility="private", collision=False):
    cluster_id = cluster(cluster_label)
    renderer = _RENDERERS[sum(map(ord, obs_label)) % len(_RENDERERS)]
    return WorkflowOutcome(
        cluster_id=cluster_id,
        observation_id=observation(cluster_id, renderer, visibility),
        visibility_condition=visibility,
        public_numeric_collision=collision, correct=correct,
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


@pytest.mark.parametrize("field,value,why", [
    ("correct", 2, "correct=2 would produce a headline above 1.0"),
    ("correct", 1, "ints must not stand in for bools"),
    ("answer_in_subtask_detected", 0, "ints must not stand in for bools"),
    ("public_numeric_collision", 1, "ints must not stand in for bools"),
    ("visibility_condition", "Private", "silently excluded, not rejected"),
    ("visibility_condition", "", "empty enum value"),
    ("cluster_id", "", "empty identifier"),
    ("observation_id", "", "empty identifier"),
    ("cluster_id", 7, "non-string identifier"),
])
def test_sensitivity_rejects_malformed_persisted_rows(field, value, why):
    """Filtering drops what it does not recognise, so a malformed row must
    fail here rather than quietly entering or leaving the population."""
    rows = [_workflow("c1", "o1"), _workflow("c2", "o2", correct=False)]
    bad = dataclasses.replace(rows[0], **{field: value})
    with pytest.raises(InfrastructureError):
        sensitivity_scores([bad] + rows[1:])


def test_sensitivity_rejects_misfiled_and_mislabelled_rows():
    """The row's own fields must agree with what its ids encode: a
    misfiled observation, or one whose id says `:visible` while the row
    claims `private`, would otherwise score inside the private headline
    population."""
    good = _workflow("c1", "o1")
    other = cluster("c2")
    misfiled = dataclasses.replace(
        good, observation_id=observation(other, "resource_first"))
    with pytest.raises(InfrastructureError, match="filed under"):
        sensitivity_scores([misfiled, _workflow("c2", "o2")])

    mislabelled = dataclasses.replace(
        good, observation_id=observation(cluster("c1"), "resource_first",
                                         "visible"))
    with pytest.raises(InfrastructureError, match="encodes visibility"):
        sensitivity_scores([mislabelled, _workflow("c2", "o2")])


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
    assert baselines.echo_predict("k", count_row.params) is None
    assert baselines.echo_predict("t", count_row.params) == \
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
    observation = program.observation_for(latent, private)
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

    # Disclosure follows the instance's own identity: a private instance
    # cannot carry payloads no matter what the caller has to hand.
    assert "Resources:\n" not in observation
    for payload in registry.union_payload_texts():
        assert payload not in observation

    visible = program.render_instance(latent, "resource_first", "visible")
    visible_observation = program.observation_for(latent, visible)
    assert "Resources:\n" in visible_observation
    for payload in registry.union_payload_texts():
        assert payload in visible_observation


def test_mutated_visibility_with_a_stale_id_is_rejected():
    """Flipping visibility_condition while the id still ends in `:private`
    would disclose payloads into what every later stage counts as a
    private observation."""
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    private = program.render_instance(latent, "resource_first", "private")
    mutated = dict(private, visibility_condition="visible")
    with pytest.raises(InfrastructureError, match="render_instance_id"):
        program.observation_for(latent, mutated)
    for field, value in (("renderer_id", "goal_first"),
                         ("cell_id", "math_atomic"),
                         ("split_id", "train"),
                         ("latent_program_id", "lookup_math:train:00000:"
                                               "deadbeef")):
        with pytest.raises(InfrastructureError, match="render_instance_id"):
            render.build_observation(dict(private, **{field: value}),
                                     program.workflow_steps(latent))


def test_observation_payloads_come_from_the_instances_own_registry():
    """Handles can coincide across instances while the payloads differ, so
    a same-manifest registry must not be able to supply the disclosure."""
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    visible = program.render_instance(latent, "resource_first", "visible")
    handle = visible["public_manifest"][0]
    foreign = copy.deepcopy(visible["private_registry"])
    foreign[handle]["payload"][0][1][0][1] = 424242  # altered value
    observation = program.observation_for(latent, visible)
    assert "424242" not in observation
    own = InstanceRegistry(visible["public_manifest"],
                           visible["private_registry"])
    for payload in own.union_payload_texts():
        assert payload in observation


def test_observation_requires_a_wellformed_identity():
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    instance = program.render_instance(latent, "resource_first", "private")
    for bad in ("bogus", "", "a:b:c:d:e:f",
                instance["render_instance_id"] + ":extra"):
        with pytest.raises(InfrastructureError):
            render.build_observation(dict(instance, render_instance_id=bad),
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


# --- serialization contract (Stage 1 is resumable) --------------------------

def test_immutable_types_survive_deepcopy_and_round_trip_json():
    """Mapping proxies break generic deepcopy/asdict, so these carry an
    explicit persistence form."""
    latent = program.generate_latent("lookup_math", "construction", 0,
                                     PROF).latent
    public = latent["public_params"]
    assert copy.deepcopy(public) is public          # immutable
    revived = type(public).from_json(public.to_json())
    assert dict(revived) == dict(public)
    assert revived.cell_id == public.cell_id

    cluster = latent["latent_program_id"]
    raw = {a: {cluster: {f"{cluster}:resource_first:private": 1}}
           for a in oracle.enumerate_assignments(2)}
    surface = oracle.validate_payoff_surface(raw, "lookup_math")
    assert copy.deepcopy(surface) is surface
    revived_surface = oracle.ValidatedSurface.from_json(surface.to_json())
    assert revived_surface.candidates == surface.candidates
    assert revived_surface.clusters == surface.clusters
    assert revived_surface.accuracy((0, 0)) == surface.accuracy((0, 0))
    json.dumps(surface.to_json())  # actually JSON-encodable

    report = intervention_report([outcome("c1", "o1")])
    assert copy.deepcopy(report) is report
    revived_report = estimands.InterventionReport.from_json(
        json.loads(json.dumps(report.to_json())))
    assert revived_report == report
    assert copy.deepcopy(revived_report) is revived_report
    for bad in ({}, {"edge": ["n1", "n2"]},
                {**report.to_json(), "edge": "n1->n2"},
                {**report.to_json(), "extra": 1}):
        with pytest.raises(InfrastructureError):
            estimands.InterventionReport.from_json(bad)


def test_report_carries_bootstrap_sufficient_statistics():
    """Cluster counts alone cannot reproduce the bootstrap: it resamples
    whole clusters and recomputes the full-sample statistic."""
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c1", "o2", mutated=10),
                                  outcome("c2", "o3")])
    stats = report.cluster_successes
    assert set(stats) == {cluster("c1"), cluster("c2")}
    assert stats[cluster("c1")] == {
        "n_total": 2, "n_eligible": 2, "base": 2, "corrupted": 1,
        "counterfactual": 1, "followed": 2, "followed_successes": 1}
    # Every reported quantity is recoverable from the statistics alone.
    eligible = sum(s["n_eligible"] for s in stats.values())
    assert sum(s["corrupted"] for s in stats.values()) / eligible == \
        pytest.approx(report.corruption_accuracy)
    assert eligible / sum(s["n_total"] for s in stats.values()) == \
        pytest.approx(report.eligibility_rate)
    assert sum(s["followed_successes"] for s in stats.values()) / \
        sum(s["followed"] for s in stats.values()) == \
        pytest.approx(report.follow_through)


def test_statistics_include_clusters_with_no_eligible_observations():
    """A bootstrap resamples the original latent-program population, so a
    fully ineligible cluster must still appear."""
    report = intervention_report([
        outcome("c1", "o1"),
        outcome("c2", "o3", eligible=False, override=False)])
    stats = report.cluster_successes
    assert set(stats) == {cluster("c1"), cluster("c2")}
    assert stats[cluster("c2")] == {
        "n_total": 1, "n_eligible": 0, "base": 0, "corrupted": 0,
        "counterfactual": 0, "followed": 0, "followed_successes": 0}
    assert sum(s["n_eligible"] for s in stats.values()) / \
        sum(s["n_total"] for s in stats.values()) == \
        pytest.approx(report.eligibility_rate)


@pytest.mark.parametrize("mutate", [
    lambda j: j.update(cluster_weighted=None),
    lambda j: j.update(cluster_successes=None),
    lambda j: j.update(cluster_observation_counts=[1, 2]),
    lambda j: j.update(cluster_weighted=["a"]),
    lambda j: j.update(corruption_drop=[0.5]),
    lambda j: j.update(cluster_successes={}),
    lambda j: j.update(cell_id=["lookup_math"]),
    lambda j: j.update(namespace=None),
])
def test_persisted_report_json_is_total(mutate):
    """Malformed persisted values must be domain errors, not raw
    TypeError/AttributeError — and a list-valued mapping would stay
    mutable behind an object claiming to be frozen."""
    report = intervention_report([outcome("c1", "o1")])
    payload = json.loads(json.dumps(report.to_json()))
    mutate(payload)
    with pytest.raises(InfrastructureError):
        estimands.InterventionReport.from_json(payload)


def _stats_report(cluster_stats, cell="lookup_math"):
    """Build report JSON directly from per-cluster counts (bypassing rows),
    to probe impossible sufficient-statistic tables."""
    c = cluster("stats", cell)
    stats = {c: cluster_stats}
    return {
        "cell_id": cell, "namespace": "construction", "edge": ["n1", "n2"],
        "cluster_successes": stats,
        # Deliberately-wrong placeholders; from_json recomputes and would
        # only reach the statistics check if these happened to match.
        "n_total": 0, "n_eligible": 0, "intervention_ineligible": 0,
        "eligibility_rate": 0.0, "n_population_clusters": 0,
        "n_eligible_clusters": 0, "base_accuracy": 0.0,
        "corruption_accuracy": 0.0, "corruption_drop": 0.0,
        "old_answer_persistence": 0.0, "counterfactual_consistency": 0.0,
        "follow_through": None, "follow_through_rate": 0.0,
        "cluster_weighted": {}, "cluster_observation_counts": {},
    }


_GOOD_STATS = {"n_total": 2, "n_eligible": 2, "base": 2, "corrupted": 1,
               "counterfactual": 1, "followed": 2, "followed_successes": 1}


@pytest.mark.parametrize("stats,match", [
    # Targets differ, so one terminal cannot be both corrupted and
    # counterfactual: corrupted + counterfactual > followed.
    ({**_GOOD_STATS, "n_eligible": 1, "n_total": 1, "base": 1,
      "corrupted": 1, "counterfactual": 1, "followed": 1,
      "followed_successes": 1}, "corrupted \\+ counterfactual exceeds"),
    # Every followed success is a counterfactual success.
    ({**_GOOD_STATS, "counterfactual": 0, "followed_successes": 1},
     "followed_successes must equal"),
    ({"n_total": 0, "n_eligible": 0, "base": 0, "corrupted": 0,
      "counterfactual": 0, "followed": 0, "followed_successes": 0},
     "n_total must be >= 1"),
    ({**_GOOD_STATS, "followed": 3}, "followed exceeds n_eligible"),
    ({**_GOOD_STATS, "base": 3}, "base exceeds n_eligible"),
])
def test_impossible_statistic_tables_are_rejected(stats, match):
    with pytest.raises(InfrastructureError, match=match):
        estimands.InterventionReport.from_json(_stats_report(stats))


def test_all_zero_cluster_cannot_pad_the_bootstrap_population():
    """A zero-count cluster would raise n_population_clusters without
    representing an observation the bootstrap can resample."""
    good = cluster("real")
    zero = cluster("zero")
    payload = intervention_report([outcome("real", "o1")]).to_json()
    payload["cluster_successes"][zero] = {
        "n_total": 0, "n_eligible": 0, "base": 0, "corrupted": 0,
        "counterfactual": 0, "followed": 0, "followed_successes": 0}
    with pytest.raises(InfrastructureError, match="n_total must be >= 1"):
        estimands.InterventionReport.from_json(payload)


def test_direct_construction_and_replace_validate_like_from_json():
    """__post_init__ is the source of truth: direct construction and
    dataclasses.replace recompute and compare, so neither is a back door
    around _derive."""
    report = intervention_report([outcome("c1", "o1")])
    with pytest.raises(InfrastructureError):
        dataclasses.replace(report, n_total=999)
    with pytest.raises(InfrastructureError):
        dataclasses.replace(report, corruption_accuracy=0.123)
    # A contradictory hand-built report cannot be constructed at all.
    kwargs = report.to_json()
    kwargs["edge"] = tuple(kwargs["edge"])
    kwargs["eligibility_rate"] = float("nan")
    with pytest.raises(InfrastructureError):
        estimands.InterventionReport(**kwargs)


@pytest.mark.parametrize("field,value", [
    ("n_total", 1.0),                       # float where a count is required
    ("eligibility_rate", float("nan")),     # NaN passes abs()-based compares
    ("base_accuracy", float("inf")),
    ("corruption_drop", 10 ** 400),         # OverflowError in isfinite
])
def test_numeric_fields_are_type_exact_and_finite(field, value):
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c1", "o2", mutated=10)])
    payload = report.to_json()
    payload[field] = value
    with pytest.raises(InfrastructureError):
        estimands.InterventionReport.from_json(payload)


def test_within_tolerance_perturbations_are_canonicalized():
    """The statistics are the source of truth: a float perturbation inside
    the comparison tolerance must not survive the round-trip — it could
    retain an accuracy fractionally above 1 and make the revived report
    unequal to the canonical one."""
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c1", "o2", mutated=10)])
    payload = json.loads(json.dumps(report.to_json()))
    perturbed = dict(payload, base_accuracy=payload["base_accuracy"] + 5e-10)
    revived = estimands.InterventionReport.from_json(perturbed)
    assert revived.base_accuracy == report.base_accuracy  # canonicalized
    assert revived == report
    assert revived.to_json() == report.to_json()
    above_one = dict(payload, base_accuracy=1.0 + 5e-10)
    revived_above = estimands.InterventionReport.from_json(above_one)
    assert revived_above.base_accuracy <= 1.0


def test_report_is_recursively_immutable():
    report = intervention_report([outcome("c1", "o1")])
    with pytest.raises(TypeError):   # inner mapping, not just the outer one
        report.cluster_successes[cluster("c1")]["base"] = 999
    with pytest.raises(TypeError):
        report.cluster_weighted["base_accuracy"] = 0.0


@pytest.mark.parametrize("mutate,match", [
    # Every redundant headline field is recomputed from the per-cluster
    # sufficient statistics and compared, so none of them is forgeable.
    (lambda j: j.update(base_accuracy=1.5), "base_accuracy is 1.5"),
    (lambda j: j.update(n_total="3"), "n_total is"),
    (lambda j: j.update(n_eligible=99), "n_eligible is 99"),
    (lambda j: j.update(eligibility_rate=-0.1), "eligibility_rate is -0.1"),
    (lambda j: j.update(corruption_drop=0.123), "corruption_drop is 0.123"),
    (lambda j: j.update(old_answer_persistence=0.123),
     "old_answer_persistence is 0.123"),
    (lambda j: j.update(follow_through_rate=0.123),
     "follow_through_rate is 0.123"),
    (lambda j: j.update(n_population_clusters=999),
     "n_population_clusters is 999"),
    (lambda j: j.update(n_eligible_clusters=999),
     "n_eligible_clusters is 999"),
    (lambda j: j.update(cluster_weighted={"bogus": 1.0}),
     "cluster_weighted disagrees"),
    (lambda j: j.update(cluster_observation_counts={"bogus": 999}),
     "cluster_observation_counts disagrees"),
    (lambda j: j.update(corruption_accuracy=0.0), "corruption_accuracy is 0.0"),
    (lambda j: j["cluster_successes"].update(bogus={"base": 1}),
     "malformed latent_program_id"),
    (lambda j: j.update(edge=["n2", "n1"]), "not a dependency edge"),
    (lambda j: j.update(cell_id="math_code"), "report is math_code"),
    (lambda j: j.update(namespace="qualification"), "report is"),
])
def test_persisted_report_is_validated_on_load(mutate, match):
    report = intervention_report([outcome("c1", "o1"),
                                  outcome("c1", "o2", mutated=10)])
    payload = json.loads(json.dumps(report.to_json()))
    mutate(payload)
    with pytest.raises(InfrastructureError, match=match):
        estimands.InterventionReport.from_json(payload)


def test_surface_json_round_trip_for_control_kinds():
    clusters = [program.generate_latent("fork_join", "construction", i,
                                        PROF).latent["latent_program_id"]
                for i in range(2)]
    def surface_for(candidates):
        return {c: {cl: {f"{cl}:resource_first:private": 1}
                    for cl in clusters} for c in candidates}
    one_call = oracle.validate_one_call_surface(
        surface_for(oracle.ENDPOINT_IDS), "fork_join")
    two_call = oracle.validate_two_call_surface(
        surface_for(oracle.enumerate_two_call_workflows()), "fork_join")
    for surface in (one_call, two_call):
        revived = oracle.ValidatedSurface.from_json(
            json.loads(json.dumps(surface.to_json())))
        assert revived.candidates == surface.candidates
        assert revived.kind == surface.kind


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
