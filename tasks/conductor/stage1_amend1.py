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

# The formal deterministic-equivalence-set seeds (161_s finding 3):
# these ARE consumed by the amended run order (entry gate) and belong
# in the canonical registry under the retained D/B domain.
DETSET_KEYS = tuple(f"D-detset|{name}" for name in
                    ("inside_zero", "boundary_plus", "boundary_minus",
                     "outside_plus", "outside_minus", "inside_edge"))

# component counts: 48 A + 24 router + 48 C paths + 8x5000 D
# + 6 det-set + 9,216 B completions
FULL_SEED_REGISTRY_ENTRIES = 48 + 24 + 48 + 8 * 5_000 + 6 + 9_216


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
    for key in DETSET_KEYS:
        registry[key] = seed(DB_SEED_DOMAIN, key)
    return registry


def finalize_seed_registry(observation_ids) -> dict[str, int]:
    """The AUTHORITATIVE full registry (161_s finding 3): the partial
    component registry plus the 9,216 concrete B completion seeds,
    whose key material is EXACTLY stage1_replay.completion_seed's —
    raw unpadded completion indices, both pinned prompt digests, the
    18 real support observation ids. Only this finalized registry's
    digest may enter an execution bundle."""
    obs = sorted(observation_ids)
    if len(obs) != 18:
        raise InfrastructureError(
            f"B support must be exactly 18 observations, got {len(obs)}")
    registry = build_seed_registry()
    prompts = (stage1.PROMPT_FEWSHOT_SHA256,
               stage1.PROMPT_SCHEMA_ONLY_SHA256)
    for oid in obs:
        for sha in prompts:
            for i in range(256):
                key = f"B|{oid}|{sha}|{i}"      # RAW index — the real
                registry[key] = seed(DB_SEED_DOMAIN, key)  # material
    if len(registry) != FULL_SEED_REGISTRY_ENTRIES:
        raise InfrastructureError(
            f"finalized seed registry has {len(registry)} entries, "
            f"expected {FULL_SEED_REGISTRY_ENTRIES} — duplicate or "
            "missing keys")
    return registry


def seed_registry_digest(registry: Mapping[str, int]) -> str:
    body = canonical_json({k: registry[k] for k in sorted(registry)})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify_registry_canonical(registry: Mapping[str, int]) -> None:
    """169_s finding 2: bundle validation proves the supplied registry
    equals the one bound at lock, NOT that its values are the frozen
    derivation. Rederive the COMPLETE registry from the frozen
    derivation over the support ids implied by the registry's own B
    keys and require exact equality — every runner calls this before
    consuming registered seeds."""
    rederived = finalize_seed_registry(_registry_support_ids(registry))
    if dict(registry) != rederived:
        raise InfrastructureError(
            "seed registry is not the canonical frozen derivation — "
            "refusing to execute under non-canonical seeds (169_s)")


# --- §4 contract: persistence branch constants and serialization ----------------

PERSISTENCE_BOUNDARY_R = 0.10
PERSISTENCE_BRANCHES = ("zero", "positive")
BISECTION_ITERATIONS = 80
ENDPOINT_ATOL = 1e-12
ENDPOINT_RTOL = 0.0                    # §4.5: rtol=0, atol=1e-12
# §4.5 numerical conventions, promoted to tested constants (161_s):
FLOAT_DTYPE = "float64"
TOLERANCE_FACTOR = 64                  # tol = 64*eps64*max(1,|S|,...)
STUDENT_T_IMPL = "scipy.stats.t.ppf"   # frozen implementation + args
QUANTILE_METHOD_D15 = "linear"         # retained by D1-D5 bootstraps


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
PERSISTENCE_BASE_FIELDS = (
    "N", "m", "K", "J", "Qbar_num", "Qbar_den", "sum_A",
    "p_hat_num", "p_hat_den",           # p_hat = J/K as integers
    "branch",                            # "zero" | "positive"
    "denominator_check",                 # "ok"|"unresolved"|"n/a"
    "decision",                          # "pass"|"fail"|"unresolved"
    "tail_a", "tail_a_zero", "tail_a_ratio",
)
# 161_s finding 4: branch-specific bound fields are EXPLICIT schema,
# not comments. Bounds are persisted as string decimals by the Unit-B
# serializer; decisions are re-derived at load, never trusted.
PERSISTENCE_ZERO_BRANCH_FIELDS = PERSISTENCE_BASE_FIELDS + (
    "zero_U",            # the operational upper bound
    "zero_U_A",          # CP component ("n/a" when structural)
    "zero_L_Q",          # Hoeffding component ("n/a" when structural)
)
PERSISTENCE_POSITIVE_BRANCH_FIELDS = PERSISTENCE_BASE_FIELDS + (
    "pos_G_L", "pos_G_U",       # threshold-score interval at r=0.10
    "pos_L_p", "pos_U_p",       # inverted ratio interval endpoints
)
PERSISTENCE_LOOK_FIELDS = PERSISTENCE_BASE_FIELDS  # shared core

