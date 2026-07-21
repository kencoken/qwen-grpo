"""D16 system prompts + demonstrations — SEPARATE 0A FREEZE ARTIFACT.

STATUS: DRAFT — pending its own review (decision D16; freeze record §7).
These strings must be reviewed and frozen against the real worker models
BEFORE the 100-example construction screen; they are fingerprinted, and any
later change retires affected qualification sets. Nothing in this module is
frozen by the phase-1 spec sign-off.

Revision cycle (evidence per revision in `plans/conductor/60_f_…`):

- rev0 (Stage 0A draft): instruction-only prompts, no worked examples.
  Stage-0B smoke against the real pool: 0/14 legal artifacts — Lookup and
  Math emitted correct expressions WITHOUT the envelope; Code used the
  envelope but wrote the resource handle instead of the literal
  identifier `resource`; Math hand-computed the arithmetic in long
  chain-of-thought and hit the 256-token cap on 4/4 calls.
- rev1: worked examples embedded in the system prompts (built at import
  time from the machine-verified DEMONSTRATIONS below, so the example
  text cannot drift from what the runtime actually accepts); explicit
  "literal word resource, never the handle"; explicit "the tool computes,
  you do not"; brevity instruction targeting the token-cap truncations.
  Eval (60_f): Lookup fixed 15/15; Code envelope fixed but handle
  substitution persisted (E_PARSE 10/10); Math unchanged (E_NO_ARTIFACT
  15/15 — CoT alignment overrides prose format contracts).
- rev2 (levers ranked in 61_f): Math reply is artifact-ONLY (removes the
  CoT foothold; §1.6 permits but does not require text before the
  envelope) with a contrastive wrong/right pair showing that the
  computed value is wrong output; Code gets a contrastive pair naming
  the handle mistake verbatim plus "resource is the only name the
  interpreter understands"; Math and Code each gain a second
  machine-verified demonstration exercising step_k (composite-cell
  request shapes); Lookup unchanged (15/15 — keep the diff minimal).
  Eval (62_f): Lookup stable; Code 4/10 (every demonstrated shape now
  succeeds; select-shape — undemonstrated — garbled 0/3); Math unmoved
  (0/17; template interference ruled out by rendered-byte check —
  boxed-CoT alignment overrides even artifact-only instructions).
- rev3 (levers ranked in 63_f): Math reframed as expression TRANSLATION
  ("you translate tasks into calculator expressions; you never solve
  them"; "Evaluate" redefined) and the boxed habit co-opted ("where you
  would normally write \\boxed{...}, write <artifact>...</artifact>
  containing the unevaluated expression"); Code gains the missing
  select-shape demonstration (canonical nesting) plus scope discipline
  ("whitelist calls only — no arithmetic operators; answer only the
  Task, ignore other arithmetic in the Problem").

The §1.5 request skeleton — chat template over exactly (system, user) —
is frozen; demonstrations enter as worked examples INSIDE the system
prompt text, never as extra chat turns.

Demonstrations are all grammar-legal and must execute through the runtime
(0A acceptance: the executes-through-runtime test); demo payloads reuse the
machine-verified §3 worked examples.
"""

from __future__ import annotations

from .types import IntegerList, IntegerRecord, Resource

D16_STATUS = "DRAFT"  # flips to "FROZEN <date>" only via its own review
D16_REVISION = "rev3"  # bumps with any change to the strings below


# --- demonstrations (endpoint -> [(subtask, resource, completion)]) ---------
# Payloads are §3 machine-verified worked examples; completions are legal
# artifacts whose executed value equals the example gold. The system
# prompts embed these same objects as worked examples, so the prompt text
# is checked by the executes-through-runtime test by construction.

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
    }, {
        # step_k form: the lookup_math n2 / fork_join n3 request shape
        # (no resource, previous results only).
        "subtask": "Multiply step_1 by 8, then add 12.",
        "handle": None, "resource": None, "steps": {1: 84},
        "completion": "<artifact>step_1 * 8 + 12</artifact>",
        "value": 684,
    }],
    "code": [{
        "subtask": "Remove later occurrences of repeated values from the "
                   "integer sequence in the requested resource and count "
                   "the values greater than 5.",
        "handle": "R-8C3", "resource": _DEMO_CODE_LIST,
        "completion": "<artifact>count_gt(stable_unique(resource), 5)"
                      "</artifact>",
        "value": 4,
    }, {
        # step_k form: the math_code n2 request shape (resource + one
        # previous result as the index).
        "subtask": "Return the value at zero-based index step_1 in the "
                   "integer sequence from the requested resource.",
        "handle": "R-8C3", "resource": _DEMO_CODE_LIST, "steps": {1: 2},
        "completion": "<artifact>at(resource, step_1)</artifact>",
        "value": 6,
    }, {
        # select shape (code_atomic): the canonical nesting the rev2
        # traces showed the model garbling when undemonstrated.
        "subtask": "Remove later occurrences of repeated values from the "
                   "integer sequence in the requested resource, rotate "
                   "the remaining sequence left by 2 positions, and "
                   "return the value at zero-based index 3.",
        "handle": "R-8C3", "resource": _DEMO_CODE_LIST,
        "completion": "<artifact>at(rotate_left(stable_unique(resource), "
                      "2), 3)</artifact>",
        "value": 3,
    }],
}


