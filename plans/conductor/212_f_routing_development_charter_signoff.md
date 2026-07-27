# 212_f — Development charter SIGNED (211_f rev4; scope + binding reminders)

Ken signed the routing-training development charter (`211_f`,
@8ec98a2) on 2026-07-27, with the reviewer's closing note. This
record fixes the authorization scope and converts the three
nonblocking reminders into BINDING notes on the freezes where each
lands.

## 1. Authorization scope (exact)

Signing authorizes ONLY:

1. the development infrastructure (211_f §15 step 3);
2. the support-materialization tranche (§4);
3. the GPU resume-validation tranche (§11);
4. the zero-update grouped probe (§5).

**It does NOT authorize P0.** The P0 launch freeze remains a
separate future authorization following the probe review (§15
steps 8–9).

## 2. The three reminders, bound to their freezes

1. **Provisional `R_cycle` numerical basis**: when the provisional
   reserve is set at the §4 support-materialization review, the
   ledger entry records its full numerical basis — the assumed
   cycle cohort size, the assumed evaluation multiplier
   (inference passes per observation incl. verification/trace/
   archival overhead), the measured per-observation timing it
   scales, and the rounding-up applied — not just the resulting
   number.
2. **Resume-validation ceiling**: the 2 GPU-hour figure in 211_f
   §11 is a PROPOSAL only. The tranche's lightweight launch freeze
   states its exact operational ceiling, which supersedes the
   proposal.
3. **P0 transport reproducibility**: whichever §5 route the P0
   freeze takes — the probe-stratum reweighting/transport
   calculation or the exact-cohort zero-update exposure sample —
   must be FULLY REPRODUCIBLE from the freeze alone: exact inputs
   (authenticated probe results / sample raw outputs by content
   hash), the computation's source identity, seeds, and the
   resulting projected counts, so a reviewer can regenerate the
   numbers byte-for-byte.

## 3. Next

211_f §15 step 3: the implementation tranche (namespaces +
disjointness test, surface materialization + authentication, cohort
builders incl. the frozen probe-selection rule machinery and the
`c_fixed_dev` selector, stratified telemetry on the §7
denominators, natural-mixture definition, append-only ledger with
reserve accounting, v1-boundary checkpoint/resume with separate
generated/consumed counters, isolated evaluation RNG, provenance
incl. the training-driver digest), closing with the full CPU suite
under `-W error`, then review.
