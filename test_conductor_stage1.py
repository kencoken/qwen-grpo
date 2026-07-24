"""Unit-1 acceptance tests — 132_s (approved 133_f; revised per 134_s).

Covers the D4 cohort erratum (range/cap rejection AND exact joint factorial
balance over indices 30-129), the policy_dev registration, the fail-closed
identity checks pinning tasks/conductor/stage1.py to the artifacts it names
(SYSTEM_DIRECT bytes, DEFAULT_PROFILE digest, the cascade trigger set, look
schedules), and the 134_s findings: per-edge intervention cross-product,
the machine-readable protocol-denominator contract across all six cells and
four workers, the two frozen prompt candidates with the no-repair decision,
and exact-literal pins for the retry and threshold tables.
"""

import hashlib
from collections import Counter

import pytest

from tasks.conductor import program, stage1
from tasks.conductor.profiles import DEFAULT_PROFILE, profile_version
from tasks.conductor.program import (
    CONSTRUCTION_CONSUMED_PREFIX, CONSTRUCTION_FORMAL_COHORT,
    GENERATOR_VERSION, GenerationError, LoadError, NAMESPACE_CONFIG,
    POLICY_DEV_COHORTS, factor_assignment, generate_latent, namespace_cap,
    policy_dev_cohort, validate_construction_cohort,
)
from tasks.conductor.prompts import SYSTEM_DIRECT
from tasks.conductor.types import NAMESPACES, SYNTAX_REJECTION_CODES

CELLS = ("lookup_atomic", "math_atomic", "code_atomic",
         "lookup_math", "math_code", "fork_join")
DPV = profile_version(DEFAULT_PROFILE)


# --- D4: range and cap ------------------------------------------------------

def test_construction_cap_is_130():
    for cell in CELLS:
        assert namespace_cap("construction", cell) == 130


def test_formal_cohort_bounds():
    assert list(CONSTRUCTION_CONSUMED_PREFIX) == list(range(30))
    assert list(CONSTRUCTION_FORMAL_COHORT) == list(range(30, 130))
    assert len(CONSTRUCTION_FORMAL_COHORT) == 100


def test_validate_construction_cohort_accepts_exact_cohort():
    validate_construction_cohort(list(range(30, 130)))


@pytest.mark.parametrize("bad", [
    list(range(29, 129)),          # consumed-prefix index 29
    list(range(31, 131)),          # 130 outside the cap
    list(range(30, 129)),          # incomplete (missing 129)
    list(range(30, 130)) + [30],   # duplicate
    list(range(0, 100)),           # the historical pre-D4 cohort
])
def test_validate_construction_cohort_fails_closed(bad):
    with pytest.raises(LoadError):
        validate_construction_cohort(bad)


def test_validate_construction_cohort_rejects_bool_and_nonint():
    with pytest.raises(LoadError):
        validate_construction_cohort([True] + list(range(31, 130)))
    with pytest.raises(LoadError):
        validate_construction_cohort(["30"] + list(range(31, 130)))


# --- D4: exact joint factorial balance over 30-129 --------------------------

def test_index_30_is_block_aligned_for_every_cell():
    # 132_s §3.1: index 30 begins on a block boundary for every frozen
    # factor-block size; block sizes come from the real CELL_FACTORS.
    for cell in CELLS:
        factors = program.CELL_FACTORS[cell]
        block = 1
        for _, levels in factors:
            block *= len(levels)
        assert 30 % block == 0, (cell, block)


@pytest.mark.parametrize("cell", CELLS)
def test_formal_cohort_joint_factor_balance(cell):
    # Recompute the exact joint contingency table over indices 30-129 and
    # require every registered joint level within one count of every
    # other. Marginal presence alone is not evidence of balance
    # (132_s §3.1); this checks the full joint assignment.
    factors = program.CELL_FACTORS[cell]
    if not factors:  # math_code: no categorical factors
        return
    joint = Counter(
        tuple(sorted(factor_assignment(
            GENERATOR_VERSION, DPV, "construction", cell, i).items()))
        for i in CONSTRUCTION_FORMAL_COHORT)
    block = 1
    for _, levels in factors:
        block *= len(levels)
    # every joint level of the full product must appear
    assert len(joint) == block, (cell, len(joint), block)
    counts = joint.values()
    assert max(counts) - min(counts) <= 1, (cell, dict(joint))
    assert sum(counts) == 100


