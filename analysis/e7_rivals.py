"""E7: score the three rivals for A3's eval advantage (see experiment_log.md).

Consumes the per-problem JSONs from data/evals/ produced by the E7 battery:
paired McNemar tests between adapters, difficulty-slice accuracies (slices
from base k=8 pass counts), and the A3 pass@k polishing signature.

  uv run python analysis/e7_rivals.py
"""

import json
from math import comb

EVALS = "data/evals"
BASE = "Qwen2.5-7B-Instruct-k1-t0.0"
BASE_K8 = "Qwen2.5-7B-Instruct-k8-t1.0"
ADAPTERS = {  # greedy per-problem files, display order
    "E1": "stage1-7b-g8-t1.0-k1-t0.0",
    "repro": "e1-repro-newstack-k1-t0.0",
    "A4": "a4-filtered-s1-k1-t0.0",
    "A3": "a3-easy-control-k1-t0.0",
}
A3_K64 = "a3-easy-control-k64-t1.0"
# E4 anchors (aggregates recorded in experiment_log.md; per-problem data for
# the base k=64 run was not saved and is not needed for this comparison)
E4_BASE_PASS64, E4_BASE_SAMPLED_PASS1 = 0.990, 0.868


def load(name):
    with open(f"{EVALS}/{name}.json") as f:
        return json.load(f)["results"]


def correct_vector(results):
    return [r["n_correct"] > 0 for r in results]  # greedy: k=1


def mcnemar(x, y):
    """Exact two-sided McNemar on paired booleans: p-value from the
    discordant pairs under a fair coin."""
    b = sum(a and not b_ for a, b_ in zip(x, y))   # x right, y wrong
    c = sum(not a and b_ for a, b_ in zip(x, y))   # y right, x wrong
    n = b + c
    if n == 0:
        return b, c, 1.0
    p = min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) * 0.5**n)
    return b, c, p


def main():
    base = correct_vector(load(BASE))
    adapters = {k: correct_vector(load(v)) for k, v in ADAPTERS.items()}
    n = len(base)

    print(f"=== aggregates (n={n}) — must reproduce the E6 ledger")
    print(f"{'base':>6} {sum(base)/n:.3f}")
    for name, v in adapters.items():
        print(f"{name:>6} {sum(v)/n:.3f}")

    print("\n=== paired McNemar (b = row-model right & column wrong)")
    for name, v in adapters.items():
        b, c, p = mcnemar(v, base)
        print(f"{name:>6} vs base    +{b:<3} -{c:<3} p={p:.3f}")
    for name in ("E1", "repro", "A4"):
        b, c, p = mcnemar(adapters["A3"], adapters[name])
        print(f"    A3 vs {name:<6} +{b:<3} -{c:<3} p={p:.3f}")

    # difficulty slices from base k=8 pass counts
    k8 = {r["i"]: r["n_correct"] for r in load(BASE_K8)}
    slices = {"easy (8/8)": lambda c: c == 8,
              "mid (4-7/8)": lambda c: 4 <= c <= 7,
              "hard (0-3/8)": lambda c: c <= 3}
    print("\n=== greedy accuracy by base-difficulty slice")
    header = f"{'slice':>14} {'n':>4} {'base':>6} " + " ".join(f"{m:>6}" for m in adapters)
    print(header)
    for label, pred in slices.items():
        idx = [i for i, c in k8.items() if pred(c)]
        row = f"{label:>14} {len(idx):>4} {sum(base[i] for i in idx)/len(idx):>6.3f} "
        row += " ".join(f"{sum(v[i] for i in idx)/len(idx):>6.3f}" for v in adapters.values())
        print(row)

    # polishing signature: A3 pass@k boundary vs E4's base anchors
    a3k = load(A3_K64)
    pass64 = sum(r["n_correct"] > 0 for r in a3k) / len(a3k)
    pass1 = sum(r["n_correct"] for r in a3k) / (len(a3k) * 64)
    print(f"\n=== A3 pass@k signature (base anchors from E4)")
    print(f"  pass@64: A3 {pass64:.3f} vs base {E4_BASE_PASS64:.3f}")
    print(f"  sampled pass@1: A3 {pass1:.3f} vs base {E4_BASE_SAMPLED_PASS1:.3f}")


if __name__ == "__main__":
    main()
