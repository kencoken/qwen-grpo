"""0A battery: strip test, failure propagation, routing bijection,
intervention positional mapping (both fork orders), pseudo-workers, B2,
oracle/comparator toy surface, byte-stability, demos execute through the
runtime (§1.5, §1.7–1.9, §1.11, §4)."""

import copy
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


def make_env(cell, index=0, renderer="resource_first", visibility="private",
             namespace="construction"):
    latent = program.generate_latent(cell, namespace, index, PROF).latent
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

# Cluster and observation ids are real identities: a surface is bound to
# its cell through them, which node arity alone cannot do (all three atomic
# cells have one node).
def cluster_ids(cell, count=2, namespace="construction"):
    return [program.generate_latent(cell, namespace, i, PROF)
            .latent["latent_program_id"] for i in range(count)]


def observation_id(cluster, renderer="resource_first", visibility="private"):
    return f"{cluster}:{renderer}:{visibility}"


LM_C1, LM_C2 = cluster_ids("lookup_math")


def _toy(pairs):
    """Observation-keyed toy surface: cluster 1 has two renderings."""
    return {assignment: {
        LM_C1: {observation_id(LM_C1): a,
                observation_id(LM_C1, "goal_first"): b},
        LM_C2: {observation_id(LM_C2): c}}
        for assignment, (a, b, c) in pairs.items()}


TOY_RAW = _toy({
    (0, 0): (1, 0, 0),
    (0, 1): (1, 1, 1),
    (0, 2): (0, 0, 0),
    (1, 0): (1, 1, 1),   # accuracy tie with (0, 1)
    (1, 1): (1, 0, 1),
    (1, 2): (0, 0, 1),
    (2, 0): (1, 1, 0),
    (2, 1): (1, 0, 1),
    (2, 2): (1, 1, 0),
})


def test_oracle_toy_surface():
    surface = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    assert surface.accuracy((1, 1)) == 0.75
    assert oracle.select_deployable(surface) == (0, 1)  # tie -> lexicographic
    assert oracle.best_fixed(surface) == (1, 1)
    assert oracle.uniform_random_accuracy(surface) == pytest.approx(5.25 / 9)
    # Runner-up at node 0 with node 1 fixed: (1,1) vs (2,1) tie -> lowest.
    assert oracle.node_runner_up(surface, (0, 1), 0) == (1, 1)
    assert oracle.node_runner_up(surface, (0, 1), 1) == (0, 0)


def test_surface_is_observation_paired_not_merely_equal_counts():
    """Equal per-cluster counts must not admit different renderings: the
    pairing is checked by observation identity."""
    raw = copy.deepcopy(TOY_RAW)
    raw[(1, 2)] = {
        LM_C1: {observation_id(LM_C1): 1,
                observation_id(LM_C1, "bound_var"): 1},   # same count
        LM_C2: {observation_id(LM_C2): 1}}
    with pytest.raises(oracle.PayoffSurfaceError, match="observation ids"):
        oracle.validate_payoff_surface(raw, "lookup_math")


def _atomic_surface(cell="lookup_atomic", value=1):
    cluster = cluster_ids(cell, 1)[0]
    return {a: {cluster: {observation_id(cluster): value}}
            for a in oracle.enumerate_assignments(1)}


@pytest.mark.parametrize("raw,cell,match", [
    ({(2,): {"c": {"o": 1}}}, "lookup_atomic", "full enumeration"),
    ({(): {"c": {"o": 1}}}, "lookup_atomic", "must have 1 entries"),
    ({0: {"c": {"o": 1}}}, "lookup_atomic", "must be a tuple"),
    ({(0.0,): {"c": {"o": 1}}, (1,): {"c": {"o": 1}}, (2,): {"c": {"o": 1}}},
     "lookup_atomic", "non-integer"),
    ({(True,): {"c": {"o": 1}}, (1,): {"c": {"o": 1}}, (2,): {"c": {"o": 1}}},
     "lookup_atomic", "non-integer"),
    (TOY_RAW, "lookup_atomic", "must have 1 entries"),   # wrong cell arity
    (TOY_RAW, "bogus_cell", "unknown cell_id"),
])
def test_surface_domain_errors_are_typed(raw, cell, match):
    with pytest.raises(oracle.PayoffSurfaceError, match=match):
        oracle.validate_payoff_surface(raw, cell)


def test_surface_is_bound_to_its_cell_by_identity_not_arity():
    """The three atomic cells all have one node, so relabelling can only
    be caught by the cell named in the cluster and observation ids."""
    raw = _atomic_surface("lookup_atomic")
    oracle.validate_payoff_surface(raw, "lookup_atomic")
    for wrong in ("math_atomic", "code_atomic"):
        with pytest.raises(oracle.PayoffSurfaceError, match="belongs to cell"):
            oracle.validate_payoff_surface(raw, wrong)


