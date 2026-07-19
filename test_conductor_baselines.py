"""0A battery: baseline request shapes, observable subtypes, and the frozen
shallow predictor (golden feature-matrix/prediction fixture, refit
determinism) — §1.11, §4."""

import warnings

import pytest

from tasks.conductor import baselines, program, render
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.resources import InstanceRegistry

PROF = DEFAULT_PROFILE


def env(cell, index=0):
    latent = program.generate_latent(cell, "construction", index, PROF).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    return latent, inst, registry


# --- request shapes (§1.11 table) -------------------------------------------

def test_b1_is_problem_only():
    _, inst, _ = env("lookup_atomic")
    request = baselines.build_b1_request(inst)
    assert request.startswith("Problem:\n")
    assert "\nTask:\n" not in request
    assert "\nResource:\n" not in request and "\nResources:\n" not in request
    assert request.endswith(render.DIRECT_FINAL_LINE)


def test_b3_visible_direct_plural_block():
    _, inst, registry = env("math_code")
    request = baselines.build_b3_request(inst, registry)
    assert "\n\nResources:\n" in request
    assert "Task:" not in request
    assert request.endswith(render.DIRECT_FINAL_LINE)


def test_b5_union_payload_and_task():
    latent, inst, registry = env("fork_join")
    request, binding = baselines.build_b5_request(inst, registry)
    assert f"Task:\n{baselines.B5_TASK}" in request
    assert "\n\nResources:\n" in request
    assert set(binding.resources) == set(inst["public_manifest"])
    assert request.endswith(render.ARTIFACT_FINAL_LINE)


def test_generic_subtask_frozen_string():
    assert render.GENERIC_SUBTASK == (
        "Complete the assigned step using the problem context, any provided "
        "resource, and any previous results.")
    assert baselines.generic_subtasks(3) == [render.GENERIC_SUBTASK] * 3


# --- observable subtype (frozen level lists; public-prompt-derivable) -------

def test_observable_subtype_levels():
    assert baselines.OBSERVABLE_SUBTYPES["lookup_atomic"] == ("constant",)
    assert baselines.observable_subtype(
        "lookup_math", {"sign": "-"}) == "minus"
    assert baselines.observable_subtype(
        "fork_join", {"branch_order": "code_first"}) == "code_first"
    assert baselines.observable_subtype("math_code", {}) == "constant"
    for cell, levels in baselines.OBSERVABLE_SUBTYPES.items():
        for index in range(3):
            latent, _, _ = env(cell, index)
            assert baselines.observable_subtype(
                cell, latent["params"]) in levels


# --- §4 golden feature-matrix/prediction fixture ----------------------------

def test_feature_row_column_order_golden():
    # lookup_math construction:00000 — subtype one-hot (minus, plus) then
    # numeric columns exactly [p, q, t, k, i], missing = −1.
    latent, _, _ = env("lookup_math", 0)
    row = baselines.feature_row("lookup_math", latent["params"],
                                latent["public_numeric_values"])
    assert row == [0, 1, 8, 12, -1, -1, -1]
    code_latent, _, _ = env("code_atomic", 1)
    code_row = baselines.feature_row("code_atomic", code_latent["params"],
                                     code_latent["public_numeric_values"])
    assert code_row == [0, 1, -1, -1, -1, 7, 8]  # select: t=-1, k=7, i=8


def test_shallow_predictor_golden_and_refit_determinism():
    latents = [program.generate_latent("lookup_math", "construction", i,
                                       PROF).latent for i in range(30)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        model_a = baselines.fit_shallow_predictor("lookup_math", latents)
        model_b = baselines.fit_shallow_predictor("lookup_math", latents)
    predictions = [baselines.shallow_predict(
        model_a, "lookup_math", latent["params"],
        latent["public_numeric_values"]) for latent in latents[:5]]
    assert predictions == [91, 128, 91, 28, 91]  # golden fixture
    refit = [baselines.shallow_predict(
        model_b, "lookup_math", latent["params"],
        latent["public_numeric_values"]) for latent in latents[:5]]
    assert refit == predictions  # refit determinism on identical data


def test_shallow_predictor_rejects_mixed_cells():
    lm, _, _ = env("lookup_math")
    ca, _, _ = env("code_atomic")
    from tasks.conductor.types import InfrastructureError
    with pytest.raises(InfrastructureError):
        baselines.fit_shallow_predictor("lookup_math", [lm, ca])
