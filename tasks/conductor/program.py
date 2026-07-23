"""Latent-program generation — spec §1.3, §1.9, §1.13–1.16, §2, §3.

Sections mirror the spec: identity/seeds (§1.13), primitive reference
functions (§2.1), shared samplers (§2.2), IR validation (§1.3), the
categorical factor scheduler (§1.14), the six cell generators with their
frozen rejection rules and the R_MAGNITUDE pre-admission check (§1.14),
deterministic interventions (§1.9, §3), collision metadata (§1.16), and the
normative load-time validator (§4).

The execution path (executor/tools) never imports this module's reference
evaluation — reference-vs-tools agreement is measured, not shared (§1.6).
"""

from __future__ import annotations

import hashlib
import itertools
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import render
from .profiles import (
    KEYED_NF_CAP, ProfileError, band, profile_version, s_minus,
    validate_profile,
)
from .types import (
    CELL_INTERVENTION_EDGES, CELL_NODES, ENTITY_POOL, FIELD_POOL,
    MAX_ABS_VALUE, NAMESPACES,
    OP_SCHEMAS, OPERAND_NAME_MATCHED_OPS, PUBLIC_NUMERIC_PARAMS, RENDERER_IDS,
    VISIBILITY_CONDITIONS, InfrastructureError, IntegerList, IntegerRecord,
    PublicParams, Resource, format_latent_program_id,
    format_render_instance_id, is_handle, parse_render_instance_id,
    public_projection, resource_from_json,
)

SEP = "\x1f"  # §1.13 separator ␟
PROJECT_TAG = "qwen-grpo-conductor"

# Bump on any behavior change to generation (retires qualification sets).
GENERATOR_CODE_VERSION = "0a0"
GENERATOR_VERSION = f"specs-v0.8+{GENERATOR_CODE_VERSION}"

RESAMPLING_CAP = 1000  # §1.14 per-instance resampling cap

# §1.13: predeclared per-namespace maxima, batch sizes, stopping rules
# (declared at 0A; only `qualification` uses the §1.14 look schedules).
NAMESPACE_CONFIG: dict[str, dict[str, Any]] = {
    "construction": {"max_latent_clusters": 100, "expansion_batch": 100,
                     "stopping_rule": "fixed"},
    "qualification": {"max_latent_clusters": 500, "expansion_batch": 200,
                      "stopping_rule": "sequential_looks",
                      "look_schedule": (100, 300, 500),
                      "fork_join": {"max_latent_clusters": 200,
                                    "look_schedule": (100, 200)}},
    "train": {"max_latent_clusters": 50_000, "expansion_batch": 5_000,
              "stopping_rule": "fixed"},
    "dev": {"max_latent_clusters": 2_000, "expansion_batch": 1_000,
            "stopping_rule": "fixed"},
    "test": {"max_latent_clusters": 2_000, "expansion_batch": 1_000,
             "stopping_rule": "fixed"},
}


class GenerationError(RuntimeError):
    """Resampling cap reached or invariant broken — a profile-screen
    failure, never silently sampled around."""


class LoadError(ValueError):
    """Normative load-time validation mismatch (§4)."""


class RMagnitude(Exception):
    """§1.14 R_MAGNITUDE: candidate rejected pre-admission (not a load error)."""


# --- §1.13: identity and randomness ----------------------------------------

def h64(s: str) -> int:
    """First 8 bytes of SHA-256(s), big-endian unsigned."""
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")


