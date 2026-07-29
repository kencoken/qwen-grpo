## Verdict

Rev3 correctly fixes both prior mechanisms, but one narrow part of the public-factor requirement remains missing. I would make that repair before launch.

### [P1] Public numeric factors are still discarded

[`public_subtype_record`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:399) now correctly uses the frozen subtype contract and separates collision diagnostics. However, it creates a `PublicFeatureRecord` and then discards `record.public_numeric_values`.

The signed design and `264_s` require disclosure of both:

- Observable subtype.
- Frozen public numeric factors `p`, `q`, `t`, `k`, and `i`.

Without them, later analysis cannot distinguish genuine instance-level routing from routing keyed to public numeric features.

Add a lossless, identity-bound per-observation or per-latent disclosure containing:

- Cell, renderer and latent identity.
- Exact frozen subtype.
- Derived `public_numeric_values`.
- Direction.

Do not invent numeric bins now. Keep collision and other generator-derived fields separate. Test every value against `baselines.public_feature_record` and ensure no private fields enter the record.

### Correctly closed

- Frozen subtype levels now match exactly: T1/T2/T3, count/select, plus/minus and branch order.
- Collision flags are isolated as generator-side diagnostics.
- The forged ScaleLift comparator is refused at the real `group_stats` boundary.
- Original comparator source, lock and worker are reverified at consumption.
- The positive ScaleLift test now checks an exact nonzero value.
- Selector and Q3 repairs remain intact.
- Full suite: `995 passed` under warnings-as-errors.
- All hashes, prelaunch bytes, ledger identity and environment attestations verify.

Implementing the numeric disclosure now is simpler than deferring it. The alternative would require an explicit pre-launch amendment binding its exact Unit-B extraction before any outcome or mixture decisions. After the small fix, regenerate the prelaunch once more and do a final narrow mechanical review.