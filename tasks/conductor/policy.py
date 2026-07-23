"""Conductor policy prompt and observation builder — 106_s §10.2.

The policy sees the Problem, the reference steps (legitimate semantic
information) and four OPAQUE worker ids. It is never told model names,
sizes, families or the small/large relationship, and it emits exactly
`{"worker_ids": [...]}` — nothing else. Worker ids are fixed and opaque
in v0; pool randomization is a later relaxation.

The system prompt carries four executable OUT-OF-DOMAIN demonstrations
(hand-written; no generator namespace, no `worker_dev` content). All
four ids occur in valid demonstrated actions; workers 2 and 3 are shown
on matched Code-like steps that both execute successfully, so the
examples establish that both are legal Code candidates without encoding
the retained renderer-conditioned lookup table.

STATUS: DRAFT pending the §10.2 prompt review. Once any reward-bearing
smoke output is inspected, these bytes are frozen — a later change is a
new launch profile, never an in-place edit.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

# --- the four out-of-domain demonstrations -----------------------------------
# Each is (observation text, correct action). The Code-like pair (C, D)
# is matched: same task shape, same resource arity, answer reachable by
# a single at() expression — demo-check executes both through the real
# workers (a non-reward-bearing check).

CONDUCTOR_DEMOS: tuple[dict[str, str], ...] = (
    {
        "observation": (
            "Problem:\nA registry lists maintenance codes. Report the "
            "code stored under badge B-11.\n\nSteps:\n"
            "1. Report the value stored under badge B-11. "
            "[resource: B-11]"),
        "action": '{"worker_ids": [0]}',
    },
    {
        "observation": (
            "Problem:\nA meter shows the reading 47. Compute 6 * 47 - "
            "13.\n\nSteps:\n"
            "1. Compute 6 * 47 - 13."),
        "action": '{"worker_ids": [1]}',
    },
    {
        "observation": (
            "Problem:\nA buffer holds an integer sequence. Return the "
            "value at zero-based index 2 of the integer sequence in the "
            "requested resource.\n\nSteps:\n"
            "1. Return the value at zero-based index 2 of the integer "
            "sequence in the requested resource. [resource: R-7Q3]"),
        "action": '{"worker_ids": [2]}',
    },
    {
        "observation": (
            "Problem:\nA log holds an integer sequence. Return the "
            "value at zero-based index 0 of the integer sequence in the "
            "requested resource.\n\nSteps:\n"
            "1. Return the value at zero-based index 0 of the integer "
            "sequence in the requested resource. [resource: R-5T4]"),
        "action": '{"worker_ids": [3]}',
    },
)

# The matched Code-like demo steps as executable worker requests
# (demo-check runs both through workers 2 AND 3 on the real pool).
DEMO_CODE_CHECKS: tuple[dict[str, Any], ...] = (
    {"demo_index": 2, "resource_handle": "R-7Q3",
     "payload": [8, 3, 5, 9], "index": 2, "expected": 5},
    {"demo_index": 3, "resource_handle": "R-5T4",
     "payload": [6, 2, 7], "index": 0, "expected": 6},
)


def _demo_block() -> str:
    parts = []
    for index, demo in enumerate(CONDUCTOR_DEMOS, start=1):
        parts.append(f"Example {index}:\n{demo['observation']}\n"
                     f"Answer: {demo['action']}")
    return "\n\n".join(parts)


SYSTEM_CONDUCTOR = f"""\
You are a workflow router. Each request shows a Problem and its \
numbered Steps. For every step you choose one worker from the pool by \
its id: 0, 1, 2, or 3. Workers differ in what they handle well; the \
step descriptions tell you what each step needs. A step marked \
[resource: ...] reads that resource; a step marked (uses earlier \
results) receives the results of earlier steps.

Reply with exactly {{"worker_ids": [...]}} — one id per step, in step \
order, and nothing else.

{_demo_block()}"""


def policy_prompt_sha256() -> str:
    return hashlib.sha256(SYSTEM_CONDUCTOR.encode("utf-8")).hexdigest()


def build_policy_observation(public_prompt: str,
                             steps: list[Mapping[str, Any]]) -> str:
    """The Stage-0C/2 observation: Problem + reference steps + the
    instruction line. Topology and subtasks are reference-provided; the
    policy contributes worker ids only (plan contract 1)."""
    lines = []
    for position, step in enumerate(steps, start=1):
        line = f"{position}. {step['subtask']}"
        if step.get("resource"):
            line += f" [resource: {step['resource']}]"
        if step.get("access") == "all":
            line += " (uses earlier results)"
        lines.append(line)
    count = len(steps)
    return (f"Problem:\n{public_prompt}\n\nSteps:\n" + "\n".join(lines)
            + f"\n\nChoose one worker id per step. Reply with exactly "
              f'{{"worker_ids": [...]}} containing {count} '
              f"id{'s' if count != 1 else ''}.")


def policy_messages(public_prompt: str,
                    steps: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM_CONDUCTOR},
            {"role": "user",
             "content": build_policy_observation(public_prompt, steps)}]
