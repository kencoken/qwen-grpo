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

# 106_s §8: routing bijection for the 4/16/64 four-worker assignments.
@pytest.mark.parametrize("num_steps", [1, 2, 3])
def test_routing_bijection(num_steps):
    seen = set()
    for ids in itertools.product((0, 1, 2, 3), repeat=num_steps):
        parsed = parse_routing_action(json.dumps({"worker_ids": list(ids)}),
                                      num_steps)
        seen.add(tuple(parsed))
    assert len(seen) == 4 ** num_steps


@pytest.mark.parametrize("completion", [
    "not json",
    '{"worker_ids": [0, 1], "extra": 1}',
    '{"workers": [0, 1]}',
    '{"worker_ids": [0]}',              # wrong length
    '{"worker_ids": [0, 1, 2]}',        # wrong length
    '{"worker_ids": [0, 4]}',           # out of range -> malformed, not world
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
    # 106_s: the seven worker-3 assignments completing the 4^2 surface;
    # all-zero rows leave every pinned tie above unchanged.
    **{pair: (0, 0, 0)
       for pair in [(0, 3), (1, 3), (2, 3), (3, 0), (3, 1), (3, 2),
                    (3, 3)]},
})


def test_oracle_toy_surface():
    surface = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    assert surface.accuracy((1, 1)) == 0.75
    assert oracle.select_deployable(surface) == (0, 1)  # tie -> lexicographic
    assert oracle.best_fixed(surface) == (1, 1)
    assert oracle.uniform_random_accuracy(surface) == pytest.approx(5.25 / 16)
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


