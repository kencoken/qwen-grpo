# 190_f — B repair-and-diagnostic plan (draft for review)

The narrow plan required by 186_s §4/§9 under the signed Route-B
disposition (187_f, 189_f). **Draft: nothing here is implemented or
executed until this plan is reviewed and signed.** It authorizes,
once signed, exactly three activities in order — the driver repair
(CPU), one budgeted reward-blind GPU smoke, and one separately
identified descriptive B diagnostic — and nothing else. No GRPO run,
no development-track activity, no claim.

## 1. Scope and non-goals

- The attempt-1 roots and archive remain immutable; nothing here
  touches them, resumes attempt 1, or feeds its missing aggregate.
- The diagnostic is **descriptive only**: it reports cold-start
  action/reward-diversity quantities on the retained support and
  makes NO feasibility claim. If a claim-bearing version is ever
  wanted, it requires its own plan with an affirmative
  lower-bound/group-level criterion frozen in advance (186_s §4);
  the descriptive report here cannot be promoted afterward.
- Exposure consequence, accepted in advance (186_s §4, 187_f): once
  diagnostic outcomes on the retained support are inspected, that
  support is development data. The original formal B seeds (v1
  domain, never exposed) are preserved untouched for any future
  confirmatory design, which would nevertheless require disjoint
  support/populations and fresh seeds.

## 2. The repair (code; CPU-verifiable)

**Defect** (185_f §3): under transformers 5.13.0,
`apply_chat_template(..., tokenize=True, return_tensors="pt")`
returns a `BatchEncoding`; `stage1_replay._generate` treats it as a
bare input-ids tensor (`model.generate(enc, …)`, `enc.shape[1]`).

**Fix** (exact, in `_generate`; shared by the legacy and amended
drivers):

```python
enc = tokenizer.apply_chat_template(
    messages[key], tokenize=True, return_tensors="pt",
    add_generation_prompt=True).to(model.device)
input_ids = enc["input_ids"]
attention_mask = enc["attention_mask"]
...
out = model.generate(input_ids, attention_mask=attention_mask, ...)
text = tokenizer.decode(out[0, input_ids.shape[1]:], ...)
```

The attention mask is passed explicitly (singleton unpadded input —
the inferred mask would be identical; passing it is exact and
silences nothing else). No seed, contract, request-hash, accounting
or parsing logic changes; the rendered-request hashes come from the
`tokenize=False` path, which is untouched.

**Regression tests** (CPU, in the `-W error` suite):

1. `_generate` driven with a stub tokenizer whose
   `apply_chat_template(tokenize=True, return_tensors="pt")` returns
   a REAL `transformers.BatchEncoding` holding torch tensors (the
   actual 5.x return shape), and a stub model that records its
   `generate` arguments: the test asserts `generate` receives a
   TENSOR `input_ids` plus the mask, and that decode slices at the
   prompt length. This test FAILS against the pre-repair code.
2. The stub model returns a fixed token sequence; the parse/count
   path is asserted unchanged (k2/k3/n accounting identical to the
   existing fixtures).

## 3. Reward-blind GPU smoke (budgeted)

One engineering probe that the REAL tokenizer → model → generate →
decode path executes end to end. Frozen parameters:

- Input: ONE synthetic, schema-shaped OOD user message fabricated
  for this smoke (never a retained-support observation — no support
  outcome is exposed); both frozen system prompts.
- Budget: **at most 16 completions total** (2 prompts × 8), 128
  max_new_tokens each, singleton generation; wall-time abort at
  **10 minutes**; one attempt.
- Seeds: throwaway domain `throwaway-b-smoke-v1`; never a frozen
  seed.
- Disclosure: ONLY shape/runtime validity — per-call tensor shapes,
  wall time, VRAM peak, and completion/exception status. Completions
  are NOT parsed, NOT scored, NOT persisted; no routing or reward
  outcome exists. The smoke record (a short JSON block in the
  execution response doc) contains only those engineering fields.
- Gate: the diagnostic may not launch unless the smoke completes
  within budget with no exception.

## 4. The descriptive B diagnostic (separately identified)

