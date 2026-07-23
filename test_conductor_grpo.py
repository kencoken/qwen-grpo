"""Unit-4 battery: the single trainer-facing conductor reward (all
three ladder values + the infrastructure-abort path), the frozen smoke
schedule and dataset, the policy prompt/demos, and the launch-profile
gates (106_s §§10.1-10.3)."""

import json

import pytest

from tasks.conductor import grpo_smoke, oracle, parser, policy
from tasks.conductor.grpo_task import (
    build_smoke_rows, make_conductor_reward, positional_to_semantic,
    smoke_schedule, summarize_action_trace,
)
from tasks.conductor.payoff_support import load_declaration
from tasks.conductor.types import InfrastructureError


# --- the trainer-facing reward (§10.1) ---------------------------------------

FAKE_SURFACE = {
    ("code_atomic:worker_dev:00000:641a0144:resource_first:private",
     (2,)): 1.0,
    ("code_atomic:worker_dev:00000:641a0144:resource_first:private",
     (0,)): 0.5,
}
META = {"observation_id": [
            "code_atomic:worker_dev:00000:641a0144:resource_first:private"],
        "positions": [json.dumps(["n1"])],
        "num_steps": [1]}


def _reward(completion_text, surface=None):
    reward = make_conductor_reward(surface or FAKE_SURFACE)
    # TRL conversational completion shape.
    completions = [[{"role": "assistant", "content": completion_text}]]
    return reward(completions, **{k: list(v) for k, v in META.items()})


def test_reward_ladder_through_the_trainer_facing_callable():
    assert _reward('{"worker_ids": [2]}') == [1.0]   # correct terminal
    assert _reward('{"worker_ids": [0]}') == [0.5]   # world failure
    assert _reward('not json') == [0.0]              # malformed action
    assert _reward('{"worker_ids": [2], "x": 1}') == [0.0]
    assert _reward('{"worker_ids": [4]}') == [0.0]   # outside the pool


def test_missing_surface_row_is_an_infrastructure_abort():
    with pytest.raises(InfrastructureError, match="never a reward"):
        _reward('{"worker_ids": [3]}')  # schema-valid, no outcome row


def test_reward_trace_rows_are_persisted(tmp_path):
    trace = tmp_path / "actions.jsonl"
    reward = make_conductor_reward(FAKE_SURFACE, trace_path=trace)
    reward([[{"role": "assistant", "content": '{"worker_ids": [2]}'}],
            [{"role": "assistant", "content": "garbage"}]],
           observation_id=[META["observation_id"][0]] * 2,
           positions=[META["positions"][0]] * 2,
           num_steps=[1, 1])
    rows = [json.loads(l) for l in trace.read_text().splitlines()]
    assert [r["reward"] for r in rows] == [1.0, 0.0]
    assert rows[0]["assignment"] == [2]
    assert rows[1]["schema_error"]


def test_positional_to_semantic_inverts_the_frozen_mapping():
    for positions in (["n1", "n2", "n3"], ["n2", "n1", "n3"]):
        for assignment in ((0, 2, 1), (3, 1, 2)):
            positional = oracle.semantic_to_positional(
                assignment, "fork_join", positions)
            assert positional_to_semantic(positional, positions) == \
                assignment


# --- the frozen schedule and dataset (§10.1/§10.3) ---------------------------

def test_smoke_schedule_is_the_recorded_deterministic_order():
    schedule = smoke_schedule()
    declared = [obs["observation_id"]
                for obs in load_declaration()["observations"]]
    assert schedule == declared + declared
    assert len(schedule) == 36
    from collections import Counter
    assert set(Counter(schedule).values()) == {2}


def test_smoke_dataset_rows_follow_the_schedule():
    rows = build_smoke_rows()
    assert [row["observation_id"] for row in rows] == smoke_schedule()
    for row in rows:
        assert row["prompt"][0]["role"] == "system"
        assert row["prompt"][1]["role"] == "user"
        assert row["prompt"][1]["content"].startswith("Problem:")
        assert '"worker_ids"' in row["prompt"][1]["content"]
        assert row["num_steps"] == len(json.loads(row["positions"]))


# --- policy prompt and demonstrations (§10.2) --------------------------------

def test_demos_cover_all_four_ids_with_valid_actions():
    seen = set()
    for demo in policy.CONDUCTOR_DEMOS:
        steps = demo["observation"].count("\n1.") + \
            demo["observation"].count("\n2.")
        parsed = parser.parse_routing_action(demo["action"], steps)
        seen.update(parsed)
    assert seen == {0, 1, 2, 3}


