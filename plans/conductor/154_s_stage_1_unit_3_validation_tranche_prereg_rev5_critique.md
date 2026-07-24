Not quite. Four of the five findings are closed, but one narrow lock blocker remains.

- `run_replay()` only catches failures inside `_generate()` (`stage1_replay.py:634–639`). Failures during model loading/preparation or artifact writing/finalization leave `run_record.json` permanently marked `running`. This contradicts rev5’s “any abort writes an aborted record with wall time” contract and is realistic on the 4090 path.

Wrap the entire post-`running` sequence—model construction through artifact reload—in the abort handler. Add targeted probes for a model-load failure and a post-generation finalization failure.

Everything else passes:

- Authoritative replay reconstruction and real-row recount: closed.
- Zero eligibility remains `unresolved`: closed.
- D deadline abort preserves timing and partial progress: closed.
- Phrasing corrections: closed.
- Focused suite: 72 passed.
- Full suite: 834 passed with warnings-as-errors.
- No frozen tranche or GPU replay was run.

Two non-blocking cleanups can accompany the fix: remove the extra EOF blank line and the duplicated rev4 sentence in `153_f`. Total CPU wall time would be useful but is not required by the frozen contract.

After that single abort-boundary fix and a changed-lines/test review, I recommend locking immediately—no further open-ended audit.