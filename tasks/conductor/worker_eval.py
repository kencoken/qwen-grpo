"""Worker-evaluation integrity — Stage 0B follow-up (plan 81_f).

The governing contract (81_f §1): given a worker result, identify the
exact request and execution configuration that produced it, score the
intended reference node independently, and pair it across renderers.

- Provenance (Tranche A): manifests bind actual prompt bytes and runtime
  facts, never labels; the no-op cache plus one-message calls guarantee
  one physical generation per planned case; every call row carries the
  exact rendered request and completion with SHA-256 digests.
- Isolated node scoring (Tranche B): `WorkerEvalCase` (executable, no
  targets) and `NodeLabel` (targets, joined post-hoc by case_id); gold
  predecessor values through the ordinary request channel; strict
  correctness over the full scheduled denominator.
- Crossing/diagnostics (Tranche C): exact paired renderer support;
  composed workflows through a StepRecord adapter with disjoint
  scheduled/called/blocked/world/synthetic categories; a derived
  counts-only summary; a strict regenerating loader; and a narrow
  two-run manifest comparison.

Everything here is descriptive Stage-0B/D16 evidence. No artifact this
module writes can emit a Stage-1 construction or qualification gate
result (§5.6); those gates remain unavailable until their own reviewed
implementations exist.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

from . import contract, executor, parser, program
from .agreement import ENDPOINT_FOR_OP
from .profiles import DEFAULT_PROFILE, ProfileError, canonical_json, \
    profile_version
from .prompts import PromptBundle, resolve_prompts
from .render import ARTIFACT_FINAL_LINE, TASK_LAST_FINAL_LINE
from .resources import InstanceRegistry
from .runtime import CallRecord, Runtime, runtime_profile_fingerprint
from .tools import Binding, ToolRejection, binding_sha256
from .types import (
    CELL_IDS, ENDPOINT_NAMES, RENDERER_IDS, SYNTAX_REJECTION_CODES,
    InfrastructureError, Resource, WorkerResult, is_utf8_encodable,
)

WORKER_EVAL_SCHEMA_VERSION = 1
GENERATION_POLICY_SINGLETON = "singleton-v1"
CACHE_SOURCE_DISABLED = "disabled"
ENDPOINT_SCHEDULE_VERSION = "d16-operator-aligned-v1"
CALL_ROLE_ON_CONTRACT = "on_contract_reference"
SCORER_VERSION = "worker-eval-scorer-v1"

_ENDPOINT_ID = {name: eid for eid, name in ENDPOINT_NAMES.items()}


# --- cache-disabled generation (81_f §6.5) ----------------------------------

class NullCache:
    """Explicit no-op cache: every lookup misses and nothing is stored, so
    every planned evaluator case is exactly one physical generation. The
    scientific evaluator never touches the Stage-0B completion cache."""

    def lookup(self, worker_visible_fp: str, endpoint_fp: str,
               request: bytes) -> None:
        return None

    def store(self, worker_visible_fp: str, endpoint_fp: str,
              request: bytes, generation: Any) -> None:
        pass

    def __len__(self) -> int:
        return 0

    def close(self) -> None:
        pass


def singleton_call(runtime: Runtime, endpoint_name: str,
                   user_message: str) -> CallRecord:
    """One physical generation for one case: one request per
    `worker_call_batch` call makes miss deduplication vacuous and the
    microbatch a single unpadded sequence (81_f §6.2). The cache must
    *be* the no-op cache before generation (82_s finding 3): a cold
    `CompletionCache` would miss, store, and mislabel every row
    `disabled` — `build_runtime`'s default cache is one forgotten
    argument away."""
    if not isinstance(runtime.cache, NullCache):
        raise InfrastructureError(
            f"scientific singleton calls require the no-op cache, got "
            f"{type(runtime.cache).__name__}; build the runtime with "
            "cache=NullCache()")
    (record,) = runtime.worker_call_batch(endpoint_name, [user_message])
    if record.cache_hit:
        raise InfrastructureError(
            "singleton evaluator call was served from cache; scientific "
            "runs must use the disabled cache (81_f §5.3)")
    return record


# --- request-contract binding (81_f §5.2) -----------------------------------

# The worker request contracts render.build_worker_request implements
# (92_s §2.2). A key resolves to exact content AND configures the
# builder; a metadata-only key is forbidden (84_s finding 3).
REQUEST_CONTRACTS: dict[str, dict[str, Any]] = {
    "worker-blocks-v0": {
        "builder": "render.build_worker_request",
        "builder_version": "specs-v0.8",
        "block_order": ["problem", "task", "resource", "previous_results",
                        "final_line"],
        "final_line": ARTIFACT_FINAL_LINE,
    },
    "worker-blocks-task-last-v1": {
        "builder": "render.build_worker_request",
        "builder_version": "specs-v0.8",
        "block_order": ["problem", "resource", "previous_results", "task",
                        "final_line"],
        "final_line": TASK_LAST_FINAL_LINE,
    },
}


def resolve_request_contract(key: str) -> dict[str, Any]:
    if key not in REQUEST_CONTRACTS:
        raise ProfileError(f"unknown request contract {key!r}; known: "
                           f"{sorted(REQUEST_CONTRACTS)}")
    spec = REQUEST_CONTRACTS[key]
    digest = hashlib.sha256(
        canonical_json(dict(spec)).encode("utf-8")).hexdigest()
    return {"key": key, "digest": digest, **copy.deepcopy(spec)}


# --- isolated node cases and labels (81_f §4.1, §4.3) ------------------------

@dataclass(frozen=True)
class WorkerEvalCase:
    """The executable half of one isolated node evaluation: everything the
    runtime and tools may see, nothing the scorer holds. `resources` and
    `steps` are immutable primitives (Resource payloads are frozen
    dataclasses over tuples); a fresh Binding is built from them at tool
    execution, so no caller-owned dictionary is ever retained."""
    case_id: str
    observation_id: str
    endpoint_name: str
    user_message: str
    resources: tuple[tuple[str, Resource], ...]  # ≤1 entry in v0
    steps: tuple[tuple[int, int], ...]           # (position, gold value)
    binding_sha256: str

    def binding(self) -> Binding:
        return Binding(resources=dict(self.resources),
                       steps=dict(self.steps))


@dataclass(frozen=True)
class NodeLabel:
    """The scoring half: joined to call rows by exact `case_id` only after
    execution. The expected value never enters an executable case."""
    case_id: str
    latent_program_id: str
    renderer_id: str
    cell_id: str
    node_id: str
    node_family: str        # the node's operator (seq_at, modular, ...)
    position: int
    call_role: str          # constant CALL_ROLE_ON_CONTRACT in this change
    predecessor_source: str  # "gold" | "none"
    expected_value: int


def endpoint_schedule(latent: Mapping[str, Any]) -> dict[str, str]:
    """The D16 operator-aligned schedule: node_id -> endpoint name, stored
    in stable semantic-node terms (action order comes from
    `reference_program.positions`, never the other way around — the
    code-first `fork_join` regression). Not a presumed gold assignment."""
    return {node["id"]: ENDPOINT_NAMES[ENDPOINT_FOR_OP[node["op"]]]
            for node in latent["reference_program"]["nodes"]}


def node_cases_for_latent(latent: Mapping[str, Any], renderers: list[str],
                          visibility: str,
                          request_contract_key: str = "worker-blocks-v0"
                          ) -> tuple[list[WorkerEvalCase], list[NodeLabel]]:
    """Isolated cases for every scheduled reference node of one latent
    (81_f §4.3): ordinary per-step requests, gold values for every
    permitted predecessor position, only the node's authorized resource."""
    registry = program.registry_from_json(latent["private_registry"])
    values = program.evaluate_reference(latent["reference_program"],
                                        registry)
    if values != latent["node_values"]:
        raise InfrastructureError(
            f"{latent['latent_program_id']}: stored node_values disagree "
            "with reference re-evaluation")
    steps = program.workflow_steps(latent)
    schedule = endpoint_schedule(latent)
    # Node family is the operator itself (82_s): worst-node-stratum
    # analysis needs seq_at vs seq_count, not the endpoint class, which
    # the endpoint column already carries.
    families = {node["id"]: node["op"]
                for node in latent["reference_program"]["nodes"]}
    cases, labels = [], []
    for renderer_id in renderers:
        inst = program.render_instance(latent, renderer_id, visibility)
        inst_registry = InstanceRegistry(inst["public_manifest"],
                                         inst["private_registry"])
        for position, step in enumerate(steps, start=1):
            node_id = step["node"]
            previous = ({k: values[steps[k - 1]["node"]]
                         for k in range(1, position)}
                        if step["access"] == "all" else None)
            user_message, binding = executor.build_worker_call(
                inst["public_prompt"], step["subtask"], step["resource"],
                inst_registry, previous, contract=request_contract_key)
            case_id = f"{inst['render_instance_id']}:{node_id}"
            cases.append(WorkerEvalCase(
                case_id=case_id,
                observation_id=inst["render_instance_id"],
                endpoint_name=schedule[node_id],
                user_message=user_message,
                resources=tuple(sorted(binding.resources.items())),
                steps=tuple(sorted(binding.steps.items())),
                binding_sha256=binding_sha256(binding)))
            labels.append(NodeLabel(
                case_id=case_id,
                latent_program_id=latent["latent_program_id"],
                renderer_id=renderer_id,
                cell_id=latent["cell_id"],
                node_id=node_id,
                node_family=families[node_id],
                position=position,
                call_role=CALL_ROLE_ON_CONTRACT,
                predecessor_source="gold" if previous else "none",
                expected_value=values[node_id]))
    return cases, labels


