"""Stage-1 CE1-prerequisite constants — 132_s unit 1 (approved in 133_f).

This module records frozen DECISIONS, not machinery: the exact numeric
gates, alpha rules, retry taxonomy, visible slice, Stage-2 population
formulas and artifact identities that units 2-5 consume. Estimators,
manifests and the gate report live in later units. Values here change only
through a reviewed plan amendment; the acceptance tests in
test_conductor_stage1.py fail closed if this module drifts from the
artifacts it names (SYSTEM_DIRECT bytes, DEFAULT_PROFILE digest,
SYNTAX_REJECTION_CODES, look schedules).

Citations are to 132_s_stage_1_2_four_worker_redraft_rev2.md unless noted.
"""

from __future__ import annotations

import hashlib
from typing import Mapping

from .types import (
    CELL_INTERVENTION_EDGES,       # authoritative edge table (136_s)
    RENDERER_IDS,                  # authoritative renderer list
    SYNTAX_REJECTION_CODES,        # §7.3 cascade trigger set
)

# --- §17.1-2: cohort and visible-slice decisions ----------------------------

# D4 lives in program.py (CONSTRUCTION_CONSUMED_PREFIX,
# CONSTRUCTION_FORMAL_COHORT, validate_construction_cohort) next to
# NAMESPACE_CONFIG so generation and range rules cannot drift apart.

# §4.1: the first 18 qualification clusters per cell (indices 0-17) get
# paired private+visible observations under all three renderers; the
# private rows stay in the primary qualification population, the visible
# variants support B3/echo/no-op diagnostics only. 18 is divisible by
# every frozen factor-block size in {1, 2, 3, 6}.
VISIBLE_SLICE_QUALIFICATION_CLUSTERS = range(0, 18)

# --- §7: gate thresholds (fractions; "lcb"/"ucb" = sequential bounds) -------

GATE_THRESHOLDS: dict[str, float] = {
    # exactly zero; abort rather than reward (§7, row 1)
    "untyped_infrastructure_failures_max": 0.0,
    # per (cell, logical worker) with on-contract support, strict UCB
    "truncation_ucb_max": 0.02,
    # per cell overall and per selected logical worker within cell
    "selected_route_syntax_ucb_max": 0.02,
    "atomic_family_accuracy_min": 0.75,
    "atomic_family_margin_lcb_min": 0.20,
    "two_step_deployable_min": 0.65,
    "deployable_vs_one_call_lcb_min": 0.20,
    "corruption_drop_lcb_min": 0.20,            # per edge
    # §8.2: strict |theta| < 0.10 equivalence; +/-0.10 belongs to the null
    "counterfactual_equivalence_band": 0.10,
    "old_answer_persistence_ucb_max": 0.10,     # non-strict (<=)
    "family_stake_point_min": 0.10,             # + paired LCB > 0
    "model_stake_point_min": 0.10,              # + paired LCB > 0 (§17.8)
    "reference_vs_generic_min": 0.10,           # gates Stage 3, not Stage 2
    "fork_leaf_capability_min": 0.80,
    "fork_deployable_min": 0.60,
    "fork_vs_two_call_shortcut_min": 0.15,
    "fork_branch_corruption_lcb_min": 0.20,     # per branch
}

# --- §7.1: gate applicability matrix ----------------------------------------

# Intervention diagnostics apply per DIRECTED EDGE, never pooled across
# edges (134_s finding 1): every (edge, diagnostic) pair is its own
# independently passed gate, named "{diagnostic}_{src}_{dst}". The edge
# table itself is the authoritative one in types.py — the same table
# generation and estimand scoring use — imported, not copied, so admission
# gates cannot drift from it (136_s finding 1).
INTERVENTION_DIAGNOSTICS = ("corruption", "counterfactual_consistency",
                            "old_answer_persistence")


