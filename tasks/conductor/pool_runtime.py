"""Four-worker Stage-0B runtime — 106_s §§9.1–9.3 (unit 2).

The v2 runtime profile embeds the ordered `WorkerSpec` entries; loading
re-derives them and compares against the frozen registry, so a profile
that omits, duplicates or relabels a worker fails closed before any
tokenizer loads. Physical sharing is derived from each spec's weights
key: workers 0–2 share one resident generic-1.5B object, worker 3 uses
the generic-3B object, and parameter counts are verified against the
declared registry values at load, before any generation.

Generation is `singleton-v1`: the profile's scientific microbatch is
frozen at 1 and `generate_singleton` takes exactly one request. A
larger physical batch is a different worker policy (D16 measured
batch-composition sensitivity) and cannot be selected here.

The cache key is worker-visible execution fingerprint +
selected-logical-worker fingerprint (`slw-…`) + canonical rendered
request (106_s §9.3). Workers 2 and 3 share request bytes but never a
selector; workers 0–2 share weights but never a selector; byte-identical
requests still share across Conductor observation conditions exactly as
D11 requires, because those conditions are outside the worker-visible
projection.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from .cache import WorkerCompletionCache
from .profiles import ProfileError, canonical_json
from .prompts import PromptBundle, resolve_prompts
from .render import CONTRACT_TASK_LAST
from .runtime import (
    CallRecord, RESOURCE_POLICY, TOOL_VERSIONS, _CONDUCTOR_ONLY_KEYS,
    _request_sha, _sha16,
)
from .types import InfrastructureError
from .workerpool import (
    STAGE0_POOL_FINGERPRINT, STAGE0_WORKER_POOL, WorkerPoolError,
    WorkerSpec, validate_worker_pool, worker_pool_fingerprint,
)

POOL_PROFILE_SCHEMA_VERSION = 2

# Stage-0 four-worker repo-default profile (v2). As with v1, repo
# defaults are not the experiment: the named Stage-0C launch profile is
# a separate checked-in artifact (106_s §10.1).
FOUR_WORKER_RUNTIME_PROFILE: dict[str, Any] = {
    "profile_name": "stage0-four-worker",
    "schema_version": POOL_PROFILE_SCHEMA_VERSION,
    # The ordered WorkerSpec entries are the authoritative pool
    # declaration (106_s §5); validation re-derives and compares them
    # against the frozen registry rather than trusting the labels.
    "worker_pool": [
        {"worker_id": spec.worker_id, "name": spec.name,
         "endpoint_family": spec.endpoint_family,
         "model_id": spec.model_id,
         "model_revision": spec.model_revision,
         "prompt_bundle_revision": spec.prompt_bundle_revision,
         "endpoint_system_prompt_sha256":
             spec.endpoint_system_prompt_sha256}
        for spec in STAGE0_WORKER_POOL],
    # Shared scientific runtime settings: singleton-v1 physical batch.
    "worker_runtime": {"max_new_tokens": 256, "microbatch": 1},
    "nf4": {
        "load_in_4bit": "true",
        "quant_type": "nf4",
        "double_quant": "true",
        "compute_dtype": "bfloat16",
    },
    "decoding": {"do_sample": "false", "stopping": "eos"},
    "tools": dict(TOOL_VERSIONS),
    "prompts": {"d16_revision": "rev10"},
    "request_contract": CONTRACT_TASK_LAST,
    "resource_policy": RESOURCE_POLICY,
    "visibility_condition": "private",
    # Conductor-side fields (never worker-visible):
    "cell_mixture": {
        "lookup_atomic": 1, "math_atomic": 1, "code_atomic": 1,
        "lookup_math": 1, "math_code": 1, "fork_join": 0,
    },
    "workflow_max_steps": 3,
    "policy_max_new_tokens": 128,
    "batch": {"group_size": 8, "prompt_groups_per_update": 2},
    "cache_path": "runs/cache/conductor-worker-completions.sqlite",
}

_TOP_LEVEL_KEYS = frozenset(FOUR_WORKER_RUNTIME_PROFILE)


def profile_worker_pool(profile: Mapping[str, Any]
                        ) -> tuple[WorkerSpec, ...]:
    """Re-derive the profile's declared pool as WorkerSpecs (fail closed
    on unknown or missing fields)."""
    entries = profile["worker_pool"]
    if not isinstance(entries, list):
        raise ProfileError("worker_pool must be a list of worker records")
    specs = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ProfileError(f"worker_pool[{index}] must be an object")
        try:
            specs.append(WorkerSpec(**entry))
        except TypeError as exc:
            raise ProfileError(
                f"worker_pool[{index}] is not a WorkerSpec record: "
                f"{exc}") from exc
    try:
        return validate_worker_pool(specs)
    except WorkerPoolError as exc:
        raise ProfileError(f"worker_pool: {exc}") from exc


def validate_pool_profile(profile: Mapping[str, Any]) -> None:
    """106_s §9.1 fail-closed load: exactly the frozen pool, singleton
    physical batching, the frozen contract, and the bundle revision the
    pool declares."""
    if set(profile) != _TOP_LEVEL_KEYS:
        raise ProfileError(
            f"four-worker profile keys {sorted(profile)} != required "
            f"{sorted(_TOP_LEVEL_KEYS)}")
    if profile["schema_version"] != POOL_PROFILE_SCHEMA_VERSION:
        raise ProfileError(
            f"schema_version {profile['schema_version']!r} is not the "
            f"four-worker schema {POOL_PROFILE_SCHEMA_VERSION}")
    specs = profile_worker_pool(profile)
    if specs != STAGE0_WORKER_POOL or \
            worker_pool_fingerprint(specs) != STAGE0_POOL_FINGERPRINT:
        raise ProfileError(
            "worker_pool does not match the frozen Stage-0 registry "
            f"({STAGE0_POOL_FINGERPRINT}); a different pool needs a new "
            "reviewed registry, not a profile edit")
    runtime = profile["worker_runtime"]
    if set(runtime) != {"max_new_tokens", "microbatch"}:
        raise ProfileError("worker_runtime must hold exactly "
                           "max_new_tokens and microbatch")
    if not isinstance(runtime["max_new_tokens"], int) \
            or isinstance(runtime["max_new_tokens"], bool) \
            or runtime["max_new_tokens"] < 1:
        raise ProfileError("worker_runtime.max_new_tokens must be a "
                           "positive integer")
    if runtime["microbatch"] != 1:
        raise ProfileError(
            "worker_runtime.microbatch must be exactly 1: singleton-v1 "
            "is the frozen scientific worker policy (106_s §9.1); a "
            "larger physical batch is a different policy requiring a "
            "new preregistration")
    revisions = {spec.prompt_bundle_revision for spec in specs}
    if profile["prompts"] != {"d16_revision": next(iter(revisions))} \
            or len(revisions) != 1:
        raise ProfileError(
            f"prompts {profile['prompts']!r} must declare exactly the "
            f"pool's bundle revision {sorted(revisions)}")
    if profile["request_contract"] != CONTRACT_TASK_LAST:
        raise ProfileError(
            f"request_contract {profile['request_contract']!r} is not "
            f"the frozen {CONTRACT_TASK_LAST!r} (106_s §4)")
    if profile["decoding"] != {"do_sample": "false", "stopping": "eos"}:
        raise ProfileError("decoding must be greedy with eos stopping")
    if profile["visibility_condition"] not in ("private", "visible"):
        raise ProfileError("visibility_condition must be private|visible")
    canonical_json(dict(profile))


def pool_profile_fingerprint(profile: Mapping[str, Any]) -> str:
    validate_pool_profile(profile)
    return "rtp-" + _sha16(canonical_json(dict(profile)))


def pool_worker_visible_projection(
        profile: Mapping[str, Any],
        chat_template_shas: Mapping[str, str],
        system_prompt_shas: Mapping[str, str]) -> dict[str, Any]:
    """The §1.10 worker-visible slice of the v2 profile: everything a
    worker call can depend on, plus the per-worker resolved
    chat-template and system-prompt hashes (behavior, not labels).
    Conductor-only keys are excluded, so byte-identical requests share
    across observation conditions exactly as D11 requires."""
    validate_pool_profile(profile)
    names = {spec.name for spec in profile_worker_pool(profile)}
    for label, shas in (("chat_template_shas", chat_template_shas),
                        ("system_prompt_shas", system_prompt_shas)):
        if set(shas) != names:
            raise ProfileError(
                f"{label} must cover exactly the pool workers "
                f"{sorted(names)}")
    projection = {key: profile[key] for key in profile
                  if key not in _CONDUCTOR_ONLY_KEYS}
    projection["chat_template_sha256"] = dict(chat_template_shas)
    projection["system_prompt_sha256"] = dict(system_prompt_shas)
    return projection


def pool_worker_visible_fingerprint(
        profile: Mapping[str, Any],
        chat_template_shas: Mapping[str, str],
        system_prompt_shas: Mapping[str, str]) -> str:
    return "wv-" + _sha16(canonical_json(pool_worker_visible_projection(
        profile, chat_template_shas, system_prompt_shas)))


def selected_worker_fingerprint(profile: Mapping[str, Any],
                                spec: WorkerSpec,
                                chat_template_sha: str,
                                system_prompt_sha: str) -> str:
    """The selected-logical-worker execution fingerprint (`slw-…`) —
    the four-worker replacement for the v1 selected-endpoint
    fingerprint in the cache-key scope (106_s §9.3): worker identity,
    endpoint family, model revision, prompt and chat-template bytes,
    grammar/tool versions, quantization, decoding, caps and stopping."""
    validate_pool_profile(profile)
    record = {
        "worker_id": spec.worker_id,
        "name": spec.name,
        "endpoint_family": spec.endpoint_family,
        "model_id": spec.model_id,
        "model_revision": spec.model_revision,
        "prompt_bundle_revision": spec.prompt_bundle_revision,
        "system_prompt_sha256": system_prompt_sha,
        "chat_template_sha256": chat_template_sha,
        "request_contract": profile["request_contract"],
        "tool_version": profile["tools"][spec.endpoint_family],
        "artifact_grammar": profile["tools"]["artifact_grammar"],
        "nf4": dict(profile["nf4"]),
        "decoding": dict(profile["decoding"]),
        **profile["worker_runtime"],
    }
    return "slw-" + _sha16(canonical_json(record))


def physical_mapping(specs: tuple[WorkerSpec, ...],
                     nf4: Mapping[str, Any],
                     device: str) -> list[dict[str, Any]]:
    """Re-derived logical-to-physical mapping (106_s §5/§9.1): the
    complete physical key is weights + quantization + device."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for spec in specs:
        by_key.setdefault(spec.weights_key(), []).append(spec.name)
    return [{"model_id": key[0], "revision": key[1], "workers": names,
             "quantization": dict(nf4), "device": device}
            for key, names in sorted(by_key.items())]


