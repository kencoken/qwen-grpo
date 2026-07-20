"""Reference-free workflow execution and the executor/scorer split — plan
contracts 2, 4, 5; spec §1.7, §1.9; Stage 0B wave batching + traces.

`execute_workflow` receives neither the reference graph nor the gold answer
(strip test); `score_terminal` alone reads the gold. The worker interface is
injected, so CPU tests run against scripted fakes.

Stage 0B adds `execute_workflow_batch`: many workflows executed in waves
grouped by worker × depth (depth = workflow position), one batched
generation per worker per wave, with optional JSONL tracing under
`runs/<run_name>/traces/`. `execute_workflow` is the single-item case of
the same code path, so both share one semantics (and the 0A acceptance
battery pins it). Infrastructure failures raise; nothing degrades to a
reward.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from . import contract, render
from .parser import WorkflowAction
from .resources import InstanceRegistry
from .tools import Binding
from .types import InfrastructureError, WorkerResult

WorkerCall = Callable[[int, str], str]
# Batched interface: (worker_id, requests) -> one record per request, in
# order. Records carry `.completion` plus, when produced by a Runtime,
# the §1.6 telemetry fields (runtime.CallRecord).
BatchWorkerCall = Callable[[int, list[str]], list[Any]]


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


@dataclass(frozen=True)
class WorkflowItem:
    """One workflow in a batch. `item_id` is the stable trace id — for
    instances, the `render_instance_id` (§1.13), suffixed by the caller
    when one instance is executed more than once in a run."""
    item_id: str
    action: WorkflowAction
    public_prompt: str
    registry: InstanceRegistry
    overrides: Mapping[int, int] = field(default_factory=dict)
    pseudo_workers: Mapping[int, PseudoWorker] = field(default_factory=dict)


def _step_failed(record: StepRecord) -> bool:
    return record.result is None or record.result.status != "success"


@dataclass
class _PendingCall:
    item_index: int
    position: int     # 1-based workflow position (= this wave)
    request: str
    binding: Binding


def execute_workflow_batch(items: list[WorkflowItem],
                           batch_worker_call: BatchWorkerCall,
                           trace: "TraceWriter | None" = None
                           ) -> list[ExecutionResult]:
    """Execute schema-valid actions in worker×depth waves.

    Wave `p` gathers position `p` of every workflow, applies the §1.7/§1.9
    pre-call rules per item, batches the surviving real calls by worker id
    (item order within each batch), executes tools per call, and threads
    values/overrides exactly as the sequential contract does. Per-item
    semantics are position-sequential by construction, so batching is
    invisible to any single workflow.
    """
    ids = [item.item_id for item in items]
    if len(set(ids)) != len(ids):
        raise InfrastructureError("duplicate item_id in batch")
    records: list[list[StepRecord]] = [[] for _ in items]
    wire_values: list[dict[int, int]] = [{} for _ in items]

    max_steps = max((len(item.action.steps) for item in items), default=0)
    for position in range(1, max_steps + 1):
        pending: list[_PendingCall] = []
        for index, item in enumerate(items):
            if position > len(item.action.steps):
                continue
            step = item.action.steps[position - 1]

            # §1.7 propagation: any failed earlier step blocks access=all.
            if step.access == "all" and any(_step_failed(r)
                                            for r in records[index]):
                rec = StepRecord(position, step.worker_id,
                                 contract.dependency_blocked_result(),
                                 None, None, None, False)
                records[index].append(rec)
                _trace_step(trace, item, rec, None)
                continue

            resource_text = None
            binding_resources = {}
            if step.resource is not None:
                resource = item.registry.resolve(step.resource)
                if resource is None:  # foreign/unknown handle: world failure
                    rec = StepRecord(position, step.worker_id, None,
                                     "unknown_handle", None, None, False)
                    records[index].append(rec)
                    _trace_step(trace, item, rec, None)
                    continue
                resource_text = item.registry.payload_text(step.resource)
                binding_resources = {step.resource: resource}

            previous = (dict(wire_values[index]) if step.access == "all"
                        else None)
            request = render.build_worker_request(
                item.public_prompt, step.subtask,
                resource_text=resource_text, previous_results=previous)
            binding = Binding(resources=binding_resources,
                              steps=previous or {})

            if position in item.pseudo_workers:
                result = item.pseudo_workers[position](request)
                if not result.synthetic:
                    raise InfrastructureError("pseudo-worker result must "
                                              "carry synthetic=true")
                rec = _finish_step(item, position, step, result, request,
                                   None, wire_values[index])
                records[index].append(rec)
                _trace_step(trace, item, rec, None)
            else:
                pending.append(_PendingCall(index, position, request,
                                            binding))

        # One batched generation per worker id for this wave.
        by_worker: dict[int, list[_PendingCall]] = {}
        for call in pending:
            step = items[call.item_index].action.steps[call.position - 1]
            by_worker.setdefault(step.worker_id, []).append(call)
        for worker_id in sorted(by_worker):
            calls = by_worker[worker_id]
            call_records = batch_worker_call(
                worker_id, [call.request for call in calls])
            if len(call_records) != len(calls):
                raise InfrastructureError(
                    f"worker {worker_id}: {len(call_records)} records for "
                    f"{len(calls)} requests")
            for call, call_record in zip(calls, call_records):
                item = items[call.item_index]
                step = item.action.steps[call.position - 1]
                result = contract.run_worker_output(
                    step.worker_id, call_record.completion, call.binding)
                rec = _finish_step(item, call.position, step, result,
                                   call.request, call_record.completion,
                                   wire_values[call.item_index])
                records[call.item_index].append(rec)
                _trace_step(trace, item, rec, call_record)

    results = []
    for index, item in enumerate(items):
        sink = records[index][-1]
        terminal = (sink.result.value
                    if sink.result is not None
                    and sink.result.status == "success" else None)
        results.append(ExecutionResult(terminal=terminal,
                                       steps=records[index]))
    return results


def _finish_step(item: WorkflowItem, position: int, step: Any,
                 result: WorkerResult, request: str | None,
                 completion: str | None,
                 wire_values: dict[int, int]) -> StepRecord:
    """Post-call bookkeeping shared by real and pseudo calls: §1.9 wire
    replacement in both channels for every downstream consumer."""
    override_applied = False
    if result.status == "success":
        value = result.value
        assert value is not None
        if position in item.overrides:
            value = item.overrides[position]  # §1.9 wire replacement
            override_applied = True
        wire_values[position] = value
    return StepRecord(position, step.worker_id, result, None, request,
                      completion, override_applied)


def execute_workflow(action: WorkflowAction, public_prompt: str,
                     registry: InstanceRegistry, worker_call: WorkerCall,
                     overrides: dict[int, int] | None = None,
                     pseudo_workers: dict[int, PseudoWorker] | None = None
                     ) -> ExecutionResult:
    """Execute a schema-valid action. `overrides` maps workflow position j to
    the §1.9 mediator replacement: `step_j` is replaced in both channels (the
    context line and the host-side binding) for every downstream consumer.
    `pseudo_workers` maps positions to §1.11 diagnostic substitutes.

    Single-item case of `execute_workflow_batch` (one wave per position,
    one call per wave, preserving the sequential call order)."""

    @dataclass(frozen=True)
    class _BareRecord:
        completion: str

    def adapter(worker_id: int, requests: list[str]) -> list[_BareRecord]:
        return [_BareRecord(worker_call(worker_id, request))
                for request in requests]

    item = WorkflowItem(item_id="single", action=action,
                        public_prompt=public_prompt, registry=registry,
                        overrides=overrides or {},
                        pseudo_workers=pseudo_workers or {})
    return execute_workflow_batch([item], adapter)[0]


# --- JSONL traces (Stage 0B) ------------------------------------------------

TRACE_SCHEMA_VERSION = 1


class TraceWriter:
    """JSONL step traces under `runs/<run_name>/traces/` with a manifest
    embedding the versioned runtime profile and all three fingerprint
    scopes (plan §8). One JSON line per step record, keyed by the stable
    `item_id` + position."""

    def __init__(self, run_name: str, runtime: Any,
                 base_dir: str | Path = "runs") -> None:
        self.trace_dir = Path(base_dir) / run_name / "traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.trace_dir / "manifest.json"
        self._trace_path = self.trace_dir / "steps.jsonl"
        if self._trace_path.exists():
            raise InfrastructureError(
                f"{self._trace_path} already exists; traces are append-only "
                "within one run and never silently merged across runs")
        self._manifest = {
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "run_name": run_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_profile": runtime.profile,
            "runtime_profile_fingerprint":
                runtime.runtime_profile_fingerprint,
            "worker_visible_fingerprint": runtime.worker_visible_fingerprint,
            "endpoint_fingerprints": dict(runtime.endpoint_fingerprints),
            "steps_written": 0,
            "closed": False,
        }
        self._write_manifest()
        self._file = self._trace_path.open("x", encoding="utf-8")
        self._steps_written = 0

    def _write_manifest(self) -> None:
        self._manifest_path.write_text(
            json.dumps(self._manifest, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    def write_step(self, item_id: str, record: StepRecord,
                   call_record: Any | None) -> None:
        result = record.result
        line = {
            "item_id": item_id,
            "position": record.position,
            "worker_id": record.worker_id,
            "world_failure": record.world_failure,
            "override_applied": record.override_applied,
            "status": result.status if result else None,
            "value": result.value if result else None,
            "rejection_code": result.rejection_code if result else None,
            "artifact_valid": result.artifact_valid if result else None,
            "tool_executed": result.tool_executed if result else None,
            "synthetic": result.synthetic if result else None,
            "request": record.request,
            "completion": record.completion,
            # §1.6 backend telemetry — null for pseudo-workers and world
            # failures (no call made) and for non-runtime worker adapters.
            "finish_reason": getattr(call_record, "finish_reason", None),
            "generated_tokens": getattr(call_record, "generated_tokens",
                                        None),
            "generation_hit_token_cap": getattr(
                call_record, "generation_hit_token_cap", None),
            "cache_hit": getattr(call_record, "cache_hit", None),
            "request_sha256": getattr(call_record, "request_sha256", None),
        }
        self._file.write(json.dumps(line, sort_keys=True) + "\n")
        self._file.flush()
        self._steps_written += 1

    def close(self) -> None:
        if not self._manifest["closed"]:
            self._file.close()
            self._manifest["steps_written"] = self._steps_written
            self._manifest["closed"] = True
            self._write_manifest()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _trace_step(trace: TraceWriter | None, item: WorkflowItem,
                record: StepRecord, call_record: Any | None) -> None:
    if trace is not None:
        trace.write_step(item.item_id, record, call_record)


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
