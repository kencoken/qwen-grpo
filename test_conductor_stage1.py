"""Unit-1 acceptance tests — 132_s (approved 133_f).

Covers the D4 cohort erratum (range/cap rejection AND exact joint factorial
balance over indices 30-129), the policy_dev registration, and the
fail-closed identity checks that pin tasks/conductor/stage1.py to the
artifacts it names (SYSTEM_DIRECT bytes, DEFAULT_PROFILE digest, the
cascade trigger set, look schedules).
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
    s1 = stage1.bootstrap_seed("m" * 64, "gate_a", "code_atomic:300")
    s2 = stage1.bootstrap_seed("m" * 64, "gate_a", "code_atomic:300")
    s3 = stage1.bootstrap_seed("m" * 64, "gate_b", "code_atomic:300")
    s4 = stage1.bootstrap_seed("n" * 64, "gate_a", "code_atomic:300")
    assert s1 == s2
    assert len({s1, s3, s4}) == 3
    assert 0 <= s1 < 2 ** 64


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
