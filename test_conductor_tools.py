"""0A battery: envelope precedence, grammars, limits, the global
resource-error procedure, flag truth table, valid-AST fuzzing (§1.6, §1.7,
§4)."""

import random

import pytest

import fuzz_oracle
from tasks.conductor import contract, tools
from tasks.conductor.contract import (
    parse_envelope, pseudo_result, run_worker_output, typed_failure_result,
)
from tasks.conductor.tools import Binding, ToolRejection, execute_artifact
from tasks.conductor.types import (
    InfrastructureError, IntegerList, IntegerRecord,
)

OPS = IntegerRecord(layout="operands",
                    payload=(("a", 83719), ("b", 43), ("c", 1), ("d", 6)))
KEYED = IntegerRecord(layout="keyed", payload=(
    ("Aster", (("crates", 31),)), ("Grove", (("crates", 39),))))
LIST = IntegerList(payload=(5, 3, 5, 8, 1, 3, 9, 2))


def math(content, binding=None):
    return execute_artifact(1, content, binding or Binding({"R": OPS}))


def code(content, binding=None):
    return execute_artifact(2, content, binding or Binding({"R": LIST}))


def lookup(content, binding=None):
    return execute_artifact(0, content, binding or Binding({"R": KEYED}))


def reject_code(fn, content, binding=None):
    with pytest.raises(ToolRejection) as err:
        fn(content, binding)
    return err.value.code


# --- envelope precedence (§1.6 cases 1–6) -----------------------------------

@pytest.mark.parametrize("completion,code", [
    ("<value>5</value>", "E_UNEXPECTED_TAG"),
    ("<artifact>a</artifact> and </value>", "E_UNEXPECTED_TAG"),  # case 1 first
    ("no envelope at all", "E_NO_ARTIFACT"),
    ("<artifact>a</artifact><artifact>b</artifact>", "E_MULTI_ARTIFACT"),
    ("<artifact>a</artifact></artifact>", "E_MULTI_ARTIFACT"),
    ("<artifact>a + b", "E_UNCLOSED_ARTIFACT"),
    ("</artifact>text<artifact>", "E_PARSE"),
])
def test_envelope_precedence(completion, code):
    with pytest.raises(ToolRejection) as err:
        parse_envelope(completion)
    assert err.value.code == code


def test_envelope_variants_are_ordinary_text():
    # Uppercase / attributed variants do not count as tags.
    with pytest.raises(ToolRejection) as err:
        parse_envelope("<ARTIFACT>a</ARTIFACT> <artifact x=1>b</artifact>")
    assert err.value.code == "E_NO_ARTIFACT"


def test_envelope_ignores_surrounding_text():
    assert parse_envelope("thinking <artifact> 1 + 1 </artifact> done") == "1 + 1"


# --- grammar and limit rejections -------------------------------------------

def test_math_examples():
    assert math("(a * b - c) / d") == 599986
    assert math("3 * step_1 - 4", Binding({}, steps={1: 17})) == 47
    assert math("7 % 3") == 1
    assert math("0 - 7") == -7          # negative intermediate is legal


@pytest.mark.parametrize("content,code", [
    ("a--5", "E_PARSE"),                # D14: no unary minus
    ("--5", "E_PARSE"),
    ("-5", "E_PARSE"),                  # no negative literal token
    ("0012", "E_NONCANONICAL_INT"),
    ("1234567890123", "E_PARSE"),       # 13-digit literal
    ("step_0", "E_PARSE"),
    ("step_10", "E_PARSE"),
    ("ab", "E_PARSE"),
    ("5 5", "E_PARSE"),
    ("(a + b", "E_PARSE"),
    ("", "E_PARSE"),
    ("a + Ω", "E_PARSE"),
])
def test_math_grammar_rejections(content, code):
    assert reject_code(math, content) == code


def test_math_semantic_rejections():
    assert reject_code(math, "a / 0") == "E_DIV_ZERO"
    assert reject_code(math, "7 / 2") == "E_INEXACT_DIV"
    assert reject_code(math, "7 % 0") == "E_DIV_ZERO"
    assert reject_code(math, "7 % (0 - 3)") == "E_BAD_ARG"
    assert reject_code(math, "999999999999 * 2") == "E_MAGNITUDE"


def test_floor_mod_semantics():
    assert math("(0 - 7) % 3") == 2


def test_depth_and_node_limits():
    deep = "(" * 9 + "1" + ")" * 9  # parens do not add nodes; build via ops
    assert math(deep) == 1
    nested = "1" + " + 1" * 70
    assert reject_code(math, nested) == "E_DEPTH"  # > 64 nodes
    chain = "((((((((1 + 1) + 1) + 1) + 1) + 1) + 1) + 1) + 1)"
    assert reject_code(math, chain) == "E_DEPTH"   # depth 9


def test_artifact_byte_limit():
    big = "1 + " * 200 + "1"
    assert len(big.encode()) > 512
    assert reject_code(math, big) == "E_PARSE"


def test_lookup_grammar():
    assert lookup('lookup(resource, "Grove", "crates")') == 39
    assert reject_code(lookup, 'lookup(resource, "Zed", "crates")') \
        == "E_UNKNOWN_KEY"
    assert reject_code(lookup, 'lookup(resource, "Grove", "spools")') \
        == "E_UNKNOWN_FIELD"
    for bad in ('lookup(resource, Grove, "crates")',
                'lookup(res, "Grove", "crates")',
                'lookup(resource, "Grove", "crates") + 1',
                'lookup(resource, "9x", "crates")'):
        assert reject_code(lookup, bad) == "E_PARSE"


