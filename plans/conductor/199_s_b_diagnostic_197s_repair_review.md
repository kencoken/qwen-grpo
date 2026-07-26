Not quite ready to freeze. Three narrow launch-boundary fixes remain:

1. **The lock does not validate smoke semantics.** I confirmed a rehashed lock pointing to `{"status":"aborted"}` is accepted. The consumer must parse the bound smoke record and verify successful status, tag, identities, budget/completion count, and shapes. Include `uv_lock_sha256` in the smoke→lock→launch identity comparison.

2. **The smoke is not one-shot.** A second invocation overwrites the first record. Refuse before preflight/model loading if the canonical record or temporary path already exists.

3. **Abort archival accepts completed runs.** `archive --mode abort` can archive a complete run with no validation error, consume the immutable destination, and skip authenticating verification. Require `status == "aborted"`.

Everything else is closed correctly: provenance rederivation, report outputs, estimands, UTF-8 handling, mid-block preservation, synthetic-only smoke loading, and the BatchEncoding repair.

Verification passed:

- 14 focused tests
- **916 full-suite tests under warnings-as-errors**
- Clean diff check
- Source digest matches `84623e3c…`

No elaborate lock framework is needed—a shared smoke-record validator plus the local checks above is sufficient. At lock time, still materialize the exact seed registry as specified. After these fixes, only a final mechanical changed-lines check should be necessary.