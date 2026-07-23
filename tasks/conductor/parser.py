"""Action parsing — spec §1.5 routing schema; plan contracts 1–2.

The 0.0/0.5 boundary principle (plan contract 4): anything rejected here is
a malformed action string (reward 0.0). A schema-valid action that fails in
the world (unknown handle, worker failure, wrong answer) is the executor's
0.5 path, never this module's.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .types import LEGAL_ACCESS_PATTERNS, is_utf8_encodable
from .workerpool import WORKER_IDS


class ActionSchemaError(ValueError):
    """Malformed action string → reward 0.0."""


def _require_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActionSchemaError(f"expected JSON integer, got {value!r}")
    return value


def _require_text(value: object, field: str) -> str:
    """Strings that survive JSON decoding but cannot be encoded as UTF-8
    (a `\\ud800` escape decodes to a lone surrogate) would fail later in
    request rendering or cache-key encoding; reject them here, where the
    failure is scored as a malformed action rather than aborting."""
    if not isinstance(value, str):
        raise ActionSchemaError(f"{field} must be a string")
    if not is_utf8_encodable(value):
        raise ActionSchemaError(f"{field} is not UTF-8 encodable")
    return value


def _load_action_json(completion: str) -> object:
    if not is_utf8_encodable(completion):
        raise ActionSchemaError("action string is not UTF-8 encodable")
    try:
        return json.loads(completion.strip())
    except json.JSONDecodeError as exc:
        raise ActionSchemaError(f"invalid JSON: {exc}") from exc


def parse_routing_action(completion: str, num_steps: int) -> list[int]:
    """§1.5 routing-action schema as amended by 106_s §6.1: the policy
    emits `{"worker_ids": [w_1, …, w_S]}` and nothing else.

    Extra fields, wrong types, wrong length, non-integer entries, or ids
    outside the registered worker pool are schema violations (the action
    space is the enumerated 4^S assignment set); duplicates are
    permitted.
    """
    obj = _load_action_json(completion)
    if not isinstance(obj, dict) or set(obj) != {"worker_ids"}:
        raise ActionSchemaError("action must be exactly {\"worker_ids\": […]}")
    ids = obj["worker_ids"]
    if not isinstance(ids, list) or len(ids) != num_steps:
        raise ActionSchemaError(f"worker_ids must be a length-{num_steps} array")
    out = []
    for w in ids:
        w = _require_int(w)
        if w not in WORKER_IDS:
            raise ActionSchemaError(f"worker id {w} outside {set(WORKER_IDS)}")
        out.append(w)
    return out


# --- full workflow JSON (Stage 4 action space; parsed at 0A) ----------------

@dataclass(frozen=True)
class WorkflowStep:
    subtask: str
    worker_id: int
    resource: str | None
    access: str  # "none" | "all"


@dataclass(frozen=True)
class WorkflowAction:
    steps: tuple[WorkflowStep, ...]


_STEP_KEYS = {"subtask", "worker_id", "resource", "access"}
MAX_STEPS = 3  # plan contract 2: fixed cap on total calls (v0)


def parse_workflow_action(completion: str) -> WorkflowAction:
    """Full workflow JSON: ≤3 steps, legal v0 access pattern, ≤1 resource
    per step, no duplicate handles, extra fields rejected (never ignored)."""
    obj = _load_action_json(completion)
    if not isinstance(obj, dict) or set(obj) != {"steps"}:
        raise ActionSchemaError("action must be exactly {\"steps\": […]}")
    raw_steps = obj["steps"]
    if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= MAX_STEPS:
        raise ActionSchemaError(f"steps must hold 1–{MAX_STEPS} entries")
    steps = []
    for raw in raw_steps:
        if not isinstance(raw, dict) or set(raw) != _STEP_KEYS:
            raise ActionSchemaError(f"step keys must be exactly {_STEP_KEYS}")
        subtask = _require_text(raw["subtask"], "subtask")
        worker_id = _require_int(raw["worker_id"])
        if worker_id not in WORKER_IDS:
            raise ActionSchemaError(
                f"worker id {worker_id} outside {set(WORKER_IDS)}")
        resource = raw["resource"]
        if resource is not None:
            resource = _require_text(resource, "resource")
        if raw["access"] not in ("none", "all"):
            raise ActionSchemaError("access must be \"none\" or \"all\"")
        steps.append(WorkflowStep(subtask=subtask, worker_id=worker_id,
                                  resource=resource, access=raw["access"]))
    access_pattern = tuple(s.access for s in steps)
    if access_pattern != LEGAL_ACCESS_PATTERNS[len(steps)]:
        raise ActionSchemaError(
            f"illegal v0 access pattern {access_pattern}")
    handles = [s.resource for s in steps if s.resource is not None]
    if len(set(handles)) != len(handles):
        raise ActionSchemaError("duplicate resource handles")
    return WorkflowAction(steps=tuple(steps))


def routing_to_workflow(worker_ids: list[int],
                        reference_steps: list[dict]) -> WorkflowAction:
    """Stages 0C/2: the harness supplies topology, subtasks, resources, and
    access from the reference workflow; the policy contributes worker_ids
    only (plan contract 1)."""
    if len(worker_ids) != len(reference_steps):
        raise ActionSchemaError("worker_ids length != step count")
    return WorkflowAction(steps=tuple(
        WorkflowStep(subtask=step["subtask"], worker_id=w,
                     resource=step["resource"], access=step["access"])
        for w, step in zip(worker_ids, reference_steps)))