def intervention_gate_names(cell_id: str) -> tuple[str, ...]:
    """The full edge x diagnostic cross-product for one cell."""
    return tuple(f"{diag}_{src}_{dst}"
                 for (src, dst) in CELL_INTERVENTION_EDGES[cell_id]
                 for diag in INTERVENTION_DIAGNOSTICS)


# Mandatory admission gates per cell; failure of any mandatory gate
# excludes the cell; failure of any of the five mandatory Core cells makes
# Core NO-GO; fork failure leaves the five-cell Core branch intact.
GATE_MATRIX: dict[str, dict[str, tuple[str, ...]]] = {
    "lookup_atomic": {
        "mandatory": ("atomic_capability", "family_margin",
                      "selected_route_protocol"),
        "c1_positions": ("n1",),
        "c2_positions": (),
    },
    "math_atomic": {
        "mandatory": ("atomic_capability", "family_margin",
                      "selected_route_protocol"),
        "c1_positions": ("n1",),
        "c2_positions": (),
    },
    "code_atomic": {
        "mandatory": ("atomic_capability", "family_margin",
                      "selected_route_protocol"),
        "c1_positions": ("n1",),
        "c2_positions": ("n1",),        # optional: affects C2 only
    },
    "lookup_math": {
        "mandatory": ("two_step_deployable", "deployable_vs_one_call",
                      "selected_route_protocol")
                     + intervention_gate_names("lookup_math"),
        "c1_positions": ("n1", "n2"),
        "c2_positions": (),
    },
    "math_code": {
        "mandatory": ("two_step_deployable", "deployable_vs_one_call",
                      "selected_route_protocol")
                     + intervention_gate_names("math_code"),
        "c1_positions": ("n1", "n2"),
        "c2_positions": ("n2",),        # optional: affects C2 only
    },
    "fork_join": {
        "mandatory": ("fork_leaf_capability", "fork_deployable",
                      "deployable_vs_two_call_shortcut",
                      "selected_route_protocol")
                     + intervention_gate_names("fork_join"),
        "c1_positions": ("n1", "n2", "n3"),
        # semantic ids are stable under branch_order: n2 is the Code leaf
        "c2_positions": ("n2",),        # optional: affects C2 only
    },
}

CORE_CELLS = ("lookup_atomic", "math_atomic", "code_atomic",
              "lookup_math", "math_code")

# --- §7.1: protocol-gate denominator contract (134_s finding 2) -------------

# The scientific denominator row is:
#   one registered private observation x one intended semantic reference
#   node x one logical worker x one independent reference-node execution.
# Each row counts once irrespective of cache reuse, de-duplication, control
# membership, or how many complete assignments consume it; the latent
# program is the resampling unit. Unit 2 derives expected manifest counts
# mechanically from the functions below.

# Logical worker id -> endpoint family (frozen registry order, 106_s §4).
WORKER_FAMILIES: dict[int, str] = {0: "lookup", 1: "math", 2: "code",
                                   3: "code"}

# Semantic node -> intended endpoint family F(c, j). Acceptance-tested
# against generated reference programs (op -> family), not hand-trusted.
NODE_FAMILIES: dict[str, dict[str, str]] = {
    "lookup_atomic": {"n1": "lookup"},
    "math_atomic": {"n1": "math"},
    "code_atomic": {"n1": "code"},
    "lookup_math": {"n1": "lookup", "n2": "math"},
    "math_code": {"n1": "math", "n2": "code"},
    "fork_join": {"n1": "lookup", "n2": "code", "n3": "math"},
}

# All private renderers at every look — derived from the authoritative
# renderer list, not a duplicate literal (136_s follow-through; the
# WORKER_FAMILIES cross-check against the worker registry is unit 2's).
RENDERERS_PER_LATENT = len(RENDERER_IDS)


def on_contract_nodes(cell_id: str, worker_id: int) -> tuple[str, ...]:
    """Nodes of `cell_id` whose intended family matches the worker's —
    the on-contract stratum for truncation telemetry and gating."""
    family = WORKER_FAMILIES[worker_id]
    nodes = NODE_FAMILIES[cell_id]
    return tuple(n for n in sorted(nodes) if nodes[n] == family)


