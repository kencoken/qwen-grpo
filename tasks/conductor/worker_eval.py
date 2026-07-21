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
from pathlib import Path
from typing import Any, Mapping

from . import program
from .profiles import DEFAULT_PROFILE, ProfileError, canonical_json, \
    profile_version
from .prompts import PromptBundle
from .render import ARTIFACT_FINAL_LINE
from .runtime import CallRecord, Runtime
from .types import InfrastructureError

WORKER_EVAL_SCHEMA_VERSION = 1
GENERATION_POLICY_SINGLETON = "singleton-v1"
CACHE_SOURCE_DISABLED = "disabled"


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
                    binding_sha256: str, record: CallRecord
                    ) -> dict[str, Any]:
    """One `called` row: identity, exact request/completion with digests,
    and §1.6 backend telemetry. Parse-stage and WorkerResult fields join
    in Tranche B; expected values never appear here."""
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
        "cache_source": CACHE_SOURCE_DISABLED,
    }


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
