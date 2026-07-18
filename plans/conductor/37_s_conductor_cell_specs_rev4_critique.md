Rev4 resolves the substantive rev3 design blockers. The cells, scheduler, node-level collision metadata, oracle coverage, modular exclusions, no-op treatment, and truncation split are now coherent. I would approve the architecture, but make one small rev4.1 contract patch before formally freezing Phase 1.

## Fix before Phase-1 sign-off

1. **Restore the missing seed and ID derivation.**

The [identity section](/Users/ken/conductor_cell_specs_rev4.md:508) uses and stores `seed`, and constructs an ID containing `hex8`, but defines neither. Rev3 did define them, so this is a regression.

Freeze something like:

```text
seed = h64(seed_material)
hex8 = first 8 lowercase hexadecimal characters of SHA-256(seed_material)
```

Also specify canonical unpadded ASCII decimal encoding for `latent_index` and `block_index`. The schema’s `seed: 18421` should either be replaced with a matching value or explicitly labelled schematic. Add one golden seed/ID fixture.

The “canonical JSON … integers only” rule also needs scoping: the runtime profile contains `β=1e-3`. Either restrict the integer-only rule to generator/difficulty-profile numeric fields or encode runtime floats as canonical decimal strings.

2. **B2 must remove both resource channels.**

[B2 currently removes only the rendered `Resource` block](/Users/ken/conductor_cell_specs_rev4.md:462). Because resources are supplied both in-context and through host-side binding, B2 must:

- omit the payload block; and
- set the authorized resource set/binding to empty.

Otherwise a worker can emit `resource` or `a * b` and still access the hidden payload through the tool.

This is also the right place to freeze resource-error precedence:

- no authorized resource and an expression requires one → `E_NO_RESOURCE`;
- resources authorized but none grammar-compatible → `E_RESOURCE_KIND`;
- compatible operands record present but identifier absent → `E_UNKNOWN_IDENT`;
- unavailable `step_k` → `E_UNKNOWN_IDENT`;
- a literal-only Math expression requires no resource and may still succeed.

3. **Interventions must map semantic nodes back to workflow positions.**

The [intervention text](/Users/ken/conductor_cell_specs_rev4.md:417) says to override `step_u`, but `u` is a semantic node ID. In a code-first fork, node `n2` is positional `step_1`. Define:

```text
j = 1 + positions.index(u)
override step_j in both the context and host binding
```

Also freeze the paired estimand:

- eligibility is determined once from the base execution;
- base, corrupted, and counterfactual accuracies use the identical eligible edge-instance set;
- clustered comparisons pair the same latent/rendered executions;
- `override_applied=false` on an eligible execution is a harness failure and aborts, rather than becoming an ordinary observation.

The present “conditional follow-through” definition is effectively identical to the eligible set because all parents already succeeded and are reused. Either remove it or redefine it as conditioning on successful execution of the complete mutated downstream path. Full-sample accuracy should remain primary.

4. **Make oracle and baseline selection mathematically executable.**

[“Lowest endpoint index”](/Users/ken/conductor_cell_specs_rev4.md:398) does not fully resolve ties between multi-node assignments. Define:

- objective: argmax of cluster-weighted terminal accuracy on construction data;
- assignment tuple ordered by stable node order `n1,n2,n3`;
- tied assignments resolved lexicographically by endpoint-index tuple;
- node runner-up = best alternative endpoint while all other nodes remain at the deployable-oracle assignment;
- equivalent frozen ordering for best one-call and the 18-workflow shortcut.

This prevents different implementations from producing different Stage-2 targets and routing-stakes gates.

5. **Resolve the cache visibility contradiction.**

[Worker completions are supposed to share across visibility](/Users/ken/conductor_cell_specs_rev4.md:442), while [visibility enters the profile fingerprint](/Users/ken/conductor_cell_specs_rev4.md:496). If that condition-specific fingerprint is in the worker-cache key, sharing cannot occur.

Use a worker-visible fingerprint for worker caching; it should contain the disclosure policy and canonical worker request, but not the Conductor’s private/visible observation condition. Store generation metadata alongside raw text—at least `finish_reason`, generated-token count, and `generation_hit_token_cap`—so truncation telemetry survives cache hits.

6. **Finish the pseudo-worker contract.**

The [no-op and echo workers](/Users/ken/conductor_cell_specs_rev4.md:483) do not emit artifacts or run tools, yet a successful `WorkerResult` currently requires both flags to be true.

Define either a separate synthetic/diagnostic result type or an explicit pseudo-worker row in the truth table. Also freeze their evaluation:

- substitute the pseudo-worker at one node while keeping deployable-oracle workers elsewhere;
- report each node substitution separately;
- optionally report an all-pseudo workflow.

That node-wise definition is required for the documented “no-op at true index zero” case.

## Fix before qualification or scientific claims

- **Sequential inference:** deterministic prefixes solve data identity, but ordinary 95% CIs at 100, 300, and 500 followed by “stop when decisive” do not retain 95% coverage. Pre-register confidence sequences or alpha spending across looks. Also state: conclusive failure stops as failure; all gates passing stops as pass; unresolved at the maximum means no admission.

- **Collision headline:** rename [“clean headline stratum”](/Users/ken/conductor_cell_specs_rev4.md:638) to “private, no-public-semantic-parameter-collision stratum.” It removes pre-existing copying opportunities but cannot exclude lucky guesses or encoded answers. Restore rev3’s reports: collision rate by cell/subtype, collision versus non-collision accuracy, and answer-in-subtask rate crossed with collision status. Counts should be latent clusters with clustered CIs. A useful conservative companion score would count every detected answer-in-subtask workflow as wrong; the token detector should be described as a lower bound.

- **Public-feature baseline:** the present majority/parameter-echo family is too weak to detect shortcuts such as `t → modal count`. Either rename it “public-parameter echo” or add a frozen shallow predictor fitted on construction data using subtype plus all available semantic parameters.

- **Phase-2 ranges:** make explicit that every `(S)` band in sampler descriptions is read from the difficulty profile, not hard-coded. If a tuned constructive range has an empty feasible set, define candidate retry/profile failure. Report post-rejection joint distributions such as `(m, residue)`, `(U,t,answer)`, and collision rate, not only one-dimensional marginals.

## Minor exactness cleanups

Before freezing the parser/IR, I would also specify:

- exact allowed opaque worker IDs, array length, integer typing, duplicate-worker permissibility, and unknown-ID scoring in the [routing schema](/Users/ken/conductor_cell_specs_rev4.md:217);
- integer-versus-string literal types and exact operand-name matching—e.g. argument `a` must reference operand `"a"`—in the [IR schemas](/Users/ken/conductor_cell_specs_rev4.md:120);
- `</value>` as well as `<value>` should trigger `E_UNEXPECTED_TAG`;
- the private-condition provenance test uses the frozen token boundaries and excludes intentionally visible payload prompts;
- the shortcut byte fixtures cover 18 workflows × 2 calls, rather than ambiguously “18 requests.”

Overall, no cell or data redesign is needed. After these bounded textual fixes and the separate D16 system-prompt review, I would sign off Phase 1. The high-level claim remains appropriately narrow: this is an orchestration-learning laboratory under constructed capability and authorization differences, not yet evidence that selective delegation is useful in a visible frontier-model setting.