def test_code_grammar():
    assert code("count_gt(stable_unique(resource), 5)") == 2
    assert code("at(rotate_left(stable_unique(resource), 2), 4)") == 5
    assert code("at(resource, step_1)", Binding({"R": LIST}, {1: 7})) == 2
    assert reject_code(code, "at(resource, 99)") == "E_INDEX_RANGE"
    assert reject_code(code, "rotate_left(resource, 1)") == "E_PARSE"  # seq top
    assert reject_code(code, "count_gt(resource)") == "E_PARSE"
    assert reject_code(code, "sum(resource, 1)") == "E_PARSE"


def test_rotate_left_negative_step_value():
    binding = Binding({"R": LIST}, steps={1: -2})
    assert reject_code(code, "at(rotate_left(resource, step_1), 0)", binding) \
        == "E_BAD_ARG"


# --- §1.6 global resource-error procedure, in order -------------------------

def test_global_procedure_order():
    # 1. demanded, none authorized
    assert reject_code(math, "a + 1", Binding()) == "E_NO_RESOURCE"
    # 2. demanded, none grammar-compatible (both directions)
    assert reject_code(math, "a + 1", Binding({"R": LIST})) == "E_RESOURCE_KIND"
    assert reject_code(code, "count_gt(resource, 1)", Binding({"R": OPS})) \
        == "E_RESOURCE_KIND"
    assert reject_code(lookup, 'lookup(resource, "A", "b")',
                       Binding({"R": OPS})) == "E_RESOURCE_KIND"
    # 3. operands bound, required identifier absent
    assert reject_code(math, "a + x", Binding({"R": OPS})) == "E_UNKNOWN_IDENT"
    # 4. step unavailable (no access / forward / out of range)
    assert reject_code(math, "a + step_9", Binding({"R": OPS})) \
        == "E_UNKNOWN_IDENT"
    # mixed demand: resource condition (1) precedes step condition (4)
    assert reject_code(math, "a + step_9", Binding()) == "E_NO_RESOURCE"
    # step-only expression with unavailable step
    assert reject_code(math, "step_2 + 1", Binding({"R": OPS}, {1: 5})) \
        == "E_UNKNOWN_IDENT"


def test_literal_only_ignores_authorized_set():
    # B5's intended in-context capability: empty and incompatible alike.
    assert math("2 + 3", Binding()) == 5
    assert math("2 + 3", Binding({"R": LIST})) == 5
    assert code("count_gt(rotate_left(stable_unique(resource), 0), 0)",
                Binding({"R": LIST})) == 6
    assert math("step_1 * 2", Binding({}, steps={1: 21})) == 42


def test_multiple_compatible_payloads_is_harness_error():
    two = Binding({"R1": LIST, "R2": IntegerList(payload=(1, 2))})
    with pytest.raises(InfrastructureError):
        code("count_gt(resource, 0)", two)


# --- §1.7 flag truth table --------------------------------------------------

def test_truth_table_rows():
    env = run_worker_output(1, "no tags", Binding())
    assert (env.artifact_valid, env.tool_executed, env.synthetic) == \
        (False, False, False)
    grammar = run_worker_output(1, "<artifact>0012</artifact>", Binding())
    assert (grammar.artifact_valid, grammar.tool_executed) == (False, False)
    semantic = run_worker_output(1, "<artifact>1 / 0</artifact>", Binding())
    assert (semantic.artifact_valid, semantic.tool_executed) == (True, True)
    ok = run_worker_output(1, "<artifact>2 + 2</artifact>", Binding())
    assert ok.status == "success" and ok.value == 4
    blocked = contract.dependency_blocked_result()
    assert (blocked.artifact_valid, blocked.tool_executed,
            blocked.synthetic) == (False, False, False)
    pseudo = pseudo_result(0)
    assert (pseudo.artifact_valid, pseudo.tool_executed, pseudo.synthetic) \
        == (False, False, True)
    pseudo_fail = pseudo_result(None, "E_PARSE")
    assert pseudo_fail.status == "typed_failure" and pseudo_fail.synthetic


def test_every_rejection_code_classified():
    from tasks.conductor.types import REJECTION_CODES
    for code_name in REJECTION_CODES:
        result = typed_failure_result(code_name)
        assert result.rejection_code == code_name


# --- §4 random valid-AST fuzzing vs fuzz_oracle -----------------------------

def test_fuzz_math_agreement():
    rng = random.Random(0)
    operands = {name: value for name, value in OPS.payload}
    steps = {1: 17, 2: -4}
    binding = Binding({"R": OPS}, steps=steps)
    for _ in range(2000):
        text, expected = fuzz_oracle.gen_math(rng, operands, steps)
        try:
            got = execute_artifact(1, text, binding)
        except ToolRejection as rej:
            got = rej.code
        assert got == expected, text


def test_fuzz_code_agreement():
    rng = random.Random(1)
    steps = {1: 3, 2: -1}
    binding = Binding({"R": LIST}, steps=steps)
    for _ in range(2000):
        text, expected = fuzz_oracle.gen_code(rng, list(LIST.payload), steps)
        try:
            got = execute_artifact(2, text, binding)
        except ToolRejection as rej:
            got = rej.code
        assert got == expected, text


def test_fuzz_lookup_agreement():
    rng = random.Random(2)
    record = [(e, list(fs)) for e, fs in KEYED.payload]
    binding = Binding({"R": KEYED})
    for _ in range(500):
        text, expected = fuzz_oracle.gen_lookup(rng, record)
        try:
            got = execute_artifact(0, text, binding)
        except ToolRejection as rej:
            got = rej.code
        assert got == expected, text
