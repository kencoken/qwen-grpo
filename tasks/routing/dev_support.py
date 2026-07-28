"""Development-namespace payoff surfaces (211_f §4).

The Stage-0 `payoff_support` machinery is frozen (SOURCE_DIGEST_FILES),
so this module re-implements the declaration → materialization →
fail-closed reload lifecycle PARAMETERIZED by cohort, importing the
frozen executable pieces (assignment enumeration, workflow items,
terminal scoring, trace writer) rather than copying them. Differences
from the Stage-0 support, all deliberate:

- the cohort (namespace, per-cell latent indices, renderers,
  visibility) is an argument, frozen per tranche — not module
  constants; the declaration is persisted INSIDE the surface directory
  and hash-bound by the manifest (the tranche freeze commits it too);
- disclosure is a first-class product: `direction_yields` reports
  every materialized row's direction so nothing screened is silent
  (211_f §4 step 4);
- `select_c_fixed_dev` (210_s issue 1) is selected here, on the
  outcome-blind support, and persisted with both candidate scores.

Every surface this module produces is development data permanently.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor import executor, oracle, program
from tasks.conductor.payoff_support import (
    _assignment_items, _exact_int, _sha_file,
)
from tasks.conductor.pool_runtime import PoolTraceWriter
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.stage1_replay import eligible_pair_table
from tasks.conductor.types import CELL_IDS, InfrastructureError
from tasks.conductor.workerpool import STAGE0_POOL_FINGERPRINT, WORKER_IDS

from .charter import DEV_NAMESPACES, content_sha256

DEV_SURFACE_SCHEMA_VERSION = 1
_DEV_MANIFEST_KEYS = frozenset({
    "surface_schema_version", "support", "declaration_sha256",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "planned_step_executions",
    "executed_step_records", "uncached_step_records",
    "unique_singleton_generations", "cache_hits", "payoff_rows",
    "wall_seconds", "payoffs_sha256", "trace_manifest_sha256",
    "trace_steps_sha256",
})
_ROW_KEYS = frozenset({"observation_id", "assignment", "payoff",
                       "terminal_value", "step_statuses"})


# --- cohorts and observations -------------------------------------------------

def validate_dev_cohort(namespace: str,
                        cohort: Mapping[str, Any],
                        renderers: tuple[str, ...] | list[str],
                        visibility: str) -> None:
    """A development cohort spec is exact: a dev namespace, per-cell
    duplicate-free integer index lists inside the namespace cap, known
    renderers, one visibility condition. 214_s: every development
    cohort covers ALL SIX cells and the COMPLETE renderer crossing —
    the charter's populations (support, probe, val, cycle) all do,
    and a partial population must never masquerade as one."""
    from tasks.conductor.program import namespace_cap
    from tasks.conductor.types import RENDERER_IDS, VISIBILITY_CONDITIONS
    if namespace not in DEV_NAMESPACES:
        raise InfrastructureError(
            f"{namespace!r} is not a development namespace "
            f"{DEV_NAMESPACES}")
    if not cohort:
        raise InfrastructureError("empty development cohort")
    if set(cohort) != set(CELL_IDS):
        raise InfrastructureError(
            f"development cohorts cover all six cells "
            f"{sorted(CELL_IDS)}; got {sorted(cohort)} (214_s)")
    for cell, indices in cohort.items():
        if cell not in CELL_IDS:
            raise InfrastructureError(f"unknown cell {cell!r}")
        if not indices or not isinstance(indices, (list, tuple)):
            raise InfrastructureError(f"{cell}: empty index list")
        seen = set()
        cap = namespace_cap(namespace, cell)
        for idx in indices:
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise InfrastructureError(
                    f"{cell}: non-integer latent index {idx!r}")
            if not 0 <= idx < cap:
                raise InfrastructureError(
                    f"{cell}: index {idx} outside [0, {cap})")
            if idx in seen:
                raise InfrastructureError(
                    f"{cell}: duplicate latent index {idx}")
            seen.add(idx)
    if not renderers:
        raise InfrastructureError("cohort declares no renderers")
    if list(renderers) != list(RENDERER_IDS):
        raise InfrastructureError(
            f"development cohorts cross ALL renderers in canonical "
            f"order {RENDERER_IDS}; got {tuple(renderers)!r} (214_s)")
    if visibility not in VISIBILITY_CONDITIONS:
        raise InfrastructureError(f"unknown visibility {visibility!r}")


def dev_cohort_observations(namespace: str,
                            cohort: Mapping[str, Any],
                            renderers: tuple[str, ...] | list[str],
                            visibility: str) -> list[dict[str, Any]]:
    """Regenerate the cohort's observations from the frozen generator in
    canonical (cell, index, renderer) order — the declaration verifies
    these, never the other way around."""
    validate_dev_cohort(namespace, cohort, renderers, visibility)
    observations = []
    for cell in sorted(cohort):
        for index in sorted(cohort[cell]):
            latent = program.generate_latent(
                cell, namespace, index, DEFAULT_PROFILE).latent
            positions = latent["reference_program"]["positions"]
            for renderer in renderers:
                inst = program.render_instance(latent, renderer,
                                               visibility)
                observations.append({
                    "observation_id": inst["render_instance_id"],
                    "cell_id": cell,
                    "renderer_id": renderer,
                    "latent_program_id": latent["latent_program_id"],
                    "num_nodes": len(positions),
                    "latent": latent,
                    "instance": inst,
                })
    return observations


# --- declaration ---------------------------------------------------------------

def cache_identity_of(profile: Mapping[str, Any]) -> str:
    """The frozen cache-key contract: the slw-keyed worker-completion
    table under the profile's request contract (106_s §8.5)."""
    return f"worker_completions/slw/{profile['request_contract']}"


