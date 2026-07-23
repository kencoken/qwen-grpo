"""106_s §8 regression battery for the four-worker registry contract.

Routing bijection and the 4^S oracle/control fixtures live with the
existing parser/oracle tests; this file pins the registry itself: the
frozen Stage-0 pool identities, worker/endpoint/checkpoint separation,
fingerprint distinctness, fail-closed pool validation, and the
three-vs-four-worker bundle mixing refusal.
"""

import dataclasses
import hashlib
import json

import pytest

from tasks.conductor import oracle
from tasks.conductor.workerpool import (
    STAGE0_POOL_FINGERPRINT, STAGE0_WORKER_POOL, WORKER_IDS, WORKER_NAMES,
    WORKER_TO_ENDPOINT, WORKER_TO_ENDPOINT_ID, WorkerPoolError, WorkerSpec,
    validate_worker_pool, worker_pool_fingerprint, worker_static_fingerprint,
)


def test_stage0_pool_is_the_frozen_106s_table():
    assert WORKER_IDS == (0, 1, 2, 3)
    assert dict(WORKER_NAMES) == {0: "lookup_1p5b", 1: "math_1p5b",
                                  2: "code_1p5b", 3: "code_3b"}
    assert dict(WORKER_TO_ENDPOINT) == {0: "lookup", 1: "math",
                                        2: "code", 3: "code"}
    assert dict(WORKER_TO_ENDPOINT_ID) == {0: 0, 1: 1, 2: 2, 3: 2}
    # Immutable views (108_s): dispatch cannot be mutated in place.
    for view in (WORKER_NAMES, WORKER_TO_ENDPOINT, WORKER_TO_ENDPOINT_ID):
        with pytest.raises(TypeError):
            view[3] = "mutated"  # type: ignore[index]
    for spec in STAGE0_WORKER_POOL:
        assert spec.prompt_bundle_revision == "rev10"
    # Two physical checkpoints, derived from the exact key.
    keys = {spec.weights_key() for spec in STAGE0_WORKER_POOL}
    assert len(keys) == 2
    assert STAGE0_WORKER_POOL[3].weights_key() == (
        "Qwen/Qwen2.5-3B-Instruct",
        "aa8e72537993ba99e69dfaafa59ed015b17504d1")
    # Golden pool fingerprint: any identity change is a deliberate,
    # reviewed regeneration, never drift.
    assert STAGE0_POOL_FINGERPRINT == "wp-197e286115f56e4a"


def test_registry_prompt_hashes_match_the_prompt_registry():
    """The registry's per-worker prompt SHAs must be the hashes of the
    bytes the rev10 bundle actually resolves — the 106_s §4 guarantee
    that no mixed prompt configuration can be assembled."""
    from tasks.conductor.prompts import resolve_prompts
    bundle = resolve_prompts("rev10")
    for spec in STAGE0_WORKER_POOL:
        expected = hashlib.sha256(
            bundle.text(spec.endpoint_family).encode("utf-8")).hexdigest()
        assert spec.endpoint_system_prompt_sha256 == expected, spec.name


def test_both_code_workers_share_family_but_never_identity():
    """Workers 2 and 3 share the Code grammar/tool family and (via one
    shared chat template and prompt) byte-identical requests; their
    results are attributable only to checkpoint, and their cache
    identities never collide (106_s §§6.2, 9.3)."""
    w2, w3 = STAGE0_WORKER_POOL[2], STAGE0_WORKER_POOL[3]
    assert w2.endpoint_family == w3.endpoint_family == "code"
    assert w2.endpoint_system_prompt_sha256 == w3.endpoint_system_prompt_sha256
    assert w2.weights_key() != w3.weights_key()
    assert worker_static_fingerprint(w2) != worker_static_fingerprint(w3)


def test_shared_checkpoint_workers_never_share_prompt_identity():
    """Workers 0-2 share one physical checkpoint object; their prompt
    identities and worker fingerprints all differ (106_s §8)."""
    shared = [STAGE0_WORKER_POOL[i] for i in (0, 1, 2)]
    assert len({spec.weights_key() for spec in shared}) == 1
    assert len({spec.endpoint_system_prompt_sha256
                for spec in shared}) == 3
    fingerprints = [worker_static_fingerprint(spec) for spec in STAGE0_WORKER_POOL]
    assert len(set(fingerprints)) == 4


def _respec(index, **changes):
    spec = STAGE0_WORKER_POOL[index]
    return dataclasses.replace(spec, **changes)


@pytest.mark.parametrize("mutate", [
    lambda pool: pool[:2],                            # code family missing
    lambda pool: pool + (pool[3],),                   # duplicate id
    lambda pool: (pool[0], pool[2], pool[1], pool[3]),  # relabeled order
    lambda pool: pool[:3] + (_respec(3, name="code_1p5b"),),  # dup name
    lambda pool: pool[:3] + (_respec(3, endpoint_family="coder"),),
    lambda pool: pool[:3] + (_respec(3, model_revision=""),),
    lambda pool: (),
])
def test_pool_validation_fails_closed(mutate):
    with pytest.raises(WorkerPoolError):
        validate_worker_pool(mutate(STAGE0_WORKER_POOL))


def test_structural_validity_is_not_pool_identity():
    """Dropping worker 3 still validates structurally (families remain
    covered) — binding an operation to the exact Stage-0 pool is the
    pool fingerprint's job, not the structural validator's."""
    shorter = validate_worker_pool(STAGE0_WORKER_POOL[:3])
    assert worker_pool_fingerprint(shorter) != STAGE0_POOL_FINGERPRINT


