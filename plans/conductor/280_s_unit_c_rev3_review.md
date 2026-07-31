## Verdict

Rev3 closes the substantive Q2 and reporting defects. One final sizing correction is required before launch; no further broad review should be necessary.

### P1 — The cap allocates the full ten hours to training

The policy at [`unit_c_sample.py:155`](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:155) floors whole epochs against the full ten-hour ceiling. The governing charter requires that ceiling to include:

- time already consumed across engineering resumes;
- the measured finalization reserve;
- evaluation/checkpoint/trace/archive overhead.

As written, the likely capped branch can allocate essentially all ten hours to rollout generation and leave no compliant finalization window.

Freeze the prospective calculation as:

```text
available_generation_seconds =
    10 hours
    - cumulative time already consumed
    - measured finalization reserve
    - any frozen non-rollout overhead not included in the epoch rate

capped_epochs =
    floor(available_generation_seconds / measured whole-epoch duration)
```

If `capped_epochs <= 0`, stop for a reviewed amendment. The capped run must remain explicitly under-target, with claims based on achieved projected/observed exposure rather than the nominal target of 100.

The numerical rate and reserve may arrive from later smokes; the formula and branch semantics should be frozen now.

### P2 — Bind the complete LoRA key set

The verifier now rejects empty maps, but a one-key map containing `lora` still passes. The validated construction has:

- **504 LoRA keys**
- key-set digest
  `e44ecb9caf0be396aaaceae6802dbaab9209677103ba263c89ca9a7ea65f6215`

Bind that expected key-set digest—or an equivalent exact manifest—in the configuration and verify both maps against it.

### Correctly closed

- Crossed-wrong Q2 selections now fail both directions.
- Each direction requires its intended specialist across at least two latents.
- Q2 statistics remain composite-only.
- The report refuses truncated/noncanonical schedules.
- Renderer/subtype strata now include C2, ModelAcc, contrast and latent information.
- Integer sizing derivation is correct and persisted.
- Stale scientific-question wording is corrected.
- Exact schedule remains 785 groups / 6,280 completions.
- All recorded hashes reproduce.
- **1,002 tests passed** under warnings-as-errors.
- Worktree and diff checks are clean.

After the cap correction, exact adapter-key binding, and regenerated identities, I would approve Unit C for launch following only a mechanical hash/test check.