"""Renderers, reference subtasks, observation + worker-request text — spec
§1.4, §1.5, §1.11, §1.12, §3.

Every string here is phase-1 frozen. Prompt typography uses × − ÷ mod
(artifacts are ASCII); digits everywhere (D4); "zero-based" always; template
inputs are handles and public parameters only (no private-value provenance).
"""

from __future__ import annotations

from typing import Any

# Prompt typography (§1.4): real × (U+00D7), − (U+2212), ÷ (U+00F7).
TIMES, MINUS, DIVIDE = "×", "−", "÷"

MATH_FORMULAS = {
    "T1": f"(a {TIMES} b {MINUS} c) {DIVIDE} d",
    "T2": f"(a {TIMES} b + c) mod m",
    "T3": f"a {TIMES} b + c",
}
MATH_NAMES = {
    "T1": "a, b, c and d",
    "T2": "a, b, c and m",
    "T3": "a, b and c",
}
MATH_CODE_FORMULA = f"(a {TIMES} b + c) mod m"

GENERIC_SUBTASK = ("Complete the assigned step using the problem context, "
                   "any provided resource, and any previous results.")

ARTIFACT_FINAL_LINE = ("Respond with exactly one <artifact>...</artifact> "
                       "containing a single expression.")
DIRECT_FINAL_LINE = "Answer with a single integer on the final line."


