"""Charter constants, natural mixture, and development provenance.

The frozen literals of the signed charter (211_f, 212_f) live here so
code and document cannot drift silently: budgets, ceilings, the three
development namespaces with their per-cell caps, and the cycle-wide
natural-mixture definition. Provenance: the development execution
digest covers tasks/conductor/*.py AND tasks/routing/*.py, and
`routing_execution_digest` refuses to describe a run whose driver file
is outside the digested set (208_s: the digest must include the actual
training driver, not only tasks/conductor).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from tasks.conductor.types import InfrastructureError

CHARTER = "211_f-routing-development-charter"

# --- 211_f §1/§10 budget literals (engineering safeguards, not science) ------
CYCLE_ENVELOPE_GPU_HOURS = 60.0     # initial-cycle cumulative envelope
RUN_CEILING_HOURS = 10.0            # per training launch, cumulative
                                    # across engineering resumes
PROBE_CEILING_HOURS = 3.0           # zero-update grouped probe
PROMPT_VARIANT_CAP = 10             # initial-cycle resource control

# --- 211_f §3: the three development namespaces (caps are PER CELL) ----------
DEV_NAMESPACES = ("routing_dev", "routing_dev_val", "routing_dev_cycle")
DEV_NAMESPACE_CAPS = {
    "routing_dev": {"max_latent_clusters": 2_000, "expansion_batch": 500},
    "routing_dev_val": {"max_latent_clusters": 500,
                        "expansion_batch": 250},
    "routing_dev_cycle": {"max_latent_clusters": 500,
                          "expansion_batch": 250},
}

ROUTING_RUN_ROOT = Path("runs/routing-dev")

# --- 211_f §6: the cycle-wide natural-mixture definition ----------------------
NATURAL_MIXTURE = {
    "definition": "routing-dev-natural-mixture-v1",
    "cells": "equal",
    "latent_clusters": "equal_within_cell",
    "renderers": "equal_within_latent",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


NATURAL_MIXTURE_SHA256 = content_sha256(NATURAL_MIXTURE)


def verify_namespace_registration() -> None:
    """Fail closed if the charter caps and the generator's
    NAMESPACE_CONFIG ever disagree (the same anti-drift pattern as
    stage1's look-schedule cross-check)."""
    from tasks.conductor.program import NAMESPACE_CONFIG
    from tasks.conductor.types import NAMESPACES
    for namespace, caps in DEV_NAMESPACE_CAPS.items():
        if namespace not in NAMESPACES:
            raise InfrastructureError(
                f"{namespace} is not a registered namespace")
        config = NAMESPACE_CONFIG.get(namespace)
        if config is None or \
                config["max_latent_clusters"] != caps["max_latent_clusters"] \
                or config["expansion_batch"] != caps["expansion_batch"] \
                or config["stopping_rule"] != "fixed":
            raise InfrastructureError(
                f"NAMESPACE_CONFIG[{namespace!r}] does not match the "
                f"211_f charter caps {caps} + fixed stopping rule")


def natural_mixture_weights(observations: list[Mapping[str, Any]]
                            ) -> dict[str, float]:
    """Per-observation weights under the frozen natural mixture:
    renderer-within-latent, latent-within-cell, equal cell weights.
    Observations carry observation_id, cell_id, latent_program_id,
    renderer_id. Weights sum to 1 over the population; an empty
    population refuses."""
    if not observations:
        raise InfrastructureError("natural mixture over an empty "
                                  "population")
    cells: dict[str, dict[str, list[str]]] = {}
    for obs in observations:
        cells.setdefault(obs["cell_id"], {}).setdefault(
            obs["latent_program_id"], []).append(obs["observation_id"])
    weights: dict[str, float] = {}
    cell_weight = 1.0 / len(cells)
    for latents in cells.values():
        latent_weight = cell_weight / len(latents)
        for members in latents.values():
            renderer_weight = latent_weight / len(members)
            for observation_id in members:
                if observation_id in weights:
                    raise InfrastructureError(
                        f"duplicate observation {observation_id} in the "
                        "mixture population")
                weights[observation_id] = renderer_weight
    return weights


# --- development execution digest (208_s) ------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]


def routing_source_files() -> tuple[str, ...]:
    """Every tracked .py under tasks/conductor/ AND tasks/routing/,
    sorted. Tracked-only for the same reason as stage1_source_files:
    an untracked scratch file cannot silently enter the execution
    identity."""
    out = subprocess.run(
        ["git", "ls-files", "tasks/conductor/*.py", "tasks/routing/*.py"],
        capture_output=True, text=True, check=True,
        cwd=_REPO_ROOT).stdout
    files = tuple(sorted(line for line in out.splitlines() if line))
    if not files:
        raise InfrastructureError("git ls-files returned no sources — "
                                  "wrong working directory?")
    return files


def routing_execution_digest(driver: ModuleType | str) -> dict[str, Any]:
    """The development execution identity: name\\0bytes\\0 chaining over
    the complete routing source list, refusing if the ACTUAL driver
    (module or repo-relative path) is not inside the digested set —
    a driver outside the digest would make the identity a lie (208_s).
    """
    if isinstance(driver, ModuleType):
        driver_file = getattr(driver, "__file__", None)
        if driver_file is None:
            raise InfrastructureError(
                f"driver module {driver.__name__} has no source file")
        driver_path = Path(driver_file).resolve().relative_to(_REPO_ROOT)
    else:
        driver_path = Path(driver)
    driver_name = driver_path.as_posix()
    files = routing_source_files()
    if driver_name not in files:
        raise InfrastructureError(
            f"driver {driver_name} is not in the digested source set — "
            "the execution digest must include the actual training "
            "driver (208_s)")
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update((_REPO_ROOT / name).read_bytes())
        digest.update(b"\x00")
    return {"routing_source_sha256": digest.hexdigest(),
            "routing_source_files": list(files),
            "driver": driver_name}


# --- run roots and lightweight freezes (211_f §§1, 12) ------------------------

def claim_run_root(name: str, base: str | Path | None = None) -> Path:
    """A unique run/segment root under runs/routing-dev/. Refuses an
    existing directory — a recorded run is never overwritten."""
    if not name or "/" in name or name.startswith("."):
        raise InfrastructureError(f"bad run root name {name!r}")
    root = Path(base) if base is not None else ROUTING_RUN_ROOT
    run_dir = root / name
    if run_dir.exists():
        raise InfrastructureError(
            f"{run_dir} exists; development runs never overwrite a "
            "recorded root")
    run_dir.mkdir(parents=True)
    return run_dir


_LIGHTWEIGHT_FREEZE_KEYS = frozenset({
    "kind", "question", "motivation", "config", "budget_gpu_hours"})


def lightweight_freeze(record: Mapping[str, Any]) -> dict[str, Any]:
    """The 211_f §1 lightweight freeze for engineering smokes, the
    resume validation, and standalone GPU evaluations: exact config +
    motivation + budget, content-hashed BEFORE launch. Returns the
    frozen record with its self-hash; missing fields refuse."""
    missing = _LIGHTWEIGHT_FREEZE_KEYS - set(record)
    if missing:
        raise InfrastructureError(
            f"lightweight freeze missing {sorted(missing)}")
    budget = record["budget_gpu_hours"]
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) \
            or not budget > 0:
        raise InfrastructureError(
            f"lightweight freeze needs a positive budget, got {budget!r}")
    frozen = {key: record[key] for key in sorted(record)}
    frozen["freeze_sha256"] = content_sha256(frozen)
    return frozen