def _demo_payload_text(endpoint: str) -> str:
    demo = DEMONSTRATIONS[endpoint][0]
    resource = demo["resource"]
    assert isinstance(resource, (IntegerRecord, IntegerList))
    return resource.payload_text(str(demo["handle"]))


def _demo_completion(endpoint: str) -> str:
    return str(DEMONSTRATIONS[endpoint][0]["completion"])


SYSTEM_LOOKUP = f"""\
You are a retrieval worker. Respond with exactly one \
<artifact>...</artifact> containing a single expression of the form \
lookup(resource, "Key", "field"). Always write the literal word resource \
as the first argument — never the resource's name (such as R-7K2). The \
expression is executed against the resource shown in the request; its \
result is your answer.

Worked example — given this resource:

{_demo_payload_text("lookup")}

the task "{DEMONSTRATIONS["lookup"][0]["subtask"]}" has this complete, \
correct response:

{_demo_completion("lookup")}

Reply with at most one short sentence of reasoning, then the artifact. \
Your reply must contain <artifact> and </artifact> exactly once, with the \
expression between them."""

SYSTEM_MATH = f"""\
You are an expression translator for an exact calculator. You translate \
each task into a single calculator expression — you never solve the \
task. When a task says "Evaluate", it means: write the expression the \
calculator should evaluate. Where you would normally write \\boxed{{...}}, \
write <artifact>...</artifact> instead, containing the UNevaluated \
expression. Respond with exactly one <artifact>...</artifact>. Allowed \
in the expression: integer literals, single-letter operand names from \
the resource (a, b, c, d, m), previous results (step_1, step_2), \
parentheses, and the operators + - * / %. Division must be exact; write \
subtraction with the - operator (no negative literals). Plain ASCII only \
— no LaTeX.

Worked example — given this resource:

{_demo_payload_text("math")}

the task "{DEMONSTRATIONS["math"][0]["subtask"]}" has exactly this \
correct response:

{_demo_completion("math")}

Wrong: {DEMONSTRATIONS["math"][0]["value"]} (a computed number). Wrong: \
a step-by-step solution. The calculator computes the value; you only \
write the expression.

Second example — with no resource and the previous result step_1 = 84, \
the task "{DEMONSTRATIONS["math"][1]["subtask"]}" has exactly this \
correct response:

{DEMONSTRATIONS["math"][1]["completion"]}

Your entire reply must be exactly the artifact — no text before it, no \
text after it."""

SYSTEM_CODE = f"""\
You are a sequence-processing worker. Respond with exactly one \
<artifact>...</artifact> containing a single expression over the \
whitelist: count_gt(seq, n), at(seq, n), stable_unique(seq), \
rotate_left(seq, n), where seq is the word resource or a nested \
whitelist call, and n is a nonnegative integer or step_k. The word \
resource is the only name the interpreter understands — it refers to the \
sequence shown in the request. stable_unique keeps the first occurrence \
of each value; rotate_left rotates left; at is zero-based. The artifact \
may contain whitelist calls only — no arithmetic operators. Answer only \
the Task; ignore any other arithmetic mentioned in the Problem.

Worked example — given this resource:

{_demo_payload_text("code")}

the task "{DEMONSTRATIONS["code"][0]["subtask"]}" has exactly this \
correct response:

{_demo_completion("code")}

Wrong: count_gt(stable_unique(R-8C3), 5) — R-8C3 is the resource's name, \
and the interpreter does not understand names; always write the word \
resource.

Second example — given the same resource and the previous result \
step_1 = 2, the task "{DEMONSTRATIONS["code"][1]["subtask"]}" has \
exactly this correct response:

{DEMONSTRATIONS["code"][1]["completion"]}

Third example — given the same resource, the task \
"{DEMONSTRATIONS["code"][2]["subtask"]}" has exactly this correct \
response:

{DEMONSTRATIONS["code"][2]["completion"]}

Reply with at most one short sentence of reasoning, then the artifact. \
Your reply must contain <artifact> and </artifact> exactly once, with the \
expression between them."""

# Unchanged from rev0: the direct arms (B1/B3/B4) run on the policy model,
# which the worker pool does not load; revising SYSTEM_DIRECT without
# execution evidence would be a change without measurement. Revisit when
# the baseline harness can execute direct arms (Stage 1A calibrate).
SYSTEM_DIRECT = """\
Solve the problem using only the information given. You may reason step by \
step. Answer with a single integer on the final line."""

SYSTEM_PROMPTS = {
    "lookup": SYSTEM_LOOKUP,
    "math": SYSTEM_MATH,
    "code": SYSTEM_CODE,
    "direct": SYSTEM_DIRECT,
}


def demo_binding(demo: dict[str, object]):
    from .tools import Binding
    resource = demo["resource"]
    resources: dict[str, Resource] = {}
    if resource is not None:
        assert isinstance(resource, (IntegerRecord, IntegerList))
        resources[str(demo["handle"])] = resource
    steps = demo.get("steps") or {}
    assert isinstance(steps, dict)
    return Binding(resources=resources, steps=dict(steps))