# Amended C/D sufficient-statistic row schemas (161_s finding 4),
# frozen BEFORE Unit B produces them. Integer counts only; identities
# enforced at load exactly like the v1 _ROW_SCHEMAS.
AMEND1_ROW_SCHEMAS: dict[str, dict[str, Any]] = {
    # per coupled path: first terminal decision counts over the outer
    # trials (first_pass + first_fail + cap_unresolved == trials)
    "C_path": {
        "fields": frozenset({"first_pass", "first_fail",
                             "cap_unresolved", "trials"}),
        "trials": C_OUTER_TRIALS,
        "identity": lambda r: (r["first_pass"] + r["first_fail"]
                               + r["cap_unresolved"] == r["trials"]),
    },
    # per registered-look marginal: decision counts + branch counts
    # (pass+fail+unresolved == trials; zero+positive == trials;
    # denominator-unresolved only arises inside the positive branch,
    # always with an unresolved decision, and fails only arise in the
    # positive branch with a RESOLVED denominator — 169_s)
    "C_marginal": {
        "fields": frozenset({"pass_count", "fail_count",
                             "unresolved_count", "zero_branch",
                             "positive_branch",
                             "denominator_unresolved", "trials"}),
        "trials": C_OUTER_TRIALS,
        "identity": lambda r: (
            r["pass_count"] + r["fail_count"] + r["unresolved_count"]
            == r["trials"]
            and r["zero_branch"] + r["positive_branch"] == r["trials"]
            and r["denominator_unresolved"] <= r["positive_branch"]
            and r["denominator_unresolved"] <= r["unresolved_count"]
            and r["fail_count"] + r["denominator_unresolved"]
            <= r["positive_branch"]),
    },
    # per D scenario (unchanged meaning, amended production policy)
    "D": {
        "fields": frozenset({"error_count", "trials"}),
        "trials": sv.COVERAGE_OUTER_TRIALS,
        "identity": lambda r: r["error_count"] <= r["trials"],
    },
    # D6-D8 per-look branch counts (158_s §6)
    "D_branch": {
        "fields": frozenset({"zero_branch", "positive_branch",
                             "denominator_unresolved", "trials"}),
        "trials": sv.COVERAGE_OUTER_TRIALS,
        "identity": lambda r: (
            r["zero_branch"] + r["positive_branch"] == r["trials"]
            and r["denominator_unresolved"] <= r["positive_branch"]),
    },
}


def validate_amend1_rows(kind: str,
                         rows: Mapping[str, Mapping[str, int]]) -> None:
    """Fail-closed row validation against the frozen amended schemas
    (Unit B/C runners and loaders both call this)."""
    schema = AMEND1_ROW_SCHEMAS.get(kind)
    if schema is None:
        raise InfrastructureError(f"unknown amend1 row kind {kind!r}")
    for key, row in rows.items():
        if set(row) != schema["fields"]:
            raise InfrastructureError(
                f"{kind} row {key!r}: fields {sorted(row)} != schema")
        for field, value in row.items():
            if type(value) is not int or value < 0:
                raise InfrastructureError(
                    f"{kind} row {key!r}: bad {field!r}={value!r}")
        if row["trials"] != schema["trials"]:
            raise InfrastructureError(
                f"{kind} row {key!r}: trials != frozen "
                f"{schema['trials']}")
        if not schema["identity"](row):
            raise InfrastructureError(
                f"{kind} row {key!r}: impossible counts {dict(row)!r}")

# --- §2: v1 evidence archive verifier (entry gate for the amended lock) ---------

V1_EVIDENCE_DIR = Path(
    "plans/conductor/evidence/stage1_pre_ce1_v1_ae26ba5d")
# 161_s finding 2: the manifest itself is PINNED, the diagnostic
# script joins the frozen table (as corrected at Unit-A repair), and
# the complete identity block + exact file set are validated.
V1_EVIDENCE_MANIFEST_SHA256 = (
    "b01b706084c235f2024c6c3fd32e8054fb93c22bd1a96c5bc9dcfa588f0b2baa")
