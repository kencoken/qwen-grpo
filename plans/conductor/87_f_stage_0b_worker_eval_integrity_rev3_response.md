# Response to 86_s — third-round worker-eval review

**Review target:** `9f751bd`. **This response:** the commit carrying this
document. Full suite: 548 tests (1 net new), `-W error` clean.

## Disposition

Both blocking findings and the lower-severity recommendation are
**accepted and fixed**. All three are narrow, and the first is directly
result-relevant given the pending Math endpoint-swap erratum.

### Finding 1 — endpoint-scoped model comparison: fixed

Accepted, with emphasis on the finding's second half: the caller never
declared *which* endpoint a model comparison was about, and D16
comparison runs will straddle the Math endpoint-swap history — an
intended Code contrast whose arms actually differed on Math would have
passed, misattributing the delta to the Code candidate.

`compare_worker_eval_runs` now takes `model_endpoint`, required for
`allowed_difference="model"` and rejected otherwise. The allowlist is
built per call by `_model_scope(endpoint)`: the declared endpoint's
`model_id`/`revision`, its chat-template hash, tokenizer facts and
endpoint fingerprint, plus the two global fingerprints those feed.
Everything else — including any *other* endpoint's template, tokenizer
or fingerprint drift — is an undeclared difference and refuses. The
must-differ set is the declared endpoint's checkpoint identity, so the
previous exactly-one-endpoint post-check is subsumed and removed. The
verdict records `model_endpoint`.

Tests (`test_comparison_requires_actual_byte_differences`): the
reviewer's exact reproduction (Code `model_id` change plus unrelated
Math chat-template drift) now refuses; a missing endpoint raises; a
declared-Math comparison over an actual Code change refuses; the
multi-endpoint case still refuses (now via the scoped allowlist);
`model_endpoint` with a prompt comparison raises.

### Finding 2 — fixed public §7.4 entry point: fixed, per the review's own suggestion

`confirm_repeat_run(left, right, expected_namespace)` no longer accepts
a population override; it is fixed at `FULL_RUN_PER_CELL` and delegates
to module-private `_confirm_repeat_run(..., per_cell)`, which exists
only so CPU tests can exercise every check against 1/cell fake
populations. D16 integration code calling the public authority directly
therefore cannot weaken the confirmation. The test suite asserts the
public signature rejects the old keyword (`TypeError`), and the
mechanism tests import the private helper explicitly. No proof-marker
abstraction was introduced, per the review's note.

### Lower severity — P0 self-comparison: fixed

Accepted as practical: §7.2's protocol includes executing the original
grouping *twice*, and comparing one output file against itself by slip
would manufacture exactly the "0/90 changed" bit-stability evidence
that condition exists to establish. `compare_probe_outputs` now refuses
two outputs sharing one recorded process identity (pid + start time)
with the `NOT COMPARABLE` outcome (exit 2), before any header or
per-case check. Test: `test_probe_compare_refuses_self_comparison`.

## Deferred-gates note: adopted as a D1 obligation

Agreed on both points. A green `admit`/`confirm` against `construction`
(or any namespace other than the eventual registered one) is **not**
Gate-D completion — the commands validate mechanism, not registration.
Pointer comments now sit at both namespace surfaces (the `admit` CLI
argument and the `confirm_repeat_run` docstring) stating the
obligation: when the D1 erratum registers the dedicated
worker-development namespace, bind it into these commands as the
authoritative default rather than a per-invocation operator assertion.
That binding is Tranche-D/D1 work by construction, since the namespace
does not yet exist.

## Verification

- Full suite: 548 passed, warnings-as-errors clean.
- The reviewer's reproduction from finding 1 is now a named test case
  and refuses; self-comparison of a probe output exits
  `NOT COMPARABLE`; the public confirmation signature has no override.
- No change to generation, rendering, parsing, tool or cache behavior.

Ready for the focused confirmation/comparator check the review scopes
as the final step before merge.
