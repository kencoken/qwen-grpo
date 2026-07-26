# 196_f — B repair-and-diagnostic implementation (195_f §3 step 1)

Step 1 of the signed 195_f execution order: implement and test.
**No GPU work has run**; the sequence ahead is unchanged —
changed-lines review (step 2) → candidate freeze (step 3) → smoke of
exactly those bytes (step 4) → launch lock (step 5) → the one-shot
diagnostic (step 6). All completions in the tests are synthetic; no
retained-support outcome exists.

## 1. The repair (`stage1_replay.py`)

`_generate` now consumes the `BatchEncoding`: `input_ids` and
`attention_mask` are extracted and passed to `model.generate`
explicitly; decode slices at `input_ids.shape[1]`. The frozen
decoding parameters moved to a single shared literal
`GENERATION_KWARGS` — the formal replay, the smoke, and the
diagnostic use it verbatim (192_s change 4's "same kwargs" is now
true by construction). 195_f additions to the same helper:
`n_completions` (the smoke runs the SAME code at a smaller count),
`deadline_seconds` (in-loop monotonic wall-time abort, checked every
draw), `on_block_complete` (staged-persistence callback per
observation×prompt block).

Regressions: a stub tokenizer returning a REAL
`transformers.BatchEncoding` of torch tensors drives `_generate`
against a stub model that asserts it receives a 2-D integer TENSOR
plus the mask and exactly the shared kwargs — this assertion fails
against the pre-repair code; the decode-slice and parse/count path
are asserted unchanged (fixed-token counting to k2), and the
deadline and block-callback behaviors are pinned.

## 2. The diagnostic module (`stage1_b_diagnostic.py`, tracked)

- **Contract/manifest (§4.1)**: `B_DIAGNOSTIC_CONTRACT` mirrors
  `REPLAY_CONTRACT` and adds tokenizer revision, RNG semantics, the
  exact seed recipe string, parser/parseable/valid/reward
  definitions, and the frozen budget literals. The self-hashed
  pre-sampling manifest binds env identity, source digest,
  chat-template hash, per-observation×prompt rendered-request
  hashes, the generation-config hash, and the seed-registry digest;
  `validate_diagnostic_manifest` refuses tampering including a
  rehashed manifest with a modified contract.
- **Seeds (§4.2)**: `diagnostic_seed` = the exact
  `uint64_be(SHA256(utf8(domain ␟ key))[0:8])` formula (pinned by
  test against a manual recomputation), unpadded indices, and the
  exact 9,216-key registry with canonical digest; the driver
  consumes ONLY registered values via fail-closed lookup.
- **Counting boundary (§4.3)**: `count_from_raw` is THE single
  counting function (driver and verifier both run it on the same
  raw bytes): `parseable` = UTF-8 + `json.loads`; `valid` = the
  complete frozen `parse_routing_action` schema; assignments over
  valid draws; reward levels {0, 0.5, 1} with non-valid → 0 and
  valid → the pinned-surface payoff (a payoff outside {0.5, 1.0}
  refuses — the ladder property verified in 195_f). All frozen
  identities enforced at build AND load, including
  `reward_0 == 256 − valid`.
- **Verifier (§4.4)**: exact 9,216 raw keys,
  `raw_completions_sha256` binding, full reparse reproducing both
  counts, semantic conversion + rescore, exact equality with every
  persisted count, manifest/registry/environment bindings,
  regenerated rendered-request hashes.
- **Report (§4.2/4.3)**: per-(observation×prompt) rows first, then
  the frozen renderer→latent→equal-cell aggregation; `p2`/`p3`
  denominators are all 256 draws; `g8` only for distinct-payoff
  populations (w2-favoured and w3-favoured separately); tied pairs
  are their own population with selection rates only (no `g8`);
  zero-variance `Σ p_L⁸` and diversity `Σ [1 − (1 − p_L)⁸]` pinned
  by test; every report carries the descriptive/plug-in label.
- **Smoke (§3)**: same helper, same constructor, same kwargs; one
  synthetic OOD input + both frozen system prompts; ≤ 16
  completions; 10-minute in-loop deadline; VRAM preflight
  (≥ 8 GiB free); the record carries source digest, contract hash,
  model/tokenizer revision, and generation-config hash — the four
  identities the launch lock must match. Outputs discarded.
- **Driver (§4)**: preflight → manifest/env/record persisted BEFORE
  model work → shared helper with registered seeds, 3-hour in-loop
  deadline, staged partial-raw flushes per block → integer artifact
  → authenticating verification → complete record; aborts preserve
  the partial raw file and the aborted record (tested end-to-end
  with a scripted model, including root-claim refusal on rerun).
- **Archiver (§4.5)**: staged copy + byte/SHA-256 manifest +
  verification + atomic rename; success requires the exact file
  set, a complete record, and the authenticating verifier; abort
  preserves whatever exists (partial raw included) without trusting
  anything, recording validation errors. Both modes tested;
  destinations immutable.
- **CLI**: `python -m tasks.conductor.stage1_b_diagnostic
  smoke|run|report|archive --mode success|abort`.

## 3. Verification

- New tests: 11 (regression, seed formula/registry, manifest,
  counting identities, verifier round-trip + refusals, report
  estimands/populations, smoke record, driver end-to-end, abort
  preservation, archiver modes).
- Full CPU suite: **913 passed under `-W error`, TRUE process
  exit 0.**
- Current source digest (input to the step-3 candidate freeze after
  the changed-lines review):
  `228da215e0c2fc57c688a122e85428380258336263aa0ea9876f0bc2d590e84d`

## 4. Boundary

Awaiting the step-2 changed-lines review. Any repair it produces
regenerates the candidate digest; the smoke then runs exactly the
frozen bytes and the launch lock proves smoked == launched before
the diagnostic samples the retained support.
