"""Unit tests for the verifier. Run `uv run pytest` before any GPU time:
a verifier bug means every subsequent GPU-hour optimizes the wrong thing."""

import pytest

from data import gold_answer
from rewards import (
    FORMAT_REWARD,
    correctness_reward,
    extract_answer,
    format_reward,
    is_formatted,
    normalize_number,
)

GOOD = "<think>2+2=4</think>\n<answer>4</answer>"


# --- answer normalization / extraction ---------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("42", "42"),
        (" 42 ", "42"),
        ("1,000", "1000"),          # the classic silent-zero-signal bug
        ("$1,000.00", "1000"),
        ("72.0", "72"),
        ("72.", "72"),
        ("3.5", "3.5"),
        ("-5", "-5"),
        ("80%", "80"),
        ("72 dollars", "72 dollars"),  # non-numeric stays text -> never matches
    ],
)
def test_normalize_number(raw, expected):
    assert normalize_number(raw) == expected


def test_extract_answer_basic():
    assert extract_answer(GOOD) == "4"


def test_extract_answer_takes_last_block():
    assert extract_answer("<answer>1</answer> no <answer>2</answer>") == "2"


def test_extract_answer_multiline():
    assert extract_answer("<answer>\n 1,234 \n</answer>") == "1234"


def test_extract_answer_missing():
    assert extract_answer("<think>no answer tag</think>") is None


# --- format checking ----------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "ok"),
    [
        (GOOD, True),
        ("<think>\nlong\nreasoning\n</think>\n<answer>\n7\n</answer>", True),
        ("  " + GOOD + "\n", True),                          # surrounding ws ok
        ("<answer>4</answer>", False),                       # missing think
        ("<think>x</think>", False),                         # missing answer
        ("Sure! " + GOOD, False),                            # chatter before
        (GOOD + " Hope that helps!", False),                 # chatter after
        ("<answer>4</answer><think>x</think>", False),       # wrong order
        ("<think>x</think><answer>4</answer><answer>5</answer>", False),  # dup
        ("<think>x<think>y</think></think><answer>4</answer>", False),    # nested
        ("<think>x</think><answer>4", False),                # unclosed
        ("", False),
    ],
)
def test_is_formatted(text, ok):
    assert is_formatted(text) is ok


# --- reward functions ---------------------------------------------------------

def test_format_reward_values():
    assert format_reward([GOOD, "nope"]) == [FORMAT_REWARD, 0.0]


def test_format_reward_handles_chat_completions():
    chat = [{"role": "assistant", "content": GOOD}]
    assert format_reward([chat]) == [FORMAT_REWARD]


def test_correctness_reward_normalizes_both_sides():
    completions = [
        "<think>.</think><answer>$1,000</answer>",  # right, needs normalizing
        "<think>.</think><answer>999</answer>",     # wrong
        "no tags at all",                           # unparseable
    ]
    assert correctness_reward(completions, ["1000", "1,000", "1000"]) == [1.0, 0.0, 0.0]


def test_correctness_reward_logs_metrics():
    logged = {}
    completions = [
        "<think>.</think><answer>4</answer>",
        "<think>.</think><answer>4</answer>",
        "<think>.</think><answer>5</answer>",
        "junk",
    ]
    correctness_reward(
        completions, ["4"] * 4, log_metric=lambda k, v: logged.__setitem__(k, v)
    )
    assert logged["accuracy"] == 0.5
    assert logged["unique_answer_rate"] == 0.75  # {"4", "5", None} of 4


# --- GSM8K gold-answer parsing (data.py) --------------------------------------

def test_gold_answer_parses_gsm8k_solution():
    sol = "She sells 16 - 3 - 4 = <<16-3-4=9>>9 eggs.\n#### 18"
    assert gold_answer(sol) == "18"


def test_gold_answer_strips_commas():
    assert gold_answer("blah blah\n#### 1,234") == "1234"