V1_IDENTITY = {
    "preregistration_153f_sha256":
        "235acb78d9b875999ab90ca50a37e9fbe4c208fa2fa92a285c3229ec01748572",
    "reviewed_executable_commit":
        "75b852ff3bc3bd5671352451bfc60eae161b4370",
    "lock_commit": "da8424bcf27dd59ad4c4e3fc32cb4edef6ba090a",
    "source_digest":
        "8034178f00d952e4f8952dc511a79ac8fc7e36fa58b46e523d47964a9cc4470b",
    "execution_identity":
        "ae26ba5d3ab951ce0a898fcd14b055be144b3a8d642cc3a80e38c433c53d24b1",
    "outcome_commit": "20507e6d9f4573746813a47349e11cb227a42b9b",
}
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
    "agreement_diagnostic_script.py":
        "85f7f26bc2f3a24cbc29529c4634900138b3183e7007c78ea96b81442dcfcf05",
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
    got_manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if got_manifest_sha != V1_EVIDENCE_MANIFEST_SHA256:
        raise InfrastructureError(
            f"v1 evidence manifest sha256 {got_manifest_sha[:8]}... != "
            f"pinned {V1_EVIDENCE_MANIFEST_SHA256[:8]}... — the archive "
            "identity itself is frozen (161_s)")
    manifest = json.loads(manifest_bytes)
    files = manifest.get("files", {})
    if set(files) != set(V1_EVIDENCE_HASHES):
        raise InfrastructureError(
            "v1 evidence manifest file set != the frozen table")
    for field, expected in V1_IDENTITY.items():
        if manifest.get(field) != expected:
            raise InfrastructureError(
                f"v1 evidence manifest identity field {field!r} != "
                "frozen value")
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
    return got_manifest_sha


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

# 158_s §11 / §9.4: the exact expected file sets per run root, frozen.
EXPECTED_RUN_FILES: dict[str, tuple[str, ...]] = {
    AMEND1_VALIDATION_RUN_ROOT: (
        "execution_bundle_manifest.json", "env_manifest.json",
        "deterministic_equivalence.json", "benchmark.json",
        "artifact_A.json", "artifact_C.json", "artifact_D.json",
    ) + tuple(f"partial_D_{d_id}.json" for d_id in AMEND1_D_IDS)
      + ("aggregate.json", "run_record.json"),
    AMEND1_REPLAY_RUN_ROOT: (
        "execution_bundle_manifest.json", "env_manifest.json",
        "replay_manifest.json", "raw_completions.json",
        "artifact_B.json", "run_record.json",
    ),
}


def verify_run_file_set(directory: Path | str, run_root: str) -> None:
    """169_s finding 4: the successful lifecycle must satisfy the
    frozen contract EXACTLY — no missing files, no extras, no
    subdirectories under a run root."""
    expected = EXPECTED_RUN_FILES.get(run_root)
    if expected is None:
        raise InfrastructureError(f"unknown run root {run_root!r}")
    directory = Path(directory)
    entries = list(directory.iterdir())
    subdirs = sorted(p.name for p in entries if not p.is_file())
    if subdirs:
        raise InfrastructureError(
            f"{directory}: unexpected non-file entries {subdirs}")
    got = {p.name for p in entries}
    if got != set(expected):
        raise InfrastructureError(
            f"{directory}: run file set != the frozen contract "
            f"(missing {sorted(set(expected) - got)}, "
            f"extra {sorted(got - set(expected))})")


def request_contract_digest() -> str:
    """Digest of the frozen B replay contract — derived from the
    authoritative literal, never caller-supplied (163_s)."""
    from .stage1_replay import REPLAY_CONTRACT
    return hashlib.sha256(
        canonical_json(dict(REPLAY_CONTRACT)).encode("utf-8")).hexdigest()


def artifact_schema_digest() -> str:
    """Digest of a canonical DESCRIPTION of every frozen amended
    schema: row field sets and trial counts (identities are code,
    reviewed with the source digest), the persistence branch field
    tuples, and the version tags."""
    description = {
        "tags": [AMEND1_VALIDATION_TAG, AMEND1_REPLAY_TAG,
                 AMEND1_ARTIFACT_TAG],
        "rows": {kind: {"fields": sorted(schema["fields"]),
                        "trials": schema["trials"]}
                 for kind, schema in AMEND1_ROW_SCHEMAS.items()},
        "persistence_zero": list(PERSISTENCE_ZERO_BRANCH_FIELDS),
        "persistence_positive": list(PERSISTENCE_POSITIVE_BRANCH_FIELDS),
    }
    return hashlib.sha256(
        canonical_json(description).encode("utf-8")).hexdigest()


def expected_file_set_digest() -> str:
    description = {root: list(files)
                   for root, files in EXPECTED_RUN_FILES.items()}
    return hashlib.sha256(
        canonical_json(description).encode("utf-8")).hexdigest()


