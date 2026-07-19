"""0A battery: strip test, failure propagation, routing bijection,
intervention positional mapping (both fork orders), pseudo-workers, B2,
oracle/comparator toy surface, byte-stability, demos execute through the
runtime (§1.5, §1.7–1.9, §1.11, §4)."""

import itertools
import json
from pathlib import Path

import pytest

from tasks.conductor import (
    baselines, contract, executor, oracle, parser, program, prompts, render,
)
from tasks.conductor.gen_byte_fixtures import FIXTURE_PATH, build_fixture
from tasks.conductor.parser import ActionSchemaError, parse_routing_action
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.resources import InstanceRegistry

PROF = DEFAULT_PROFILE


def make_env(cell, index=0, renderer="resource_first", visibility="private"):
    latent = program.generate_latent(cell, "construction", index, PROF).latent
    inst = program.render_instance(latent, renderer, visibility)
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    steps = [{"subtask": s["subtask"], "resource": s["resource"],
              "access": s["access"]} for s in program.workflow_steps(latent)]
    return latent, inst, registry, steps


def perfect_worker(latent):
    """Scripted endpoint pool that answers every reference subtask
    correctly with a legal artifact (the fake pool for CPU tests)."""
    params = latent["params"]
    by_node = {}
    for step in program.workflow_steps(latent):
        node = step["node"]
        cell = latent["cell_id"]
        if cell in ("lookup_atomic", "lookup_math", "fork_join") \
                and node == "n1":
            by_node[node] = (0, f'<artifact>lookup(resource, '
                                f'"{params["key"]}", "{params["field"]}")'
                                f"</artifact>")
        elif cell == "math_atomic":
            expr = {"T1": "(a * b - c) / d", "T2": "(a * b + c) % m",
                    "T3": "a * b + c"}[params["template"]]
            by_node[node] = (1, f"<artifact>{expr}</artifact>")
        elif cell == "code_atomic":
            expr = ("count_gt(stable_unique(resource), %d)" % params["t"]
                    if params["shape"] == "count" else
                    "at(rotate_left(stable_unique(resource), %d), %d)"
                    % (params["k"], params["i"]))
            by_node[node] = (2, f"<artifact>{expr}</artifact>")
        elif cell == "lookup_math" and node == "n2":
            op = "-" if params["sign"] == "-" else "+"
            by_node[node] = (1, f'<artifact>{params["p"]} * step_1 {op} '
                                f'{params["q"]}</artifact>')
        elif cell == "math_code":
            by_node[node] = ((1, "<artifact>(a * b + c) % m</artifact>")
                             if node == "n1" else
                             (2, "<artifact>at(resource, step_1)</artifact>"))
        elif cell == "fork_join" and node == "n2":
            by_node[node] = (2, "<artifact>count_gt(stable_unique(resource),"
                                f" {params['t']})</artifact>")
        elif cell == "fork_join" and node == "n3":
            by_node[node] = (1, "<artifact>step_1 * step_2 + "
                                f"{params['q']}</artifact>")
    positions = latent["reference_program"]["positions"]
    worker_ids = [by_node[n][0] for n in positions]
    subtasks = {step["node"]: step["subtask"]
                for step in program.workflow_steps(latent)}
    by_subtask = {subtasks[node]: completion
                  for node, (_, completion) in by_node.items()}

    def worker_call(worker_id, request):
        # Stateless fake pool: answer by the request's Task block.
        task = request.split("Task:\n", 1)[1].split("\n\n", 1)[0]
        return by_subtask[task]

    return worker_ids, worker_call


ALL_CELLS = ("lookup_atomic", "math_atomic", "code_atomic", "lookup_math",
             "math_code", "fork_join")


# --- correct execution end-to-end -------------------------------------------

@pytest.mark.parametrize("cell", ALL_CELLS)
def test_perfect_pool_reaches_gold(cell):
    latent, inst, registry, steps = make_env(cell)
    worker_ids, worker_call = perfect_worker(latent)
    action = parser.routing_to_workflow(worker_ids, steps)
    result = executor.execute_workflow(action, inst["public_prompt"],
                                       registry, worker_call)
    assert result.terminal == inst["gold_answer"]
    assert executor.score_terminal(result.terminal, inst["gold_answer"]) == 1.0


# --- §4 strip test ----------------------------------------------------------

