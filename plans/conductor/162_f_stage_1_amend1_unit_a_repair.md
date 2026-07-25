# 162_f — Unit-A repair (response to 161_s)

The one narrow repair commit 161_s requested. All four blockers and the
three pre-Unit-B items are implemented. Full CPU suite: **752 passed**
under `-W error` (17 Unit-A tests, including one named probe per 161_s
reproduction). Nothing statistical ran.

**1. Bundle semantics enforced at load.** `_check_bundle_semantics` is
now applied identically by the builder AND `validate_execution_bundle`
after the hash recompute: exact field set (missing or smuggled extra
fields refuse), frozen attempt-id/tag/root literals, pinned prompt
digests, 64-lowercase-hex format on all eight digest fields, 40-hex
commit, and the finalized-registry entry count. The reviewer's exact
attack — alter the frozen tags and self-rehash — is a named refusing
test, alongside altered roots, altered prompts, a smuggled field, and
a partial registry count.

**2. Archive authentication completed.** The evidence manifest hash is
now PINNED (`4ae0fb83…`, recomputed after the §5 script correction);
the complete identity block (153_f hash, executable/lock/outcome
commits, source digest, execution identity) is validated against
frozen literals; the file set must equal the frozen table exactly; and
`agreement_diagnostic_script.py` joins the frozen hash table
(`f816b43e…`). Reproductions tested: modified `lock_commit`, modified
diagnostic script, modified manifest entry — all refuse.

**3. The registry is now finalized-or-nothing.**
`finalize_seed_registry(observation_ids)` produces the authoritative
full registry: components + the 6 deterministic-equivalence-set seeds
(they ARE consumed by the amended run order and were missing) + the
9,216 concrete B completion seeds under EXACTLY
`stage1_replay.completion_seed`'s key material — raw unpadded indices,
as the corrected test now asserts end-to-end against `completion_seed`
itself (the padded `|000` key the reviewer caught is gone; note the
padded key coincidentally hashed consistently in both derivations, so
the old test was vacuous rather than wrong — now it tests the real
material). `FULL_SEED_REGISTRY_ENTRIES = 49,342`; the execution bundle
carries `seed_registry_entries` and refuses any other count, so a
partial-registry digest cannot enter a bundle.

**4. Exact schemas frozen before Unit B.**
`PERSISTENCE_ZERO_BRANCH_FIELDS` (`zero_U`, `zero_U_A`, `zero_L_Q`) and
`PERSISTENCE_POSITIVE_BRANCH_FIELDS` (`pos_G_L`, `pos_G_U`, `pos_L_p`,
`pos_U_p`) are explicit schema on top of the shared base fields —
bounds as string decimals, decisions re-derived at load. The amended
sufficient-statistic row schemas are frozen as `AMEND1_ROW_SCHEMAS`
with count identities (`C_path`: first_pass+first_fail+cap_unresolved
= trials; `C_marginal`: decision counts = trials, branch counts =
trials, denominator-unresolved ≤ positive-branch; `D`; `D_branch`) and
enforced by `validate_amend1_rows`, which Unit B/C runners and loaders
both call. Impossible-count and wrong-field probes refuse.

**Pre-Unit-B items:** NumPy and SciPy versions are now recorded in the
`stage1-environment-v2` manifest (load-bearing for PCG64/Student-t/
Beta/score inversion); the §4.5 numerical conventions are tested
constants (`FLOAT_DTYPE`, `TOLERANCE_FACTOR = 64`,
`STUDENT_T_IMPL = "scipy.stats.t.ppf"`, `ENDPOINT_RTOL = 0`,
`QUANTILE_METHOD_D15`); and the archived diagnostic's regeneration
header is corrected — the script post-dates the historical checkout
(first committed at Unit A), so the instructions now say to run it by
absolute path from a worktree of `da8424b` so only the imported
modules resolve to v1 bytes. The archive manifest was regenerated for
the corrected script bytes and re-pinned; the seven frozen v1 payload
files are byte-identical throughout.

Ready for Unit B.
