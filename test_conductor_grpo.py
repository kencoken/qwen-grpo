"""Unit-4 battery (121_s rev2): the single trainer-facing conductor
reward with schedule enforcement, the frozen schedule/dataset over the
canonical observation boundary, the preregistered demonstration
workflows, and the launch-profile + freeze gates."""

import json

import pytest

from tasks.conductor import grpo_smoke, oracle, parser, policy, render
from tasks.conductor.grpo_task import (
    build_smoke_rows, make_conductor_reward, positional_to_semantic,
    smoke_schedule, summarize_action_trace,
)
from tasks.conductor.payoff_support import load_declaration
from tasks.conductor.types import InfrastructureError


# --- the trainer-facing reward (§10.1) ---------------------------------------

OBS = "code_atomic:worker_dev:00000:641a0144:resource_first:private"
FAKE_SURFACE = {(OBS, (2,)): 1.0, (OBS, (0,)): 0.5}
META = {"observation_id": [OBS],
        "positions": [json.dumps(["n1"])],
        "num_steps": [1]}


def _reward(completion_text, surface=None, **kw):
    reward = make_conductor_reward(surface or FAKE_SURFACE, **kw)
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


def test_reward_enforces_the_frozen_schedule():
    """121_s: a completion arriving out of the frozen order aborts."""
    with pytest.raises(InfrastructureError, match="frozen"):
        _reward('{"worker_ids": [2]}', schedule=["some:other:obs"])
    assert _reward('{"worker_ids": [2]}', schedule=[OBS]) == [1.0]


def test_reward_trace_rows_carry_schedule_indices(tmp_path):
    trace = tmp_path / "actions.jsonl"
    reward = make_conductor_reward(FAKE_SURFACE, trace_path=trace,
                                   schedule=[OBS], group_size=2)
    reward([[{"role": "assistant", "content": '{"worker_ids": [2]}'}],
            [{"role": "assistant", "content": "garbage"}]],
           observation_id=[OBS] * 2,
           positions=[META["positions"][0]] * 2,
           num_steps=[1, 1])
    rows = [json.loads(l) for l in trace.read_text().splitlines()]
    assert [r["reward"] for r in rows] == [1.0, 0.0]
    assert [r["schedule_index"] for r in rows] == [0, 0]
    assert reward.state == {"written": 2, "lookups": 1}


def test_positional_to_semantic_inverts_the_frozen_mapping():
    for positions in (["n1", "n2", "n3"], ["n2", "n1", "n3"]):
        for assignment in ((0, 2, 1), (3, 1, 2)):
            positional = oracle.semantic_to_positional(
                assignment, "fork_join", positions)
            assert positional_to_semantic(positional, positions) == \
                assignment


# --- the frozen schedule and canonical dataset -------------------------------

def test_smoke_schedule_is_the_recorded_deterministic_order():
    schedule = smoke_schedule()
    declared = [obs["observation_id"]
                for obs in load_declaration()["observations"]]
    assert schedule == declared + declared
    assert len(schedule) == 36
    from collections import Counter
    assert set(Counter(schedule).values()) == {2}


def test_smoke_rows_use_the_canonical_observation_boundary():
    """121_s finding 1: the user message is render.build_observation's
    output exactly — Resources available, canonical access notation."""
    from tasks.conductor.payoff_support import support_observations
    rows = build_smoke_rows()
    assert [row["observation_id"] for row in rows] == smoke_schedule()
    by_id = {obs["observation_id"]: obs for obs in support_observations()}
    for row in rows[:18]:
        obs = by_id[row["observation_id"]]
        from tasks.conductor import program
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(obs["latent"])]
        canonical = render.build_observation(obs["instance"], steps)
        assert row["prompt"][1]["content"] == canonical
        assert "Resources available:" in canonical
        assert "(resource: " in canonical
        assert canonical.endswith("Choose one worker for each step.")
        assert row["prompt"][0]["content"] == policy.SYSTEM_CONDUCTOR


# --- the preregistered demonstrations (121_s) --------------------------------

