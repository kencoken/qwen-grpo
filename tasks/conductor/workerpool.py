"""Four-worker registry — the 106_s §§4–5 pool contract.

Worker, endpoint family and physical checkpoint are distinct concepts
from this module on. A *worker* is a stable scientific identity (id,
name, endpoint family, exact checkpoint, exact resolved prompt bytes).
An *endpoint family* (lookup/math/code) selects the system prompt,
artifact parser and tool; families stay three-valued and are never the
action domain. A *physical checkpoint* is derived from the exact
`(model_id, model_revision)` key, never asserted by a label.

The action domain is `WORKER_IDS = (0, 1, 2, 3)`; the valid Stage-0C/2
action set is the exact enumeration of `4^S` assignments. One immutable
four-entry registry, used consistently by parser, executor, cache,
trace and oracle code, is the preferred didactic implementation
(106_s §5) — no plugin framework.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields
from types import MappingProxyType

from .profiles import canonical_json
from .types import ENDPOINT_NAMES


class WorkerPoolError(ValueError):
    """A worker pool declaration is malformed: a profile that omits,
    duplicates or relabels a worker fails closed (106_s §9.1)."""


ENDPOINT_FAMILIES = tuple(sorted(set(ENDPOINT_NAMES.values())))


@dataclass(frozen=True)
class WorkerSpec:
    """The minimal normative worker record (106_s §5). Decoding and
    runtime settings are profile-owned fingerprint inputs composed in at
    runtime construction; they are deliberately not duplicated here."""
    worker_id: int
    name: str
    endpoint_family: str
    model_id: str
    model_revision: str
    prompt_bundle_revision: str
    endpoint_system_prompt_sha256: str

    def weights_key(self) -> tuple[str, str]:
        """Checkpoint *weights* identity — the sharing-derivation input
        (106_s §5); a shorthand label is never an independent sharing
        claim. The complete physical key additionally includes
        quantization config and device, composed at the runtime
        boundary where those settings live (108_f)."""
        return (self.model_id, self.model_revision)


# The frozen Stage-0 pool (106_s §4 as recorded in its Freeze Record).
# Four logical workers over two physical checkpoints; one global rev10
# bundle (Lookup/Code bytes inherited from rev9, Math amended), so no
# mixed or nonexistent prompt configuration can be assembled from the
# component names.
_GENERIC_1P5B = ("Qwen/Qwen2.5-1.5B-Instruct",
                 "989aa7980e4cf806f80c7fef2b1adb7bc71aa306")
_GENERIC_3B = ("Qwen/Qwen2.5-3B-Instruct",
               "aa8e72537993ba99e69dfaafa59ed015b17504d1")
_REV10_PROMPT_SHA = {
    "lookup": "b013c142be2ed48fea221196f80bdbc0b8fb459c83a73c62c42c03986f6f952f",
    "math": "24c16a2115eceed072c0189692bf25799e59977f199829cc1f896e9da3b48787",
    "code": "9b08f3e6f4afad854484a13257d973e79e8664194f16cf44930644ab22e88aea",
}

STAGE0_WORKER_POOL: tuple[WorkerSpec, ...] = tuple(
    WorkerSpec(worker_id=worker_id, name=name, endpoint_family=family,
               model_id=checkpoint[0], model_revision=checkpoint[1],
               prompt_bundle_revision="rev10",
               endpoint_system_prompt_sha256=_REV10_PROMPT_SHA[family])
    for worker_id, name, family, checkpoint in (
        (0, "lookup_1p5b", "lookup", _GENERIC_1P5B),
        (1, "math_1p5b", "math", _GENERIC_1P5B),
        (2, "code_1p5b", "code", _GENERIC_1P5B),
        (3, "code_3b", "code", _GENERIC_3B),
    ))

WORKER_IDS: tuple[int, ...] = tuple(
    spec.worker_id for spec in STAGE0_WORKER_POOL)
# Immutable views (108_f): mutating dispatch must not be possible
# without changing the pool fingerprint.
WORKER_NAMES: "MappingProxyType[int, str]" = MappingProxyType(
    {spec.worker_id: spec.name for spec in STAGE0_WORKER_POOL})
WORKER_TO_ENDPOINT: "MappingProxyType[int, str]" = MappingProxyType(
    {spec.worker_id: spec.endpoint_family for spec in STAGE0_WORKER_POOL})
# Family *index* view for the three-valued artifact/tool boundary
# (contract.run_worker_output): workers 2 and 3 both resolve to the
# code family's index.
_FAMILY_INDEX = {name: index for index, name in ENDPOINT_NAMES.items()}
WORKER_TO_ENDPOINT_ID: "MappingProxyType[int, int]" = MappingProxyType(
    {spec.worker_id: _FAMILY_INDEX[spec.endpoint_family]
     for spec in STAGE0_WORKER_POOL})


def validate_worker_pool(specs: tuple[WorkerSpec, ...] | list[WorkerSpec]
                         ) -> tuple[WorkerSpec, ...]:
    """Fail-closed §9.1 check: exactly the ids 0..N-1 in order, unique
    names, known endpoint families with every family represented, and no
    empty identity field. Returns the validated immutable tuple."""
    specs = tuple(specs)
    if not specs:
        raise WorkerPoolError("a worker pool has at least one worker")
    for index, spec in enumerate(specs):
        if not isinstance(spec, WorkerSpec):
            raise WorkerPoolError(f"entry {index} is not a WorkerSpec")
        if spec.worker_id != index:
            raise WorkerPoolError(
                f"worker ids must be exactly 0..{len(specs) - 1} in "
                f"order; entry {index} has id {spec.worker_id}")
        if spec.endpoint_family not in ENDPOINT_FAMILIES:
            raise WorkerPoolError(
                f"worker {index}: unknown endpoint family "
                f"{spec.endpoint_family!r}")
        for spec_field in fields(spec):
            if spec_field.name == "worker_id":
                continue
            value = getattr(spec, spec_field.name)
            if not isinstance(value, str) or not value:
                raise WorkerPoolError(
                    f"worker {index}: {spec_field.name} must be a "
                    "non-empty string")
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise WorkerPoolError(f"duplicate worker names in {names}")
    families = {spec.endpoint_family for spec in specs}
    if families != set(ENDPOINT_FAMILIES):
        raise WorkerPoolError(
            f"pool families {sorted(families)} must cover exactly "
            f"{ENDPOINT_FAMILIES}")
    return specs


def worker_static_fingerprint(spec: WorkerSpec) -> str:
    """STATIC logical-worker identity hash (`lw-…`). This is the
    identity half only: the complete selected-logical-worker execution
    fingerprint (chat-template bytes, request contract, decoding, token
    caps, grammar/tool versions) is composed at the runtime boundary in
    unit 2, where those settings live (108_f). Two workers may share
    weights (0-2) or request bytes (2 and 3); they never share this
    identity."""
    record = {spec_field.name: getattr(spec, spec_field.name)
              for spec_field in fields(spec)}
    return "lw-" + hashlib.sha256(
        canonical_json(record).encode("utf-8")).hexdigest()[:16]


def worker_pool_fingerprint(specs: tuple[WorkerSpec, ...]) -> str:
    """Content hash (`wp-…`) of the validated ordered pool. Population
    and execution manifests bind this hash; a four-worker operation that
    receives a manifest without the expected pool hash fails closed
    (106_s §§8, 9.3)."""
    validate_worker_pool(specs)
    return "wp-" + hashlib.sha256(canonical_json(
        [worker_static_fingerprint(spec) for spec in specs]
    ).encode("utf-8")).hexdigest()[:16]


STAGE0_POOL_FINGERPRINT = worker_pool_fingerprint(STAGE0_WORKER_POOL)
