import json
from dataclasses import replace

from tasks.conductor import contract, q3_discovery


def _lat(strategy="strategy3", revision="v1", namespace="dev", index=0):
    return q3_discovery.generate_latent(
        strategy, revision, namespace, index)


def test_q3_latent_generation_is_deterministic_and_namespaced():
    left = _lat()
    assert left == _lat()
    assert left != _lat(namespace="fresh")
    assert left != _lat(revision="v2")
    assert left.sequence[:len(left.unique_sequence)] == left.unique_sequence
    assert len(set(left.references.values())) == len(left.references)
    assert left.references["intermediate"] == q3_discovery.program.count_gt(
        list(left.unique_sequence), left.threshold)


def test_q3_strategy_crossings_and_task_last_contract():
    latent = _lat()
    cases = q3_discovery.cases_for_latent(
        latent, q3_discovery.RENDERERS, "canonical")
    assert len(cases) == 4 * 3
    assert {
        (case.condition, case.renderer) for case in cases
    } == {
        (condition, renderer)
        for condition in q3_discovery.STRATEGY_CONDITIONS["strategy3"]
        for renderer in q3_discovery.RENDERERS
    }
    for case in cases:
        text = case.user_message
        assert text.index("Problem:\n") < text.index("Resource:\n")
        assert text.index("Resource:\n") < text.index(
            "Previous results:\n")
        assert text.index("Previous results:\n") < text.index("Task:\n")
        assert text.endswith(q3_discovery.render.TASK_LAST_FINAL_LINE)
        assert case.previous_results == {1: latent.count_index}

    # Renderer changes the Problem bytes, not the assigned target Task.
    for condition in q3_discovery.STRATEGY_CONDITIONS["strategy3"]:
        target_cases = [case for case in cases
                        if case.condition == condition]
        assert len({case.public_prompt for case in target_cases}) == 3
        assert len({case.task_block for case in target_cases}) == 1

    # The declaration must preserve the non-lexical CLI renderer order;
    # verification later regenerates case files from this exact order.
    _, ordered_cases = q3_discovery.build_strategy_cases(
        "strategy1", "s1-v2", "renderer_order", 0, 1,
        ("goal_first", "bound_var"), "canonical")
    declaration = q3_discovery._generation_declaration(  # noqa: SLF001
        [q3_discovery.generate_latent(
            "strategy1", "s1-v2", "renderer_order", 0)],
        ordered_cases,
    )
    assert declaration["renderers"] == ["goal_first", "bound_var"]

    subset_latents, subset_cases = q3_discovery.build_strategy_cases(
        "strategy3", "s3-v1", "condition_subset", 0, 2,
        ("goal_first", "bound_var"), "canonical",
        ("direct_literal", "nested_bound"))
    subset_declaration = q3_discovery._generation_declaration(  # noqa: SLF001
        subset_latents, subset_cases)
    assert subset_declaration["conditions"] == [
        "direct_literal", "nested_bound"]
    assert len(subset_cases) == 2 * 2 * 2


def test_q3_generated_reference_artifacts_agree_with_frozen_tool():
    for strategy in q3_discovery.STRATEGY_CONDITIONS:
        latents, cases = q3_discovery.build_strategy_cases(
            strategy, "v1", f"{strategy}_dev", 0, 6,
            ("goal_first", "bound_var"), "canonical")
        assert len(latents) == 6
        for case in cases:
            q3_discovery.validate_reference_agreement(case)
            body = case.reference_artifact
            assert body.startswith(("at(", "count_gt("))
            assert not body.startswith(("stable_unique(", "rotate_left("))


def test_q3_alternate_wording_changes_task_not_semantics():
    latent = _lat(strategy="strategy1")
    canonical = q3_discovery.cases_for_latent(
        latent, ("goal_first",), "canonical")
    alternate = q3_discovery.cases_for_latent(
        latent, ("goal_first",), "alternate")
    assert [case.reference_target for case in canonical] == [
        case.reference_target for case in alternate]
    assert [case.reference_artifact for case in canonical] == [
        case.reference_artifact for case in alternate]
    assert [case.task_block for case in canonical] != [
        case.task_block for case in alternate]