def test_consumed_prefix_still_generable_for_historical_verification():
    # 0-29 stay generable (the D16 artifacts must remain regenerable);
    # exclusion is the manifest's job, not the generator's.
    r = generate_latent("code_atomic", "construction", 0, DEFAULT_PROFILE)
    assert r.latent["latent_index"] == 0


# --- policy_dev registration -------------------------------------------------

def test_policy_dev_registered():
    assert "policy_dev" in NAMESPACES
    assert namespace_cap("policy_dev", "code_atomic") == 1_000
    assert NAMESPACE_CONFIG["policy_dev"]["stopping_rule"] == "fixed"


def test_policy_dev_cohorts_disjoint_and_complete():
    ranges = list(POLICY_DEV_COHORTS.values())
    seen = set()
    for rng in ranges:
        assert not (set(rng) & seen)
        seen |= set(rng)
    assert seen == set(range(1_000))
    assert list(POLICY_DEV_COHORTS["format_a"]) == list(range(0, 24))
    assert list(POLICY_DEV_COHORTS["format_b"]) == list(range(24, 48))
    assert list(POLICY_DEV_COHORTS["cold_start"]) == list(range(48, 1_000))


def test_policy_dev_cohort_lookup():
    assert policy_dev_cohort(0) == "format_a"
    assert policy_dev_cohort(23) == "format_a"
    assert policy_dev_cohort(24) == "format_b"
    assert policy_dev_cohort(47) == "format_b"
    assert policy_dev_cohort(48) == "cold_start"
    assert policy_dev_cohort(999) == "cold_start"
    with pytest.raises(LoadError):
        policy_dev_cohort(1_000)


def test_policy_dev_generation_within_cap():
    r = generate_latent("lookup_atomic", "policy_dev", 999, DEFAULT_PROFILE)
    assert r.latent["namespace"] == "policy_dev"
    with pytest.raises(GenerationError):
        generate_latent("lookup_atomic", "policy_dev", 1_000, DEFAULT_PROFILE)


def test_policy_dev_disjoint_from_other_namespaces():
    # Same index, different namespace => different latent identity/values.
    a = generate_latent("code_atomic", "policy_dev", 48, DEFAULT_PROFILE)
    b = generate_latent("code_atomic", "construction", 48, DEFAULT_PROFILE)
    assert a.latent["latent_program_id"] != b.latent["latent_program_id"]


# --- stage1 constants: fail-closed identity checks ---------------------------

def test_system_direct_digest_pinned():
    assert hashlib.sha256(SYSTEM_DIRECT.encode("utf-8")).hexdigest() == \
        stage1.SYSTEM_DIRECT_SHA256


def test_primary_profile_digest_pinned():
    assert profile_version(DEFAULT_PROFILE) == stage1.PRIMARY_PROFILE_VERSION
    for cell in CELLS:
        assert stage1.PROFILE_CANDIDATES[cell] == (
            stage1.PRIMARY_PROFILE_VERSION,)


def test_cascade_trigger_codes_match_types():
    assert stage1.CASCADE_TRIGGER_CODES == SYNTAX_REJECTION_CODES
    assert stage1.CASCADE_TRIGGER_CODES == frozenset({
        "E_NO_ARTIFACT", "E_MULTI_ARTIFACT", "E_UNCLOSED_ARTIFACT",
        "E_UNEXPECTED_TAG", "E_PARSE", "E_NONCANONICAL_INT", "E_DEPTH"})


def test_infra_retry_codes_disjoint_from_typed_rejections():
    # Infrastructure retry codes are a separate taxonomy from the typed
    # rejection contract (132_s §7.3): no overlap, and every entry is
    # bounded with at least one backoff step.
    from tasks.conductor.types import REJECTION_CODES
    assert not (set(stage1.INFRA_RETRY_CODES) & REJECTION_CODES)
    for code, rule in stage1.INFRA_RETRY_CODES.items():
        assert code.startswith("E_INFRA_"), code
        assert isinstance(rule["max_attempts"], int)
        assert 2 <= rule["max_attempts"] <= 3, code
        assert len(rule["backoff_seconds"]) >= 1


