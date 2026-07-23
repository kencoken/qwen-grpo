# Response to 84_s — second-round worker-eval review

**Review target:** `dec2863`. **This response:** the commit carrying this
document. Full suite: 547 tests (4 net new), `-W error` clean.

## Disposition

All three blocking findings and the lower-severity discrepancy are
**accepted and fixed** — nothing declined this round. Each finding named
a path D16 will actually exercise, and each fix stayed local, per the
shared triage principle. The reviewer also correctly overturned a claim
in `83_f` (pairwise-flip derivability); the correction is below.

### Finding 1 — §7.4 confirmation under-specification: fixed

The self-confirmation reproduction (`confirm_repeat_run(run, run)` →
confirmed) was one CLI slip away — passing the same run directory twice.
`confirm_repeat_run` now takes an explicit `expected_namespace` (CLI
`--namespace`, required) and additionally requires:

- the declared full §7.4 population: isolated mode, 30 per cell
  (`FULL_RUN_PER_CELL`), the full renderer crossing, private
  visibility — enforced without override at the CLI; the function's
  `per_cell` parameter exists only so CPU tests can exercise the
  mechanism at 1/cell;
- singleton generation policy on both manifests;
- **distinct run IDs and distinct recorded process identities** — the
  evaluator manifest now carries a `process` field (pid + start time,
  injectable via `process_info` for same-process tests), which the
  probe outputs already had;
- **one clean commit.** Agreed with the review: the cross-candidate
  commit policy does not apply here — a repeat run is same-candidate,
  same-code by definition, and the docstring says so.

Canonical generation order is enforced one level down, in `load_run`:
every isolated row's `generation_ordinal` must equal its position in
the regenerated plan, so *any* loaded run proves canonical order and
the confirmation inherits it (tamper test:
`test_loader_requires_canonical_generation_order`). The test that
previously codified 30-case confirmation now asserts the reviewer's
reproduction fails (`test_confirm_repeat_run_and_cli`: self-
confirmation, wrong namespace, diagnostic population, and split
commits all refuse).

### Finding 2 — header-blind P0 comparison: fixed

Accepted as the most practically dangerous item: P0 conditions run in
separate invocations during active D16 iteration, so a prompt, model,
template or code change between `original` and `reversed` would have
been misreported as batching evidence — manufacturing the very confound
P0 exists to pin down. New `compare_probe_outputs`:

- refuses unless the probe-type-specific held-fixed headers match — for
  P0: cohort SHA, endpoint, generator/schedule versions, runtime
  profile fingerprint, prompt and template hashes, environment; for P1
  pairs: the existing held-fixed set;
- refuses dirty trees and split commits between the compared runs;
- refuses if any case's `user_message_sha256`/`request_sha256` pair
  differs (the reviewer's reproduction — equal completions over
  different request bytes — now fails closed);
- only then reports per-case outcome differences, which for P0 remain
  the retained evidence, not an error.

The CLI distinguishes the two outcomes: exit 2 with `NOT COMPARABLE`
for configuration drift, exit 1 for genuine outcome differences.
`compare_records` survives unchanged as the inner per-case comparator
used by admission. Test:
`test_probe_compare_refuses_configuration_drift` (request drift, header
drift, split commit → all exit 2).

### Finding 3 — label-driven candidate identity: fixed, all four parts

- **Freeze grade is intrinsic.** `build_manifest` now verifies any
  bundle *claiming* `FROZEN` against the registry whether or not
  `frozen_candidate` was passed — the flag is a convenience, not the
  guard. `load_run` rechecks every stored FROZEN claim: the revision
  must resolve through the registry with FROZEN status and matching
  text/hashes, so the claim is downstream-verifiable. Tests:
  `test_frozen_claim_is_intrinsic` (build side without the flag; loader
  side against a tampered stored status).
- **"prompt" must differ in actual bytes.** The declared-difference
  check now uses a per-enum `_MUST_DIFFER` set:
  `system_prompts.text`/`sha256` for prompts. A revision-label-only
  relabel is refused.
- **"model" must change a checkpoint, on exactly one endpoint.** The
  must-differ set is per-endpoint `model_id`/`revision`; a chat-
  template-only change is refused, and a comparison whose declared
  model paths span more than one endpoint is refused with an
  instruction to name a multi-endpoint contrast explicitly if one is
  ever intended. This matches the actual D16 design: one Code-endpoint
  contrast per comparison, both arms sharing the ratified Math swap.
  Test: `test_comparison_requires_actual_byte_differences` (relabel,
  template-only, two-endpoint each refused; a single-endpoint
  Code-model change compares).
- **`request_contract` comparison disabled.** The reviewer is right
  that this was anticipatory: `resolve_request_contract` metadata does
  not configure `build_worker_call`, so a second registry key would
  have created a no-op arm with real-looking provenance. The enum
  entry is removed and the name raises a targeted error explaining the
  re-enable condition: a request-scope option that actually
  parameterizes the builder (the D16 request-scope experiment is where
  that code path will exist).

### Lower severity — pairwise flips: fixed, and the 83_f claim corrected

The reviewer is correct and `83_f`'s derivability claim was wrong: the
aggregate `paired.flipped` records only whether *any* renderer
disagreed and cannot identify the pair. The summary now records
`paired.pairwise`: for each unordered renderer pair, `{n, flipped}`
counts (counts-only, exact rederivation preserved). The hand-calculated
fixture verifies all three pairs (both bound_var pairs flip once on L1;
resource_first/goal_first never flip).

## Also adopted from the review's notes

- "Registered" wording replaced with "declared" throughout the probe
  and confirmation surfaces — the `worker_dev` namespace, exact P1 case
  set and retained P0 cohort hashes remain Tranche-D blockers pending
  the D1 erratum, exactly as the review frames them.
- The review's practical advice on commit hygiene is noted for the D16
  runbook: use one commit across D16 arms unless a human has verified a
  difference is documentation-only. The comparison tool reports commit
  differences loudly either way.

## Verification

- Full suite: 547 passed, warnings-as-errors clean.
- Each reproduced behavior now has a test at the named boundary:
  self-confirmation fails; request-hash drift is `NOT COMPARABLE`
  (exit 2), not "no differences"; a forged FROZEN status fails at build
  without the flag and at load against the registry; relabelled-
  revision and template-only comparisons are refused.
- No change to generation, rendering, parsing, tool or cache behavior.

Per the review's closing paragraph, the affected boundaries —
confirmation, P0 comparison, candidate identity — are ready for the
focused re-review before merge.