def scenario_grid_digest() -> str:
    """Digest of the complete amended scenario grids (A cells, router
    cells, C paths and marginals, D ids and alphas as strings)."""
    description = {
        "A": [f"A|{sc}|{d}|{sg}|{sv.POWER_TRIALS}"
              for sc in sv.POSITION_SCENARIOS
              for d in sv.POWER_DELTAS for sg in sv.POWER_SIGMAS],
        "router": [f"A-router|{m}|{e}|{sg}|{sv.POWER_TRIALS}"
                   for m in sv.ROUTER_MIXTURES
                   for e in sv.ROUTER_EFFECTS for sg in sv.POWER_SIGMAS],
        "C_paths": [c_path_key(*cell) for cell in c_path_cells()],
        "C_marginals": sorted(c_marginal_keys()),
        "D": {d_id: repr(AMEND1_D_ALPHAS[d_id])
              for d_id in AMEND1_D_IDS},
    }
    return hashlib.sha256(
        canonical_json(description).encode("utf-8")).hexdigest()


def b_support_digest(observation_ids) -> str:
    return hashlib.sha256(canonical_json(
        sorted(observation_ids)).encode("utf-8")).hexdigest()


def _registry_support_ids(registry: Mapping[str, int]) -> list[str]:
    """The observation ids IMPLIED by the registry's B keys — used to
    bind b_support_sha256 to the registry itself."""
    ids = set()
    for key in registry:
        if key.startswith("B|"):
            ids.add(key.split("|", 2)[1])
    return sorted(ids)


_BUNDLE_REQUIRED = (
    "amendment_prereg_sha256", "lock_record_sha256", "git_commit",
    "source_digest", "environment_manifest_sha256",
    "v1_evidence_manifest_sha256", "seed_registry_sha256",
    "seed_registry_entries", "scenario_grid_sha256", "b_support_sha256",
    "request_contract_sha256", "artifact_schema_sha256",
    "expected_file_set_sha256",
    "prompt_sha256s", "artifact_tags", "run_roots", "attempt_id",
)
_BUNDLE_HEX64_FIELDS = (
    "amendment_prereg_sha256", "lock_record_sha256", "source_digest",
    "environment_manifest_sha256", "v1_evidence_manifest_sha256",
    "seed_registry_sha256", "scenario_grid_sha256", "b_support_sha256",
    "request_contract_sha256", "artifact_schema_sha256",
    "expected_file_set_sha256",
)
_HEX = frozenset("0123456789abcdef")


def _check_bundle_semantics(body: Mapping[str, Any]) -> None:
    """The SAME semantic checks at build and at load (161_s finding 1):
    a self-rehashed bundle with altered frozen literals must refuse at
    validation, not only at construction."""
    expected_fields = {"manifest", *_BUNDLE_REQUIRED}
    got_fields = set(body) - {"execution_bundle_sha256"}
    if got_fields != expected_fields:
        raise InfrastructureError(
            f"execution bundle field set mismatch: missing "
            f"{sorted(expected_fields - got_fields)}, extra "
            f"{sorted(got_fields - expected_fields)}")
    if body["manifest"] != "stage1-execution-bundle-amend1-v1":
        raise InfrastructureError("not an amend1 execution bundle")
    if body["attempt_id"] != ATTEMPT_ID:
        raise InfrastructureError(
            f"attempt id must be the frozen literal {ATTEMPT_ID!r}")
    if body["artifact_tags"] != [AMEND1_VALIDATION_TAG,
                                 AMEND1_REPLAY_TAG,
                                 AMEND1_ARTIFACT_TAG]:
        raise InfrastructureError("artifact tags are not the frozen "
                                  "amend1 literals")
    if body["run_roots"] != [AMEND1_VALIDATION_RUN_ROOT,
                             AMEND1_REPLAY_RUN_ROOT]:
        raise InfrastructureError("run roots are not the frozen amend1 "
                                  "literals")
    if body["prompt_sha256s"] != [stage1.PROMPT_FEWSHOT_SHA256,
                                  stage1.PROMPT_SCHEMA_ONLY_SHA256]:
        raise InfrastructureError("prompt digests are not the pinned "
                                  "candidates")
    for field in _BUNDLE_HEX64_FIELDS:
        value = body[field]
        if not isinstance(value, str) or len(value) != 64 or \
                not set(value) <= _HEX:
            raise InfrastructureError(
                f"bundle field {field!r} must be 64 lowercase hex")
    if not isinstance(body["git_commit"], str) or \
            len(body["git_commit"]) != 40:
        raise InfrastructureError("git_commit must be a 40-hex commit")
    if body["seed_registry_entries"] != FULL_SEED_REGISTRY_ENTRIES:
        raise InfrastructureError(
            f"seed_registry_entries "
            f"{body['seed_registry_entries']!r} != authoritative "
            f"{FULL_SEED_REGISTRY_ENTRIES} — a bundle may only bind the "
            "FINALIZED full registry (161_s finding 3)")
    # 163_s: provenance fields are DERIVED or PINNED, never trusted as
    # valid-looking hashes
    if body["v1_evidence_manifest_sha256"] != \
            V1_EVIDENCE_MANIFEST_SHA256:
        raise InfrastructureError(
            "v1_evidence_manifest_sha256 != the pinned archive manifest "
            "hash — fabricated evidence provenance refuses (163_s)")
    if body["request_contract_sha256"] != request_contract_digest():
        raise InfrastructureError(
            "request_contract_sha256 != the digest of the frozen "
            "REPLAY_CONTRACT")
    if body["artifact_schema_sha256"] != artifact_schema_digest():
        raise InfrastructureError(
            "artifact_schema_sha256 != the digest of the frozen amended "
            "schemas")
    if body["expected_file_set_sha256"] != expected_file_set_digest():
        raise InfrastructureError(
            "expected_file_set_sha256 != the digest of the frozen "
            "expected run-file sets")
    if body["scenario_grid_sha256"] != scenario_grid_digest():
        raise InfrastructureError(
            "scenario_grid_sha256 != the digest of the frozen amended "
            "scenario grids")


