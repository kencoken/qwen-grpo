"""0A battery: golden §3 fixtures, seed/ID fixture, IR validation,
scheduler, metamorphic, provenance no-leakage, split isolation, collision,
sampler/R_MAGNITUDE fixtures (§4)."""

import copy
import time

import numpy as np
import pytest

from tasks.conductor import program, profiles, render, types
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.program import (
    GenerationError, LoadError, RMagnitude, evaluate_reference,
    generate_latent, validate_reference_program,
)
from tasks.conductor.types import (
    InfrastructureError, IntegerList, IntegerRecord,
)

PROF = DEFAULT_PROFILE


def keyed(*entries):
    return IntegerRecord(layout="keyed", payload=tuple(
        (name, tuple(fields.items())) for name, fields in entries))


def operands(**kv):
    return IntegerRecord(layout="operands", payload=tuple(kv.items()))


# --- §3 golden fixtures (machine-verified worked examples) ------------------

def test_lookup_atomic_worked_examples():
    reg = {"R-7K2": keyed(("Aster", {"crates": 31}), ("Cedar", {"crates": 17}),
                          ("Grove", {"crates": 39}), ("Ivory", {"crates": 53}))}
    prog = {"nodes": [{"id": "n1", "op": "lookup",
                       "args": {"handle": {"res": "R-7K2"},
                                "key": {"lit": "Grove"},
                                "field": {"lit": "crates"}}}],
            "positions": ["n1"], "sink": "n1"}
    validate_reference_program(prog, ["R-7K2"], reg)
    assert evaluate_reference(prog, reg)["n1"] == 39

    reg_b = {"R-4H8": keyed(("Lark", {"units": 99}), ("Onyx", {"units": 10}),
                            ("Pine", {"units": 11}), ("Quill", {"units": 98}))}
    prog_b = {"nodes": [{"id": "n1", "op": "lookup",
                         "args": {"handle": {"res": "R-4H8"},
                                  "key": {"lit": "Quill"},
                                  "field": {"lit": "units"}}}],
              "positions": ["n1"], "sink": "n1"}
    assert evaluate_reference(prog_b, reg_b)["n1"] == 98


def test_math_atomic_worked_examples():
    cases = [
        ("ratio", dict(a=83719, b=43, c=1, d=6), 599986),
        ("modular", dict(a=999983, b=89, c=19, m=12), 2),
        ("mul_add", dict(a=524287, b=83, c=17), 43515838),
        ("ratio", dict(a=10007, b=10, c=2, d=6), 16678),
    ]
    for op, kv, gold in cases:
        reg = {"R-1A1": operands(**kv)}
        prog = {"nodes": [{"id": "n1", "op": op,
                           "args": {n: {"operand": {"res": "R-1A1", "name": n}}
                                    for n in kv}}],
                "positions": ["n1"], "sink": "n1"}
        validate_reference_program(prog, ["R-1A1"], reg)
        assert evaluate_reference(prog, reg)["n1"] == gold, (op, kv)


def test_math_atomic_t2_modular_check_compliance():
    # §3.2 O (T2): relevance 7/0/6 ≠ 2; exclusions 11 ≠ 2, 0 ≠ 2.
    a, b, c, m, g = 999983, 89, 19, 12, 2
    assert (a * b) % m == 7 and (b + c) % m == 0 and (a + c) % m == 6
    assert (a + b + c) % m == 11 and (a * b - c) % m == 0
    for v in [(a * b) % m, (b + c) % m, (a + c) % m,
              (a + b + c) % m, (a * b - c) % m]:
        assert v != g


def test_code_atomic_worked_examples():
    o_count = [6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]
    assert program.prim_seq_count(o_count, 5) == 4
    assert len(program.stable_unique(o_count)) == 8
    assert program.count_gt(o_count, 5) == 6          # dedup ablation 6 != 4

    o_select = [5, 3, 5, 8, 1, 3, 9, 2]
    unique = program.stable_unique(o_select)
    assert len(unique) == 6
    assert program.rotate_left(unique, 2) == [8, 1, 9, 2, 5, 3]
    assert program.prim_seq_select(o_select, 2, 4) == 5
    assert program.at(program.rotate_left(o_select, 2), 4) == 9  # ablation
    assert program.at(unique, 4) == 9                            # ablation

    b_count = [9, 8, 9, 7, 6, 8, 5, 9]
    assert len(program.stable_unique(b_count)) == 5
    assert program.prim_seq_count(b_count, 5) == 4    # answer = U - 1
    assert program.count_gt(b_count, 5) == 7          # ablation 7 != 4