def truncation_rows_per_latent(cell_id: str, worker_id: int) -> int:
    """Truncation gate rows per latent for one (cell, logical worker):
    exactly 3 x number_of_on_contract_nodes; 0 means no on-contract
    support (that worker is not truncation-gated in that cell)."""
    return RENDERERS_PER_LATENT * len(on_contract_nodes(cell_id, worker_id))


def selected_route_rows_per_latent(cell_id: str) -> int:
    """Selected-route syntax rows per latent for the cell overall:
    exactly 3 x S."""
    return RENDERERS_PER_LATENT * len(NODE_FAMILIES[cell_id])


def selected_route_rows_per_worker(
        cell_id: str, deployable: Mapping[str, int]) -> dict[int, int]:
    """Selected-route syntax rows per latent for every logical worker the
    construction-frozen deployable mapping `d` selects in this cell:
    exactly 3 x selected_nodes_for_worker. Validates that `deployable`
    covers exactly this cell's semantic nodes with known worker ids."""
    nodes = NODE_FAMILIES[cell_id]
    if set(deployable) != set(nodes):
        raise ValueError(
            f"deployable mapping keys {sorted(deployable)} != semantic "
            f"nodes {sorted(nodes)} of {cell_id}")
    counts: dict[int, int] = {}
    for node, worker_id in deployable.items():
        if worker_id not in WORKER_FAMILIES:
            raise ValueError(f"unknown worker id {worker_id!r} at "
                             f"{cell_id}:{node}")
        counts[worker_id] = counts.get(worker_id, 0) + RENDERERS_PER_LATENT
    return counts


# §8.2: the one registered universe of renderer-aggregated Code positions.
# The model-position tail alpha always divides by its size (3), whether the
# final mixture is Core or Core+fork; Core leaves the fork position unused
# but never relaxes the divisor after qualification.
C2_POSITION_UNIVERSE = (("code_atomic", "n1"), ("math_code", "n2"),
                        ("fork_join", "n2"))

# --- §8.1-8.2: looks and alpha spending -------------------------------------

# Cross-checked against program.NAMESPACE_CONFIG by the acceptance tests.
ORDINARY_LOOK_SCHEDULE = (100, 300, 500)
FORK_LOOK_SCHEDULE = (100, 200)

ALPHA_TOTAL = 0.05
ORDINARY_LOOK_TAIL_ALPHA = ALPHA_TOTAL / len(ORDINARY_LOOK_SCHEDULE)  # 0.05/3
FORK_LOOK_TAIL_ALPHA = ALPHA_TOTAL / len(FORK_LOOK_SCHEDULE)          # 0.05/2
# family position-classification gates further divide their one-look alpha
# by the number of positions tested within that cell (GATE_MATRIX
# c1_positions); model-position classification always divides by:
MODEL_POSITION_ALPHA_DIVISOR = len(C2_POSITION_UNIVERSE)  # == 3, fixed

# Both construction-frozen aggregate router hypotheses are registered
# before qualification, each at one-sided 0.025, on the fixed first-100-
# per-cell qualification support with all renderers; evaluated exactly
# once; the non-activated branch stays descriptive.
AGGREGATE_ROUTER_ALPHA = 0.025
AGGREGATE_ROUTER_SUPPORT_CLUSTERS = range(0, 100)

# Two-sided descriptive/equivalence intervals split the tail alpha across
# both tails; admission is intersection-union, so no correction across
# distinct required gates.

# --- §8.3: bootstrap identity ------------------------------------------------

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_QUANTILE_METHOD = "linear"     # numpy.quantile(method=...)
BOOTSTRAP_BITGENERATOR = "PCG64"
_BOOTSTRAP_TAG = "bootstrap-v1"


_HEX64 = frozenset("0123456789abcdef")