def hex8(s: str) -> str:
    """First 8 lowercase hex characters of SHA-256(s)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def seed_material(generator_version: str, dp_version: str, namespace: str,
                  cell_id: str, latent_index: int) -> str:
    # latent_index as canonical unpadded ASCII decimal in hash inputs.
    return SEP.join([PROJECT_TAG, generator_version, dp_version, namespace,
                     cell_id, str(latent_index)])


def substream(material: str, label: str) -> np.random.Generator:
    """Labelled per-instance substream (§1.13): child seed = h64(sm ␟ label)."""
    return np.random.Generator(np.random.PCG64(h64(material + SEP + label)))


def latent_program_id(cell_id: str, namespace: str, latent_index: int,
                      material: str) -> str:
    # Formatting lives with parsing in types.py so the two cannot drift.
    return format_latent_program_id(cell_id, namespace, latent_index,
                                    hex8(material))


def render_instance_id(lp_id: str, renderer_id: str, visibility: str) -> str:
    return format_render_instance_id(lp_id, renderer_id, visibility)


def intervention_seed(lp_id: str, u: str, v: str) -> int:
    # edge_label (frozen) = "{u}->{v}" over stable semantic node ids.
    return h64(SEP.join(["intervention", lp_id, f"{u}->{v}"]))


# --- §2.1: primitive ops and direct reference functions ---------------------

def stable_unique(xs: list[int] | tuple[int, ...]) -> list[int]:
    seen: dict[int, None] = {}
    for x in xs:
        seen.setdefault(x, None)
    return list(seen)


def rotate_left(xs: list[int], k: int) -> list[int]:
    if k < 0:
        raise ValueError("rotate_left requires k >= 0")
    if not xs:
        return list(xs)
    k %= len(xs)
    return list(xs[k:]) + list(xs[:k])


def at(xs: list[int], i: int) -> int:
    if not 0 <= i < len(xs):
        raise IndexError(f"index {i} out of range for length {len(xs)}")
    return xs[i]


def count_gt(xs: list[int], t: int) -> int:
    return sum(1 for x in xs if x > t)


def prim_lookup(rec: IntegerRecord, key: str, field_name: str) -> int:
    if rec.layout != "keyed":
        raise ValueError("prim_lookup requires a keyed record")
    for entity, fields in rec.payload:
        if entity == key:
            for fname, value in fields:
                if fname == field_name:
                    return value
            raise KeyError(f"field {field_name!r} absent for {key!r}")
    raise KeyError(f"key {key!r} absent")


def prim_affine(x: int, p: int, sign: str, q: int) -> int:
    if sign not in ("+", "-"):
        raise ValueError(f"bad sign {sign!r}")
    return p * x + q if sign == "+" else p * x - q


def prim_mul_add(a: int, b: int, c: int) -> int:
    return a * b + c


def prim_ratio(a: int, b: int, c: int, d: int) -> int:
    num = a * b - c
    if d == 0 or num % d != 0:
        raise ValueError("prim_ratio requires exact division")
    return num // d


def prim_modular(a: int, b: int, c: int, m: int) -> int:
    if m <= 0:
        raise ValueError("prim_modular requires m > 0")
    return (a * b + c) % m


def prim_product_affine(x: int, y: int, q: int) -> int:
    return x * y + q


def prim_seq_count(xs: list[int], t: int) -> int:
    return count_gt(stable_unique(xs), t)


def prim_seq_select(xs: list[int], k: int, i: int) -> int:
    return at(rotate_left(stable_unique(xs), k), i)


def prim_seq_at(xs: list[int], i: int) -> int:
    return at(list(xs), i)


# --- §2.2: shared samplers (band arguments required, no defaults) -----------

class SampleRejected(Exception):
    """Candidate violates a sampling rule; counts toward the stratum cap."""

    def __init__(self, rule: str) -> None:
        super().__init__(rule)
        self.rule = rule


def integer_record(names_rng: np.random.Generator,
                   values_rng: np.random.Generator,
                   N: int, F: int, value_band: tuple[int, int],
                   layout: str) -> IntegerRecord:
    """Keyed record: entities/fields uniform without replacement, values
    uniform without replacement (§1.14)."""
    if layout != "keyed":
        raise ValueError("operands records are built per-cell from their "
                         "per-name bands, not by this sampler")
    entity_idx = names_rng.choice(len(ENTITY_POOL), size=N, replace=False)
    field_idx = names_rng.choice(len(FIELD_POOL), size=F, replace=False)
    lo, hi = value_band
    values = values_rng.choice(hi - lo + 1, size=N * F, replace=False) + lo
    payload = []
    pos = 0
    for e in entity_idx:
        fields = []
        for f in field_idx:
            fields.append((FIELD_POOL[f], int(values[pos])))
            pos += 1
        payload.append((ENTITY_POOL[e], tuple(fields)))
    return IntegerRecord(layout="keyed", payload=tuple(payload))


def integer_list_dedup(values_rng: np.random.Generator, L: int,
                       value_band: tuple[int, int]) -> tuple[list[int], int]:
    """Dedup-flavor list: i.i.d. uniform on the band; requires 3 <= U <= L-2."""
    lo, hi = value_band
    xs = [int(v) for v in values_rng.integers(lo, hi + 1, size=L)]
    u = len(stable_unique(xs))
    if not 3 <= u <= L - 2:
        raise SampleRejected("dedup_U_range")
    return xs, u


def integer_list_select(values_rng: np.random.Generator, L: int,
                        value_band: tuple[int, int]) -> list[int]:
    """Select-flavor list: uniform without replacement (pairwise distinct)."""
    lo, hi = value_band
    values = values_rng.choice(hi - lo + 1, size=L, replace=False) + lo
    return [int(v) for v in values]


# --- §1.14: categorical factor scheduler (frozen order) ---------------------

CELL_FACTORS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "lookup_atomic": (("target_stratum", ("first", "middle", "last")),),
    "math_atomic": (("template", ("T1", "T2", "T3")),),
    "code_atomic": (("shape", ("count", "select")),),
    "lookup_math": (("sign", ("minus", "plus")),
                    ("target_stratum", ("first", "middle", "last"))),
    "math_code": (),
    "fork_join": (("branch_order", ("lookup_first", "code_first")),
                  ("target_stratum", ("first", "middle", "last"))),
}


def factor_assignment(generator_version: str, dp_version: str, namespace: str,
                      cell_id: str, latent_index: int) -> dict[str, str]:
    factors = CELL_FACTORS[cell_id]
    if not factors:
        return {}
    levels = [f[1] for f in factors]
    product = list(itertools.product(*levels))
    block_size = len(product)
    block_index, offset = divmod(latent_index, block_size)
    block_seed = h64(SEP.join([PROJECT_TAG, generator_version, dp_version,
                               namespace, cell_id, "factor_perm",
                               str(block_index)]))
    rng = np.random.Generator(np.random.PCG64(block_seed))
    perm = rng.permutation(block_size)
    chosen = product[perm[offset]]
    return {name: value for (name, _), value in zip(factors, chosen)}


def full_latent_stratum(latent: dict[str, Any]) -> tuple[str, ...]:
    """§1.11: joint categorical-factor assignment (renderer excluded)."""
    factors = CELL_FACTORS[latent["cell_id"]]
    return tuple(latent["factor_assignment"][name] for name, _ in factors)


# --- §1.3: IR validation ----------------------------------------------------

def validate_reference_program(program: dict[str, Any],
                               manifest: list[str],
                               registry: dict[str, Resource]) -> None:
    """Every §1.3 IR validity rule; raises LoadError on violation."""
    # Same boundary discipline as InstanceRegistry: element types, then
    # cardinality, then the set comparison a repeated handle would pass.
    if not isinstance(manifest, (list, tuple)):
        raise LoadError("manifest must be a list of handles")
    for handle in manifest:
        if not isinstance(handle, str) or not is_handle(handle):
            raise LoadError(f"malformed handle {handle!r} in manifest")
    if len(set(manifest)) != len(manifest):
        raise LoadError(f"duplicate handles in manifest {manifest}")
    if set(manifest) != set(registry):
        raise LoadError("manifest keys != registry keys")
    nodes = program["nodes"]
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise LoadError("duplicate node ids")
    positions = program["positions"]
    if sorted(positions) != sorted(ids):
        raise LoadError("positions must contain every node exactly once")
    if program["sink"] != positions[-1]:
        raise LoadError("sink != positions[-1]")
    pos_rank = {nid: i for i, nid in enumerate(positions)}
    by_id = {n["id"]: n for n in nodes}

    for node in nodes:
        op, args = node["op"], node["args"]
        schema = OP_SCHEMAS.get(op)
        if schema is None:
            raise LoadError(f"unknown op {op!r}")
        if set(args) != set(schema):
            raise LoadError(f"{node['id']}: args {sorted(args)} != "
                            f"required {sorted(schema)}")
        operand_handles: set[str] = set()
        for slot, kind in schema.items():
            ref = args[slot]
            if not isinstance(ref, dict) or len(ref) != 1:
                raise LoadError(f"{node['id']}.{slot}: malformed ref {ref!r}")
            ((ref_kind, ref_val),) = ref.items()
            if kind == "lit_int":
                if ref_kind != "lit" or not isinstance(ref_val, int) \
                        or isinstance(ref_val, bool):
                    raise LoadError(f"{node['id']}.{slot}: expected int lit")
            elif kind == "lit_str":
                if ref_kind != "lit" or not isinstance(ref_val, str):
                    raise LoadError(f"{node['id']}.{slot}: expected str lit")
            elif kind == "lit_sign":
                if ref_kind != "lit" or ref_val not in ("+", "-"):
                    raise LoadError(f"{node['id']}.{slot}: expected sign lit")
            elif kind == "node":
                if ref_kind != "node" or ref_val not in by_id:
                    raise LoadError(f"{node['id']}.{slot}: undeclared node")
                if pos_rank[ref_val] >= pos_rank[node["id"]]:
                    raise LoadError(f"{node['id']}.{slot}: positions is not "
                                    f"a topological ordering")
            elif kind == "operand":
                if ref_kind != "operand":
                    raise LoadError(f"{node['id']}.{slot}: expected operand")
                handle, name = ref_val["res"], ref_val["name"]
                res = registry.get(handle)
                if res is None or handle not in manifest:
                    raise LoadError(f"{node['id']}.{slot}: unknown handle")
                if not isinstance(res, IntegerRecord) \
                        or res.layout != "operands":
                    raise LoadError(f"{node['id']}.{slot}: incompatible "
                                    f"layout for operand ref")
                if res.operand(name) is None:
                    raise LoadError(f"{node['id']}.{slot}: operand "
                                    f"{name!r} absent")
                if op in OPERAND_NAME_MATCHED_OPS and name != slot:
                    raise LoadError(f"{node['id']}.{slot}: operand name "
                                    f"{name!r} must match slot")
                operand_handles.add(handle)
            elif kind in ("res_keyed", "res_list"):
                if ref_kind != "res":
                    raise LoadError(f"{node['id']}.{slot}: expected res ref")
                res = registry.get(ref_val)
                if res is None or ref_val not in manifest:
                    raise LoadError(f"{node['id']}.{slot}: unknown handle")
                if kind == "res_keyed" and not (
                        isinstance(res, IntegerRecord) and res.layout == "keyed"):
                    raise LoadError(f"{node['id']}.{slot}: not a keyed record")
                if kind == "res_list" and not isinstance(res, IntegerList):
                    raise LoadError(f"{node['id']}.{slot}: not an "
                                    f"integer_list")
            else:  # pragma: no cover
                raise LoadError(f"unknown slot kind {kind!r}")
        if len(operand_handles) > 1:
            raise LoadError(f"{node['id']}: operand refs span multiple "
                            f"records")


# --- checked reference evaluation (R_MAGNITUDE decomposition, §1.14) --------

def _chk(v: int) -> int:
    if abs(v) > MAX_ABS_VALUE:
        raise RMagnitude(str(v))
    return v


def evaluate_reference(program: dict[str, Any],
                       registry: dict[str, Resource],
                       overrides: dict[str, int] | None = None
                       ) -> dict[str, int]:
    """Evaluate nodes in `positions` order with the artifact-level operator
    decomposition magnitude checks. `overrides` implements §1.9 wire
    semantics: downstream consumers of node u read overrides[u]."""
    overrides = overrides or {}
    by_id = {n["id"]: n for n in program["nodes"]}
    values: dict[str, int] = {}

    def wire(node_id: str) -> int:
        return overrides.get(node_id, values[node_id])

    for node_id in program["positions"]:
        node = by_id[node_id]
        op, args = node["op"], node["args"]

        def lit(slot: str) -> Any:
            return args[slot]["lit"]

        def operand(slot: str) -> int:
            ref = args[slot]["operand"]
            rec = registry[ref["res"]]
            assert isinstance(rec, IntegerRecord)
            value = rec.operand(ref["name"])
            assert value is not None
            return _chk(value)

        if op == "lookup":
            rec = registry[args["handle"]["res"]]
            assert isinstance(rec, IntegerRecord)
            value = _chk(prim_lookup(rec, lit("key"), lit("field")))
        elif op == "affine":
            x = _chk(wire(args["x"]["node"]))
            product = _chk(lit("p") * x)
            value = _chk(product + lit("q") if lit("sign") == "+"
                         else product - lit("q"))
        elif op == "mul_add":
            a, b, c = operand("a"), operand("b"), operand("c")
            value = _chk(_chk(a * b) + c)
        elif op == "ratio":
            a, b, c, d = (operand("a"), operand("b"), operand("c"),
                          operand("d"))
            num = _chk(_chk(a * b) - c)
            if d == 0 or num % d != 0:
                raise ValueError("ratio requires exact division")
            value = _chk(num // d)
        elif op == "modular":
            a, b, c, m = (operand("a"), operand("b"), operand("c"),
                          operand("m"))
            if m <= 0:
                raise ValueError("modular requires m > 0")
            value = _chk(_chk(_chk(a * b) + c) % m)
        elif op == "product_affine":
            x = _chk(wire(args["x"]["node"]))
            y = _chk(wire(args["y"]["node"]))
            value = _chk(_chk(x * y) + lit("q"))
        elif op == "seq_count":
            xs = registry[args["xs"]["res"]]
            assert isinstance(xs, IntegerList)
            value = _chk(prim_seq_count(list(xs.payload), lit("t")))
        elif op == "seq_select":
            xs = registry[args["xs"]["res"]]
            assert isinstance(xs, IntegerList)
            value = _chk(prim_seq_select(list(xs.payload), lit("k"), lit("i")))
        elif op == "seq_at":
            xs = registry[args["xs"]["res"]]
            assert isinstance(xs, IntegerList)
            value = _chk(prim_seq_at(list(xs.payload), _chk(wire(args["i"]["node"]))))
        else:  # pragma: no cover
            raise LoadError(f"unknown op {op!r}")
        values[node_id] = value
    return values


# --- registry helpers -------------------------------------------------------

def registry_from_json(reg: dict[str, dict[str, Any]]) -> dict[str, Resource]:
    return {h: resource_from_json(obj) for h, obj in reg.items()}


def registry_to_json(reg: dict[str, Resource]) -> dict[str, dict[str, Any]]:
    return {h: res.to_json() for h, res in reg.items()}


def node_resource(program: dict[str, Any], node_id: str) -> str | None:
    """The single resource handle a node's args demand, or None."""
    node = next(n for n in program["nodes"] if n["id"] == node_id)
    handles = set()
    for ref in node["args"].values():
        if "res" in ref:
            handles.add(ref["res"])
        elif "operand" in ref:
            handles.add(ref["operand"]["res"])
    if len(handles) > 1:
        raise LoadError(f"{node_id}: multiple resources demanded")
    return handles.pop() if handles else None