def test_look_schedules_match_namespace_config():
    q = NAMESPACE_CONFIG["qualification"]
    assert tuple(q["look_schedule"]) == stage1.ORDINARY_LOOK_SCHEDULE
    assert tuple(q["fork_join"]["look_schedule"]) == stage1.FORK_LOOK_SCHEDULE
    assert q["max_latent_clusters"] == stage1.ORDINARY_LOOK_SCHEDULE[-1]
    assert (q["fork_join"]["max_latent_clusters"]
            == stage1.FORK_LOOK_SCHEDULE[-1])


def test_alpha_arithmetic():
    assert stage1.ORDINARY_LOOK_TAIL_ALPHA == pytest.approx(0.05 / 3)
    assert stage1.FORK_LOOK_TAIL_ALPHA == pytest.approx(0.05 / 2)
    assert stage1.MODEL_POSITION_ALPHA_DIVISOR == 3
    assert stage1.AGGREGATE_ROUTER_ALPHA == pytest.approx(0.025)
    # the two one-sided router branch tests split 0.05 exactly
    assert 2 * stage1.AGGREGATE_ROUTER_ALPHA == pytest.approx(
        stage1.ALPHA_TOTAL)


def test_gate_matrix_positions_exist_in_generated_programs():
    # Every C1/C2 position named by the matrix is a real semantic node id
    # of that cell's reference program (checked against generation, not
    # against a hand-maintained list).
    for cell, spec in stage1.GATE_MATRIX.items():
        r = generate_latent(cell, "worker_dev", 0, DEFAULT_PROFILE)
        node_ids = {n["id"] for n in r.latent["reference_program"]["nodes"]}
        for pos in spec["c1_positions"] + spec["c2_positions"]:
            assert pos in node_ids, (cell, pos, node_ids)


def test_c2_universe_matches_gate_matrix():
    expected = tuple(
        (cell, pos)
        for cell in ("code_atomic", "math_code", "fork_join")
        for pos in stage1.GATE_MATRIX[cell]["c2_positions"])
    assert stage1.C2_POSITION_UNIVERSE == expected


def test_core_cells_are_the_five_mandatory_cells():
    assert set(stage1.CORE_CELLS) == set(CELLS) - {"fork_join"}


def test_visible_slice_is_first_18():
    vs = stage1.VISIBLE_SLICE_QUALIFICATION_CLUSTERS
    assert list(vs) == list(range(18))
    # divisible by every frozen factor-block size (132_s §4.1)
    for cell in CELLS:
        factors = program.CELL_FACTORS[cell]
        block = 1
        for _, levels in factors:
            block *= len(levels)
        assert 18 % block == 0, (cell, block)


def test_bootstrap_seed_deterministic_and_sensitive():
    m1, m2 = "a" * 64, "b" * 64
    looks = {"code_atomic": 300}
    s1 = stage1.bootstrap_seed(m1, "gate_a", looks)
    s2 = stage1.bootstrap_seed(m1, "gate_a", looks)
    s3 = stage1.bootstrap_seed(m1, "gate_b", looks)
    s4 = stage1.bootstrap_seed(m2, "gate_a", looks)
    assert s1 == s2
    assert len({s1, s3, s4}) == 3
    assert 0 <= s1 < 2 ** 64


def test_bootstrap_seed_validates_inputs():
    looks = {"code_atomic": 300}
    with pytest.raises(ValueError):        # not 64 chars
        stage1.bootstrap_seed("abc", "gate_a", looks)
    with pytest.raises(ValueError):        # uppercase hex rejected
        stage1.bootstrap_seed("A" * 64, "gate_a", looks)
    with pytest.raises(ValueError):        # non-hex
        stage1.bootstrap_seed("z" * 64, "gate_a", looks)
    with pytest.raises(ValueError):        # empty gate id
        stage1.bootstrap_seed("a" * 64, "", looks)