def _lookup_math_prog(handle, key, field, p, sign, q):
    return {"nodes": [
        {"id": "n1", "op": "lookup",
         "args": {"handle": {"res": handle}, "key": {"lit": key},
                  "field": {"lit": field}}},
        {"id": "n2", "op": "affine",
         "args": {"x": {"node": "n1"}, "p": {"lit": p},
                  "sign": {"lit": sign}, "q": {"lit": q}}}],
        "positions": ["n1", "n2"], "sink": "n2"}


def test_lookup_math_worked_examples():
    reg = {"R-3T5": keyed(("Aster", {"units": 31}), ("Cedar", {"units": 17}),
                          ("Grove", {"units": 39}), ("Ivory", {"units": 53}))}
    prog = _lookup_math_prog("R-3T5", "Cedar", "units", 3, "-", 4)
    values = evaluate_reference(prog, reg)
    assert values == {"n1": 17, "n2": 47}
    # §3.4 intervention example: n1' = 19 -> run 53 (corruption wrong),
    # counterfactual target 53.
    mutated = evaluate_reference(prog, reg, overrides={"n1": 19})
    assert mutated["n2"] == 53 != 47

    reg_b = {"R-2W9": keyed(("Vale", {"units": 99}), ("Aster", {"units": 10}),
                            ("Hazel", {"units": 23}), ("Tarn", {"units": 57}))}
    prog_b = _lookup_math_prog("R-2W9", "Vale", "units", 9, "-", 20)
    assert evaluate_reference(prog_b, reg_b)["n2"] == 871


def _math_code_prog(h1, h2):
    return {"nodes": [
        {"id": "n1", "op": "modular",
         "args": {n: {"operand": {"res": h1, "name": n}}
                  for n in ("a", "b", "c", "m")}},
        {"id": "n2", "op": "seq_at",
         "args": {"xs": {"res": h2}, "i": {"node": "n1"}}}],
        "positions": ["n1", "n2"], "sink": "n2"}


def test_math_code_worked_examples():
    reg = {"R-6D1": operands(a=314159265, b=55, c=17, m=12),
           "R-9V4": IntegerList(payload=(41, 7, 83, 22, 65, 14, 39, 90, 56,
                                         11, 72, 28))}
    prog = _math_code_prog("R-6D1", "R-9V4")
    values = evaluate_reference(prog, reg)
    assert values == {"n1": 8, "n2": 56}
    mutated = evaluate_reference(prog, reg, overrides={"n1": 3})
    assert mutated["n2"] == 22  # §3.5 intervention example

    reg_b = {"R-3F7": operands(a=123456789, b=45, c=6, m=8),
             "R-6M2": IntegerList(payload=(17, 64, 80, 23, 46, 91, 12, 58))}
    values_b = evaluate_reference(_math_code_prog("R-3F7", "R-6M2"), reg_b)
    assert values_b == {"n1": 7, "n2": 58}  # index = m − 1


def _fork_prog(h1, h2, key, field, t, q, positions):
    return {"nodes": [
        {"id": "n1", "op": "lookup",
         "args": {"handle": {"res": h1}, "key": {"lit": key},
                  "field": {"lit": field}}},
        {"id": "n2", "op": "seq_count",
         "args": {"xs": {"res": h2}, "t": {"lit": t}}},
        {"id": "n3", "op": "product_affine",
         "args": {"x": {"node": "n1"}, "y": {"node": "n2"},
                  "q": {"lit": q}}}],
        "positions": positions, "sink": "n3"}


def test_fork_join_worked_examples():
    reg = {"R-5A8": keyed(("Aster", {"units": 31}), ("Cedar", {"units": 14}),
                          ("Grove", {"units": 39})),
           "R-1J7": IntegerList(payload=(6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4))}
    for positions in (["n1", "n2", "n3"], ["n2", "n1", "n3"]):  # O and O′
        prog = _fork_prog("R-5A8", "R-1J7", "Cedar", "units", 5, 3, positions)
        validate_reference_program(prog, ["R-5A8", "R-1J7"], reg)
        values = evaluate_reference(prog, reg)
        assert values == {"n1": 14, "n2": 4, "n3": 59}
        assert evaluate_reference(prog, reg, overrides={"n1": 15})["n3"] == 63
        assert evaluate_reference(prog, reg, overrides={"n2": 3})["n3"] == 45

    reg_b = {"R-8D4": keyed(("Wren", {"crates": 99}), ("Slate", {"crates": 10}),
                            ("Fern", {"crates": 57})),
             "R-2K9": IntegerList(payload=(4, 2, 4, 3, 1, 2, 3, 4))}
    prog_b = _fork_prog("R-8D4", "R-2K9", "Wren", "crates", 3, 20,
                        ["n1", "n2", "n3"])
    values_b = evaluate_reference(prog_b, reg_b)
    assert values_b == {"n1": 99, "n2": 1, "n3": 119}
    assert evaluate_reference(prog_b, reg_b, overrides={"n1": 98})["n3"] == 118
    assert evaluate_reference(prog_b, reg_b, overrides={"n2": 2})["n3"] == 218