def test_pool_fingerprint_binds_every_identity_field():
    base = worker_pool_fingerprint(STAGE0_WORKER_POOL)
    changed = STAGE0_WORKER_POOL[:3] + (
        _respec(3, model_revision="0" * 40),)
    assert worker_pool_fingerprint(changed) != base


def test_controls_and_surfaces_derive_from_the_registry():
    """§8: best_fixed / random / runner-up / one-call / two-call all
    come from the same registry-derived candidate sets."""
    assert oracle.enumerate_assignments(1) == [(w,) for w in WORKER_IDS]
    assert len(oracle.enumerate_assignments(3)) == 4 ** 3
    workflows = oracle.enumerate_two_call_workflows()
    assert len(workflows) == 2 * len(WORKER_IDS) ** 2
    assert {pair for _, pair in workflows} == {
        (a, b) for a in WORKER_IDS for b in WORKER_IDS}


def test_worker_3_participates_in_selection_and_ties():
    """Deterministic lexicographic ties across all four workers: worker
    3 wins only strictly, never a tie (106_s §6.3)."""
    from test_conductor_executor import cluster_ids, observation_id
    cluster = cluster_ids("code_atomic", 1)[0]

    def surface(values):
        return oracle.validate_payoff_surface(
            {(w,): {cluster: {observation_id(cluster): values[w]}}
             for w in WORKER_IDS}, "code_atomic")

    tied = surface({0: 0, 1: 1, 2: 0, 3: 1})       # 1 ties 3 -> lowest id
    assert oracle.select_deployable(tied) == (1,)
    strict = surface({0: 0, 1: 0, 2: 0, 3: 1})     # 3 strictly best
    assert oracle.select_deployable(strict) == (3,)
    assert oracle.best_fixed(strict) == (3,)
    assert oracle.node_runner_up(strict, (3,), 0) == (0,)  # others tie -> 0


def test_three_and_four_worker_bundles_cannot_be_mixed():
    """A persisted three-worker artifact must fail closed against the
    four-worker validators and digests (106_s §8)."""
    from test_conductor_executor import cluster_ids, observation_id
    cluster = cluster_ids("code_atomic", 1)[0]
    three_worker = {(w,): {cluster: {observation_id(cluster): 1}}
                    for w in (0, 1, 2)}
    with pytest.raises(oracle.PayoffSurfaceError, match="full enumeration"):
        oracle.validate_payoff_surface(three_worker, "code_atomic")
    # Digest schema: a surfdig1-era digest can never match a rebuilt
    # four-worker bundle digest.
    full = oracle.validate_payoff_surface(
        {(w,): {cluster: {observation_id(cluster): 1}}
         for w in WORKER_IDS}, "code_atomic")
    bundle = oracle.CalibrationBundle(assignment=full)
    digest = bundle.surface_digest()
    assert digest.startswith("surfdig2-")
    frozen = bundle.freeze_selections()
    stale = dataclasses.replace(
        frozen, source_surface_digest="surfdig1-" + "0" * 32)
    with pytest.raises(oracle.PayoffSurfaceError):
        stale.verify_against(bundle)


# =============================================================================
# 108_s finding 4: persisted payoff identity binds the pool fingerprint.
# =============================================================================

def _atomic_full_surface():
    from test_conductor_executor import cluster_ids, observation_id
    cluster = cluster_ids("code_atomic", 1)[0]
    return oracle.validate_payoff_surface(
        {(w,): {cluster: {observation_id(cluster): 1}}
         for w in WORKER_IDS}, "code_atomic")


def test_surface_json_carries_and_verifies_the_pool_fingerprint():
    surface = _atomic_full_surface()
    obj = surface.to_json()
    assert obj["worker_pool"] == STAGE0_POOL_FINGERPRINT
    assert oracle.ValidatedSurface.from_json(obj).worker_pool == \
        STAGE0_POOL_FINGERPRINT
    # A same-cardinality surface from a *different* pool fails closed.
    foreign = dict(obj, worker_pool="wp-0000000000000000")
    with pytest.raises(oracle.PayoffSurfaceError, match="bound to worker"):
        oracle.ValidatedSurface.from_json(foreign)
    # A pool-free (pre-108_s) persisted surface fails the exact-key check.
    legacy = {k: v for k, v in obj.items() if k != "worker_pool"}
    with pytest.raises(oracle.PayoffSurfaceError, match="keys must be"):
        oracle.ValidatedSurface.from_json(legacy)


def test_frozen_selections_carry_and_verify_the_pool_fingerprint():
    bundle = oracle.CalibrationBundle(assignment=_atomic_full_surface())
    frozen = bundle.freeze_selections()
    assert frozen.worker_pool == STAGE0_POOL_FINGERPRINT
    obj = frozen.to_json()
    assert obj["worker_pool"] == STAGE0_POOL_FINGERPRINT
    assert oracle.FrozenSelections.from_json(obj) == frozen
    with pytest.raises(oracle.PayoffSurfaceError, match="bound to worker"):
        oracle.FrozenSelections.from_json(
            dict(obj, worker_pool="wp-0000000000000000"))
    legacy = {k: v for k, v in obj.items() if k != "worker_pool"}
    with pytest.raises(oracle.PayoffSurfaceError, match="keys must be"):
        oracle.FrozenSelections.from_json(legacy)
    # The digest binds the pool too: same outcomes under a different
    # pool could never reproduce this digest, because to_json embeds it.
    assert "worker_pool" in json.dumps(bundle.assignment.to_json())