class FourWorkerPool:
    """Real HF/bitsandbytes backend over the frozen four-worker pool.
    Tests substitute fakes implementing `chat_template_sha`,
    `system_prompt`, `render_request`, `generate_singleton`, `close`."""

    def __init__(self, profile: Mapping[str, Any], device: str = "cuda",
                 prompts: PromptBundle | None = None) -> None:
        validate_pool_profile(profile)
        self._profile = copy.deepcopy(dict(profile))
        self._specs = profile_worker_pool(self._profile)
        self._device = device
        self._prompts = (prompts if prompts is not None else resolve_prompts(
            self._profile["prompts"]["d16_revision"]))
        # Registered prompt SHAs are behavior claims: verify the bundle
        # actually resolves those bytes before anything renders.
        for spec in self._specs:
            actual = hashlib.sha256(self._prompts.text(
                spec.endpoint_family).encode("utf-8")).hexdigest()
            if actual != spec.endpoint_system_prompt_sha256:
                raise InfrastructureError(
                    f"worker {spec.name}: bundle "
                    f"{self._prompts.revision!r} resolves prompt "
                    f"{actual[:16]}…, registry declares "
                    f"{spec.endpoint_system_prompt_sha256[:16]}…")
        # Physical sharing is derived from the exact weights key; one
        # tokenizer/model object per key (106_s §9.1).
        self._tokenizers: dict[tuple[str, str], Any] = {}
        self._models: dict[tuple[str, str], Any] = {}
        for spec in self._specs:
            key = spec.weights_key()
            if key not in self._tokenizers:
                self._tokenizers[key] = self._load_tokenizer(spec)

    def _spec(self, worker_id: int) -> WorkerSpec:
        if not isinstance(worker_id, int) or isinstance(worker_id, bool) \
                or not 0 <= worker_id < len(self._specs):
            raise InfrastructureError(
                f"worker id {worker_id!r} is not in the registered pool")
        return self._specs[worker_id]

    def _load_tokenizer(self, spec: WorkerSpec) -> Any:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            spec.model_id, revision=spec.model_revision)
        if not getattr(tokenizer, "chat_template", None):
            raise InfrastructureError(
                f"{spec.model_id} has no chat template; the canonical "
                "rendered request is defined over one (§1.5)")
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left"
        return tokenizer

    # --- fingerprint inputs -------------------------------------------------

    def chat_template_sha(self, worker_id: int) -> str:
        template = self._tokenizers[
            self._spec(worker_id).weights_key()].chat_template
        return hashlib.sha256(template.encode("utf-8")).hexdigest()

    def system_prompt(self, worker_id: int) -> str:
        return self._prompts.text(self._spec(worker_id).endpoint_family)

    # --- canonical rendered request (§1.5, cache-key component) -------------

    def render_request(self, worker_id: int, user_message: str) -> bytes:
        spec = self._spec(worker_id)
        tokenizer = self._tokenizers[spec.weights_key()]
        text = tokenizer.apply_chat_template(
            [{"role": "system", "content": self.system_prompt(worker_id)},
             {"role": "user", "content": user_message}],
            tokenize=False, add_generation_prompt=True)
        return text.encode("utf-8")

    # --- generation ---------------------------------------------------------

    def _load_model(self, spec: WorkerSpec) -> Any:
        from .candidates import CHECKPOINT_PARAMETERS
        from .workers import load_nf4_checkpoint, measured_parameters
        key = spec.weights_key()
        if key not in self._models:
            model = load_nf4_checkpoint(spec.model_id, spec.model_revision,
                                        self._profile["nf4"], self._device)
            declared = CHECKPOINT_PARAMETERS.get(key)
            measured = measured_parameters(model)
            # §9.1: registered parameter counts are verified before any
            # generation; a mismatch is a hard stop, never a shrug.
            if declared is None or measured != declared:
                raise InfrastructureError(
                    f"checkpoint {key}: measured parameters {measured} "
                    f"!= declared {declared}")
            self._models[key] = model
        return self._models[key]

    def generate_singleton(self, worker_id: int, request: bytes):
        """One request, one physical generation — singleton-v1. There
        is deliberately no batched entry point on this pool."""
        import torch
        from .workers import WorkerPool
        spec = self._spec(worker_id)
        tokenizer = self._tokenizers[spec.weights_key()]
        model = self._load_model(spec)
        cap = self._profile["worker_runtime"]["max_new_tokens"]
        batch = tokenizer([request.decode("utf-8")], return_tensors="pt",
                          padding=True,
                          add_special_tokens=False).to(model.device)
        with torch.no_grad():
            output = model.generate(
                **batch, max_new_tokens=cap, do_sample=False,
                pad_token_id=tokenizer.pad_token_id)
        eos = model.generation_config.eos_token_id
        eos_ids = frozenset([eos] if isinstance(eos, int) else eos or [])
        row = output[0, batch["input_ids"].shape[1]:]
        return WorkerPool._decode_row(tokenizer, row, eos_ids)

    def checkpoint_report(self) -> list[dict[str, Any]]:
        """Actual physical layout: loaded checkpoints, the workers
        sharing them, and measured parameters."""
        report = []
        for entry in physical_mapping(self._specs, self._profile["nf4"],
                                      self._device):
            key = (entry["model_id"], entry["revision"])
            model = self._models.get(key)
            from .workers import measured_parameters
            report.append({
                "model_id": key[0], "revision": key[1],
                "workers": entry["workers"],
                "loaded": model is not None,
                "measured_parameters": (measured_parameters(model)
                                        if model is not None else None),
            })
        return report

    def close(self) -> None:
        self._models.clear()
        self._tokenizers.clear()


