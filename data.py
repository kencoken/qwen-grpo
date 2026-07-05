"""GSM8K task module: turns raw problems into (prompt, answer) pairs.

This file is the swap point for other tasks. A task is just a function that
returns a datasets.Dataset with two columns:
  prompt   chat messages (TRL applies the tokenizer's chat template)
  answer   gold answer string — TRL forwards extra columns to reward funcs
Stage 2 additions live here: Countdown (synthetic generator instead of
load_dataset), MATH500 (needs math_verify in rewards.py), and the base-model
R1-Zero arm (replace the chat messages with a single raw-text prompt string —
TRL treats string prompts as plain completion, no chat template).
"""

import json
import sys

from datasets import load_dataset

from rewards import normalize_number

# The format contract. Kept terse: every token of system prompt is prepended
# to all ~2400 rollouts of a run. The example matters more than the prose —
# instruct models imitate shape better than they follow instructions.
SYSTEM_PROMPT = (
    "Solve the math problem. Think step by step between <think> and </think>, "
    "then give only the final number between <answer> and </answer>.\n"
    "Respond exactly in this format:\n"
    "<think>\n...\n</think>\n<answer>\n42\n</answer>"
)

FILTERED_PATH = "data/gsm8k_filtered.json"


def gold_answer(solution):
    """GSM8K solutions end with '#### <answer>'. Normalize so the reward
    comparison is canonical-vs-canonical ('1,234' -> '1234')."""
    return normalize_number(solution.split("####")[-1])


def _to_example(row):
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": row["question"]},
        ],
        "answer": gold_answer(row["answer"]),
    }


def load_gsm8k(split="train", n=None):
    """First n problems of GSM8K as (prompt, answer). ~7.5k train / 1.3k test."""
    ds = load_dataset("openai/gsm8k", "main", split=split)
    if n is not None:
        ds = ds.select(range(min(n, len(ds))))
    return ds.map(_to_example, remove_columns=ds.column_names)


def load_gsm8k_filtered(n=None, path=FILTERED_PATH):
    """The difficulty-filtered training set: problems where the base model's
    pass rate is strictly between 0 and 1 (see filter_data.py). All-fail and
    all-pass problems give every rollout in a group the same reward -> zero
    advantage -> zero gradient; training on them is pure waste."""
    try:
        with open(path) as f:
            indices = json.load(f)["kept_indices"]
    except FileNotFoundError:
        print(
            f"WARNING: {path} not found (run filter_data.py first) — "
            "falling back to unfiltered GSM8K.",
            file=sys.stderr,
        )
        return load_gsm8k("train", n)
    if n is not None:
        indices = indices[:n]
    ds = load_dataset("openai/gsm8k", "main", split="train").select(indices)
    return ds.map(_to_example, remove_columns=ds.column_names)


if __name__ == "__main__":
    # Eyeball one rendered example: python data.py
    ds = load_gsm8k("train", n=1)
    for message in ds[0]["prompt"]:
        print(f"--- {message['role']} ---\n{message['content']}")
    print(f"--- gold answer ---\n{ds[0]['answer']}")
