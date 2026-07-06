"""One-off difficulty filter for the Stage-1 training set (~minutes on vLLM).

Samples a few rollouts per training problem at the training temperature and
keeps only problems with pass rate strictly between 0 and 1. Why: GRPO's
advantage is (reward - group mean) *within* each group, so a problem the
model always solves — Qwen2.5-7B-Instruct is ~80-85% on GSM8K — or never
solves gives every rollout identical reward: zero advantage, zero gradient,
GPU-time wasted. The printed histogram makes this visible.

  uv run python filter_data.py
"""

import argparse
import json
import os
from collections import Counter

from eval import batch_generate, load_model
from rewards import extract_answer
from tasks.gsm8k import FILTERED_PATH, load_train


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--n_problems", type=int, default=1500)
    parser.add_argument("--num_rollouts", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=1.0)
    args = parser.parse_args()

    dataset = load_train(n=args.n_problems)
    llm, _ = load_model(args.model)
    completions = batch_generate(
        llm, dataset["prompt"],
        temperature=args.temperature,
        num_return=args.num_rollouts,
    )

    passes = [
        sum(extract_answer(c) == gold for c in group)
        for group, gold in zip(completions, dataset["answer"])
    ]
    kept = [i for i, p in enumerate(passes) if 0 < p < args.num_rollouts]

    histogram = Counter(passes)
    print(f"\npass rate over {args.num_rollouts} rollouts (0 and max give no gradient):")
    for k in range(args.num_rollouts + 1):
        print(f"  {k}/{args.num_rollouts}: {'#' * (60 * histogram[k] // len(passes))} {histogram[k]}")
    print(f"kept {len(kept)}/{len(passes)} problems with mixed outcomes")

    os.makedirs(os.path.dirname(FILTERED_PATH), exist_ok=True)
    with open(FILTERED_PATH, "w") as f:
        json.dump(
            {
                "model": args.model,
                "temperature": args.temperature,
                "num_rollouts": args.num_rollouts,
                "kept_indices": kept,
            },
            f,
        )
    print(f"wrote {FILTERED_PATH}")


if __name__ == "__main__":
    main()
