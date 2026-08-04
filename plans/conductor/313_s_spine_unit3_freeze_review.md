## Verdict

Unit 3’s main result is sound, but two narrow repairs are needed before sign-off.

### P1 — Exact row-order validation is incomplete

`p0_c2_equivalence.py:129–148` compares only observation IDs and ignores `global_group_index`. Because scheduled IDs repeat, I swapped two complete rows for the same observation; derivation still produced the frozen projection exactly. Changing a non-sentinel group index to `999999` was likewise accepted.

Require every index to be a non-boolean integer equal to its physical row position. Add a repeated-ID swap regression. This closes the registered “row reorder must break equivalence” requirement and protects future temporal diagnostics.

### P1 — Malformed assignments can enter Q2 estimands

`p0_estimands.py:140–194` assumes any non-`None` assignment is parser-valid:

- `(0, 2, 1, 0)` is incorrectly counted as eligible and marginal for `fork_join`.
- `(0,)` raises `IndexError` in `marginal_target_selection()`.

That contradicts the signed valid-only/malformed-excluded semantics. Add a shared exact assignment check—correct node count, non-boolean integer workers, registered worker IDs—and return `False` for malformed assignments. Apply it consistently where estimands accept assignments, with short/long/bool/out-of-range regressions.

Neither issue changes the current C2 result: the authenticated trace has correct indices and parser-valid assignments. The repairs should leave every artifact hash unchanged.

Everything else checks out:

- Exact replay: **25/25 fields**, hash `f1912078…`.
- Independence from the legacy report and frozen projection is genuine.
- The coherent action sensitivity changes Q1 and sizing while remaining internally valid.
- Population substitution and corruption controls behave correctly.
- Full suite: **1,018 passed** under warnings-as-errors.
- Worktree and diff checks are clean.

After these local repairs, Unit 3 should be signable.