def test_demo_arrangement_is_the_123s_approved_form():
    ids = [demo["worker_ids"] for demo in policy.CONDUCTOR_DEMOS]
    assert ids == [[0], [0, 1], [3, 2, 1], [2, 3]]
    from collections import Counter
    appearances = Counter(w for action in ids for w in action)
    assert appearances == {0: 2, 1: 2, 2: 2, 3: 2}
    # Code order reversed across the two Code-bearing demos.
    code_orders = [[w for w in action if w in (2, 3)] for action in ids
                   if any(w in (2, 3) for w in action)]
    assert code_orders == [[3, 2], [2, 3]]


def test_demo_actions_parse_and_workflows_are_wellformed():
    for demo in policy.CONDUCTOR_DEMOS:
        action = json.dumps({"worker_ids": demo["worker_ids"]})
        parsed = parser.parse_routing_action(action, len(demo["steps"]))
        assert parsed == demo["worker_ids"]
        # The workflow itself builds: registry + legal access pattern.
        registry = policy.demo_registry(demo)
        workflow = parser.routing_to_workflow(
            parsed, [dict(step) for step in demo["steps"]])
        assert len(workflow.steps) == len(demo["steps"])
        for step in demo["steps"]:
            if step["resource"] is not None:
                assert registry.resolve(step["resource"]) is not None


def test_demo_observations_use_the_canonical_layout():
    for demo in policy.CONDUCTOR_DEMOS:
        observation = policy.demo_observation(demo)
        assert observation.startswith("Problem:\n")
        assert "Resources available: " + ", ".join(demo["manifest"]) \
            in observation
        assert observation.endswith("Choose one worker for each step.")
        for index, step in enumerate(demo["steps"], start=1):
            resource = step["resource"] or "none"
            previous = "all" if step["access"] == "all" else "none"
            assert (f"{index}. (resource: {resource}; previous "
                    f"results: {previous})") in observation
        assert observation in policy.SYSTEM_CONDUCTOR


def test_demo_golds_follow_from_the_payloads():
    d1, d2, d3, d4 = policy.CONDUCTOR_DEMOS
    assert d1["gold"] == 27                      # Mesa.crates
    assert d2["gold"] == 8 * 3 + 4               # Harbor.flags * 3 + 4
    assert d3["gold"] == 5 * 2 + 9               # at(,2)=5, at(,1)=2
    seq = d4["resources"]["R-9J5"]["payload"]
    unique = list(dict.fromkeys(seq))
    count = sum(1 for v in unique if v > 4)
    assert d4["gold"] == d4["resources"]["R-2M8"]["payload"][count]


def test_policy_prompt_never_names_the_models():
    prompt = policy.SYSTEM_CONDUCTOR.lower()
    for leak in ("qwen", "1.5b", "3b", "coder", "instruct", "model",
                 "large", "small", "checkpoint", "parameter"):
        assert leak not in prompt, leak
    assert "0, 1, 2, or 3" in policy.SYSTEM_CONDUCTOR
    # 123_s §7: the neutral full-request-context wording.
    assert "in the context of the full request" in policy.SYSTEM_CONDUCTOR
    assert "step descriptions tell you" not in policy.SYSTEM_CONDUCTOR


def test_demo_check_cross_swaps_only_the_matched_pair():
    """123_s §4: the matched independent pair is cross-swapped; the
    asymmetric specialist example runs only its demonstrated route."""
    variants = grpo_smoke.demo_check_variants()
    labels = [label for label, _, _ in variants]
    assert labels == ["direct:assigned", "dependency:assigned",
                      "independent_final:assigned",
                      "independent_final:code-swapped",
                      "specialist_check:assigned"]
    runs = [ids for label, demo, ids in variants
            if demo["name"] == "independent_final"]
    for position in (0, 1):
        assert {run[position] for run in runs} == {2, 3}
    specialist = [ids for label, demo, ids in variants
                  if demo["name"] == "specialist_check"]
    assert specialist == [[2, 3]]


# --- launch profile and freeze gates -----------------------------------------

def test_launch_profile_validates_and_pins():
    grpo_smoke.validate_launch_profile()
    profile = grpo_smoke.STAGE0C_LAUNCH_PROFILE
    assert profile["policy_system_prompt_sha256"] == \
        policy.policy_prompt_sha256()
    assert profile["grpo"]["max_steps"] == 18
    assert profile["grpo"]["loss"] == "dapo"
    assert profile["eval"] == {"n_eval": 0, "strategy": "no"}


