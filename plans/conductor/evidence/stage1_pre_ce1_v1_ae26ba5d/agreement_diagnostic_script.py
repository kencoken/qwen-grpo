"""RETROSPECTIVE regenerating script for `agreement_diagnostic.txt`
(158_s §2 label: post-hoc descriptive, NOT prospectively frozen
evidence).

Run 2026-07-24 on picome AFTER the formal 998/1000 agreement-gate stop
recorded in run_record.json; it re-derives the same deterministic
comparisons under the frozen seeds and localizes the two
disagreements. It did not enter the gate; the frozen agreement failure
does not depend on it. Its directionality finding (both flips
2k=pass vs 10k=not_pass/unresolved) is retrospective.

Regeneration (161_s correction: this FILE did not exist at the
historical checkout — it was first committed at Unit A, 2b2b6dc; only
the MODULES it imports must be at the v1 commit):

    git worktree add /tmp/v1-checkout da8424b
    cd /tmp/v1-checkout && PYTHONPATH=/tmp/v1-checkout uv run python \
        /home/ken/qwen-grpo/plans/conductor/evidence/\
stage1_pre_ce1_v1_ae26ba5d/agreement_diagnostic_script.py

i.e. run this script by absolute path from a worktree of commit
da8424b, with PYTHONPATH pointing at that worktree (163_s: python puts
the SCRIPT'S directory on sys.path, not the cwd, so without PYTHONPATH
`tasks.conductor.*` fail to import), so the modules resolve to the
exact v1 bytes.
"""

import numpy as np

from tasks.conductor import stage1_validation as sv
from tasks.conductor import stage1_tranche as st

deltas = (0.08, 0.10, 0.12)
disagree = []
for i in range(sv.COVERAGE_AGREEMENT_DATASETS):
    family = st._AGREEMENT_FAMILIES[i % 4]
    seed = sv.scenario_seed(f'D-agreement|{family}|{i}')
    rng = np.random.Generator(np.random.PCG64(seed))
    delta = deltas[(i // 4) % 3]
    if family == 'stake_ordinary':
        rows = [st._tp_rows(rng, delta, 0.75, 500) for _ in range(5)]
    elif family == 'stake_fork':
        rows = [st._tp_rows(rng, delta, 0.5, 200)]
    elif family == 'equivalence':
        sign = 1.0 if (i // 8) % 2 == 0 else -1.0
        rows = [sign * st._tp_rows(rng, delta, 0.5, 500)]
    else:
        sigmas = (0.25, 0.40, 0.50, 0.60, 0.75, 0.90)
        counts = (12, 12, 12, 12, 12, 6)
        rows = [st._tp_rows(rng, delta / 2, sg, n)
                for sg, n in zip(sigmas, counts)]
    d_small = st._agreement_decision(family, rows,
                                     sv.COVERAGE_INNER_REPLICATES,
                                     seed ^ 0xA9)
    d_big = st._agreement_decision(family, rows,
                                   sv.COVERAGE_PRODUCTION_REPLICATES,
                                   seed ^ 0xA9)
    if d_small != d_big:
        disagree.append((i, family, delta, d_small, d_big))
        print(f'DISAGREE i={i} family={family} delta={delta} '
              f'2k={d_small} 10k={d_big}', flush=True)
print('total datasets:', sv.COVERAGE_AGREEMENT_DATASETS,
      'disagreements:', len(disagree))