def test_q3_failure_taxonomy_separates_parse_binding_value_and_wrong_target():
    latent = _lat()
    cases = q3_discovery.cases_for_latent(
        latent, ("goal_first",), "canonical")
    by_condition = {case.condition: case for case in cases}

    bound = by_condition["nested_bound"]
    parse_completion = "<artifact>stable_unique(resource)</artifact>"
    parse_result = contract.run_worker_output(
        2, parse_completion, bound.binding())
    assert q3_discovery.classify_failure(
        bound, parse_result, parse_completion) == "parse/grammar"

    wrong_target_completion = (
        f"<artifact>{latent.reference_artifacts['nested_literal']}</artifact>"
    )
    wrong_target_result = contract.run_worker_output(
        2, wrong_target_completion, bound.binding())
    assert q3_discovery.classify_failure(
        bound, wrong_target_result, wrong_target_completion
    ) == "over-composition/wrong target"

    used = {latent.count_index, latent.literal_index}
    other_index = next(index for index in range(len(latent.unique_sequence))
                       if index not in used)
    binding_completion = (
        "<artifact>at(rotate_left(stable_unique(resource), "
        f"{latent.rotation}), {other_index})</artifact>"
    )
    binding_result = contract.run_worker_output(
        2, binding_completion, bound.binding())
    assert binding_result.status == "success"
    assert q3_discovery.classify_failure(
        bound, binding_result, binding_completion
    ) == "predecessor/binding"

    side_probe = q3_discovery.cases_for_latent(
        q3_discovery.generate_latent(
            "strategy1", "v2", "dev", 0),
        ("goal_first",), "canonical")[0]
    intermediate = replace(
        side_probe,
        previous_results={},
        binding_sha256=q3_discovery.binding_sha256(
            q3_discovery.Binding(
                resources={
                    side_probe.handle: q3_discovery.IntegerList(
                        payload=side_probe.sequence),
                },
                steps={},
            )),
        reference_target=latent.references["intermediate"],
        reference_artifact=(
            "count_gt(stable_unique(resource), "
            f"{latent.threshold})"),
        alternate_targets={},
    )
    value_completion = (
        "<artifact>count_gt(stable_unique(resource), 999)</artifact>"
    )
    value_result = contract.run_worker_output(
        2, value_completion, intermediate.binding())
    assert value_result.status == "success"
    assert q3_discovery.classify_failure(
        intermediate, value_result, value_completion
    ) == "threshold/index/value"


def _metric_row(case_id, condition, renderer, worker_id, correct):
    return {
        "case_id": case_id,
        "worker_id": worker_id,
        "strategy_id": "strategy1",
        "strategy_revision": "v1",
        "split": "dev",
        "namespace": "dev",
        "latent_id": "latent0",
        "paired_latent_id": "pair0",
        "latent_index": 0,
        "renderer": renderer,
        "wording_family": "canonical",
        "condition": condition,
        "target_node": "n1",
        "target_scope": "terminal",
        "semantic_factors": {"target_condition": condition},
        "request_sha256": f"request-{case_id}",
        "request_text": f"request {case_id}",
        "reference_target": 7,
        "semantic_correct": correct,
        "status": "success",
        "parse_status": "legal",
        "failure_class": None if correct else "threshold/index/value",
    }


def test_q3_metrics_router_stability_and_group_of_eight():
    rows = []
    renderers = ("resource_first", "goal_first", "bound_var")
    for renderer in renderers:
        # Condition A: w2 unique twice, tied once.
        c2 = True
        c3 = renderer == "resource_first"
        case = f"A-{renderer}"
        rows += [
            _metric_row(case, "A", renderer, 2, c2),
            _metric_row(case, "A", renderer, 3, c3),
        ]
        # Condition B: w3 unique under all three renderers.
        case = f"B-{renderer}"
        rows += [
            _metric_row(case, "B", renderer, 2, False),
            _metric_row(case, "B", renderer, 3, True),
        ]

    summary = q3_discovery.summarize_rows(rows, {"A": 2, "B": 3})
    assert summary["rendered_observation_metrics"]["only_w2_correct"] == 2
    assert summary["rendered_observation_metrics"]["only_w3_correct"] == 3
    assert summary["routing"]["semantic_router_accuracy"] == 1.0
    assert summary["routing"]["best_fixed_accuracy"] == 4 / 6
    stable = summary["renderer_stability"]
    assert stable["renderer_stable_unique_win_targets"] == {
        "w2": 1, "w3": 1}
    assert stable["strict_all_three_unique_win_targets"] == {"w3": 1}
    assert stable["paired_latents_with_stable_w2_and_w3_conditions"] == 1
    expected = (5 / 6) * (1 - 2 * 0.5 ** 8)
    assert summary["group_of_eight_projection"][
        "iid_uniform_worker_sampling_nonzero_diversity_probability"
    ] == expected
    json.dumps(summary)


def test_q3_baseline_regenerates_exact_retained_case_set():
    cases = q3_discovery.build_baseline_cases()
    assert len(cases) == 4
    assert {case.expected_direction for case in cases} == {
        "both", "w2", "w3", "w2_legal_semantic_w3"}
    assert all(case.source_case_id for case in cases)
    assert all(case.reference_target is not None for case in cases)


def test_q3_checkpoint_evidence_is_exact_and_resume_merge_is_fail_closed():
    report = [
        {
            "model_id": model_id,
            "revision": revision,
            "workers": expected["workers"],
            "loaded": False,
            "measured_parameters": None,
        }
        for (model_id, revision), expected
        in q3_discovery.EXPECTED_CHECKPOINTS.items()
    ]
    assert not q3_discovery._checkpoint_report_identity(  # noqa: SLF001
        [], require_loaded=True)
    assert not q3_discovery._checkpoint_report_identity(  # noqa: SLF001
        report, require_loaded=True)

    rows = [
        {"worker_name": "code_1p5b", "physical_generation": True},
        {"worker_name": "code_3b", "physical_generation": True},
    ]
    merged = q3_discovery._merge_checkpoint_evidence(  # noqa: SLF001
        report, rows)
    assert q3_discovery._checkpoint_report_identity(  # noqa: SLF001
        merged, require_loaded=True)
    assert {
        entry["loaded_evidence"] for entry in merged
    } == {"validated_physical_generation"}
