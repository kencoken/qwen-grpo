# 185_f — Infrastructure abort: B replay driver defect (record + recovery options)

The amended tranche executed under lock 184_f @2aa2332. The CPU side
COMPLETED cleanly; the GPU B replay ABORTED one second after
claiming its root, on the first generation call, before any
completion was produced. Per 158_s §11 / 183_f §7 the partial
evidence was archived (`--mode abort`) BEFORE this record and before
any recovery decision. No frozen threshold, seed or criterion is
touched by this record.

## 1. Execution timeline (all under bundle `9b5f1ab85f26…`)

1. Lock committed @2aa2332; clean tree; both roots absent; GPU idle.
2. `tranche`: all gates passed — v1 archive verified, bundle derived
   and validated, registry canonical, deterministic set EXACT, live
   benchmark 1.136291 s/outer (1.19× the frozen literal, inside the
   inclusive sanity band; frozen 19,031 s deadline controlled).
   **Complete in 9,672 s (2.69 h)** vs the 12 h gate.
3. `replay`: `persisted_context` gates passed (complete CPU root,
   exact pre-aggregate file set, persisted bundle == rebuilt
   authoritative bundle); root claimed; env/bundle/replay manifests
   and `running` record persisted; model built; **first generate
   call raised** → abort record written (`wall_seconds: 1`).
4. `archive --mode abort`:
   `plans/conductor/evidence/stage1_pre_ce1_amend1_9b5f1ab85f26/`,
   20 files, byte-verified, `validation_errors: []`, manifest
   SHA-256
   `114cf207dd98e8578b814602e109a5261ce2ddf1454d5ace185dd388380d31c1`.

## 2. CPU results now on record (formal verdict PENDING — the
aggregate requires verified B evidence and none exists)

- **A**: all 72 cells persisted; every gated cell far above the 0.80
  criterion on inspection (formal evaluation at the aggregate).
- **C**: 48 paths / 120 marginals persisted and reloaded through the
  exact-set gates.
- **D** (error_count / 5,000; ceiling = alpha + max(0.005, 0.25·alpha)
  on the Wilson upper):
  | scenario | errors | rate | nominal α | ceiling | Wilson UB | state |
  |---|---|---|---|---|---|---|
  | D1 ordinary null | 12 | 0.24% | 1.67% | 2.08% | 0.35% | inside |
  | D2 fork null (100,500) | 15 | 0.30% | 1.67% | 2.08% | 0.43% | inside |
  | D3 equiv +0.10 | 81 | 1.62% | 2.5% | 3.125% | 1.93% | inside |
  | D4 equiv −0.10 | 101 | 2.02% | 2.5% | 3.125% | 2.37% | inside |
  | **D5 pilot unequal** | **157** | **3.14%** | 2.5% | **3.125%** | **3.57%** | **EXCEEDS** |
  | D6 persist structural | 208 | 4.16% | 5% | 6.25% | 4.64% | inside |
  | D7 persist row-dispersed | 199 | 3.98% | 5% | 6.25% | 4.45% | inside |
  | D8 persist fork θ=0.01 | 0 | 0% | 5% | 6.25% | ~0.06% | inside |
- **D8 branch support**: zero-branch 2,782 @look100 and 257
  @look500 vs registered predictions ≈2,700 and ≈245 — both
  branches present at both looks; the prediction was essentially
  exact. D6–D8 confirm the amended statistic's calibration,
  including the row-dispersed case the v1 envelope failed (D7 at
  3.98% vs v1's 0/10,000 structural blindness).
- **The registered "all eight inside ceilings" prediction FAILED at
  D5**: 157 false-passes where the ceiling tolerates ≈139. This is
  the first-ever measurement of D5 at production replicates (v1
  stopped before D), and it is the same pilot-unequal
  anti-conservatism the v1 agreement diagnostic flagged. If this
  artifact stands, `aggregate_amend1_verdict` returns
  `scientific_stop` — terminal for unit 3 under the frozen table.

## 3. Root cause of the abort (post-hoc diagnostic, CPU-only)

Under the pinned stack (transformers 5.13.0),
`tokenizer.apply_chat_template(msgs, tokenize=True,
return_tensors="pt", add_generation_prompt=True)` returns a
**`BatchEncoding`** (`{input_ids, attention_mask}`), not the bare
input-ids tensor the driver assumes. `_generate` then calls
`model.generate(enc, …)` and `enc.shape[1]`;
`generation/utils.py:2498` does `inputs_tensor.shape[0]` →
`BatchEncoding.__getattr__` raises `AttributeError`. Deterministic,
immediate, environment-wide.

Why it survived review and tests: the generation loop was written in
the v1 era (143_f–155_f) against the transformers-4.x return
convention; v1's B never executed (the tranche stopped at the
agreement gate), the amended replay reuses the same `_generate`, and
the 154_s/169_s abort probes inject `tokenizer=None` with
`_generate` monkeypatched — the defective line is unreachable
without a GPU generate call, which no formal run had ever made.

The fix is two expressions in `stage1_replay._generate`
(`enc["input_ids"]` as the generate input / for the prompt length);
no seed, contract, request hash or accounting logic is involved —
the rendered-request hashes come from the `tokenize=False` path,
which is unaffected.

## 4. Recovery options (reviewed decision — not taken here)

**Option 1 (recommended): fix, relock, re-execute in full.**
Apply the two-expression fix; full suite under `-W error`; issue a
successor erratum (rev5) pinning the regenerated source digest and a
new lock record; relocate the archived-and-superseded run roots so
the atomic claims can proceed; re-execute the complete §11 sequence
under the new bundle. Every A/C/D input is a registered seed through
deterministic PCG64 streams, so the CPU results are expected to
reproduce IDENTICALLY (disclosed expectation, checkable row-for-row
against archive `9b5f1ab85f26`); B runs for the first time. Cost
≈2.7 h CPU + ≈50 min GPU. This yields the complete formal record —
the aggregate, B's first-ever measurement, and a §12 decision made
against finalized evidence. The scientific outcome is already
overwhelmingly determined (D5), but the wind-tunnel's product is the
calibration record itself.

**Option 2: rule §12 directly on the abort archive.** D5's
exceedance alone forces `scientific_stop` under the frozen table,
and B can neither cause nor prevent a scientific failure (158_s §7).
A reviewed decision could cite archive `9b5f1ab85f26…`'s artifact_D
without a formal aggregate (which structurally requires verified B
evidence). Cheaper, but leaves B unmeasured and no
finalized/success-archived record.

The infrastructure abort does not consume the amend-once allowance
(132_s §8.4 governs SCIENTIFIC amendment; 158_s §11 explicitly
provides the abort-then-recovery path). No statistical criterion
would change under either option.