def render_public_prompt(cell_id: str, renderer_id: str,
                         params: dict[str, Any]) -> str:
    """The §3 renderer string for one cell/subtype/renderer.

    `params` holds public parameters and handles only: H/H1/H2, key, field,
    p, q, sign, t, k, i, template, shape, branch_order as applicable.
    """
    p = params
    if cell_id == "lookup_atomic":
        return {
            "resource_first": (
                f"Resource {p['H']} contains keyed integer records. Return "
                f"the {p['field']} value recorded for {p['key']}."),
            "goal_first": (
                f"Return the {p['field']} value that {p['H']} records for "
                f"{p['key']}."),
            "bound_var": (
                f"Let v be {p['key']}'s {p['field']} in {p['H']}. Output v."),
        }[renderer_id]

    if cell_id == "math_atomic":
        formula = MATH_FORMULAS[p["template"]]
        names = MATH_NAMES[p["template"]]
        return {
            "resource_first": (
                f"{p['H']} contains integers {names}. Evaluate `{formula}` "
                f"exactly."),
            "goal_first": (
                f"Return the exact value of `{formula}`, where {names} are "
                f"the integers recorded in {p['H']}."),
            "bound_var": (
                f"Let {names} be the integers in {p['H']}. Output "
                f"`{formula}`."),
        }[renderer_id]

    if cell_id == "code_atomic":
        if p["shape"] == "count":
            return {
                "resource_first": (
                    f"From the integer sequence in {p['H']}, remove later "
                    f"occurrences of repeated values and count the values "
                    f"greater than {p['t']}."),
                "goal_first": (
                    f"Return how many values exceed {p['t']} in the sequence "
                    f"obtained from {p['H']} by removing later occurrences "
                    f"of repeated values."),
                "bound_var": (
                    f"Let s be the sequence in {p['H']} after removing later "
                    f"occurrences of repeated values. Output the count of "
                    f"values in s greater than {p['t']}."),
            }[renderer_id]
        return {
            "resource_first": (
                f"From the integer sequence in {p['H']}, remove later "
                f"occurrences of repeated values, rotate the remaining "
                f"sequence left by {p['k']} positions, and return the value "
                f"at zero-based index {p['i']}."),
            "goal_first": (
                f"Return the value at zero-based index {p['i']} of the "
                f"sequence obtained from {p['H']} by removing later "
                f"occurrences of repeated values and rotating it left by "
                f"{p['k']} positions."),
            "bound_var": (
                f"Let s be the sequence in {p['H']} after removing later "
                f"occurrences of repeated values and rotating left by "
                f"{p['k']} positions. Output the value of s at zero-based "
                f"index {p['i']}."),
        }[renderer_id]

    if cell_id == "lookup_math":
        if p["sign"] == "-":
            return {
                "resource_first": (
                    f"Retrieve {p['key']}'s {p['field']} from {p['H']}. "
                    f"Return {p['p']} times that value minus {p['q']}."),
                "goal_first": (
                    f"Return the number obtained by subtracting {p['q']} "
                    f"from {p['p']} times {p['key']}'s {p['field']} recorded "
                    f"in {p['H']}."),
                "bound_var": (
                    f"Let x be {p['key']}'s {p['field']} in {p['H']}. Output "
                    f"`{p['p']}x {MINUS} {p['q']}`."),
            }[renderer_id]
        return {
            "resource_first": (
                f"Retrieve {p['key']}'s {p['field']} from {p['H']}. Return "
                f"{p['p']} times that value plus {p['q']}."),
            "goal_first": (
                f"Return the number obtained by adding {p['q']} to {p['p']} "
                f"times {p['key']}'s {p['field']} recorded in {p['H']}."),
            "bound_var": (
                f"Let x be {p['key']}'s {p['field']} in {p['H']}. Output "
                f"`{p['p']}x + {p['q']}`."),
        }[renderer_id]

    if cell_id == "math_code":
        return {
            "resource_first": (
                f"{p['H1']} contains integers a, b, c and m. Compute "
                f"`{MATH_CODE_FORMULA}`. Use the result as a zero-based "
                f"index into the sequence in {p['H2']} and return the "
                f"selected integer."),
            "goal_first": (
                f"Return the integer found in {p['H2']} at the zero-based "
                f"index given by `{MATH_CODE_FORMULA}`, where a, b, c and m "
                f"are the integers in {p['H1']}."),
            "bound_var": (
                f"Let i = `{MATH_CODE_FORMULA}`, with a, b, c and m taken "
                f"from {p['H1']}. Output the value of the sequence in "
                f"{p['H2']} at zero-based index i."),
        }[renderer_id]

    if cell_id == "fork_join":
        if p["branch_order"] == "lookup_first":
            return {
                "resource_first": (
                    f"Retrieve {p['key']}'s {p['field']} from {p['H1']}. "
                    f"Separately, remove later occurrences of repeated "
                    f"values from the integer sequence in {p['H2']} and "
                    f"count the values greater than {p['t']}. Return the "
                    f"product of the two results plus {p['q']}."),
                "goal_first": (
                    f"Return {p['q']} plus the product of two values: "
                    f"{p['key']}'s {p['field']} recorded in {p['H1']}, and "
                    f"the count of values greater than {p['t']} after "
                    f"removing later occurrences of repeated values from "
                    f"the sequence in {p['H2']}."),
                "bound_var": (
                    f"Let x be {p['key']}'s {p['field']} in {p['H1']}. Let y "
                    f"be the count of values greater than {p['t']} in the "
                    f"sequence from {p['H2']} after removing later "
                    f"occurrences of repeated values. Output "
                    f"`x {TIMES} y + {p['q']}`."),
            }[renderer_id]
        return {
            "resource_first": (
                f"Remove later occurrences of repeated values from the "
                f"integer sequence in {p['H2']} and count the values "
                f"greater than {p['t']}. Separately, retrieve {p['key']}'s "
                f"{p['field']} from {p['H1']}. Return the product of the "
                f"two results plus {p['q']}."),
            "goal_first": (
                f"Return {p['q']} plus the product of two values: the count "
                f"of values greater than {p['t']} after removing later "
                f"occurrences of repeated values from the sequence in "
                f"{p['H2']}, and {p['key']}'s {p['field']} recorded in "
                f"{p['H1']}."),
            "bound_var": (
                f"Let x be the count of values greater than {p['t']} in the "
                f"sequence from {p['H2']} after removing later occurrences "
                f"of repeated values. Let y be {p['key']}'s {p['field']} in "
                f"{p['H1']}. Output `x {TIMES} y + {p['q']}`."),
        }[renderer_id]

    raise ValueError(f"unknown cell_id {cell_id!r}")


# --- §3: reference subtasks (tool-neutral), keyed by semantic node ----------

def reference_subtasks(cell_id: str, params: dict[str, Any]) -> dict[str, str]:
    """Semantic node id -> frozen reference subtask string."""
    p = params
    lookup_st = (f"Retrieve {p.get('key')}'s {p.get('field')} value from the "
                 f"requested resource.")
    if cell_id == "lookup_atomic":
        return {"n1": lookup_st}
    if cell_id == "math_atomic":
        formula = MATH_FORMULAS[p["template"]]
        return {"n1": (f"Evaluate `{formula}` exactly using the integers in "
                       f"the requested resource.")}
    if cell_id == "code_atomic":
        return {"n1": _code_subtask(p["shape"], p)}
    if cell_id == "lookup_math":
        tail = f"subtract {p['q']}." if p["sign"] == "-" else f"add {p['q']}."
        return {"n1": lookup_st,
                "n2": f"Multiply step_1 by {p['p']}, then {tail}"}
    if cell_id == "math_code":
        return {
            "n1": (f"Evaluate `{MATH_CODE_FORMULA}` exactly using the "
                   f"integers in the requested resource."),
            "n2": ("Return the value at zero-based index step_1 in the "
                   "integer sequence from the requested resource."),
        }
    if cell_id == "fork_join":
        return {
            "n1": lookup_st,
            "n2": _code_subtask("count", p),
            "n3": f"Multiply step_1 by step_2, then add {p['q']}.",
        }
    raise ValueError(f"unknown cell_id {cell_id!r}")


