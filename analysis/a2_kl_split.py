"""A2: split E1's per-step kl/entropy by group outcome (see experiment_log.md).

E1 finding 5 claimed the late-run KL drop reflects relaxation of the
sharpening, with a caveat that per-step KL varies with which problem was
sampled (composition noise). Pre-registered discriminator:
  - drop mostly in zero-variance steps  -> composition effect
  - drop present in mixed-outcome steps -> genuine relaxation

Zero GPU: pulls the logged history of run nfrzmbjv from the W&B API.

  uv run python analysis/a2_kl_split.py
"""

import wandb

RUN = "kencoken/qwen-grpo/nfrzmbjv"
WINDOW = 50


def main():
    history = wandb.Api().run(RUN).history(samples=10_000, pandas=True)
    rows = history[["train/global_step", "train/kl", "train/entropy",
                    "train/frac_reward_zero_std"]].dropna()
    rows = rows.sort_values("train/global_step")

    print(f"{len(rows)} steps | split by frac_reward_zero_std "
          f"(1 = uniform group: no gradient, 0 = mixed)\n")
    header = (f"{'steps':>12} | {'kl uniform':>10} {'kl mixed':>10} | "
              f"{'ent uniform':>11} {'ent mixed':>10} | {'n_unif':>6}")
    print(header)
    print("-" * len(header))
    for lo in range(0, 300, WINDOW):
        w = rows[(rows["train/global_step"] > lo)
                 & (rows["train/global_step"] <= lo + WINDOW)]
        uniform = w[w["train/frac_reward_zero_std"] == 1]
        mixed = w[w["train/frac_reward_zero_std"] < 1]
        fmt = lambda s, col: f"{s[col].mean():.4f}" if len(s) else "     -"
        print(f"{lo+1:>5}-{lo+WINDOW:<6} | {fmt(uniform,'train/kl'):>10} "
              f"{fmt(mixed,'train/kl'):>10} | "
              f"{fmt(uniform,'train/entropy'):>11} "
              f"{fmt(mixed,'train/entropy'):>10} | {len(uniform):>6}")


if __name__ == "__main__":
    main()
