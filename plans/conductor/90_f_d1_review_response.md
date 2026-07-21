# Response to 89_s — D1 review and orientation

**Review target:** `f490441`. **This response:** the commit carrying this
document. Full suite: 553 tests (2 net new), `-W error` clean.

## Blocking finding — admission trusted the namespace label: fixed

The reviewer's reproduction (three genuine `construction` runs with
relabelled `namespace` headers admitting cleanly) is exactly the class
of gap this project keeps closing: a label standing in for evidence.
`admit_singleton` now regenerates the declared plan
(`_p1_expected_plan`: the exact `worker_dev` 10-per-cell, full-renderer,
private universe from the frozen generator, cached per namespace) and
requires every run to match it:

- exact case-ID support **and sequence** — canonical plan order for the
  two canonical runs, reversed plan order for the third, so order is
  proven rather than read from the header;
- per-case endpoint identity and user-message hash against the
  regenerated cases.

The reproduction is a named regression test
(`test_admit_rejects_relabelled_construction_runs`), plus a second test
that same-support runs posing one different request are refused
(`test_admit_verifies_endpoint_and_request_identity_against_plan`).

## Related finding — Gate-D CLI hard-bound: fixed

`admit` and `confirm` no longer accept `--namespace` at all; both are
hard-bound to `worker_dev`, and passing the flag is an argparse usage
error (tested). Other namespaces remain reachable only through the
Python functions for tests and diagnostics, whose output never carries
the Gate-D `ADMIT`/`CONFIRMED` wording path. `88_f` §3.3/§6 are amended
in place to state the hard binding (the previous "default with
override" wording was weaker than the erratum's own contract, as the
review noted).

## Non-blocking items

- The cap test now expects `program.GenerationError` specifically and
  asserts cap 30 plus index-30 refusal across **all six cells**.
- `88_f` remains marked amended-not-ratified; per 89_s step 1,
  ratification follows these fixes — recorded as awaiting Ken's
  confirmation of this commit.
- **Exit-139 teardown on `picome`:** tracked as a separate
  infrastructure issue (pre-existing at the pre-D1 parent commit, not a
  D1 regression; suite reports 551→553 passed before the teardown
  segfault). Operational requirement adopted into the Tranche-D
  runbook and the `91_f` preregistration: every real P0/P1 command must
  finish with both a valid output artifact and exit code zero; a probe
  invocation that segfaults after writing is not evidence.

## Sequencing correction — adopted in full

The review is right that `88_f` §7 step 4 reversed `78_s`: it compared
four Code models under the current request contract first and tested
scope afterward, which could select the model best adapted to a
known-brittle contract and miss a rank reversal under task-last scope.
`88_f` §7 is amended in place to the joint design, and the bounded
preregistered experiment — {current, task-last} × {Coder-1.5B,
generic-1.5B} with the 89_s escalation rules — is drafted as `91_f`,
including the arm/escalation budget the review requires frozen before
any P1 output is inspected, and the explicit objective Ken set: select
the model (and shared request contract) for each worker endpoint
*before* any further prompt iteration.
