"""Reference-free workflow execution and the executor/scorer split — plan
contracts 2, 4, 5; spec §1.7, §1.9.

`execute_workflow` receives neither the reference graph nor the gold answer
(strip test); `score_terminal` alone reads the gold. The worker interface is
injected (`worker_call(worker_id, request) -> completion`), so CPU tests run
against scripted fakes; Stage 0B layers the NF4 pool, wave batching, traces,
and caching on top of this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from . import contract, render
from .parser import WorkflowAction
from .resources import InstanceRegistry
from .tools import Binding
from .types import InfrastructureError, WorkerResult

WorkerCall = Callable[[int, str], str]


class PseudoWorker(Protocol):
    def __call__(self, request: str) -> WorkerResult: ...


@dataclass
class StepRecord:
    position: int                # 1-based workflow position
    worker_id: int
    result: WorkerResult | None  # None => world failure before any call
    world_failure: str | None    # e.g. "unknown_handle"
    request: str | None
    completion: str | None
    override_applied: bool


@dataclass
class ExecutionResult:
    terminal: int | None  # sink value; None unless the sink succeeded
    steps: list[StepRecord]


def _step_failed(record: StepRecord) -> bool:
    return record.result is None or record.result.status != "success"


def execute_workflow(action: WorkflowAction, public_prompt: str,
                     registry: InstanceRegistry, worker_call: WorkerCall,
                     overrides: dict[int, int] | None = None,
                     pseudo_workers: dict[int, PseudoWorker] | None = None
                     ) -> ExecutionResult:
    """Execute a schema-valid action. `overrides` maps workflow position j to
    the §1.9 mediator replacement: `step_j` is replaced in both channels (the
    context line and the host-side binding) for every downstream consumer.
    `pseudo_workers` maps positions to §1.11 diagnostic substitutes."""
    overrides = overrides or {}
    pseudo_workers = pseudo_workers or {}
    records: list[StepRecord] = []
    wire_values: dict[int, int] = {}  # position -> value downstream steps see

    for position, step in enumerate(action.steps, start=1):
        # §1.7 propagation: any failed earlier step blocks access=all steps.
        if step.access == "all" and any(_step_failed(r) for r in records):
            records.append(StepRecord(position, step.worker_id,
                                      contract.dependency_blocked_result(),
                                      None, None, None, False))
            continue

        resource_text = None
        binding_resources = {}
        if step.resource is not None:
            resource = registry.resolve(step.resource)
            if resource is None:  # foreign/unknown handle: world failure
                records.append(StepRecord(position, step.worker_id, None,
                                          "unknown_handle", None, None,
                                          False))
                continue
            resource_text = registry.payload_text(step.resource)
            binding_resources = {step.resource: resource}

        previous = dict(wire_values) if step.access == "all" else None
        request = render.build_worker_request(
            public_prompt, step.subtask, resource_text=resource_text,
            previous_results=previous)
        binding = Binding(resources=binding_resources,
                          steps=previous or {})

        if position in pseudo_workers:
            result = pseudo_workers[position](request)
            if not result.synthetic:
                raise InfrastructureError("pseudo-worker result must carry "
                                          "synthetic=true")
            completion = None
        else:
            completion = worker_call(step.worker_id, request)
            result = contract.run_worker_output(step.worker_id, completion,
                                                binding)

        override_applied = False
        if result.status == "success":
            value = result.value
            assert value is not None
            if position in overrides:
                value = overrides[position]  # §1.9 wire replacement
                override_applied = True
            wire_values[position] = value
        records.append(StepRecord(position, step.worker_id, result,
                                  None, request, completion,
                                  override_applied))

    sink = records[-1]
    terminal = (sink.result.value
                if sink.result is not None
                and sink.result.status == "success" else None)
    return ExecutionResult(terminal=terminal, steps=records)


# --- scorer (the only reader of gold_answer; plan contracts 4–5) ------------

def score_terminal(terminal: int | None, gold_answer: int) -> float:
    """0.5 = well-formed action that failed in the world; 1.0 = correct."""
    return 1.0 if terminal == gold_answer else 0.5


def reward_for_completion(parse: Callable[[], Any],
                          execute: Callable[[Any], int | None],
                          gold_answer: int) -> float:
    """Reward table (plan contract 4): malformed action string → 0.0;
    schema-valid but world-failed → 0.5; correct terminal → 1.0."""
    from .parser import ActionSchemaError
    try:
        action = parse()
    except ActionSchemaError:
        return 0.0
    return score_terminal(execute(action), gold_answer)