# --- §1.9 + §3: interventions ----------------------------------------------

INTERVENTION_EDGES = CELL_INTERVENTION_EDGES  # single definition, §1.9


def _replacement_support(latent: dict[str, Any], u: str,
                         profile: dict[str, Any]) -> list[int]:
    """§3 replacement pools, ascending order (frozen draw convention)."""
    cell, params = latent["cell_id"], latent["params"]
    node_values = latent["node_values"]
    cells = profile["cells"]
    if cell == "lookup_math":
        vb = band(cells["lookup_math"], "value_band")
        pool = (s_minus(params["p"], params["q"], vb)
                if params["sign"] == "-" else list(range(vb[0], vb[1] + 1)))
        return [x for x in pool if x != node_values["n1"]]
    if cell == "math_code":
        return [x for x in range(0, params["m"]) if x != node_values["n1"]]
    if cell == "fork_join":
        if u == "n1":
            vb = band(cells["fork_join"], "value_band")
            return [x for x in range(vb[0], vb[1] + 1)
                    if x != node_values["n1"]]
        if u == "n2":
            return [x for x in range(1, params["U"])
                    if x != node_values["n2"]]
    raise GenerationError(f"no replacement rule for {cell}:{u}")


def draw_intervention(latent: dict[str, Any], u: str, v: str,
                      profile: dict[str, Any]) -> dict[str, Any]:
    """One deterministic replacement per (latent_program_id, edge) (§1.9);
    one mutated execution scored twice (corruption + counterfactual).

    The public entry point validates that `profile` is the profile the
    latent was generated under — the replacement support is drawn from it,
    so a mis-wired but individually valid profile would silently change the
    counterfactual target on a resumed run — and that the latent's own
    identity is self-consistent: the intervention seed derives from
    `latent_program_id`, so a swapped id would silently change the
    deterministic replacement. Internal generation calls
    `_draw_intervention` directly, having established both once at the top
    of `generate_latent`, so neither check is repeated per edge.
    """
    validate_profile(profile)
    if profile_version(profile) != latent["difficulty_profile_version"]:
        raise GenerationError(
            f"intervention profile {profile_version(profile)} does not match "
            f"the latent's {latent['difficulty_profile_version']}")
    if latent.get("generator_version") != GENERATOR_VERSION:
        raise GenerationError(
            f"latent generator_version {latent.get('generator_version')!r} "
            f"is not the current {GENERATOR_VERSION!r}; regenerate it")
    material = seed_material(GENERATOR_VERSION,
                             latent["difficulty_profile_version"],
                             latent["namespace"], latent["cell_id"],
                             latent["latent_index"])
    expected_id = latent_program_id(latent["cell_id"], latent["namespace"],
                                    latent["latent_index"], material)
    if latent["latent_program_id"] != expected_id \
            or latent["seed"] != h64(material):
        raise GenerationError(
            f"latent identity {latent['latent_program_id']!r} does not "
            f"derive from its own cell/namespace/index (expected "
            f"{expected_id!r})")
    return _draw_intervention(latent, u, v, profile)


