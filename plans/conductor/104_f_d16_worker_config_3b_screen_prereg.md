# 104_f — preregistration: the bounded 3B prompt×model screen

**Status: registered by Ken's in-session direction, 2026-07-22**
("Let's proceed", adopting the 103_s recommended course), under the
same rules as 99_f/101_f: exact named configurations, candidate-specific
P1 admission, full crossed runs, preregistered evaluation, hard stop.
This is 102_f option (a) widened to {rev10, rev11} per 103_s.

## Question and design

Does Code-worker scale close the remaining protocol-class gap, and does
scale absorb rev11's instruction load without its 1.5B regressions?

Four candidates, tranche **F3**:

```text
{generic_3b, coder_3b} × task_last × {rev10, rev11}
```

Code scale is the **only** model change: Lookup and Math stay on the
generic 1.5B checkpoint (rev9 Lookup / rev10 Math bytes, `task_last`)
in every arm. Registry fact established at registration: all Qwen2.5
checkpoints share one chat template, so every F3 arm's support digest
is byte-identical to its 1.5B counterpart's — the screen swaps
**weights only**, not a single request byte. Support digests
regenerated to 23 candidates; the 19 pre-existing entries verified
byte-identical to the committed registry.

## Arm order and conditionality

1. `generic_3b-task_last-rev10` — the anchor prompt at 3B.
2. `generic_3b-task_last-rev11` — **unconditional** (runs regardless of
   arm 1's outcome): if 3B keeps rev11's ten targeted repairs without
   the 19 regressions, that is direct evidence for the
   instruction-capacity explanation, independent of hitting the target.
3. `coder_3b-task_last-rev10` and 4. `coder_3b-task_last-rev11` —
   **conditional**: run only if **neither** generic arm meets the §4.1
   target (103_s: generic prioritized; 92_s §8 smallest-pool preference
   makes a coder win relevant only on a generic miss).

## Gates (unchanged — declared before any P1)

- Frozen §7.3 cost gate stands **unamended**: 3600 s projected /
  900 cases and 22 GiB peak VRAM. Basis: 1.5B arms projected 258 s;
  even 3× slower decode projects ~775 s, and the mixed 1.5B+3B NF4
  layout was frozen-estimated ~7.8 GiB. A gate failure is a genuine
  non-admission, not a reason to revisit thresholds post hoc.
- Admission per arm: P1 triplet (canonical, canonical, reversed; three
  fresh processes) + `admit` at this document's commit, clean worktree,
  `EXPERIMENT_DEVICE` cuda.
- `coder_3b` is the one checkpoint never loaded locally: its declared
  3,085,938,688 parameters are verified at first load, and a mismatch
  is a **HARD STOP** requiring a new preregistration (registry rule,
  94_s) — never an in-place correction.

## Preregistered evaluation

1. **Primary, per arm:** the frozen §4.1 target — 30/30 in every
   endpoint×cell×renderer group (900/900); §4.2 floor as frozen
   fallback.
2. **Guard:** all 630 Lookup+Math records of every arm byte-identical
   to the 99_f rev10 run (prompts, requests and workers are unchanged;
   any difference is a reproducibility stop).
3. **rev11-at-3B secondary (arm 2 vs retained artifacts):** the fate of
   (a) the 13 rev10-characterized residual cases (do the ten 1.5B
   repairs persist?) and (b) the 19 rev11-at-1.5B regression cases (do
   they vanish at 3B?). Case identities derive from the retained
   `runs/99f-rev10` and `runs/101f-rev11` score records.
4. **Selection if any arm meets the target:** 92_s §8 smallest-pool
   preference — generic before coder; rev10 before rev11 on a tie (the
   anchor prompt, fewer instructions). The selected arm proceeds to the
   92_s §10 close-out (confirmation run, composed diagnostic, decision
   record). The 103_s shared-3B deployment alternative (Lookup/Math on
   the same 3B checkpoint) is explicitly **out of scope** — a separate
   follow-up decision requiring Lookup/Math revalidation.
5. **All executed arms miss → stop with evidence.** No prompt edits
   under this document; the four named arms are the complete scope.
   Fallback levers are 103_s's list (local_only, BF16,
   grammar-constrained decoding, one compressed replacement prompt),
   each requiring its own preregistration.

Per 103_s, unrestricted prompt editing against the current
`worker_dev` population is closed — eleven revisions were developed on
these 30 programs per cell; any future prompt work needs fresh
instances. The complementary 1.5B policies (rev10/rev11-generic/
rev11-coder, oracle union 270/270 Code) are preserved as a separate
orchestration preregistration, not part of this screen.
