# Response to 94_s — implementation critique of the 92_s prerequisites

**Review target:** `691c653` (which already carried the 94_s prompt
amendment and the `93_f` corrections). **This response:** the commit
carrying this document. Full suite: 563 tests, `-W error` clean.

## Disposition

All eight blocking findings **accepted and fixed** — as reported to Ken
before implementation, this round's findings all mapped to paths that
would change which candidate gets selected, so nothing was declined.
One sub-point within finding 4 is resolved differently than suggested,
with rationale below.

### F1 — screening requires the complete triggered tranche: fixed

`screen` refuses (no launch manifest of any kind) unless every
candidate in the triggered arm set has a complete, well-formed triplet.
The test that previously blessed single-arm screening is replaced by
`test_screen_requires_the_complete_tranche`, which builds all eight
Tranche-A triplets, and asserts a deleted file refuses.

### F2 — candidate identity at both boundaries: fixed

- Screening refuses files that do not embed the expected candidate id
  (candidate-less diagnostic files included).
- Reveal never trusts the index label: `_verify_candidate_run` checks
  the loaded manifest's candidate label, evaluation mode, commit,
  runtime-profile fingerprint, prompt hashes, contract digest, planned
  physical layout and population against the registry, and the run's
  posed support against the pre-registered digest. The reviewer's
  reproduction — a generic run under a Coder identity — is a named
  refusing test inside the reveal end-to-end.

### F3 — the launch manifest is rederived, never trusted: fixed

The screening artifact now records the tranche's single commit and the
sha256 of every P1 source file. `reveal` recomputes the entire
screening from the raw P1 artifacts and refuses if the stored manifest
does not rederive (edited-launch test included). `run` maintains
`completion_index.json` mapping each candidate/mode to its actual fresh
run directory and manifest hash — which also resolves the hard-coded
`<cid>-full` restart problem: `RunWriter` still refuses directory
reuse, restarts take fresh names, and reveal follows the index with a
manifest-hash check.

### F4 — one clean executable commit across arms: fixed, one sub-point resolved differently

Screening refuses dirty trees or split commits across all 24 P1 files;
reveal additionally requires every full-run manifest to carry the
screening's commit. The cross-candidate git middle ground agreed in
`83_f` is explicitly overridden for this experiment, per `92_s` §2.4.

**The `frozen_candidate=True` sub-point is not implemented as
suggested**, deliberately: that flag gates on registry-FROZEN prompt
status, and the experiment's treatments are preregistered *drafts* —
the D16 prompt surface freezes at `92_s` §10, after selection. Setting
the flag would refuse every legitimate arm. The one-commit rule the
finding actually targets is enforced at the screening and reveal
boundaries instead. Flagged for the reviewer's confirmation.

### F5 — the Tranche B state machine: fixed

Reveal emits `contract_states` (`viable` / `proven_non_target` /
`unaudited`) derived from the sentinels' unchanged Lookup/Math groups,
carrying forward `proven_non_target` for contracts ineligible at
screening. Tranche B screening requires the validated Tranche A reveal
artifact, refuses outright if A selected a target (§8: the larger
tranche is never opened in that state), restricts the B arm set to
eligible contracts, and stops if none remain. All three transitions are
tested.

### F6 — the pre-run support freeze: fixed, in the compact form

`gen_support_digests` produced the committed registry
(`fixtures/support_digests.json`, sha `84b4baa3…`): per candidate, one
content hash over the complete 300-case P1 identity rows (case id,
endpoint, user-message hash, rendered request digest), the
canonical/reversed sequence hashes, and one over the 900-case full
rows — all sixteen candidates, including Tranche B (the Coder-3B
tokenizer resolved and downloaded; weights remain first-use). Admission
refuses if the regenerated plan does not match the registered digest;
reveal refuses a full run whose posed support does not match. No new
type system — three hashes per candidate. One sanity note the registry
surfaced: `generic_1p5b` and `generic_3b` share identical support
digests under equal contracts/prompts because the Qwen2.5 chat template
is identical across sizes — correct, and exactly why admission also
binds the runtime-profile fingerprint, which does differ.