# --- §4 golden seed/ID fixture (pins the full §1.13 derivation) -------------

def test_golden_identity_fixture():
    dpv = profiles.profile_version(PROF)
    assert dpv == "dp-2bcb6373340a8a79"
    sm = program.seed_material(program.GENERATOR_VERSION, dpv,
                               "qualification", "lookup_math", 42)
    assert sm.encode() == (b"qwen-grpo-conductor\x1fspecs-v0.8+0a0\x1f"
                           b"dp-2bcb6373340a8a79\x1fqualification\x1f"
                           b"lookup_math\x1f42")
    assert program.h64(sm) == 8736009181577540778
    assert program.hex8(sm) == "793c8a10"
    lp_id = program.latent_program_id("lookup_math", "qualification", 42, sm)
    assert lp_id == "lookup_math:qualification:00042:793c8a10"
    assert program.render_instance_id(lp_id, "goal_first", "private") == \
        "lookup_math:qualification:00042:793c8a10:goal_first:private"
    # Block-seed/assignment pair for the same index.
    assert program.factor_assignment(program.GENERATOR_VERSION, dpv,
                                     "qualification", "lookup_math", 42) == \
        {"sign": "plus", "target_stratum": "last"}
    # Intervention seed + drawn replacement for one edge.
    assert program.intervention_seed(lp_id, "n1", "n2") == \
        9184936153647782786
    latent = generate_latent("lookup_math", "qualification", 42, PROF).latent
    iv = program.draw_intervention(latent, "n1", "n2", PROF)
    assert iv["replacement"] == 22
    assert iv["corruption_target"] == latent["gold_answer"] == 217
    assert iv["counterfactual_target"] == 117


# --- §1.3 IR validation tests (every rule violated once) --------------------

def _valid_lm():
    reg = {"R-3T5": keyed(("Aster", {"units": 31}), ("Cedar", {"units": 17}),
                          ("Grove", {"units": 39}))}
    return _lookup_math_prog("R-3T5", "Cedar", "units", 3, "-", 4), \
        ["R-3T5"], reg


@pytest.mark.parametrize("mutate", [
    lambda p: p["nodes"].append(dict(p["nodes"][0])),          # dup node id
    lambda p: p["positions"].remove("n1"),                      # missing pos
    lambda p: p["positions"].append("n2"),                      # dup pos
    lambda p: p.update(sink="n1"),                              # sink rule
    lambda p: p.update(positions=["n2", "n1"]),                 # topological
    lambda p: p["nodes"][1].update(op="frobnicate"),            # unknown op
    lambda p: p["nodes"][1]["args"].update(extra={"lit": 1}),   # extra arg
    lambda p: p["nodes"][1]["args"].pop("q"),                   # missing arg
    lambda p: p["nodes"][1]["args"].update(x={"lit": 5}),       # wrong kind
    lambda p: p["nodes"][1]["args"].update(p={"lit": "3"}),     # str-typed int
    lambda p: p["nodes"][1]["args"].update(sign={"lit": "±"}),  # bad sign
    lambda p: p["nodes"][1]["args"].update(
        x={"node": "n9"}),                                      # undeclared
    lambda p: p["nodes"][0]["args"].update(
        handle={"res": "R-9Z9"}),                               # unknown handle
])
def test_ir_validation_rules(mutate):
    prog, manifest, reg = _valid_lm()
    mutate(prog)
    with pytest.raises(LoadError):
        validate_reference_program(prog, manifest, reg)


