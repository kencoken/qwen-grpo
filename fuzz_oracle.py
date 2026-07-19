"""Independent recursive AST evaluator for random valid-AST fuzzing (§4).

Test-suite-only oracle: builds random ASTs in the three endpoint grammars,
renders them to artifact text, and evaluates them by direct recursion —
sharing no code with `tasks.conductor.tools` or `tasks.conductor.program`.
Returns (text, expected) where expected is an int or a rejection code.
"""

from __future__ import annotations

import random

MAX_ABS = 10**12


class Reject(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _c(v: int) -> int:
    if abs(v) > MAX_ABS:
        raise Reject("E_MAGNITUDE")
    return v


# --- Math -------------------------------------------------------------------

def gen_math(rng: random.Random, operands: dict[str, int],
             steps: dict[int, int], depth: int = 0) -> tuple[str, object]:
    roll = rng.random()
    if depth >= 3 or roll < 0.4:
        choice = rng.random()
        if choice < 0.5 or (not operands and not steps):
            v = rng.randint(0, 999)
            return str(v), v
        if operands and (choice < 0.8 or not steps):
            name = rng.choice(sorted(operands))
            return name, operands[name]
        k = rng.choice(sorted(steps))
        return f"step_{k}", steps[k]
    op = rng.choice("+-*/%")
    lt, lv = gen_math(rng, operands, steps, depth + 1)
    rt, rv = gen_math(rng, operands, steps, depth + 1)
    text = f"({lt} {op} {rt})"
    if isinstance(lv, str):
        return text, lv
    if isinstance(rv, str):
        return text, rv
    try:
        if op == "+":
            return text, _c(lv + rv)
        if op == "-":
            return text, _c(lv - rv)
        if op == "*":
            return text, _c(lv * rv)
        if op == "/":
            if rv == 0:
                raise Reject("E_DIV_ZERO")
            if lv % rv != 0:
                raise Reject("E_INEXACT_DIV")
            return text, _c(lv // rv)
        if rv == 0:
            raise Reject("E_DIV_ZERO")
        if rv < 0:
            raise Reject("E_BAD_ARG")
        return text, _c(lv % rv)
    except Reject as rej:
        return text, rej.code


# --- Code -------------------------------------------------------------------

def _unique(xs: list[int]) -> list[int]:
    out: list[int] = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def gen_code_seq(rng: random.Random, base: list[int],
                 steps: dict[int, int], depth: int = 0
                 ) -> tuple[str, object]:
    if depth >= 3 or rng.random() < 0.4:
        return "resource", list(base)
    if rng.random() < 0.5:
        t, v = gen_code_seq(rng, base, steps, depth + 1)
        text = f"stable_unique({t})"
        return text, v if isinstance(v, str) else _unique(v)
    t, v = gen_code_seq(rng, base, steps, depth + 1)
    at_text, arg = _int_arg(rng, steps)
    text = f"rotate_left({t}, {at_text})"
    if isinstance(v, str):
        return text, v
    if arg < 0:
        return text, "E_BAD_ARG"
    if not v:
        return text, []
    k = arg % len(v)
    return text, v[k:] + v[:k]


def _int_arg(rng: random.Random, steps: dict[int, int]) -> tuple[str, int]:
    if steps and rng.random() < 0.4:
        k = rng.choice(sorted(steps))
        return f"step_{k}", steps[k]
    v = rng.randint(0, 20)
    return str(v), v


def gen_code(rng: random.Random, base: list[int],
             steps: dict[int, int]) -> tuple[str, object]:
    seq_text, seq_val = gen_code_seq(rng, base, steps)
    arg_text, arg = _int_arg(rng, steps)
    if rng.random() < 0.5:
        text = f"count_gt({seq_text}, {arg_text})"
        if isinstance(seq_val, str):
            return text, seq_val
        return text, len([x for x in seq_val if x > arg])
    text = f"at({seq_text}, {arg_text})"
    if isinstance(seq_val, str):
        return text, seq_val
    if arg < 0 or arg >= len(seq_val):
        return text, "E_INDEX_RANGE"
    return text, seq_val[arg]


# --- Lookup -----------------------------------------------------------------

def gen_lookup(rng: random.Random,
               record: list[tuple[str, list[tuple[str, int]]]]
               ) -> tuple[str, object]:
    keys = [e for e, _ in record]
    fields = sorted({f for _, fs in record for f, _ in fs})
    key = rng.choice(keys + ["Zed"])
    fld = rng.choice(fields + ["ghosts"])
    text = f'lookup(resource, "{key}", "{fld}")'
    for entity, fs in record:
        if entity == key:
            for fname, value in fs:
                if fname == fld:
                    return text, value
            return text, "E_UNKNOWN_FIELD"
    return text, "E_UNKNOWN_KEY"
