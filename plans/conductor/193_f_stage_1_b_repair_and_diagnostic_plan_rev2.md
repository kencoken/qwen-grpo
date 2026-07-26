# 193_f — B repair-and-diagnostic plan, rev2 (response to 192_s)

Rev2 of Ken's 190_f (@52b447b, preserved at committed bytes),
incorporating all four 192_s changes. **Draft: nothing is
implemented or executed until this revision is signed.** Once
signed it authorizes exactly, in order: the driver repair (CPU),
one budgeted reward-blind GPU smoke, a changed-lines review +
clean-source lock, and one separately identified descriptive B
diagnostic — nothing else. No GRPO, no development-track activity,
no claim. The development-track launch plan (191_f) is PAUSED until
the fixed B run completes (192_s).

## 1. Scope and non-goals (unchanged from 190_f)

- Attempt-1 roots and archive remain immutable; nothing here
  touches them, resumes attempt 1, or feeds its missing aggregate.
- The diagnostic is **descriptive only** and cannot be promoted to
  claim-bearing afterward; a claim-bearing version would need its
  own plan with an affirmative criterion frozen in advance — and
  disjoint support with fresh seeds, since this diagnostic exposes
  the retained support (development data from first inspection).
- The original formal B seeds (v1 domain, never exposed) are
  preserved untouched.

## 2. The repair (code; CPU-verifiable — unchanged from 190_f)

Fix in `stage1_replay._generate` (shared by legacy and amended
drivers): take `input_ids`/`attention_mask` from the
`BatchEncoding`, pass both to `model.generate` explicitly, slice
the decode at `input_ids.shape[1]`. No seed, contract,
request-hash, accounting or parsing logic changes.

Regression tests (CPU, `-W error` suite): (1) `_generate` driven
with a stub tokenizer returning a REAL `transformers.BatchEncoding`
of torch tensors and a stub model asserting it receives a 2-D
integer tensor plus the mask, with decode sliced at prompt length —
FAILS against pre-repair code; (2) fixed-token stub output asserting
the parse/count path unchanged.

## 3. Reward-blind GPU smoke (192_s change 4 tightened)

- **Same code path as the diagnostic**: the smoke calls the SAME
  repaired generation helper, the SAME model constructor
  (`_build_replay_model`), and the SAME generation kwargs the
  diagnostic uses — no smoke-only shortcut.
- Input: ONE synthetic, schema-shaped OOD user message (never a
  retained-support observation); both frozen system prompts.
- Budget: ≤ 16 completions (2 × 8), 128 max_new_tokens, singleton;
  **wall-time abort at 10 minutes enforced INSIDE the generation
  loop on the monotonic clock** (checked every draw); one attempt.
- **Ollama/free-VRAM preflight** before model load: `nvidia-smi`
  free memory recorded; if ollama (or anything) holds VRAM such
  that free < 8 GiB, stop and resolve first (`systemctl stop
  ollama` per the Stage-0 runbook) — the preflight result is part
  of the smoke record.
- Disclosure: ONLY shape/runtime validity — per-call tensor shapes,
  wall time, VRAM peak, completion/exception status. Completions
  are not parsed, not scored, not persisted.
- Gate: the diagnostic may not launch unless the smoke completes
  within budget with no exception.

## 4. The descriptive B diagnostic (192_s changes 1–3 incorporated)

### 4.1 Identity and the COMPLETE bound contract (192_s change 1)

All identities NEW: tag `stage1-b-diagnostic-v1`, run root
`runs/stage1-b-diagnostic` (atomic claim, one attempt), seed domain
`stage1-b-diagnostic-v1` with key material
`B-diag|{observation_id}|{prompt_sha256}|{raw_index}` under the
frozen 8-byte SHA-256 recipe.

The diagnostic reuses the EXISTING contract/manifest machinery as a
diagnostic variant (`B_DIAGNOSTIC_CONTRACT` mirroring
`REPLAY_CONTRACT`; `build_diagnostic_manifest` mirroring
`build_replay_manifest`), binding — beyond model id/revision and
the two prompt hashes — ALL of:

- tokenizer revision (pinned = the model revision) and the
  **chat-template hash** (SHA-256 of the tokenizer's chat-template
  bytes at load);
- **per-observation×prompt rendered-request hashes**, regenerated
  from the pinned tokenizer exactly as in the formal replay
  manifest;
- the full quantization/adapter construction literals (NF4,
  double-quant, bfloat16 compute, sdpa, fresh zero-B LoRA
  r16/α32/d0.05 on the frozen target modules, k-bit preparation);