def _draw_intervention(latent: dict[str, Any], u: str, v: str,
                       profile: dict[str, Any]) -> dict[str, Any]:
    """Core: assumes `profile` is valid and is the latent's own profile."""
    # Fail closed rather than emit an invalid record: ordinary generation
    # iterates the legal table, but a caller passing (n1, n1) must not get a
    # usable record back.
    legal = CELL_INTERVENTION_EDGES[latent["cell_id"]]
    if (u, v) not in legal:
        raise GenerationError(
            f"({u}, {v}) is not a dependency edge of {latent['cell_id']}; "
            f"legal edges are {list(legal)}")
    support = _replacement_support(latent, u, profile)
    if not support:
        raise GenerationError(
            f"empty intervention support for {latent['latent_program_id']} "
            f"edge {u}->{v}")
    rng = np.random.Generator(np.random.PCG64(
        intervention_seed(latent["latent_program_id"], u, v)))
    replacement = support[int(rng.integers(0, len(support)))]
    registry = registry_from_json(latent["private_registry"])
    mutated = evaluate_reference(latent["reference_program"], registry,
                                 overrides={u: replacement})
    sink = latent["reference_program"]["sink"]
    # §3: replacement rules are constructed to provably change the sink.
    if mutated[sink] == latent["gold_answer"]:
        raise GenerationError(
            f"intervention on {u}->{v} for {latent['latent_program_id']} "
            f"left the sink unchanged ({mutated[sink]})")
    positions = latent["reference_program"]["positions"]
    return {
        "edge": (u, v),
        "replacement": replacement,
        # §1.9 positional application: override step_j, j = 1 + index(u).
        "override_position": 1 + positions.index(u),
        "corruption_target": latent["gold_answer"],
        "counterfactual_target": mutated[latent["reference_program"]["sink"]],
    }


