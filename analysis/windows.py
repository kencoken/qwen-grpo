"""Print the 50-step window table (the E-entry dynamics fingerprint) for one
or more W&B runs — entropy, zero-variance fraction, kl, completion length,
correctness. Used for cross-run comparisons in experiment_log.md.

  uv run python analysis/windows.py upkp33jc qwen-grpo-countdown/abc123 ...

Bare run ids default to the qwen-grpo project; prefix with "project/" for
other projects.
"""

import sys

import wandb

COLS = {"entropy": "train/entropy", "zero-var": "train/frac_reward_zero_std",
        "kl": "train/kl", "len": "train/completions/mean_length",
        "corr": "train/rewards/correctness_reward/mean"}
WINDOW = 50


def main():
    api = wandb.Api()
    for run_id in sys.argv[1:]:
        path = run_id if "/" in run_id else f"qwen-grpo/{run_id}"
        run = api.run(f"kencoken/{path}")
        h = run.history(samples=10_000, pandas=True)
        rows = h[["train/global_step"] + list(COLS.values())].dropna()
        rows = rows.sort_values("train/global_step")
        last = int(rows["train/global_step"].max())
        print(f"--- {run.name} ({run_id})")
        print(f"{'steps':>10} " + " ".join(f"{k:>9}" for k in COLS))
        for lo in range(0, last, WINDOW):
            w = rows[(rows["train/global_step"] > lo)
                     & (rows["train/global_step"] <= lo + WINDOW)]
            cells = " ".join(f"{w[v].mean():>9.3f}" for v in COLS.values())
            print(f"{lo+1:>4}-{lo+WINDOW:<5} {cells}")
        print()


if __name__ == "__main__":
    main()
