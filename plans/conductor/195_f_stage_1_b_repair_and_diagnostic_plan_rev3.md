# 195_f — B repair-and-diagnostic plan, rev3 (response to 194_s)

Rev3 of the B plan (190_f @52b447b → 193_f @c31d3e6, both preserved
at committed bytes), incorporating the three 194_s corrections. One
flagged point for the reviewer in §4.3 (the `reward_0` identity).
**Draft: nothing is implemented or executed until this revision is
signed.** Scope unchanged: repair (CPU) → review → freeze → smoke →
launch lock → ONE descriptive diagnostic. No GRPO; 191_f stays
paused.

## 1. Scope and non-goals (unchanged from 193_f §1)

Attempt-1 roots/archive immutable; diagnostic descriptive-only and
never promotable; retained support becomes development data at
first inspection; formal v1-domain B seeds preserved untouched.

## 2. The repair and regressions (unchanged from 193_f §2)

`_generate` fix (input_ids + attention_mask from the
`BatchEncoding`; decode sliced at `input_ids.shape[1]`); stub
`BatchEncoding` regression that fails pre-repair; parse/count-path
regression.

## 3. Execution order (194_s correction 1 — smoke authenticates the launched bytes)

1. Implement and test (§2 fix + §4 machinery + archiver); full CPU
   suite under `-W error`, TRUE exit code.
2. **Changed-lines review and repairs** (reviewer pass over
   everything since sign-off).
3. **Freeze the candidate**: commit a candidate note pinning the
   source digest, uv.lock hash, contract hash, and generation-config
   hash.
4. **Smoke EXACTLY those bytes** (same helper, model constructor,
   and generation kwargs as the diagnostic; ≤ 16 completions;
   ≤ 10 min in-loop monotonic deadline; ollama/VRAM preflight; one
   synthetic OOD input; shape/runtime disclosure only). The smoke
   record includes the source digest, contract hash, model/tokenizer
   revision and generation-config hash IT ran under.
5. **Launch lock**: a committed record proving
   `smoked executable == launched executable` — the lock pins the
   same four identities and the diagnostic may run only from the
   lock commit with a clean tree matching them.
6. Run the diagnostic once.

**Any executable change after the smoke returns to review and
requires a newly authorized smoke** — no exceptions.

## 4. The diagnostic (identity/contract as 193_f §4.1, with 194_s corrections 2–3)

### 4.1 Contract and manifest (unchanged from 193_f §4.1)

`B_DIAGNOSTIC_CONTRACT` + self-hashed pre-sampling manifest binding
model/tokenizer revision, chat-template hash, per-observation×prompt
rendered-request hashes, quantization/adapter construction, decoding
parameters, singleton RNG semantics, parser and reward identities,
support/surface pins, budgets, env manifest and source digest.

### 4.2 Seed identity (194_s correction 3 — exact)

- Derivation, exactly:
  `uint64_be( SHA256( utf8(domain ∥ U+001F ∥ key) )[0:8] )`
  with `domain = "stage1-b-diagnostic-v1"`.
- Key material: `B-diag|{observation_id}|{prompt_sha256}|{index}`
  with UNPADDED indices `0 … 255` (frozen).
- The exact **9,216-key diagnostic seed registry** (18 observations
  × 2 prompts × 256 indices) is materialized at the launch lock and
  its canonical digest is pinned there; the driver consumes ONLY
  registered values via fail-closed lookup (missing key refuses),
  and the manifest binds the registry digest.

### 4.3 Estimand populations and count boundary (194_s correction 2)

Support composition, stated: nine Code-pair observations, of which
THREE have distinct payoffs (two favour worker 2, one favours
worker 3) and six are ties.

- `p2`, `p3`, `g8` and the direction summaries are computed ONLY
  over the distinct-payoff pairs (`payoff_w2 != payoff_w3`);
  worker-2-favoured (2 observations) and worker-3-favoured (1
  observation) are reported separately at every aggregation level.
- Tied pairs are reported SEPARATELY (their p2/p3/g8 values are
  descriptive of selection behavior only) and are never described
  as gradient-bearing.
- Parse/valid/action-distribution/reward/zero-variance/diversity
  summaries use ALL 18 observations.
- All group-of-8 quantities are **iid-singleton plug-in
  predictions** — not measurements of batched GRPO groups or of
  actual gradients — and the report says so on every page.
- `E[# distinct levels in 8] = Σ_L [1 − (1 − p_L)^8]` (frozen
  formula).

Count boundary (frozen definitions):

- `parseable` := the completion is UTF-8-encodable and JSON
  decoding succeeds;
- `valid` := the COMPLETE frozen `parse_routing_action` schema
  succeeds (field names, worker-id domain, and length — not merely
  correct length);
- assignments counted over valid draws only; reward for non-valid
  draws is 0; reward for valid draws is the pinned-surface payoff
  of the semantic assignment.

Frozen identities at build AND load:
`0 ≤ valid ≤ parseable ≤ 256`; `Σ assignment counts = valid`;
`Σ reward-level counts = 256`; **`reward_0 == 256 − valid`** (the
194_s identity, adopted as frozen).

Verification note (checked before freezing, 2026-07-27): the
equality presumes no VALID assignment scores 0 on the pinned
surface. Confirmed by direct inspection — the 324-row surface's
payoff distribution is `{1.0: 24, 0.5: 300}`: zero payoff-0 rows,
so every valid draw scores ≥ 0.5 and the 0 level contains exactly
the non-valid draws. The verifier additionally RECOMPUTES all
reward-level counts from raw reparse + rescore (subsuming the
identity), so if any surface row with payoff 0 ever appeared, the
equality check would refuse rather than silently absorb it.

### 4.4 The authenticating verifier (193_f §4.3 + 194_s additions)

Exact 9,216 raw keys; binds `raw_completions_sha256`; reparses
every completion (computing `parseable` and `valid` under the §4.3
definitions and requiring EXACT reproduction of both counts);
positional→semantic conversion; rescores every valid assignment
against the pinned surface; exact equality with every persisted
assignment and reward-level count; the §4.3 identities including
the `reward_0` decomposition; manifest self-hash, rendered-request
hashes, registry digest, and environment binding. The descriptive
report is computed only from verifier-authenticated integers by a
committed executable script.

### 4.5 The diagnostic archiver (194_s correction 3 — explicit scope)

In implementation scope: a success/abort archiver for the
diagnostic root, mirroring the attempt-1 archiver semantics —
unique ATOMIC evidence root
(`plans/conductor/evidence/stage1_b_diagnostic_{first12(manifest_sha)}/`,
staged copy + byte/length/SHA-256 manifest + verification + atomic
rename; refuses a pre-existing destination); **success mode
requires the §4.4 authenticating verifier to pass**; **abort mode
preserves partial raw completions and the run record WITHOUT
trusting a complete artifact**, recording validation errors instead
of raising on them.

### 4.6 Budgets (unchanged from 193_f §4.4)

Smoke ≤ 16 completions / ≤ 10 min; diagnostic 9,216 completions /
≤ 3 h; both deadlines in-loop on the monotonic clock; one attempt
each; staged persistence preserves partial evidence on abort.

## 5. After the run

Verifier-authenticated descriptive report committed with the
archive; handed to development-track planning (191_f resumes);
descriptive prior information only.