def canonical_cell_look_vector(cell_looks: Mapping[str, int]) -> str:
    """The one canonical builder (134_s, corrected per 136_s finding 2):
    comma-joined `cell_id:count` sorted by cell_id.

    Population-INDEPENDENT: §8.3 applies the same bootstrap identity to
    qualification looks, policy-dev headroom, `pilot_gate`, and final
    C1/C2/C3 inference, so counts like 12/24/56/67/72 are all valid here.
    Phase-specific schedule/count validation belongs to unit 2's
    population manifest, not this serializer. Validation here is exactly:
    known cell, plain-int count (`type(count) is int` — a bool or an
    integral float would serialize to a different seed identity than the
    int it compares equal to), count > 0, sorted canonical order."""
    if not cell_looks:
        raise ValueError("empty cell-look vector")
    parts = []
    for cell in sorted(cell_looks):
        if cell not in NODE_FAMILIES:
            raise ValueError(f"unknown cell_id {cell!r}")
        count = cell_looks[cell]
        if type(count) is not int:
            raise ValueError(
                f"count for {cell} must be a plain int, got {count!r}")
        if count <= 0:
            raise ValueError(f"count for {cell} must be > 0, got {count}")
        parts.append(f"{cell}:{count}")
    return ",".join(parts)


def bootstrap_seed(population_manifest_sha256: str, gate_id: str,
                   cell_looks: Mapping[str, int]) -> int:
    """§8.3 seed: first 8 bytes (big-endian) of the SHA-256 over the
    ␟-joined material — the same h64 convention as program.py. The
    cell-look vector is built internally by `canonical_cell_look_vector`
    so callers cannot supply a non-canonical string (134_s)."""
    digest_chars = set(population_manifest_sha256)
    if (len(population_manifest_sha256) != 64
            or not digest_chars <= _HEX64):
        raise ValueError("population_manifest_sha256 must be 64 lowercase "
                         "hex characters")
    if not gate_id:
        raise ValueError("empty gate_id")
    material = "\x1f".join([population_manifest_sha256, gate_id,
                            canonical_cell_look_vector(cell_looks),
                            _BOOTSTRAP_TAG])
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


# --- §7.3: retry taxonomy ----------------------------------------------------

# The descriptive worker-2 -> worker-3 cascade triggers exactly on the
# frozen SYNTAX_REJECTION_CODES set (types.py §1.7); re-exported here so
# unit-2+ execution code takes both lists from one module.
CASCADE_TRIGGER_CODES = frozenset(SYNTAX_REJECTION_CODES)

# INFRA_RETRY_CODES (§7.3): the runtime is a local single-GPU singleton —
# there is no network transport at execution time (checkpoint revisions
# are frozen and locally cached). The only transient failure classes are
# CUDA allocation failure, filesystem I/O on trace/cache writes, and an
# interrupted generation (no finish_reason). Typed InfrastructureError
# contract violations are deterministic and never retried. Exception ->
# code mapping is implemented (and acceptance-tested) in the UNIT-4
# execution layer (deferral recorded per 139_s: unit 2 is registration
# only, and this mapping must exist before the first construction call):
#   torch.cuda.OutOfMemoryError            -> E_INFRA_CUDA_OOM
#   OSError/IOError on artifact read/write -> E_INFRA_IO
#   generation ends without finish_reason  -> E_INFRA_INCOMPLETE_CALL
INFRA_RETRY_CODES: dict[str, dict[str, object]] = {
    # empty_cache() before each retry
    "E_INFRA_CUDA_OOM": {"max_attempts": 3, "backoff_seconds": (10, 60)},
    "E_INFRA_IO": {"max_attempts": 3, "backoff_seconds": (10, 60)},
    "E_INFRA_INCOMPLETE_CALL": {"max_attempts": 2, "backoff_seconds": (10,)},
}
# max_attempts counts the initial call; exhaustion aborts the affected
# gate surface (never becomes a model outcome, never scores as reward).

# --- §10: policy-development gates -------------------------------------------

