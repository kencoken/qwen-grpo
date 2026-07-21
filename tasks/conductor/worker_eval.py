"""Worker-evaluation integrity — Stage 0B follow-up (plan 81_f).

Tranche A surface: fail-closed provenance manifests, cache-disabled
singleton generation, and call-row writing. Isolated node cases, labels
and scoring land in Tranche B; renderer crossing, composed-workflow
diagnostics, summaries and strict loaders in Tranche C.

The governing contract (81_f §1): given a worker result, identify the
exact request and execution configuration that produced it. Hence the
manifest binds actual prompt bytes and runtime facts (not labels), the
no-op cache guarantees one physical generation per planned case, and
every call row carries the exact rendered request and completion with
their SHA-256 digests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import contract, executor, program
from .agreement import ENDPOINT_FOR_OP
from .profiles import DEFAULT_PROFILE, ProfileError, canonical_json, \
    profile_version
from .prompts import PromptBundle
from .render import ARTIFACT_FINAL_LINE
from .resources import InstanceRegistry
from .runtime import CallRecord, Runtime
from .tools import Binding, ToolRejection
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
    microbatch a single unpadded sequence (81_f §6.2). A cache hit here
    means the runtime was not built cache-disabled — abort, don't shrug."""
    (record,) = runtime.worker_call_batch(endpoint_name, [user_message])
    if record.cache_hit:
        raise InfrastructureError(
            "singleton evaluator call was served from cache; scientific "
            "runs must use the disabled cache (81_f §5.3)")
    return record


# --- request-contract binding (81_f §5.2) -----------------------------------

# The v0 worker request contract: render.build_worker_request's frozen block
# order and final instruction. A key resolves to exact content; a label
# alone ("task_last") is not provenance.
REQUEST_CONTRACTS: dict[str, dict[str, Any]] = {
    "worker-blocks-v0": {
        "builder": "render.build_worker_request",
        "builder_version": "specs-v0.8",
        "block_order": ["problem", "task", "resource", "previous_results",
                        "final_line"],
        "final_line": ARTIFACT_FINAL_LINE,
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
    node_family: str
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


def _binding_sha(registry_json: Mapping[str, Any], resource: str | None,
                 previous: Mapping[int, int] | None) -> str:
    payload = {
        "resources": ({resource: registry_json[resource]}
                      if resource is not None else {}),
        "steps": {str(k): v for k, v in (previous or {}).items()},
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def node_cases_for_latent(latent: Mapping[str, Any], renderers: list[str],
                          visibility: str
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
    families = {node["id"]: ENDPOINT_NAMES[ENDPOINT_FOR_OP[node["op"]]]
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
                inst_registry, previous)
            case_id = f"{inst['render_instance_id']}:{node_id}"
            cases.append(WorkerEvalCase(
                case_id=case_id,
                observation_id=inst["render_instance_id"],
                endpoint_name=schedule[node_id],
                user_message=user_message,
                resources=tuple(sorted(binding.resources.items())),
                steps=tuple(sorted(binding.steps.items())),
                binding_sha256=_binding_sha(inst["private_registry"],
                                            step["resource"], previous)))
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
                latent, renderers, population["visibility"])
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
    return facts


# --- manifest (81_f §5.1) ----------------------------------------------------

def build_manifest(runtime: Runtime, prompts: PromptBundle, *,
                   run_id: str, purpose: str,
                   population: Mapping[str, Any],
                   endpoint_schedule_version: str,
                   candidate_label: str,
                   request_contract_key: str,
                   expected_calls: int,
                   generation_policy: str = GENERATION_POLICY_SINGLETON,
                   frozen_candidate: bool = False,
                   seed_policy: str = "greedy-no-sampling",
                   git_info: Mapping[str, Any] | None = None,
                   difficulty_profile: Mapping[str, Any] | None = None,
                   ) -> dict[str, Any]:
    """Assemble the run manifest from actual runtime facts.

    Fail-closed bindings: the declared prompt bundle must hash to exactly
    what the pool renders; the request-contract key must resolve; a
    frozen-candidate run refuses a DRAFT prompt bundle.
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
    if frozen_candidate and not prompts.status.startswith("FROZEN"):
        raise ProfileError(
            f"frozen-candidate run refuses prompt bundle "
            f"{prompts.revision!r} with status {prompts.status!r}")
    profile = runtime.profile
    return {
        "schema_version": WORKER_EVAL_SCHEMA_VERSION,
        "run_id": run_id,
        "purpose": purpose,
        "status": "running",
        "git": dict(git_info) if git_info is not None else git_provenance(),
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
        "expected_rows": {"calls": expected_calls},
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


# --- run writer (81_f §5.1) --------------------------------------------------

class RunWriter:
    """Owns one run directory: manifest first (status `running`), call rows
    appended and flushed, then a final manifest with row counts, payload
    hashes and terminal status. Refuses an existing directory; an
    exception marks the run `aborted`; a clean exit that wrote fewer rows
    than planned also cannot look complete."""

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
        self._calls_path = self.run_dir / "calls.jsonl"
        self._calls = self._calls_path.open("x", encoding="utf-8")
        self._written = 0
        self.manifest_sha256: str | None = None

    @property
    def run_id(self) -> str:
        return self._manifest["run_id"]

    def _write_manifest(self) -> None:
        (self.run_dir / "manifest.json").write_text(
            json.dumps(self._manifest, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    def write_call(self, row: Mapping[str, Any]) -> None:
        if self._manifest["status"] != "running":
            raise InfrastructureError("run is finalized")
        self._calls.write(json.dumps(dict(row), sort_keys=True) + "\n")
        self._calls.flush()
        self._written += 1

    def _finalize(self, status: str) -> None:
        if self._manifest["status"] != "running":
            return
        self._calls.close()
        self._manifest["written_rows"] = {"calls": self._written}
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
        expected = self._manifest["expected_rows"]["calls"]
        if self._written != expected:
            self._finalize("aborted")
            raise InfrastructureError(
                f"run wrote {self._written} call rows but planned "
                f"{expected}; marked aborted")
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
