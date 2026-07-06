"""Countdown verifier tests. The verifier is a tiny expression interpreter —
exactly the kind of code that silently rewards garbage if untested."""

import random

from tasks.countdown import _make_problem, load_train, verify


def wrap(expr):
    return f"<think>searching...</think>\n<answer>\n{expr}\n</answer>"


# --- accepts ------------------------------------------------------------------

def test_simple_expression():
    assert verify(wrap("(3 + 5) * 7"), numbers=[3, 5, 7], target=56)


def test_nested_parens():
    assert verify(wrap("((8 - 2) * 4) / 3"), numbers=[8, 2, 4, 3], target=8)


def test_non_integer_intermediate():
    # 7/2 = 3.5 exactly via Fractions; * 4 lands back on an integer
    assert verify(wrap("7 / 2 * 4"), numbers=[7, 2, 4], target=14)


def test_unary_minus_allowed():
    assert verify(wrap("-3 + 8"), numbers=[3, 8], target=5)


def test_order_of_numbers_irrelevant():
    assert verify(wrap("5 * (7 - 3)"), numbers=[3, 5, 7], target=20)


# --- rejects ------------------------------------------------------------------

def test_wrong_value():
    assert not verify(wrap("(3 + 5) * 7"), numbers=[3, 5, 7], target=55)


def test_number_unused():
    assert not verify(wrap("3 * 7"), numbers=[3, 5, 7], target=21)


def test_number_reused():
    assert not verify(wrap("3 * 3 + 5"), numbers=[3, 5, 7], target=14)


def test_foreign_number():
    assert not verify(wrap("3 * 5 + 9"), numbers=[3, 5, 7], target=24)


def test_division_by_zero():
    assert not verify(wrap("3 / (5 - 5)"), numbers=[3, 5, 5], target=1)


def test_pow_rejected():
    assert not verify(wrap("3 ** 5"), numbers=[3, 5], target=243)


def test_names_rejected():
    assert not verify(wrap("__import__('os').getpid()"), numbers=[3, 5], target=8)
    assert not verify(wrap("x + y"), numbers=[3, 5], target=8)


def test_float_literals_rejected():
    assert not verify(wrap("1.5 * 2"), numbers=[1, 5, 2], target=3)


def test_malformed():
    assert not verify(wrap("3 +"), numbers=[3, 5], target=8)       # syntax error
    assert not verify(wrap(""), numbers=[3, 5], target=8)          # empty
    assert not verify("<think>no answer</think>", numbers=[3, 5], target=8)


# --- generator ↔ verifier consistency ------------------------------------------

def test_generated_solutions_verify():
    """Property test: the generator's own solution expression must always
    pass the verifier — 40 random problems across the difficulty dial."""
    rng = random.Random(123)
    for num_numbers in (3, 4, 5, 6):
        for _ in range(10):
            numbers, target, expr = _make_problem(rng, num_numbers)
            assert verify(wrap(expr), numbers=numbers, target=target), (
                numbers, target, expr)


def test_generator_determinism_and_shape():
    a = load_train(6, num_numbers=4, seed=7)
    b = load_train(6, num_numbers=4, seed=7)
    c = load_train(6, num_numbers=4, seed=8)
    assert a["target"] == b["target"] and a["target"] != c["target"]
    assert all(len(ns) == 4 for ns in a["numbers"])
    assert all(1 <= t <= 999 for t in a["target"])