# --- §1.16: collision metadata ----------------------------------------------

def public_numeric_values(cell_id: str,
                          params: PublicParams) -> dict[str, int]:
    """Provenance-tagged public semantic parameters — read from the public
    projection, never by scanning rendered text (§1.16)."""
    key = cell_id
    if cell_id == "code_atomic":
        key = f"code_atomic_{params['shape']}"
    return {name: params[name] for name in PUBLIC_NUMERIC_PARAMS[key]}


def collision_metadata(cell_id: str, params: PublicParams,
                       node_values: dict[str, int],
                       sink: str) -> dict[str, Any]:
    values = public_numeric_values(cell_id, params)
    nodes = {}
    for node_id, value in node_values.items():
        matches = sorted(n for n, v in values.items() if v == value)
        if matches:
            nodes[node_id] = matches
    return {
        "public_numeric_values": values,
        "public_numeric_collision_nodes": nodes,
        "public_numeric_collision": bool(nodes),
        "sink_public_numeric_collision": sink in nodes,
    }


# --- cell proposal functions ------------------------------------------------

def _uniform(rng: np.random.Generator, b: tuple[int, int]) -> int:
    return int(rng.integers(b[0], b[1] + 1))


def _draw_handles(handles_rng: np.random.Generator, n: int) -> list[str]:
    """`R-` + digit + uppercase + digit; uniform, unique per instance (N1)."""
    out: list[str] = []
    while len(out) < n:
        h = (f"R-{int(handles_rng.integers(0, 10))}"
             f"{chr(65 + int(handles_rng.integers(0, 26)))}"
             f"{int(handles_rng.integers(0, 10))}")
        if h not in out:
            out.append(h)
    return out


_STRATUM_INDEX = {"first": 0, "middle": 1, "last": 2}


def _keyed_record_with_target(rngs: dict[str, np.random.Generator],
                              cell_profile: dict[str, Any],
                              target_stratum: str):
    """Sample a keyed record and its stratified target (§1.14).

    Returns (record, key, field, target_value). Raises SampleRejected on the
    N*F cap."""
    n_band = band(cell_profile, "N_band")
    f_band = band(cell_profile, "F_band")
    value_band = band(cell_profile, "value_band")
    N = _uniform(rngs["values"], n_band)
    F = _uniform(rngs["values"], f_band)
    if N * F > KEYED_NF_CAP:
        raise SampleRejected("nf_cap")
    rec = integer_record(rngs["names"], rngs["values"], N, F, value_band,
                         "keyed")
    strata = np.array_split(np.arange(N), 3)
    stratum = strata[_STRATUM_INDEX[target_stratum]]
    entity_pos = int(stratum[int(rngs["names"].integers(0, len(stratum)))])
    field_pos = int(rngs["names"].integers(0, F))
    key = rec.payload[entity_pos][0]
    field_name, target_value = rec.payload[entity_pos][1][field_pos]
    return rec, key, field_name, target_value


def _propose_lookup_atomic(rngs, cell_profile, assignment):
    rec, key, field_name, gold = _keyed_record_with_target(
        rngs, cell_profile, assignment["target_stratum"])
    (h,) = _draw_handles(rngs["handles"], 1)
    program = {
        "nodes": [{"id": "n1", "op": "lookup",
                   "args": {"handle": {"res": h}, "key": {"lit": key},
                            "field": {"lit": field_name}}}],
        "positions": ["n1"], "sink": "n1",
    }
    params = {"H": h, "key": key, "field": field_name}
    return params, {h: rec}, program


def _sample_congruent(rng: np.random.Generator, value_band: tuple[int, int],
                      residue: int, modulus: int) -> int:
    """Uniform draw from {c ∈ value_band : c ≡ residue (mod modulus)}.

    Solved arithmetically rather than by materializing the feasible set:
    the band can legitimately span a million values while the congruence
    admits few or none, and the enumeration would then be repeated for
    every one of the resampling attempts.
    """
    lo, hi = value_band
    # First value ≥ lo that is congruent to `residue` modulo `modulus`.
    first = lo + ((residue - lo) % modulus)
    if first > hi:
        raise SampleRejected("t1_constructive_empty")
    count = (hi - first) // modulus + 1
    return first + modulus * int(rng.integers(0, count))


def _propose_math_atomic(rngs, cell_profile, assignment):
    template = assignment["template"]
    a = _uniform(rngs["values"], band(cell_profile, "a_band"))
    b = _uniform(rngs["values"], band(cell_profile, "b_band"))
    c_band = band(cell_profile, "c_band")
    if template == "T1":
        d = _uniform(rngs["values"], band(cell_profile, "t1", "d_band"))
        c = _sample_congruent(rngs["values"], c_band, (a * b) % d, d)
        names, op, extra = ("a", "b", "c", "d"), "ratio", d
    elif template == "T2":
        m = _uniform(rngs["values"], band(cell_profile, "t2", "m_band"))
        c = _uniform(rngs["values"], c_band)
        names, op, extra = ("a", "b", "c", "m"), "modular", m
    else:
        c = _uniform(rngs["values"], c_band)
        names, op, extra = ("a", "b", "c"), "mul_add", None
    operand_values = dict(zip(names, (a, b, c) + ((extra,) if extra else ())))
    rec = IntegerRecord(layout="operands",
                        payload=tuple(operand_values.items()))
    (h,) = _draw_handles(rngs["handles"], 1)
    program = {
        "nodes": [{"id": "n1", "op": op,
                   "args": {n: {"operand": {"res": h, "name": n}}
                            for n in names}}],
        "positions": ["n1"], "sink": "n1",
    }
    params = {"H": h, "template": template, **operand_values}

    # §3.2 rejection rules.
    answer = {"ratio": lambda: prim_ratio(a, b, c, extra),
              "modular": lambda: prim_modular(a, b, c, extra),
              "mul_add": lambda: prim_mul_add(a, b, c)}[op]()
    if not 1 <= answer <= 10**9:
        raise SampleRejected("answer_range")
    if answer in operand_values.values():
        raise SampleRejected("answer_in_operands")
    if template == "T2":
        _modular_checks(a, b, c, extra, answer)
    return params, {h: rec}, program