def build_dev_declaration(rt: Any, *, tag: str, namespace: str,
                          cohort: Mapping[str, Any],
                          renderers: tuple[str, ...] | list[str],
                          visibility: str) -> dict[str, Any]:
    """Identities + fingerprints + the exact cohort spec, computed from
    a RUNTIME bound to the frozen profile, BEFORE materialization —
    including the runtime-profile fingerprint, request contract and
    cache identity (214_s P1: the declaration binds the execution it
    authorizes, not just the pool). The tranche freeze commits this
    record; materialization persists it beside the surface and binds
    it by content hash."""
    import hashlib
    pool = rt.pool
    profile = pool.profile
    from tasks.conductor.pool_runtime import (
        pool_worker_visible_fingerprint,
    )
    chat_shas, system_shas = {}, {}
    for entry in profile["worker_pool"]:
        worker_id, name = entry["worker_id"], entry["name"]
        chat_shas[name] = pool.chat_template_sha(worker_id)
        system_shas[name] = hashlib.sha256(pool.system_prompt(
            worker_id).encode("utf-8")).hexdigest()
    observations = dev_cohort_observations(namespace, cohort, renderers,
                                           visibility)
    planned = sum(len(oracle.enumerate_assignments(obs["num_nodes"]))
                  * obs["num_nodes"] for obs in observations)
    return {
        "support": tag,
        "namespace": namespace,
        "cohort": {cell: sorted(cohort[cell]) for cell in sorted(cohort)},
        "renderers": list(renderers),
        "visibility": visibility,
        "observations": [
            {"observation_id": obs["observation_id"],
             "cell_id": obs["cell_id"],
             "renderer_id": obs["renderer_id"],
             "num_nodes": obs["num_nodes"],
             "assignments": len(oracle.enumerate_assignments(
                 obs["num_nodes"]))}
            for obs in observations],
        "planned_step_executions": planned,
        "worker_ids": list(WORKER_IDS),
        "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
        "worker_visible_fingerprint": pool_worker_visible_fingerprint(
            profile, chat_shas, system_shas),
        "runtime_profile_fingerprint": rt.runtime_profile_fingerprint,
        "request_contract": profile["request_contract"],
        "cache_identity": cache_identity_of(profile),
        "prompt_revision": profile["prompts"]["d16_revision"],
        "device": profile["device"],
    }


def _verify_dev_declaration(declaration: Mapping[str, Any],
                            observations: list[dict[str, Any]]) -> None:
    """Verify the COMPLETE regenerated cohort description against the
    declaration — identities, cells, renderers, arities, assignment
    counts and the cohort spec itself."""
    regenerated = [
        {"observation_id": obs["observation_id"],
         "cell_id": obs["cell_id"],
         "renderer_id": obs["renderer_id"],
         "num_nodes": obs["num_nodes"],
         "assignments": len(oracle.enumerate_assignments(
             obs["num_nodes"]))}
        for obs in observations]
    checks = {
        "observations": regenerated,
        "planned_step_executions": sum(
            obs["assignments"] * obs["num_nodes"]
            for obs in regenerated),
        "worker_ids": list(WORKER_IDS),
        "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
    }
    for key, expected in checks.items():
        if declaration.get(key) != expected:
            raise InfrastructureError(
                f"dev declaration field {key!r} does not match the "
                "regenerated cohort description; the generator or the "
                "declaration moved")


# --- materialization -----------------------------------------------------------