**Identity (all NEW; attempt-1 identities are never reused):**

- Tag: `stage1-b-diagnostic-v1`; run root: `runs/stage1-b-diagnostic`
  (atomic claim; any pre-existing path refuses); one attempt.
- Seed domain: `stage1-b-diagnostic-v1` (fresh), key material
  `B-diag|{observation_id}|{prompt_sha256}|{raw_index}`, derivation
  = the frozen 8-byte SHA-256 recipe. The formal v1-domain B seeds
  are not consumed, derived, or logged.
- Provenance: a diagnostic manifest persisted BEFORE sampling —
  environment manifest (validated, numpy/scipy included), source
  digest, model id + revision `aa8e7253…`, both prompt hashes,
  support declaration `6df4c42b…`, surface manifest `221a04d5…`,
  the seed recipe string, the budget literals, and the manifest's
  self-hash; the artifact binds the manifest hash and the env
  identity. No amend1 execution bundle is involved (that machinery
  belongs to attempt 1).

**Retained frozen elements** (186_s §4 default, unchanged): model +
revision, NF4 base + fresh zero-B LoRA + k-bit preparation, both
candidate prompts, the 18-observation retained support, the pinned
surface, singleton generation with global RNG reset per draw,
complete accounting (malformed completions stay in the
denominator).

**Sampling budget (frozen):** 256 completions per (observation,
prompt) = **9,216 total**; wall-time abort at **3 hours** (≈3.5× the
~50-minute estimate); staged persistence (raw completions + integer
count artifact) with an aborted-run record on any failure.

**Persisted sufficient statistics** (integers only, per
(observation, prompt)): n = 256; parseable count; correct-length
(valid-action) count; per-assignment counts over the observation's
full 4^S action set (sparse map assignment→count, which subsumes
k2/k3); reward-level counts over the frozen levels {0, 0.5, 1}
(reward = 0 for malformed/invalid per the frozen boundary rule,
else the pinned-surface payoff of the parsed assignment — computed
offline from the cached surface, no worker executes).

**Derived descriptive report** (recomputed from the integers at
load; group size 8 = the frozen Stage-2 group size, all analytic
under the iid singleton draw model):

- valid and correct-length action rates, by prompt × renderer ×
  observation;
- worker-2 / worker-3 selection probabilities on the payoff-distinct
  pairs (p̂2, p̂3), where defined;
- P(a group of 8 contains both payoff-distinct choices) =
  `g_direct_gradient(p̂2, p̂3)` — the frozen inclusion–exclusion
  surface;
- predicted zero-variance-group fraction = Σ_L p̂_L⁸ over the
  empirical reward-level distribution;
- expected reward-level diversity = E[# distinct reward levels in a
  group of 8], analytic from the same p̂_L;
- aggregation: per observation×prompt rows, plus renderer-, latent-,
  cell- and prompt-level means under the frozen
  renderer→latent→cell weighting.

No pass/fail evaluation is computed or reported. The report explicitly
carries the label: *descriptive; authorizes nothing; support is
development data from first inspection*.

## 5. Execution order and verification

1. Review and sign-off of THIS plan (no code before sign-off).
2. Implement the §2 fix + regression tests; full CPU suite under
   `-W error` with TRUE exit code; commit with response doc.
3. Run the §3 smoke (GPU, ≤16 completions, ≤10 min); commit its
   engineering record. Abort here aborts the plan back to review.
4. Run the §4 diagnostic once (GPU, 9,216 completions, ≤3 h);
   persist raw + integer artifact + manifest; commit the descriptive
   report with the artifact hashes and the committed reporting
   script (executable, read-only, 189_f-style).
5. Hand the report to the development-track planning (which remains
   a separate, later plan — not authorized here).

## 6. Budget summary (frozen literals)

| item | budget |
|---|---|
| smoke completions | ≤ 16 |
| smoke wall time | ≤ 10 min |
| diagnostic completions | 9,216 (256 × 18 × 2) |
| diagnostic wall time | ≤ 3 h |
| attempts | 1 each; aborts recorded, never silently retried |