def test_ir_operand_rules():
    reg = {"R-1A1": operands(a=5, b=11, c=2, d=3),
           "R-2B2": operands(a=7, b=13, c=1, d=2)}
    prog = {"nodes": [{"id": "n1", "op": "ratio",
                       "args": {n: {"operand": {"res": "R-1A1", "name": n}}
                                for n in ("a", "b", "c", "d")}}],
            "positions": ["n1"], "sink": "n1"}
    validate_reference_program(prog, ["R-1A1", "R-2B2"], reg)
    # Operand-name/slot mismatch (§1.3 frozen matching rule).
    bad = copy.deepcopy(prog)
    bad["nodes"][0]["args"]["a"] = {"operand": {"res": "R-1A1", "name": "b"}}
    with pytest.raises(LoadError):
        validate_reference_program(bad, ["R-1A1", "R-2B2"], reg)
    # Cross-record operand references.
    bad = copy.deepcopy(prog)
    bad["nodes"][0]["args"]["a"] = {"operand": {"res": "R-2B2", "name": "a"}}
    with pytest.raises(LoadError):
        validate_reference_program(bad, ["R-1A1", "R-2B2"], reg)
    # Wrong layout for a res slot.
    seq = {"nodes": [{"id": "n1", "op": "seq_count",
                      "args": {"xs": {"res": "R-1A1"}, "t": {"lit": 1}}}],
           "positions": ["n1"], "sink": "n1"}
    with pytest.raises(LoadError):
        validate_reference_program(seq, ["R-1A1", "R-2B2"], reg)
    # Manifest/registry key mismatch.
    with pytest.raises(LoadError):
        validate_reference_program(prog, ["R-1A1"], reg)


# --- §1.14 scheduler tests --------------------------------------------------

def test_scheduler_block_balance_and_crossing():
    dpv = profiles.profile_version(PROF)
    assignments = [program.factor_assignment(
        program.GENERATOR_VERSION, dpv, "train", "lookup_math", i)
        for i in range(12)]
    combos = [(a["sign"], a["target_stratum"]) for a in assignments]
    # Exact balance at block boundaries (B = 6): each level pair twice.
    assert sorted(combos.count(c) for c in set(combos)) == [2] * 6
    # Within one block: each combination exactly once.
    assert len(set(combos[:6])) == 6


def test_scheduler_partial_block_within_one():
    dpv = profiles.profile_version(PROF)
    combos = [tuple(program.factor_assignment(
        program.GENERATOR_VERSION, dpv, "train", "math_atomic", i).values())
        for i in range(8)]  # B = 3; 8 = 2 full blocks + 2
    counts = [combos.count((level,)) for level in ("T1", "T2", "T3")]
    assert max(counts) - min(counts) <= 1


def test_target_stratum_stratification():
    # §1.14: entity indices split by numpy.array_split(range(N), 3).
    for index in range(9):
        result = generate_latent("lookup_atomic", "train", index, PROF)
        latent = result.latent
        stratum = latent["factor_assignment"]["target_stratum"]
        rec = IntegerRecord.from_json(
            latent["private_registry"][latent["params"]["H"]])
        entities = [e for e, _ in rec.payload]
        pos = entities.index(latent["params"]["key"])
        strata = np.array_split(np.arange(len(entities)), 3)
        expected = strata[{"first": 0, "middle": 1, "last": 2}[stratum]]
        assert pos in expected


# --- metamorphic tests (§4) -------------------------------------------------

def test_stable_unique_idempotent():
    xs = [6, 1, 6, 9, 4, 1, 8]
    once = program.stable_unique(xs)
    assert program.stable_unique(once) == once


def test_count_invariant_under_dedup_permutation():
    xs = [6, 1, 9, 4, 8, 3, 2, 7]
    rng = np.random.default_rng(0)
    for _ in range(10):
        perm = list(rng.permutation(xs))
        assert program.count_gt(perm, 5) == program.count_gt(xs, 5)


def test_renderer_invariance():
    latent = generate_latent("lookup_math", "construction", 7, PROF).latent
    instances = [program.render_instance(latent, r, "private")
                 for r in ("resource_first", "goal_first", "bound_var")]
    prompts = {i["public_prompt"] for i in instances}
    assert len(prompts) == 3
    for inst in instances[1:]:
        assert inst["gold_answer"] == instances[0]["gold_answer"]
        assert inst["reference_program"] == instances[0]["reference_program"]
        assert inst["private_registry"] == instances[0]["private_registry"]
        assert inst["latent_program_id"] == instances[0]["latent_program_id"]


def test_handle_renaming_invariance():
    prog, manifest, reg = _valid_lm()
    renamed_prog = copy.deepcopy(prog)
    renamed_prog["nodes"][0]["args"]["handle"] = {"res": "R-9Z9"}
    renamed_reg = {"R-9Z9": reg["R-3T5"]}
    assert evaluate_reference(prog, reg) == \
        evaluate_reference(renamed_prog, renamed_reg)