def _validate_population(population: Mapping[str, Any]) -> None:
    required = {"namespace", "per_cell", "renderers", "visibility"}
    if set(population) != required:
        raise ProfileError(f"population keys {sorted(population)} != "
                           f"required {sorted(required)}")
    renderers = list(population["renderers"])
    if (not renderers or len(set(renderers)) != len(renderers)
            or not set(renderers) <= set(RENDERER_IDS)):
        raise ProfileError(f"renderers must be distinct members of "
                           f"{RENDERER_IDS}, got {renderers}")
    per_cell = population["per_cell"]
    if not isinstance(per_cell, int) or isinstance(per_cell, bool) \
            or per_cell < 1:
        raise ProfileError(f"per_cell must be a positive integer, "
                           f"got {per_cell!r}")
    for cell in CELL_IDS:
        cap = program.namespace_cap(population["namespace"], cell)
        if per_cell > cap:
            raise ProfileError(
                f"namespace {population['namespace']!r} cell {cell}: "
                f"per_cell {per_cell} exceeds cap {cap}")


def build_node_cases(population: Mapping[str, Any],
                     endpoint_schedule_version: str =
                     ENDPOINT_SCHEDULE_VERSION,
                     request_contract_key: str = "worker-blocks-v0",
                     profile: Mapping[str, Any] | None = None
                     ) -> tuple[list[WorkerEvalCase], list[NodeLabel]]:
    """The full isolated-node plan for a registered population, in
    deterministic cell x index x renderer x position order."""
    if endpoint_schedule_version != ENDPOINT_SCHEDULE_VERSION:
        raise ProfileError(
            f"unknown endpoint schedule {endpoint_schedule_version!r}; "
            f"this evaluator implements {ENDPOINT_SCHEDULE_VERSION!r}")
    resolve_request_contract(request_contract_key)  # fail-closed key check
    _validate_population(population)
    renderers = list(population["renderers"])
    gen_profile = dict(profile) if profile is not None else DEFAULT_PROFILE
    cases, labels = [], []
    for cell in CELL_IDS:
        for index in range(population["per_cell"]):
            latent = program.generate_latent(
                cell, population["namespace"], index, gen_profile).latent
            latent_cases, latent_labels = node_cases_for_latent(
                latent, renderers, population["visibility"],
                request_contract_key)
            cases.extend(latent_cases)
            labels.extend(latent_labels)
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise InfrastructureError("duplicate case_id in population plan")
    return cases, labels


def case_identities(labels: list[NodeLabel]) -> dict[str, dict[str, Any]]:
    """Row-identity fields for the call writer, with the expected value
    deliberately excluded (81_f §4.1: rows carry join identity, never
    targets; labels reach only the scoring path)."""
    identities: dict[str, dict[str, Any]] = {}
    for label in labels:
        if label.case_id in identities:
            raise InfrastructureError(f"duplicate label {label.case_id}")
        identities[label.case_id] = {
            "latent_program_id": label.latent_program_id,
            "cell_id": label.cell_id,
            "renderer_id": label.renderer_id,
            "node_id": label.node_id,
            "position": label.position,
            "predecessor_source": label.predecessor_source,
        }
    return identities


# --- renderer crossing (81_f §4.5) -------------------------------------------

def check_renderer_support(labels: list[NodeLabel],
                           renderers: list[str]) -> None:
    """Exact paired support: every (latent_program_id, node_id) must have
    exactly one label per declared renderer. Missing, duplicate or extra
    support invalidates the run rather than skewing a marginal."""
    expected = sorted(renderers)
    seen: dict[tuple[str, str], list[str]] = {}
    for label in labels:
        seen.setdefault((label.latent_program_id, label.node_id),
                        []).append(label.renderer_id)
    bad = {key: sorted(rends) for key, rends in seen.items()
           if sorted(rends) != expected}
    if bad:
        shown = dict(sorted(bad.items())[:5])
        raise InfrastructureError(
            f"renderer support violated (expected {expected}) for "
            f"{len(bad)} latent/node pairs, e.g. {shown}")


# --- composed workflow mode (81_f §4.3 composed; §5.3 adapter) ---------------

@dataclass(frozen=True)
class WorkflowLabel:
    """Scoring half of one composed workflow: the final gold, joined by
    exact case_id (= render_instance_id) after execution."""
    case_id: str
    latent_program_id: str
    renderer_id: str
    cell_id: str
    final_gold: int


def build_workflow_plan(population: Mapping[str, Any],
                        endpoint_schedule_version: str =
                        ENDPOINT_SCHEDULE_VERSION,
                        request_contract_key: str = "worker-blocks-v0",
                        profile: Mapping[str, Any] | None = None
                        ) -> tuple[list[executor.WorkflowItem],
                                   list[WorkflowLabel],
                                   dict[tuple[str, int], dict[str, Any]]]:
    """Reference-routed workflow items for the population, plus labels and
    per-(case, position) row identities. Routing derives from the semantic
    endpoint schedule through `reference_program.positions`."""
    if endpoint_schedule_version != ENDPOINT_SCHEDULE_VERSION:
        raise ProfileError(
            f"unknown endpoint schedule {endpoint_schedule_version!r}; "
            f"this evaluator implements {ENDPOINT_SCHEDULE_VERSION!r}")
    resolve_request_contract(request_contract_key)
    _validate_population(population)
    gen_profile = dict(profile) if profile is not None else DEFAULT_PROFILE
    items, labels = [], []
    identities: dict[tuple[str, int], dict[str, Any]] = {}
    for cell in CELL_IDS:
        for index in range(population["per_cell"]):
            latent = program.generate_latent(
                cell, population["namespace"], index, gen_profile).latent
            steps = program.workflow_steps(latent)
            schedule = endpoint_schedule(latent)
            for renderer_id in population["renderers"]:
                inst = program.render_instance(latent, renderer_id,
                                               population["visibility"])
                registry = InstanceRegistry(inst["public_manifest"],
                                            inst["private_registry"])
                routing = [_ENDPOINT_ID[schedule[step["node"]]]
                           for step in steps]
                action = parser.routing_to_workflow(
                    routing, [{key: step[key] for key in
                               ("subtask", "resource", "access")}
                              for step in steps])
                case_id = inst["render_instance_id"]
                items.append(executor.WorkflowItem(
                    item_id=case_id, action=action,
                    public_prompt=inst["public_prompt"],
                    registry=registry,
                    request_contract=request_contract_key))
                labels.append(WorkflowLabel(
                    case_id=case_id,
                    latent_program_id=latent["latent_program_id"],
                    renderer_id=renderer_id,
                    cell_id=latent["cell_id"],
                    final_gold=inst["gold_answer"]))
                for position, step in enumerate(steps, start=1):
                    identities[(case_id, position)] = {
                        "latent_program_id": latent["latent_program_id"],
                        "cell_id": latent["cell_id"],
                        "renderer_id": renderer_id,
                        "node_id": step["node"],
                        "position": position,
                        "endpoint_name": schedule[step["node"]],
                        "predecessor_source": ("produced"
                                               if step["access"] == "all"
                                               else "none"),
                        "predecessor_positions": (
                            list(range(1, position))
                            if step["access"] == "all" else []),
                    }
    ids = [item.item_id for item in items]
    if len(set(ids)) != len(ids):
        raise InfrastructureError("duplicate workflow case_id in plan")
    return items, labels, identities


def make_uncalled_row(*, run_id: str, case_id: str, position: int,
                      identity: Mapping[str, Any], call_status: str,
                      result: WorkerResult | None,
                      world_failure: str | None) -> dict[str, Any]:
    """One scheduled-but-not-called row (§5.3 status-conditional schema):
    schedule identity and status only; request, generation and backend
    telemetry are null. Synthetic pseudo-worker output stays in the
    explicit WorkerResult fields."""
    return {
        "run_id": run_id,
        "case_id": case_id,
        "observation_id": case_id,
        "position": position,
        "latent_program_id": identity["latent_program_id"],
        "cell_id": identity["cell_id"],
        "renderer_id": identity["renderer_id"],
        "node_id": identity["node_id"],
        "endpoint_name": identity["endpoint_name"],
        "evaluation_mode": "composed",
        "predecessor_source": identity["predecessor_source"],
        "predecessor_positions": identity["predecessor_positions"],
        "call_status": call_status,
        "world_failure": world_failure,
        "user_message": None,
        "request_text": None,
        "request_sha256": None,
        "binding_sha256": None,
        "generation_ordinal": None,
        "physical_batch_size": None,
        "physical_batch_slot": None,
        "completion": None,
        "completion_sha256": None,
        "finish_reason": None,
        "generated_tokens": None,
        "generation_hit_token_cap": None,
        "envelope_outcome": None,
        "grammar_outcome": None,
        "status": result.status if result is not None else None,
        "value": result.value if result is not None else None,
        "rejection_code": (result.rejection_code
                           if result is not None else None),
        "artifact_valid": (result.artifact_valid
                           if result is not None else None),
        "tool_executed": (result.tool_executed
                          if result is not None else None),
        "cache_source": None,
    }


