"""Versioned runtime profile, caching fingerprints, runtime lifecycle —
Stage 0B (plan rev6 §8, spec §1.10, §1.13).

The profile is the single serialized description of the execution
environment: it goes into every trace manifest and into W&B config, and its
fingerprints key the completion cache. Three fingerprints with distinct
scopes (§1.10):

- **runtime-profile fingerprint** (`rtp-…`) — the full profile, including
  the Conductor-side observation condition, cell mixture and batch shape.
  Governs Conductor-side generations and trace manifests.
- **worker-visible fingerprint** (`wv-…`) — everything a worker call can
  observe or depend on (model/tokenizer revisions, chat templates, NF4
  config, caps, truncation/stopping, greedy decoding, grammar/tool
  versions, disclosure/resource policy) but **not** the private/visible
  observation condition, so byte-identical worker requests intentionally
  share completions across visibility conditions (D11).
- **endpoint fingerprint** (`ep-…`) — the selected endpoint within the
  pool (name, model id + revision, chat-template bytes, per-worker caps).

Hashed configuration follows the §1.13 non-generator scope: canonical JSON
with strings and integers only; float-valued fields are encoded as
shortest-round-trip decimal strings, never JSON floats
(`encode_float`). `profiles.canonical_json` enforces this by rejecting raw
floats/bools at hash time.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from .profiles import ProfileError, canonical_json
from .types import ENDPOINT_NAMES, InfrastructureError

# Grammar/tool versioning (§1.10 "artifact grammar, tool version"): the
# executable grammar is frozen with the spec revision; any change to
# tools.py/contract.py behavior must bump this and thereby retire cached
# completions and qualification sets.
TOOL_VERSIONS: dict[str, str] = {
    "artifact_grammar": "cell-specs-v0.8",
    "lookup": "cell-specs-v0.8",
    "math": "cell-specs-v0.8",
    "code": "cell-specs-v0.8",
}

# The only disclosure/resource policy implemented in v0 (spec §1.2, §1.5):
# action-controlled disclosure, one authorized payload per step.
RESOURCE_POLICY = "action-controlled-disclosure-v0"

ENDPOINT_ORDER = tuple(ENDPOINT_NAMES[i] for i in sorted(ENDPOINT_NAMES))


def encode_float(value: float) -> str:
    """Shortest-round-trip decimal string (§1.13 hashed-config scope)."""
    text = repr(float(value))
    if float(text) != float(value):
        raise ProfileError(f"float {value!r} does not round-trip via {text}")
    return text


# --- profile schema ---------------------------------------------------------

# Stage 0B repo-default profile. Repo defaults are not the experiment: the
# named Stage-0C launch profile is a separate checked-in artifact with its
# own recorded numeric values (plan §8).
DEFAULT_RUNTIME_PROFILE: dict[str, Any] = {
    "profile_name": "stage0b-default",
    "schema_version": 1,
    "workers": {
        "lookup": {
            "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
            "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
            "max_new_tokens": 256,
            "microbatch": 16,
        },
        "math": {
            "model_id": "Qwen/Qwen2.5-Math-1.5B-Instruct",
            "revision": "aafeb0fc6f22cbf0eaeed126eff8be45b0360a35",
            "max_new_tokens": 256,
            "microbatch": 16,
        },
        "code": {
            "model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "revision": "2e1fd397ee46e1388853d2af2c993145b0f1098a",
            "max_new_tokens": 256,
            "microbatch": 16,
        },
    },
    "nf4": {
        "load_in_4bit": "true",
        "quant_type": "nf4",
        "double_quant": "true",
        "compute_dtype": "bfloat16",
    },
    "decoding": {
        # §1.10: cached completions presuppose greedy decoding.
        "do_sample": "false",
        "stopping": "eos",
    },
    "tools": dict(TOOL_VERSIONS),
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
    "cache_path": "runs/cache/conductor-completions.sqlite",
}

_TOP_LEVEL_KEYS = frozenset(DEFAULT_RUNTIME_PROFILE)
_WORKER_KEYS = frozenset({"model_id", "revision", "max_new_tokens",
                          "microbatch"})

# Conductor-side keys excluded from the worker-visible projection (§1.10):
# the observation condition, mixture and batch shape shape what the
# *Conductor* sees or how work is scheduled, never a worker request;
# `cache_path` is where completions are stored, not what they are;
# `profile_name` is a label. Moving the cache or renaming the profile must
# not orphan every cached completion.
_CONDUCTOR_ONLY_KEYS = frozenset({
    "profile_name", "visibility_condition", "cell_mixture",
    "workflow_max_steps", "policy_max_new_tokens", "batch", "cache_path",
})


def validate_runtime_profile(profile: Mapping[str, Any]) -> None:
    """Reject schema violations at load (mirrors profiles.validate_profile)."""
    if set(profile) != _TOP_LEVEL_KEYS:
        raise ProfileError(
            f"runtime profile keys {sorted(profile)} != required "
            f"{sorted(_TOP_LEVEL_KEYS)}")
    if set(profile["workers"]) != set(ENDPOINT_ORDER):
        raise ProfileError(f"workers must be exactly {ENDPOINT_ORDER}")
    for name, worker in profile["workers"].items():
        if set(worker) != _WORKER_KEYS:
            raise ProfileError(f"worker {name}: keys {sorted(worker)} != "
                               f"required {sorted(_WORKER_KEYS)}")
        for key in ("max_new_tokens", "microbatch"):
            value = worker[key]
            if not isinstance(value, int) or isinstance(value, bool) \
                    or value < 1:
                raise ProfileError(f"worker {name}.{key} must be a positive "
                                   f"integer, got {value!r}")
        for key in ("model_id", "revision"):
            if not isinstance(worker[key], str) or not worker[key]:
                raise ProfileError(f"worker {name}.{key} must be a non-empty "
                                   "string")
    if profile["visibility_condition"] not in ("private", "visible"):
        raise ProfileError("visibility_condition must be private|visible")
    if profile["decoding"].get("do_sample") != "false":
        raise ProfileError("decoding.do_sample must be the string 'false' "
                           "(§1.10: the cache presupposes greedy decoding)")
    if set(profile["cell_mixture"]) != set(
            DEFAULT_RUNTIME_PROFILE["cell_mixture"]):
        raise ProfileError("cell_mixture must cover exactly the six cells")
    # canonical_json rejects floats/bools anywhere in the tree, enforcing
    # the §1.13 string encoding for non-integer scalars.
    canonical_json(dict(profile))


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def runtime_profile_fingerprint(profile: Mapping[str, Any]) -> str:
    """Full-profile fingerprint — Conductor-side generations and manifests."""
    validate_runtime_profile(profile)
    return "rtp-" + _sha16(canonical_json(dict(profile)))


def worker_visible_projection(
        profile: Mapping[str, Any],
        chat_template_shas: Mapping[str, str]) -> dict[str, Any]:
    """The §1.10 worker-visible slice: profile minus Conductor-only keys,
    plus the resolved chat-template bytes hash per endpoint (the template
    is a property of the pinned tokenizer, resolved at build time)."""
    validate_runtime_profile(profile)
    if set(chat_template_shas) != set(ENDPOINT_ORDER):
        raise ProfileError("chat_template_shas must cover exactly "
                           f"{ENDPOINT_ORDER}")
    projection = {key: profile[key] for key in profile
                  if key not in _CONDUCTOR_ONLY_KEYS}
    projection["chat_template_sha256"] = dict(chat_template_shas)
    return projection


def worker_visible_fingerprint(
        profile: Mapping[str, Any],
        chat_template_shas: Mapping[str, str]) -> str:
    return "wv-" + _sha16(canonical_json(
        worker_visible_projection(profile, chat_template_shas)))


def endpoint_fingerprint(profile: Mapping[str, Any], endpoint_name: str,
                         chat_template_sha: str) -> str:
    """Selected-endpoint fingerprint: which worker, pinned exactly."""
    validate_runtime_profile(profile)
    if endpoint_name not in ENDPOINT_ORDER:
        raise ProfileError(f"unknown endpoint {endpoint_name!r}")
    record = {"endpoint": endpoint_name,
              "chat_template_sha256": chat_template_sha,
              **profile["workers"][endpoint_name]}
    return "ep-" + _sha16(canonical_json(record))


# --- runtime lifecycle ------------------------------------------------------

@dataclass(frozen=True)
class CallRecord:
    """One worker call's completion + §1.6 backend telemetry. Raw text and
    generation metadata only — never an executed WorkerResult (§1.10)."""
    completion: str
    finish_reason: str
    generated_tokens: int
    generation_hit_token_cap: bool
    cache_hit: bool
    request_sha256: str


class Runtime:
    """Built execution environment: pool + cache + fingerprints.

    `worker_call_batch(endpoint, user_messages)` is the one generation
    path: render each request through the endpoint's chat template
    (canonical rendered request, §1.5), consult the write-through cache
    (§1.10), batch-generate the misses, persist, and return records in
    input order.
    """

    def __init__(self, profile: Mapping[str, Any], pool: Any,
                 cache: Any) -> None:
        validate_runtime_profile(profile)
        self.profile = {key: profile[key] for key in profile}
        self.pool = pool
        self.cache = cache
        shas = {name: pool.chat_template_sha(name)
                for name in ENDPOINT_ORDER}
        self.runtime_profile_fingerprint = runtime_profile_fingerprint(profile)
        self.worker_visible_fingerprint = worker_visible_fingerprint(
            profile, shas)
        self.endpoint_fingerprints = {
            name: endpoint_fingerprint(profile, name, shas[name])
            for name in ENDPOINT_ORDER}
        self._closed = False

    def worker_call_batch(self, endpoint_name: str,
                          user_messages: list[str]) -> list[CallRecord]:
        if self._closed:
            raise InfrastructureError("runtime is closed")
        if endpoint_name not in ENDPOINT_ORDER:
            raise InfrastructureError(f"unknown endpoint {endpoint_name!r}")
        rendered = [self.pool.render_request(endpoint_name, user)
                    for user in user_messages]
        ep_fp = self.endpoint_fingerprints[endpoint_name]
        cached: list[CallRecord | None] = []
        for request in rendered:
            row = self.cache.lookup(self.worker_visible_fingerprint, ep_fp,
                                    request)
            cached.append(None if row is None else CallRecord(
                completion=row.completion, finish_reason=row.finish_reason,
                generated_tokens=row.generated_tokens,
                generation_hit_token_cap=row.generation_hit_token_cap,
                cache_hit=True,
                request_sha256=_request_sha(request)))
        # Deduplicate misses: byte-identical requests are one generation
        # (and one stored row) — batching nondeterminism across duplicate
        # in-flight requests must not race the greedy-decoding guard.
        unique_misses: dict[bytes, list[int]] = {}
        for index, row in enumerate(cached):
            if row is None:
                unique_misses.setdefault(rendered[index], []).append(index)
        if unique_misses:
            requests = list(unique_misses)
            generations = self.pool.generate(endpoint_name, requests)
            if len(generations) != len(requests):
                raise InfrastructureError(
                    f"pool returned {len(generations)} generations for "
                    f"{len(requests)} requests")
            for request, gen in zip(requests, generations):
                self.cache.store(self.worker_visible_fingerprint, ep_fp,
                                 request, gen)
                for index in unique_misses[request]:
                    cached[index] = CallRecord(
                        completion=gen.completion,
                        finish_reason=gen.finish_reason,
                        generated_tokens=gen.generated_tokens,
                        generation_hit_token_cap=gen.generation_hit_token_cap,
                        cache_hit=False,
                        request_sha256=_request_sha(request))
        if any(record is None for record in cached):
            raise InfrastructureError("unfilled cache slot after generation")
        return cached  # type: ignore[return-value]

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.pool.close()
            self.cache.close()

    def __enter__(self) -> "Runtime":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _request_sha(request_bytes: bytes) -> str:
    return hashlib.sha256(request_bytes).hexdigest()


def build_runtime(profile: Mapping[str, Any], pool: Any = None,
                  cache: Any = None) -> Runtime:
    """Assemble a Runtime. With no arguments this builds the real NF4 pool
    and the profile's SQLite cache; tests inject fakes for both."""
    validate_runtime_profile(profile)
    if pool is None:
        from .workers import WorkerPool
        pool = WorkerPool(profile)
    if cache is None:
        from .cache import CompletionCache
        cache = CompletionCache(profile["cache_path"])
    return Runtime(profile, pool, cache)