def materialize_dev_support(rt: Any, declaration: Mapping[str, Any],
                            out_dir: str | Path, *,
                            launch_manifest: Mapping[str, Any],
                            environment_manifest: Mapping[str, Any],
                            expected_manifest_sha256: str,
                            ledger_path: str | Path,
                            expected_head_sha256: str
                            ) -> dict[str, Any]:
    """Execute the complete declared 4^S surface through a runtime
    whose identity matches the declaration, CONSUMING the externally
    frozen support-launch manifest (218_s F1) AND the recorded ledger
    admission (220_s F1: the current ledger head must be the ADMITTED
    support-launch entry naming exactly this manifest and budget —
    materialization cannot run unadmitted, and the recorded launch is
    the executed launch), then persisting the manifest and the
    environment bytes beside the surface for the post-run lock to
    extend. Mirrors the frozen Stage-0 materializer."""
    from .ledger import verify_ledger_head
    launch_manifest = validate_support_launch_manifest(
        launch_manifest, declaration)
    if launch_manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "support-launch manifest is not the externally frozen one "
            "(218_s F1)")
    if launch_manifest["environment_manifest_sha256"] != \
            validate_environment_manifest_binding(environment_manifest):
        raise InfrastructureError(
            "environment manifest is not the one the launch manifest "
            "binds")
    entries = verify_ledger_head(expected_head_sha256, ledger_path)
    if not entries or entries[-1]["kind"] != "support_materialization":
        raise InfrastructureError(
            "the ledger head is not an admitted support launch — "
            "materialization cannot run unadmitted (220_s F1)")
    admitted = entries[-1]
    if admitted["freeze"].get("support_launch_sha256") != \
            launch_manifest["manifest_sha256"]:
        raise InfrastructureError(
            "the admitted launch entry names a different "
            "support-launch manifest (220_s F1)")
    if admitted["budget_allocated_gpu_hours"] != \
            launch_manifest["budget_gpu_hours"]:
        raise InfrastructureError(
            "the admitted budget differs from the manifest budget "
            "(220_s F1)")
    for key, expected in (
            ("worker_visible_fingerprint", rt.worker_visible_fingerprint),
            ("worker_pool_fingerprint", rt.pool_fingerprint),
            ("runtime_profile_fingerprint",
             rt.runtime_profile_fingerprint),
            ("request_contract", rt.profile["request_contract"]),
            ("cache_identity", cache_identity_of(rt.profile))):
        if declaration.get(key) != expected:
            raise InfrastructureError(
                f"runtime {key} {expected!r} does not match the declared "
                f"{declaration.get(key)!r}; the support binds one "
                "execution identity (214_s P1)")
    if rt.profile["visibility_condition"] != declaration["visibility"]:
        raise InfrastructureError(
            f"runtime visibility {rt.profile['visibility_condition']!r} "
            f"does not match the declared {declaration['visibility']!r}")
    out_dir = Path(out_dir)
    payoff_path = out_dir / "payoffs.jsonl"
    manifest_path = out_dir / "manifest.json"
    declaration_path = out_dir / "declaration.json"
    launch_path = out_dir / "support_launch.json"
    env_path = out_dir / "env_manifest.json"
    if payoff_path.exists() or manifest_path.exists() \
            or declaration_path.exists() or launch_path.exists() \
            or env_path.exists():
        raise InfrastructureError(
            f"{out_dir} already holds a materialized surface; refusing "
            "to overwrite a recorded artifact")
    out_dir.mkdir(parents=True, exist_ok=True)

    observations = dev_cohort_observations(
        declaration["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    _verify_dev_declaration(declaration, observations)
    declaration_path.write_text(
        json.dumps(declaration, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    launch_path.write_text(
        json.dumps(dict(launch_manifest), indent=1, sort_keys=True)
        + "\n", encoding="utf-8")
    env_path.write_text(
        json.dumps(dict(environment_manifest), indent=1,
                   sort_keys=True) + "\n", encoding="utf-8")

    started = time.monotonic()
    generations_before = getattr(rt.pool, "singleton_generations", 0)
    executed_steps = 0
    uncached_records = 0
    cache_hits = 0
    rows = []
    with PoolTraceWriter("traces", rt, base_dir=out_dir) as trace:
        for obs in observations:
            gold = obs["instance"]["gold_answer"]
            pairs = _assignment_items(
                obs, rt.profile["request_contract"])
            results, telemetry = rt.execute_batch(
                [item for _, item in pairs], trace=trace)
            for record_pair, result in zip(pairs, results):
                assignment, _item = record_pair
                payoff = executor.score_terminal(result.terminal, gold)
                executed_steps += sum(
                    1 for step in result.steps
                    if step.completion is not None)
                rows.append({
                    "observation_id": obs["observation_id"],
                    "assignment": list(assignment),
                    "payoff": payoff,
                    "terminal_value": result.terminal,
                    "step_statuses": [
                        step.result.status if step.result
                        else f"world:{step.world_failure}"
                        for step in result.steps],
                })
            uncached_records += sum(
                1 for _, record in telemetry if not record.cache_hit)
            cache_hits += sum(
                1 for _, record in telemetry if record.cache_hit)
    wall = time.monotonic() - started

    with payoff_path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    trace_dir = out_dir / "traces" / "traces"
    manifest = {
        "surface_schema_version": DEV_SURFACE_SCHEMA_VERSION,
        "support": declaration["support"],
        "declaration_sha256": _sha_file(declaration_path),
        "worker_visible_fingerprint": rt.worker_visible_fingerprint,
        "runtime_profile_fingerprint": rt.runtime_profile_fingerprint,
        "worker_pool_fingerprint": rt.pool_fingerprint,
        "planned_step_executions":
            declaration["planned_step_executions"],
        "executed_step_records": executed_steps,
        "uncached_step_records": uncached_records,
        "unique_singleton_generations":
            getattr(rt.pool, "singleton_generations", 0)
            - generations_before,
        "cache_hits": cache_hits,
        "payoff_rows": len(rows),
        "wall_seconds": round(wall, 1),
        "payoffs_sha256": _sha_file(payoff_path),
        "trace_manifest_sha256": _sha_file(trace_dir / "manifest.json"),
        "trace_steps_sha256": _sha_file(trace_dir / "steps.jsonl"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest


# --- support-launch manifest and post-run surface lock (218_s F1) --------------
#
# ONE pre-launch manifest binds every prelaunch input: the exact
# declaration (cohort + runtime/pool/cache identity), the frozen
# probe rule, the search cap, the budget, the recomputed source
# digest with the actual driver, and the CANONICAL Stage-1
# environment manifest (validated by the stage1 validator, which
# ties it to the current source identity — a fictional manifest
# cannot pass). Materialization consumes the manifest's EXTERNALLY
# frozen hash and persists both the manifest and the environment
# bytes; the surface lock extends the persisted manifest with the
# output hashes.

SUPPORT_LAUNCH_KIND = "routing-dev-support-launch-v1"
SURFACE_LOCK_KIND = "routing-dev-surface-lock-v3"
_SUPPORT_LAUNCH_KEYS = frozenset({
    "kind", "declaration_sha256", "namespace",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "request_contract", "cache_identity",
    "probe_rule_sha256", "search_cap", "budget_gpu_hours",
    "routing_source_sha256", "driver", "environment_manifest_sha256",
})
_LOCK_KEYS = frozenset({
    "lock", "support", "support_launch_sha256", "declaration_sha256",
    "manifest_sha256", "payoffs_sha256", "trace_manifest_sha256",
    "trace_steps_sha256", "env_manifest_file_sha256",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "request_contract", "cache_identity",
    "probe_rule_sha256", "routing_source_sha256", "driver",
    "environment_manifest_sha256",
})


def validate_environment_manifest_binding(env: Mapping[str, Any]) -> str:
    """218_s F1: the CANONICAL Stage-1 validator — manifest kind,
    required fields, self-hash, AND the source identity bound to the
    current tree. A self-consistent but fictional mapping refuses.
    Used at BUILD/materialization time; historical loads use
    `validate_env_self_hash` (220_s F2), because the tree legitimately
    moves after a run while the persisted bytes must still verify."""
    from tasks.conductor.stage1_manifest import (
        ManifestError, validate_env_manifest,
    )
    try:
        return validate_env_manifest(env)
    except ManifestError as error:
        raise InfrastructureError(str(error)) from error


def validate_env_self_hash(env: Mapping[str, Any]) -> str:
    """220_s F2: the historical check — manifest kind, required
    fields, and the body→hash binding, WITHOUT current-source
    equality. A replaced or truncated env_manifest.json refuses."""
    import hashlib
    from tasks.conductor.profiles import canonical_json
    if env.get("manifest") != "stage1-environment-v2":
        raise InfrastructureError(
            f"not a stage1-environment-v2 manifest: "
            f"{env.get('manifest')!r}")
    for field in ("git_commit", "uv_lock_sha256",
                  "stage1_source_sha256", "stage1_source_files",
                  "gpu", "torch"):
        if field not in env:
            raise InfrastructureError(
                f"environment manifest missing {field!r}")
    declared = env.get("execution_manifest_sha256")
    body = {k: v for k, v in env.items()
            if k != "execution_manifest_sha256"}
    if not declared or hashlib.sha256(
            canonical_json(body).encode("utf-8")).hexdigest() != declared:
        raise InfrastructureError(
            "environment manifest hash mismatch — the execution "
            "identity is not the hash of this manifest")
    return declared


def build_support_launch_manifest(*, declaration: Mapping[str, Any],
                                  frozen_probe_rule: Mapping[str, Any],
                                  search_cap: int,
                                  budget_gpu_hours: float,
                                  driver: Any,
                                  environment_manifest:
                                  Mapping[str, Any]) -> dict[str, Any]:
    """The ONE pre-launch record (218_s F1). Everything is validated
    or recomputed here; the freeze commits this manifest's hash, and
    materialization consumes it."""
    import math
    from .charter import routing_execution_digest
    from .cohorts import (
        FIRST_PROBE_RULE_KIND, apply_probe_rule, validate_probe_rule,
    )
    validate_dev_cohort(declaration["namespace"], declaration["cohort"],
                        declaration["renderers"],
                        declaration["visibility"])
    # 220_s F3: the support launch carries THE SIGNED FIRST PROBE, and
    # its selection must apply to this declaration BEFORE execution —
    # a rule the declaration cannot serve refuses here, not later.
    rule = validate_probe_rule(frozen_probe_rule)
    if rule["kind"] != FIRST_PROBE_RULE_KIND:
        raise InfrastructureError(
            f"the support launch binds the signed first probe, not a "
            f"{rule['kind']!r} rule (220_s F3)")
    apply_probe_rule(frozen_probe_rule, declaration)
    # 220_s F4: outcome-blind prefixes — each cell's declared indices
    # must BE the frozen prefix 0..k-1, never a curated subset.
    for cell, indices in declaration["cohort"].items():
        if sorted(indices) != list(range(len(indices))):
            raise InfrastructureError(
                f"{cell}: declared indices {sorted(indices)[:6]} are "
                "not the outcome-blind prefix 0..k-1 (211_f §4)")
    if not isinstance(search_cap, int) or isinstance(search_cap, bool) \
            or search_cap < 1:
        raise InfrastructureError(f"bad search_cap {search_cap!r}")
    # 220_s F4: the signed §4 cap counts RENDERED OBSERVATIONS.
    total = len(declaration["observations"])
    if total > search_cap:
        raise InfrastructureError(
            f"declaration screens {total} rendered observations, "
            f"above the frozen search cap {search_cap}")
    if not isinstance(budget_gpu_hours, (int, float)) \
            or isinstance(budget_gpu_hours, bool) \
            or not math.isfinite(budget_gpu_hours) \
            or budget_gpu_hours <= 0:
        raise InfrastructureError(
            f"budget_gpu_hours must be finite and > 0, got "
            f"{budget_gpu_hours!r}")
    digest = routing_execution_digest(driver)
    manifest = {
        "kind": SUPPORT_LAUNCH_KIND,
        "declaration_sha256": content_sha256(dict(declaration)),
        "namespace": declaration["namespace"],
        "worker_visible_fingerprint":
            declaration["worker_visible_fingerprint"],
        "runtime_profile_fingerprint":
            declaration["runtime_profile_fingerprint"],
        "worker_pool_fingerprint":
            declaration["worker_pool_fingerprint"],
        "request_contract": declaration["request_contract"],
        "cache_identity": declaration["cache_identity"],
        "probe_rule_sha256": frozen_probe_rule["rule_sha256"],
        "search_cap": search_cap,
        "budget_gpu_hours": budget_gpu_hours,
        "routing_source_sha256": digest["routing_source_sha256"],
        "driver": digest["driver"],
        "environment_manifest_sha256":
            validate_environment_manifest_binding(environment_manifest),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


# 224_s F2: the SCIENTIFIC design of a support launch — everything an
# aborted-retry may NOT change without becoming an outcome-informed
# successor. Source/environment/budget/driver are absent on purpose:
# an infrastructure repair may change them.
_SCIENTIFIC_DESIGN_FIELDS = (
    "declaration_sha256", "namespace", "worker_visible_fingerprint",
    "runtime_profile_fingerprint", "worker_pool_fingerprint",
    "request_contract", "cache_identity", "probe_rule_sha256",
    "search_cap",
)


def scientific_design_sha256(manifest: Mapping[str, Any]) -> str:
    """The frozen scientific-design identity of a support-launch
    manifest (224_s F2): declaration/cohort, probe rule,
    worker/request/cache identities and the search cap."""
    missing = [f for f in _SCIENTIFIC_DESIGN_FIELDS
               if f not in manifest]
    if missing:
        raise InfrastructureError(
            f"manifest lacks scientific-design fields {missing}")
    return content_sha256(
        {field: manifest[field] for field in _SCIENTIFIC_DESIGN_FIELDS})


def validate_support_launch_manifest(manifest: Mapping[str, Any],
                                     declaration: Mapping[str, Any],
                                     *, recompute: bool = True
                                     ) -> dict[str, Any]:
    """Closed schema + rehash + the declaration must BE the bound
    declaration; with `recompute` the source digest must also
    recompute from the current tree for the named driver."""
    if not isinstance(manifest, Mapping) \
            or set(manifest) != _SUPPORT_LAUNCH_KEYS | \
            {"manifest_sha256"}:
        raise InfrastructureError(
            "support-launch manifest keys do not match the closed "
            "schema")
    if manifest["kind"] != SUPPORT_LAUNCH_KIND:
        raise InfrastructureError(
            f"unknown launch-manifest kind {manifest['kind']!r}")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if content_sha256(body) != manifest["manifest_sha256"]:
        raise InfrastructureError(
            "support-launch manifest does not rehash")
    if manifest["declaration_sha256"] != \
            content_sha256(dict(declaration)):
        raise InfrastructureError(
            "support-launch manifest is bound to a different "
            "declaration (218_s F1)")
    for key in ("namespace", "worker_visible_fingerprint",
                "runtime_profile_fingerprint",
                "worker_pool_fingerprint", "request_contract",
                "cache_identity"):
        if manifest[key] != declaration[key]:
            raise InfrastructureError(
                f"support-launch manifest {key} does not match the "
                "declaration")
    if recompute:
        from .charter import routing_execution_digest
        digest = routing_execution_digest(manifest["driver"])
        if digest["routing_source_sha256"] != \
                manifest["routing_source_sha256"]:
            raise InfrastructureError(
                "support-launch source digest does not recompute from "
                "the tree — the source moved after the freeze")
    return dict(manifest)


def _load_persisted_launch(out_dir: Path, *, recompute: bool
                           ) -> dict[str, Any]:
    """Read + revalidate the persisted launch manifest and environment
    bytes from a surface directory. 220_s F2: the environment bytes
    ALWAYS verify — full canonical validation in-session
    (recompute=True), body→hash self-binding on historical loads —
    so a replaced env_manifest.json refuses either way."""
    launch_path = out_dir / "support_launch.json"
    env_path = out_dir / "env_manifest.json"
    if not launch_path.exists() or not env_path.exists():
        raise InfrastructureError(
            f"{out_dir} lacks the persisted launch/environment "
            "manifests — not materialized under a support launch "
            "(218_s F1)")
    declaration = json.loads(
        (out_dir / "declaration.json").read_text(encoding="utf-8"))
    launch = validate_support_launch_manifest(
        json.loads(launch_path.read_text(encoding="utf-8")),
        declaration, recompute=recompute)
    env = json.loads(env_path.read_text(encoding="utf-8"))
    verified = (validate_environment_manifest_binding(env) if recompute
                else validate_env_self_hash(env))
    if verified != launch["environment_manifest_sha256"]:
        raise InfrastructureError(
            "persisted environment manifest does not match the "
            "launch manifest binding (220_s F2)")
    return launch


def build_surface_lock(out_dir: str | Path) -> dict[str, Any]:
    """The POST-RUN lock: extends the persisted, revalidated
    support-launch manifest with the output hashes. No identity is
    caller-supplied — everything is read from the surface directory
    or recomputed. Written as `surface_lock.json`; its self-hash is
    what the tranche freeze commits, and every consumer requires it."""
    out_dir = Path(out_dir)
    declaration = json.loads(
        (out_dir / "declaration.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    launch = _load_persisted_launch(out_dir, recompute=True)
    lock_path = out_dir / "surface_lock.json"
    if lock_path.exists():
        raise InfrastructureError(
            f"{lock_path} exists; a surface is locked exactly once")
    lock = {
        "lock": SURFACE_LOCK_KIND,
        "support": manifest["support"],
        "support_launch_sha256": launch["manifest_sha256"],
        "declaration_sha256": _sha_file(out_dir / "declaration.json"),
        "manifest_sha256": _sha_file(out_dir / "manifest.json"),
        "payoffs_sha256": manifest["payoffs_sha256"],
        "trace_manifest_sha256": manifest["trace_manifest_sha256"],
        "trace_steps_sha256": manifest["trace_steps_sha256"],
        # 220_s F2: the lock binds the archived environment BYTES
        "env_manifest_file_sha256":
            _sha_file(out_dir / "env_manifest.json"),
        "worker_visible_fingerprint":
            declaration["worker_visible_fingerprint"],
        "runtime_profile_fingerprint":
            declaration["runtime_profile_fingerprint"],
        "worker_pool_fingerprint":
            declaration["worker_pool_fingerprint"],
        "request_contract": declaration["request_contract"],
        "cache_identity": declaration["cache_identity"],
        "probe_rule_sha256": launch["probe_rule_sha256"],
        "routing_source_sha256": launch["routing_source_sha256"],
        "driver": launch["driver"],
        "environment_manifest_sha256":
            launch["environment_manifest_sha256"],
    }
    if manifest["declaration_sha256"] != lock["declaration_sha256"]:
        raise InfrastructureError(
            "manifest and lock disagree on the declaration bytes")
    lock["lock_sha256"] = content_sha256(lock)
    lock_path.write_text(json.dumps(lock, indent=1, sort_keys=True)
                         + "\n", encoding="utf-8")
    return lock


def validate_surface_lock(out_dir: str | Path,
                          expected_lock_sha256: str) -> dict[str, Any]:
    """The consuming boundary: the persisted lock must carry the
    EXTERNALLY frozen hash, rehash to it, use the exact closed schema,
    and every file binding must recompute from the bytes on disk."""
    out_dir = Path(out_dir)
    lock_path = out_dir / "surface_lock.json"
    if not lock_path.exists():
        raise InfrastructureError(f"{out_dir} holds no surface lock")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if set(lock) != _LOCK_KEYS | {"lock_sha256"}:
        raise InfrastructureError(
            f"surface lock keys {sorted(lock)} != the exact closed "
            "schema")
    if lock["lock"] != SURFACE_LOCK_KIND:
        raise InfrastructureError(f"unknown lock kind {lock['lock']!r}")
    body = {k: v for k, v in lock.items() if k != "lock_sha256"}
    if content_sha256(body) != lock["lock_sha256"]:
        raise InfrastructureError("surface lock does not rehash")
    if lock["lock_sha256"] != expected_lock_sha256:
        raise InfrastructureError(
            "surface lock is not the externally frozen lock — refusing "
            "to consume a surface under an unrelated lock (214_s P1)")
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    launch = _load_persisted_launch(out_dir, recompute=False)
    checks = {
        "support_launch_sha256": launch["manifest_sha256"],
        "declaration_sha256": _sha_file(out_dir / "declaration.json"),
        "manifest_sha256": _sha_file(out_dir / "manifest.json"),
        "payoffs_sha256": _sha_file(out_dir / "payoffs.jsonl"),
        "trace_manifest_sha256":
            _sha_file(out_dir / "traces" / "traces" / "manifest.json"),
        "trace_steps_sha256":
            _sha_file(out_dir / "traces" / "traces" / "steps.jsonl"),
        "env_manifest_file_sha256":
            _sha_file(out_dir / "env_manifest.json"),
        "support": manifest["support"],
        "probe_rule_sha256": launch["probe_rule_sha256"],
        "routing_source_sha256": launch["routing_source_sha256"],
        "driver": launch["driver"],
        "environment_manifest_sha256":
            launch["environment_manifest_sha256"],
    }
    for key, actual in checks.items():
        if lock[key] != actual:
            raise InfrastructureError(
                f"surface lock {key} does not match the bytes on disk")
    declaration = json.loads(
        (out_dir / "declaration.json").read_text(encoding="utf-8"))
    for key in ("worker_visible_fingerprint",
                "runtime_profile_fingerprint",
                "worker_pool_fingerprint", "request_contract",
                "cache_identity"):
        if lock[key] != declaration[key]:
            raise InfrastructureError(
                f"surface lock {key} does not match the declaration")
    return lock


# --- fail-closed loader ----------------------------------------------------------

def load_dev_surface(out_dir: str | Path, *,
                     expected_lock_sha256: str) -> dict[str, Any]:
    """Mirror of the frozen Stage-0 loader for a persisted development
    declaration, gated by the EXTERNALLY frozen surface lock (214_s
    P1): the lock validates first, then complete coverage over the
    declared 4^S space, every payoff independently re-scored from its
    stored terminal value against the regenerated gold, artifacts
    bound by content hash, trace complete with the same execution
    identity. Returns {"surface", "declaration", "observations",
    "manifest", "lock"}."""
    out_dir = Path(out_dir)
    lock = validate_surface_lock(out_dir, expected_lock_sha256)
    declaration_path = out_dir / "declaration.json"
    if not declaration_path.exists():
        raise InfrastructureError(
            f"{out_dir} holds no declaration.json — not a development "
            "surface directory")
    declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    observations = dev_cohort_observations(
        declaration["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    _verify_dev_declaration(declaration, observations)
    golds = {obs["observation_id"]: obs["instance"]["gold_answer"]
             for obs in observations}

    manifest = json.loads((out_dir / "manifest.json").read_text(
        encoding="utf-8"))
    if set(manifest) != _DEV_MANIFEST_KEYS:
        raise InfrastructureError(
            f"surface manifest keys {sorted(manifest)} != the exact "
            f"schema {sorted(_DEV_MANIFEST_KEYS)}")
    if manifest["surface_schema_version"] != DEV_SURFACE_SCHEMA_VERSION:
        raise InfrastructureError(
            f"surface schema {manifest['surface_schema_version']!r} is "
            f"not {DEV_SURFACE_SCHEMA_VERSION}")
    if manifest["declaration_sha256"] != _sha_file(declaration_path):
        raise InfrastructureError(
            "surface was materialized against a different declaration; "
            "regenerate rather than reinterpret")
    if manifest["support"] != declaration["support"]:
        raise InfrastructureError(
            "manifest support tag does not match the declaration")
    for key in ("worker_visible_fingerprint", "worker_pool_fingerprint"):
        if manifest[key] != declaration[key]:
            raise InfrastructureError(
                f"surface manifest {key} does not match the declaration")
    if manifest["payoffs_sha256"] != _sha_file(out_dir / "payoffs.jsonl"):
        raise InfrastructureError(
            "payoffs.jsonl does not match the manifest content hash")
    trace_dir = out_dir / "traces" / "traces"
    for name, claimed in (("manifest.json",
                           manifest["trace_manifest_sha256"]),
                          ("steps.jsonl", manifest["trace_steps_sha256"])):
        if _sha_file(trace_dir / name) != claimed:
            raise InfrastructureError(
                f"trace {name} does not match the manifest content hash")
    trace_manifest = json.loads(
        (trace_dir / "manifest.json").read_text(encoding="utf-8"))
    if not trace_manifest.get("closed") \
            or trace_manifest.get("status") != "complete":
        raise InfrastructureError(
            "surface trace is not a complete closed run")
    for surface_key, trace_key in (
            ("worker_visible_fingerprint", "worker_visible_fingerprint"),
            ("worker_pool_fingerprint", "worker_pool_fingerprint"),
            ("runtime_profile_fingerprint",
             "runtime_profile_fingerprint")):
        if manifest[surface_key] != trace_manifest[trace_key]:
            raise InfrastructureError(
                f"trace {trace_key} does not match the surface manifest")
    if trace_manifest["steps_written"] != \
            declaration["planned_step_executions"]:
        raise InfrastructureError(
            f"trace holds {trace_manifest['steps_written']} step rows; "
            f"the declared plan is "
            f"{declaration['planned_step_executions']}")
    if not (0 < manifest["unique_singleton_generations"]
            <= manifest["uncached_step_records"]
            <= manifest["executed_step_records"]
            <= declaration["planned_step_executions"]):
        raise InfrastructureError(
            "surface accounting invariants do not hold")
    if manifest["uncached_step_records"] + manifest["cache_hits"] != \
            manifest["executed_step_records"]:
        raise InfrastructureError(
            "cache accounting does not reconcile with executed records")

    expected: set[tuple[str, tuple[int, ...]]] = set()
    for obs in declaration["observations"]:
        for assignment in oracle.enumerate_assignments(obs["num_nodes"]):
            expected.add((obs["observation_id"], assignment))
    if manifest["payoff_rows"] != len(expected):
        raise InfrastructureError(
            f"manifest declares {manifest['payoff_rows']} payoff rows; "
            f"the declared support requires {len(expected)}")
    surface: dict[tuple[str, tuple[int, ...]], float] = {}
    with (out_dir / "payoffs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not isinstance(row, dict) or set(row) != _ROW_KEYS:
                raise InfrastructureError(
                    f"payoff row keys must be exactly {sorted(_ROW_KEYS)}")
            if not isinstance(row["observation_id"], str) \
                    or not isinstance(row["assignment"], list) \
                    or not all(_exact_int(w) for w in row["assignment"]):
                raise InfrastructureError(
                    "payoff row identity fields are mistyped (bools and "
                    "floats alias integer ids)")
            key = (row["observation_id"], tuple(row["assignment"]))
            if key not in expected:
                raise InfrastructureError(
                    f"payoff row {key!r} is not in the declared support")
            if key in surface:
                raise InfrastructureError(f"duplicate payoff row {key!r}")
            terminal = row["terminal_value"]
            if terminal is not None and not _exact_int(terminal):
                raise InfrastructureError(
                    f"terminal_value {terminal!r} is not an exact int")
            rescored = executor.score_terminal(
                terminal, golds[row["observation_id"]])
            if row["payoff"] != rescored:
                raise InfrastructureError(
                    f"row {key!r}: persisted payoff {row['payoff']!r} != "
                    f"re-scored {rescored} from its terminal value")
            surface[key] = rescored
    missing = expected - set(surface)
    if missing:
        raise InfrastructureError(
            f"surface is incomplete: {len(missing)} declared rows "
            f"missing (e.g. {sorted(missing)[:3]})")
    meta = [{key: obs[key] for key in
             ("observation_id", "cell_id", "renderer_id",
              "latent_program_id", "num_nodes")}
            for obs in observations]
    return {"surface": surface, "declaration": declaration,
            "observations": meta, "manifest": manifest, "lock": lock}


# --- disclosure: direction yields (211_f §4 step 4) ---------------------------

def direction_yields(surface: Mapping[tuple[str, tuple[int, ...]], float],
                     observations: list[Mapping[str, Any]]
                     ) -> dict[str, Any]:
    """Every materialized observation's payoff direction, disclosed —
    per cell and in total. Code-free cells are 'no_pair'. Uses the
    frozen family-correct variant-pair table."""
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in observations}
    surface_rows = [{"observation_id": oid, "assignment": list(a),
                     "payoff": p}
                    for (oid, a), p in surface.items()]
    table = eligible_pair_table(surface_rows, cell_of)
    per_observation: dict[str, str] = {}
    for oid in sorted(cell_of):
        if oid not in table:
            per_observation[oid] = "no_pair"
            continue
        entry = table[oid]
        if not entry["distinct_payoff"]:
            per_observation[oid] = "tied"
        else:
            per_observation[oid] = f"w{entry['direction']}_favoured"
    yields: dict[str, dict[str, int]] = {}
    for oid, direction in per_observation.items():
        cell = cell_of[oid]
        bucket = yields.setdefault(cell, {
            "w2_favoured": 0, "w3_favoured": 0, "tied": 0, "no_pair": 0})
        bucket[direction] += 1
    return {"per_observation": per_observation, "per_cell": yields,
            "pair_table": {oid: {k: v for k, v in entry.items()}
                           for oid, entry in table.items()}}


# --- c_fixed_dev (210_s issue 1) ----------------------------------------------

def validate_c_fixed_record(record: Mapping[str, Any]) -> int:
    """Consumers (telemetry, launch freezes) accept only a rehashing
    comparator record and extract the worker from it — never a bare
    int (214_s P1 telemetry finding)."""
    if not isinstance(record, Mapping) \
            or record.get("comparator") != "c_fixed_dev-v1":
        raise InfrastructureError("not a c_fixed_dev-v1 record")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError("c_fixed_dev record does not rehash")
    worker = record["c_fixed_dev"]
    if worker not in (2, 3):
        raise InfrastructureError(f"c_fixed_dev {worker!r} not in {{2,3}}")
    if record.get("development_only") is not True:
        raise InfrastructureError(
            "c_fixed_dev record must be marked development_only")
    return worker


def verify_c_fixed_for(loaded: Mapping[str, Any],
                       record: Mapping[str, Any]) -> int:
    """216_s F3: the strongest comparator check — the record must
    rehash, bind THIS loaded surface's lock, and REDERIVE exactly
    (scores, tie, selection) from the lock-validated surface. A
    fabricated or foreign comparator cannot pass. Returns the
    worker."""
    worker = validate_c_fixed_record(record)
    lock = loaded.get("lock")
    if not isinstance(lock, Mapping) or "lock_sha256" not in lock:
        raise InfrastructureError(
            "verify_c_fixed_for needs the lock-validated loader result")
    if record.get("surface_lock_sha256") != lock["lock_sha256"]:
        raise InfrastructureError(
            "c_fixed_dev record is bound to a different surface lock "
            "(216_s F3)")
    rederived = select_c_fixed_dev(loaded)
    if rederived != dict(record):
        raise InfrastructureError(
            "c_fixed_dev record does not rederive from the locked "
            "surface (216_s F3)")
    return worker


def select_c_fixed_dev(loaded: Mapping[str, Any]) -> dict[str, Any]:
    """The development best-fixed-Code comparator: for each candidate
    w ∈ {2, 3}, the equal-weight family-correct terminal payoff —
    renderer-within-latent, latent-within-cell, equal weights over the
    Code-bearing cells — of the assignment that is family-correct at
    every non-Code node with the (unique) Code node fixed to w.
    Tie → worker 2. Takes the `load_dev_surface` result, so the
    comparator can only be selected on a LOCK-VALIDATED surface
    (214_s P1); persisted with both candidate scores, the rule, and
    the lock identity; development-only forever."""
    surface = loaded["surface"]
    observations = loaded["observations"]
    lock = loaded["lock"]
    if not isinstance(lock, Mapping) or "lock_sha256" not in lock:
        raise InfrastructureError(
            "select_c_fixed_dev needs the lock-validated loader result")
    code_cells: dict[str, dict[str, dict[str, dict[int, float]]]] = {}
    for obs in observations:
        cell = obs["cell_id"]
        families = NODE_FAMILIES[cell]
        code_nodes = [n for n, f in sorted(families.items())
                      if f == "code"]
        if not code_nodes:
            continue
        if len(code_nodes) != 1:
            raise InfrastructureError(
                f"{cell}: multiple Code nodes — the collapse is not "
                "unique; the contract must be revisited")
        payoffs: dict[int, float] = {}
        for w in (2, 3):
            assignment = []
            for node in sorted(families):
                family = families[node]
                if family == "code":
                    assignment.append(w)
                else:
                    (member,) = [wid for wid, fam in
                                 WORKER_FAMILIES.items() if fam == family]
                    assignment.append(member)
            key = (obs["observation_id"], tuple(assignment))
            if key not in surface:
                raise InfrastructureError(
                    f"{key!r}: family-correct variant row missing from "
                    "the surface")
            payoffs[w] = surface[key]
        code_cells.setdefault(cell, {}).setdefault(
            obs["latent_program_id"], {})[obs["observation_id"]] = payoffs
    if not code_cells:
        raise InfrastructureError(
            "no Code-bearing observations — c_fixed_dev is undefined")
    scores: dict[int, float] = {}
    for w in (2, 3):
        cell_means = []
        for latents in code_cells.values():
            latent_means = []
            for members in latents.values():
                latent_means.append(
                    sum(p[w] for p in members.values()) / len(members))
            cell_means.append(sum(latent_means) / len(latent_means))
        scores[w] = sum(cell_means) / len(cell_means)
    tie = scores[2] == scores[3]
    selected = 2 if scores[2] >= scores[3] else 3
    record = {
        "comparator": "c_fixed_dev-v1",
        "rule": ("argmax over w in {2,3} of equal-weight family-correct "
                 "terminal payoff, renderer-within-latent, "
                 "latent-within-cell, equal Code-bearing cell weights; "
                 "tie -> worker 2 (211_f section 4)"),
        "candidate_scores": {"2": scores[2], "3": scores[3]},
        "tie": tie,
        "c_fixed_dev": selected,
        "code_bearing_cells": sorted(code_cells),
        "surface_lock_sha256": lock["lock_sha256"],
        "payoffs_sha256": lock["payoffs_sha256"],
        "development_only": True,
    }
    record["record_sha256"] = content_sha256(record)
    return record