def test_surface_rejects_unparseable_or_misfiled_identities():
    cluster = cluster_ids("lookup_atomic", 1)[0]
    anonymous = {a: {"c1": {"o1": 1}} for a in oracle.enumerate_assignments(1)}
    with pytest.raises(oracle.PayoffSurfaceError, match="latent_program_id"):
        oracle.validate_payoff_surface(anonymous, "lookup_atomic")
    other = cluster_ids("lookup_atomic", 2)[1]
    misfiled = {a: {cluster: {observation_id(other): 1}}
                for a in oracle.enumerate_assignments(1)}
    with pytest.raises(oracle.PayoffSurfaceError, match="filed under"):
        oracle.validate_payoff_surface(misfiled, "lookup_atomic")
    mixed_keys = {a: {cluster: {observation_id(cluster): 1}, 7: {"o": 1}}
                  for a in oracle.enumerate_assignments(1)}
    with pytest.raises(oracle.PayoffSurfaceError, match="not a str"):
        oracle.validate_payoff_surface(mixed_keys, "lookup_atomic")


def test_surface_correctness_is_binary():
    """A 0.5 GRPO reward for a well-formed world failure must never be
    averaged into a terminal-accuracy surface."""
    with pytest.raises(oracle.PayoffSurfaceError, match="must be 0 or 1"):
        oracle.validate_payoff_surface(_atomic_surface(value=0.5),
                                       "lookup_atomic")


def test_forged_validated_surface_cannot_reach_selectors():
    """The dataclass constructor re-checks its invariants, so a directly
    constructed or deserialized surface is not an unchecked back door."""
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.ValidatedSurface(
            kind="assignment", cell_id="lookup_atomic", candidates=((9,),),
            clusters=("c1",), observations={"c1": ("o1",)},
            data={(9,): {"c1": {"o1": 1}}})


def test_selectors_require_a_validated_surface():
    for call in (oracle.select_deployable, oracle.best_fixed,
                 oracle.uniform_random_accuracy):
        with pytest.raises(oracle.PayoffSurfaceError, match="ValidatedSurface"):
            call(TOY_RAW)
    surface = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.select_best_one_call(surface)   # wrong surface kind
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.node_runner_up(surface, [0, 1], 0)   # list, not tuple
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.node_runner_up(surface, (0, 1), 5)   # node index range


def test_semantic_to_positional_both_fork_orders():
    assignment = (0, 2, 1)  # stable node order (n1, n2, n3)
    assert oracle.semantic_to_positional(assignment, "fork_join",
                                         ["n1", "n2", "n3"]) == [0, 2, 1]
    assert oracle.semantic_to_positional(assignment, "fork_join",
                                         ["n2", "n1", "n3"]) == [2, 0, 1]


def test_signed_gap_paired_and_unclipped():
    deployable = {"c1": {"o1": 1, "o2": 1}, "c2": {"o3": 1}}
    policy = {"c1": {"o1": 1, "o2": 0}, "c2": {"o3": 0}}  # malformed -> 0
    assert oracle.signed_deployable_gap(deployable, policy) == \
        pytest.approx(0.75)
    better = {"c1": {"o1": 1, "o2": 1}, "c2": {"o3": 1}}
    worse = {"c1": {"o1": 0, "o2": 0}, "c2": {"o3": 1}}
    assert oracle.signed_deployable_gap(worse, better) == pytest.approx(-0.5)
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.signed_deployable_gap(deployable, {"c1": {"o1": 1}})
    with pytest.raises(oracle.PayoffSurfaceError):  # unpaired observations
        oracle.signed_deployable_gap(
            {"c1": {"o1": 1}}, {"c1": {"o9": 1}})


FJ_C1, FJ_C2 = cluster_ids("fork_join")


def _candidate_surface(candidates, value_for):
    return {c: {FJ_C1: {observation_id(FJ_C1): value_for(c)},
                FJ_C2: {observation_id(FJ_C2): value_for(c)}}
            for c in candidates}


def test_two_call_family_and_tie_order():
    workflows = oracle.enumerate_two_call_workflows()
    assert len(workflows) == 18
    assert workflows[0] == ("lookup_first", (0, 0))
    tied = oracle.validate_two_call_surface(
        _candidate_surface(workflows, lambda c: 1), "fork_join")
    assert oracle.select_best_two_call(tied) == ("lookup_first", (0, 0))
    one_call = oracle.validate_one_call_surface(
        _candidate_surface(oracle.ENDPOINT_IDS,
                           lambda e: 1 if e in (0, 1) else 0), "fork_join")
    assert oracle.select_best_one_call(one_call) == 0  # tie -> lowest index


