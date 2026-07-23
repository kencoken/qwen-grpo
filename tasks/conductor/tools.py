"""Endpoint grammars and tool evaluators — spec §1.6.

Independent implementations of the primitives (never shared with
`program.py`'s reference functions; the 10k reference-vs-tools agreement
command measures their agreement, §1.6). Expected artifact errors surface as
`ToolRejection(code)`; anything else propagates and aborts.

Endpoints: 0 = Lookup (keyed retrieval), 1 = Math (exact calculator),
2 = Code (whitelist sequence interpreter).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from .types import (
    ARTIFACT_MAX_BYTES, AST_MAX_DEPTH, AST_MAX_NODES, LITERAL_MAX_DIGITS,
    MAX_ABS_VALUE, InfrastructureError, IntegerList, IntegerRecord, Resource,
    is_utf8_encodable,
)


class ToolRejection(Exception):
    """Typed rejection (§1.6); takes the contract-4 path (reward 0.5)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Binding:
    """Host-side authorized binding set for one worker call.

    `resources`: the authorized payloads (≤1 per step in v0; the plural
    union is the harness-only B5 exception). `steps`: available predecessor
    values (`step_k`), present iff access = `all`.
    """

    resources: dict[str, Resource] = field(default_factory=dict)
    steps: dict[int, int] = field(default_factory=dict)


def binding_sha256(binding: Binding) -> str:
    """Canonical SHA-256 of one call's authorized inputs (81_f §5.3):
    resources and predecessor values, serialized deterministically. Shared
    by the isolated evaluator and composed executor rows so the two paths
    hash identically. Pure provenance — never affects tool execution."""
    def unroll(value: Any) -> Any:
        if isinstance(value, tuple):
            return [unroll(item) for item in value]
        return value

    def resource_obj(resource: Resource) -> dict[str, Any]:
        obj = {"kind": resource.kind, "payload": unroll(resource.payload)}
        if isinstance(resource, IntegerRecord):
            obj["layout"] = resource.layout
        return obj

    from .profiles import canonical_json
    payload = {
        "resources": {handle: resource_obj(resource)
                      for handle, resource in binding.resources.items()},
        "steps": {str(k): v for k, v in binding.steps.items()},
    }
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")).hexdigest()


# --- tokenizer --------------------------------------------------------------

@dataclass(frozen=True)
class _Tok:
    kind: str  # INT | WORD | STR | SYM
    value: Any


_WORD_RE = re.compile(r"[a-z_][a-z0-9_]*")
_STR_RE = re.compile(r'"([A-Za-z][A-Za-z0-9]*)"')
_SYMBOLS = set("+-*/%(),")
# Artifacts are ASCII (§1.6). Unicode-wide `str.isdigit()`/`str.isspace()`
# would admit characters the grammars cannot represent (Arabic-Indic
# numerals, NBSP) and then fail the ASCII regexes.
_ASCII_DIGITS = set("0123456789")
_ASCII_SPACE = set(" \t\n\r\f\v")


def _tokenize(text: str) -> list[_Tok]:
    tokens: list[_Tok] = []
    pos = 0
    while pos < len(text):
        ch = text[pos]
        if ch in _ASCII_SPACE:
            pos += 1
            continue
        if ch in _SYMBOLS:
            tokens.append(_Tok("SYM", ch))
            pos += 1
            continue
        if ch in _ASCII_DIGITS:
            end = pos
            while end < len(text) and text[end] in _ASCII_DIGITS:
                end += 1
            digits = text[pos:end]
            if len(digits) > LITERAL_MAX_DIGITS:
                raise ToolRejection("E_PARSE")
            if len(digits) > 1 and digits[0] == "0":
                raise ToolRejection("E_NONCANONICAL_INT")
            tokens.append(_Tok("INT", int(digits)))
            pos = end
            continue
        if ch == '"':
            m = _STR_RE.match(text, pos)
            if not m:
                raise ToolRejection("E_PARSE")
            tokens.append(_Tok("STR", m.group(1)))
            pos = m.end()
            continue
        m = _WORD_RE.match(text, pos)
        if m:
            tokens.append(_Tok("WORD", m.group(0)))
            pos = m.end()
            continue
        raise ToolRejection("E_PARSE")
    return tokens