def test_distractor_invariance():
    prog, manifest, reg = _valid_lm()
    gold = evaluate_reference(prog, reg)["n2"]
    resampled = {"R-3T5": keyed(("Aster", {"units": 88}),
                                ("Cedar", {"units": 17}),
                                ("Grove", {"units": 61}))}
    assert evaluate_reference(prog, resampled)["n2"] == gold


# --- provenance-based no-leakage (§4) ---------------------------------------

# The frozen requirement is structural: private-value provenance must not be
# available to the renderer at all. Output scanning alone would stay green if
# private values were supplied but happened not to be printed.

def test_renderers_reject_raw_generator_parameters():
    latent = generate_latent("math_atomic", "construction", 0, PROF).latent
    raw = dict(latent["params"])
    for call in (
        lambda p: render.render_public_prompt("math_atomic",
                                              "resource_first", p),
        lambda p: render.reference_subtasks("math_atomic", p),
    ):
        with pytest.raises(InfrastructureError):
            call(raw)
        call(latent["public_params"])  # the projection is accepted


@pytest.mark.parametrize("cell,private_keys", [
    ("math_atomic", ("a", "b", "c", "d", "m")),
    ("math_code", ("a", "b", "c", "m")),
    ("code_atomic", ("U",)),
    ("fork_join", ("U",)),
])
def test_public_projection_excludes_private_state(cell, private_keys):
    for index in range(4):
        latent = generate_latent(cell, "construction", index, PROF).latent
        public = latent["public_params"]
        assert set(public) == set(
            types.public_param_keys(cell, latent["params"]))
        for key in private_keys:
            assert key not in public
        # No public value coincides with a private operand by construction
        # of the projection: the private ones are simply not members.
        private_values = {v for k, v in latent["params"].items()
                          if k not in public and isinstance(v, int)}
        assert not private_values & {v for v in public.values()
                                     if isinstance(v, int)} - set(
            latent["public_numeric_values"].values())


def test_public_projection_is_immutable_and_typed():
    latent = generate_latent("lookup_math", "construction", 0, PROF).latent
    public = latent["public_params"]
    assert isinstance(public, types.PublicParams)
    with pytest.raises(TypeError):
        public["p"] = 99  # Mapping, not MutableMapping
    with pytest.raises(InfrastructureError):
        types.PublicParams("lookup_math", {"H": "R-1A1"})  # incomplete


def test_public_projection_immutability_is_real_not_documented():
    """Mutating a projection would change rendered bytes without changing
    the latent identity those bytes are pinned to."""
    latent = generate_latent("lookup_math", "construction", 0, PROF).latent
    public = latent["public_params"]
    before = render.render_public_prompt("lookup_math", "resource_first",
                                         public)
    with pytest.raises(TypeError):          # backing map is a read-only proxy
        public._values["p"] = 99
    with pytest.raises(InfrastructureError):  # attributes cannot be rebound
        public._values = {"p": 99}
    with pytest.raises(InfrastructureError):
        public._cell_id = "math_atomic"
    with pytest.raises(InfrastructureError):
        del public._values
    assert render.render_public_prompt("lookup_math", "resource_first",
                                       public) == before


def test_numeric_features_are_derived_not_supplied():
    latent = generate_latent("code_atomic", "construction", 1, PROF).latent
    public = latent["public_params"]
    assert public.numeric_features() == latent["public_numeric_values"]
    # Only the subtype's own parameters can appear: a `count` instance has
    # no k/i, and nothing outside the frozen family can be injected.
    assert set(public.numeric_features()) <= {"p", "q", "t", "k", "i"}


def test_prompt_integers_trace_to_public_parameters():
    from tasks.conductor.types import INTEGER_TOKEN_RE
    for cell in ("lookup_atomic", "math_atomic", "code_atomic",
                 "lookup_math", "math_code", "fork_join"):
        for index in range(4):
            latent = generate_latent(cell, "construction", index, PROF).latent
            inst = program.render_instance(latent, "resource_first",
                                           "private")
            public = set(latent["public_numeric_values"].values())
            for match in INTEGER_TOKEN_RE.finditer(inst["public_prompt"]):
                assert int(match.group(0)) in public, \
                    (cell, match.group(0), inst["public_prompt"])


# --- §1.13 split isolation and determinism ----------------------------------

