"""Difficulty profile: schema, defaults, domain validation — spec §1.13–1.14.

The profile is the only source of numeric bands at generation time (none are
hard-coded in generators). Phase 1 freezes the schema and the validation
rules; every (S)-marked default value below freezes at phase 2, after the
100-example construction screen.

Canonical JSON here follows the §1.13 generator/difficulty-profile scope:
UTF-8, sorted keys, separators (",", ":"), JSON integers only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# §3.1: joint sampling cap for keyed records (record workload control).
# Bands come from the profile; this joint cap is a frozen generator rule.
KEYED_NF_CAP = 60

# §1.14: every public value inserted as a grammar literal must be
# nonnegative and fit the 12-digit literal limit.
PUBLIC_LITERAL_MAX = 999_999_999_999


class ProfileError(ValueError):
    """Offending profiles are rejected at load, never silently sampled around."""


# Initial default-profile values (§3 parameter tables; all (S)-marked).
DEFAULT_PROFILE: dict[str, Any] = {
    "cells": {
        "lookup_atomic": {
            "N_band": [3, 16], "F_band": [1, 5], "value_band": [10, 99],
        },
        "math_atomic": {
            "a_band": [10_000, 1_000_000], "b_band": [10, 99],
            "c_band": [1, 20],
            "t1": {"d_band": [2, 12]}, "t2": {"m_band": [5, 60]},
        },
        "code_atomic": {
            "L_band": [8, 16], "value_band": [1, 9],
            "k_band": [1, 9], "t_band": [1, 8],
        },
        "lookup_math": {
            "N_band": [3, 16], "F_band": [1, 5], "value_band": [10, 99],
            "p_band": [2, 9], "q_band": [1, 20],
        },
        "math_code": {
            "a_band": [100_000_000, 1_000_000_000], "b_band": [10, 99],
            "c_band": [1, 20], "L_band": [8, 16], "list_value_band": [1, 99],
        },
        "fork_join": {
            "N_band": [3, 16], "F_band": [1, 5], "value_band": [10, 99],
            "q_band": [1, 20],
            "count": {"L_band": [8, 16], "value_band": [1, 9], "t_band": [1, 8]},
            "derived_from": {"count": "code_atomic"},
        },
    },
}

# Exact per-cell field sets (§1.14 cell-scoped schema; no implicit fallback).
_CELL_FIELDS: dict[str, dict[str, Any]] = {
    "lookup_atomic": {"N_band", "F_band", "value_band"},
    "math_atomic": {"a_band", "b_band", "c_band", "t1", "t2"},
    "code_atomic": {"L_band", "value_band", "k_band", "t_band"},
    "lookup_math": {"N_band", "F_band", "value_band", "p_band", "q_band"},
    "math_code": {"a_band", "b_band", "c_band", "L_band", "list_value_band"},
    "fork_join": {"N_band", "F_band", "value_band", "q_band", "count",
                  "derived_from"},
}


def canonical_json(obj: Any) -> str:
    """§1.13 canonical JSON, integers-only scope (floats/bools/None rejected)."""
    _assert_hashable(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _assert_hashable(obj: Any) -> None:
    if isinstance(obj, bool) or obj is None or isinstance(obj, float):
        raise ProfileError(f"non-integer JSON value in hashed config: {obj!r}")
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise ProfileError(f"non-string key {key!r}")
            _assert_hashable(value)
    elif isinstance(obj, list):
        for value in obj:
            _assert_hashable(value)
    elif not isinstance(obj, (str, int)):
        raise ProfileError(f"unhashable value {obj!r}")


def profile_version(profile: dict[str, Any]) -> str:
    """`difficulty_profile_version` = "dp-" + first 16 hex of SHA-256 (§1.13)."""
    digest = hashlib.sha256(canonical_json(profile).encode("utf-8")).hexdigest()
    return "dp-" + digest[:16]


# --- band helpers -----------------------------------------------------------

def band(profile_cell: dict[str, Any], *path: str) -> tuple[int, int]:
    """Read a band like band(cells['math_atomic'], 't1', 'd_band')."""
    node: Any = profile_cell
    for part in path:
        node = node[part]
    lo, hi = node
    return lo, hi


def band_size(b: tuple[int, int]) -> int:
    return b[1] - b[0] + 1


def _check_band(cell: str, name: str, value: Any) -> tuple[int, int]:
    ok = (isinstance(value, list) and len(value) == 2
          and all(isinstance(v, int) and not isinstance(v, bool) for v in value))
    if not ok:
        raise ProfileError(f"{cell}.{name}: band must be [min, max] ints")
    lo, hi = value
    if lo > hi:
        raise ProfileError(f"{cell}.{name}: min {lo} > max {hi}")
    return lo, hi


def max_admitted_nf(n_band: tuple[int, int], f_band: tuple[int, int]) -> int:
    """Largest N*F a keyed sampler can propose under the KEYED_NF_CAP."""
    best = 0
    for n in range(n_band[0], n_band[1] + 1):
        for f in range(f_band[0], f_band[1] + 1):
            if n * f <= KEYED_NF_CAP:
                best = max(best, n * f)
    if best == 0:
        raise ProfileError("no admissible (N, F) under the N*F cap")
    return best


def s_minus(p: int, q: int, value_band: tuple[int, int]) -> list[int]:
    """S⁻(p, q) = {x in value_band : p*x - q >= 1} (§1.14, lookup_math)."""
    return [x for x in range(value_band[0], value_band[1] + 1) if p * x - q >= 1]


# --- §1.14 profile-domain validation ---------------------------------------

def _check_keyed_fields(cell: str, fields: dict[str, Any]) -> None:
    n_band = _check_band(cell, "N_band", fields["N_band"])
    f_band = _check_band(cell, "F_band", fields["F_band"])
    value_band = _check_band(cell, "value_band", fields["value_band"])
    if n_band[0] < 3:
        raise ProfileError(f"{cell}.N_band.min {n_band[0]} < 3")
    if n_band[1] > 20:
        raise ProfileError(f"{cell}.N_band.max {n_band[1]} > 20")
    if not (1 <= f_band[0] <= f_band[1] <= 10):
        raise ProfileError(f"{cell}.F_band {f_band} outside [1, 10]")
    if band_size(value_band) < max_admitted_nf(n_band, f_band):
        raise ProfileError(f"{cell}.value_band too small for N*F "
                           "without-replacement sampling")
    if value_band[0] < 1:
        raise ProfileError(f"{cell}.value_band.min {value_band[0]} < 1 "
                           "(gold >= 1 contract)")


def _check_public_literal(cell: str, name: str, b: tuple[int, int]) -> None:
    if b[0] < 0:
        raise ProfileError(f"{cell}.{name}: negative public literal")
    if b[1] > PUBLIC_LITERAL_MAX:
        raise ProfileError(f"{cell}.{name}: public literal exceeds 12 digits")


def _check_dedup_fields(cell: str, fields: dict[str, Any],
                        prefix: str = "") -> None:
    l_band = _check_band(cell, prefix + "L_band", fields["L_band"])
    value_band = _check_band(cell, prefix + "value_band", fields["value_band"])
    if l_band[0] < 5:
        raise ProfileError(f"{cell}.{prefix}L_band.min {l_band[0]} < 5 "
                           "(U >= 3 requires L >= U + 2)")
    if band_size(value_band) < 3:
        raise ProfileError(f"{cell}.{prefix}value_band admits fewer than 3 "
                           "values (U >= 3 unattainable)")
    if value_band[0] < 1:
        raise ProfileError(f"{cell}.{prefix}value_band.min < 1 "
                           "(gold >= 1 contract)")


def validate_profile(profile: dict[str, Any]) -> None:
    """Reject any §1.14 domain violation at load. Raises ProfileError."""
    if set(profile) != {"cells"}:
        raise ProfileError("profile must have exactly the 'cells' key")
    cells = profile["cells"]
    if set(cells) != set(_CELL_FIELDS):
        raise ProfileError(f"profile cells {sorted(cells)} != required "
                           f"{sorted(_CELL_FIELDS)}")
    for cell, required in _CELL_FIELDS.items():
        fields = cells[cell]
        if set(fields) != required:
            raise ProfileError(f"{cell}: fields {sorted(fields)} != required "
                               f"{sorted(required)}")

    # lookup_atomic
    _check_keyed_fields("lookup_atomic", cells["lookup_atomic"])

    # math_atomic
    ma = cells["math_atomic"]
    _check_band("math_atomic", "a_band", ma["a_band"])
    b_band = _check_band("math_atomic", "b_band", ma["b_band"])
    c_band = _check_band("math_atomic", "c_band", ma["c_band"])
    if set(ma["t1"]) != {"d_band"} or set(ma["t2"]) != {"m_band"}:
        raise ProfileError("math_atomic.t1/t2 must hold exactly d_band/m_band")
    d_band = _check_band("math_atomic", "t1.d_band", ma["t1"]["d_band"])
    m_band = _check_band("math_atomic", "t2.m_band", ma["t2"]["m_band"])
    if b_band[0] < 10:
        raise ProfileError("math_atomic.b_band.min < 10")
    if c_band[0] < 1:
        raise ProfileError("math_atomic.c_band.min < 1")
    if d_band[0] < 2:
        raise ProfileError("math_atomic.t1.d_band.min < 2")
    if m_band[0] < 2:
        raise ProfileError("math_atomic.t2.m_band.min < 2")

    # code_atomic (dedup task; value_band doubles as the select terminal)
    ca = cells["code_atomic"]
    _check_dedup_fields("code_atomic", ca)
    k_band = _check_band("code_atomic", "k_band", ca["k_band"])
    t_band = _check_band("code_atomic", "t_band", ca["t_band"])
    _check_public_literal("code_atomic", "k_band", k_band)
    _check_public_literal("code_atomic", "t_band", t_band)
    value_band = _check_band("code_atomic", "value_band", ca["value_band"])
    if value_band[0] < 1:
        raise ProfileError("code_atomic.value_band.min < 1 "
                           "(select returns a band value as the terminal)")

    # lookup_math
    lm = cells["lookup_math"]
    _check_keyed_fields("lookup_math", lm)
    p_band = _check_band("lookup_math", "p_band", lm["p_band"])
    q_band = _check_band("lookup_math", "q_band", lm["q_band"])
    _check_public_literal("lookup_math", "p_band", p_band)
    _check_public_literal("lookup_math", "q_band", q_band)
    if p_band[0] < 2:
        raise ProfileError("lookup_math.p_band.min < 2")
    if q_band[0] < 1:
        raise ProfileError("lookup_math.q_band.min < 1")
    # Minus-form intervention support: S⁻ grows with p and shrinks with q,
    # so the single (p_min, q_max) check covers every admitted pair (§1.14).
    lm_value_band = band(lm, "value_band")
    if len(s_minus(p_band[0], q_band[1], lm_value_band)) < 2:
        raise ProfileError("lookup_math: |S⁻(p_min, q_max)| < 2 "
                           "(minus-form intervention support)")

    # math_code
    mc = cells["math_code"]
    _check_band("math_code", "a_band", mc["a_band"])
    _check_band("math_code", "b_band", mc["b_band"])
    _check_band("math_code", "c_band", mc["c_band"])
    l_band = _check_band("math_code", "L_band", mc["L_band"])
    lv_band = _check_band("math_code", "list_value_band", mc["list_value_band"])
    if l_band[0] < 2:
        raise ProfileError("math_code.L_band.min < 2 "
                           "(non-empty intervention alternative set)")
    if band_size(lv_band) < l_band[1]:
        raise ProfileError("math_code.list_value_band too small for "
                           "pairwise-distinct sampling at max L")
    if lv_band[0] < 1:
        raise ProfileError("math_code.list_value_band.min < 1 "
                           "(gold >= 1 contract)")

    # fork_join
    fj = cells["fork_join"]
    _check_keyed_fields("fork_join", fj)
    fq_band = _check_band("fork_join", "q_band", fj["q_band"])
    _check_public_literal("fork_join", "q_band", fq_band)
    if fq_band[0] < 1:
        raise ProfileError("fork_join.q_band.min < 1")
    count = fj["count"]
    if set(count) != {"L_band", "value_band", "t_band"}:
        raise ProfileError("fork_join.count must hold exactly "
                           "L_band/value_band/t_band")
    _check_dedup_fields("fork_join", count, prefix="count.")
    ct_band = _check_band("fork_join", "count.t_band", count["t_band"])
    _check_public_literal("fork_join", "count.t_band", ct_band)
    if fj["derived_from"] != {"count": "code_atomic"}:
        raise ProfileError("fork_join.derived_from must record the count "
                           "branch default-copy from code_atomic")