def test_strip_test():
    """Delete all reference metadata *and the gold answer*; an arbitrary
    sampled workflow must execute identically from {public prompt +
    manifest, instance registry, sampled action, endpoint definitions}."""
    latent, inst, registry, steps = make_env("lookup_math")
    stripped = {k: v for k, v in inst.items()
                if k not in ("reference_program", "gold_answer",
                             "public_numeric_values",
                             "public_numeric_collision_nodes",
                             "public_numeric_collision",
                             "sink_public_numeric_collision")}
    stripped_registry = InstanceRegistry(stripped["public_manifest"],
                                         stripped["private_registry"])
    worker_ids, make_call = perfect_worker(latent)
    for sampled in itertools.product((0, 1, 2), repeat=len(steps)):
        action = parser.routing_to_workflow(list(sampled), steps)
        _, call_a = perfect_worker(latent)
        _, call_b = perfect_worker(latent)
        full = executor.execute_workflow(action, inst["public_prompt"],
                                         registry, call_a)
        bare = executor.execute_workflow(action, stripped["public_prompt"],
                                         stripped_registry, call_b)
        assert full.terminal == bare.terminal
        assert [(r.result, r.request) for r in full.steps] == \
            [(r.result, r.request) for r in bare.steps]


# --- §1.7 failure propagation -----------------------------------------------

def test_propagation_blocks_access_all_only():
    latent, inst, registry, steps = make_env("fork_join")
    worker_ids, worker_call = perfect_worker(latent)

    # Fail step 1 only: step 2 (access none) unaffected, join blocked.
    def failing_first(worker_id, request):
        if steps[0]["subtask"] in request:
            return "no artifact here"
        return worker_call(worker_id, request)

    action = parser.routing_to_workflow(worker_ids, steps)
    result = executor.execute_workflow(action, inst["public_prompt"],
                                       registry, failing_first)
    assert result.steps[0].result.status == "typed_failure"
    assert result.steps[0].result.rejection_code == "E_NO_ARTIFACT"
    assert result.steps[1].result.status == "success"  # access none
    assert result.steps[2].result.status == "dependency_blocked"
    assert result.steps[2].request is None  # no worker call made
    assert result.terminal is None
    assert executor.score_terminal(result.terminal, inst["gold_answer"]) == 0.5


def test_unknown_handle_is_world_failure():
    latent, inst, registry, steps = make_env("lookup_atomic")
    steps[0]["resource"] = "R-9Z9"  # foreign handle: registries are scoped
    action = parser.routing_to_workflow([0], steps)
    result = executor.execute_workflow(action, inst["public_prompt"],
                                       registry, lambda w, r: "unused")
    assert result.steps[0].world_failure == "unknown_handle"
    assert result.terminal is None


# --- §1.5 routing schema bijection + rejections (§4) ------------------------

@pytest.mark.parametrize("num_steps", [1, 2, 3])
def test_routing_bijection(num_steps):
    seen = set()
    for ids in itertools.product((0, 1, 2), repeat=num_steps):
        parsed = parse_routing_action(json.dumps({"worker_ids": list(ids)}),
                                      num_steps)
        seen.add(tuple(parsed))
    assert len(seen) == 3 ** num_steps


@pytest.mark.parametrize("completion", [
    "not json",
    '{"worker_ids": [0, 1], "extra": 1}',
    '{"workers": [0, 1]}',
    '{"worker_ids": [0]}',              # wrong length
    '{"worker_ids": [0, 1, 2]}',        # wrong length
    '{"worker_ids": [0, 3]}',           # out of range -> malformed, not world
    '{"worker_ids": [0, -1]}',
    '{"worker_ids": [0, 1.0]}',
    '{"worker_ids": [0, true]}',
    '{"worker_ids": [0, "1"]}',
    '{"worker_ids": "01"}',
    '[0, 1]',
])
def test_routing_schema_rejections(completion):
    with pytest.raises(ActionSchemaError):
        parse_routing_action(completion, 2)


def test_routing_duplicates_permitted():
    assert parse_routing_action('{"worker_ids": [1, 1]}', 2) == [1, 1]


def test_workflow_action_rejections():
    ok = json.dumps({"steps": [
        {"subtask": "s", "worker_id": 0, "resource": "R-1A1",
         "access": "none"},
        {"subtask": "t", "worker_id": 1, "resource": None, "access": "all"}]})
    parser.parse_workflow_action(ok)
    bad_cases = [
        {"steps": []},
        {"steps": [{"subtask": "s", "worker_id": 0, "resource": None,
                    "access": "all"}]},                      # illegal pattern
        {"steps": [{"subtask": "s", "worker_id": 0, "resource": "R-1A1",
                    "access": "none", "extra": 1}]},         # extra field
        {"steps": [{"subtask": "s", "worker_id": 0, "resource": "R-1A1",
                    "access": "none"},
                   {"subtask": "t", "worker_id": 1, "resource": "R-1A1",
                    "access": "all"}]},                      # duplicate handle
    ]
    for case in bad_cases:
        with pytest.raises(ActionSchemaError):
            parser.parse_workflow_action(json.dumps(case))


