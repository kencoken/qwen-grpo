# 202_f — B diagnostic execution record (195_f §3 steps 3–6, complete)

The full approved sequence executed 2026-07-27 with zero deviations.
Every artifact referenced here is committed; the retained support is
now DEVELOPMENT DATA (first inspection has occurred). The report is
descriptive, iid-singleton plug-in prediction only; it authorizes
nothing.

## 1. Sequence and identities

1. **Freeze** (201_f @f537454): source `105d8c0e…`, uv.lock
   `f5486ec4…`, contract `1e2f63fc…`, generation-config `1feb7605…`,
   model/tokenizer revision `aa8e7253…`.
2. **Smoke** (@2be0f3b): complete, 16/16 non-empty, 7.2 s wall,
   VRAM peak 3,157 MiB, prompt shapes 666/144 tokens, identities ==
   the freeze.
3. **Launch lock** (@a551fde, `1303106e…`): binds the smoke record
   bytes, the frozen identities, and the materialized 9,216-key
   diagnostic seed-registry digest `66dd41bc…`; consumer-side
   validation passed (smoked == locked == launched).
4. **Diagnostic run**: one shot, lock re-validated at the consuming
   boundary; **complete in 4,150 s (69 min)** vs the 3 h in-loop
   deadline; manifest `973e8adc…`, raw completions `afb9d8dc…`,
   artifact `19252ed7…`; the driver's in-line authenticating
   verification (full 9,216-key reparse + rescore + exact count
   equality + provenance rederivation) passed before `complete` was
   written.
5. **Report** (`plans/conductor/b_diagnostic_report.json`):
   regenerated through the full verifier by the committed CLI.
6. **Archive** (success mode, verifier-gated):
   `plans/conductor/evidence/stage1_b_diagnostic_973e8adc316e/`,
   evidence manifest `ea9dfbd2…`, zero validation errors.

## 2. Headline descriptive results (equal-cell aggregates)

Support composition confirmed: 18 observations; 9 Code-pair
observations, 3 with distinct payoffs (2 w2-favoured, 1
w3-favoured), 6 ties — exactly the 194_s statement.

| quantity | few-shot | schema-only |
|---|---|---|
| parse rate (all 18) | 0.9998 | 0.9996 |
| valid rate (all 18) | 0.9974 | 0.5204 |
| zero-variance-group fraction | 0.797 | 0.093 |
| expected reward-level diversity | 1.20 | 2.08 |
| w2-favoured: p2 / p3 / g8 | 0.008 / 0.336 / 0.054 | 0.000 / 0.057 / 0.000 |
| w3-favoured: p2 / p3 / g8 | 0.063 / 0.004 / 0.011 | 0.008 / 0.012 / 0.005 |
| tied pairs: p2 / p3 | 0.119 / 0.109 | 0.017 / 0.020 |

## 3. Reading (descriptive only — development priors for 191_f)

- **The two prompts trade validity against reward diversity.**
  Few-shot: near-perfect validity but ~80% of groups of 8 are
  predicted zero-variance (no within-group gradient). Schema-only:
  validity collapses to ~52%, which itself creates reward variance —
  ~91% of groups carry signal, but much of it is the FORMAT contrast
  (0 vs 0.5), not routing.
- **Direction-bearing sampling is thin at cold start.** On the three
  distinct-payoff pairs, the predicted probability that a group of 8
  contains both payoff-distinct choices is ~1–5% (few-shot) and
  ~0–0.5% (schema-only). The direct w2/w3 routing gradient is RARE
  under singleton cold-start sampling.
- **Cold-start preferences run AGAINST the payoff direction on both
  distinct-pair cells** (few-shot: picks w3 where w2 is favoured,
  p3 = 0.336 vs p2 = 0.008; picks w2 where w3 is favoured,
  p2 = 0.063 vs p3 = 0.004). There is headroom for routing learning
  — and a risk that early gradient mostly reinforces format/validity
  rather than correcting direction.
- These are plug-in predictions from singleton draws, not batched
  GRPO measurements; the development pilot observes the real thing.

## 4. Boundary

Per 186_s/187_f/189_f: this diagnostic completes the B repair track.
No claim is made or authorized; the support is development data;
any future confirmatory B design needs disjoint support and fresh
seeds. Next: resume the development-track launch plan (191_f) with
these priors, under its 188_s/189_f binding guards.
