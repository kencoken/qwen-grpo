## Verdict

Not ready to freeze `92_s` or launch Tranche A yet. The response closes much of the previous review, but several remaining paths could still alter eligibility, execution order, or selection.

### Blocking findings

1. **The A→B state transition is not trustworthy yet.**

   [screen_candidates()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:985) accepts arbitrary JSON as the A reveal. I reproduced a fabricated reveal opening a four-arm B tranche.

   [reveal_tranche()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:1188) also trusts the screening artifact’s own `eligible_contracts`; a self-consistent forged A screening can omit an entire contract and still rederive.

   B must instead rederive A from its screening and run artifacts, then:

   - derive eligibility from that result;
   - enforce the same clean executable commit across A and B;
   - compare B’s unchanged Lookup/Math outputs with A’s audited sentinel;
   - require the currently executing screening/reveal checkout to be clean and at that commit.

2. **Malformed P1 evidence is treated as scientific non-admission.**

   [admit_singleton()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:603) mixes invalid-artifact reasons with legitimate non-admission. [Screening](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:953) then silently eliminates the candidate.

   I reproduced this by making the third invocation claim canonical order: screening continued with `admitted=False`. Wrong order/support, non-fresh processes, provenance drift, or malformed artifacts must stop the tranche. Only genuine generation instability and frozen cost-gate failure should count as valid candidate infeasibility.

3. **Completed selection runs are replaceable.**

   [run_candidate()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:870) overwrites an existing `candidate:mode` completion-index entry. A second complete run can therefore replace the preregistered first run; confirmation later also loses the run-1 association.

   Use append-only, role-specific receipts such as `selection-r1`, `confirmation-r2`, and `composed`, refusing a second completed selection run.

4. **The ordinary reveal command fails after a pruned screen.**

   Non-evaluated arms lack `target`, but the [CLI prints it unconditionally](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:1511). It writes the output, raises `KeyError`, and exits non-zero. This will occur in the normal workflow whenever any arm is screened out.

5. **Contract viability does not apply the complete target.**

   [Contract-state derivation](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:1266) checks Lookup/Math correctness but not their protocol conditions. A correct Lookup result with `generation_hit_token_cap=true` produces `target=false` yet marks the contract `viable`. Viability should require the relevant §4.1 zero-failure conditions too.

6. **The frozen launch order is not preserved.**

   [Launch construction](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:965) collects clean-prefix arms and then appends sentinels. The test fixture consequently emits arm positions `[1, 6, 2]`, rather than registry order `[1, 2, 6]`. Form a launch set, then filter the frozen `arm_order`.

7. **Section 9 interactions remain incomplete.**

   The current [rectangle output](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:1325) reports aggregate arm counts, not the preregistered model×contract and model×prompt difference-in-differences overall and by endpoint × cell × renderer. Freeze the sign convention and emit actual numerators/denominators before outcomes exist.

8. **Device identity still does not match §3.**

   [physical_layout()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/candidates.py:141) omits device, P1 does not bind it, and [measurement validation](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval.py:1216) ignores `measurements.device`. Freeze the CUDA device and one environment fingerprint across P1 arms and full runs.

### What is approved and verified

- `code_local_v1` is approved unchanged at SHA-256  
  `17a05a190b3c011b81794c82b741134f40945772cb71ba1ebe7587d29d4f7fba`.
- The procedural “retained but not surfaced or inspected” interpretation is acceptable.
- Not setting `frozen_candidate=True` is acceptable because the experiment receipt and one-commit rule freeze treatment bytes.
- All 16 support entries regenerated byte-identically; registry SHA-256 is  
  `84b4baa3c40bfe4eb6bf66be5cb0f2c91236a8b3b063b307818068b842fd439b`.
- The retained P0 artifacts were verified on `picome`: all four generation commands exited zero, with comparisons `0/90`, `0/90`, and `2/90` as reported.
- All 563 tests reached passing status under warnings-as-errors. The already documented Linux interpreter teardown segfault remains, so the suite process itself is not a clean-zero run; this is pre-existing and the real P0 commands exited cleanly.

### Recommended close-out

Make one narrowly scoped correction pass covering the findings above, then perform only a changed-lines review plus the corresponding workflow probes. After that:

1. Record D1 ratification and the prompt-hash approval.
2. Freeze `92_s`, the exact executable commit, contract/prompt/registry hashes, and preferably the retained P0 artifact hashes.
3. Keep the worktree clean and logs outside it.
4. Launch Tranche A in the registry order.

Once those checks pass, I would sign off and stop reopening the design with further general audits.