def test_policy_prompt_never_names_the_models():
    prompt = policy.SYSTEM_CONDUCTOR.lower()
    for leak in ("qwen", "1.5b", "3b", "coder", "instruct", "model",
                 "large", "small", "checkpoint", "parameter"):
        assert leak not in prompt, leak
    # The ids are presented as opaque.
    assert "0, 1, 2, or 3" in policy.SYSTEM_CONDUCTOR


def test_code_demos_are_matched_and_solvable():
    """The w2/w3 demos share the Code-like task shape and their
    expected values follow from the stated payloads under the tool's
    zero-based at() semantics."""
    for check in policy.DEMO_CODE_CHECKS:
        demo = policy.CONDUCTOR_DEMOS[check["demo_index"]]
        assert "zero-based index" in demo["observation"]
        assert check["payload"][check["index"]] == check["expected"]
    ids = {json.loads(policy.CONDUCTOR_DEMOS[c["demo_index"]]["action"])
           ["worker_ids"][0] for c in policy.DEMO_CODE_CHECKS}
    assert ids == {2, 3}


def test_observation_builder_formats_steps():
    text = policy.build_policy_observation(
        "The problem.", [
            {"subtask": "First task.", "resource": "R-1A1",
             "access": "none"},
            {"subtask": "Second task.", "resource": None,
             "access": "all"}])
    assert "1. First task. [resource: R-1A1]" in text
    assert "2. Second task. (uses earlier results)" in text
    assert "containing 2 ids" in text


# --- launch profile gates (§10.1/§10.2) --------------------------------------

def test_launch_profile_validates_and_records_the_prompt_hash():
    grpo_smoke.validate_launch_profile()
    profile = grpo_smoke.STAGE0C_LAUNCH_PROFILE
    assert profile["policy_system_prompt_sha256"] == \
        policy.policy_prompt_sha256()
    assert profile["grpo"]["max_steps"] == 18
    assert profile["worker_outcome_mode"] == "precomputed_surface"
    assert profile["eval"] == {"n_eval": 0, "strategy": "no"}


def test_launch_profile_detects_prompt_drift(monkeypatch):
    monkeypatch.setitem(grpo_smoke.STAGE0C_LAUNCH_PROFILE,
                        "policy_system_prompt_sha256", "0" * 64)
    with pytest.raises(InfrastructureError, match="prompt hash"):
        grpo_smoke.validate_launch_profile()


def test_reward_bearing_smoke_is_gated_on_the_prompt_review():
    assert grpo_smoke.STAGE0C_LAUNCH_PROFILE["policy_prompt_review"] \
        is None
    with pytest.raises(InfrastructureError, match="gated"):
        grpo_smoke.run_smoke()


def test_surface_pin_mismatch_refuses(monkeypatch):
    monkeypatch.setattr(grpo_smoke, "SURFACE_MANIFEST_SHA256", "0" * 64)
    with pytest.raises(InfrastructureError, match="pin"):
        grpo_smoke.verify_surface_pin()


# --- §10.3 summary derivation ------------------------------------------------

def test_summarize_action_trace(tmp_path):
    trace = tmp_path / "actions.jsonl"
    rows = []
    obs = "fork_join:worker_dev:00000:5b6d01a9:goal_first:private"
    for i in range(16):  # two groups of eight
        good = i % 8 == 0
        rows.append({"observation_id": obs,
                     "completion": "x",
                     "action": [0, 2, 1] if i % 2 == 0 else None,
                     "schema_error": None if i % 2 == 0 else "bad",
                     "assignment": [0, 2, 1] if i % 2 == 0 else None,
                     "reward": 1.0 if good else
                     (0.5 if i % 2 == 0 else 0.0)})
    trace.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    summary = summarize_action_trace(trace)
    assert summary["completions"] == 16 and summary["groups"] == 2
    assert summary["action_parse_rate"] == 0.5
    assert summary["reward_frequencies"] == {"0.0": 8, "0.5": 6,
                                             "1.0": 2}
    assert summary["groups_with_win_and_loss"] == 2
    assert summary["zero_variance_groups"] == 0
    assert summary["by_topology"]["fork"]["n"] == 16
    assert summary["worker_selection_counts"][2] == 8
