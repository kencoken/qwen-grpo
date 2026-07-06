"""Task registry. A task is everything dataset-specific — its problems and
its verifier travel together because they share a format. The rest of the
codebase (train.py, eval.py) is task-agnostic and talks to a task only
through these module-level names:

    load_train(n, **kw) -> Dataset  `prompt` column (chat messages) + the
                                    meta columns its verifier needs (TRL
                                    forwards extras to reward funcs)
    load_eval(n, **kw)  -> Dataset  held-out problems, same shape
    correctness_reward(completions, <meta...>, log_metric=None, **kw)
                                    the +1.0 reward (format_reward is shared,
                                    lives in rewards.py)
    verify(text, **meta) -> bool    scores one completion (used by eval.py)
    canonical                       fn mapping completion -> canonical answer
                                    for maj@k voting, or None when voting is
                                    meaningless (many valid answers)

Loaders accept **kw and ignore what they don't need, so callers can pass a
uniform argument set without per-task branching.

Growth rule: a task is a single file while it fits in a sitting (~<=150
lines). Past that, promote it to a tasks/<name>/ package whose __init__.py
re-exports the same names — callers never notice the difference.
"""

from tasks import gsm8k

TASKS = {"gsm8k": gsm8k}
