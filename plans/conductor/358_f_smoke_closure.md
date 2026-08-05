# 358_f — Beta-smoke CLOSURE (execution signed off; corrected disclosure + ledger commit)

Execution sign-off received. This closure commit performs the
reviewer's four steps in order: (1) the corrected
prediction-disclosure wording (an ERRATUM to 357_f §2 — the
committed report is not edited); (2) ledger entries 21–22
committed UNCHANGED; (3) `verify_smoke_run` re-run at
`df4bf7ad…` against the committed bytes (result recorded below);
(4) Unit L proceeds from the authenticated smoke record and the
39-epoch launch plan.

## 1. ERRATUM to 357_f §2 — the prediction misses, correctly stated

357_f's heading "one band miss" UNDERSTATED the preregistered
prediction misses. Three registered predictions missed, all in
the conservative direction:

| prediction | preregistered | measured/derived |
|---|---|---|
| eval pass | ~7 minutes | **2.38 minutes** (142.955 s) |
| capacity | 33–38 epochs | **41 epochs** |
| smoke cost | 0.50–0.65 GPU-h | **0.3117 GPU-h** |

These are RELATED conservative timing-model misses — one
overpriced eval/timing model propagated through all three — not
three independent failures. They do not invalidate the
registered measured-value formula: the cap arithmetic consumes
only measured values, and the misses left no imprint on any
downstream quantity.

## 2. Ledger entries 21–22, committed unchanged

The worktree diff was verified as a PURE APPEND (54 inserted
lines, zero deletions/modifications): entry 21 = launch
`4738b32b…`, entry 22 = complete closeout `df4bf7ad…` (the new
head). This commit records them byte-for-byte as written by the
run.

## 3. Terminal verification at the committed head

`verify_smoke_run(run_root, ledger_path, expected_head_sha256 =
df4bf7ad…)` re-run from a fresh process against the committed
ledger bytes: **PASS** (recorded in §5's command transcript
note; the same verifier that passed in-run pre-closeout and on
the completed head).

## 4. The binding implication carried to Unit L (per sign-off)

- 39-epoch projected total: **9.4029 h** = (39 × 827.157 s
  epoch) + 1,443.757 s frozen non-rollout overhead + 147.485 s
  measured finalization reserve.
- Headroom against the 10 h operational ceiling: **≈0.597 h**
  (35.8 minutes).
- Capacity 41 epochs, but **launch stays capped at the nominal
  39 — no opportunistic extra training** (branch
  `no_extra_training`).
- Peak reserved VRAM 6,652 MiB.
- Scope: this establishes COMPUTE AND RUNTIME FEASIBILITY ONLY —
  no evidence about routing learning exists yet.

## 5. State after closure

Ledger head `df4bf7ad…` (22 entries verify, committed); envelope
3.5059 / 56.4941; final 1.0 reserve. Unit L consumes the
authenticated smoke record (`smoke_record.json` sha
`a9d6f55b…`, bound to closeout `df4bf7ad…` through the verified
chain) and the 39-epoch launch plan through
`derive_cap_inputs`/`derive_launch_plan` at the P0LaunchFreeze,
with the registered carry-forwards: final-reserve ledger-entry
cross-check vs pinned reserve record `e13cf4d3…` + duplicate
rejection; per-slot seed realization binding at
P0ExecutionIdentity; the four deferred launch-admission
obligations from Unit 5.
