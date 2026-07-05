"""The verifier: answer extraction and the two GRPO reward functions.

This is the most load-bearing file in the repo. GRPO will optimize whatever
these functions return, including their bugs: a regex that accepts malformed
output teaches the model malformed output, and a normalizer that thinks
"1,000" != "1000" silently zeroes the learning signal. Hence test_rewards.py.

Reward scheme (from the exploration plan):
    +0.2  completion is exactly <think>...</think><answer>...</answer>
    +1.0  extracted answer matches the gold answer
Absolute magnitudes matter less than they look: GRPO normalizes advantages
within each group of rollouts, so what counts is the *ordering* of rewards
and where the variance lives. Stage-2 reward-shaping experiments should use
GRPOConfig(reward_weights=[...]) rather than editing these constants.

TRL calls each reward function with the batch of completions plus every extra
dataset column as a keyword argument (our gold `answer` column arrives that
way), and optional callbacks like `log_metric` for custom W&B scalars.
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
    """Contents of the last <answer>...</answer> block, normalized.
    None if there is no answer block at all."""
    matches = ANSWER_RE.findall(text)
    return normalize_number(matches[-1]) if matches else None


def is_formatted(text):
    """True iff the completion is exactly one think block then one answer
    block. Deliberately strict: trailing chatter after </answer> fails."""
    return (
        FORMAT_RE.fullmatch(text) is not None
        and text.count("<think>") == 1
        and text.count("<answer>") == 1
    )


def format_reward(completions, **kwargs):
    """+0.2 for exact format compliance. On an instruct model this is the
    curve that should move first — it needs no math, only obedience."""
    return [
        FORMAT_REWARD if is_formatted(completion_text(c)) else 0.0
        for c in completions
    ]


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