class FourWorkerRuntime:
    """Built four-worker execution environment: pool + worker cache +
    fingerprints. `worker_call_batch(worker_id, user_messages)` is the
    one generation path — the public boundary resolves everything
    through the registry-validated pool, and physical generation is
    singleton even when calls arrive in waves."""

    def __init__(self, profile: Mapping[str, Any], pool: Any,
                 cache: Any) -> None:
        validate_pool_profile(profile)
        if not isinstance(cache, WorkerCompletionCache):
            raise InfrastructureError(
                "the four-worker runtime requires a WorkerCompletionCache "
                "(106_s §8.5: the v1 endpoint-keyed cache is a different "
                "identity)")
        self.profile = copy.deepcopy(dict(profile))
        self.specs = profile_worker_pool(self.profile)
        self.pool = pool
        self.cache = cache
        chat_shas = {spec.name: pool.chat_template_sha(spec.worker_id)
                     for spec in self.specs}
        system_shas = {
            spec.name: hashlib.sha256(pool.system_prompt(
                spec.worker_id).encode("utf-8")).hexdigest()
            for spec in self.specs}
        self.pool_fingerprint = worker_pool_fingerprint(self.specs)
        self.runtime_profile_fingerprint = pool_profile_fingerprint(
            self.profile)
        self.worker_visible_fingerprint = pool_worker_visible_fingerprint(
            self.profile, chat_shas, system_shas)
        self.worker_fingerprints = {
            spec.worker_id: selected_worker_fingerprint(
                self.profile, spec, chat_shas[spec.name],
                system_shas[spec.name])
            for spec in self.specs}
        self.chat_template_shas = chat_shas
        self.system_prompt_shas = system_shas
        self.logical_to_physical = physical_mapping(
            self.specs, self.profile["nf4"],
            getattr(pool, "_device", "unknown"))
        self._closed = False

    def worker_call_batch(self, worker_id: int,
                          user_messages: list[str]) -> list[CallRecord]:
        if self._closed:
            raise InfrastructureError("runtime is closed")
        if worker_id not in self.worker_fingerprints:
            raise InfrastructureError(
                f"worker id {worker_id!r} is not in the registered pool")
        slw = self.worker_fingerprints[worker_id]
        rendered = [self.pool.render_request(worker_id, user)
                    for user in user_messages]
        cached: list[CallRecord | None] = []
        for request in rendered:
            row = self.cache.lookup(self.worker_visible_fingerprint, slw,
                                    request)
            cached.append(None if row is None else CallRecord(
                completion=row.completion, finish_reason=row.finish_reason,
                generated_tokens=row.generated_tokens,
                generation_hit_token_cap=row.generation_hit_token_cap,
                cache_hit=True,
                request_text=request.decode("utf-8"),
                request_sha256=_request_sha(request)))
        # Byte-identical in-flight requests are one singleton generation
        # and one stored row (greedy-decoding guard discipline as v1).
        unique_misses: dict[bytes, list[int]] = {}
        for index, row in enumerate(cached):
            if row is None:
                unique_misses.setdefault(rendered[index], []).append(index)
        for request, indices in unique_misses.items():
            gen = self.pool.generate_singleton(worker_id, request)
            self.cache.store(self.worker_visible_fingerprint, slw,
                             request, gen)
            for index in indices:
                cached[index] = CallRecord(
                    completion=gen.completion,
                    finish_reason=gen.finish_reason,
                    generated_tokens=gen.generated_tokens,
                    generation_hit_token_cap=gen.generation_hit_token_cap,
                    cache_hit=False,
                    request_text=request.decode("utf-8"),
                    request_sha256=_request_sha(request))
        if any(record is None for record in cached):
            raise InfrastructureError("unfilled cache slot after generation")
        return cached  # type: ignore[return-value]

    def close(self) -> None:
        if not self._closed:
            self.pool.close()
            self.cache.close()
            self._closed = True