def build_execution_bundle(fields: Mapping[str, Any], *,
                           seed_registry: Mapping[str, int]
                           ) -> dict[str, Any]:
    """Canonical execution-bundle manifest; its self-hash is the
    amended execution identity consumed by every runner, artifact,
    loader and the aggregate.

    163_s: the registry-derived fields (`seed_registry_sha256`,
    `seed_registry_entries`, `b_support_sha256`) are COMPUTED here from
    the supplied FINALIZED registry — a caller cannot pair a partial
    registry's digest with a claimed full count. The remaining
    provenance digests are checked against pinned/derived authoritative
    values by the shared semantic check."""
    if len(seed_registry) != FULL_SEED_REGISTRY_ENTRIES:
        raise InfrastructureError(
            f"bundle construction requires the FINALIZED registry "
            f"({FULL_SEED_REGISTRY_ENTRIES} entries), got "
            f"{len(seed_registry)} (163_s)")
    derived = {
        "seed_registry_sha256": seed_registry_digest(seed_registry),
        "seed_registry_entries": len(seed_registry),
        "b_support_sha256": b_support_digest(
            _registry_support_ids(seed_registry)),
    }
    supplied = dict(fields)
    for key, value in derived.items():
        if key in supplied and supplied[key] != value:
            raise InfrastructureError(
                f"bundle field {key!r} disagrees with the value derived "
                "from the finalized registry (163_s)")
        supplied[key] = value
    missing = [f for f in _BUNDLE_REQUIRED if f not in supplied]
    if missing:
        raise InfrastructureError(
            f"execution bundle missing fields: {missing}")
    body = {"manifest": "stage1-execution-bundle-amend1-v1"}
    body.update({k: supplied[k] for k in _BUNDLE_REQUIRED})
    _check_bundle_semantics(body)
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["execution_bundle_sha256"] = digest
    return out


def validate_execution_bundle(bundle: Mapping[str, Any], *,
                              seed_registry: Mapping[str, int]) -> str:
    """Recompute the self-hash, reapply every semantic check (161_s),
    and verify the registry-derived provenance against the FINALIZED
    registry the consumer holds (163_s: the registry is regenerable
    deterministically, so every consumer can and must supply it).
    Returns the amended execution identity."""
    body = {k: v for k, v in bundle.items()
            if k != "execution_bundle_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != bundle.get("execution_bundle_sha256"):
        raise InfrastructureError("execution bundle hash mismatch")
    _check_bundle_semantics(body)
    if len(seed_registry) != FULL_SEED_REGISTRY_ENTRIES:
        raise InfrastructureError(
            "bundle validation requires the FINALIZED registry (163_s)")
    if body["seed_registry_sha256"] != \
            seed_registry_digest(seed_registry):
        raise InfrastructureError(
            "bundle seed_registry_sha256 != the finalized registry's "
            "digest")
    if body["b_support_sha256"] != b_support_digest(
            _registry_support_ids(seed_registry)):
        raise InfrastructureError(
            "bundle b_support_sha256 != the support implied by the "
            "finalized registry")
    return digest


def current_git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          check=True).stdout.strip()
