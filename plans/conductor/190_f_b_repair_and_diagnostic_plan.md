# 190_f — B repair-and-diagnostic plan (draft for review)

First draft under the signed-off Route B package (186_s + 187_f +
189_f; Ken signed off 2026-07-26). Scope: exactly 186_s §4 with the
187_f/189_f guards. **Draft — no authority until reviewed; nothing
here runs before its own sign-off.** This plan authorizes, once
signed: the driver fix, its regression, one budgeted reward-blind
GPU smoke, and one descriptive B feasibility diagnostic. It does NOT
authorize GRPO, does not complete attempt 1, and does not restore
any global GO.

## 1. The repair (code)

`stage1_replay._generate` currently passes the object returned by
`tokenizer.apply_chat_template(..., tokenize=True,
return_tensors="pt")` directly to `model.generate` and reads
`enc.shape[1]`. Under the pinned transformers 5.13.0 that object is
a `BatchEncoding`, and the call crashes before the first completion
(185_f §3). The repair is two expressions inside `_generate`:

- `input_ids = enc["input_ids"].to(model.device)` as the generate
  input;
- prompt length from `input_ids.shape[1]`.

Nothing else changes: seeds, contract, request hashing (built on
the `tokenize=False` path), accounting, parsing and artifact logic
are untouched. The legacy `run_replay` and the (never again
executed) `run_amend1_replay` share the fixed loop.

**Regression (CPU, in the suite):** a test drives `_generate` with
the REAL pinned tokenizer's `apply_chat_template` output (a genuine
`BatchEncoding`) and a fake model that (a) asserts it receives a
2-D integer TENSOR, (b) returns a plausible output tensor. It must
fail against the pre-fix code and pass after. A second assertion
pins the prompt-length computation against the tokenizer's actual
input_ids length.

## 2. The reward-blind GPU smoke (budgeted)

Purpose: prove the REAL tokenizer→model→generate path executes,
nothing more.

- Input: one synthetic OOD request assembled from a throwaway
  system string and a throwaway user string (not a support
  observation, not a frozen prompt); nonformal seed from the
  throwaway timing domain.
- **Budget: at most 8 completions**, `max_new_tokens = 128`, one
  model load.
- Disclosure: shape/dtype of the generate output, wall time, and
  whether decoding returned non-empty text. NO routing parse, NO
  reward, NO per-prompt statistics — the outputs are discarded.
- Runs only after the regression passes locally; aborts are
  reported verbatim.

## 3. The B feasibility diagnostic (separately identified, descriptive)

**Status: DESCRIPTIVE.** It supports, at most, the scoped statement
that the retained support shows cold-start action/reward diversity
compatible with nonzero within-group routing advantage (186_s §4);
it makes no claim-bearing assertion. If it is ever upgraded to
claim-bearing, that upgrade is a new reviewed plan with an
AFFIRMATIVE lower-bound/group-level feasibility criterion frozen in
advance (189_f §2.4) — and, because this diagnostic exposes the
support, that future plan needs disjoint support/populations and
fresh seeds regardless.

Identity (all new; the formal attempt-1 identities are never
reused):

- Run root: `runs/stage1-b-diagnostic-dev1` (atomic claim).
- Tag: `stage1-b-diagnostic-dev1`.
- Seed domain: `stage1-b-diagnostic-dev1` (fresh; derivation =
  the frozen §9.3 recipe over the new domain). The original formal
  B seeds (`stage1-validation-v1` domain) are PRESERVED untouched.
- Source identity: the env manifest + source digest at the
  diagnostic's own lock commit, persisted in the run root.

Retained frozen elements (unchanged from the formal contract,
per 186_s §4): model `Qwen/Qwen2.5-3B-Instruct@aa8e7253…`, fresh
zero-B LoRA over the NF4 base, both pinned prompts, the 18-obs
support, the pinned surface pair table, singleton generation with
one global-RNG reset per draw, complete accounting with malformed
completions kept in the denominator.

**Budget: 256 completions × 18 observations × 2 prompts = 9,216
draws (~50 min GPU), plus the §2 smoke's 8. No repeats, no
adaptive extension.**

Report, per (prompt × observation) with renderer/latent/cell
rollups (schema frozen at this plan's sign-off):

1. valid and correct-length action rate;
2. worker-2 and worker-3 selection probabilities (the pair-table
   variants), with CP intervals as DESCRIPTIVE bands;
3. `P(a group of 8 contains both payoff-distinct choices)` — the
   frozen inclusion-exclusion `g(p2, p3)` at group size 8,
   evaluated at the observed point rates;
4. predicted zero-variance-group fraction (all-8-same-reward-level
   probability under the observed per-level rates);
5. expected reward-level diversity (expected number of distinct
   reward levels per group of 8).

Persistence: raw completions + integer count artifact + report
JSON, content-addressed under the diagnostic tag; archived to
`plans/conductor/evidence/` after the run; run record with abort
contract as in the formal drivers.

**Exposure consequence, restated:** once this report is inspected,
the retained support is development data (186_s §4). That is
accepted — it follows the recorded Route B choice.

## 4. Order of operations and review gates

1. Reviewer signs off on this plan (and 191_f if reviewed
   together).
2. Implement §1 fix + regression; full suite under `-W error`
   (true exit); commit.
3. Run the §2 smoke; disclose verbatim; commit the disclosure.
4. Lock the diagnostic (source digest + budget + report schema
   pinned in a short lock note), run §3, archive, commit.
5. Review the report → it feeds the development-track priors
   (191_f), nothing else.