def build_pool_runtime(profile: Mapping[str, Any], pool: Any,
                       cache: Any) -> FourWorkerRuntime:
    return FourWorkerRuntime(profile, pool, cache)


class PoolTraceWriter:
    """Pool-bound trace writer — trace schema v2 (106_s §9.2, 110_f).

    Deliberately NOT a `TraceWriter` subclass: the executor refuses that
    class outright. The manifest binds the pool fingerprint, per-worker
    execution fingerprints and the re-derived logical-to-physical
    mapping; every step row carries worker id and stable name, endpoint
    family, weights key and the selected-worker fingerprint."""

    def __init__(self, run_name: str, runtime: FourWorkerRuntime,
                 base_dir: Any = "runs") -> None:
        import json
        from datetime import datetime, timezone
        from pathlib import Path
        self._dir = Path(base_dir) / run_name / "traces"
        self._manifest_path = self._dir / "manifest.json"
        self._trace_path = self._dir / "steps.jsonl"
        if self._manifest_path.exists() or self._trace_path.exists():
            raise InfrastructureError(
                f"trace files already exist under {self._dir}; refusing "
                "to overwrite a recorded run")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._names = {spec.worker_id: spec.name
                       for spec in runtime.specs}
        self._families = {spec.worker_id: spec.endpoint_family
                          for spec in runtime.specs}
        self._weights = {spec.worker_id: list(spec.weights_key())
                         for spec in runtime.specs}
        self._worker_fps = {
            spec.worker_id: runtime.worker_fingerprints[spec.worker_id]
            for spec in runtime.specs}
        self._manifest = {
            "trace_schema_version": 2,
            "run_name": run_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_profile": runtime.profile,
            "runtime_profile_fingerprint":
                runtime.runtime_profile_fingerprint,
            "worker_visible_fingerprint":
                runtime.worker_visible_fingerprint,
            "worker_pool_fingerprint": runtime.pool_fingerprint,
            "worker_fingerprints": {
                self._names[worker_id]: fp
                for worker_id, fp in runtime.worker_fingerprints.items()},
            "logical_to_physical": runtime.logical_to_physical,
            "steps_written": 0,
            "closed": False,
        }
        self._json = json
        self._write_manifest()
        self._file = self._trace_path.open("x", encoding="utf-8")
        self._steps_written = 0

    def _write_manifest(self) -> None:
        self._manifest_path.write_text(
            self._json.dumps(self._manifest, indent=1, sort_keys=True)
            + "\n", encoding="utf-8")

    def write_step(self, item_id: str, record: Any,
                   call_record: Any | None) -> None:
        worker_id = record.worker_id
        if worker_id not in self._names:
            raise InfrastructureError(
                f"worker id {worker_id!r} is not in this trace's pool")
        result = record.result
        line = {
            "item_id": item_id,
            "position": record.position,
            "worker_id": worker_id,
            "worker_name": self._names[worker_id],
            "endpoint_family": self._families[worker_id],
            "weights_key": self._weights[worker_id],
            "selected_worker_fp": self._worker_fps[worker_id],
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
            "finish_reason": getattr(call_record, "finish_reason", None),
            "generated_tokens": getattr(call_record, "generated_tokens",
                                        None),
            "generation_hit_token_cap": getattr(
                call_record, "generation_hit_token_cap", None),
            "cache_hit": getattr(call_record, "cache_hit", None),
            "request_sha256": getattr(call_record, "request_sha256", None),
        }
        self._file.write(self._json.dumps(line, sort_keys=True) + "\n")
        self._file.flush()
        self._steps_written += 1

    def close(self) -> None:
        if not self._manifest["closed"]:
            self._file.close()
            self._manifest["steps_written"] = self._steps_written
            self._manifest["closed"] = True
            self._write_manifest()

    def __enter__(self) -> "PoolTraceWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