def test_no_latent_program_crosses_namespaces():
    ids = {ns: generate_latent("math_atomic", ns, 1, PROF)
           .latent["latent_program_id"]
           for ns in ("construction", "qualification", "train")}
    assert len(set(ids.values())) == 3


def test_prefix_determinism():
    a = [generate_latent("code_atomic", "dev", i, PROF).latent
         for i in range(3)]
    b = [generate_latent("code_atomic", "dev", i, PROF).latent
         for i in range(3)]
    assert a == b


def test_namespace_caps_enforced():
    # D4 (132_s §3.1, approved 133_f): construction cap extended 100→130.
    with pytest.raises(GenerationError):
        generate_latent("lookup_atomic", "construction", 130, PROF)
    generate_latent("lookup_atomic", "construction", 129, PROF)
    with pytest.raises(GenerationError):
        generate_latent("fork_join", "qualification", 200, PROF)
    generate_latent("fork_join", "qualification", 199, PROF)


@pytest.mark.parametrize("bad_index", [-1, -42, True, False, 1.0, "0"])
def test_latent_index_domain_closed(bad_index):
    # `False` is the subtle one: bool subclasses int, so it would display
    # as index 00000 while seeding from "False" — an instance that fails
    # its own normative regeneration.
    with pytest.raises(GenerationError):
        generate_latent("lookup_atomic", "construction", bad_index, PROF)


def test_unknown_cell_and_namespace_rejected():
    with pytest.raises(GenerationError):
        generate_latent("bogus_cell", "construction", 0, PROF)
    with pytest.raises(GenerationError):
        generate_latent("lookup_atomic", "bogus_namespace", 0, PROF)


def test_visibility_and_renderer_labels_closed():
    latent = generate_latent("lookup_atomic", "construction", 0, PROF).latent
    program.render_instance(latent, "resource_first", "private")
    program.render_instance(latent, "resource_first", "visible")
    for renderer, visibility in (("resource_first", "bogus"),
                                 ("bogus", "private"),
                                 ("resource_first", "Private")):
        with pytest.raises(ValueError):
            program.render_instance(latent, renderer, visibility)


# --- §1.16 collision metadata -----------------------------------------------

def test_collision_metadata_node_level():
    meta = program.collision_metadata(
        "lookup_math", {"p": 3, "q": 47, "sign": "-"},
        {"n1": 17, "n2": 47}, "n2")
    assert meta["public_numeric_collision_nodes"] == {"n2": ["q"]}
    assert meta["public_numeric_collision"] is True
    assert meta["sink_public_numeric_collision"] is True

    meta = program.collision_metadata(
        "fork_join", {"t": 4, "q": 9, "branch_order": "lookup_first"},
        {"n1": 14, "n2": 4, "n3": 65}, "n3")
    assert meta["public_numeric_collision_nodes"] == {"n2": ["t"]}
    assert meta["sink_public_numeric_collision"] is False

    meta = program.collision_metadata(
        "lookup_atomic", {"key": "Grove", "field": "crates"},
        {"n1": 39}, "n1")
    assert meta["public_numeric_collision"] is False
    assert meta["public_numeric_values"] == {}


# --- sampler and R_MAGNITUDE fixtures (§4) ----------------------------------

def test_samplers_require_band_arguments():
    rng = np.random.default_rng(0)
    with pytest.raises(TypeError):
        program.integer_list_dedup(rng, 8)          # no band
    with pytest.raises(TypeError):
        program.integer_list_select(rng, 8)         # no band
    with pytest.raises(TypeError):
        program.integer_record(rng, rng, 3, 1)      # no band/layout


def test_r_magnitude_base_path_rejection():
    profile = copy.deepcopy(PROF)
    profile["cells"]["math_code"]["a_band"] = [10**11, 10**11]
    profile["cells"]["math_code"]["b_band"] = [99, 99]
    profiles.validate_profile(profile)  # loads fine; rejection is per-candidate
    with pytest.raises(GenerationError) as err:
        generate_latent("math_code", "construction", 0, profile)
    assert "R_MAGNITUDE" in str(err.value)


def test_r_magnitude_intervention_path_checked():
    reg = {"R-3T5": keyed(("Aster", {"units": 31}))}
    prog = _lookup_math_prog("R-3T5", "Aster", "units", 2, "+", 1)
    assert evaluate_reference(prog, reg)["n2"] == 63
    with pytest.raises(RMagnitude):
        evaluate_reference(prog, reg, overrides={"n1": 500_000_000_001})


