"""Core types and frozen conventions — spec §1.1, §1.2, §1.3, §1.6, §1.7.

Everything here is phase-1 frozen (conductor_cell_specs.md v0.8): typed
rejection codes, canonical integer wire form, resource kinds and their
worker-facing payload text, the normative per-operation IR schemas, uniform
artifact limits, and the WorkerResult union with its flag truth table.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

# --- §1.6: typed rejection codes -------------------------------------------

REJECTION_CODES = frozenset({
    "E_NO_ARTIFACT", "E_MULTI_ARTIFACT", "E_UNCLOSED_ARTIFACT",
    "E_UNEXPECTED_TAG", "E_PARSE", "E_NONCANONICAL_INT", "E_UNKNOWN_IDENT",
    "E_NO_RESOURCE", "E_RESOURCE_KIND", "E_UNKNOWN_KEY", "E_UNKNOWN_FIELD",
    "E_INDEX_RANGE", "E_INEXACT_DIV", "E_DIV_ZERO", "E_BAD_ARG", "E_DEPTH",
    "E_MAGNITUDE",
})

# §1.7 flag truth table: envelope + grammar/limit failures never execute a
# tool (artifact_valid = tool_executed = False); the remaining codes are
# semantic tool rejections (artifact parsed, tool ran, typed refusal).
SYNTAX_REJECTION_CODES = frozenset({
    "E_NO_ARTIFACT", "E_MULTI_ARTIFACT", "E_UNCLOSED_ARTIFACT",
    "E_UNEXPECTED_TAG", "E_PARSE", "E_NONCANONICAL_INT", "E_DEPTH",
})
SEMANTIC_REJECTION_CODES = REJECTION_CODES - SYNTAX_REJECTION_CODES


class InfrastructureError(RuntimeError):
    """Unexpected failure outside the typed-rejection contract — aborts."""


# --- §1.6: uniform limits ---------------------------------------------------

ARTIFACT_MAX_BYTES = 512      # trimmed artifact content, else E_PARSE
AST_MAX_NODES = 64            # else E_DEPTH
AST_MAX_DEPTH = 8             # else E_DEPTH
LITERAL_MAX_DIGITS = 12       # else E_PARSE
MAX_ABS_VALUE = 10**12        # any intermediate/result, else E_MAGNITUDE

# --- §1.1: canonical integer wire form -------------------------------------

CANONICAL_INT_RE = re.compile(r"-?[1-9][0-9]*\Z|0\Z")
_LEADING_ZERO_RE = re.compile(r"-?0[0-9]+\Z")

# §1.13: echo/collision integer-token boundaries (frozen regex).
INTEGER_TOKEN_RE = re.compile(r"(?<![\w-])-?(0|[1-9][0-9]*)(?![\w])")


def classify_integer_text(text: str) -> str | None:
    """Return None if `text` is a canonical integer, else the rejection code.

    Digits with a leading zero (`0012`, `-07`) are E_NONCANONICAL_INT; any
    other malformed token (`+5`, `5.0`, `1,000`, inner whitespace) is E_PARSE.
    """
    if CANONICAL_INT_RE.fullmatch(text):
        return None
    if _LEADING_ZERO_RE.fullmatch(text):
        return "E_NONCANONICAL_INT"
    return "E_PARSE"


def parse_canonical_int(text: str) -> int:
    """Parse a canonical integer or raise ValueError (callers map to codes)."""
    code = classify_integer_text(text)
    if code is not None:
        raise ValueError(code)
    return int(text)


def canonical_int_str(value: int) -> str:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InfrastructureError(f"non-integer wire value: {value!r}")
    return str(value)


def is_utf8_encodable(text: str) -> bool:
    """False for strings Python accepts but UTF-8 cannot represent — lone
    surrogates such as `\\ud800`.

    Model output reaches us as arbitrary text and is later encoded for
    requests, traces, and cache keys. A non-encodable string is malformed
    output, not a world failure: callers turn it into a typed rejection or
    a schema error so it can never abort a rollout group.
    """
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# --- §1.2: handles ----------------------------------------------------------

HANDLE_RE = re.compile(r"R-[0-9][A-Z][0-9]\Z")


def is_handle(text: str) -> bool:
    return bool(HANDLE_RE.fullmatch(text))


# --- §1.2: resource kinds ---------------------------------------------------

# Operand identifier convention (D9): names `a, b, c` then optionally `d`
# (ratio) or `m` (modular), in order.
_ALLOWED_OPERAND_NAME_TUPLES = (
    ("a", "b", "c"), ("a", "b", "c", "d"), ("a", "b", "c", "m"),
)


@dataclass(frozen=True)
class IntegerRecord:
    """`integer_record`, layout `keyed` or `operands` (§1.2).

    keyed payload:    ((entity, ((field, value), ...)), ...) — stored order.
    operands payload: ((name, value), ...) — names per D9.
    """

    layout: Literal["keyed", "operands"]
    payload: tuple[tuple[str, Any], ...]

    kind = "integer_record"

    def __post_init__(self) -> None:
        if self.layout == "keyed":
            # §1.2 specifies an ordered entities x ordered fields grid.
            # Duplicate names or a ragged grid would make `lookup` depend
            # on first-match order instead of the specified structure.
            if not self.payload:
                raise ValueError("keyed record must be non-empty")
            entities = [entity for entity, _ in self.payload]
            if len(set(entities)) != len(entities):
                raise ValueError("duplicate entity names in keyed record")
            schema: tuple[str, ...] | None = None
            values: list[int] = []
            for entity, fields in self.payload:
                _check_name(entity)
                if not fields:
                    raise ValueError(f"entity {entity!r} has no fields")
                names = tuple(name for name, _ in fields)
                if len(set(names)) != len(names):
                    raise ValueError(
                        f"duplicate field names for entity {entity!r}")
                if schema is None:
                    schema = names
                elif names != schema:
                    raise ValueError(
                        "keyed record is not rectangular: entity "
                        f"{entity!r} has fields {names}, expected {schema}")
                for field, value in fields:
                    _check_name(field)
                    _check_int(value)
                    values.append(value)
            if len(set(values)) != len(values):
                raise ValueError("keyed values must be pairwise distinct (D3)")
        elif self.layout == "operands":
            names = tuple(name for name, _ in self.payload)
            if names not in _ALLOWED_OPERAND_NAME_TUPLES:
                raise ValueError(f"operand names {names} violate D9")
            for _, value in self.payload:
                _check_int(value)
        else:
            raise ValueError(f"unknown layout {self.layout!r}")

    def operand(self, name: str) -> int | None:
        for entry_name, value in self.payload:
            if entry_name == name:
                return value
        return None

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "layout": self.layout,
            "payload": _to_lists(self.payload),
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "IntegerRecord":
        if obj.get("kind") != cls.kind:
            raise ValueError(f"kind mismatch: {obj.get('kind')!r}")
        return cls(layout=obj["layout"], payload=_to_tuples(obj["payload"]))

    def payload_text(self, handle: str) -> str:
        """Worker-facing payload text (§1.2): frozen byte form."""
        lines = [f"{handle}:"]
        if self.layout == "keyed":
            for entity, fields in self.payload:
                for field, value in fields:
                    lines.append(f"{entity}.{field} = {canonical_int_str(value)}")
        else:
            for name, value in self.payload:
                lines.append(f"{name} = {canonical_int_str(value)}")
        return "\n".join(lines)


@dataclass(frozen=True)
class IntegerList:
    """`integer_list` (§1.2): ordered ints, bound by Code `resource` only."""

    payload: tuple[int, ...]

    kind = "integer_list"

    def __post_init__(self) -> None:
        for value in self.payload:
            _check_int(value)

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "payload": list(self.payload)}

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "IntegerList":
        if obj.get("kind") != cls.kind:
            raise ValueError(f"kind mismatch: {obj.get('kind')!r}")
        return cls(payload=tuple(obj["payload"]))

    def payload_text(self, handle: str) -> str:
        body = ", ".join(canonical_int_str(v) for v in self.payload)
        return f"{handle}:\n[{body}]"


Resource = IntegerRecord | IntegerList


def resource_from_json(obj: dict[str, Any]) -> Resource:
    kind = obj.get("kind")
    if kind == "integer_record":
        return IntegerRecord.from_json(obj)
    if kind == "integer_list":
        return IntegerList.from_json(obj)
    raise ValueError(f"unknown resource kind {kind!r}")


def _check_int(value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"payload value must be int, got {value!r}")


_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*\Z")


def _check_name(text: Any) -> None:
    if not isinstance(text, str) or not _NAME_RE.fullmatch(text):
        raise ValueError(f"invalid entity/field name {text!r}")


def _to_lists(obj: Any) -> Any:
    return [_to_lists(x) for x in obj] if isinstance(obj, tuple) else obj


def _to_tuples(obj: Any) -> Any:
    return tuple(_to_tuples(x) for x in obj) if isinstance(obj, list) else obj


# --- §1.3: normative per-operation IR schemas -------------------------------

# Slot kinds: which typed argument reference each op slot admits, plus the
# literal's JSON type where the slot is a `lit`.
LIT_INT, LIT_STR, LIT_SIGN = "lit_int", "lit_str", "lit_sign"
REF_NODE, REF_OPERAND = "node", "operand"
RES_KEYED, RES_LIST = "res_keyed", "res_list"

OP_SCHEMAS: dict[str, dict[str, str]] = {
    "lookup":         {"handle": RES_KEYED, "key": LIT_STR, "field": LIT_STR},
    "affine":         {"x": REF_NODE, "p": LIT_INT, "sign": LIT_SIGN, "q": LIT_INT},
    "mul_add":        {"a": REF_OPERAND, "b": REF_OPERAND, "c": REF_OPERAND},
    "ratio":          {"a": REF_OPERAND, "b": REF_OPERAND, "c": REF_OPERAND, "d": REF_OPERAND},
    "modular":        {"a": REF_OPERAND, "b": REF_OPERAND, "c": REF_OPERAND, "m": REF_OPERAND},
    "product_affine": {"x": REF_NODE, "y": REF_NODE, "q": LIT_INT},
    "seq_count":      {"xs": RES_LIST, "t": LIT_INT},
    "seq_select":     {"xs": RES_LIST, "k": LIT_INT, "i": LIT_INT},
    "seq_at":         {"xs": RES_LIST, "i": REF_NODE},
}

# Ops whose argument slots must reference the operand of the same name
# (slot `a` -> operand "a", ...) — a mismatch is an IR validity error (§1.3).
OPERAND_NAME_MATCHED_OPS = frozenset({"ratio", "modular", "mul_add"})


# --- §1.7: WorkerResult -----------------------------------------------------

WorkerStatus = Literal["success", "typed_failure", "dependency_blocked"]
WORKER_STATUSES = frozenset({"success", "typed_failure",
                             "dependency_blocked"})


@dataclass(frozen=True)
class WorkerResult:
    """§1.7 union; invariants enforced, truth-table rows built in contract.py."""

    status: WorkerStatus
    value: int | None
    rejection_code: str | None
    artifact_valid: bool
    tool_executed: bool
    synthetic: bool

    def __post_init__(self) -> None:
        if self.status not in WORKER_STATUSES:
            raise InfrastructureError(f"unknown status {self.status!r}")
        for name in ("artifact_valid", "tool_executed", "synthetic"):
            if not isinstance(getattr(self, name), bool):
                raise InfrastructureError(f"{name} must be a bool")
        # `bool` subclasses `int`, so an unguarded True would compare equal
        # to gold answer 1 and score as correct.
        if isinstance(self.value, bool):
            raise InfrastructureError("value must be an int, not a bool")
        if (self.status == "success") != isinstance(self.value, int):
            raise InfrastructureError("value must be int iff status=success")
        if (self.status == "typed_failure") != (self.rejection_code is not None):
            raise InfrastructureError("rejection_code set iff typed_failure")
        if self.rejection_code is not None and self.rejection_code not in REJECTION_CODES:
            raise InfrastructureError(f"unknown code {self.rejection_code!r}")
        if self.status == "dependency_blocked" and (
            self.artifact_valid or self.tool_executed or self.synthetic
        ):
            raise InfrastructureError("dependency_blocked flags must be false")
        if self.synthetic and (self.artifact_valid or self.tool_executed):
            raise InfrastructureError("pseudo-worker rows are false/false/true")
        # §1.7 truth table: a tool can only have executed on a valid
        # artifact, and a real (non-synthetic) success must have executed.
        if self.tool_executed and not self.artifact_valid:
            raise InfrastructureError(
                "tool_executed requires artifact_valid (§1.7 truth table)")
        if self.status == "success" and not self.synthetic and not (
                self.artifact_valid and self.tool_executed):
            raise InfrastructureError(
                "endpoint success is artifact_valid + tool_executed")
        if self.status == "typed_failure" and not self.synthetic:
            syntax = self.rejection_code in SYNTAX_REJECTION_CODES
            if syntax and (self.artifact_valid or self.tool_executed):
                raise InfrastructureError(
                    f"{self.rejection_code} is an envelope/grammar failure: "
                    f"flags must be false/false")
            if not syntax and not (self.artifact_valid and self.tool_executed):
                raise InfrastructureError(
                    f"{self.rejection_code} is a semantic tool rejection: "
                    f"flags must be true/true")


# §1.5/§1.8: frozen endpoint indices == opaque routing worker ids.
ENDPOINT_LOOKUP, ENDPOINT_MATH, ENDPOINT_CODE = 0, 1, 2
ENDPOINT_IDS = (ENDPOINT_LOOKUP, ENDPOINT_MATH, ENDPOINT_CODE)
ENDPOINT_NAMES = {0: "lookup", 1: "math", 2: "code"}

CELL_IDS = (
    "lookup_atomic", "math_atomic", "code_atomic",
    "lookup_math", "math_code", "fork_join",
)

# §1.8: node-id -> workflow shape per cell (stable node order n1, n2, n3).
CELL_NODES: dict[str, tuple[str, ...]] = {
    "lookup_atomic": ("n1",),
    "math_atomic": ("n1",),
    "code_atomic": ("n1",),
    "lookup_math": ("n1", "n2"),
    "math_code": ("n1", "n2"),
    "fork_join": ("n1", "n2", "n3"),
}

# §1.9/§3: the fixed directed dependency edges an intervention may target.
# Direction matters — an intervention overrides a parent and measures the
# effect on its child — so a reversed pair, a self-edge, or a fork sibling
# pair is not an intervention edge at all.
CELL_INTERVENTION_EDGES: dict[str, tuple[tuple[str, str], ...]] = {
    "lookup_atomic": (), "math_atomic": (), "code_atomic": (),
    "lookup_math": (("n1", "n2"),),
    "math_code": (("n1", "n2"),),
    "fork_join": (("n1", "n3"), ("n2", "n3")),
}

# Plan contract 2: legal v0 access patterns by step count.
LEGAL_ACCESS_PATTERNS = {
    1: ("none",),
    2: ("none", "all"),
    3: ("none", "none", "all"),
}

# --- §1.4/§4: the structural public/private rendering boundary -------------

# Exactly the parameters a renderer or reference subtask may read: handles
# and public parameters. Private operand values (a, b, c, d, m), the target
# lookup value, and private-derived quantities (U) are absent by
# construction, so no renderer can read them even by mistake — the
# no-leakage guarantee is the type, not a scan of the rendered output.
PUBLIC_PARAM_KEYS: dict[str, tuple[str, ...]] = {
    "lookup_atomic": ("H", "key", "field"),
    "math_atomic": ("H", "template"),
    "code_atomic_count": ("H", "shape", "t"),
    "code_atomic_select": ("H", "shape", "k", "i"),
    "lookup_math": ("H", "key", "field", "p", "q", "sign"),
    "math_code": ("H1", "H2"),
    "fork_join": ("H1", "H2", "key", "field", "t", "q", "branch_order"),
}


# §1.16: the public *semantic* parameters whose values may coincide with a
# node value (the collision family), keyed like PUBLIC_PARAM_KEYS. A subset
# of the public parameters: handles and categorical labels are excluded.
PUBLIC_NUMERIC_PARAMS: dict[str, tuple[str, ...]] = {
    "lookup_atomic": (), "math_atomic": (), "math_code": (),
    "code_atomic_count": ("t",), "code_atomic_select": ("k", "i"),
    "lookup_math": ("p", "q"), "fork_join": ("t", "q"),
}


def public_param_keys(cell_id: str, params: Mapping[str, Any]
                      ) -> tuple[str, ...]:
    if cell_id not in CELL_IDS:
        raise InfrastructureError(f"unknown cell_id {cell_id!r}")
    if cell_id == "code_atomic":
        shape = params.get("shape") if isinstance(params, Mapping) else None
        if shape not in ("count", "select"):
            raise InfrastructureError(
                f"code_atomic public params need a valid shape, got {shape!r}")
        return PUBLIC_PARAM_KEYS[f"code_atomic_{shape}"]
    return PUBLIC_PARAM_KEYS[cell_id]


def _pv_handle(cell_id: str, key: str, value: Any) -> None:
    if not isinstance(value, str) or not is_handle(value):
        raise InfrastructureError(
            f"{cell_id}.{key}: expected a resource handle, got {value!r}")


def _pv_name(cell_id: str, key: str, value: Any) -> None:
    if not isinstance(value, str) or not _NAME_RE.fullmatch(value):
        raise InfrastructureError(
            f"{cell_id}.{key}: expected an entity/field name, got {value!r}")


def _pv_enum(*allowed: str):
    def check(cell_id: str, key: str, value: Any) -> None:
        if value not in allowed:
            raise InfrastructureError(
                f"{cell_id}.{key}: expected one of {allowed}, got {value!r}")
    return check


def _pv_numeric(cell_id: str, key: str, value: Any) -> None:
    # `type(...) is int` rather than isinstance: bool subclasses int, and
    # `p=True` would render as "True" in a prompt.
    if type(value) is not int or not 0 <= value <= 999_999_999_999:
        raise InfrastructureError(
            f"{cell_id}.{key}: expected a nonnegative 12-digit-bounded "
            f"integer, got {value!r}")


_PUBLIC_VALUE_VALIDATORS = {
    "H": _pv_handle, "H1": _pv_handle, "H2": _pv_handle,
    "key": _pv_name, "field": _pv_name,
    "template": _pv_enum("T1", "T2", "T3"),
    "shape": _pv_enum("count", "select"),
    "sign": _pv_enum("+", "-"),
    "branch_order": _pv_enum("lookup_first", "code_first"),
    "p": _pv_numeric, "q": _pv_numeric, "t": _pv_numeric,
    "k": _pv_numeric, "i": _pv_numeric,
}


class PublicParams(Mapping):
    """A genuinely immutable projection holding *only* a cell's public
    parameters.

    Constructed solely by `public_projection`; renderers accept this type
    and reject a raw dict, so private generator state cannot reach a
    template even accidentally. Immutability is real rather than
    documented: the backing mapping is a read-only proxy and attribute
    rebinding is blocked, because mutating a projection would change
    rendered bytes without changing the latent identity that those bytes
    are supposed to be pinned to.
    """

    __slots__ = ("_cell_id", "_values")

    def __init__(self, cell_id: str, values: Mapping[str, Any]) -> None:
        # One-shot: re-running __init__ on a live instance would swap the
        # backing mapping despite the immutability guarantee.
        if hasattr(self, "_values"):
            raise InfrastructureError("PublicParams is already initialised")
        expected = set(public_param_keys(cell_id, values))
        if set(values) != expected:
            raise InfrastructureError(
                f"{cell_id}: public projection keys {sorted(values)} != "
                f"{sorted(expected)}")
        # Values are type-checked, not merely present: an unvalidated
        # mapping could carry `p=True` (a bool that renders as "True") or a
        # mutable list whose later mutation would change rendered bytes
        # while the projection's identity stayed the same.
        for key, value in values.items():
            _PUBLIC_VALUE_VALIDATORS[key](cell_id, key, value)
        object.__setattr__(self, "_cell_id", cell_id)
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __setattr__(self, name: str, value: Any) -> None:
        raise InfrastructureError("PublicParams is immutable")

    def __delattr__(self, name: str) -> None:
        raise InfrastructureError("PublicParams is immutable")

    @property
    def cell_id(self) -> str:
        return self._cell_id

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __hash__(self) -> int:
        return hash((self._cell_id, tuple(sorted(self._values.items()))))

    def __repr__(self) -> str:
        return f"PublicParams({self._cell_id}, {dict(self._values)!r})"

    def __deepcopy__(self, memo: dict) -> "PublicParams":
        # Genuinely immutable, and the backing proxy is unpicklable, so a
        # deep copy is the object itself.
        return self

    def __reduce__(self):
        return (PublicParams, (self._cell_id, dict(self._values)))

    def to_json(self) -> dict[str, Any]:
        """Explicit persistence form — Stage 1 is resumable, so these
        objects are round-tripped rather than generically serialized."""
        return {"cell_id": self._cell_id, "values": dict(self._values)}

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "PublicParams":
        if not isinstance(obj, Mapping) or set(obj) != {"cell_id", "values"}:
            raise InfrastructureError(
                "PublicParams JSON must have exactly cell_id and values")
        cell_id, values = obj["cell_id"], obj["values"]
        if cell_id not in CELL_IDS:
            raise InfrastructureError(f"unknown cell_id {cell_id!r}")
        if not isinstance(values, Mapping):
            raise InfrastructureError("values must be an object")
        return cls(cell_id, dict(values))

    def numeric_features(self) -> dict[str, int]:
        """The §1.16 public *semantic* parameters, derived here rather than
        supplied by a caller — so a control record cannot be handed extra
        or private-derived p/q/t/k/i values."""
        keys = PUBLIC_NUMERIC_PARAMS[
            f"code_atomic_{self['shape']}" if self._cell_id == "code_atomic"
            else self._cell_id]
        return {name: self._values[name] for name in keys}


def public_projection(cell_id: str, params: Mapping[str, Any]) -> PublicParams:
    """Project full generator parameters onto the public rendering record."""
    keys = public_param_keys(cell_id, params)
    missing = [k for k in keys if k not in params]
    if missing:
        raise InfrastructureError(f"{cell_id}: missing public params {missing}")
    return PublicParams(cell_id, {k: params[k] for k in keys})


def require_public(params: Any, cell_id: str | None = None) -> PublicParams:
    """Guard for renderer entry points: a raw mapping is never accepted."""
    if not isinstance(params, PublicParams):
        raise InfrastructureError(
            "renderers require a PublicParams projection, not raw generator "
            f"parameters (got {type(params).__name__})")
    if cell_id is not None and params.cell_id != cell_id:
        raise InfrastructureError(
            f"public params are for {params.cell_id}, not {cell_id}")
    return params


# §1.17: frozen name pools.
ENTITY_POOL = (
    "Aster", "Birch", "Cedar", "Elm", "Fern", "Grove", "Hazel", "Ivory",
    "Juniper", "Lark", "Maple", "Nettle", "Onyx", "Pine", "Quill", "Rowan",
    "Slate", "Tarn", "Vale", "Wren",
)
FIELD_POOL = (
    "crates", "units", "tokens", "points", "seats", "kits", "spools",
    "tiles", "flasks", "reams",
)

# §1.13: namespaces are disjoint generation universes.
NAMESPACES = ("construction", "qualification", "train", "dev", "test",
              # D1 erratum (88_f): dedicated worker-development
              # universe — adaptive inspection permitted, permanently
              # barred from screens/estimates.
              "worker_dev")

# §1.4: renderer ids; `resource_first` is canonical.
RENDERER_IDS = ("resource_first", "goal_first", "bound_var")

VISIBILITY_CONDITIONS = ("private", "visible")


# --- §1.13 identity grammar (formatting and parsing in one place) ----------
#
# latent_program_id  = "{cell_id}:{namespace}:{index:05d}:{hex8}"
# render_instance_id = latent_program_id + ":{renderer_id}:{visibility}"
#
# Parsing matters as much as formatting: an id carries the cell, split and
# visibility of the thing it names, so boundaries can check that a payoff
# surface or an observation really belongs to the population it claims.

_HEX8_RE = re.compile(r"[0-9a-f]{8}\Z")
_INDEX_RE = re.compile(r"[0-9]{5}\Z")


@dataclass(frozen=True)
class LatentId:
    cell_id: str
    namespace: str
    latent_index: int
    hex8: str


@dataclass(frozen=True)
class RenderId:
    latent: LatentId
    latent_program_id: str
    renderer_id: str
    visibility_condition: str


def format_latent_program_id(cell_id: str, namespace: str,
                             latent_index: int, hex8: str) -> str:
    return f"{cell_id}:{namespace}:{latent_index:05d}:{hex8}"


def format_render_instance_id(latent_program_id: str, renderer_id: str,
                              visibility_condition: str) -> str:
    return f"{latent_program_id}:{renderer_id}:{visibility_condition}"


def parse_latent_program_id(value: Any) -> LatentId:
    if not isinstance(value, str):
        raise ValueError(f"latent_program_id must be a str, got {value!r}")
    parts = value.split(":")
    if len(parts) != 4:
        raise ValueError(f"malformed latent_program_id {value!r}")
    cell_id, namespace, index, hex8 = parts
    if cell_id not in CELL_IDS:
        raise ValueError(f"unknown cell_id in {value!r}")
    if namespace not in NAMESPACES:
        raise ValueError(f"unknown namespace in {value!r}")
    if not _INDEX_RE.fullmatch(index):
        raise ValueError(f"malformed latent index in {value!r}")
    if not _HEX8_RE.fullmatch(hex8):
        raise ValueError(f"malformed hex8 in {value!r}")
    return LatentId(cell_id, namespace, int(index), hex8)


def parse_render_instance_id(value: Any) -> RenderId:
    if not isinstance(value, str):
        raise ValueError(f"render_instance_id must be a str, got {value!r}")
    parts = value.split(":")
    if len(parts) != 6:
        raise ValueError(f"malformed render_instance_id {value!r}")
    latent_program_id = ":".join(parts[:4])
    latent = parse_latent_program_id(latent_program_id)
    renderer_id, visibility = parts[4], parts[5]
    if renderer_id not in RENDERER_IDS:
        raise ValueError(f"unknown renderer_id in {value!r}")
    if visibility not in VISIBILITY_CONDITIONS:
        raise ValueError(f"unknown visibility_condition in {value!r}")
    return RenderId(latent, latent_program_id, renderer_id, visibility)