# --- §1.9 intervention positional mapping, both fork orders -----------------

def test_intervention_positional_mapping_both_orders():
    seen_orders = set()
    for index in range(6):
        latent, inst, registry, steps = make_env("fork_join", index)
        order = latent["params"]["branch_order"]
        seen_orders.add(order)
        worker_ids, _ = perfect_worker(latent)
        for u, v in program.INTERVENTION_EDGES["fork_join"]:
            iv = program.draw_intervention(latent, u, v, PROF)
            positions = latent["reference_program"]["positions"]
            assert iv["override_position"] == 1 + positions.index(u)
            _, worker_call = perfect_worker(latent)
            action = parser.routing_to_workflow(worker_ids, steps)
            result = executor.execute_workflow(
                action, inst["public_prompt"], registry, worker_call,
                overrides={iv["override_position"]: iv["replacement"]})
            # One mutated execution scored twice:
            assert result.terminal == iv["counterfactual_target"]
            assert result.terminal != iv["corruption_target"]
            assert result.steps[iv["override_position"] - 1].override_applied
    assert seen_orders == {"lookup_first", "code_first"}


def test_code_first_override_of_n2_overrides_step_1():
    for index in range(6):
        latent, *_ = make_env("fork_join", index)
        if latent["params"]["branch_order"] == "code_first":
            iv = program.draw_intervention(latent, "n2", "n3", PROF)
            assert iv["override_position"] == 1
            return
    pytest.fail("no code-first fork in range")


# --- §1.11 pseudo-workers ---------------------------------------------------

def test_echo_worker_token_boundaries():
    # step_1/step_2 digits sit inside \w boundaries and are not tokens;
    # the last integer token in the Task block is q.
    request = render.build_worker_request(
        "prompt", "Multiply step_1 by step_2, then add 17.")
    result = baselines.echo_worker(request)
    assert result.synthetic and result.value == 17
    no_int = render.build_worker_request(
        "prompt 99", "Retrieve Cedar's units value from the requested "
        "resource.")
    failed = baselines.echo_worker(no_int)
    assert failed.status == "typed_failure"
    assert failed.rejection_code == "E_PARSE" and failed.synthetic


def test_noop_substitution_protocol():
    latent, inst, registry, steps = make_env("fork_join")
    worker_ids, worker_call = perfect_worker(latent)
    action = parser.routing_to_workflow(worker_ids, steps)
    # Substitute the no-op at one node; all other nodes keep their workers.
    result = executor.execute_workflow(
        action, inst["public_prompt"], registry, worker_call,
        pseudo_workers={1: baselines.noop_worker})
    assert result.steps[0].result.synthetic
    assert result.steps[0].result.value == 0
    assert result.steps[1].result.synthetic is False
    # Join consumed step_1 = 0 -> terminal = q (x*0 or 0*y + q).
    assert result.terminal == latent["params"]["q"]
    noop_correct = result.terminal == inst["gold_answer"]
    assert noop_correct is False  # gold >= 1 and != q by rejection rules


# --- §1.11 B2: payload block absent and binding set empty -------------------

def test_b2_draws_typed_errors_never_payload_values():
    latent, inst, registry, steps = make_env("lookup_atomic")
    request, binding = baselines.build_b2_request(inst, steps[0]["subtask"])
    assert "Resource:" not in request
    result = contract.run_worker_output(
        0, f'<artifact>lookup(resource, "{latent["params"]["key"]}", '
           f'"{latent["params"]["field"]}")</artifact>', binding)
    assert result.status == "typed_failure"
    assert result.rejection_code == "E_NO_RESOURCE"


# --- §1.8 oracle/comparator on a hand-enumerated toy surface ----------------

TOY = {
    (0, 0): {"c1": [1, 0], "c2": [0]},
    (0, 1): {"c1": [1, 1], "c2": [1]},
    (0, 2): {"c1": [0, 0], "c2": [0]},
    (1, 0): {"c1": [1, 1], "c2": [1]},   # accuracy tie with (0, 1)
    (1, 1): {"c1": [1, 0], "c2": [1]},
    (1, 2): {"c1": [0, 0], "c2": [1]},
    (2, 0): {"c1": [1, 1], "c2": [0]},
    (2, 1): {"c1": [1, 0], "c2": [1]},
    (2, 2): {"c1": [1, 1], "c2": [0]},
}