POLICY_GROUP_SIZE = 8
COLD_START_GROUPS_PER_TOPOLOGY = 72     # per prompt treatment
COLD_START_GROUPS_PER_DIRECTION = 72    # per admitted direction u in {2,3}

# General topology-trainability gates (§10.2): evaluated separately within
# each prompt candidate and admitted topology; these three alone may
# participate in ForkColdStartFallback (§9.2).
COLD_START_GENERAL_GATES: dict[str, float] = {
    "schema_validity_min": 0.80,
    "non_zero_variance_groups_min": 0.25,
    "groups_with_win_and_lower_min": 0.10,
}
# Claim-specific C2 gate at unit (prompt, direction): both Code workers
# appear and >=10% of the 72 groups are direct model-gradient groups.
DIRECT_MODEL_GRADIENT_GROUPS_MIN = 0.10

# §10.3 prompt headroom floors.
C1_TERMINAL_HEADROOM_MIN = 0.05
C1_FAMILY_SELECTION_HEADROOM_MIN = 0.10
C2_MODEL_SELECTION_HEADROOM_MIN = 0.10

# --- §11-12: Stage-2 population and schedule formulas ------------------------

TRAIN_CLUSTERS_PER_CELL = 100           # one balanced renderer per cluster
DEV_SELECT_CLUSTERS = range(0, 24)      # dev namespace, fully crossed
PILOT_GATE_CLUSTERS = range(24, 36)     # disjoint, read exactly once
TEST_TOTAL_TARGET = 1_000               # ceil(1000/(3C)) clusters per cell

GROUPS_PER_UPDATE = 2
SNAPSHOT_EVERY_UPDATES = 25             # plus update 0
PILOT_SCHEMA_VALIDITY_MIN = 0.80

# §6.2/§6.3: every construction tie in a worker-2-vs-3 contrast goes to
# worker 2 (the lower id).
CODE_TIE_WINNER = 2

# §6.3: the frozen shallow routing control.
SHALLOW_ROUTER_PARAMS: dict[str, object] = {
    "max_depth": 3, "criterion": "gini", "min_samples_leaf": 5,
    "random_state": 0,
}
# Exact input columns and order; public numerics missing -> -1;
# renderer_id, handles, names, private strata/values, split id and
# realized qualification outcomes are excluded.
SHALLOW_ROUTER_FEATURES = ("cell_id", "node_id", "subtype",
                           "p", "q", "t", "k", "i")
SHALLOW_ROUTER_MISSING_VALUE = -1

# Encoder configuration (134_s): every categorical is one-hot in a frozen
# level order; no hashing, no learned embedding, no unseen-level bucket —
# an unseen level is a LoadError at encode time, never a silent zero row.
# cell_id levels: lexicographic; node_id levels: n1<n2<n3; subtype levels:
# the frozen per-cell OBSERVABLE_SUBTYPES lists from baselines.py (the
# §1.11 shallow-predictor contract), namespaced as "cell:level" and
# concatenated in cell order. Numeric columns follow in the frozen order
# (p, q, t, k, i) with missing -> -1, exactly as baselines.feature_row.
SHALLOW_ROUTER_CELL_LEVELS = ("code_atomic", "fork_join", "lookup_atomic",
                              "lookup_math", "math_atomic", "math_code")
SHALLOW_ROUTER_NODE_LEVELS = ("n1", "n2", "n3")


def shallow_router_subtype_levels() -> tuple[str, ...]:
    """Frozen namespaced subtype one-hot order, bound to the baselines
    §1.11 contract so the two shallow controls cannot drift apart."""
    from .baselines import OBSERVABLE_SUBTYPES
    return tuple(f"{cell}:{level}"
                 for cell in SHALLOW_ROUTER_CELL_LEVELS
                 for level in OBSERVABLE_SUBTYPES[cell])

# --- §10.1: frozen policy prompt candidates (134_s finding 3) ---------------