def _modular_checks(a: int, b: int, c: int, m: int, g: int) -> None:
    """§3.2 modular relevance + wrong-program exclusions (also math_code n1)."""
    if (a * b) % m == g:
        raise SampleRejected("modular_relevance_drop_c")
    if (b + c) % m == g:
        raise SampleRejected("modular_relevance_a_to_1")
    if (a + c) % m == g:
        raise SampleRejected("modular_relevance_b_to_1")
    if (a + b + c) % m == g:
        raise SampleRejected("modular_exclusion_mul_to_add")
    if (a * b - c) % m == g:
        raise SampleRejected("modular_exclusion_sign_flip")


def _propose_code_atomic(rngs, cell_profile, assignment):
    shape = assignment["shape"]
    L = _uniform(rngs["values"], band(cell_profile, "L_band"))
    xs, U = integer_list_dedup(rngs["values"], L,
                               band(cell_profile, "value_band"))
    unique = stable_unique(xs)
    (h,) = _draw_handles(rngs["handles"], 1)
    if shape == "count":
        t = _uniform(rngs["values"], band(cell_profile, "t_band"))
        answer = count_gt(unique, t)
        if not 1 <= answer <= U - 1:
            raise SampleRejected("count_range")
        if count_gt(xs, t) == answer:
            raise SampleRejected("dedup_ablation")
        params = {"H": h, "shape": shape, "t": t, "U": U}
        args = {"xs": {"res": h}, "t": {"lit": t}}
        op = "seq_count"
    else:
        k = _uniform(rngs["values"], band(cell_profile, "k_band"))
        if k % U == 0:
            raise SampleRejected("k_mod_U")
        i = int(rngs["values"].integers(0, U))
        answer = at(rotate_left(unique, k), i)
        if at(rotate_left(xs, k), i) == answer:
            raise SampleRejected("dedup_ablation")
        if at(unique, i) == answer:
            raise SampleRejected("rotation_ablation")
        params = {"H": h, "shape": shape, "k": k, "i": i, "U": U}
        args = {"xs": {"res": h}, "k": {"lit": k}, "i": {"lit": i}}
        op = "seq_select"
    program = {"nodes": [{"id": "n1", "op": op, "args": args}],
               "positions": ["n1"], "sink": "n1"}
    return params, {h: IntegerList(payload=tuple(xs))}, program


def _propose_lookup_math(rngs, cell_profile, assignment):
    rec, key, field_name, n1 = _keyed_record_with_target(
        rngs, cell_profile, assignment["target_stratum"])
    p = _uniform(rngs["values"], band(cell_profile, "p_band"))
    q = _uniform(rngs["values"], band(cell_profile, "q_band"))
    sign = "-" if assignment["sign"] == "minus" else "+"
    answer = prim_affine(n1, p, sign, q)
    if answer < 1:
        raise SampleRejected("answer_range")
    record_values = [v for _, fields in rec.payload for _, v in fields]
    if answer in record_values:
        raise SampleRejected("answer_in_record")
    if answer == n1:
        raise SampleRejected("answer_echo")
    (h,) = _draw_handles(rngs["handles"], 1)
    program = {
        "nodes": [
            {"id": "n1", "op": "lookup",
             "args": {"handle": {"res": h}, "key": {"lit": key},
                      "field": {"lit": field_name}}},
            {"id": "n2", "op": "affine",
             "args": {"x": {"node": "n1"}, "p": {"lit": p},
                      "sign": {"lit": sign}, "q": {"lit": q}}},
        ],
        "positions": ["n1", "n2"], "sink": "n2",
    }
    params = {"H": h, "key": key, "field": field_name, "p": p, "q": q,
              "sign": sign}
    return params, {h: rec}, program


def _propose_math_code(rngs, cell_profile, assignment):
    a = _uniform(rngs["values"], band(cell_profile, "a_band"))
    b = _uniform(rngs["values"], band(cell_profile, "b_band"))
    c = _uniform(rngs["values"], band(cell_profile, "c_band"))
    L = _uniform(rngs["values"], band(cell_profile, "L_band"))
    m = L  # D6: index validity by construction
    xs = integer_list_select(rngs["values"], L,
                             band(cell_profile, "list_value_band"))
    n1 = prim_modular(a, b, c, m)
    answer = at(xs, n1)
    if answer == n1:
        raise SampleRejected("index_echo")
    if answer in (a, b, c, m):
        raise SampleRejected("answer_in_operands")
    _modular_checks(a, b, c, m, n1)
    h1, h2 = _draw_handles(rngs["handles"], 2)
    rec = IntegerRecord(layout="operands",
                        payload=(("a", a), ("b", b), ("c", c), ("m", m)))
    program = {
        "nodes": [
            {"id": "n1", "op": "modular",
             "args": {n: {"operand": {"res": h1, "name": n}}
                      for n in ("a", "b", "c", "m")}},
            {"id": "n2", "op": "seq_at",
             "args": {"xs": {"res": h2}, "i": {"node": "n1"}}},
        ],
        "positions": ["n1", "n2"], "sink": "n2",
    }
    params = {"H1": h1, "H2": h2, "a": a, "b": b, "c": c, "m": m}
    return params, {h1: rec, h2: IntegerList(payload=tuple(xs))}, program


