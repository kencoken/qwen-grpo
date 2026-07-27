"""Routing-training development track (211_f charter, signed 212_f).

This package is the DEVELOPMENT-track implementation: namespaces,
surface materialization, cohort builders, stratified telemetry, the
append-only ledger, and the v1 checkpoint/resume contract. Everything
here produces development data permanently — nothing in this package
may feed a confirmatory estimate (211_f §14).

It deliberately lives OUTSIDE tasks/conductor/: the eight Stage-0
SOURCE_DIGEST_FILES are frozen, and the Stage-1 source identity
(`stage1_manifest.stage1_source_digest`, over tasks/conductor/*.py)
should not churn with development iteration. The development track has
its own execution digest (`charter.routing_execution_digest`) covering
BOTH directories plus the actual training driver, per 208_s.
"""
