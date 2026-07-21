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
  Eval (64_f): Code select nesting fixed but handle substitution
  regressed 4/10 → 1/10 (rule got buried mid-prompt); Math 0/15 third
  consecutive revision; probes showed (1) three maximally different Math
  prompts all score 0/20 — content irrelevant — and (2) base
  Qwen2.5-1.5B-Instruct with the same prompt scores 20/20 legal →
  endpoint-model question escalated to the D16/spec review.
- rev4 (levers ranked in 65_f): Code restructured to Lookup's winning
  layout — identifier rule in the FIRST sentence, three examples, rule +
  envelope contract restated LAST (recency); "given the same resource"
  repetitions and the "ignore other arithmetic" sentence cut. Math
  frozen at the rev3 text as the documented best-effort candidate
  (probe 2 proves a compliant model follows it).
  Eval (66_f/68_f): Code 9/10, confirmed 26/30 at 3x scale — all four
  residual failures are fork_join two-handle contexts; Lookup 45/45
  (CLOSED as of rev6); Math 0/56 → endpoint-model decision.
- rev6 (70_f; rev5 was confirmation-only): the Math ENDPOINT MODEL
  switches to base Qwen2.5-1.5B-Instruct in the runtime profile
  (provisionally signed off 2026-07-21; spec §1.6 erratum deferred to
  the D16/third-party review) — Math prompt TEXT unchanged from rev3 so
  the eval isolates the swap. Code: the wrong/right contrast extended to
  the two-handle case ("this also holds when the Problem mentions
  several resources"), targeting the only remaining failure mode.
  Eval (70_f): Math 57/57 with correct values (freeze posture); Code
  code_atomic 15/15, fork_join 12/15, and the newly-unlocked math_code
  step 2 0/15 — argument-order flips (at(step_1, R-8X7)) and invented
  guards (at(resource, step_1 % length(resource))).
- rev7 (levers ranked in 71_f): Code only — argument-order + anti-guard
  wrong/right contrasts attached to the second worked example; the
  first-sentence rule extended with the positional form ("in every call
  the FIRST argument is the sequence and the SECOND is a number").
  Math and Lookup untouched.
  Eval (72_f): Code 41/45 — fork_join 15/15, math_code 11/15; ALL four
  residuals copy the anti-guard wrong exemplar verbatim
  (at(resource, step_1 % 8)) — a concrete wrong string that flatters
  the model's defensive prior becomes a template, not a warning.
- rev8 (73_f): the copyable anti-guard exemplar replaced with a
  non-copyable phrasing ("the number argument is step_1 or an integer,
  written exactly as given — never wrap it in arithmetic"). Nothing
  else changes.
  Eval (74_f): math_code still 11/15, SAME four instances — with the
  template gone they re-invent at(resource, step_1 % length(resource))
  spontaneously. Trigger isolated: failures are exactly step_1 >= 10;
  passes all step_1 <= 5. Value-dependent defensive prior.
- rev9 (75_f): the matched-regime lever — the second Code demonstration
  binds step_1 = 10 (large-index regime, the trigger zone) instead of
  step_1 = 2, plus the assurance "step_1 is always a valid zero-based
  index, even when it is large." Pre-registered decision rule: clears
  math_code -> content iteration done; guard persists -> model-limit
  verdict for this mode, residue referred to the 1A gates.

The §1.5 request skeleton — chat template over exactly (system, user) —
is frozen; demonstrations enter as worked examples INSIDE the system
prompt text, never as extra chat turns.

Demonstrations are all grammar-legal and must execute through the runtime
(0A acceptance: the executes-through-runtime test); demo payloads reuse the
machine-verified §3 worked examples.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .profiles import ProfileError
from .types import IntegerList, IntegerRecord, Resource

D16_STATUS = "DRAFT"  # flips to "FROZEN <date>" only via its own review
D16_REVISION = "rev9"  # bumps with any change to the strings below
# (rev5 was the no-change confirmation run; the counter tracks the
# revision-log numbering in plans/conductor/.)


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
        # step_1 = 10 deliberately sits in the large-index regime that
        # triggers the model's defensive %-guard (74_f): the demo must
        # cover the regime it needs to teach.
        "subtask": "Return the value at zero-based index step_1 in the "
                   "integer sequence from the requested resource.",
        "handle": "R-8C3", "resource": _DEMO_CODE_LIST, "steps": {1: 10},
        "completion": "<artifact>at(resource, step_1)</artifact>",
        "value": 7,
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
You are a sequence-processing worker. The sequence argument in your \
expression is always the word resource — never a name like R-8C3; \
resource is the only name the interpreter understands, and it refers to \
the sequence shown in the request. Respond with exactly one \
<artifact>...</artifact> containing a single expression built only from \
the whitelist calls count_gt(seq, n), at(seq, n), stable_unique(seq), \
rotate_left(seq, n) — no arithmetic operators — where seq is resource or \
a nested whitelist call and n is a nonnegative integer or step_k. In \
every call the FIRST argument is the sequence and the SECOND is a \
number. stable_unique keeps the first occurrence of each value; \
rotate_left rotates left; at is zero-based.

Worked example — given this resource:

{_demo_payload_text("code")}

the task "{DEMONSTRATIONS["code"][0]["subtask"]}" has exactly this \
correct response:

{_demo_completion("code")}

Wrong: count_gt(stable_unique(R-8C3), 5) — R-8C3 is the resource's name, \
and the interpreter does not understand names; always write the word \
resource. This also holds when the Problem mentions several resources \
(for example R-2M4 and R-8C3): the word resource always means the \
payload shown under Resource: in this request, so the correct response \
is still count_gt(stable_unique(resource), 5).

Second example — with the previous result step_1 = 10, the task \
"{DEMONSTRATIONS["code"][1]["subtask"]}" has exactly this correct \
response:

{DEMONSTRATIONS["code"][1]["completion"]}

Wrong: at(step_1, resource) — the sequence is always the first \
argument; the index comes second. The number argument is step_1 or an \
integer, written exactly as given — never wrap it in arithmetic; the \
whitelist has no operators. step_1 is always a valid zero-based index, \
even when it is large.

Third example — the task "{DEMONSTRATIONS["code"][2]["subtask"]}" has \
exactly this correct response:

{DEMONSTRATIONS["code"][2]["completion"]}

The sequence argument is always the word resource, never its name. Your \
reply must contain <artifact> and </artifact> exactly once, with the \
expression between them."""

# 92_s §2.3 second Code prompt condition — model-neutral, derived only
# from the retained rev1-9 evidence (no new GPU output was inspected):
# - task-locality is the FIRST rule: the dominant alternative-renderer
#   failure solved or composed the global Problem (78_s finding 3);
#   rev3 carried the rule mid-prompt, rev4 cut it, rev9 never restored
#   it explicitly;
# - NO wrong exemplars: rev7/8 showed a concrete wrong string that
#   flatters the model's prior becomes a template, and rev8's
#   non-copyable phrasing still left re-invented guards — v1 states the
#   positive rule only;
# - the rev4 winning layout (critical rules first, worked examples,
#   rules + envelope restated last) and the rev9 matched-regime
#   step_1 = 10 demonstration are kept.
# Lookup and Math texts are byte-identical to rev9 in this bundle.
SYSTEM_CODE_LOCAL_V1 = f"""\
You are a sequence-processing worker. Complete only the assigned Task — \
the Problem is background context, and other numbers or operations in \
it are not part of your answer. The sequence argument in your \
expression is always the word resource — never a name like R-8C3 — and \
it refers to the sequence shown under Resource: in this request. \
Respond with exactly one <artifact>...</artifact> containing a single \
expression with no arithmetic operators. The top-level call must be \
count_gt(seq, n) or at(seq, n), where seq is resource or a nesting \
formed only with stable_unique(seq) and rotate_left(seq, n), and n is \
a nonnegative integer or step_k, written exactly as given. In \
count_gt, at, and rotate_left, the FIRST argument is the sequence and \
the SECOND is the number; stable_unique takes only the sequence. \
stable_unique keeps the first occurrence of each value; rotate_left \
rotates left; at is zero-based, and any step_k you are given is \
already a valid zero-based index, even when it is large.

Worked example — given this resource:

{_demo_payload_text("code")}

the task "{DEMONSTRATIONS["code"][0]["subtask"]}" has exactly this \
correct response:

{_demo_completion("code")}

Second example — with the previous result step_1 = 10, the task \
"{DEMONSTRATIONS["code"][1]["subtask"]}" has exactly this correct \
response:

{DEMONSTRATIONS["code"][1]["completion"]}

Third example — the task "{DEMONSTRATIONS["code"][2]["subtask"]}" has \
exactly this correct response:

{DEMONSTRATIONS["code"][2]["completion"]}

Answer the Task alone, using the word resource for the sequence and \
step_k or integers exactly as given. Your reply must contain \
<artifact> and </artifact> exactly once, with the expression between \
them."""

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


# --- revision-keyed worker prompt registry (worker-eval plan 81_f §5.2) -----
# A named revision is valid only if it resolves to exact strings; the pool
# binds a resolved bundle at construction and never re-reads module globals.
# `SYSTEM_DIRECT` status is deliberately separate (§5.2) and not in bundles.

PROMPT_REVISIONS: dict[str, dict[str, str]] = {
    D16_REVISION: {
        "lookup": SYSTEM_LOOKUP,
        "math": SYSTEM_MATH,
        "code": SYSTEM_CODE,
    },
    # 92_s §2.3: the second Code prompt condition; DRAFT until reviewed
    # and hashed into the frozen preregistration.
    "code_local_v1": {
        "lookup": SYSTEM_LOOKUP,
        "math": SYSTEM_MATH,
        "code": SYSTEM_CODE_LOCAL_V1,
    },
}

WORKER_ENDPOINT_SET = frozenset({"lookup", "math", "code"})


@dataclass(frozen=True)
class PromptBundle:
    """Immutable resolved worker prompts: (endpoint, exact text) pairs bound
    to a revision name and freeze status. Deeply immutable — safe to retain
    in frozen evaluator cases and to hash for provenance."""

    revision: str
    status: str  # D16_STATUS at resolution time: "DRAFT" | "FROZEN <date>"
    prompts: tuple[tuple[str, str], ...]  # sorted (endpoint, text)

    def text(self, endpoint_name: str) -> str:
        for name, text in self.prompts:
            if name == endpoint_name:
                return text
        raise ProfileError(f"bundle {self.revision!r} has no prompt for "
                           f"endpoint {endpoint_name!r}")

    def sha256(self) -> dict[str, str]:
        return {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                for name, text in self.prompts}


def resolve_prompts(revision: str = D16_REVISION,
                    expected_sha256: Mapping[str, str] | None = None
                    ) -> PromptBundle:
    """Fail-closed prompt binding: unknown revision or declared-hash
    mismatch raises before any generation can occur."""
    if revision not in PROMPT_REVISIONS:
        raise ProfileError(
            f"unknown worker prompt revision {revision!r}; known: "
            f"{sorted(PROMPT_REVISIONS)}")
    prompts = PROMPT_REVISIONS[revision]
    if set(prompts) != WORKER_ENDPOINT_SET:
        raise ProfileError(
            f"revision {revision!r} must cover exactly "
            f"{sorted(WORKER_ENDPOINT_SET)}, got {sorted(prompts)}")
    bundle = PromptBundle(revision=revision, status=D16_STATUS,
                          prompts=tuple(sorted(prompts.items())))
    if expected_sha256 is not None:
        actual = bundle.sha256()
        declared = dict(expected_sha256)
        if declared != actual:
            wrong = sorted(name for name in set(actual) | set(declared)
                           if actual.get(name) != declared.get(name))
            raise ProfileError(
                f"prompt revision {revision!r} content mismatch for "
                f"endpoints {wrong}: declared hashes do not match the "
                "registered strings")
    return bundle


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
