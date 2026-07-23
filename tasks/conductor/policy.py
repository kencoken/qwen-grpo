"""Conductor policy prompt and demonstrations — 106_s §10.2 as
corrected by 121_s (unit 4 rev2).

The policy sees the CANONICAL observation (`render.build_observation` —
the identity- and visibility-checked skeleton with `Resources
available` and the `(resource: …; previous results: …)` access
notation) plus this system prompt with four OPAQUE worker ids. It is
never told model names, sizes, families or the small/large
relationship, and it emits exactly `{"worker_ids": [...]}`. Worker ids
are fixed and opaque in v0.

The four demonstrations are complete OUT-OF-DOMAIN executable
workflows (new synthetic problems, resources and identities — no
generator namespace or `worker_dev` content; endpoint-compatible task
shapes and the worker-tested `R-*` / "zero-based index … requested
resource" language are deliberately reused, since demonstrations
establish legal capabilities, not linguistic generalization). They
cover the inherited 01_s workflow types under the reviewer's compact
arrangement, giving every worker exactly two appearances and reversing
the Code-worker order across the two Code-bearing demos:

  1. direct route          [0]        (one step)
  2. dependency chain      [0, 1]     (two steps)
  3. independent → final   [2, 3, 1]  (three steps)
  4. specialist → check    [3, 2]     (two steps)

Recorded interpretation (121_s addendum): "specialist → check" is a
SEMANTIC ROLE PATTERN over the legal `[none, all]` two-step chain, not
a fourth v0 graph. The executable check performed is a dependent read:
the specialist counts qualifying values and the second worker reads the
sequence entry at that count — a transform of the first result, not a
verification operator, and it is recorded as such.

Exchangeability (121_s standard): both Code workers execute both
Code-bearing demos successfully (demo-check runs each Code-bearing
workflow with the assigned ids AND with the Code ids swapped);
assignment was fixed at preregistration, before any probing; no
task-relevant feature — operation, index regime, wording, access
pattern or difficulty — is intentionally varied with worker id.

STATUS: DRAFT pending the demo-check + reward-blind format probe under
the 121_s-agreed procedure. Frozen immediately after a passing probe;
any later change is a new launch profile.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from . import render
from .resources import InstanceRegistry

# --- the four preregistered demonstration workflows --------------------------
# Each record is a complete executable workflow: canonical observation
# inputs (problem, manifest, typed resources, steps), the demonstrated
# action, and the gold terminal. Resources serialize through the frozen
# payload_text forms via InstanceRegistry — never hand-formatted.

CONDUCTOR_DEMOS: tuple[dict[str, Any], ...] = (
    {
        "name": "direct",
        "problem": ("A depot ledger records fittings per bay. Report "
                    "Mesa's crates figure."),
        "manifest": ["R-3W6"],
        "resources": {"R-3W6": {
            "kind": "integer_record", "layout": "keyed",
            "payload": [["Harbor", [["crates", 12], ["flags", 8]]],
                        ["Mesa", [["crates", 27], ["flags", 3]]]]}},
        "steps": [
            {"subtask": "Retrieve Mesa's crates value from the "
                        "requested resource.",
             "resource": "R-3W6", "access": "none"}],
        "worker_ids": [0],
        "gold": 27,
    },
    {
        "name": "dependency",
        "problem": ("A dispatch sheet lists flags per bay. Take "
                    "Harbor's flags figure, multiply it by 3, then "
                    "add 4."),
        "manifest": ["R-6D2"],
        "resources": {"R-6D2": {
            "kind": "integer_record", "layout": "keyed",
            "payload": [["Harbor", [["crates", 15], ["flags", 8]]],
                        ["Vista", [["crates", 21], ["flags", 5]]]]}},
        "steps": [
            {"subtask": "Retrieve Harbor's flags value from the "
                        "requested resource.",
             "resource": "R-6D2", "access": "none"},
            {"subtask": "Multiply step_1 by 3, then add 4.",
             "resource": None, "access": "all"}],
        "worker_ids": [0, 1],
        "gold": 28,
    },
    {
        "name": "independent_final",
        "problem": ("Two intake buffers each hold an integer "
                    "sequence. Read one entry from each buffer, "
                    "multiply the two entries, then add 9."),
        "manifest": ["R-7Q3", "R-5T4"],
        "resources": {
            "R-7Q3": {"kind": "integer_list",
                      "payload": [8, 3, 5, 9]},
            "R-5T4": {"kind": "integer_list",
                      "payload": [6, 2, 7]}},
        "steps": [
            {"subtask": "Return the value at zero-based index 2 in "
                        "the integer sequence from the requested "
                        "resource.",
             "resource": "R-7Q3", "access": "none"},
            {"subtask": "Return the value at zero-based index 1 in "
                        "the integer sequence from the requested "
                        "resource.",
             "resource": "R-5T4", "access": "none"},
            {"subtask": "Multiply step_1 by step_2, then add 9.",
             "resource": None, "access": "all"}],
        "worker_ids": [2, 3, 1],
        "gold": 19,   # 5 * 2 + 9
    },
    {
        "name": "specialist_check",
        "problem": ("A gauge log holds an integer sequence, and a "
                    "rack list holds another. Count the gauge values "
                    "greater than 4 after removing repeats, then read "
                    "the rack entry at that count."),
        "manifest": ["R-9J5", "R-2M8"],
        "resources": {
            "R-9J5": {"kind": "integer_list",
                      "payload": [7, 1, 7, 5, 2, 5]},
            "R-2M8": {"kind": "integer_list",
                      "payload": [4, 9, 6, 3]}},
        "steps": [
            {"subtask": "Remove later occurrences of repeated values "
                        "from the integer sequence in the requested "
                        "resource and count the values greater "
                        "than 4.",
             "resource": "R-9J5", "access": "none"},
            {"subtask": "Return the value at zero-based index step_1 "
                        "in the integer sequence from the requested "
                        "resource.",
             "resource": "R-2M8", "access": "all"}],
        "worker_ids": [3, 2],
        "gold": 6,    # stable_unique -> [7,1,5,2]; count>4 = 2; at(,2) = 6
    },
)


def demo_registry(demo: Mapping[str, Any]) -> InstanceRegistry:
    return InstanceRegistry(list(demo["manifest"]),
                            json.loads(json.dumps(demo["resources"])))


def demo_observation(demo: Mapping[str, Any]) -> str:
    """The demo's observation in the CANONICAL private-condition layout
    (121_s finding 1): same skeleton the smoke rows use."""
    return render.format_ood_observation(
        demo["problem"], list(demo["manifest"]), list(demo["steps"]))


def _demo_block() -> str:
    parts = []
    for index, demo in enumerate(CONDUCTOR_DEMOS, start=1):
        action = json.dumps({"worker_ids": demo["worker_ids"]})
        parts.append(f"Example {index}:\n{demo_observation(demo)}\n"
                     f"Answer: {action}")
    return "\n\n".join(parts)


SYSTEM_CONDUCTOR = f"""\
You are a workflow router. Each request shows a Problem, the resources \
available, and its numbered Steps. For every step you choose one \
worker from the pool by its id: 0, 1, 2, or 3. Workers differ in what \
they handle well; the step descriptions tell you what each step needs. \
Each step line shows which resource it reads and whether it receives \
the results of earlier steps.

Reply with exactly {{"worker_ids": [...]}} — one id per step, in step \
order, and nothing else.

{_demo_block()}"""


def policy_prompt_sha256() -> str:
    return hashlib.sha256(SYSTEM_CONDUCTOR.encode("utf-8")).hexdigest()


def policy_messages(instance: dict[str, Any],
                    steps: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    """System prompt + the canonical observation for one instance
    (121_s finding 1: `render.build_observation` is the one supported
    observation boundary — identity-checked, visibility-coupled)."""
    return [{"role": "system", "content": SYSTEM_CONDUCTOR},
            {"role": "user",
             "content": render.build_observation(instance, list(steps))}]
