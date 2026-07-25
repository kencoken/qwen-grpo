"""Amend-once contract — 158_s (accepted unchanged by 159_f), Unit A.

This module carries the amendment's IDENTITY layer: version tags, the
split seed domains and canonical seed registry, the execution-bundle
manifest, atomic run-root claims, the v1 evidence-archive verifier (an
entry gate for the amended lock), the persistence branch CONTRACT
(constants and serialization fields — the statistic itself is Unit B),
and amended-artifact tagging with old-artifact refusal.

Nothing in this module runs a frozen simulation or reveals a result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from . import stage1
from . import stage1_validation as sv
from .profiles import canonical_json
from .types import InfrastructureError

# --- §9: amended identities ---------------------------------------------------

AMEND1_VALIDATION_TAG = "stage1-validation-amend1-v1"
AMEND1_REPLAY_TAG = "stage1-replay-amend1-v1"
AMEND1_ARTIFACT_TAG = "stage1-tranche-artifact-amend1-v1"
ATTEMPT_ID = "stage1-pre-ce1-amend1-attempt-1"

AMEND1_VALIDATION_RUN_ROOT = "runs/stage1-validation-amend1"
AMEND1_REPLAY_RUN_ROOT = "runs/stage1-replay-amend1"

# --- §9.3: split seed domains ---------------------------------------------------
#
# A and C use the FRESH domain because the remedy was selected after
# inspecting v1 C output; D and B keep the v1 domain because their
# per-trial/per-completion seeds were never exposed (D never ran; B
# never ran). seed(V1_SEED_DOMAIN, key) == the v1 scenario_seed(key)
# by construction, asserted by test.

AC_SEED_DOMAIN = AMEND1_VALIDATION_TAG          # fresh
DB_SEED_DOMAIN = "stage1-validation-v1"         # retained, unexposed


def seed(domain: str, key: str) -> int:
    """The frozen derivation of §9.3: first 8 bytes (big-endian) of
    SHA-256 over utf8(domain ␟ key)."""
    material = "\x1f".join([domain, key])
    return int.from_bytes(
        hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


# --- §5.2 / §6: amended registries ---------------------------------------------

C_PATH_SUFFIX = "coupled-path-v1"
C_OUTER_TRIALS = 10_000


def c_path_cells() -> tuple[tuple[str, float, float, str], ...]:
    """48 coupled maximum-cap paths: 2 schedules x 4 eligibilities x
    3 thetas x 2 distributions (look sizes are NOT in the key)."""
    return tuple((schedule, e, theta, dist)
                 for schedule in ("ordinary", "fork")
                 for e in sv.PERSISTENCE_ELIGIBILITY
                 for theta in sv.PERSISTENCE_THETAS
                 for dist in ("cluster_correlated", "row_dispersed"))


def c_path_key(schedule: str, eligibility: float, theta: float,
               dist: str) -> str:
    return (f"C|{schedule}|{eligibility}|{theta}|{dist}|"
            f"{C_OUTER_TRIALS}|{C_PATH_SUFFIX}")


def c_marginal_keys() -> frozenset[str]:
    """120 registered-look marginal summaries: (3 ordinary + 2 fork
    looks) x 4 eligibilities x 3 thetas x 2 distributions."""
    keys = set()
    for schedule, e, theta, dist in c_path_cells():
        for look in sv.PERSISTENCE_LOOKS[schedule]["looks"]:
            keys.add(f"{c_path_key(schedule, e, theta, dist)}|look{look}")
    return frozenset(keys)


# §6: amended D registry ids. D1-D5 keep their v1 ids (seeds unexposed;
# schedule-based rows pick up the amended fork looks in Unit C).
# D6-D8 are materially redefined under NEW frozen ids (except D6, whose
# id is unchanged but whose statistic is the amended interval).
AMEND1_D_IDS = (
    "D1_seq_null_ordinary_div3",
    "D2_seq_null_fork_div3",
    "D3_equiv_boundary_plus",
    "D4_equiv_boundary_minus",
    "D5_pilot_hetero_unequal",
    "D6_persist_const_theta10",
    "D7_persist_rowdispersed_theta10",
    "D8_persist_hybrid_theta01_fork",
)
AMEND1_D_ALPHAS = {
    # D1-D5 inherit their v1 allocations (unchanged meanings)
    "D1_seq_null_ordinary_div3": 3 * 0.05 / 9,
    "D2_seq_null_fork_div3": 2 * 0.05 / 6,
    "D3_equiv_boundary_plus": 3 * 0.05 / 6,
    "D4_equiv_boundary_minus": 3 * 0.05 / 6,
    "D5_pilot_hetero_unequal": 0.05 / 2,
    # §6 table: reissued persistence undercoverage rows
    "D6_persist_const_theta10": 0.05,
    "D7_persist_rowdispersed_theta10": 0.05,
    "D8_persist_hybrid_theta01_fork": 0.05,
}

B_COMPLETION_KEYS_EXPECTED = 9_216


# --- §9.3: canonical seed registry ----------------------------------------------

def build_seed_registry() -> dict[str, int]:
    """Every expected seed key -> unsigned 64-bit value, canonical.
    A/C under the fresh domain; D (per-trial) and B (per-completion,
    derived at replay time from observation ids — here the RECIPE
    prefix is registered; the 9,216 concrete B keys join at lock once
    the support ids are bound into the bundle) under the v1 domain."""
    registry: dict[str, int] = {}
    for scen, d, s in ((sc, dd, ss)
                       for sc in sv.POSITION_SCENARIOS
                       for dd in sv.POWER_DELTAS
                       for ss in sv.POWER_SIGMAS):
        key = f"A|{scen}|{d}|{s}|{sv.POWER_TRIALS}"
        registry[key] = seed(AC_SEED_DOMAIN, key)
    for mix, e, s in ((m, ee, ss)
                      for m in sv.ROUTER_MIXTURES
                      for ee in sv.ROUTER_EFFECTS
                      for ss in sv.POWER_SIGMAS):
        key = f"A-router|{mix}|{e}|{s}|{sv.POWER_TRIALS}"
        registry[key] = seed(AC_SEED_DOMAIN, key)
    for cell in c_path_cells():
        key = c_path_key(*cell)
        registry[key] = seed(AC_SEED_DOMAIN, key)
    for d_id in AMEND1_D_IDS:
        for t in range(sv.COVERAGE_OUTER_TRIALS):
            key = f"{d_id}|{t}"
            registry[key] = seed(DB_SEED_DOMAIN, key)
    return registry


def seed_registry_digest(registry: Mapping[str, int]) -> str:
    body = canonical_json({k: registry[k] for k in sorted(registry)})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# --- §4 contract: persistence branch constants and serialization ----------------

PERSISTENCE_BOUNDARY_R = 0.10
PERSISTENCE_BRANCHES = ("zero", "positive")
BISECTION_ITERATIONS = 80
ENDPOINT_ATOL = 1e-12


def persistence_tail_allocation(schedule: str
                                ) -> tuple[float, float, float]:
    """(a, a_zero, a_ratio): the one-look tail budget and its frozen
    pre-observation Bonferroni split (§4.3). The variable-eligibility
    zero branch further splits a_zero internally (§4.4)."""
    looks = sv.PERSISTENCE_LOOKS[schedule]["looks"]
    a = 0.05 / len(looks)
    return a, a / 2.0, a / 2.0


# §4.6: the exact per-look serialization fields for qualification and
# simulation persistence records. No descriptive rate may replace
# p_hat or the interval fields.
PERSISTENCE_LOOK_FIELDS = (
    "N", "m", "K", "J", "Qbar_num", "Qbar_den", "sum_A",
    "p_hat_num", "p_hat_den",           # p_hat = J/K as integers
    "branch",                            # "zero" | "positive"
    "denominator_check",                 # "ok"|"unresolved"|"n/a"
    "decision",                          # "pass"|"fail"|"unresolved"
    "tail_a", "tail_a_zero", "tail_a_ratio",
    # zero branch: U (and U_A, L_Q when variable eligibility);
    # positive branch: G_L, G_U, L_p, U_p — persisted as string
    # decimals by the Unit B serializer; decisions re-derived at load
)

# --- §2: v1 evidence archive verifier (entry gate for the amended lock) ---------

V1_EVIDENCE_DIR = Path(
    "plans/conductor/evidence/stage1_pre_ce1_v1_ae26ba5d")
V1_EVIDENCE_HASHES = {
    "env_manifest.json":
        "caa666660ee4ebbbf88189771fc8f2322799964f891a1a68fbc1fac639c7b189",
    "deterministic_equivalence.json":
        "12c48da5e2a57e2f2f9a011cd9acbe3d903ee1aaa306fb52b01f9877a3d940cd",
    "benchmark.json":
        "1fd09bff0b9fc7476b8a72cca2e4700e9af4c8ba30506aa2185b1b4ba5cf07e3",
    "artifact_A.json":
        "3ad61310142e1c07062e77afff9da764a5fd4d14c0a6b6456efa8359251eae24",
    "artifact_C.json":
        "eb4c13912f7f4da1f7f7511fb5021852af39367545964efbf3186b652ea900a7",
    "agreement.json":
        "21f8267c42bf6546b02736b909df37c11660ceda4e2bc2ea67d38a34f806f492",
    "run_record.json":
        "6a0b6fac3561f45bf439415b5f84a6a1ca1caf05485b1430f251bc6055a71cf0",
    "agreement_diagnostic.txt":
        "34ec1caa5b7e0e11ec8d5fe5b7fad1da3a65e85db963144ca894dfd2068eb754",
}


def verify_v1_evidence_archive(root: Path | str = V1_EVIDENCE_DIR
                               ) -> str:
    """Byte-verify the archived v1 evidence and its manifest; returns
    the evidence-manifest SHA-256 the execution bundle binds. Fails
    closed on any missing file, hash mismatch, length mismatch, or a
    manifest that disagrees with the frozen hash table."""
    root = Path(root)
    manifest_path = root / "evidence_manifest.json"
    if not manifest_path.exists():
        raise InfrastructureError("v1 evidence manifest is absent")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    files = manifest.get("files", {})
    for name, expected_sha in V1_EVIDENCE_HASHES.items():
        path = root / name
        if not path.exists():
            raise InfrastructureError(f"v1 evidence file missing: {name}")
        data = path.read_bytes()
        got = hashlib.sha256(data).hexdigest()
        if got != expected_sha:
            raise InfrastructureError(
                f"v1 evidence {name}: sha256 {got[:8]}... != frozen "
                f"{expected_sha[:8]}...")
        entry = files.get(name)
        if not entry or entry.get("sha256") != expected_sha or \
                entry.get("bytes") != len(data):
            raise InfrastructureError(
                f"v1 evidence manifest entry for {name} disagrees with "
                "the archived bytes")
    if manifest.get("execution_identity") != (
            "ae26ba5d3ab951ce0a898fcd14b055be144b3a8d642cc3a80e38c433"
            "c53d24b1"):
        raise InfrastructureError("v1 evidence manifest names the wrong "
                                  "execution identity")
    return hashlib.sha256(manifest_bytes).hexdigest()


# --- §9.2: atomic run-root claim --------------------------------------------------

def claim_run_root(root: Path | str) -> Path:
    """Atomic directory creation; ANY pre-existing path — including an
    empty directory — refuses (§9.2)."""
    root = Path(root)
    if root.exists():
        raise InfrastructureError(
            f"{root} already exists — an amended run root is claimed "
            "by atomic creation and never reused (158_s §9.2)")
    root.parent.mkdir(parents=True, exist_ok=True)
    try:
        root.mkdir(exist_ok=False)
    except FileExistsError:
        raise InfrastructureError(
            f"{root} was created concurrently — refusing")
    return root


# --- §9.1: the one lock-specific execution bundle ---------------------------------

_BUNDLE_REQUIRED = (
    "amendment_prereg_sha256", "lock_record_sha256", "git_commit",
    "source_digest", "environment_manifest_sha256",
    "v1_evidence_manifest_sha256", "seed_registry_sha256",
    "scenario_grid_sha256", "b_support_sha256", "prompt_sha256s",
    "artifact_tags", "run_roots", "attempt_id",
)


def build_execution_bundle(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical execution-bundle manifest; its self-hash is the
    amended execution identity consumed by every runner, artifact,
    loader and the aggregate. All required fields must be present and
    the attempt id / tags / roots must be the frozen literals."""
    missing = [f for f in _BUNDLE_REQUIRED if f not in fields]
    if missing:
        raise InfrastructureError(
            f"execution bundle missing fields: {missing}")
    if fields["attempt_id"] != ATTEMPT_ID:
        raise InfrastructureError(
            f"attempt id must be the frozen literal {ATTEMPT_ID!r}")
    if fields["artifact_tags"] != [AMEND1_VALIDATION_TAG,
                                   AMEND1_REPLAY_TAG,
                                   AMEND1_ARTIFACT_TAG]:
        raise InfrastructureError("artifact tags are not the frozen "
                                  "amend1 literals")
    if fields["run_roots"] != [AMEND1_VALIDATION_RUN_ROOT,
                               AMEND1_REPLAY_RUN_ROOT]:
        raise InfrastructureError("run roots are not the frozen amend1 "
                                  "literals")
    body = {"manifest": "stage1-execution-bundle-amend1-v1"}
    body.update({k: fields[k] for k in _BUNDLE_REQUIRED})
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["execution_bundle_sha256"] = digest
    return out


def validate_execution_bundle(bundle: Mapping[str, Any]) -> str:
    """Recompute the self-hash and check the frozen literals; returns
    the amended execution identity."""
    body = {k: v for k, v in bundle.items()
            if k != "execution_bundle_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != bundle.get("execution_bundle_sha256"):
        raise InfrastructureError("execution bundle hash mismatch")
    if bundle.get("manifest") != "stage1-execution-bundle-amend1-v1":
        raise InfrastructureError("not an amend1 execution bundle")
    if bundle.get("attempt_id") != ATTEMPT_ID:
        raise InfrastructureError("wrong attempt id")
    return digest


def current_git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          check=True).stdout.strip()
