Unit C2 is valid and should be accepted. I found no blocking discrepancy.

### Integrity

- Both live and committed archives independently verify as `PASS`.
- All committed files exactly match the ledger-bound terminal inventory.
- Ledger head is the complete closeout `2bf50c1e…`; all 17 entries verify.
- Exact schedule: 785 groups and 6,280 completions.
- 6,242 valid completions plus 38 correctly recorded parser-invalid completions.
- The persisted 504-key LoRA maps are identical before and after execution.
- Runtime was 1.0142 GPU-h, below the 1.25-hour ceiling.
- Full suite: 1009 tests pass under warnings-as-errors.

### Scientific result

Q1 passes in every registered cell:

| Cell | Counted/draws | Distinct latents |
|---|---:|---:|
| `code_atomic` | 13/30 | 2 |
| `fork_join` | 34/195 | 5 |
| `math_code` | 13/195 | 7 |

Every renderer contributes counted groups. `code_atomic` has good repeated exposure but exactly the minimum two-latent breadth, which is worth retaining as a limitation.

Both registered Q2 marginal-support gates pass:

- `fork_join → w2`: 73 selections across 14 latents.
- `math_code → w3`: 108 selections across 7 latents.

However, their starting conditions differ materially:

- Fork/join already has 152 eligible completions, 8 optimal completions, 5 direct-contrast groups and 8 semantic-contrast groups.
- Math→code has only 15 eligible completions, zero optimal completions and no downstream contrast groups.

Therefore, Q2 authorization means the full hierarchical-learning question may be trained. It does not show that Q2 has already been learned. In particular, math→code must exhibit genuine delayed unlocking after upstream routing improves.

The sentinel is correctly silent at checkpoint zero: 15 groups, no worker-1 selection or reward variance. That leaves a clean baseline for transfer and later self-reinforcement.

Reward variance remains sparse: 123/785 groups vary, with Q2 composites varying in only 16/160 groups. This is adequate to proceed but makes zero-variance fraction and conditional Q2 eligibility essential P0 diagnostics.

### Disposition and next step

The frozen decision is correctly:

> Q1 + Q2 hierarchical-unlocking authorized.

The nominal P0 size is 39 epochs / 6,123 groups. At C2’s beta-zero throughput this is approximately 7.9 hours, but it is not yet the operational P0 budget: the beta smoke and finalization measurement must feed the frozen cap formula first.

Proceed to the contract-spine work. It should reproduce the exact C2 schedule, populations, counts, gates and decision from this frozen archive. For P0, retain trajectories for:

- Q1 counted exposure by cell;
- Q2 eligibility, optimality and target choice conditional on eligibility;
- direct and semantic contrast groups;
- sentinel first occurrences;
- zero-variance and invalid-completion rates.

Finally, comparisons with C1 are useful descriptively but are not causal estimates because both the mixture and seed changed. This authorizes the coarse, cell-correlated Q2 study—not the stronger Q3 within-cell expertise claim.