### F7 — model comparison unbroken: fixed

`physical_layout` joined the model-scoped allowed differences (it
follows from the declared endpoint's checkpoint). The real
generic-vs-Coder manifests now compare; a layout difference under a
prompt or contract comparison still refuses.

### F8 — §9 contrasts and fallback landed now, in the frozen commit: fixed

Conceded from my earlier "before reveal suffices" position — analysis
rules are reveal rules under §6.11. Reveal now derives: full-population
paired contrasts for executed pairs differing in exactly one factor
(exact win/loss/tie counts, overall and per endpoint × cell × renderer
group, identical support enforced); prefix paired contrasts over all
P1-admitted candidates (strict per-case recompute); complete executed
rectangles with per-arm counts; and the §4.2 fallback verdict for every
fully evaluated arm, with `fallback_not_evaluated` recorded for
screened-out arms — never imputed.

### Tail items

Quantization is bound into the planned layout and checked against the
profile at load; measurements record the device; per-endpoint telemetry
(all three endpoints, positive call counts, finite non-negative
seconds) is loader-validated. The Coder-3B condition is written into
the registry: a first-load parameter mismatch is a **hard stop
requiring a new preregistration**, never an in-place correction. The
reveal-interpretation wording is adopted verbatim: semantic material is
retained in the run artifacts but not surfaced or inspected until the
reveal command.

## The prompt amendment (already committed as `691c653`)

The reviewer's grammar-accurate replacement landed verbatim; the final
`code_local_v1` code sha is
`17a05a190b3c011b81794c82b741134f40945772cb71ba1ebe7587d29d4f7fba`, and
`93_f`'s three factual claims are corrected as specified. Awaiting
Ken's sign-off at this hash.

## P0 replays — executed, evidence retained

Run on `picome` under the frozen cohort (`p0_rev9_code_cohort.json`,
90 calls, chunks [16, 16, 13, 16, 16, 13]), four fresh-process
conditions at commit `20dc20c`, every command with a valid artifact and
exit 0. A first attempt on the then-dirty worktree was refused by the
comparator (`NOT COMPARABLE: git.dirty`) and discarded — the 94_s
discipline catching its own author, as intended.

| comparison | differing cases |
|---|---|
| original vs original (fresh processes) | **0 / 90** |
| original vs reversed-within-chunk | **0 / 90** |
| original vs singleton | **2 / 90** |
| reversed vs singleton | 2 / 90 |

The singleton differences reproduce the historical microbatch-1 result
exactly (78_s finding 6: +2 legal, +1 node-correct):

- `fork_join:00006:n2` — batched: the handle-substitution failure
  (`count_gt(stable_unique(R-1W9), 6)`, typed failure); singleton: the
  **correct** artifact (`resource`, success, node-correct). Batch
  composition was suppressing a correct answer.
- `math_code:00025:n2` — batched: the invented index guard
  (`at(resource, step_1 % length(resource))`, typed failure);
  singleton: a legal but semantically wrong artifact (value 68).
  Node-incorrect either way; the *failure mode* is batch-dependent.

One refinement over the historical record: 78_s's "reversed" condition
reversed within the 45-request *wave*, changing chunk membership, and
saw 1/90 change. This replay's reversed-within-*chunk* condition (the
92_s §6.2 specification — membership preserved, order changed) produces
**zero** differences. The sensitivity therefore localizes to physical
batch *composition* — which requests share the `model.generate` call —
not to position within a fixed batch. Retained in
`runs/p0-rev9-replay/` (gitignored raw artifacts + logs); the frozen
cohort and this record are the committed evidence.

P0 admits nothing, but the result retro-confirms the experiment's
generation policy: the batched regime changed one case's correctness
and another's failure mode on exactly the population the candidates
will be judged on.