def _propose_fork_join(rngs, cell_profile, assignment):
    rec, key, field_name, n_lk = _keyed_record_with_target(
        rngs, cell_profile, assignment["target_stratum"])
    count_profile = cell_profile["count"]
    L = _uniform(rngs["values"], band(count_profile, "L_band"))
    xs, U = integer_list_dedup(rngs["values"], L,
                               band(count_profile, "value_band"))
    t = _uniform(rngs["values"], band(count_profile, "t_band"))
    n_code = count_gt(stable_unique(xs), t)
    if not 1 <= n_code <= U - 1:
        raise SampleRejected("count_range")
    if count_gt(xs, t) == n_code:
        raise SampleRejected("dedup_ablation")
    q = _uniform(rngs["values"], band(cell_profile, "q_band"))
    answer = prim_product_affine(n_lk, n_code, q)
    if answer in (n_lk, n_code):
        raise SampleRejected("answer_echo")
    record_values = [v for _, fields in rec.payload for _, v in fields]
    if answer in record_values:
        raise SampleRejected("answer_in_record")
    if answer in xs:
        raise SampleRejected("answer_in_list")
    h1, h2 = _draw_handles(rngs["handles"], 2)
    branch_order = assignment["branch_order"]
    positions = (["n1", "n2", "n3"] if branch_order == "lookup_first"
                 else ["n2", "n1", "n3"])
    program = {
        "nodes": [
            {"id": "n1", "op": "lookup",
             "args": {"handle": {"res": h1}, "key": {"lit": key},
                      "field": {"lit": field_name}}},
            {"id": "n2", "op": "seq_count",
             "args": {"xs": {"res": h2}, "t": {"lit": t}}},
            {"id": "n3", "op": "product_affine",
             "args": {"x": {"node": "n1"}, "y": {"node": "n2"},
                      "q": {"lit": q}}},
        ],
        "positions": positions, "sink": "n3",
    }
    params = {"H1": h1, "H2": h2, "key": key, "field": field_name, "t": t,
              "q": q, "U": U, "branch_order": branch_order}
    return params, {h1: rec, h2: IntegerList(payload=tuple(xs))}, program


_PROPOSERS = {
    "lookup_atomic": _propose_lookup_atomic,
    "math_atomic": _propose_math_atomic,
    "code_atomic": _propose_code_atomic,
    "lookup_math": _propose_lookup_math,
    "math_code": _propose_math_code,
    "fork_join": _propose_fork_join,
}


# --- generation entry point -------------------------------------------------

@dataclass
class GenerationResult:
    latent: dict[str, Any]
    attempts: int
    rejections: Counter = field(default_factory=Counter)


def namespace_cap(namespace: str, cell_id: str) -> int:
    config = NAMESPACE_CONFIG[namespace]
    if cell_id == "fork_join" and "fork_join" in config:
        return config["fork_join"]["max_latent_clusters"]
    return config["max_latent_clusters"]


def generate_latent(cell_id: str, namespace: str, latent_index: int,
                    profile: dict[str, Any]) -> GenerationResult:
    if cell_id not in _PROPOSERS:
        raise GenerationError(f"unknown cell_id {cell_id!r}")
    if namespace not in NAMESPACES:
        raise GenerationError(f"unknown namespace {namespace!r}")
    # `bool` subclasses `int`: `False` would display as index 00000 while
    # seeding from the string "False", producing an instance that fails its
    # own normative regeneration.
    if not isinstance(latent_index, int) or isinstance(latent_index, bool):
        raise GenerationError(
            f"latent_index must be a plain int, got {latent_index!r}")
    if not 0 <= latent_index < namespace_cap(namespace, cell_id):
        raise GenerationError(
            f"latent_index {latent_index} outside the predeclared "
            f"{namespace} range for {cell_id} "
            f"[0, {namespace_cap(namespace, cell_id)})")
    validate_profile(profile)
    dp_version = profile_version(profile)
    material = seed_material(GENERATOR_VERSION, dp_version, namespace,
                             cell_id, latent_index)
    lp_id = latent_program_id(cell_id, namespace, latent_index, material)
    assignment = factor_assignment(GENERATOR_VERSION, dp_version, namespace,
                                   cell_id, latent_index)
    rngs = {label: substream(material, label)
            for label in ("values", "names", "handles", "manifest")}
    cell_profile = profile["cells"][cell_id]
    rejections: Counter = Counter()

    for attempt in range(1, RESAMPLING_CAP + 1):
        try:
            params, registry, program = _PROPOSERS[cell_id](
                rngs, cell_profile, assignment)
            manifest = sorted(registry)
            manifest = [manifest[int(i)] for i in
                        rngs["manifest"].permutation(len(manifest))]  # N8
            validate_reference_program(program, manifest, registry)
            node_values = evaluate_reference(program, registry)
            public_params = public_projection(cell_id, params)
            latent = {
                "cell_id": cell_id,
                "namespace": namespace,
                "latent_index": latent_index,
                "latent_program_id": lp_id,
                "seed": h64(material),
                "difficulty_profile_version": dp_version,
                "generator_version": GENERATOR_VERSION,
                "factor_assignment": assignment,
                # `params` is private generator state (operand values, the
                # target lookup value, U); `public_params` is the only
                # mapping renderers and subtasks ever see (§1.4).
                "params": params,
                "public_params": public_params,
                "public_manifest": manifest,
                "private_registry": registry_to_json(registry),
                "reference_program": program,
                "gold_answer": node_values[program["sink"]],
                "node_values": node_values,
                **collision_metadata(cell_id, public_params, node_values,
                                     program["sink"]),
            }
            # §1.14 R_MAGNITUDE: base path was checked during evaluation;
            # now check every deterministically drawn intervention path.
            # The profile was validated at the top of this function and the
            # latent carries its version, so use the unchecked core rather
            # than re-hashing the profile per edge per resample attempt.
            for u, v in INTERVENTION_EDGES[cell_id]:
                _draw_intervention(latent, u, v, profile)
            if latent["gold_answer"] < 1:
                raise GenerationError(
                    f"gold < 1 escaped rejection rules for {lp_id}")
            return GenerationResult(latent, attempt, rejections)
        except SampleRejected as rej:
            rejections[rej.rule] += 1
        except RMagnitude:
            rejections["R_MAGNITUDE"] += 1
    raise GenerationError(
        f"resampling cap {RESAMPLING_CAP} reached for {lp_id} "
        f"(profile-screen failure); rejections: {dict(rejections)}")


