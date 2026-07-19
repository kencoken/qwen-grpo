"""D16 system prompts + demonstrations — SEPARATE 0A FREEZE ARTIFACT.

STATUS: DRAFT — pending its own review (decision D16; freeze record §7).
These strings must be reviewed and frozen against the real worker models
BEFORE the 100-example construction screen; they are fingerprinted, and any
later change retires affected qualification sets. Nothing in this module is
frozen by the phase-1 spec sign-off.

Demonstrations are all grammar-legal and must execute through the runtime
(0A acceptance: the executes-through-runtime test); demo payloads reuse the
machine-verified §3 worked examples.
"""

from __future__ import annotations

from .types import IntegerList, IntegerRecord, Resource

D16_STATUS = "DRAFT"  # flips to "FROZEN <date>" only via its own review

SYSTEM_LOOKUP = """\
You are a retrieval worker. Read the task and the resource, then respond \
with exactly one <artifact>...</artifact> containing a single lookup \
expression of the form lookup(resource, "Key", "field"). The expression is \
executed against the authorized resource; its result is your answer. You \
may reason before the artifact, but emit exactly one artifact and nothing \
after it."""

SYSTEM_MATH = """\
You are an exact-arithmetic worker. Read the task, then respond with \
exactly one <artifact>...</artifact> containing a single arithmetic \
expression. Allowed: integer literals, single-letter operand names from \
the resource (a, b, c, d, m), previous results (step_1, step_2), \
parentheses, and the operators + - * / %. Division must be exact; write \
subtraction with the - operator (no negative literals). The expression is \
evaluated by an exact calculator; its result is your answer. You may \
reason before the artifact, but emit exactly one artifact and nothing \
after it."""

SYSTEM_CODE = """\
You are a sequence-processing worker. Read the task, then respond with \
exactly one <artifact>...</artifact> containing a single expression over \
the whitelist: count_gt(seq, n), at(seq, n), stable_unique(seq), \
rotate_left(seq, n), where seq is resource or a nested whitelist call and \
n is a nonnegative integer or step_k. stable_unique keeps the first \
occurrence of each value; rotate_left rotates left; at is zero-based. The \
expression is executed by a whitelist interpreter; its result is your \
answer. You may reason before the artifact, but emit exactly one artifact \
and nothing after it."""

SYSTEM_DIRECT = """\
Solve the problem using only the information given. You may reason step by \
step. Answer with a single integer on the final line."""

SYSTEM_PROMPTS = {
    "lookup": SYSTEM_LOOKUP,
    "math": SYSTEM_MATH,
    "code": SYSTEM_CODE,
    "direct": SYSTEM_DIRECT,
}


# --- demonstrations (endpoint -> [(subtask, resource, completion)]) ---------
# Payloads are §3 machine-verified worked examples; completions are legal
# artifacts whose executed value equals the example gold.

_DEMO_LOOKUP_RECORD = IntegerRecord(layout="keyed", payload=(
    ("Aster", (("crates", 31),)), ("Cedar", (("crates", 17),)),
    ("Grove", (("crates", 39),)), ("Ivory", (("crates", 53),))))

_DEMO_MATH_RECORD = IntegerRecord(layout="operands", payload=(
    ("a", 83719), ("b", 43), ("c", 1), ("d", 6)))

_DEMO_CODE_LIST = IntegerList(payload=(6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4))

DEMONSTRATIONS: dict[str, list[dict[str, object]]] = {
    "lookup": [{
        "subtask": "Retrieve Grove's crates value from the requested "
                   "resource.",
        "handle": "R-7K2", "resource": _DEMO_LOOKUP_RECORD,
        "completion": '<artifact>lookup(resource, "Grove", "crates")'
                      "</artifact>",
        "value": 39,
    }],
    "math": [{
        "subtask": "Evaluate `(a × b − c) ÷ d` exactly using the integers "
                   "in the requested resource.",
        "handle": "R-2P6", "resource": _DEMO_MATH_RECORD,
        "completion": "<artifact>(a * b - c) / d</artifact>",
        "value": 599986,
    }],
    "code": [{
        "subtask": "Remove later occurrences of repeated values from the "
                   "integer sequence in the requested resource and count "
                   "the values greater than 5.",
        "handle": "R-8C3", "resource": _DEMO_CODE_LIST,
        "completion": "<artifact>count_gt(stable_unique(resource), 5)"
                      "</artifact>",
        "value": 4,
    }],
}


def demo_binding(demo: dict[str, object]):
    from .tools import Binding
    resource = demo["resource"]
    assert isinstance(resource, (IntegerRecord, IntegerList))
    return Binding(resources={str(demo["handle"]): resource})
