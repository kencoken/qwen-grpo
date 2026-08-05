Changes requested. Rev3 fixes the original normal-path issues, but it is not yet ready for the GPU probe or prelaunch freeze.

### Blocking findings

1. **Every real checkpoint bundle fails terminal verification.**
   `_BUNDLE_FILES` expects `adapter_state.safetensors`, `optimizer_state.pt`, and `scheduler_state.pt`, while the saver writes `adapter.safetensors`, `optimizer.pt`, and `scheduler.pt` from `CHECKPOINT_BUNDLE_FILENAMES`. This deterministically fails at `p0_execution.py:1620–1625`. Derive the inventory from the authoritative checkpoint contract and add a writer→verifier regression.

2. **Recoverable finalization is deterministically broken.**
   The finalize-only session starts at group `-1`, but the trajectory merger treats every session as a training session. It therefore truncates the preceding training segment at `-1` and rejects the 6,123-group trajectory. Filter merge boundaries to `fresh`/`resume` sessions and validate `finalize` sessions separately.

3. **SIGKILL recovery does not recover the evidence needed for resume.**
   `_close_killed_session()` records elapsed time but leaves raw training/evaluation files untouched. Consequently:

   - the previous checkpoint-authorized training prefix is absent from the merge;
   - the raw file violates the sealed inventory;
   - a raw partial evaluation can be overwritten on rerun.

   Resume needs an idempotent crash-sanitation step that preserves and seals/moves these artifacts before starting another session.

4. **An incomplete cadence attempt overwrites retained evidence.**
   When a bundle/HF checkpoint exists but evaluation did not complete, resume moves only the evaluation gzip. The bundle and `checkpoint-<i>` remain at their fixed paths and are overwritten when that cadence point reruns. Move the whole uncommitted attempt—bundle, HF checkpoint, and raw/sealed evaluation—into session-scoped excluded evidence.

### Additional repairs worth making in the same revision

- The session loader is not yet the claimed state machine. A valid hash chain containing `start(1), end(1,100), end(1,0)` is accepted and reports zero cumulative time because the second end overwrites the first in a dictionary. Enforce contiguous indices, closed schemas, and exactly one legal start/end pair per session.
- `_unwrapped()` follows a raw scheduler’s `.optimizer`, so the post-training scheduler identity assertion can pass after scheduler replacement. Use separate optimizer and scheduler unwrapping; ensure the GPU probe checks the actual scheduler identity/state.
- Final directory hashing, ledger append, and final verification still occur after the session is closed and are therefore outside measured elapsed time.
- `verify_p0_run()` should enforce the manifest-bound execution root and use the archived, manifest-pinned prelaunch artifacts rather than current committed copies for genuinely historical verification.

### Verification

- `1039 passed` under warnings-as-errors.
- Diff check is clean.
- The approved freeze, execution-identity, and evaluation-realization pins remain unchanged, appropriately: these repairs do not alter evaluation semantics.

The green suite currently lacks the end-to-end saver→verifier, all-cadence finalization-resume, and hard-crash sanitation cases that expose the blockers. I recommend one tightly scoped Rev4 addressing these integration paths, followed by the planned reward-blind GPU probe.