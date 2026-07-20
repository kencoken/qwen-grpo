"""0A battery: types, canonical integers, payload text, profiles (§1.1,
§1.2, §1.14, §4 invalid-profile fixtures)."""

import copy

import pytest

from tasks.conductor import profiles, types
from tasks.conductor.profiles import DEFAULT_PROFILE, ProfileError
from tasks.conductor.types import (
    IntegerList, IntegerRecord, InfrastructureError, WorkerResult,
)


# --- §1.1 canonical wire form ----------------------------------------------

@pytest.mark.parametrize("text,code", [
    ("0", None), ("5", None), ("-7", None), ("1000", None),
    ("0012", "E_NONCANONICAL_INT"), ("-07", "E_NONCANONICAL_INT"),
    ("+5", "E_PARSE"), ("5.0", "E_PARSE"), ("1,000", "E_PARSE"),
    ("1 000", "E_PARSE"), ("", "E_PARSE"), ("-0", "E_PARSE"),
])
def test_canonical_integer_classification(text, code):
    assert types.classify_integer_text(text) == code


# --- §1.2 resources and frozen payload text ---------------------------------

def test_keyed_payload_text_frozen_bytes():
    rec = IntegerRecord(layout="keyed", payload=(
        ("Aster", (("crates", 31),)), ("Cedar", (("crates", 17),))))
    assert rec.payload_text("R-7K2") == "R-7K2:\nAster.crates = 31\nCedar.crates = 17"


def test_operands_payload_text_frozen_bytes():
    # §1.2 shows the a/b prefix of this record; the frozen line form is
    # `{name} = {value}` per operand in stored order.
    rec = IntegerRecord(layout="operands",
                        payload=(("a", 83719), ("b", 43), ("c", 1), ("d", 6)))
    assert rec.payload_text("R-2P6") == \
        "R-2P6:\na = 83719\nb = 43\nc = 1\nd = 6"


def test_list_payload_text_frozen_bytes():
    lst = IntegerList(payload=(41, 7, 83))
    assert lst.payload_text("R-9V4") == "R-9V4:\n[41, 7, 83]"


def test_keyed_values_pairwise_distinct_d3():
    with pytest.raises(ValueError):
        IntegerRecord(layout="keyed", payload=(
            ("Aster", (("crates", 31),)), ("Cedar", (("crates", 31),))))


@pytest.mark.parametrize("payload,why", [
    ((("Aster", (("crates", 31),)), ("Aster", (("crates", 17),))),
     "duplicate entity makes lookup first-match dependent"),
    ((("Aster", (("crates", 31), ("crates", 17))),),
     "duplicate field name"),
    ((("Aster", (("crates", 31),)), ("Cedar", (("units", 17),))),
     "ragged grid: entities disagree about the field schema"),
    ((("Aster", (("crates", 31),)), ("Cedar", ())),
     "entity with no fields"),
    ((), "empty record"),
])
def test_keyed_record_requires_an_ordered_rectangular_grid(payload, why):
    with pytest.raises(ValueError):
        IntegerRecord(layout="keyed", payload=payload)


@pytest.mark.parametrize("registry_json,match", [
    ({"R-1A1": None}, "must be an object"),
    ({"R-1A1": {}}, "malformed resource"),
    ({"R-1A1": {"kind": "integer_list"}}, "malformed resource"),
    ({"R-1A1": {"kind": "bogus", "payload": []}}, "malformed resource"),
    ({"R-1A1": {"kind": "integer_record", "payload": []}},
     "malformed resource"),
])
def test_registry_translates_malformed_resources(registry_json, match):
    """A null or incomplete resource object must name the handle at fault
    rather than leaking a raw AttributeError/KeyError."""
    from tasks.conductor.resources import InstanceRegistry
    from tasks.conductor.types import InfrastructureError as IE
    with pytest.raises(IE, match=match):
        InstanceRegistry(["R-1A1"], registry_json)


@pytest.mark.parametrize("manifest", [
    [["R-1A1"]],            # unhashable element: set() would raise TypeError
    [None],
    [7],
    "R-1A1",
])
def test_registry_validates_manifest_element_types(manifest):
    from tasks.conductor.resources import InstanceRegistry
    from tasks.conductor.types import InfrastructureError as IE
    with pytest.raises(IE):
        InstanceRegistry(manifest, {})