def test_oracle_toy_surface():
    assert oracle.cluster_weighted_accuracy(TOY[(1, 1)]) == 0.75
    assert oracle.select_deployable(TOY) == (0, 1)  # tie -> lexicographic
    assert oracle.best_fixed(TOY) == (1, 1)
    assert oracle.uniform_random_accuracy(TOY) == pytest.approx(5.25 / 9)
    # Runner-up at node 0 with node 1 fixed: (1,1) vs (2,1) tie -> lowest.
    assert oracle.node_runner_up(TOY, (0, 1), 0) == (1, 1)
    assert oracle.node_runner_up(TOY, (0, 1), 1) == (0, 0)


def test_semantic_to_positional_both_fork_orders():
    assignment = (0, 2, 1)  # stable node order (n1, n2, n3)
    assert oracle.semantic_to_positional(assignment, "fork_join",
                                         ["n1", "n2", "n3"]) == [0, 2, 1]
    assert oracle.semantic_to_positional(assignment, "fork_join",
                                         ["n2", "n1", "n3"]) == [2, 0, 1]


def test_signed_gap_paired_and_unclipped():
    deployable = {"c1": [1.0, 1.0], "c2": [1.0]}
    policy = {"c1": [1.0, 0.0], "c2": [0.0]}  # malformed action enters as 0
    assert oracle.signed_deployable_gap(deployable, policy) == \
        pytest.approx(0.75)
    better = {"c1": [1.0, 1.0], "c2": [1.0]}
    worse = {"c1": [0.0, 0.0], "c2": [1.0]}
    assert oracle.signed_deployable_gap(worse, better) == pytest.approx(-0.5)
    with pytest.raises(ValueError):
        oracle.signed_deployable_gap(deployable, {"c1": [1.0]})


def test_two_call_family_and_tie_order():
    workflows = oracle.enumerate_two_call_workflows()
    assert len(workflows) == 18
    assert workflows[0] == ("lookup_first", (0, 0))
    accuracy = {wf: 0.5 for wf in workflows}
    assert oracle.select_best_two_call(accuracy) == ("lookup_first", (0, 0))
    assert oracle.select_best_one_call({0: 0.5, 1: 0.5, 2: 0.4}) == 0


# --- §4 byte-stability fixture ----------------------------------------------

def test_byte_stability_fixture():
    stored = json.loads(Path(FIXTURE_PATH).read_text())
    assert build_fixture() == stored
    assert sum(1 for k in stored if k.startswith("two_call")) == 36


# --- D16 demos execute through the runtime ----------------------------------

def test_demos_execute_through_runtime():
    endpoint_index = {"lookup": 0, "math": 1, "code": 2}
    for endpoint_name, demos in prompts.DEMONSTRATIONS.items():
        for demo in demos:
            result = contract.run_worker_output(
                endpoint_index[endpoint_name], str(demo["completion"]),
                prompts.demo_binding(demo))
            assert result.status == "success"
            assert result.value == demo["value"]


def test_d16_is_draft_until_its_own_review():
    assert prompts.D16_STATUS == "DRAFT"


# --- reward boundary (plan contract 4) --------------------------------------

def test_reward_boundary():
    latent, inst, registry, steps = make_env("lookup_atomic")
    gold = inst["gold_answer"]

    def run(action):
        _, worker_call = perfect_worker(latent)
        return executor.execute_workflow(action, inst["public_prompt"],
                                         registry, worker_call).terminal

    def parse_ok():
        return parser.routing_to_workflow(
            parse_routing_action('{"worker_ids": [0]}', 1), steps)

    def parse_bad():
        return parser.routing_to_workflow(
            parse_routing_action('{"worker_ids": [7]}', 1), steps)

    assert executor.reward_for_completion(parse_ok, run, gold) == 1.0
    assert executor.reward_for_completion(parse_bad, run, gold) == 0.0

    def run_misroute(action):
        return executor.execute_workflow(
            action, inst["public_prompt"], registry,
            lambda w, r: "<artifact>1 + 1</artifact>").terminal

    def parse_misroute():
        return parser.routing_to_workflow(
            parse_routing_action('{"worker_ids": [1]}', 1), steps)

    assert executor.reward_for_completion(parse_misroute, run_misroute,
                                          gold) == 0.5