@pytest.mark.parametrize("field,value", [
    ("cell_id", ["lookup_atomic"]),   # unhashable: `in` would raise TypeError
    ("cell_id", None),
    ("kind", ["assignment"]),
    ("kind", 7),
])
def test_surface_field_types_are_checked_before_membership(field, value):
    surface = oracle.validate_payoff_surface(_atomic_surface(),
                                             "lookup_atomic")
    kwargs = dict(kind=surface.kind, cell_id=surface.cell_id,
                  candidates=surface.candidates, clusters=surface.clusters,
                  observations=dict(surface.observations),
                  data=dict(surface.data))
    kwargs[field] = value
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.ValidatedSurface(**kwargs)


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
    # 106_s §6.3: 2 orientations x 4 x 4 workers, derived from the
    # registry (32 is an acceptance expectation, not a source of truth).
    workflows = oracle.enumerate_two_call_workflows()
    assert len(workflows) == 32
    assert workflows[0] == ("lookup_first", (0, 0))
    tied = oracle.validate_two_call_surface(
        _candidate_surface(workflows, lambda c: 1), "fork_join")
    assert oracle.select_best_two_call(tied) == ("lookup_first", (0, 0))
    one_call = oracle.validate_one_call_surface(
        _candidate_surface(oracle.WORKER_IDS,
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
        raw = _candidate_surface(oracle.WORKER_IDS, lambda e: 1)
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
        _candidate_surface(oracle.WORKER_IDS, lambda e: 0), "fork_join")
    bundle = oracle.CalibrationBundle(assignment=assignment,
                                      one_call=one_call)
    assert bundle.cell_id == "fork_join"
    frozen = bundle.freeze_selections()
    assert frozen.deployable == (0, 0, 0)
    assert frozen.best_one_call == 0
    assert bundle.descriptive_deployable_minus_one_call(frozen, bundle) == \
        pytest.approx(0.5)

    # A control scored on a disjoint population would silently invalidate
    # the oracle-versus-one-call gate.
    other1, other2 = cluster_ids("fork_join", 4)[2:]
    disjoint = oracle.validate_one_call_surface(
        {e: {other1: {observation_id(other1): 1},
             other2: {observation_id(other2): 1}}
         for e in oracle.WORKER_IDS}, "fork_join")
    with pytest.raises(oracle.PayoffSurfaceError, match="different clusters"):
        oracle.CalibrationBundle(assignment=assignment, one_call=disjoint)


# --- §1.8 / plan contract 7: selected on construction, never reselected ----

def _surface_for(cell, namespace, winner, num_nodes):
    clusters = cluster_ids(cell, 2, namespace)
    return oracle.validate_payoff_surface(
        {a: {c: {observation_id(c): (1 if a == winner else 0)}
             for c in clusters}
         for a in oracle.enumerate_assignments(num_nodes)}, cell)


def test_selection_is_construction_only():
    """Re-maximizing at a qualification look would change the hypothesis
    the pre-registered alpha spending is tested against."""
    qualification = _surface_for("lookup_math", "qualification", (2, 2), 2)
    for call in (oracle.select_deployable, oracle.best_fixed):
        with pytest.raises(oracle.PayoffSurfaceError,
                           match="never reselected"):
            call(qualification)
    with pytest.raises(oracle.PayoffSurfaceError, match="never reselected"):
        oracle.node_runner_up(qualification, (0, 0), 0)
    with pytest.raises(oracle.PayoffSurfaceError, match="never reselected"):
        oracle.CalibrationBundle(assignment=qualification).freeze_selections()
    # Descriptive statistics remain computable on any split.
    assert 0.0 <= oracle.uniform_random_accuracy(qualification) <= 1.0


def test_qualification_evaluates_the_frozen_choice_not_its_own_argmax():
    construction = _surface_for("lookup_math", "construction", (0, 0), 2)
    construction_bundle = oracle.CalibrationBundle(assignment=construction)
    frozen = construction_bundle.freeze_selections()
    assert frozen.deployable == (0, 0)

    # Fresh qualification data where a different assignment happens to win.
    qualification = _surface_for("lookup_math", "qualification", (2, 2), 2)
    bundle = oracle.CalibrationBundle(assignment=qualification)
    # Evaluation verifies the frozen choice against its construction bundle
    # in the same call, then evaluates it as-is: 0.0 here, not the 1.0 that
    # reselecting on qualification outcomes would have reported.
    assert bundle.deployable_accuracy(frozen, construction_bundle) == \
        pytest.approx(0.0)
    assert qualification.accuracy((2, 2)) == pytest.approx(1.0)
    assert not hasattr(bundle, "deployable")  # no argmax on the eval path


def test_frozen_selections_round_trip_and_validate():
    construction = _surface_for("fork_join", "construction", (0, 1, 2), 3)
    one_call = oracle.validate_one_call_surface(
        {e: {c: {observation_id(c): 1} for c in construction.clusters}
         for e in oracle.WORKER_IDS}, "fork_join")
    frozen = oracle.CalibrationBundle(assignment=construction,
                                      one_call=one_call).freeze_selections()
    assert frozen.deployable == (0, 1, 2)
    assert set(frozen.node_runner_ups) == {"n1", "n2", "n3"}
    revived = oracle.FrozenSelections.from_json(
        json.loads(json.dumps(frozen.to_json())))
    assert revived == frozen
    with pytest.raises(oracle.PayoffSurfaceError):
        oracle.FrozenSelections.from_json({"cell_id": "fork_join"})


def _selections(cell="lookup_math", **overrides):
    fields = dict(cell_id=cell, namespace="construction", deployable=(0, 0),
                  best_fixed_assignment=(0, 0),
                  node_runner_ups={"n1": (1, 0), "n2": (0, 1)},
                  construction_random_accuracy=0.5,
                  source_surface_digest="cb-test")
    fields.update(overrides)
    return oracle.FrozenSelections(**fields)


def test_frozen_selections_are_semantically_valid():
    """The stored fields carry scientific meaning: a heterogeneous tuple
    under the `best_fixed` label, or a runner-up that changes the wrong
    node, would be a different quantity than the one the label names."""
    _selections()  # the well-formed baseline
    cases = [
        ({"namespace": "qualification"}, "construction"),
        ({"cell_id": "bogus"}, "unknown cell_id"),
        # best_fixed is the best *constant* assignment (§1.8).
        ({"best_fixed_assignment": (0, 1)}, "not constant"),
        ({"node_runner_ups": {}}, "must cover exactly"),
        ({"node_runner_ups": {"n1": (1, 0)}}, "must cover exactly"),
        # A runner-up changes its own node and nothing else.
        ({"node_runner_ups": {"n1": (0, 0), "n2": (0, 1)}}, "exactly that node"),
        ({"node_runner_ups": {"n1": (1, 1), "n2": (0, 1)}}, "exactly that node"),
        ({"construction_random_accuracy": float("nan")}, "finite number"),
        ({"construction_random_accuracy": 1.5}, "finite number"),
        ({"source_surface_digest": ""}, "non-empty"),
    ]
    for overrides, match in cases:
        with pytest.raises(oracle.PayoffSurfaceError, match=match):
            _selections(**overrides)
    # The two-call family exists only for fork_join.
    with pytest.raises(oracle.PayoffSurfaceError, match="not defined"):
        _selections(best_two_call=("lookup_first", (0, 0)))


@pytest.mark.parametrize("mutate,match", [
    (lambda j: j.update(deployable="00"), "list of ints"),
    (lambda j: j.update(deployable=[0, "1"]), "non-int"),
    (lambda j: j.update(node_runner_ups=[]), "must be an object"),
    (lambda j: j.update(node_runner_ups={"n1": None}), "list of ints"),
    # tuple() would silently truncate this to a valid-looking pair.
    (lambda j: j.update(best_two_call=["lookup_first", [0, 0, 0]]),
     "exactly 2 entries"),
    (lambda j: j.update(best_two_call=["lookup_first"]), "orientation"),
    (lambda j: j.update(best_two_call=42), "orientation"),
])
def test_frozen_selections_json_is_totally_validated(mutate, match):
    construction = _surface_for("lookup_math", "construction", (0, 0), 2)
    payload = oracle.CalibrationBundle(assignment=construction) \
        .freeze_selections().to_json()
    mutate(payload)
    with pytest.raises(oracle.PayoffSurfaceError, match=match):
        oracle.FrozenSelections.from_json(payload)


def test_frozen_selections_are_bound_to_their_source_bundle():
    """Local invariants cannot prove a stored candidate really was the
    argmax; re-deriving it from the fingerprinted source can."""
    construction = _surface_for("lookup_math", "construction", (0, 0), 2)
    bundle = oracle.CalibrationBundle(assignment=construction)
    frozen = bundle.freeze_selections()
    frozen.verify_against(bundle)                      # raises if not argmax
    assert frozen.source_surface_digest == bundle.surface_digest()

    other = oracle.CalibrationBundle(
        assignment=_surface_for("lookup_math", "construction", (1, 1), 2))
    with pytest.raises(oracle.PayoffSurfaceError,
                       match="different construction population"):
        frozen.verify_against(other)

    forged = _selections(cell="lookup_math", deployable=(2, 2),
                         best_fixed_assignment=(2, 2),
                         node_runner_ups={"n1": (0, 2), "n2": (2, 0)},
                         source_surface_digest=bundle.surface_digest())
    with pytest.raises(oracle.PayoffSurfaceError, match="do not match the "
                                                       "argmax"):
        forged.verify_against(bundle)


def test_random_control_belongs_to_the_surface_being_evaluated():
    """The `random` control is the uniform mean over the surface under
    evaluation, so the construction value is only a diagnostic."""
    construction = _surface_for("lookup_math", "construction", (0, 0), 2)
    frozen = oracle.CalibrationBundle(assignment=construction) \
        .freeze_selections()
    assert frozen.construction_random_accuracy == pytest.approx(1 / 16)
    assert not hasattr(frozen, "random_accuracy")
    qualification = _surface_for("lookup_math", "qualification", (2, 2), 2)
    qual_bundle = oracle.CalibrationBundle(assignment=qualification)
    assert qual_bundle.random_accuracy() == pytest.approx(1 / 16)


# --- population and execution provenance ------------------------------------

def test_surface_covers_exactly_one_split():
    """Gates are defined per split, and selection is construction-only, so
    a surface mixing namespaces is not a population."""
    con = cluster_ids("lookup_math", 1)[0]
    qual = program.generate_latent("lookup_math", "qualification", 0,
                                   PROF).latent["latent_program_id"]
    mixed = {a: {con: {observation_id(con): 1},
                 qual: {observation_id(qual): 1}}
             for a in oracle.enumerate_assignments(2)}
    with pytest.raises(oracle.PayoffSurfaceError, match="mixes namespaces"):
        oracle.validate_payoff_surface(mixed, "lookup_math")


def test_stage_1_gate_evaluation_is_explicitly_unavailable():
    """The bundle's numbers are descriptive: binding a surface to the
    registered population and to one execution environment needs Stage-0B
    fingerprints and the Stage-1A calibration layer. Anything reaching for
    a gate result must fail loudly rather than accept a bare float."""
    surface = _surface_for("lookup_math", "construction", (0, 0), 2)
    bundle = oracle.CalibrationBundle(assignment=surface)
    frozen = bundle.freeze_selections()
    with pytest.raises(oracle.PayoffSurfaceError, match="Stage-1A gate"):
        bundle.gate_report(frozen, bundle)
    # The descriptive helpers are named so they cannot be mistaken for it.
    assert hasattr(bundle, "descriptive_deployable_minus_one_call")
    assert not hasattr(bundle, "deployable_vs_one_call")
    assert "not implemented at Stage 0A" in oracle.GATE_PROVENANCE_REQUIREMENT


def test_evaluation_rejects_selections_from_another_cell():
    construction = _surface_for("lookup_math", "construction", (0, 0), 2)
    source = oracle.CalibrationBundle(assignment=construction)
    frozen = source.freeze_selections()
    other = _surface_for("math_code", "construction", (0, 0), 2)
    with pytest.raises(oracle.PayoffSurfaceError, match="selections are for"):
        oracle.CalibrationBundle(assignment=other).deployable_accuracy(
            frozen, source)


def test_evaluation_verifies_against_the_construction_bundle_in_one_call():
    """A locally valid but forged artifact cannot be evaluated: there is no
    wrappable 'verified' marker, and evaluation re-derives the argmax from
    the construction bundle it is handed."""
    construction = oracle.CalibrationBundle(
        assignment=_surface_for("lookup_math", "construction", (0, 0), 2))
    qualification = oracle.CalibrationBundle(
        assignment=_surface_for("lookup_math", "qualification", (2, 2), 2))
    forged = _selections(cell="lookup_math", deployable=(2, 2),
                         best_fixed_assignment=(2, 2),
                         node_runner_ups={"n1": (0, 2), "n2": (2, 0)},
                         source_surface_digest=construction.surface_digest())
    with pytest.raises(oracle.PayoffSurfaceError, match="do not match"):
        qualification.deployable_accuracy(forged, construction)


def test_calibration_bundle_rejects_cross_cell_controls():
    assignment = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    fork_control = oracle.validate_one_call_surface(
        _candidate_surface(oracle.WORKER_IDS, lambda e: 1), "fork_join")
    with pytest.raises(oracle.PayoffSurfaceError, match="for cell"):
        oracle.CalibrationBundle(assignment=assignment,
                                 one_call=fork_control)


def test_calibration_bundle_reports_missing_controls():
    assignment = oracle.validate_payoff_surface(TOY_RAW, "lookup_math")
    bundle = oracle.CalibrationBundle(assignment=assignment)
    frozen = bundle.freeze_selections()
    assert frozen.best_one_call is None and frozen.best_two_call is None
    for call in (bundle.one_call_accuracy, bundle.two_call_accuracy,
                 bundle.descriptive_deployable_minus_one_call,
                 bundle.descriptive_deployable_minus_two_call):
        with pytest.raises(oracle.PayoffSurfaceError, match="no .*surface"):
            call(frozen, bundle)


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
    # 32 registry-derived two-call workflows x 2 calls (106_s §6.3).
    assert sum(1 for k in stored if k.startswith("two_call")) == 64


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


# =============================================================================
# 108_f: worker-3 execution boundary (findings 1 and 4).
# =============================================================================

def test_worker_3_executes_the_code_family():
    """106_s §6.2: worker 3 resolves to the Code grammar/tool at the
    artifact boundary and reaches the terminal exactly like worker 2."""
    latent, inst, registry, steps = make_env("code_atomic")
    worker_ids, worker_call = perfect_worker(latent)
    assert worker_ids == [2]
    for code_worker in (2, 3):
        action = parser.routing_to_workflow([code_worker], steps)
        result = executor.execute_workflow(action, inst["public_prompt"],
                                           registry, worker_call)
        assert result.terminal == inst["gold_answer"], code_worker
        assert result.steps[0].result.status == "success"


def test_worker_3_executes_in_a_composed_workflow():
    latent, inst, registry, steps = make_env("fork_join")
    worker_ids, worker_call = perfect_worker(latent)
    swapped = [3 if w == 2 else w for w in worker_ids]
    assert swapped != worker_ids  # fork_join routes one code node
    action = parser.routing_to_workflow(swapped, steps)
    result = executor.execute_workflow(action, inst["public_prompt"],
                                       registry, worker_call)
    assert result.terminal == inst["gold_answer"]
    assert [r.worker_id for r in result.steps] == swapped


def test_wrong_family_selection_is_a_typed_failure_not_an_abort():
    """Selecting an incompatible family is a well-formed world action
    (reward 0.5), for worker 3 exactly as for workers 0-2 (106_s §6.2)."""
    latent, inst, registry, steps = make_env("lookup_atomic")
    _, worker_call = perfect_worker(latent)
    for wrong_worker in (1, 3):
        action = parser.routing_to_workflow([wrong_worker], steps)
        result = executor.execute_workflow(action, inst["public_prompt"],
                                           registry, worker_call)
        assert result.steps[0].result.status == "typed_failure", wrong_worker
        assert result.terminal is None
        assert executor.score_terminal(result.terminal,
                                       inst["gold_answer"]) == 0.5


def test_unregistered_worker_id_is_an_infrastructure_error():
    """The parser bounds actions to the pool; a directly constructed
    workflow with an unregistered id must abort, never guess a family."""
    latent, inst, registry, steps = make_env("lookup_atomic")
    _, worker_call = perfect_worker(latent)
    action = parser.WorkflowAction(steps=(parser.WorkflowStep(
        subtask=steps[0]["subtask"], worker_id=7,
        resource=steps[0]["resource"], access="none"),))
    with pytest.raises(executor.InfrastructureError,
                       match="not in the registered pool"):
        executor.execute_workflow(action, inst["public_prompt"],
                                  registry, worker_call)


def test_worker_3_refuses_the_v1_trace_schema():
    """108_f finding 4: the v1 trace schema is pool-free; recording
    worker 3 under it fails closed until the unit-2 trace schema."""
    latent, inst, registry, steps = make_env("code_atomic")
    _, worker_call = perfect_worker(latent)
    record = executor.StepRecord(1, 3, None, "unknown_handle", None, None,
                                 False)
    item = executor.WorkflowItem(
        item_id="t", action=parser.routing_to_workflow([3], steps),
        public_prompt=inst["public_prompt"], registry=registry)

    class _Sentinel:
        def write_step(self, *args):
            raise AssertionError("worker 3 must not reach a v1 trace")

    with pytest.raises(executor.InfrastructureError, match="trace schema"):
        executor._trace_step(_Sentinel(), item, record, None)


def test_workflow_action_worker_domain():
    """108_f smaller issue: the full-workflow parser accepts worker 3
    and rejects worker 4."""
    def wf(worker_id):
        return json.dumps({"steps": [{"subtask": "s", "worker_id": worker_id,
                                      "resource": "R-1A1", "access": "none"}]})
    parsed = parser.parse_workflow_action(wf(3))
    assert parsed.steps[0].worker_id == 3
    with pytest.raises(ActionSchemaError, match="outside"):
        parser.parse_workflow_action(wf(4))