def test_registry_rejects_a_manifest_repeating_a_handle():
    from tasks.conductor.resources import InstanceRegistry
    from tasks.conductor.types import InfrastructureError as IE
    record = IntegerRecord(layout="keyed",
                           payload=(("Aster", (("crates", 31),)),)).to_json()
    with pytest.raises(IE, match="duplicate handles"):
        InstanceRegistry(["R-1A1", "R-1A1"], {"R-1A1": record})
    registry = InstanceRegistry(["R-1A1"], {"R-1A1": record})
    assert len(registry.union_payload_texts()) == 1


def test_operand_names_d9():
    IntegerRecord(layout="operands",
                  payload=(("a", 1), ("b", 2), ("c", 3), ("m", 4)))
    with pytest.raises(ValueError):
        IntegerRecord(layout="operands", payload=(("x", 1), ("y", 2)))
    with pytest.raises(ValueError):
        IntegerRecord(layout="operands",
                      payload=(("a", 1), ("c", 2), ("b", 3)))


def test_resource_json_round_trip():
    rec = IntegerRecord(layout="keyed", payload=(
        ("Aster", (("crates", 31),)),))
    assert types.resource_from_json(rec.to_json()) == rec
    lst = IntegerList(payload=(1, 2, 3))
    assert types.resource_from_json(lst.to_json()) == lst


def test_handle_shape_n1():
    assert types.is_handle("R-7K2")
    for bad in ("R-7k2", "Q-7K2", "R-77K", "R-7K22", "R7K2"):
        assert not types.is_handle(bad)


# --- §1.7 WorkerResult invariants -------------------------------------------

@pytest.mark.parametrize("args,why", [
    (("success", None, None, True, True, False), "success needs a value"),
    (("typed_failure", None, None, False, False, False), "code required"),
    (("typed_failure", None, "E_BOGUS", False, False, False), "unknown code"),
    (("dependency_blocked", None, None, True, False, False), "flags false"),
    (("success", 5, None, True, True, True), "synthetic never executes"),
    (("bogus_status", None, None, False, False, False), "unknown status"),
    (("success", True, None, True, True, False), "bool is not an int value"),
    (("success", 5, None, False, True, False), "tool needs valid artifact"),
    (("success", 5, None, False, False, False), "endpoint success flags"),
    (("typed_failure", None, "E_PARSE", True, True, False), "syntax flags"),
    (("typed_failure", None, "E_UNKNOWN_KEY", False, False, False),
     "semantic flags"),
    (("success", 5, None, 1, True, False), "flags must be bools"),
])
def test_worker_result_invariants(args, why):
    with pytest.raises(InfrastructureError):
        WorkerResult(*args)


def test_worker_result_bool_value_cannot_score_as_gold_one():
    """True == 1 in Python, so an unguarded bool value would be scored
    correct against gold answer 1."""
    with pytest.raises(InfrastructureError):
        WorkerResult("success", True, None, True, True, False)


@pytest.mark.parametrize("args", [
    ("success", 42, None, True, True, False),
    ("typed_failure", None, "E_PARSE", False, False, False),
    ("typed_failure", None, "E_UNKNOWN_KEY", True, True, False),
    ("dependency_blocked", None, None, False, False, False),
    ("success", 0, None, False, False, True),
    ("typed_failure", None, "E_PARSE", False, False, True),
])
def test_worker_result_legal_truth_table_rows(args):
    assert WorkerResult(*args).status == args[0]


def test_rejection_code_partition():
    assert types.SYNTAX_REJECTION_CODES | types.SEMANTIC_REJECTION_CODES \
        == types.REJECTION_CODES
    assert not types.SYNTAX_REJECTION_CODES & types.SEMANTIC_REJECTION_CODES


# --- §1.14 profile validation ----------------------------------------------

def test_default_profile_valid():
    profiles.validate_profile(DEFAULT_PROFILE)


def _mutated(path, value):
    profile = copy.deepcopy(DEFAULT_PROFILE)
    node = profile["cells"]
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = value
    return profile