class _ComposedTraceAdapter:
    """The §5.3 StepRecord adapter: converts each executor step (plus its
    runtime CallRecord for real calls) into one calls.jsonl row. Duck-types
    the executor's trace interface; no second trace format exists."""

    def __init__(self, run_id: str, identities: Mapping[tuple[str, int],
                                                        Mapping[str, Any]],
                 writer: "RunWriter | None") -> None:
        self._run_id = run_id
        self._identities = identities
        self._writer = writer
        self._generation_ordinal = 0
        self.rows: list[dict[str, Any]] = []

    def write_step(self, item_id: str, record: executor.StepRecord,
                   call_record: Any | None) -> None:
        identity = self._identities[(item_id, record.position)]
        result = record.result
        if record.world_failure is not None:
            row = make_uncalled_row(
                run_id=self._run_id, case_id=item_id,
                position=record.position, identity=identity,
                call_status="pre_call_world_failure", result=None,
                world_failure=record.world_failure)
        elif result is not None and result.synthetic:
            row = make_uncalled_row(
                run_id=self._run_id, case_id=item_id,
                position=record.position, identity=identity,
                call_status="synthetic", result=result, world_failure=None)
        elif result is not None and result.status == "dependency_blocked":
            row = make_uncalled_row(
                run_id=self._run_id, case_id=item_id,
                position=record.position, identity=identity,
                call_status="dependency_blocked", result=result,
                world_failure=None)
        else:
            assert result is not None and call_record is not None
            row = make_called_row(
                run_id=self._run_id, case_id=item_id,
                observation_id=item_id, position=record.position,
                latent_program_id=identity["latent_program_id"],
                cell_id=identity["cell_id"],
                renderer_id=identity["renderer_id"],
                node_id=identity["node_id"],
                endpoint_name=identity["endpoint_name"],
                evaluation_mode="composed",
                predecessor_source=identity["predecessor_source"],
                predecessor_positions=identity["predecessor_positions"],
                generation_ordinal=self._generation_ordinal,
                user_message=record.request,
                binding_sha256=record.binding_sha256,
                record=call_record, result=result,
                stages=parse_stages(record.completion, result))
            self._generation_ordinal += 1
        if self._writer is not None:
            self._writer.write_call(row)
        self.rows.append(row)


def run_composed_workflows(runtime: Runtime,
                           population: Mapping[str, Any],
                           writer: "RunWriter | None",
                           endpoint_schedule_version: str =
                           ENDPOINT_SCHEDULE_VERSION,
                           request_contract_key: str = "worker-blocks-v0",
                           profile: Mapping[str, Any] | None = None
                           ) -> tuple[list[dict[str, Any]],
                                      list[WorkflowLabel]]:
    """Execute the reference-routed workflows normally (produced
    predecessor values, ordinary dependency propagation) with singleton
    cache-disabled generation. Measures compounding and terminal
    correctness; never pooled with isolated results (§4.3)."""
    items, labels, identities = build_workflow_plan(
        population, endpoint_schedule_version, request_contract_key,
        profile)
    run_id = writer.run_id if writer is not None else "unwritten"
    adapter = _ComposedTraceAdapter(run_id, identities, writer)

    def batch_call(worker_id: int, requests: list[str]) -> list[CallRecord]:
        # One physical generation per request preserves singleton-v1
        # inside the executor's wave batching.
        return [singleton_call(runtime, ENDPOINT_NAMES[worker_id], request)
                for request in requests]

    executor.execute_workflow_batch(items, batch_call, trace=adapter)
    return adapter.rows, labels


def score_workflow_calls(call_rows: list[Mapping[str, Any]],
                         labels: list[WorkflowLabel]
                         ) -> list[dict[str, Any]]:
    """Terminal correctness over all scheduled workflows, with the §4.3
    disjoint-category reconciliation enforced per workflow."""
    by_case: dict[str, dict[int, Mapping[str, Any]]] = {}
    for row in call_rows:
        if row["evaluation_mode"] != "composed":
            raise InfrastructureError(
                "isolated rows in workflow scoring; modes are never pooled")
        steps = by_case.setdefault(row["case_id"], {})
        if row["position"] in steps:
            raise InfrastructureError(
                f"duplicate step ({row['case_id']}, {row['position']})")
        steps[row["position"]] = row
    label_ids = {label.case_id for label in labels}
    if len(label_ids) != len(labels):
        raise InfrastructureError("duplicate workflow label case_id")
    if set(by_case) != label_ids:
        missing = sorted(label_ids - set(by_case))
        extra = sorted(set(by_case) - label_ids)
        raise InfrastructureError(
            f"workflow rows and labels disagree: missing {missing}, "
            f"extra {extra}")
    legal_status = {"called", "dependency_blocked",
                    "pre_call_world_failure", "synthetic"}
    scores = []
    for label in labels:
        steps = by_case[label.case_id]
        if sorted(steps) != list(range(1, len(steps) + 1)):
            raise InfrastructureError(
                f"{label.case_id}: scheduled positions {sorted(steps)} are "
                "not contiguous from 1")
        for row in steps.values():
            if row["call_status"] not in legal_status:
                raise InfrastructureError(
                    f"unknown call status {row['call_status']!r}")
        sink = steps[len(steps)]
        terminal = (sink["value"] if sink["call_status"] == "called"
                    and sink["status"] == "success" else None)
        scores.append({
            "row_type": "workflow",
            "run_id": sink["run_id"],
            "case_id": label.case_id,
            "latent_program_id": label.latent_program_id,
            "cell_id": label.cell_id,
            "renderer_id": label.renderer_id,
            "terminal_value": terminal,
            "final_gold": label.final_gold,
            "terminal_correct": terminal == label.final_gold,
            "scorer_version": SCORER_VERSION,
        })
    return scores


# --- parse-stage attribution (81_f §5.3) -------------------------------------

def parse_stages(completion: str, result: WorkerResult) -> dict[str, Any]:
    """Envelope-vs-grammar attribution by re-calling the pure envelope
    parser; the authoritative tool path ran exactly once elsewhere. The
    staged record must agree with the terminal WorkerResult."""
    if not is_utf8_encodable(completion):
        envelope = "E_PARSE"  # run_worker_output's pre-envelope check
    else:
        try:
            contract.parse_envelope(completion)
            envelope = "ok"
        except ToolRejection as rejection:
            envelope = rejection.code
    if envelope != "ok":
        if result.rejection_code != envelope:
            raise InfrastructureError(
                f"staged envelope outcome {envelope!r} disagrees with "
                f"terminal WorkerResult {result.rejection_code!r}")
        return {"envelope_outcome": envelope, "grammar_outcome": None}
    if result.status == "success":
        return {"envelope_outcome": "ok", "grammar_outcome": "ok"}
    if result.rejection_code in SYNTAX_REJECTION_CODES:
        return {"envelope_outcome": "ok",
                "grammar_outcome": result.rejection_code}
    # Semantic rejection: grammar parsed and the tool executed.
    return {"envelope_outcome": "ok", "grammar_outcome": "ok"}


# --- environment/provenance facts (81_f §5.1) -------------------------------