def test_launch_profile_detects_prompt_drift(monkeypatch):
    monkeypatch.setitem(grpo_smoke.STAGE0C_LAUNCH_PROFILE,
                        "policy_system_prompt_sha256", "0" * 64)
    with pytest.raises(InfrastructureError, match="prompt hash"):
        grpo_smoke.validate_launch_profile()


def test_live_singleton_mode_fails_closed(monkeypatch):
    """121_s finding 3: declaring an unimplemented mode is fabricated
    provenance."""
    monkeypatch.setitem(grpo_smoke.STAGE0C_LAUNCH_PROFILE,
                        "worker_outcome_mode", "live_singleton")
    with pytest.raises(InfrastructureError, match="not supported"):
        grpo_smoke.validate_launch_profile()


def test_reward_bearing_smoke_requires_the_freeze(monkeypatch, tmp_path):
    monkeypatch.setattr(grpo_smoke, "FREEZE_PATH",
                        tmp_path / "missing.json")
    with pytest.raises(InfrastructureError, match="not frozen"):
        grpo_smoke.run_smoke()


def test_freeze_fixture_verifies_and_names_the_review():
    """Post-freeze: the committed fixture matches the live bytes and
    names the §10.2 review record; any byte drift refuses."""
    frozen = grpo_smoke.verify_freeze()
    assert frozen["policy_prompt_review"] == \
        grpo_smoke.STAGE0C_LAUNCH_PROFILE["policy_prompt_review"]
    assert len(frozen["observation_sha256"]) == 18


def test_surface_pin_is_hermetic(monkeypatch, tmp_path):
    """121_s: the pin check must not depend on the untracked artifact.
    Absence refuses with its own message; a mismatching manifest
    refuses on the hash."""
    monkeypatch.setattr(grpo_smoke, "SURFACE_DIR", tmp_path / "absent")
    with pytest.raises(InfrastructureError, match="absent"):
        grpo_smoke.verify_surface_pin()
    surface_dir = tmp_path / "surface"
    surface_dir.mkdir()
    (surface_dir / "manifest.json").write_text("{}")
    monkeypatch.setattr(grpo_smoke, "SURFACE_DIR", surface_dir)
    with pytest.raises(InfrastructureError, match="pin"):
        grpo_smoke.verify_surface_pin()


# --- §10.3 summary invariants ------------------------------------------------

def _trace_rows(obs, n, group_size=8):
    rows = []
    for i in range(n):
        good = i % group_size == 0
        rows.append({"observation_id": obs, "schedule_index":
                     i // group_size, "completion": "x",
                     "action": [0, 2, 1] if i % 2 == 0 else None,
                     "schema_error": None if i % 2 == 0 else "bad",
                     "assignment": [0, 2, 1] if i % 2 == 0 else None,
                     "reward": 1.0 if good else
                     (0.5 if i % 2 == 0 else 0.0)})
    return rows


def test_summarize_action_trace(tmp_path):
    trace = tmp_path / "actions.jsonl"
    obs = "fork_join:worker_dev:00000:5b6d01a9:goal_first:private"
    rows = _trace_rows(obs, 16)
    trace.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    summary = summarize_action_trace(trace, expected_schedule=[obs, obs])
    assert summary["completions"] == 16 and summary["groups"] == 2
    assert summary["action_parse_rate"] == 0.5
    assert summary["reward_frequencies"] == {"0.0": 8, "0.5": 6,
                                             "1.0": 2}
    assert summary["groups_with_win_and_loss"] == 2
    assert summary["by_topology"]["fork"]["n"] == 16


def test_summarizer_rejects_a_partial_or_reordered_trace(tmp_path):
    """121_s: a one-row trace must never summarize as a run."""
    trace = tmp_path / "actions.jsonl"
    obs = "fork_join:worker_dev:00000:5b6d01a9:goal_first:private"
    rows = _trace_rows(obs, 8)
    trace.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    with pytest.raises(InfrastructureError, match="exactly"):
        summarize_action_trace(trace, expected_schedule=[obs, obs])
    wrong = dict(rows[0], observation_id="other:obs")
    trace.write_text("\n".join(
        json.dumps(r) for r in [wrong] + rows[1:]) + "\n")
    with pytest.raises(InfrastructureError, match="frozen schedule"):
        summarize_action_trace(trace, expected_schedule=[obs])