def test_canonical_cell_look_vector():
    # sorted by cell_id regardless of input order
    vec = stage1.canonical_cell_look_vector(
        {"math_code": 500, "code_atomic": 100})
    assert vec == "code_atomic:100,math_code:500"
    # fork uses the fork schedule
    assert stage1.canonical_cell_look_vector({"fork_join": 200}) == \
        "fork_join:200"
    with pytest.raises(ValueError):        # unknown cell
        stage1.canonical_cell_look_vector({"bogus_cell": 100})
    with pytest.raises(ValueError):        # look off the ordinary schedule
        stage1.canonical_cell_look_vector({"code_atomic": 200})
    with pytest.raises(ValueError):        # fork look off the fork schedule
        stage1.canonical_cell_look_vector({"fork_join": 300})
    with pytest.raises(ValueError):        # empty
        stage1.canonical_cell_look_vector({})


def test_stage2_population_constants():
    assert stage1.TRAIN_CLUSTERS_PER_CELL == 100
    assert list(stage1.DEV_SELECT_CLUSTERS) == list(range(24))
    assert list(stage1.PILOT_GATE_CLUSTERS) == list(range(24, 36))
    assert not (set(stage1.DEV_SELECT_CLUSTERS)
                & set(stage1.PILOT_GATE_CLUSTERS))
    # 132_s §11.1 arithmetic at C=6 and C=5
    for c, test_obs, updates in ((6, 1_008, 300), (5, 1_005, 250)):
        per_cell = -(-stage1.TEST_TOTAL_TARGET // (3 * c))  # ceil
        assert per_cell * 3 * c == test_obs
        groups = stage1.TRAIN_CLUSTERS_PER_CELL * c
        assert -(-groups // stage1.GROUPS_PER_UPDATE) == updates


# --- 134_s finding 1: per-edge intervention cross-product --------------------

def test_intervention_edge_diagnostic_cross_product():
    for cell, edges in stage1.CELL_INTERVENTION_EDGES.items():
        names = stage1.intervention_gate_names(cell)
        # exact cardinality: |edges| x |diagnostics|, no pooling
        assert len(names) == len(edges) * len(
            stage1.INTERVENTION_DIAGNOSTICS), cell
        assert len(set(names)) == len(names), cell
        for (src, dst) in edges:
            for diag in stage1.INTERVENTION_DIAGNOSTICS:
                assert f"{diag}_{src}_{dst}" in names, (cell, diag, src, dst)
        # every intervention gate is mandatory for its cell
        for name in names:
            assert name in stage1.GATE_MATRIX[cell]["mandatory"], (cell,
                                                                   name)


def test_fork_has_both_edges_and_chains_one():
    assert stage1.CELL_INTERVENTION_EDGES["fork_join"] == (
        ("n1", "n3"), ("n2", "n3"))
    assert len(stage1.intervention_gate_names("fork_join")) == 6
    for cell in ("lookup_math", "math_code"):
        assert stage1.CELL_INTERVENTION_EDGES[cell] == (("n1", "n2"),)
        assert len(stage1.intervention_gate_names(cell)) == 3
    for cell in ("lookup_atomic", "math_atomic", "code_atomic"):
        assert stage1.intervention_gate_names(cell) == ()


def test_intervention_edges_exist_in_generated_programs():
    for cell, edges in stage1.CELL_INTERVENTION_EDGES.items():
        if not edges:
            continue
        r = generate_latent(cell, "worker_dev", 0, DEFAULT_PROFILE)
        node_ids = {n["id"] for n in r.latent["reference_program"]["nodes"]}
        for (src, dst) in edges:
            assert {src, dst} <= node_ids, (cell, src, dst)


# --- 134_s finding 2: protocol-denominator contract ---------------------------

def _op_family(op: str) -> str:
    if op == "lookup":
        return "lookup"
    if op.startswith("seq_"):
        return "code"
    return "math"


@pytest.mark.parametrize("cell", CELLS)
def test_node_families_match_generated_programs(cell):
    # NODE_FAMILIES is acceptance-tested against generation across several
    # latents so template/factor variation is covered, not hand-trusted.
    for index in (0, 1, 2, 7, 13):
        r = generate_latent(cell, "worker_dev", index % 30, DEFAULT_PROFILE)
        nodes = r.latent["reference_program"]["nodes"]
        derived = {n["id"]: _op_family(n["op"]) for n in nodes}
        assert derived == stage1.NODE_FAMILIES[cell], (cell, index, derived)


def test_worker_families_frozen():
    assert stage1.WORKER_FAMILIES == {0: "lookup", 1: "math", 2: "code",
                                      3: "code"}


def test_on_contract_nodes_all_cells_all_workers():
    expected = {
        ("lookup_atomic", 0): ("n1",), ("lookup_atomic", 1): (),
        ("lookup_atomic", 2): (), ("lookup_atomic", 3): (),
        ("math_atomic", 0): (), ("math_atomic", 1): ("n1",),
        ("math_atomic", 2): (), ("math_atomic", 3): (),
        ("code_atomic", 0): (), ("code_atomic", 1): (),
        ("code_atomic", 2): ("n1",), ("code_atomic", 3): ("n1",),
        ("lookup_math", 0): ("n1",), ("lookup_math", 1): ("n2",),
        ("lookup_math", 2): (), ("lookup_math", 3): (),
        ("math_code", 0): (), ("math_code", 1): ("n1",),
        ("math_code", 2): ("n2",), ("math_code", 3): ("n2",),
        ("fork_join", 0): ("n1",), ("fork_join", 1): ("n3",),
        ("fork_join", 2): ("n2",), ("fork_join", 3): ("n2",),
    }
    for (cell, worker), nodes in expected.items():
        assert stage1.on_contract_nodes(cell, worker) == nodes, (cell,
                                                                 worker)


def test_truncation_row_counts():
    # exactly 3 x on-contract nodes per latent, per (cell, worker)
    for cell in CELLS:
        for worker in (0, 1, 2, 3):
            n = len(stage1.on_contract_nodes(cell, worker))
            assert stage1.truncation_rows_per_latent(cell, worker) == 3 * n


def test_selected_route_row_counts():
    # exactly 3 x S per latent for the cell overall
    expected_s = {"lookup_atomic": 1, "math_atomic": 1, "code_atomic": 1,
                  "lookup_math": 2, "math_code": 2, "fork_join": 3}
    for cell, s in expected_s.items():
        assert stage1.selected_route_rows_per_latent(cell) == 3 * s


def test_selected_route_rows_per_worker():
    # the CE0 reference deployable route for fork: lookup, code(w2), math
    counts = stage1.selected_route_rows_per_worker(
        "fork_join", {"n1": 0, "n2": 2, "n3": 1})
    assert counts == {0: 3, 2: 3, 1: 3}
    # a worker selected at both math_code nodes accumulates both
    counts = stage1.selected_route_rows_per_worker(
        "math_code", {"n1": 3, "n2": 3})
    assert counts == {3: 6}
    with pytest.raises(ValueError):    # missing node
        stage1.selected_route_rows_per_worker("math_code", {"n1": 1})
    with pytest.raises(ValueError):    # foreign node
        stage1.selected_route_rows_per_worker(
            "math_code", {"n1": 1, "n2": 2, "n3": 0})
    with pytest.raises(ValueError):    # unknown worker id
        stage1.selected_route_rows_per_worker(
            "math_code", {"n1": 1, "n2": 9})


# --- 134_s finding 3: frozen prompt candidates and no-repair ------------------

def test_prompt_fewshot_matches_stage0_policy_freeze():
    text = stage1.prompt_fewshot()
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == \
        stage1.PROMPT_FEWSHOT_SHA256
    # the pinned digest IS the Stage-0 policy-freeze prompt identity
    assert stage1.PROMPT_FEWSHOT_SHA256.startswith("fe9bba0d")
    assert "Example 1:" in text


def test_prompt_schema_only_derivation():
    fewshot = stage1.prompt_fewshot()
    schema_only = stage1.prompt_schema_only()
    assert hashlib.sha256(schema_only.encode("utf-8")).hexdigest() == \
        stage1.PROMPT_SCHEMA_ONLY_SHA256
    # identical instructions and output contract: a strict prefix of the
    # few-shot bytes, ending at the contract line, with no demonstrations
    assert fewshot.startswith(schema_only)
    assert schema_only.endswith("nothing else.")
    assert "Example" not in schema_only
    assert '{"worker_ids": [...]}' in schema_only
    # no replacement task examples were added
    assert len(schema_only) < len(fewshot)


def test_format_repair_frozen_as_no_repair():
    # 132_s §10.1: "if none is frozen, no repair is allowed."
    assert stage1.FORMAT_REPAIR_V1 is None
    # cohort B stays registered (never reassigned) even though unused
    assert list(POLICY_DEV_COHORTS["format_b"]) == list(range(24, 48))


# --- 134_s lower-severity items -----------------------------------------------

def test_policy_dev_cohort_rejects_bool_and_float():
    with pytest.raises(LoadError):
        policy_dev_cohort(True)
    with pytest.raises(LoadError):
        policy_dev_cohort(1.0)
    with pytest.raises(LoadError):
        policy_dev_cohort("0")


def test_infra_retry_dictionary_pinned_exactly():
    assert stage1.INFRA_RETRY_CODES == {
        "E_INFRA_CUDA_OOM": {"max_attempts": 3,
                             "backoff_seconds": (10, 60)},
        "E_INFRA_IO": {"max_attempts": 3, "backoff_seconds": (10, 60)},
        "E_INFRA_INCOMPLETE_CALL": {"max_attempts": 2,
                                    "backoff_seconds": (10,)},
    }


def test_gate_thresholds_pinned_exactly():
    assert stage1.GATE_THRESHOLDS == {
        "untyped_infrastructure_failures_max": 0.0,
        "truncation_ucb_max": 0.02,
        "selected_route_syntax_ucb_max": 0.02,
        "atomic_family_accuracy_min": 0.75,
        "atomic_family_margin_lcb_min": 0.20,
        "two_step_deployable_min": 0.65,
        "deployable_vs_one_call_lcb_min": 0.20,
        "corruption_drop_lcb_min": 0.20,
        "counterfactual_equivalence_band": 0.10,
        "old_answer_persistence_ucb_max": 0.10,
        "family_stake_point_min": 0.10,
        "model_stake_point_min": 0.10,
        "reference_vs_generic_min": 0.10,
        "fork_leaf_capability_min": 0.80,
        "fork_deployable_min": 0.60,
        "fork_vs_two_call_shortcut_min": 0.15,
        "fork_branch_corruption_lcb_min": 0.20,
    }


def test_shallow_router_encoder_frozen():
    from tasks.conductor.baselines import OBSERVABLE_SUBTYPES
    assert stage1.SHALLOW_ROUTER_CELL_LEVELS == tuple(sorted(CELLS))
    assert stage1.SHALLOW_ROUTER_NODE_LEVELS == ("n1", "n2", "n3")
    levels = stage1.shallow_router_subtype_levels()
    # bound to the baselines §1.11 contract: complete, ordered, namespaced
    expected = tuple(f"{cell}:{lvl}"
                     for cell in stage1.SHALLOW_ROUTER_CELL_LEVELS
                     for lvl in OBSERVABLE_SUBTYPES[cell])
    assert levels == expected
    assert len(levels) == len(set(levels))
    # numeric tail matches the frozen baselines order
    assert stage1.SHALLOW_ROUTER_FEATURES[3:] == ("p", "q", "t", "k", "i")


def test_successor_digest_floor_includes_contract():
    from tasks.conductor.grpo_smoke import SOURCE_DIGEST_FILES
    assert "tasks/conductor/contract.py" in \
        stage1.SUCCESSOR_DIGEST_REQUIRED_ADDITIONS
    # additions are genuinely additional to the historical eight
    assert not (set(stage1.SUCCESSOR_DIGEST_REQUIRED_ADDITIONS)
                & set(SOURCE_DIGEST_FILES))


def test_cold_start_constants():
    assert stage1.POLICY_GROUP_SIZE == 8
    assert stage1.COLD_START_GROUPS_PER_TOPOLOGY == 72
    assert stage1.COLD_START_GROUPS_PER_DIRECTION == 72
    g = stage1.COLD_START_GENERAL_GATES
    assert g["schema_validity_min"] == pytest.approx(0.80)
    assert g["non_zero_variance_groups_min"] == pytest.approx(0.25)
    assert g["groups_with_win_and_lower_min"] == pytest.approx(0.10)
    assert stage1.DIRECT_MODEL_GRADIENT_GROUPS_MIN == pytest.approx(0.10)
    # >=64-group prerequisite from 127_f item 3 is satisfied by 72
    assert stage1.COLD_START_GROUPS_PER_TOPOLOGY >= 64