# --- rendered instances (§1.3 stored schema) --------------------------------

def workflow_steps(latent: dict[str, Any]) -> list[dict[str, Any]]:
    """Observation steps in `positions` order: resource, access, subtask."""
    program = latent["reference_program"]
    positions = program["positions"]
    from .types import LEGAL_ACCESS_PATTERNS
    access = LEGAL_ACCESS_PATTERNS[len(positions)]
    subtasks = render.reference_subtasks(latent["cell_id"],
                                         latent["public_params"])
    return [{"node": node_id,
             "resource": node_resource(program, node_id),
             "access": access[idx],
             "subtask": subtasks[node_id]}
            for idx, node_id in enumerate(positions)]


def observation_for(latent: dict[str, Any],
                    instance: dict[str, Any]) -> str:
    """Canonical Conductor observation for a rendered instance (§1.5).

    Disclosure follows the instance's own identity and registry; the steps
    come from the reference topology in `positions` order.
    """
    if instance["latent_program_id"] != latent["latent_program_id"]:
        raise InfrastructureError(
            "instance and latent describe different latent programs")
    return render.build_observation(instance, workflow_steps(latent))


def render_instance(latent: dict[str, Any], renderer_id: str,
                    visibility_condition: str) -> dict[str, Any]:
    if renderer_id not in RENDERER_IDS:
        raise ValueError(f"unknown renderer {renderer_id!r}")
    if visibility_condition not in VISIBILITY_CONDITIONS:
        raise ValueError(
            f"unknown visibility_condition {visibility_condition!r}")
    public_prompt = render.render_public_prompt(
        latent["cell_id"], renderer_id, latent["public_params"])
    return {
        "cell_id": latent["cell_id"],
        "latent_program_id": latent["latent_program_id"],
        "render_instance_id": render_instance_id(
            latent["latent_program_id"], renderer_id, visibility_condition),
        "renderer_id": renderer_id,
        "split_id": latent["namespace"],
        "visibility_condition": visibility_condition,
        "difficulty_profile_version": latent["difficulty_profile_version"],
        "generator_version": latent["generator_version"],
        "seed": latent["seed"],
        "public_numeric_values": latent["public_numeric_values"],
        "public_numeric_collision_nodes":
            latent["public_numeric_collision_nodes"],
        "public_numeric_collision": latent["public_numeric_collision"],
        "sink_public_numeric_collision":
            latent["sink_public_numeric_collision"],
        "public_prompt": public_prompt,
        "public_manifest": list(latent["public_manifest"]),
        "private_registry": latent["private_registry"],
        "reference_program": latent["reference_program"],
        "gold_answer": latent["gold_answer"],
    }


# The exact §1.3 stored-instance schema, for load-time shape validation.
INSTANCE_FIELDS = frozenset({
    "cell_id", "latent_program_id", "render_instance_id", "renderer_id",
    "split_id", "visibility_condition", "difficulty_profile_version",
    "generator_version", "seed", "public_numeric_values",
    "public_numeric_collision_nodes", "public_numeric_collision",
    "sink_public_numeric_collision", "public_prompt", "public_manifest",
    "private_registry", "reference_program", "gold_answer",
})


def validate_instance(instance: dict[str, Any],
                      profile: dict[str, Any]) -> None:
    """§4 normative load-time validation: regenerate from identity fields and
    require byte/field equality; re-run IR validation and reference
    evaluation. The generator's rejection path re-asserts the sampling rules.

    Every failure surfaces as LoadError — this is the persisted-artifact
    boundary the resumable Stage-1 loader relies on, so malformed shapes,
    malformed identities, and regeneration failures are all translated
    rather than leaking KeyError/ValueError/GenerationError.
    """
    if not isinstance(instance, dict):
        raise LoadError(f"instance must be an object, got "
                        f"{type(instance).__name__}")
    if set(instance) != INSTANCE_FIELDS:
        missing = sorted(INSTANCE_FIELDS - set(instance))
        extra = sorted(set(instance) - INSTANCE_FIELDS)
        raise LoadError(f"instance fields do not match the §1.3 schema "
                        f"(missing {missing}, unexpected {extra})")
    try:
        render_id = parse_render_instance_id(instance["render_instance_id"])
    except ValueError as exc:
        raise LoadError(f"malformed render_instance_id: {exc}") from exc
    if instance["latent_program_id"] != render_id.latent_program_id:
        raise LoadError("latent_program_id disagrees with render_instance_id")
    if instance["difficulty_profile_version"] != profile_version(profile):
        raise LoadError("difficulty_profile_version mismatch")
    latent = render_id.latent
    try:
        result = generate_latent(latent.cell_id, latent.namespace,
                                 latent.latent_index, profile)
        regenerated = render_instance(result.latent, instance["renderer_id"],
                                      instance["visibility_condition"])
    except (GenerationError, ValueError) as exc:
        raise LoadError(f"instance does not regenerate: {exc}") from exc
    if regenerated != instance:
        diff = [k for k in regenerated
                if regenerated[k] != instance.get(k)]
        raise LoadError(f"instance mismatch on fields {diff}")
    try:
        registry = registry_from_json(instance["private_registry"])
    except (ValueError, KeyError, TypeError) as exc:
        raise LoadError(f"malformed private_registry: {exc}") from exc
    validate_reference_program(instance["reference_program"],
                               instance["public_manifest"], registry)
    values = evaluate_reference(instance["reference_program"], registry)
    if values[instance["reference_program"]["sink"]] != \
            instance["gold_answer"]:
        raise LoadError("gold_answer mismatch")
