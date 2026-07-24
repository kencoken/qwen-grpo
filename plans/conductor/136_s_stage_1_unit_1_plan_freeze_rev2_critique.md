## Final-review verdict

Not quite ready for Unit 2. The previous findings were addressed correctly, but two narrow blockers remain at remote tip `bd5953d`.

### Findings

1. **[P1] The intervention edge table has two sources of truth.**

   [stage1.py:68](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/stage1.py:68) duplicates the authoritative table in [types.py:376](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/types.py:376). Generation and estimand scoring use the latter, while admission gates use the new copy. The tests only exercise the copy, so the two could drift despite `135_f` stating that this is impossible.

   Import `CELL_INTERVENTION_EDGES` from `types.py`, delete the duplicate, and retain the cross-product tests.

2. **[P1] Bootstrap seed canonicalization rejects supported later populations.**

   [stage1.py:247](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/stage1.py:247) permits only qualification looks—ordinary `{100,300,500}` and fork `{100,200}`. But §8.3 applies the same bootstrap identity to policy-development headroom, `pilot_gate`, and final C1/C2/C3 inference. Counts such as 12, 24, 56, 67, and 72 are therefore rejected.

   It also accepts `100.0` because integral floats compare equal to integers in schedule membership, producing a different serialized seed identity.

   Make this canonicalizer population-independent:

   - known cell;
   - `type(count) is int`;
   - count greater than zero;
   - sorted canonical serialization.

   Unit 2’s population manifest should perform the phase-specific schedule/count validation. Add tests for pilot, both final mixtures, policy-development counts, and float/bool rejection.

### Confirmed closed

The earlier fixes are otherwise sound:

- all fork edge × diagnostic gates are now represented;
- protocol denominator formulas are correct;
- few-shot and schema-only prompt bytes are pinned correctly;
- no-repair is explicitly and coherently frozen;
- `policy_dev_cohort` now rejects malformed index types;
- retry and gate tables are exact-pinned;
- shallow-router levels are frozen;
- the successor digest requirement records `contract.py`.

As cheap follow-through, Unit 2 should cross-check `WORKER_FAMILIES` and renderer count against the authoritative worker registry and renderer list rather than trusting duplicate literals.

### Verification

- Focused suite: 130 passed with warnings as errors.
- CPU-compatible suite: 632 passed.
- `git diff --check`: clean.

After these two local corrections, I recommend closing Unit 1 and moving directly to Unit 2 without another broad audit.