def _code_subtask(shape: str, p: dict[str, Any]) -> str:
    if shape == "count":
        return (f"Remove later occurrences of repeated values from the "
                f"integer sequence in the requested resource and count the "
                f"values greater than {p['t']}.")
    return (f"Remove later occurrences of repeated values from the integer "
            f"sequence in the requested resource, rotate the remaining "
            f"sequence left by {p['k']} positions, and return the value at "
            f"zero-based index {p['i']}.")


# §1.11/D12: frozen contracted two-call shortcut subtasks (fork_join).
def two_call_subtasks(orientation: str, params: dict[str, Any]) -> list[str]:
    p = params
    if orientation == "lookup_first":
        return [
            (f"Retrieve {p['key']}'s {p['field']} value from the requested "
             f"resource."),
            (f"Remove later occurrences of repeated values from the integer "
             f"sequence in the requested resource, count the values greater "
             f"than {p['t']}, multiply that count by step_1, and add "
             f"{p['q']}."),
        ]
    if orientation == "code_first":
        return [
            (f"Remove later occurrences of repeated values from the integer "
             f"sequence in the requested resource and count the values "
             f"greater than {p['t']}."),
            (f"Retrieve {p['key']}'s {p['field']} value from the requested "
             f"resource, multiply it by step_1, and add {p['q']}."),
        ]
    raise ValueError(f"unknown orientation {orientation!r}")


# --- §1.5: Stage-0C/2 policy observation (frozen skeleton) ------------------

def render_observation(public_prompt: str, manifest: list[str],
                       steps: list[dict[str, Any]],
                       visible_payload_texts: list[str] | None = None) -> str:
    """Conductor-side observation. Steps are dicts with keys
    `resource` (handle or None), `access` ("none" | "all"), `subtask`,
    ordered by workflow position (`positions` order)."""
    lines = ["Problem:", public_prompt]
    if visible_payload_texts is not None:  # §1.12 visible condition
        lines += ["", "Resources:"]
        lines.append("\n\n".join(visible_payload_texts))
    lines += ["", f"Resources available: {', '.join(manifest)}", "", "Steps:"]
    for idx, step in enumerate(steps, start=1):
        resource = step["resource"] if step["resource"] is not None else "none"
        previous = "all" if step["access"] == "all" else "none"
        lines.append(f"{idx}. (resource: {resource}; previous results: "
                     f"{previous}) {step['subtask']}")
    lines += ["", "Choose one worker for each step."]
    return "\n".join(lines)


# --- §1.5: canonical worker request (byte-stable) ---------------------------

def build_worker_request(public_prompt: str, subtask: str | None,
                         resource_text: str | None = None,
                         resources_texts: list[str] | None = None,
                         previous_results: dict[int, int] | None = None,
                         direct: bool = False) -> str:
    """Canonical user-message bytes: blocks in fixed order, each present or
    omitted whole, one blank line between blocks, LF, no trailing whitespace.

    `resources_texts` is the harness-only plural block (B3/B5, §1.11).
    `direct=True` swaps the artifact final line for the answer-line protocol.
    """
    if resource_text is not None and resources_texts is not None:
        raise ValueError("Resource and Resources blocks are exclusive")
    blocks = [f"Problem:\n{public_prompt}"]
    if subtask is not None:  # B1/B3 direct arms carry no Task block (§1.11)
        blocks.append(f"Task:\n{subtask}")
    if resource_text is not None:
        blocks.append(f"Resource:\n{resource_text}")
    if resources_texts is not None:
        blocks.append("Resources:\n" + "\n\n".join(resources_texts))
    if previous_results is not None:
        result_lines = "\n".join(
            f"step_{k} = {v}" for k, v in sorted(previous_results.items()))
        blocks.append(f"Previous results:\n{result_lines}")
    blocks.append(DIRECT_FINAL_LINE if direct else ARTIFACT_FINAL_LINE)
    return "\n\n".join(blocks)