def test_t1_congruence_sampling_is_analytic_not_enumerated():
    """A wide c band whose congruence class is empty must fail fast: the
    old enumeration scanned the whole band on every one of the 1000
    resampling attempts."""
    profile = copy.deepcopy(PROF)
    profile["cells"]["math_atomic"].update(
        a_band=[1_000_000, 1_000_000], b_band=[99, 99],
        c_band=[1, 1_000_000])
    profile["cells"]["math_atomic"]["t1"]["d_band"] = [10**9, 10**9]
    profiles.validate_profile(profile)
    dpv = profiles.profile_version(profile)
    t1_index = next(
        i for i in range(6)
        if program.factor_assignment(program.GENERATOR_VERSION, dpv,
                                     "construction", "math_atomic",
                                     i)["template"] == "T1")
    start = time.monotonic()
    with pytest.raises(GenerationError, match="resampling cap"):
        generate_latent("math_atomic", "construction", t1_index, profile)
    assert time.monotonic() - start < 5.0


def test_congruent_sampler_matches_enumeration():
    rng = np.random.default_rng(0)
    for lo, hi, residue, modulus in [(1, 20, 3, 6), (5, 5, 5, 1),
                                     (1, 100, 0, 7), (10, 30, 2, 5)]:
        expected = [c for c in range(lo, hi + 1) if c % modulus == residue
                    % modulus]
        drawn = {program._sample_congruent(rng, (lo, hi), residue, modulus)
                 for _ in range(200)}
        assert drawn <= set(expected) and drawn  # never outside the support
    with pytest.raises(program.SampleRejected):
        program._sample_congruent(rng, (1, 5), 0, 100)  # empty class


def test_construction_inviable_profile_fails_cleanly():
    # Degenerate modulus-only domain: T2 with m = 2 always violates the
    # sign-flip exclusion, so T2-scheduled indices reach the resampling cap.
    profile = copy.deepcopy(PROF)
    profile["cells"]["math_atomic"]["t2"]["m_band"] = [2, 2]
    dpv = profiles.profile_version(profile)
    t2_index = next(
        i for i in range(6)
        if program.factor_assignment(program.GENERATOR_VERSION, dpv,
                                     "construction", "math_atomic",
                                     i)["template"] == "T2")
    with pytest.raises(GenerationError) as err:
        generate_latent("math_atomic", "construction", t2_index, profile)
    assert "resampling cap" in str(err.value)


def test_draw_intervention_requires_a_legal_directed_edge():
    """The public constructor fails closed rather than emitting an invalid
    intervention record."""
    latent = generate_latent("lookup_math", "construction", 0, PROF).latent
    program.draw_intervention(latent, "n1", "n2", PROF)   # the legal edge
    for u, v in (("n1", "n1"), ("n2", "n1"), ("n2", "n2")):
        with pytest.raises(GenerationError, match="not a dependency edge"):
            program.draw_intervention(latent, u, v, PROF)
    atomic = generate_latent("lookup_atomic", "construction", 0, PROF).latent
    with pytest.raises(GenerationError, match="not a dependency edge"):
        program.draw_intervention(atomic, "n1", "n1", PROF)


def test_draw_intervention_requires_the_latents_own_profile():
    """The replacement support comes from the profile, so a mis-wired but
    individually valid profile must not silently change the counterfactual
    target for a resumed run."""
    latent = generate_latent("lookup_math", "construction", 0, PROF).latent
    program.draw_intervention(latent, "n1", "n2", PROF)   # matching profile
    import copy
    other = copy.deepcopy(PROF)
    other["cells"]["lookup_math"]["value_band"] = [10, 199]  # different digest
    with pytest.raises(GenerationError, match="does not match the latent"):
        program.draw_intervention(latent, "n1", "n2", other)


def test_draw_intervention_requires_a_self_consistent_latent_identity():
    """The intervention seed derives from latent_program_id, so a swapped
    id or a stale generator version would silently change the
    deterministic replacement."""
    latent = generate_latent("lookup_math", "construction", 0, PROF).latent
    other = generate_latent("lookup_math", "construction", 1, PROF).latent
    baseline = program.draw_intervention(latent, "n1", "n2", PROF)

    stale = dict(latent, generator_version="specs-v0.8+older")
    with pytest.raises(GenerationError, match="generator_version"):
        program.draw_intervention(stale, "n1", "n2", PROF)

    swapped = dict(latent, latent_program_id=other["latent_program_id"])
    with pytest.raises(GenerationError, match="does not derive"):
        program.draw_intervention(swapped, "n1", "n2", PROF)

    wrong_seed = dict(latent, seed=latent["seed"] + 1)
    with pytest.raises(GenerationError, match="does not derive"):
        program.draw_intervention(wrong_seed, "n1", "n2", PROF)

    # The untouched latent still draws its deterministic replacement.
    assert program.draw_intervention(latent, "n1", "n2", PROF) == baseline


