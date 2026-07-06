"""GSM8K: grade-school word problems with a single numeric answer.

The original Stage-1 task (see experiment_log.md E1) — now retired as a
research object but kept as the regression control. Everything GSM8K lives
here: loading, gold-answer parsing, and the correctness verifier.
"""

import json
import sys

from datasets import load_dataset

from rewards import CORRECT_REWARD, completion_text, extract_answer, normalize_number

# The format contract. Kept terse: every token of system prompt is prepended
# to all rollouts of a run. The example matters more than the prose —
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


def _load(split, n):
    ds = load_dataset("openai/gsm8k", "main", split=split)
    if n is not None:
        ds = ds.select(range(min(n, len(ds))))
    return ds.map(_to_example, remove_columns=ds.column_names)


def load_train(n=None, variant="unfiltered", **_):
    """First n train problems, or the difficulty-filtered subset: problems
    where the base model's pass rate is strictly between 0 and 1 (see
    filter_data.py). All-pass and all-fail problems give every rollout in a
    group the same reward -> zero advantage -> zero gradient."""
    if variant != "filtered":
        return _load("train", n)
    try:
        with open(FILTERED_PATH) as f:
            indices = json.load(f)["kept_indices"]
    except FileNotFoundError:
        print(
            f"WARNING: {FILTERED_PATH} not found (run filter_data.py first) — "
            "falling back to unfiltered GSM8K.",
            file=sys.stderr,
        )
        return _load("train", n)
    if n is not None:
        indices = indices[:n]
    ds = load_dataset("openai/gsm8k", "main", split="train").select(indices)
    return ds.map(_to_example, remove_columns=ds.column_names)


def load_eval(n=None, **_):
    return _load("test", n)


def verify(text, answer, **_):
    """Exact match on normalized numeric answers."""
    return extract_answer(text) == answer


# maj@k votes on the extracted numeric answer (a canonical form exists)
canonical = extract_answer


def correctness_reward(completions, answer, log_metric=None, **kwargs):
    """+1.0 for the exact (normalized) gold answer. `answer` is our dataset
    column, forwarded by TRL. Also emits two custom W&B metrics:
      accuracy            fraction correct in this generation batch
      unique_answer_rate  distinct answers / completions — the collapse
                          detector: drifting toward 1/num_generations means
                          rollouts are becoming copies of each other and
                          within-group variance (hence the gradient) is dying.
    """
    extracted = [extract_answer(completion_text(c)) for c in completions]
    rewards = [
        CORRECT_REWARD if e is not None and e == normalize_number(g) else 0.0
        for e, g in zip(extracted, answer)
    ]
    if log_metric is not None:
        log_metric("accuracy", sum(r > 0 for r in rewards) / len(rewards))
        log_metric("unique_answer_rate", len(set(extracted)) / len(extracted))
    return rewards


if __name__ == "__main__":
    # Eyeball one rendered example: python -m tasks.gsm8k
    ds = load_train(n=1)
    for message in ds[0]["prompt"]:
        print(f"--- {message['role']} ---\n{message['content']}")
    print(f"--- gold answer ---\n{ds[0]['answer']}")