- decoding parameters (do_sample, temperature 1.0, top-p/top-k
  disabled, max_new_tokens 128, eos stop, pad = eos);
- singleton batching and RNG semantics (generation_batch = 1;
  global CPU+CUDA RNG reset per draw from the registered
  diagnostic seed; the seed-recipe string);
- parser and reward identities: the frozen parser entrypoints
  (`parse_routing_action` + `positional_to_semantic`, under the
  committed source digest), the reward levels {0, 0.5, 1}, the
  malformed/invalid → reward-0 rule, and the pinned surface
  manifest hash `221a04d5…` + support declaration `6df4c42b…`;
- the budget literals (§4.4) and the env manifest / source digest
  of the lock commit.

The manifest is persisted BEFORE sampling and self-hashed; the
artifact binds the manifest hash and the environment identity.

### 4.2 Frozen estimands (192_s change 3)

For each pair-bearing observation, the pair table fixes the two
EXACT otherwise-identical family-correct assignments (w2-variant,
w3-variant) and the favoured direction (from the pinned payoffs).
Then, per (observation × prompt):

- `p2 := count(semantic assignment == exact w2-variant) / 256`
- `p3 := count(semantic assignment == exact w3-variant) / 256`

— denominators are ALL 256 draws (never conditional on valid;
never generic worker marginals). All nonlinear quantities are
computed per (observation × prompt) FIRST and only then aggregated
renderer → latent → equal-cell (the frozen weighting):

- `g8 := g_direct_gradient(p2, p3)` (frozen inclusion–exclusion,
  group size 8);
- zero-variance-group fraction `:= Σ_L p_L⁸` over the empirical
  reward-level distribution `p_L` (all 256 draws; non-valid draws
  are reward-0 members of the distribution);
- expected reward-level diversity `:= E[# distinct levels in 8]`,
  analytic from the same `p_L`.

Reporting separates the **worker-2-favoured** and
**worker-3-favoured** directions at every aggregation level (as in
the frozen §8.4B summary), plus the descriptive rates: parseable,
valid (correct-length), and per-assignment frequencies.

### 4.3 Persisted statistics and the authenticating verifier (192_s change 2)

Persisted per (observation × prompt), integers only: `n = 256`;
`parseable`; `valid`; the sparse `assignment → count` map over the
observation's 4^S semantic space (counted over VALID draws only);
reward-level counts over {0, 0.5, 1}.

**Frozen count identities** (enforced at build AND load):

- `0 ≤ valid ≤ parseable ≤ 256`;
- `Σ assignment counts = valid`;
- `Σ reward-level counts = 256`;
- reward-0 count ≥ (256 − valid) — malformed/invalid completions
  stay in the denominator with reward zero.

**Consuming verifier** (read-only; the only formal boundary for the
report): requires the exact **9,216 raw completion keys**; REPARSES
every completion with the frozen parser; applies
positional→semantic conversion; RESCORES every valid assignment
against the pinned surface; and requires EXACT equality with every
persisted assignment count and reward-level count, plus the
identities above, the manifest self-hash, the rendered-request
hashes, and the artifact's manifest/environment binding. The
descriptive report is computed only from verifier-authenticated
integers, by a committed executable script (189_f-style), and
carries the label: *descriptive; authorizes nothing; support is
development data from first inspection*.

### 4.4 Budgets (frozen)

| item | budget |
|---|---|
| smoke completions | ≤ 16 |
| smoke wall time | ≤ 10 min, in-loop, monotonic |
| diagnostic completions | 9,216 (256 × 18 × 2), one attempt |
| diagnostic wall time | ≤ 3 h, **in-loop, monotonic, checked every draw** |
| abort behavior | staged persistence — partial raw completions + aborted record are PRESERVED and archived abort-mode |

## 5. Execution order (192_s change 4: implementation lock added)

1. Review and sign THIS revision (no code before sign-off).
2. Implement §2 + §4 machinery (contract, manifest, driver,
   verifier, report script) + regressions; full CPU suite under
   `-W error` with TRUE exit; commit with response doc.
3. Run the §3 smoke (preflight, gate); commit its engineering
   record verbatim.
4. **Changed-lines review of everything since this sign-off, then a
   clean-source LOCK note** pinning the source digest, uv.lock, the
   budget literals, and the report schema — committed BEFORE any
   retained-support sampling.
5. Run the §4 diagnostic once from the lock commit (preflight
   again); persist raw + integer artifact + manifest; archive
   (success or abort mode) to `plans/conductor/evidence/`; commit
   the verifier-authenticated descriptive report.
6. Hand the report to development-track planning (191_f, which
   resumes only then). B output is descriptive prior information —
   nothing more.