class _TokenStream:
    def __init__(self, tokens: list[_Tok]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> _Tok | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def next(self) -> _Tok:
        tok = self.peek()
        if tok is None:
            raise ToolRejection("E_PARSE")
        self._pos += 1
        return tok

    def expect_sym(self, sym: str) -> None:
        tok = self.next()
        if tok.kind != "SYM" or tok.value != sym:
            raise ToolRejection("E_PARSE")

    def at_end(self) -> bool:
        return self._pos >= len(self._tokens)


_STEP_RE = re.compile(r"step_([1-9])\Z")


# --- AST: tuples ("int", v) ("ident", c) ("step", k) ("bin", op, l, r)
#          ("lookup", key, field) ("resource",) ("call", fn, *args) ---------

def _ast_metrics(node: tuple) -> tuple[int, int]:
    """(node count, depth) over semantic AST nodes."""
    kind = node[0]
    if kind in ("int", "ident", "step", "resource"):
        return 1, 1
    if kind == "lookup":
        return 1, 1
    children = [c for c in node[1:] if isinstance(c, tuple)]
    counts, depths = zip(*(_ast_metrics(c) for c in children))
    return 1 + sum(counts), 1 + max(depths)


def _check_limits(ast: tuple) -> None:
    count, depth = _ast_metrics(ast)
    if count > AST_MAX_NODES or depth > AST_MAX_DEPTH:
        raise ToolRejection("E_DEPTH")


# --- Math grammar -----------------------------------------------------------

def _parse_math(text: str) -> tuple:
    ts = _TokenStream(_tokenize(text))
    ast = _parse_math_expr(ts)
    if not ts.at_end():
        raise ToolRejection("E_PARSE")
    return ast


def _parse_math_expr(ts: _TokenStream) -> tuple:
    node = _parse_math_term(ts)
    while (tok := ts.peek()) and tok.kind == "SYM" and tok.value in "+-":
        ts.next()
        node = ("bin", tok.value, node, _parse_math_term(ts))
    return node


def _parse_math_term(ts: _TokenStream) -> tuple:
    node = _parse_math_factor(ts)
    while (tok := ts.peek()) and tok.kind == "SYM" and tok.value in "*/%":
        ts.next()
        node = ("bin", tok.value, node, _parse_math_factor(ts))
    return node


def _parse_math_factor(ts: _TokenStream) -> tuple:
    tok = ts.next()
    if tok.kind == "INT":
        return ("int", tok.value)
    if tok.kind == "WORD":
        if m := _STEP_RE.fullmatch(tok.value):
            return ("step", int(m.group(1)))
        if len(tok.value) == 1:
            return ("ident", tok.value)
        raise ToolRejection("E_PARSE")
    if tok.kind == "SYM" and tok.value == "(":
        node = _parse_math_expr(ts)
        ts.expect_sym(")")
        return node
    raise ToolRejection("E_PARSE")


# --- Lookup grammar ---------------------------------------------------------

def _parse_lookup(text: str) -> tuple:
    ts = _TokenStream(_tokenize(text))
    tok = ts.next()
    if tok.kind != "WORD" or tok.value != "lookup":
        raise ToolRejection("E_PARSE")
    ts.expect_sym("(")
    tok = ts.next()
    if tok.kind != "WORD" or tok.value != "resource":
        raise ToolRejection("E_PARSE")
    ts.expect_sym(",")
    key = ts.next()
    if key.kind != "STR":
        raise ToolRejection("E_PARSE")
    ts.expect_sym(",")
    fld = ts.next()
    if fld.kind != "STR":
        raise ToolRejection("E_PARSE")
    ts.expect_sym(")")
    if not ts.at_end():
        raise ToolRejection("E_PARSE")
    return ("lookup", key.value, fld.value)


# --- Code grammar -----------------------------------------------------------

def _parse_code(text: str) -> tuple:
    ts = _TokenStream(_tokenize(text))
    ast = _parse_code_int_expr(ts)
    if not ts.at_end():
        raise ToolRejection("E_PARSE")
    return ast


def _parse_code_int_expr(ts: _TokenStream) -> tuple:
    tok = ts.next()
    if tok.kind != "WORD" or tok.value not in ("count_gt", "at"):
        raise ToolRejection("E_PARSE")
    ts.expect_sym("(")
    seq = _parse_code_seq_expr(ts)
    ts.expect_sym(",")
    arg = _parse_code_int_arg(ts)
    ts.expect_sym(")")
    return ("call", tok.value, seq, arg)


def _parse_code_seq_expr(ts: _TokenStream) -> tuple:
    tok = ts.next()
    if tok.kind != "WORD":
        raise ToolRejection("E_PARSE")
    if tok.value == "resource":
        return ("resource",)
    if tok.value == "stable_unique":
        ts.expect_sym("(")
        seq = _parse_code_seq_expr(ts)
        ts.expect_sym(")")
        return ("call", "stable_unique", seq)
    if tok.value == "rotate_left":
        ts.expect_sym("(")
        seq = _parse_code_seq_expr(ts)
        ts.expect_sym(",")
        arg = _parse_code_int_arg(ts)
        ts.expect_sym(")")
        return ("call", "rotate_left", seq, arg)
    raise ToolRejection("E_PARSE")


def _parse_code_int_arg(ts: _TokenStream) -> tuple:
    tok = ts.next()
    if tok.kind == "INT":
        return ("int", tok.value)
    if tok.kind == "WORD" and (m := _STEP_RE.fullmatch(tok.value)):
        return ("step", int(m.group(1)))
    raise ToolRejection("E_PARSE")


# --- demand collection (§1.6 global resource-error procedure) ---------------

def _collect(ast: tuple, idents: set[str], steps: set[int],
             resource: list[bool]) -> None:
    kind = ast[0]
    if kind == "ident":
        idents.add(ast[1])
    elif kind == "step":
        steps.add(ast[1])
    elif kind in ("resource", "lookup"):
        resource.append(True)
    for child in ast[1:]:
        if isinstance(child, tuple):
            _collect(child, idents, steps, resource)


def _select_resource(binding: Binding, compatible) -> Resource:
    """Global conditions 1–2: E_NO_RESOURCE then E_RESOURCE_KIND (§1.6)."""
    if not binding.resources:
        raise ToolRejection("E_NO_RESOURCE")
    matches = [r for r in binding.resources.values() if compatible(r)]
    if not matches:
        raise ToolRejection("E_RESOURCE_KIND")
    if len(matches) > 1:
        raise InfrastructureError(
            "more than one grammar-compatible payload (v0 harness "
            "configuration error, §1.11 B5)")
    return matches[0]


def _chk(v: int) -> int:
    if abs(v) > MAX_ABS_VALUE:
        raise ToolRejection("E_MAGNITUDE")
    return v


# --- independent tool primitives -------------------------------------------

def _tool_stable_unique(xs: list[int]) -> list[int]:
    out: list[int] = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def _tool_rotate_left(xs: list[int], k: int) -> list[int]:
    if k < 0:
        raise ToolRejection("E_BAD_ARG")
    if not xs:
        return []
    k %= len(xs)
    return xs[k:] + xs[:k]


def _tool_at(xs: list[int], i: int) -> int:
    if i < 0 or i >= len(xs):
        raise ToolRejection("E_INDEX_RANGE")
    return xs[i]


def _tool_count_gt(xs: list[int], t: int) -> int:
    return len([x for x in xs if x > t])


# --- evaluation -------------------------------------------------------------

def execute_artifact(endpoint: int, content: str, binding: Binding) -> int:
    """Parse and execute one trimmed artifact body. Returns the integer
    result or raises ToolRejection; unexpected exceptions propagate."""
    if not is_utf8_encodable(content):
        raise ToolRejection("E_PARSE")
    if len(content.encode("utf-8")) > ARTIFACT_MAX_BYTES:
        raise ToolRejection("E_PARSE")
    if endpoint == 0:
        ast = _parse_lookup(content)
    elif endpoint == 1:
        ast = _parse_math(content)
    elif endpoint == 2:
        ast = _parse_code(content)
    else:
        raise InfrastructureError(f"unknown endpoint {endpoint!r}")
    _check_limits(ast)

    idents: set[str] = set()
    step_refs: set[int] = set()
    demands: list[bool] = []
    _collect(ast, idents, step_refs, demands)
    # §1.6: resource-bound symbols are Lookup's/Code's `resource` and Math
    # single-letter identifiers.
    demanded = bool(demands) or bool(idents)

    record: IntegerRecord | None = None
    sequence: list[int] | None = None
    if demanded:
        if endpoint == 0:
            keyed = _select_resource(
                binding, lambda r: isinstance(r, IntegerRecord)
                and r.layout == "keyed")
            assert isinstance(keyed, IntegerRecord)
            record = keyed
        elif endpoint == 1:
            operands = _select_resource(
                binding, lambda r: isinstance(r, IntegerRecord)
                and r.layout == "operands")
            assert isinstance(operands, IntegerRecord)
            record = operands
            # Global condition 3: any required identifier absent.
            for name in sorted(idents):
                if record.operand(name) is None:
                    raise ToolRejection("E_UNKNOWN_IDENT")
        else:
            lst = _select_resource(binding,
                                   lambda r: isinstance(r, IntegerList))
            assert isinstance(lst, IntegerList)
            sequence = list(lst.payload)
    # Global condition 4: any unavailable step reference.
    for k in sorted(step_refs):
        if k not in binding.steps:
            raise ToolRejection("E_UNKNOWN_IDENT")

    if endpoint == 0:
        assert record is not None
        return _chk(_eval_lookup(ast, record))
    if endpoint == 1:
        return _chk(_eval_math(ast, record, binding.steps))
    return _chk(_eval_code_int(ast, sequence, binding.steps))


def _eval_lookup(ast: tuple, record: IntegerRecord) -> int:
    _, key, field_name = ast
    for entity, fields in record.payload:
        if entity == key:
            for fname, value in fields:
                if fname == field_name:
                    return value
            raise ToolRejection("E_UNKNOWN_FIELD")
    raise ToolRejection("E_UNKNOWN_KEY")


def _eval_math(ast: tuple, record: IntegerRecord | None,
               steps: dict[int, int]) -> int:
    kind = ast[0]
    if kind == "int":
        return _chk(ast[1])
    if kind == "step":
        return _chk(steps[ast[1]])
    if kind == "ident":
        assert record is not None  # demand checks ran
        value = record.operand(ast[1])
        assert value is not None
        return _chk(value)
    _, op, left, right = ast
    lv = _eval_math(left, record, steps)
    rv = _eval_math(right, record, steps)
    if op == "+":
        return _chk(lv + rv)
    if op == "-":
        return _chk(lv - rv)
    if op == "*":
        return _chk(lv * rv)
    if op == "/":
        if rv == 0:
            raise ToolRejection("E_DIV_ZERO")
        if lv % rv != 0:
            raise ToolRejection("E_INEXACT_DIV")
        return _chk(lv // rv)
    if op == "%":
        if rv == 0:
            raise ToolRejection("E_DIV_ZERO")
        if rv < 0:
            raise ToolRejection("E_BAD_ARG")
        return _chk(lv % rv)  # floor-mod
    raise InfrastructureError(f"unknown operator {op!r}")


def _eval_code_int(ast: tuple, sequence: list[int] | None,
                   steps: dict[int, int]) -> int:
    _, fn, seq_ast, arg_ast = ast
    xs = _eval_code_seq(seq_ast, sequence, steps)
    arg = _chk(steps[arg_ast[1]] if arg_ast[0] == "step" else arg_ast[1])
    if fn == "count_gt":
        return _tool_count_gt(xs, arg)
    return _tool_at(xs, arg)


def _eval_code_seq(ast: tuple, sequence: list[int] | None,
                   steps: dict[int, int]) -> list[int]:
    if ast[0] == "resource":
        assert sequence is not None  # demand checks ran
        return sequence
    _, fn, *rest = ast
    xs = _eval_code_seq(rest[0], sequence, steps)
    if fn == "stable_unique":
        return _tool_stable_unique(xs)
    arg_ast = rest[1]
    arg = _chk(steps[arg_ast[1]] if arg_ast[0] == "step" else arg_ast[1])
    return _tool_rotate_left(xs, arg)