# few-shot: the exact Stage-0 SYSTEM_CONDUCTOR bytes (policy freeze
# fe9bba0d...). schema-only: identical instructions, observation skeleton
# and output contract with the demonstration block removed — derived
# mechanically from the frozen bytes, never retyped. Both digests are
# pinned; drift in either fails closed.
PROMPT_FEWSHOT_SHA256 = (
    "fe9bba0deafc60ec45f7883d9fb7bbddda4da847ed7e5d92a53f9b88adb29070")
PROMPT_SCHEMA_ONLY_SHA256 = (
    "9efe8998f1ee17fa9b194ab5e8179c61bbc1036d0c8000c064676ef2c721e9fb")


def prompt_fewshot() -> str:
    from .policy import SYSTEM_CONDUCTOR
    text = SYSTEM_CONDUCTOR
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != \
            PROMPT_FEWSHOT_SHA256:
        raise RuntimeError("few-shot prompt bytes drifted from the pinned "
                           "Stage-0 policy freeze digest")
    return text


def prompt_schema_only() -> str:
    from .policy import SYSTEM_CONDUCTOR, _demo_block
    suffix = "\n\n" + _demo_block()
    if not SYSTEM_CONDUCTOR.endswith(suffix):
        raise RuntimeError("SYSTEM_CONDUCTOR no longer ends with the "
                           "demonstration block; schema-only derivation "
                           "is invalid")
    text = SYSTEM_CONDUCTOR[:-len(suffix)]
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != \
            PROMPT_SCHEMA_ONLY_SHA256:
        raise RuntimeError("schema-only prompt bytes drifted from the "
                           "pinned digest")
    return text


# FORMAT_REPAIR_V1 (134_s finding 3, taking the reviewer's recommended
# no-repair choice): NO repair transformation is frozen. Per 132_s §10.1,
# "if none is frozen, no repair is allowed" — a prompt candidate failing
# the reward-blind format gate is simply ineligible. policy_dev cohort B
# (indices 24-47) stays registered but unused; it is never reassigned.
FORMAT_REPAIR_V1 = None

# --- unit-2 successor source digest (134_s) ----------------------------------

# The successor source/environment manifest issued by unit 2 must include,
# beyond the eight historical SOURCE_DIGEST_FILES, at least contract.py:
# the Stage-0 digest never bound the direct-answer parser used by the
# B1/B3/B4 arms. Unit 2 defines the complete list; this constant is the
# reviewer-required floor and is asserted against that list.
SUCCESSOR_DIGEST_REQUIRED_ADDITIONS = ("tasks/conductor/contract.py",)

# --- artifact identities ------------------------------------------------------

# SYSTEM_DIRECT (cell spec §1.11): the rev0 bytes in the freeze-digested
# prompts.py are ADOPTED unchanged as the frozen Stage-1 artifact — the
# in-code note that revising them without execution evidence would be a
# change without measurement is exactly the 103_s prompt-editing
# discipline. The digest below is the freeze; the acceptance test
# recomputes it from prompts.SYSTEM_DIRECT and fails closed on drift.
SYSTEM_DIRECT_SHA256 = (
    "b7a7d2d2bac1493eaf217dd415be1d5dd4cff4846ef16dfad825a95be2982452")

# §5.2 / §17.3-4: profile candidates. One primary per cell — the current
# complete DEFAULT_PROFILE (all six cells share its digest) — and NO
# registered fallbacks: no cell has a concrete pre-CE1 reason, and
# math_code keeps the full L_band=[8,16] with no silent index cap.
# Failure of a primary excludes the cell until a new reviewed plan.
PRIMARY_PROFILE_VERSION = "dp-2bcb6373340a8a79"
PROFILE_CANDIDATES: dict[str, tuple[str, ...]] = {
    cell: (PRIMARY_PROFILE_VERSION,)
    for cell in ("lookup_atomic", "math_atomic", "code_atomic",
                 "lookup_math", "math_code", "fork_join")
}