def git_provenance(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Source commit plus dirty-state/diff digest. Diagnostic-only for
    candidate freezing: retained GPU comparison runs require a clean tree."""
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True,
            cwd=repo_root).stdout
    commit = run("rev-parse", "HEAD").strip()
    dirty = bool(run("status", "--porcelain").strip())
    diff_sha = (hashlib.sha256(run("diff", "HEAD").encode()).hexdigest()
                if dirty else None)
    return {"commit": commit, "dirty": dirty, "diff_sha256": diff_sha}


def environment_versions() -> dict[str, Any]:
    """Library, backend and deterministic-flag facts actually in effect.
    Fields are null where a library or device is genuinely absent (CPU
    test runs); the GPU acceptance run records them all."""
    facts: dict[str, Any] = {"python": platform.python_version()}
    try:
        import torch
        facts["torch"] = torch.__version__
        facts["cuda"] = torch.version.cuda
        facts["deterministic_algorithms"] = \
            torch.are_deterministic_algorithms_enabled()
        facts["cudnn_deterministic"] = torch.backends.cudnn.deterministic
        facts["cudnn_benchmark"] = torch.backends.cudnn.benchmark
        facts["gpu"] = (torch.cuda.get_device_name(0)
                        if torch.cuda.is_available() else None)
    except ImportError:
        facts["torch"] = None
    try:
        import transformers
        facts["transformers"] = transformers.__version__
    except ImportError:
        facts["transformers"] = None
    try:
        import bitsandbytes
        facts["bitsandbytes"] = bitsandbytes.__version__
    except ImportError:
        facts["bitsandbytes"] = None
    facts["cublas_workspace_config"] = os.environ.get(
        "CUBLAS_WORKSPACE_CONFIG")
    try:
        facts["nvidia_driver"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version",
             "--format=csv,noheader"], capture_output=True, text=True,
            check=True).stdout.strip().splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        facts["nvidia_driver"] = None
    return facts


# --- manifest (81_f §5.1) ----------------------------------------------------

def build_manifest(runtime: Runtime, prompts: PromptBundle, *,
                   run_id: str, purpose: str,
                   population: Mapping[str, Any],
                   endpoint_schedule_version: str,
                   candidate_label: str,
                   request_contract_key: str,
                   expected_calls: int,
                   expected_scores: int = 0,
                   evaluation_mode: str = "isolated",
                   generation_policy: str = GENERATION_POLICY_SINGLETON,
                   physical_layout: Mapping[str, Any] | None = None,
                   frozen_candidate: bool = False,
                   seed_policy: str = "greedy-no-sampling",
                   git_info: Mapping[str, Any] | None = None,
                   process_info: Mapping[str, Any] | None = None,
                   difficulty_profile: Mapping[str, Any] | None = None,
                   ) -> dict[str, Any]:
    """Assemble the run manifest from actual runtime facts.

    Fail-closed bindings: the declared prompt bundle must hash to exactly
    what the pool renders; the request-contract key must resolve; a
    frozen-candidate run refuses a DRAFT bundle, a hand-built bundle that
    bypasses the registry, or a renderer subset.
    """
    declared = prompts.sha256()
    actual = dict(runtime.system_prompt_shas)
    if declared != actual:
        wrong = sorted(name for name in set(declared) | set(actual)
                       if declared.get(name) != actual.get(name))
        raise ProfileError(
            f"prompt bundle {prompts.revision!r} does not match the "
            f"prompts the pool actually renders (endpoints {wrong}); "
            "a declared revision is valid only for its exact strings")
    if frozen_candidate or prompts.status.startswith("FROZEN"):
        # 82_s finding 5 / 84_s finding 3: freeze grade is intrinsic —
        # any bundle *claiming* FROZEN must match the authoritative
        # registry, whether or not the caller set the flag.
        registered = resolve_prompts(prompts.revision)
        if prompts != registered:
            raise ProfileError(
                f"bundle {prompts.revision!r} claims or requires frozen "
                "status but does not match the registry; frozen prompts "
                "resolve only through the registry")
    if frozen_candidate:
        if not registered.status.startswith("FROZEN"):
            raise ProfileError(
                f"frozen-candidate run refuses prompt bundle "
                f"{prompts.revision!r} with status {registered.status!r}")
        if sorted(population["renderers"]) != sorted(RENDERER_IDS):
            raise ProfileError(
                "frozen-candidate runs require the full renderer "
                f"crossing {sorted(RENDERER_IDS)}, got "
                f"{sorted(population['renderers'])}")
    if evaluation_mode not in ("isolated", "composed"):
        raise ProfileError(f"unknown evaluation mode {evaluation_mode!r}")
    profile = runtime.profile
    # 92_s §6.8: the profile's declared prompt label and the resolved
    # bundle are one identity; a mismatch fails before execution.
    if prompts.revision != profile["prompts"]["d16_revision"]:
        raise ProfileError(
            f"profile declares d16_revision "
            f"{profile['prompts']['d16_revision']!r} but the bundle is "
            f"{prompts.revision!r}; label and bundle must agree")
    if runtime_profile_fingerprint(profile) \
            != runtime.runtime_profile_fingerprint:
        raise ProfileError(
            "runtime profile was mutated after build_runtime; the "
            "manifest would describe a configuration that did not run")
    return {
        "schema_version": WORKER_EVAL_SCHEMA_VERSION,
        "run_id": run_id,
        "purpose": purpose,
        "evaluation_mode": evaluation_mode,
        "status": "running",
        "git": dict(git_info) if git_info is not None else git_provenance(),
        # Fresh-process evidence for the §7.4 repeat confirmation.
        "process": (dict(process_info) if process_info is not None else
                    {"pid": os.getpid(),
                     "started_utc": datetime.now(
                         timezone.utc).isoformat()}),
        "population": copy.deepcopy(dict(population)),
        "endpoint_schedule_version": endpoint_schedule_version,
        "generator_version": program.GENERATOR_VERSION,
        "difficulty_profile_version": profile_version(
            dict(difficulty_profile) if difficulty_profile is not None
            else DEFAULT_PROFILE),
        "candidate_label": candidate_label,
        "request_contract": resolve_request_contract(request_contract_key),
        "runtime_profile": copy.deepcopy(profile),
        "runtime_profile_fingerprint": runtime.runtime_profile_fingerprint,
        "worker_visible_fingerprint": runtime.worker_visible_fingerprint,
        "endpoint_fingerprints": dict(runtime.endpoint_fingerprints),
        "system_prompts": {
            "revision": prompts.revision,
            "status": prompts.status,
            "text": dict(prompts.prompts),
            "sha256": actual,
        },
        "chat_template_sha256": dict(runtime.chat_template_shas),
        "tokenizer_facts": {name: runtime.pool.tokenizer_facts(name)
                            for name in sorted(actual)},
        "tool_versions": dict(profile["tools"]),
        "resource_policy": profile["resource_policy"],
        "seed_policy": seed_policy,
        "environment": environment_versions(),
        "generation_policy": generation_policy,
        "expected_rows": {"calls": expected_calls,
                          "scores": expected_scores},
        # 92_s §3: planned physical-worker layout for candidate runs.
        **({"physical_layout": copy.deepcopy(dict(physical_layout))}
           if physical_layout is not None else {}),
    }


# --- call rows (81_f §5.3) ---------------------------------------------------

def make_called_row(*, run_id: str, case_id: str, observation_id: str,
                    position: int, latent_program_id: str, cell_id: str,
                    renderer_id: str, node_id: str, endpoint_name: str,
                    evaluation_mode: str, predecessor_source: str,
                    predecessor_positions: list[int],
                    generation_ordinal: int, user_message: str,
                    binding_sha256: str, record: CallRecord,
                    result: WorkerResult, stages: Mapping[str, Any]
                    ) -> dict[str, Any]:
    """One `called` row: identity, exact request/completion with digests,
    §1.6 backend telemetry, parse-stage attribution and the executed
    WorkerResult. Expected values never appear here."""
    if record.cache_hit:
        raise InfrastructureError(
            "called row for a cache-served record; scientific rows must "
            f"be {CACHE_SOURCE_DISABLED!r}")
    return {
        "run_id": run_id,
        "case_id": case_id,
        "observation_id": observation_id,
        "position": position,
        "latent_program_id": latent_program_id,
        "cell_id": cell_id,
        "renderer_id": renderer_id,
        "node_id": node_id,
        "endpoint_name": endpoint_name,
        "evaluation_mode": evaluation_mode,
        "predecessor_source": predecessor_source,
        "predecessor_positions": list(predecessor_positions),
        "call_status": "called",
        "user_message": user_message,
        "request_text": record.request_text,
        "request_sha256": record.request_sha256,
        "binding_sha256": binding_sha256,
        "generation_ordinal": generation_ordinal,
        "physical_batch_size": 1,
        "physical_batch_slot": 0,
        "completion": record.completion,
        "completion_sha256": hashlib.sha256(
            record.completion.encode("utf-8")).hexdigest(),
        "finish_reason": record.finish_reason,
        "generated_tokens": record.generated_tokens,
        "generation_hit_token_cap": record.generation_hit_token_cap,
        "envelope_outcome": stages["envelope_outcome"],
        "grammar_outcome": stages["grammar_outcome"],
        "status": result.status,
        "value": result.value,
        "rejection_code": result.rejection_code,
        "artifact_valid": result.artifact_valid,
        "tool_executed": result.tool_executed,
        "cache_source": CACHE_SOURCE_DISABLED,
    }


def run_node_cases(runtime: Runtime, cases: list[WorkerEvalCase],
                   writer: "RunWriter | None",
                   identities: Mapping[str, Mapping[str, Any]]
                   ) -> list[dict[str, Any]]:
    """Execute every isolated case: singleton generation, one
    authoritative envelope->grammar->tool execution against a fresh
    Binding, stage attribution, one called row. For a valid isolated run
    scheduled == called (81_f §4.3); any infrastructure failure aborts."""
    run_id = writer.run_id if writer is not None else "unwritten"
    rows = []
    for ordinal, case in enumerate(cases):
        record = singleton_call(runtime, case.endpoint_name,
                                case.user_message)
        result = contract.run_worker_output(
            _ENDPOINT_ID[case.endpoint_name], record.completion,
            case.binding())
        identity = identities[case.case_id]
        row = make_called_row(
            run_id=run_id, case_id=case.case_id,
            observation_id=case.observation_id,
            position=identity["position"],
            latent_program_id=identity["latent_program_id"],
            cell_id=identity["cell_id"],
            renderer_id=identity["renderer_id"],
            node_id=identity["node_id"],
            endpoint_name=case.endpoint_name,
            evaluation_mode="isolated",
            predecessor_source=identity["predecessor_source"],
            predecessor_positions=[k for k, _ in case.steps],
            generation_ordinal=ordinal,
            user_message=case.user_message,
            binding_sha256=case.binding_sha256,
            record=record, result=result,
            stages=parse_stages(record.completion, result))
        if writer is not None:
            writer.write_call(row)
        rows.append(row)
    return rows


# --- strict node scoring (81_f §5.4) -----------------------------------------

def score_node_calls(call_rows: list[Mapping[str, Any]],
                     labels: list[NodeLabel]) -> list[dict[str, Any]]:
    """Join calls to labels by exact case_id after execution. Strict
    correctness over the full scheduled denominator: parse/tool failures
    are called outcomes and score node-incorrect. Missing, duplicate or
    extra rows are an invalid run, not data."""
    by_case: dict[str, Mapping[str, Any]] = {}
    for row in call_rows:
        if row["case_id"] in by_case:
            raise InfrastructureError(f"duplicate call row "
                                      f"{row['case_id']}")
        by_case[row["case_id"]] = row
    label_ids = {label.case_id for label in labels}
    if len(label_ids) != len(labels):
        raise InfrastructureError("duplicate label case_id")
    if set(by_case) != label_ids:
        missing = sorted(label_ids - set(by_case))
        extra = sorted(set(by_case) - label_ids)
        raise InfrastructureError(
            f"calls and labels disagree: missing {missing}, extra {extra}")
    scores = []
    for label in labels:
        row = by_case[label.case_id]
        for field in ("latent_program_id", "cell_id", "renderer_id",
                      "node_id", "position", "predecessor_source"):
            if row[field] != getattr(label, field):
                raise InfrastructureError(
                    f"{label.case_id}: call row {field}={row[field]!r} "
                    f"disagrees with label {getattr(label, field)!r}")
        observed = row["value"]
        scores.append({
            "row_type": "node",
            "run_id": row["run_id"],
            "case_id": label.case_id,
            "call_role": label.call_role,
            "latent_program_id": label.latent_program_id,
            "cell_id": label.cell_id,
            "renderer_id": label.renderer_id,
            "node_id": label.node_id,
            "node_family": label.node_family,
            "position": label.position,
            "endpoint_name": row["endpoint_name"],
            "predecessor_source": label.predecessor_source,
            "observed_value": observed,
            "expected_value": label.expected_value,
            "node_correct": (row["status"] == "success"
                             and observed == label.expected_value),
            "scorer_version": SCORER_VERSION,
        })
    return scores


# --- derived summary (81_f §5.5) ---------------------------------------------

def _tally(counter: dict[str, dict[str, int]], key: str,
           correct: bool) -> None:
    stratum = counter.setdefault(key, {"n": 0, "correct": 0})
    stratum["n"] += 1
    stratum["correct"] += int(correct)


def summarize_worker_eval(manifest: Mapping[str, Any],
                          calls: list[Mapping[str, Any]],
                          scores: list[Mapping[str, Any]]
                          ) -> dict[str, Any]:
    """Derived, never source truth: recomputed from calls and scores and
    compared on load. Counts only (numerator/denominator pairs), so
    rederivation is exact. `WorkerResult.status == "success"` is reported
    as protocol success, never labelled accuracy."""
    for row in calls:
        if row["run_id"] != manifest["run_id"]:
            raise InfrastructureError(
                f"mixed run ids: row {row['run_id']!r} in "
                f"{manifest['run_id']!r}")
    summary: dict[str, Any] = {
        "schema_version": WORKER_EVAL_SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "gate_scope": ("descriptive only; Stage-0B/D16 artifacts emit no "
                       "Stage-1 construction or qualification gate "
                       "results"),
    }
    isolated = [row for row in calls
                if row["evaluation_mode"] == "isolated"]
    node_scores = [s for s in scores if s["row_type"] == "node"]
    if isolated or node_scores:
        outcomes = {
            "scheduled": len(isolated),
            "called": sum(r["call_status"] == "called" for r in isolated),
            "token_cap": sum(bool(r["generation_hit_token_cap"])
                             for r in isolated),
            "envelope_failed": sum(r["envelope_outcome"] not in (None, "ok")
                                   for r in isolated),
            "grammar_failed": sum(r["grammar_outcome"] not in (None, "ok")
                                  for r in isolated),
            "tool_executed": sum(bool(r["tool_executed"])
                                 for r in isolated),
            "protocol_success": sum(r["status"] == "success"
                                    for r in isolated),
        }
        by_stratum: dict[str, dict[str, int]] = {}
        by_renderer: dict[str, dict[str, int]] = {}
        pairs: dict[tuple[str, str], dict[str, bool]] = {}
        correct = 0
        for score in node_scores:
            correct += int(score["node_correct"])
            _tally(by_stratum,
                   "|".join((score["endpoint_name"], score["cell_id"],
                             score["node_family"], score["renderer_id"])),
                   score["node_correct"])
            _tally(by_renderer, score["renderer_id"],
                   score["node_correct"])
            pairs.setdefault((score["latent_program_id"],
                              score["node_id"]),
                             {})[score["renderer_id"]] = \
                score["node_correct"]
        flipped = sum(1 for group in pairs.values()
                      if len(set(group.values())) > 1)
        # §4.5/§5.5 pairwise flips (84_s): which renderer *pair*
        # disagreed — the any-of-three flag above cannot identify it.
        pairwise: dict[str, dict[str, int]] = {}
        for group in pairs.values():
            for left, right in combinations(sorted(group), 2):
                entry = pairwise.setdefault(f"{left}|{right}",
                                            {"n": 0, "flipped": 0})
                entry["n"] += 1
                entry["flipped"] += int(group[left] != group[right])
        by_rate = sorted(by_renderer.items(),
                         key=lambda kv: (Fraction(kv[1]["correct"],
                                                  kv[1]["n"]), kv[0]))
        summary["isolated"] = {
            "outcomes": outcomes,
            "node_correct": {"n": len(node_scores), "correct": correct},
            "by_stratum": by_stratum,
            "by_renderer": by_renderer,
            # The §5.5 max-min renderer gap as its two endpoints; rates
            # and the gap itself derive exactly from these counts.
            "worst_renderer": ({"renderer_id": by_rate[0][0],
                                **by_rate[0][1]} if by_rate else None),
            "best_renderer": ({"renderer_id": by_rate[-1][0],
                               **by_rate[-1][1]} if by_rate else None),
            "paired": {"groups": len(pairs), "flipped": flipped,
                       "pairwise": pairwise},
        }
    composed = [row for row in calls
                if row["evaluation_mode"] == "composed"]
    workflow_scores = [s for s in scores if s["row_type"] == "workflow"]
    if composed or workflow_scores:
        called = [r for r in composed if r["call_status"] == "called"]
        steps = {
            "scheduled": len(composed),
            "called": len(called),
            "dependency_blocked": sum(
                r["call_status"] == "dependency_blocked" for r in composed),
            "pre_call_world_failure": sum(
                r["call_status"] == "pre_call_world_failure"
                for r in composed),
            "synthetic": sum(r["call_status"] == "synthetic"
                             for r in composed),
        }
        if steps["scheduled"] != (steps["called"]
                                  + steps["dependency_blocked"]
                                  + steps["pre_call_world_failure"]
                                  + steps["synthetic"]):
            raise InfrastructureError(
                f"composed step categories do not reconcile: {steps}")
        summary["composed"] = {
            "workflows": len(workflow_scores),
            "terminal_correct": sum(s["terminal_correct"]
                                    for s in workflow_scores),
            "steps": steps,
            # Conditional-on-called protocol success is diagnostic only.
            "called_protocol_success": sum(r["status"] == "success"
                                           for r in called),
        }
    return summary


# --- run writer (81_f §5.1) --------------------------------------------------

class RunWriter:
    """Owns one run directory: manifest first (status `running`), call and
    score rows appended and flushed, the derived summary, then a final
    manifest with row counts, payload hashes and terminal status. Refuses
    an existing directory; an exception marks the run `aborted`; a clean
    exit that wrote fewer rows than planned also cannot look complete."""

    def __init__(self, run_dir: str | Path, manifest: dict[str, Any]) -> None:
        self.run_dir = Path(run_dir)
        if self.run_dir.exists():
            raise InfrastructureError(
                f"{self.run_dir} already exists; evaluation runs are never "
                "merged or overwritten")
        if manifest.get("status") != "running":
            raise InfrastructureError("manifest must start status=running")
        self.run_dir.mkdir(parents=True)
        self._manifest = copy.deepcopy(manifest)
        self._write_manifest()
        self._calls = (self.run_dir / "calls.jsonl").open(
            "x", encoding="utf-8")
        self._scores = (self.run_dir / "scores.jsonl").open(
            "x", encoding="utf-8")
        self._written = {"calls": 0, "scores": 0}
        self._summary: dict[str, Any] | None = None
        self._extras: dict[str, dict[str, Any]] = {}
        self.manifest_sha256: str | None = None

    @property
    def run_id(self) -> str:
        return self._manifest["run_id"]

    def _write_manifest(self) -> None:
        (self.run_dir / "manifest.json").write_text(
            json.dumps(self._manifest, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    def _append(self, name: str, handle: Any, row: Mapping[str, Any]) -> None:
        if self._manifest["status"] != "running":
            raise InfrastructureError("run is finalized")
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
        handle.flush()
        self._written[name] += 1

    def write_call(self, row: Mapping[str, Any]) -> None:
        self._append("calls", self._calls, row)

    def write_score(self, row: Mapping[str, Any]) -> None:
        self._append("scores", self._scores, row)

    def write_summary(self, summary: Mapping[str, Any]) -> None:
        if self._manifest["status"] != "running":
            raise InfrastructureError("run is finalized")
        self._summary = copy.deepcopy(dict(summary))

    def write_extra(self, name: str, payload: Mapping[str, Any]) -> None:
        """Additional payload file (92_s §3: execution measurements),
        written at finalize and hashed with the other payloads."""
        if self._manifest["status"] != "running":
            raise InfrastructureError("run is finalized")
        if name in ("manifest.json", "calls.jsonl", "scores.jsonl",
                    "summary.json"):
            raise InfrastructureError(f"reserved payload name {name!r}")
        self._extras[name] = copy.deepcopy(dict(payload))

    def _finalize(self, status: str) -> None:
        if self._manifest["status"] != "running":
            return
        self._calls.close()
        self._scores.close()
        if self._summary is not None:
            (self.run_dir / "summary.json").write_text(
                json.dumps(self._summary, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
        for name, payload in sorted(self._extras.items()):
            (self.run_dir / name).write_text(
                json.dumps(payload, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
        self._manifest["written_rows"] = dict(self._written)
        self._manifest["payload_sha256"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.run_dir.iterdir())
            if path.name != "manifest.json"}
        self._manifest["status"] = status
        self._write_manifest()
        # §5.1: the manifest does not hash itself; record its digest in
        # the run log after close.
        self.manifest_sha256 = hashlib.sha256(
            (self.run_dir / "manifest.json").read_bytes()).hexdigest()

    def close(self) -> None:
        expected = self._manifest["expected_rows"]
        if dict(self._written) != dict(expected):
            self._finalize("aborted")
            raise InfrastructureError(
                f"run wrote {self._written} rows but planned {expected}; "
                "marked aborted")
        if self._summary is None:
            self._finalize("aborted")
            raise InfrastructureError(
                "run closed without a derived summary; marked aborted")
        self._finalize("complete")

    def abort(self) -> None:
        self._finalize("aborted")

    def __enter__(self) -> "RunWriter":
        return self

    def __exit__(self, exc_type: Any, *exc: Any) -> None:
        if exc_type is not None:
            self.abort()
        else:
            self.close()


# --- strict loader (81_f §5.6) -----------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()]


def _validate_measurements(run_dir: Path,
                           manifest: Mapping[str, Any]) -> None:
    """92_s §3: candidate runs carry a planned physical layout and
    loader-validated execution measurements; selection consumes only the
    validated record, never a console value."""
    path = run_dir / "measurements.json"
    if not path.exists():
        raise InfrastructureError(
            "candidate run declares a physical layout but has no "
            "measurements.json")
    measurements = json.loads(path.read_text(encoding="utf-8"))
    for field in ("wall_seconds", "idle_reserved_bytes",
                  "peak_reserved_bytes"):
        value = measurements.get(field)
        if not isinstance(value, (int, float)) or value < 0 \
                or value != value:
            raise InfrastructureError(
                f"measurement {field!r} is missing or invalid: {value!r}")
    per_endpoint = measurements.get("per_endpoint")
    expected_endpoints = set(ENDPOINT_NAMES.values())
    if not isinstance(per_endpoint, dict) \
            or set(per_endpoint) != expected_endpoints:
        raise InfrastructureError(
            f"per-endpoint telemetry must cover exactly "
            f"{sorted(expected_endpoints)}")
    for endpoint, entry in per_endpoint.items():
        calls, seconds = entry.get("calls"), entry.get("seconds")
        if not isinstance(calls, int) or calls < 1 \
                or not isinstance(seconds, (int, float)) or seconds < 0 \
                or seconds != seconds:
            raise InfrastructureError(
                f"per-endpoint telemetry for {endpoint!r} is invalid: "
                f"{entry!r}")
    layout_quant = manifest["physical_layout"].get("quantization")
    if layout_quant != manifest["runtime_profile"]["nf4"]:
        raise InfrastructureError(
            "physical layout quantization does not match the profile")
    planned = manifest["physical_layout"]["checkpoints"]
    actual = measurements.get("checkpoints")
    if not isinstance(actual, list):
        raise InfrastructureError("measurements lack a checkpoint report")
    planned_keys = {(c["model_id"], c["revision"]): c for c in planned}
    actual_keys = {(c["model_id"], c["revision"]): c for c in actual}
    if set(planned_keys) != set(actual_keys):
        raise InfrastructureError(
            f"actual checkpoints {sorted(actual_keys)} differ from the "
            f"planned layout {sorted(planned_keys)}")
    for key, plan in planned_keys.items():
        fact = actual_keys[key]
        if sorted(fact.get("endpoints", [])) != sorted(plan["endpoints"]):
            raise InfrastructureError(
                f"checkpoint {key}: endpoint mapping differs from plan")
        if not fact.get("loaded"):
            raise InfrastructureError(
                f"checkpoint {key} was never loaded; the measurement "
                "does not describe the declared layout")
        if fact.get("measured_parameters") != plan["declared_parameters"]:
            raise InfrastructureError(
                f"checkpoint {key}: measured parameters "
                f"{fact.get('measured_parameters')!r} != declared "
                f"{plan['declared_parameters']!r}")


def load_run(run_dir: str | Path,
             profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Hand-written fail-closed loader. Completeness is checked by
    regenerating the planned population from the manifest identity and the
    frozen generator — file hashes and an internally consistent summary
    are never allowed to bless a wrong target (§5.6)."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(
        encoding="utf-8"))
    if manifest["status"] != "complete":
        raise InfrastructureError(
            f"run status {manifest['status']!r} is not loadable")
    if manifest["schema_version"] != WORKER_EVAL_SCHEMA_VERSION:
        raise InfrastructureError(
            f"schema {manifest['schema_version']} != "
            f"{WORKER_EVAL_SCHEMA_VERSION}")
    if runtime_profile_fingerprint(manifest["runtime_profile"]) \
            != manifest["runtime_profile_fingerprint"]:
        raise InfrastructureError(
            "manifest runtime profile does not rederive its own "
            "fingerprint; the stored configuration was altered")
    stored_prompts = manifest["system_prompts"]
    if stored_prompts["status"].startswith("FROZEN"):
        # 84_s finding 3: a FROZEN claim is intrinsic and downstream-
        # verifiable — recheck it against the authoritative registry.
        try:
            registered = resolve_prompts(stored_prompts["revision"])
        except ProfileError as error:
            raise InfrastructureError(
                f"stored FROZEN prompt claim cannot be verified: "
                f"{error}") from error
        if (not registered.status.startswith("FROZEN")
                or stored_prompts["text"] != dict(registered.prompts)
                or stored_prompts["sha256"] != registered.sha256()):
            raise InfrastructureError(
                f"stored FROZEN claim for revision "
                f"{stored_prompts['revision']!r} does not match the "
                "registry")

    payload_shas = manifest["payload_sha256"]
    on_disk = {path.name for path in run_dir.iterdir()
               if path.name != "manifest.json"}
    if on_disk != set(payload_shas):
        raise InfrastructureError(
            f"payload files {sorted(on_disk)} != manifest "
            f"{sorted(payload_shas)}")
    for name, sha in payload_shas.items():
        actual = hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        if actual != sha:
            raise InfrastructureError(f"{name}: file hash mismatch")

    calls = _read_jsonl(run_dir / "calls.jsonl")
    scores = _read_jsonl(run_dir / "scores.jsonl")
    summary = json.loads((run_dir / "summary.json").read_text(
        encoding="utf-8"))
    counts = {"calls": len(calls), "scores": len(scores)}
    if counts != manifest["written_rows"] \
            or counts != manifest["expected_rows"]:
        raise InfrastructureError(
            f"row counts {counts} != written {manifest['written_rows']} / "
            f"expected {manifest['expected_rows']}")
    for row in calls + scores:
        if row["run_id"] != manifest["run_id"]:
            raise InfrastructureError(
                f"mixed run ids: {row['run_id']!r} in file for "
                f"{manifest['run_id']!r}")
    for row in calls:
        if row["call_status"] == "called":
            if row["cache_source"] != CACHE_SOURCE_DISABLED:
                raise InfrastructureError(
                    f"called row with cache_source "
                    f"{row['cache_source']!r}; scientific runs are "
                    "cache-disabled")
            for text, sha in ((row["request_text"], row["request_sha256"]),
                              (row["completion"],
                               row["completion_sha256"])):
                if hashlib.sha256(
                        text.encode("utf-8")).hexdigest() != sha:
                    raise InfrastructureError(
                        f"{row['case_id']}: request/completion hash "
                        "mismatch")
        elif row["completion"] is not None or row["request_text"] is not None:
            raise InfrastructureError(
                f"{row['case_id']}: uncalled row carries generation fields")

    if "physical_layout" in manifest:
        _validate_measurements(run_dir, manifest)
    mode = manifest["evaluation_mode"]
    population = manifest["population"]
    if mode == "isolated":
        cases, labels = build_node_cases(
            population, manifest["endpoint_schedule_version"],
            manifest["request_contract"]["key"], profile=profile)
        case_by_id = {case.case_id: case for case in cases}
        row_ids = [row["case_id"] for row in calls]
        if len(set(row_ids)) != len(row_ids):
            raise InfrastructureError("duplicate isolated call rows")
        if set(row_ids) != set(case_by_id):
            missing = sorted(set(case_by_id) - set(row_ids))
            extra = sorted(set(row_ids) - set(case_by_id))
            raise InfrastructureError(
                f"planned population mismatch: missing {missing}, "
                f"extra {extra}")
        check_renderer_support(labels, list(population["renderers"]))
        label_by_id = {label.case_id: label for label in labels}
        plan_index = {case.case_id: index
                      for index, case in enumerate(cases)}
        for row in calls:
            case = case_by_id[row["case_id"]]
            label = label_by_id[row["case_id"]]
            if row["generation_ordinal"] != plan_index[row["case_id"]]:
                # 84_s finding 1: isolated runs generate in canonical
                # plan order; the recorded ordinals must prove it.
                raise InfrastructureError(
                    f"{row['case_id']}: generation ordinal "
                    f"{row['generation_ordinal']} is not the canonical "
                    f"plan position {plan_index[row['case_id']]}")
            # 82_s finding 4: every isolated row must be a real call whose
            # identity matches the regenerated case — a relabelled
            # endpoint or an impossible blocked-with-value state must not
            # load, however internally consistent the file is.
            if row["call_status"] != "called":
                raise InfrastructureError(
                    f"{row['case_id']}: isolated rows must all be "
                    f"called, got {row['call_status']!r} (§4.3 "
                    "scheduled == called)")
            regenerated = {
                "evaluation_mode": "isolated",
                "endpoint_name": case.endpoint_name,
                "observation_id": case.observation_id,
                "position": label.position,
                "predecessor_source": label.predecessor_source,
                "predecessor_positions": [k for k, _ in case.steps],
                "user_message": case.user_message,
                "binding_sha256": case.binding_sha256,
            }
            wrong = sorted(field for field, expected in regenerated.items()
                           if row[field] != expected)
            if wrong:
                raise InfrastructureError(
                    f"{row['case_id']}: stored fields {wrong} disagree "
                    "with the regenerated case")
        rederived = score_node_calls(calls, labels)
    elif mode == "composed":
        _, labels, identities = build_workflow_plan(
            population, manifest["endpoint_schedule_version"],
            manifest["request_contract"]["key"], profile=profile)
        row_keys = [(row["case_id"], row["position"]) for row in calls]
        if len(set(row_keys)) != len(row_keys):
            raise InfrastructureError("duplicate composed step rows")
        if set(row_keys) != set(identities):
            missing = sorted(set(identities) - set(row_keys))
            extra = sorted(set(row_keys) - set(identities))
            raise InfrastructureError(
                f"planned workflow steps mismatch: missing {missing}, "
                f"extra {extra}")
        for row in calls:
            identity = identities[(row["case_id"], row["position"])]
            wrong = sorted(
                field for field in ("latent_program_id", "cell_id",
                                    "renderer_id", "node_id",
                                    "endpoint_name", "predecessor_source",
                                    "predecessor_positions")
                if row[field] != identity[field])
            if wrong or row["evaluation_mode"] != "composed":
                raise InfrastructureError(
                    f"({row['case_id']}, {row['position']}): stored "
                    f"fields {wrong or ['evaluation_mode']} disagree "
                    "with the regenerated plan")
        rederived = score_workflow_calls(calls, labels)
    else:
        raise InfrastructureError(f"unknown evaluation mode {mode!r}")

    if scores != rederived:
        raise InfrastructureError(
            "stored scores do not rederive from the regenerated "
            "population; expected values or strata were altered")
    if summary != summarize_worker_eval(manifest, calls, rederived):
        raise InfrastructureError("stored summary does not rederive")
    return {"manifest": manifest, "calls": calls, "scores": scores,
            "summary": summary}


# --- narrow two-run comparison (81_f §6.1) -----------------------------------

# Manifest paths permitted to differ, per declared difference. Everything
# else must match exactly; the comparison refuses surprises rather than
# explaining them away. Commit identity may differ (comparability comes
# from the held-fixed fields plus population regeneration, and refusing
# would invalidate hour-scale GPU runs over docs-only commits) but is
# always reported; dirty trees are refused outright.
_ALWAYS_ALLOWED_DIFFS = ("run_id", "purpose", "candidate_label", "git",
                         "process", "payload_sha256")
def _prompt_scope(endpoint: str) -> tuple[str, ...]:
    """Manifest paths a single-endpoint prompt contrast may change (92_s
    §6.8): the declared endpoint's prompt bytes and what follows from
    them. Other endpoints' prompt hashes must remain identical."""
    return (f"system_prompts.text.{endpoint}",
            f"system_prompts.sha256.{endpoint}",
            "system_prompts.revision", "system_prompts.status",
            f"endpoint_fingerprints.{endpoint}",
            "worker_visible_fingerprint", "runtime_profile_fingerprint",
            "runtime_profile.prompts.d16_revision")


def _model_scope(endpoint: str) -> tuple[str, ...]:
    """Manifest paths a single-endpoint model contrast may change (86_s
    finding 1): the declared endpoint's checkpoint and what follows from
    it (its template, tokenizer facts and endpoint fingerprint), plus
    the global fingerprints those feed. Any other endpoint's drift is an
    undeclared difference and refuses — never the caps or microbatch,
    which change results on their own (82_s finding 5)."""
    return (f"runtime_profile.workers.{endpoint}.model_id",
            f"runtime_profile.workers.{endpoint}.revision",
            f"chat_template_sha256.{endpoint}",
            f"tokenizer_facts.{endpoint}",
            f"endpoint_fingerprints.{endpoint}",
            "runtime_profile_fingerprint",
            "worker_visible_fingerprint",
            # 94_s finding 7: the planned physical layout follows from
            # the declared endpoint's checkpoint.
            "physical_layout")


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            out.update(_flatten(value, f"{prefix}{key}."))
        return out
    return {prefix.rstrip("."): obj}


def compare_worker_eval_runs(left: Mapping[str, Any],
                             right: Mapping[str, Any],
                             allowed_difference: str,
                             model_endpoint: str | None = None,
                             prompt_endpoint: str | None = None
                             ) -> dict[str, Any]:
    """Compare two loaded runs that differ in exactly one declared way.
    A model comparison names its subject endpoint explicitly (86_s
    finding 1), so an intended Code contrast whose arms actually differ
    on Math refuses instead of misattributing the delta. Requires
    identical population/case support and singleton generation; prints
    the exact differing manifest fields and refuses unexpected ones."""
    if allowed_difference == "request_contract":
        # Re-enabled per 92_s §6.8: the key now configures the builder
        # (render.build_worker_request block order), so a contract
        # difference is real request bytes — proven per case below.
        if model_endpoint is not None or prompt_endpoint is not None:
            raise ProfileError(
                "endpoint arguments do not apply to request_contract "
                "comparisons (the contract is shared by every worker)")
        dimension_allowed: tuple[str, ...] = ("request_contract",)
        must_differ: tuple[str, ...] = ("request_contract.digest",)
    elif allowed_difference == "model":
        if prompt_endpoint is not None:
            raise ProfileError(
                "prompt_endpoint applies only to prompt comparisons")
        if model_endpoint not in set(ENDPOINT_NAMES.values()):
            raise ProfileError(
                "a model comparison names its endpoint explicitly: "
                f"model_endpoint must be one of "
                f"{sorted(set(ENDPOINT_NAMES.values()))}, got "
                f"{model_endpoint!r}")
        dimension_allowed = _model_scope(model_endpoint)
        must_differ = dimension_allowed[:2]  # its model_id and revision
    elif allowed_difference == "prompt":
        if model_endpoint is not None:
            raise ProfileError(
                "model_endpoint applies only to model comparisons")
        if prompt_endpoint not in set(ENDPOINT_NAMES.values()):
            raise ProfileError(
                "a prompt comparison names its endpoint explicitly: "
                f"prompt_endpoint must be one of "
                f"{sorted(set(ENDPOINT_NAMES.values()))}, got "
                f"{prompt_endpoint!r}")
        dimension_allowed = _prompt_scope(prompt_endpoint)
        must_differ = (f"system_prompts.text.{prompt_endpoint}",
                       f"system_prompts.sha256.{prompt_endpoint}")
    else:
        raise ProfileError(
            f"allowed_difference must be one of "
            f"['model', 'prompt', 'request_contract'], "
            f"got {allowed_difference!r}")
    for run in (left, right):
        manifest = run["manifest"]
        if manifest["status"] != "complete":
            raise InfrastructureError("comparison requires complete runs")
        if manifest["generation_policy"] != GENERATION_POLICY_SINGLETON:
            raise InfrastructureError(
                "comparison requires singleton generation, got "
                f"{manifest['generation_policy']!r}")
        if manifest["git"]["dirty"]:
            raise InfrastructureError(
                "comparison refuses runs from a dirty worktree "
                "(81_f §5.1: dirty-state digests are diagnostic-only)")
        renderers = sorted(manifest["population"]["renderers"])
        if renderers != sorted(RENDERER_IDS):
            raise InfrastructureError(
                f"comparison requires the full renderer crossing "
                f"{sorted(RENDERER_IDS)}, got {renderers}; diagnostic "
                "renderer subsets are not comparable (81_f §4.5)")
    left_support = sorted((row["case_id"], row["position"])
                          for row in left["calls"])
    right_support = sorted((row["case_id"], row["position"])
                           for row in right["calls"])
    if left_support != right_support:
        raise InfrastructureError(
            "case support differs between runs; results are not "
            "comparable")
    flat_left = _flatten(left["manifest"])
    flat_right = _flatten(right["manifest"])
    differing = sorted(path for path in set(flat_left) | set(flat_right)
                       if flat_left.get(path) != flat_right.get(path))
    allowed = _ALWAYS_ALLOWED_DIFFS + dimension_allowed
    unexpected = [path for path in differing
                  if not any(path == a or path.startswith(a + ".")
                             for a in allowed)]
    if unexpected:
        raise InfrastructureError(
            f"manifest fields differ beyond declared "
            f"{allowed_difference!r} difference: {unexpected}")
    # 82_s/84_s finding: the declared dimension must differ in actual
    # bytes — a comparison whose arms are secretly identical (or differ
    # only in a label or a template side effect) is a config error.
    declared = [path for path in differing
                if any(path == a or path.startswith(a + ".")
                       for a in must_differ)]
    if not declared:
        raise InfrastructureError(
            f"declared {allowed_difference!r} difference is not present "
            "in actual bytes: the two runs are identical on that "
            "dimension")
    if allowed_difference == "request_contract":
        # 92_s §6.8: prove actual request-byte differences, not just a
        # differing digest in metadata.
        right_by_key = {(row["case_id"], row["position"]): row
                        for row in right["calls"]}
        if not any(row["user_message"]
                   != right_by_key[(row["case_id"], row["position"])][
                       "user_message"]
                   for row in left["calls"]):
            raise InfrastructureError(
                "request_contract arms posed byte-identical requests; "
                "the declared contract difference is a no-op")
    return {"allowed_difference": allowed_difference,
            "model_endpoint": model_endpoint,
            "prompt_endpoint": prompt_endpoint,
            "differing_fields": differing,
            "case_support": len(left_support)}


# --- §7.4 full-population repeat confirmation --------------------------------

# Generation fields that must be bit-equal between the two fresh-process
# runs of an accepted candidate (81_f §7.4).
CONFIRMATION_FIELDS = ("request_sha256", "completion", "finish_reason",
                       "generated_tokens", "generation_hit_token_cap")

# Manifest paths that may legitimately differ between two runs of the
# same candidate: run identity, process identity (required to differ),
# and the payload hashes that embed the run id.
_REPEAT_ALLOWED_DIFFS = ("run_id", "purpose", "git", "process",
                         "payload_sha256")

# The declared §7.4 full-population design (registration of the
# dedicated worker-development namespace is pending the D1 erratum):
# 30 latents per cell x 6 cells x all renderers = 900 isolated calls.
FULL_RUN_PER_CELL = 30


def confirm_repeat_run(left: Mapping[str, Any],
                       right: Mapping[str, Any],
                       expected_namespace: str) -> dict[str, Any]:
    """The §7.4 confirmation over two loaded runs of one candidate: the
    declared full isolated population, singleton generation, two
    genuinely distinct fresh-process runs on one clean commit, identical
    manifests (up to run identity), identical case support, and exact
    generation-field equality for every called row (84_s finding 1 —
    self-confirmation must fail). Canonical generation order is already
    enforced per run by `load_run`. Required before a candidate's full
    result enters the final comparison/freeze.

    The population size is fixed at the full §7.4 design (86_s finding
    2): the scientific entry point takes no override. The registered
    worker-development namespace (D1 erratum, 88_f) is the CLI's
    authoritative default."""
    return _confirm_repeat_run(left, right, expected_namespace,
                               FULL_RUN_PER_CELL)


def _confirm_repeat_run(left: Mapping[str, Any],
                        right: Mapping[str, Any],
                        expected_namespace: str,
                        per_cell: int) -> dict[str, Any]:
    """Module-private mechanism behind `confirm_repeat_run`, sized only
    so CPU tests can exercise every check on small fake populations."""
    reasons: list[str] = []
    for side, run in (("left", left), ("right", right)):
        manifest = run["manifest"]
        population = manifest["population"]
        if manifest["evaluation_mode"] != "isolated":
            reasons.append(f"{side}: not an isolated run")
        if manifest["generation_policy"] != GENERATION_POLICY_SINGLETON:
            reasons.append(f"{side}: not singleton generation")
        if population["namespace"] != expected_namespace:
            reasons.append(f"{side}: namespace "
                           f"{population['namespace']!r} is not the "
                           f"declared {expected_namespace!r}")
        if population["per_cell"] != per_cell:
            reasons.append(f"{side}: per_cell {population['per_cell']} "
                           f"is not the full §7.4 population "
                           f"({per_cell}/cell)")
        if sorted(population["renderers"]) != sorted(RENDERER_IDS):
            reasons.append(f"{side}: not the full renderer crossing")
        if population["visibility"] != "private":
            reasons.append(f"{side}: visibility is not private")
        if manifest["git"]["dirty"]:
            reasons.append(f"{side}: run from a dirty worktree")
    if left["manifest"]["run_id"] == right["manifest"]["run_id"]:
        reasons.append("run ids are identical; confirmation requires "
                       "two distinct runs")
    if left["manifest"]["process"]["pid"] \
            == right["manifest"]["process"]["pid"]:
        reasons.append("process ids are identical; confirmation "
                       "requires two fresh processes")
    if left["manifest"]["git"]["commit"] \
            != right["manifest"]["git"]["commit"]:
        reasons.append("runs span different commits; a repeat "
                       "confirmation requires one clean commit (the "
                       "cross-candidate commit policy does not apply)")
    flat_left = _flatten(left["manifest"])
    flat_right = _flatten(right["manifest"])
    unexpected = sorted(
        path for path in set(flat_left) | set(flat_right)
        if flat_left.get(path) != flat_right.get(path)
        and not any(path == a or path.startswith(a + ".")
                    for a in _REPEAT_ALLOWED_DIFFS))
    if unexpected:
        reasons.append(f"manifests differ on {unexpected}; a repeat run "
                       "must hold the whole candidate fixed")
    left_rows = {(row["case_id"], row["position"]): row
                 for row in left["calls"]}
    right_rows = {(row["case_id"], row["position"]): row
                  for row in right["calls"]}
    if set(left_rows) != set(right_rows):
        reasons.append("case support differs between the two runs")
    else:
        for key in sorted(left_rows):
            if left_rows[key]["call_status"] != \
                    right_rows[key]["call_status"]:
                reasons.append(f"{key}: call status differs")
                continue
            if left_rows[key]["call_status"] != "called":
                continue
            unequal = [field for field in CONFIRMATION_FIELDS
                       if left_rows[key][field] != right_rows[key][field]]
            if unequal:
                reasons.append(f"{key}: generation fields {unequal} "
                               "differ between fresh processes")
    return {"confirmed": not reasons, "reasons": reasons,
            "cases": len(left_rows)}