# §4 invalid-profile fixtures: every §1.14 profile-domain rule violated once.
@pytest.mark.parametrize("path,value", [
    (("lookup_atomic", "N_band"), [2, 16]),          # N < 3
    (("lookup_atomic", "N_band"), [3, 21]),          # N > 20
    (("lookup_atomic", "value_band"), [10, 50]),     # undersized cardinality
    (("math_atomic", "b_band"), [9, 99]),            # b < 10
    (("math_atomic", "c_band"), [0, 20]),            # c < 1
    (("math_atomic", "t1", "d_band"), [1, 12]),      # d < 2
    (("math_atomic", "t2", "m_band"), [1, 60]),      # m < 2
    (("lookup_math", "p_band"), [1, 9]),             # p < 2
    (("lookup_math", "q_band"), [0, 20]),            # q < 1
    (("code_atomic", "L_band"), [4, 16]),            # L < 5 dedup
    (("code_atomic", "t_band"), [-1, 8]),            # negative public literal
    (("code_atomic", "value_band"), [0, 9]),         # select terminal 0
    (("math_code", "list_value_band"), [0, 99]),     # gold >= 1 violated
    (("math_code", "list_value_band"), [1, 10]),     # < max L cardinality
    (("math_code", "L_band"), [1, 1]),               # L < 2
    (("lookup_math", "N_band"), [16, 3]),            # min > max
    (("lookup_atomic", "F_band"), [0, 5]),           # F_band.min = 0
    (("code_atomic", "k_band"), [1, 10**13]),        # 13-digit public literal
    (("fork_join", "q_band"), [0, 20]),              # fork q < 1
    (("fork_join", "count", "L_band"), [3, 16]),     # fork dedup L < 5
    (("fork_join", "derived_from"), {}),             # missing annotation
    (("math_atomic", "a_band"), [1, 2**63]),         # not int64-representable
    # Workload ceilings: representable but computationally impossible.
    (("code_atomic", "L_band"), [5, 10**12]),        # unbounded list alloc
    (("math_code", "L_band"), [8, 10**9]),           # unbounded list alloc
    (("lookup_math", "value_band"), [1, 10**9]),     # enumerated support
    (("math_atomic", "c_band"), [1, 10**9]),         # T1 feasible-c scan
    (("fork_join", "count", "L_band"), [5, 10**9]),
])
def test_invalid_profile_rejected_at_load(path, value):
    with pytest.raises(ProfileError):
        profiles.validate_profile(_mutated(path, value))


def test_s_minus_support_rule():
    # |S⁻(p_min, q_max)| < 2: value_band {1..3}, p=2, q=5 -> S⁻ = {3}.
    profile = _mutated(("lookup_math", "value_band"), [1, 3])
    profile["cells"]["lookup_math"]["p_band"] = [2, 2]
    profile["cells"]["lookup_math"]["q_band"] = [5, 5]
    profile["cells"]["lookup_math"]["N_band"] = [3, 3]
    profile["cells"]["lookup_math"]["F_band"] = [1, 1]
    with pytest.raises(ProfileError) as err:
        profiles.validate_profile(profile)
    assert "S⁻" in str(err.value)


def test_derived_index_bound_uses_distinct_value_count_not_list_length():
    """U is the number of *distinct* values, so it is capped by the value
    band's cardinality as well as by L."""
    profile = _mutated(("code_atomic", "L_band"), [5, 200])
    profile["cells"]["code_atomic"]["value_band"] = [1, 9]
    profiles.validate_profile(profile)  # U <= 9: index literal stays small


def test_missing_cell_field_rejected():
    profile = copy.deepcopy(DEFAULT_PROFILE)
    del profile["cells"]["math_atomic"]["b_band"]
    with pytest.raises(ProfileError):
        profiles.validate_profile(profile)


def test_profile_version_shape_and_stability():
    v = profiles.profile_version(DEFAULT_PROFILE)
    assert v.startswith("dp-") and len(v) == 19
    assert v == profiles.profile_version(copy.deepcopy(DEFAULT_PROFILE))


def test_canonical_json_rejects_floats_and_bools():
    for bad in ({"a": 1.5}, {"a": True}, {"a": None}):
        with pytest.raises(ProfileError):
            profiles.canonical_json(bad)
