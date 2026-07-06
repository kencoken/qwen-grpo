"""Tests for the shared reward machinery (format contract + parsing helpers).
Task-specific verifier tests live in test_<task>.py. Run `uv run pytest`
before any GPU time: a verifier bug means every subsequent GPU-hour
optimizes the wrong thing."""

import pytest

from rewards import (
    FORMAT_REWARD,
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


# --- format reward -------------------------------------------------------------

def test_format_reward_values():
    assert format_reward([GOOD, "nope"]) == [FORMAT_REWARD, 0.0]


def test_format_reward_handles_chat_completions():
    chat = [{"role": "assistant", "content": GOOD}]
    assert format_reward([chat]) == [FORMAT_REWARD]