@pytest.mark.parametrize("corrupt,match", [
    (lambda i: i.pop("gold_answer"), "missing \\['gold_answer'\\]"),
    (lambda i: i.update(extra=1), "unexpected \\['extra'\\]"),
    (lambda i: i.update(render_instance_id="bogus"),
     "malformed render_instance_id"),
    (lambda i: i.update(render_instance_id="a:b:00x:deadbeef:rf:private"),
     "malformed render_instance_id"),
    (lambda i: i.update(renderer_id="bogus"), "does not regenerate|mismatch"),
    # Index past the namespace cap, changed consistently in both ids so the
    # identity parses: GenerationError is translated, not leaked.
    (lambda i: i.update(
        latent_program_id=i["latent_program_id"].replace(":00002:",
                                                         ":99999:"),
        render_instance_id=i["render_instance_id"].replace(":00002:",
                                                           ":99999:")),
     "does not regenerate"),
    # Ids that disagree with each other are a shape error caught before
    # regeneration.
    (lambda i: i.update(
        render_instance_id=i["render_instance_id"].replace(":00002:",
                                                           ":00003:")),
     "disagrees with render_instance_id"),
])
def test_validate_instance_always_raises_load_error(corrupt, match):
    """The persisted-artifact boundary the resumable Stage-1 loader relies
    on: malformed shapes, identities and regeneration failures surface as
    LoadError, never raw KeyError/ValueError/GenerationError."""
    latent = generate_latent("lookup_math", "construction", 2, PROF).latent
    instance = program.render_instance(latent, "resource_first", "private")
    bad = copy.deepcopy(instance)
    corrupt(bad)
    with pytest.raises(LoadError, match=match):
        program.validate_instance(bad, PROF)
    with pytest.raises(LoadError):
        program.validate_instance("not a dict", PROF)


def test_drawn_interventions_always_move_the_sink():
    """§3 replacement rules are constructed to provably change the sink."""
    for cell in ("lookup_math", "math_code", "fork_join"):
        for index in range(6):
            latent = generate_latent(cell, "construction", index,
                                     PROF).latent
            for u, v in program.INTERVENTION_EDGES[cell]:
                iv = program.draw_intervention(latent, u, v, PROF)
                assert iv["counterfactual_target"] != iv["corruption_target"]


def test_s_minus_direct_draw():
    # Minus-form replacement pool is S⁻(p, q) \ {n1}, non-empty for every
    # admitted instance; the drawn replacement satisfies p·r − q ≥ 1.
    found = 0
    for index in range(24):
        latent = generate_latent("lookup_math", "train", index, PROF).latent
        if latent["params"]["sign"] != "-":
            continue
        found += 1
        iv = program.draw_intervention(latent, "n1", "n2", PROF)
        p, q = latent["params"]["p"], latent["params"]["q"]
        lo, hi = PROF["cells"]["lookup_math"]["value_band"]
        r = iv["replacement"]
        assert p * r - q >= 1 and lo <= r <= hi
        assert r != latent["node_values"]["n1"]
    assert found >= 5


# --- §4 normative load-time validation --------------------------------------

def test_validate_instance_round_trip_and_mismatch():
    latent = generate_latent("fork_join", "construction", 2, PROF).latent
    inst = program.render_instance(latent, "bound_var", "visible")
    program.validate_instance(inst, PROF)
    for corrupt in (
        lambda i: i.update(gold_answer=i["gold_answer"] + 1),
        lambda i: i.update(public_prompt=i["public_prompt"] + " "),
        lambda i: i.update(renderer_id="goal_first"),
        lambda i: i["public_manifest"].reverse(),
    ):
        bad = copy.deepcopy(inst)
        corrupt(bad)
        with pytest.raises(LoadError):
            program.validate_instance(bad, PROF)


def test_gold_at_least_one_everywhere():
    for cell in ("lookup_atomic", "math_atomic", "code_atomic",
                 "lookup_math", "math_code", "fork_join"):
        for index in range(6):
            latent = generate_latent(cell, "test", index, PROF).latent
            assert latent["gold_answer"] >= 1
            if cell == "math_code":  # intermediate 0 permitted at n1
                assert latent["node_values"]["n1"] >= 0
