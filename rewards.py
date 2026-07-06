"""Shared reward machinery: the <think>/<answer> format contract and the
helpers every task's verifier builds on. Task-specific correctness rewards
live with their tasks (tasks/*.py) — a verifier and its dataset share a
format, so they travel together.

GRPO will optimize whatever the rewards return, including their bugs: a
regex that accepts malformed output teaches the model malformed output.
Hence the test files. Reward scheme (per task, from the exploration plan):
    +0.2  completion is exactly <think>...</think><answer>...</answer>
    +1.0  the task verifier accepts the answer
Absolute magnitudes matter less than they look: GRPO normalizes advantages
within each group, so what counts is the *ordering* of rewards and where
the variance lives. Reward-shaping experiments should use
GRPOConfig(reward_weights=[...]) rather than editing these constants.
"""

import re

FORMAT_REWARD = 0.2
CORRECT_REWARD = 1.0

# One <think> block, then one <answer> block, nothing else (whitespace aside).
# fullmatch + the tag-count check below: regex alone would accept a second
# <answer> block via backtracking (".+?" happily swallows "</answer><answer>").
FORMAT_RE = re.compile(r"\s*<think>.+?</think>\s*<answer>.+?</answer>\s*", re.DOTALL)
ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)


def completion_text(completion):
    """TRL passes completions as plain strings, or — for chat-format datasets
    like ours — as [{"role": "assistant", "content": ...}]. Accept both."""
    if isinstance(completion, list):
        return completion[0]["content"]
    return completion


def answer_block(text):
    """Contents of the last <answer>...</answer> block, or None."""
    matches = ANSWER_RE.findall(text)
    return matches[-1] if matches else None


def normalize_number(text):
    """Canonicalize an answer string for exact-match comparison: '$1,000.00 '
    and '1000' should both become '1000'. Non-numeric text is returned
    stripped/lowercased — it will simply never match a numeric gold answer,
    which is the strictness we want (the model must answer with a number,
    not 'about 72 dollars')."""
    text = text.strip().replace(",", "").replace("$", "").rstrip("%")
    text = text.rstrip(".")  # "72." -> "72"
    try:
        value = float(text)
    except ValueError:
        return text.strip().lower()
    return str(int(value)) if value == int(value) else str(value)


def extract_answer(text):
    """Last answer block, normalized as a number. None if no block."""
    block = answer_block(text)
    return normalize_number(block) if block is not None else None


def is_formatted(text):
    """True iff the completion is exactly one think block then one answer
    block. Deliberately strict: trailing chatter after </answer> fails."""
    return (
        FORMAT_RE.fullmatch(text) is not None
        and text.count("<think>") == 1
        and text.count("<answer>") == 1
    )


def format_reward(completions, **kwargs):
    """+0.2 for exact format compliance, task-independent. On an instruct
    model this is the curve that moves first — it needs no task skill,
    only obedience."""
    return [
        FORMAT_REWARD if is_formatted(completion_text(c)) else 0.0
        for c in completions
    ]