def test_control_surfaces_are_observation_paired_too():
    workflows = oracle.enumerate_two_call_workflows()
    raw = _candidate_surface(workflows, lambda c: 1)
    raw[workflows[3]] = {FJ_C1: {observation_id(FJ_C1, "goal_first"): 1},
                         FJ_C2: {observation_id(FJ_C2): 1}}
    with pytest.raises(oracle.PayoffSurfaceError, match="observation ids"):
        oracle.validate_two_call_surface(raw, "fork_join")
    partial = {0: {FJ_C1: {observation_id(FJ_C1): 1}},
               1: {FJ_C1: {observation_id(FJ_C1): 1}}}
    with pytest.raises(oracle.PayoffSurfaceError, match="full enumeration"):
        oracle.validate_one_call_surface(partial, "fork_join")


def test_control_candidate_types_are_exact():
    """`False` and `0.0` hash equal to `0`, so key equality alone would
    admit an endpoint id of the wrong type."""
    for bad_key in (False, 0.0):
        raw = _candidate_surface(oracle.ENDPOINT_IDS, lambda e: 1)
        raw[bad_key] = raw.pop(0)
        with pytest.raises(oracle.PayoffSurfaceError, match="must be an int"):
            oracle.validate_one_call_surface(raw, "fork_join")


def test_two_call_family_is_only_defined_for_fork_join():
    raw = _candidate_surface(oracle.enumerate_two_call_workflows(),
                             lambda c: 1)
    with pytest.raises(oracle.PayoffSurfaceError, match="not defined"):
        oracle.validate_two_call_surface(raw, "lookup_math")
    for cell in ("bogus", ""):
        with pytest.raises(oracle.PayoffSurfaceError, match="unknown cell_id"):
            oracle.validate_one_call_surface(raw, cell)


# --- §1.8 calibration bundle: controls share the assignment population -----

def test_calibration_bundle_requires_one_shared_population():
    assignment = oracle.validate_payoff_surface(
        {a: {FJ_C1: {observation_id(FJ_C1): 1},
             FJ_C2: {observation_id(FJ_C2): 0}}
         for a in oracle.enumerate_assignments(3)}, "fork_join")
    one_call = oracle.validate_one_call_surface(
        _candidate_surface(oracle.ENDPOINT_IDS, lambda e: 0), "fork_join")
    bundle = oracle.CalibrationBundle(assignment=assignment,
                                      one_call=one_call)
    assert bundle.cell_id == "fork_join"
    assert bundle.deployable() == (0, 0, 0)
    assert bundle.best_one_call() == 0
    assert bundle.deployable_vs_one_call() == pytest.approx(0.5)

    # A control scored on a disjoint population would silently invalidate
    # the oracle-versus-one-call gate.
    other1, other2 = cluster_ids("fork_join", 4)[2:]
    disjoint = oracle.validate_one_call_surface(
        {e: {other1: {observation_id(other1): 1},
             other2: {observation_id(other2): 1}}
         for e in oracle.ENDPOINT_IDS}, "fork_join")
    with pytest.raises(oracle.PayoffSurfaceError, match="different clusters"):
        oracle.CalibrationBundle(assignment=assignment, one_call=disjoint)


def test_calibration_bundle_rejects_cross_cell_controls():
    assignment = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    fork_control = oracle.validate_one_call_surface(
        _candidate_surface(oracle.ENDPOINT_IDS, lambda e: 1), "fork_join")
    with pytest.raises(oracle.PayoffSurfaceError, match="for cell"):
        oracle.CalibrationBundle(assignment=assignment,
                                 one_call=fork_control)


def test_calibration_bundle_reports_missing_controls():
    assignment = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    bundle = oracle.CalibrationBundle(assignment=assignment)
    for call in (bundle.best_one_call, bundle.best_two_call,
                 bundle.deployable_vs_one_call, bundle.deployable_vs_two_call):
        with pytest.raises(oracle.PayoffSurfaceError, match="no .*surface"):
            call()


# --- §4 agreement command coverage accounting -------------------------------

def test_agreement_plan_covers_the_request_exactly():
    from tasks.conductor import agreement
    for cases in (6, 10, 100, 9999, 10_000):
        plan = agreement.plan_cases(cases, "train")
        assert sum(plan.values()) == cases  # no dropped remainder
        assert set(plan) == set(ALL_CELLS)
        assert max(plan.values()) - min(plan.values()) <= 1


def test_agreement_rejects_impossible_requests():
    from tasks.conductor import agreement
    with pytest.raises(ValueError):
        agreement.plan_cases(5, "train")            # fewer cases than cells
    with pytest.raises(ValueError):
        agreement.plan_cases(100_000, "construction")  # exceeds the caps


def test_agreement_reports_failure_on_incomplete_coverage():
    """A run too small to exercise every operator × cell stratum must fail
    rather than report success on partial coverage."""
    from tasks.conductor import agreement
    assert agreement.run(6, "train") == 1        # 1 latent/cell: T2/T3 unseen
    assert agreement.run(60, "train") == 0       # full strata coverage


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
