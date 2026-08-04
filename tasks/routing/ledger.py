"""The append-only development ledger (211_f §12) and envelope
accounting (211_f §10, 212_f reminder 1).

The ledger file is markdown with one fenced JSON block per entry.
Each entry carries a self-hash and the previous entry's self-hash, so
append-only-ness is verifiable: `read_ledger` re-derives the chain and
refuses a file whose recorded entries were edited, reordered or
removed. `append_ledger_entry` re-reads and re-verifies before every
append and never rewrites recorded bytes.

Reserve accounting: a reserve record is PROVISIONAL until the cycle
cohort and its checkpoint-selection/evaluation rule are frozen, and
must carry its full numerical basis (212_f reminder 1). Admission:
ordinary pre-closure launches need
    remaining >= launch_max + reserve;
cycle closure CONSUMES the reserve —
    launch_max <= reserve and remaining >= launch_max
(210_s issue 4: the reserve is never double-counted against closure).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import InfrastructureError

from .charter import CYCLE_ENVELOPE_GPU_HOURS, content_sha256

LEDGER_PATH = Path("plans/conductor/routing_dev_ledger.md")
LEDGER_HEADER = (
    "# Routing development ledger (211_f §12 — append-only)\n\n"
    "One fenced JSON block per entry; each entry hashes itself and\n"
    "chains the previous entry's hash. Never edit a recorded entry.\n")

_REQUIRED_ENTRY_KEYS = frozenset({
    "kind", "question", "motivating_evidence", "freeze",
    "parent", "budget_allocated_gpu_hours", "outcome_informed",
})
_OPTIONAL_ENTRY_KEYS = frozenset({
    "budget_consumed_gpu_hours", "outcome_pointer", "interpretation",
    "next_decision", "cohort_selection", "reserve",
    "closes_entry_sha256", "terminal_status",
})
_ENTRY_KINDS = (
    "support_materialization", "support_extension",
    "val_materialization",
    "resume_validation", "grouped_probe",
    "engineering_smoke", "standalone_evaluation", "training_run",
    "engineering_resume", "adaptive_continuation", "fork",
    "reserve_update", "cycle_closure", "cycle_synthesis",
    # 214_s P1: a launch entry records its allocation BEFORE the run;
    # its linked closeout records the measured cost afterwards, and
    # envelope accounting replaces the allocation with it.
    "closeout",
)
# Entry kinds that describe a GPU launch and therefore consume budget.
_LAUNCH_KINDS = frozenset({
    "support_materialization", "support_extension",
    "val_materialization",
    "resume_validation", "grouped_probe",
    "engineering_smoke", "standalone_evaluation", "training_run",
    "engineering_resume", "adaptive_continuation", "fork",
    "cycle_closure",
})
_COHORT_SELECTIONS = ("outcome_blind", "outcome_conditioned")

_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def _finite_number(value: Any) -> bool:
    """218_s F2: NaN/inf budgets fail OPEN through plain comparisons —
    every budget, timing, multiplier and reserve value must be a
    finite non-bool number."""
    return isinstance(value, (int, float)) \
        and not isinstance(value, bool) and math.isfinite(value)


def validate_entry(entry: Mapping[str, Any]) -> None:
    missing = _REQUIRED_ENTRY_KEYS - set(entry)
    if missing:
        raise InfrastructureError(
            f"ledger entry missing required fields {sorted(missing)}")
    unknown = set(entry) - _REQUIRED_ENTRY_KEYS - _OPTIONAL_ENTRY_KEYS \
        - {"entry_sha256", "previous_entry_sha256"}
    if unknown:
        raise InfrastructureError(
            f"ledger entry carries unknown fields {sorted(unknown)}")
    if entry["kind"] not in _ENTRY_KINDS:
        raise InfrastructureError(f"unknown entry kind {entry['kind']!r}")
    if not isinstance(entry["freeze"], Mapping) or not entry["freeze"]:
        raise InfrastructureError(
            "ledger entry freeze must be a non-empty mapping of hashes")
    budget = entry["budget_allocated_gpu_hours"]
    if not _finite_number(budget) or budget < 0:
        raise InfrastructureError(
            f"budget_allocated_gpu_hours must be finite and >= 0, "
            f"got {budget!r}")
    if not isinstance(entry["outcome_informed"], bool):
        raise InfrastructureError("outcome_informed must be a bool")
    selection = entry.get("cohort_selection")
    if selection is not None and selection not in _COHORT_SELECTIONS:
        raise InfrastructureError(
            f"cohort_selection must be one of {_COHORT_SELECTIONS}")
    if entry["kind"] in ("support_materialization",
                         "support_extension", "grouped_probe",
                         "val_materialization") \
            and selection != "outcome_blind":
        raise InfrastructureError(
            f"a {entry['kind']} launch must declare "
            "cohort_selection='outcome_blind' (216_s F2; 211_f §4)")
    if entry["kind"] == "reserve_update":
        validate_reserve(entry.get("reserve"))
    if entry["kind"] == "closeout":
        if not entry.get("closes_entry_sha256"):
            raise InfrastructureError(
                "a closeout must name the launch entry it closes")
        consumed = entry.get("budget_consumed_gpu_hours")
        if not _finite_number(consumed) or consumed < 0:
            raise InfrastructureError(
                "a closeout must record the measured, finite "
                "budget_consumed_gpu_hours")
        # 222_s F1: every closeout states its terminal outcome — an
        # aborted launch is closed out too (measured cost, partial
        # evidence preserved), never left open.
        if entry.get("terminal_status") not in ("complete", "aborted"):
            raise InfrastructureError(
                "a closeout must declare terminal_status "
                "'complete' or 'aborted' (222_s F1)")
    else:
        if entry.get("closes_entry_sha256") is not None:
            raise InfrastructureError(
                "only closeout entries may reference a launch to close")
        if entry.get("budget_consumed_gpu_hours") is not None:
            raise InfrastructureError(
                "measured consumption is recorded by a linked closeout "
                "entry, never on the launch itself (214_s P1)")
        if entry.get("terminal_status") is not None:
            raise InfrastructureError(
                "terminal_status belongs to closeout entries")


def validate_reserve(reserve: Any) -> None:
    """212_f reminder 1 + 216_s: a reserve carries its full numerical
    basis, every basis field validates numerically, and the reserve
    must RECOMPUTE — it cannot be smaller than the hours its own
    basis implies (rounding is always up)."""
    if not isinstance(reserve, Mapping):
        raise InfrastructureError("reserve_update entry carries no "
                                  "reserve record")
    required = {"status", "r_cycle_gpu_hours", "assumed_cohort_size",
                "evaluation_multiplier",
                "measured_seconds_per_observation",
                "measured_support_gpu_hours", "rounding"}
    missing = required - set(reserve)
    if missing:
        raise InfrastructureError(
            f"reserve record missing numerical basis {sorted(missing)} "
            "(212_f reminder 1 / 224_s F3)")
    support_hours = reserve["measured_support_gpu_hours"]
    if not _finite_number(support_hours) or support_hours < 0:
        raise InfrastructureError(
            f"measured_support_gpu_hours must be finite and >= 0, "
            f"got {support_hours!r}")
    if reserve["status"] not in ("provisional", "final"):
        raise InfrastructureError(
            f"reserve status {reserve['status']!r} must be provisional "
            "or final")
    cohort = reserve["assumed_cohort_size"]
    if not isinstance(cohort, int) or isinstance(cohort, bool) \
            or cohort <= 0:
        raise InfrastructureError(
            f"assumed_cohort_size must be a positive int, got "
            f"{cohort!r}")
    for name in ("r_cycle_gpu_hours", "evaluation_multiplier",
                 "measured_seconds_per_observation"):
        value = reserve[name]
        if not _finite_number(value) or value <= 0:
            raise InfrastructureError(
                f"{name} must be finite and > 0, got {value!r}")
    # 218_s minor: the rounding is a frozen POLICY, recomputed exactly
    # — not a description.
    if reserve["rounding"] != "ceil_to_whole_gpu_hours":
        raise InfrastructureError(
            "reserve rounding must be the frozen policy "
            "'ceil_to_whole_gpu_hours'")
    implied_hours = (cohort * reserve["evaluation_multiplier"]
                     * reserve["measured_seconds_per_observation"]
                     / 3600.0)
    expected = float(math.ceil(implied_hours))
    if reserve["r_cycle_gpu_hours"] != expected:
        raise InfrastructureError(
            f"r_cycle_gpu_hours {reserve['r_cycle_gpu_hours']} != "
            f"ceil({implied_hours:.6f}) = {expected} — the reserve "
            "must recompute exactly under the frozen rounding policy")


def read_ledger(path: str | Path = LEDGER_PATH) -> list[dict[str, Any]]:
    """Parse and verify the whole chain. A missing file is an empty
    ledger; a broken chain (edited, reordered or truncated entries)
    refuses."""
    path = Path(path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    entries = []
    previous = None
    for match in _BLOCK_RE.finditer(text):
        entry = json.loads(match.group(1))
        declared = entry.get("entry_sha256")
        body = {k: v for k, v in entry.items() if k != "entry_sha256"}
        if content_sha256(body) != declared:
            raise InfrastructureError(
                "ledger entry does not rehash — a recorded entry was "
                "edited (the ledger is append-only)")
        if entry.get("previous_entry_sha256") != previous:
            raise InfrastructureError(
                "ledger chain broken — entries were removed, reordered "
                "or inserted")
        validate_entry(entry)
        entries.append(entry)
        previous = declared
    return entries


def ledger_head(path: str | Path = LEDGER_PATH) -> str | None:
    """The last entry's self-hash — the value every tranche commit
    records EXTERNALLY (in its lineage document), because a hash chain
    alone cannot detect suffix deletion (214_s P1)."""
    entries = read_ledger(path)
    return entries[-1]["entry_sha256"] if entries else None


def verify_ledger_head(expected_head_sha256: str | None,
                       path: str | Path = LEDGER_PATH
                       ) -> list[dict[str, Any]]:
    """Consume the ledger against its externally committed head: the
    chain must verify AND end exactly at the expected entry. This is
    the read every launch boundary uses."""
    entries = read_ledger(path)
    actual = entries[-1]["entry_sha256"] if entries else None
    if actual != expected_head_sha256:
        raise InfrastructureError(
            f"ledger head {actual!r} != externally committed head "
            f"{expected_head_sha256!r} — entries were appended or "
            "deleted since the head was recorded (214_s P1)")
    return entries


def append_ledger_entry(entry: Mapping[str, Any],
                        expected_head_sha256: str | None,
                        path: str | Path = LEDGER_PATH
                        ) -> dict[str, Any]:
    """Bookkeeping appends only (closeouts, synthesis). LAUNCH
    entries must come through `admit_and_append_launch` (218_s F2);
    RESERVE updates must come through
    `support_run.record_provisional_reserve`, which verifies the
    terminal run the reserve is based on (228_s F1)."""
    validate_entry(entry)
    if entry["kind"] in _LAUNCH_KINDS:
        raise InfrastructureError(
            f"{entry['kind']!r} is a launch — it must be admitted and "
            "appended through admit_and_append_launch (218_s F2)")
    if entry["kind"] == "reserve_update":
        raise InfrastructureError(
            "reserve updates must come through "
            "support_run.record_provisional_reserve, which verifies "
            "the terminal run they are based on (228_s F1)")
    return _append(entry, expected_head_sha256, path)


def _append(entry: Mapping[str, Any],
            expected_head_sha256: str | None,
            path: str | Path) -> dict[str, Any]:
    """Verify the existing chain AGAINST the externally committed head
    (REQUIRED, None only for an empty ledger — 216_s F2: without it a
    deleted suffix could be followed by a valid-looking replacement
    chain), then append — never rewrite. The entry is validated,
    chained to the last recorded hash, self-hashed and written as a
    new fenced block; a closeout must name a recorded, not-yet-closed
    launch entry."""
    path = Path(path)
    existing = verify_ledger_head(expected_head_sha256, path)
    validate_entry(entry)
    if entry["kind"] == "closeout":
        target = entry["closes_entry_sha256"]
        launches = {e["entry_sha256"]: e for e in existing
                    if e["kind"] in _LAUNCH_KINDS}
        if target not in launches:
            raise InfrastructureError(
                f"closeout references {target!r}, which is not a "
                "recorded launch entry")
        already = {e["closes_entry_sha256"] for e in existing
                   if e["kind"] == "closeout"}
        if target in already:
            raise InfrastructureError(
                f"launch entry {target!r} is already closed out")
    if entry["kind"] == "reserve_update":
        # 224_s F3: a reserve exists only downstream of a SUCCESSFUL
        # support run — bound to its closeout, its authenticated
        # surface, and its measured cost, with nothing left open.
        closeouts = {e["closes_entry_sha256"]: e for e in existing
                     if e["kind"] == "closeout"}
        complete = {sha: e for sha, e in closeouts.items()
                    if e.get("terminal_status") == "complete"
                    and any(le["entry_sha256"] == sha
                            and le["kind"] == "support_materialization"
                            for le in existing)}
        if not complete:
            raise InfrastructureError(
                "a reserve requires a terminal_status='complete' "
                "support closeout on record (224_s F3)")
        state = envelope_state(existing)
        if state["open_launches"]:
            raise InfrastructureError(
                "a reserve cannot be recorded while a launch is open "
                "(224_s F3)")
        freeze = entry["freeze"]
        named = freeze.get("support_closeout_sha256")
        target = None
        for sha, closeout in complete.items():
            if closeout["entry_sha256"] == named:
                target = closeout
        if target is None:
            raise InfrastructureError(
                "the reserve's freeze must name a completed support "
                "closeout's entry hash (224_s F3)")
        if freeze.get("surface_lock_sha256") != \
                target["freeze"].get("surface_lock_sha256"):
            raise InfrastructureError(
                "the reserve must bind the completed support's "
                "authenticated surface lock (224_s F3)")
        # 226_s F2: the referenced closeout must carry the canonical
        # complete-support terminal binding, not a minimal freeze.
        required_binding = {"surface_lock_sha256",
                            "run_record_file_sha256",
                            "execute_env_file_sha256",
                            "rendered_observations"}
        missing_binding = required_binding - set(target["freeze"])
        if missing_binding:
            raise InfrastructureError(
                f"the referenced support closeout lacks the canonical "
                f"terminal binding {sorted(missing_binding)} "
                "(226_s F2)")
        if entry["reserve"]["measured_support_gpu_hours"] != \
                target["budget_consumed_gpu_hours"]:
            raise InfrastructureError(
                "the reserve's measured_support_gpu_hours must equal "
                "the completed support closeout's measured cost "
                "(224_s F3)")
        # 226_s F1: the per-observation timing basis DERIVES from the
        # authenticated cost and denominator — never caller-asserted.
        rendered = target["freeze"]["rendered_observations"]
        if not isinstance(rendered, int) or isinstance(rendered, bool) \
                or rendered < 1:
            raise InfrastructureError(
                f"bad rendered_observations {rendered!r} in the "
                "support closeout")
        derived = (target["budget_consumed_gpu_hours"] * 3600.0
                   / rendered)
        if entry["reserve"]["measured_seconds_per_observation"] != \
                derived:
            raise InfrastructureError(
                f"measured_seconds_per_observation must rederive "
                f"exactly from the closeout: "
                f"{target['budget_consumed_gpu_hours']} h × 3600 / "
                f"{rendered} = {derived!r} (226_s F1)")
        # 226_s F1 / 228_s F2: FINAL reserves are refused
        # UNCONDITIONALLY — enabling them requires the real
        # cycle-cohort and evaluation-rule validators, not truthy
        # strings; until those exist every reserve is provisional.
        if entry["reserve"]["status"] == "final":
            raise InfrastructureError(
                "final reserve authorization is not yet enabled — it "
                "awaits the real cycle-cohort and evaluation-rule "
                "validators; record a provisional reserve (228_s F2)")
    record = dict(entry)
    record["previous_entry_sha256"] = (
        existing[-1]["entry_sha256"] if existing else None)
    record["entry_sha256"] = content_sha256(record)
    block = ("\n## entry " + str(len(existing) + 1)
             + f" — {record['kind']}\n\n```json\n"
             + json.dumps(record, indent=1, sort_keys=True)
             + "\n```\n")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LEDGER_HEADER + block, encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(block)
    read_ledger(path)  # the appended file must itself verify
    return record


# --- envelope accounting --------------------------------------------------------

def envelope_state(entries: list[Mapping[str, Any]],
                   envelope_gpu_hours: float = CYCLE_ENVELOPE_GPU_HOURS
                   ) -> dict[str, Any]:
    """Launch entries are charged their allocation until a linked
    closeout replaces it with the measured cost (214_s P1: an open
    launch and its later closeout are never double-charged)."""
    closeouts: dict[str, float] = {}
    for entry in entries:
        if entry["kind"] == "closeout":
            closeouts[entry["closes_entry_sha256"]] = \
                entry["budget_consumed_gpu_hours"]
    consumed = 0.0
    reserve = None
    open_launches = []
    for entry in entries:
        if entry["kind"] == "reserve_update":
            reserve = entry["reserve"]
            continue
        if entry["kind"] not in _LAUNCH_KINDS:
            continue
        sha = entry["entry_sha256"]
        if sha in closeouts:
            consumed += closeouts[sha]
        else:
            consumed += entry["budget_allocated_gpu_hours"]
            open_launches.append(sha)
    return {"envelope_gpu_hours": envelope_gpu_hours,
            "consumed_gpu_hours": consumed,
            "remaining_gpu_hours": envelope_gpu_hours - consumed,
            "open_launches": open_launches,
            "reserve": reserve}


def admit_and_append_launch(entry: Mapping[str, Any],
                            expected_head_sha256: str | None,
                            path: str | Path = LEDGER_PATH, *,
                            launch_manifest: Mapping[str, Any]
                            | None = None) -> dict[str, Any]:
    """THE launch boundary (218_s F2): verifies the PERSISTED ledger
    against the externally committed head, derives admission from that
    verified state and the PROSPECTIVE ENTRY ITSELF (its kind and its
    allocated budget — the checked launch IS the recorded launch),
    and appends the same entry atomically with the admission. The
    60-hour envelope is fixed here. Non-launch entries go through
    `append_ledger_entry`; launch entries must come through here.

    211_f §10 as corrected by 210_s issue 4: ordinary pre-closure
    launches keep the reserve intact; `cycle_closure` consumes it. A
    `support_materialization` is admissible against the bare envelope
    only while no reserve exists AND every prior support launch in
    the verified chain (if any) is an ABORTED-closed,
    design-preserving attempt (the 222_s/224_s recovery rule — open
    or completed support launches block, and a changed scientific
    design refuses)."""
    path = Path(path)
    entries = verify_ledger_head(expected_head_sha256, path)
    validate_entry(entry)
    launch_kind = entry["kind"]
    if launch_kind not in _LAUNCH_KINDS:
        raise InfrastructureError(
            f"{launch_kind!r} is not a launch kind — use "
            "append_ledger_entry for bookkeeping entries")
    launch_max = entry["budget_allocated_gpu_hours"]
    if not _finite_number(launch_max) or launch_max <= 0:
        raise InfrastructureError(
            f"a launch allocation must be finite and > 0, got "
            f"{launch_max!r}")
    if launch_kind == "support_materialization":
        # 220_s F1: the recorded launch IS the executed launch — the
        # entry must name the exact support-launch manifest and carry
        # its budget, verified against the manifest itself.
        if launch_manifest is None:
            raise InfrastructureError(
                "a support launch is admitted WITH its support-launch "
                "manifest (220_s F1)")
        named = entry["freeze"].get("support_launch_sha256")
        if named != launch_manifest.get("manifest_sha256") or not named:
            raise InfrastructureError(
                "the support entry's freeze must name the exact "
                "support-launch manifest hash (220_s F1)")
        if launch_max != launch_manifest.get("budget_gpu_hours"):
            raise InfrastructureError(
                f"the admitted budget {launch_max} differs from the "
                f"manifest budget "
                f"{launch_manifest.get('budget_gpu_hours')} (220_s F1)")
        # 224_s F2: the entry carries the manifest's scientific-design
        # identity, verified — the retry rule below compares it.
        from .dev_support import scientific_design_sha256
        design = entry["freeze"].get("scientific_design_sha256")
        if design != scientific_design_sha256(launch_manifest):
            raise InfrastructureError(
                "the support entry's freeze must carry the manifest's "
                "scientific_design_sha256 (224_s F2)")
    if launch_kind == "support_extension":
        # 260_f Unit A: a support EXTENSION is admitted WITH its own
        # self-contained extension-launch manifest — it never carries
        # the first-probe contract (257_s B3), and its freeze binds
        # the manifest hash, the budget, and the manifest's own
        # scientific-design identity.
        if launch_manifest is None:
            raise InfrastructureError(
                "a support extension is admitted WITH its "
                "extension-launch manifest (260_f Unit A)")
        if launch_manifest.get("kind") != \
                "routing-dev-extension-launch-v1":
            raise InfrastructureError(
                "a support extension binds an extension-launch "
                "manifest, not a "
                f"{launch_manifest.get('kind')!r} (260_f Unit A)")
        named = entry["freeze"].get("extension_launch_sha256")
        if named != launch_manifest.get("manifest_sha256") or not named:
            raise InfrastructureError(
                "the extension entry's freeze must name the exact "
                "extension-launch manifest hash (260_f Unit A)")
        if launch_max != launch_manifest.get("budget_gpu_hours"):
            raise InfrastructureError(
                f"the admitted budget {launch_max} differs from the "
                f"manifest budget "
                f"{launch_manifest.get('budget_gpu_hours')}")
        design = entry["freeze"].get("scientific_design_sha256")
        if not design or design != \
                launch_manifest.get("scientific_design_sha256"):
            raise InfrastructureError(
                "the extension entry's freeze must carry the "
                "manifest's scientific_design_sha256 (260_f Unit A)")
    if launch_kind == "val_materialization":
        # 332_s P0-1: the validation tranche has its OWN admission
        # path — it intentionally carries no probe rule, so it can
        # never satisfy (and never borrows) the probe-bearing
        # support schema. Its freeze binds the val-launch manifest,
        # the budget, the manifest's scientific-design identity, AND
        # the signed tranche-freeze hash (332_s P1-7).
        if launch_manifest is None:
            raise InfrastructureError(
                "a val materialization is admitted WITH its "
                "val-launch manifest (332_s)")
        if launch_manifest.get("kind") != "routing-dev-val-launch-v1":
            raise InfrastructureError(
                "a val materialization binds a val-launch manifest, "
                f"not a {launch_manifest.get('kind')!r} (332_s)")
        named = entry["freeze"].get("val_launch_sha256")
        if named != launch_manifest.get("manifest_sha256") or not named:
            raise InfrastructureError(
                "the val entry's freeze must name the exact "
                "val-launch manifest hash (332_s)")
        if launch_max != launch_manifest.get("budget_gpu_hours"):
            raise InfrastructureError(
                f"the admitted budget {launch_max} differs from the "
                f"manifest budget "
                f"{launch_manifest.get('budget_gpu_hours')}")
        design = entry["freeze"].get("scientific_design_sha256")
        if not design or design != \
                launch_manifest.get("scientific_design_sha256"):
            raise InfrastructureError(
                "the val entry's freeze must carry the manifest's "
                "scientific_design_sha256")
        frozen = entry["freeze"].get("val_freeze_sha256")
        if not frozen or frozen != \
                launch_manifest.get("val_freeze_sha256"):
            raise InfrastructureError(
                "the val entry's freeze must carry the signed "
                "tranche-freeze hash the manifest binds (332_s)")
        # 334_s P1-3: the registered retry semantics, enforced at
        # THE admission boundary — a retry only after an
        # aborted-closed attempt with the IDENTICAL scientific
        # design; never after an open or completed attempt; the
        # entry persists the actual lineage parent (the verified
        # head it is admitted on).
        if entry.get("parent") != (entries[-1]["entry_sha256"]
                                   if entries else None):
            raise InfrastructureError(
                "a val entry must persist the ACTUAL lineage "
                "parent — the verified head it is admitted on "
                "(334_s P1-3)")
        val_closeouts = {e.get("closes_entry_sha256"): e
                         for e in entries if e["kind"] == "closeout"}
        prior_val = [e for e in entries
                     if e["kind"] == "val_materialization"]
        # 336_s P1-2: the FROZEN initial parent is part of the
        # validated launch contract and is enforced HERE — the
        # authoritative admission boundary, not only the runner
        if not prior_val and entry.get("parent") != \
                launch_manifest.get("lineage_parent_sha256"):
            raise InfrastructureError(
                "the FIRST val launch is admitted only on the "
                "manifest's frozen initial parent (336_s P1-2)")
        for attempt in prior_val:
            closeout = val_closeouts.get(attempt["entry_sha256"])
            if closeout is None:
                raise InfrastructureError(
                    "a prior val attempt is OPEN — no new val "
                    "launch (334_s P1-3)")
            if closeout.get("terminal_status") == "complete":
                raise InfrastructureError(
                    "a completed val materialization exists — a "
                    "second val launch is never a retry (334_s "
                    "P1-3)")
            if attempt["freeze"].get("scientific_design_sha256") \
                    != entry["freeze"].get(
                        "scientific_design_sha256"):
                raise InfrastructureError(
                    "an aborted-val retry must preserve the "
                    "scientific design (334_s P1-3)")
    state = envelope_state(entries, CYCLE_ENVELOPE_GPU_HOURS)
    remaining = state["remaining_gpu_hours"]
    reserve = state["reserve"]
    if reserve is None:
        # 222_s F1 recovery rule as tightened by 224_s F2: a prior
        # support launch blocks a new no-reserve support launch UNLESS
        # it was closed out ABORTED, and an aborted-support retry must
        # PRESERVE the scientific design — an abort can be
        # outcome-bearing (the surface may exist), so a changed
        # cohort/rule/worker/request identity is an outcome-informed
        # successor, not a retry, and cannot take this path.
        closeout_status = {e["closes_entry_sha256"]:
                           e.get("terminal_status")
                           for e in entries if e["kind"] == "closeout"}
        prior_support = [e for e in entries
                         if e["kind"] == "support_materialization"]
        blocking = [e for e in prior_support
                    if closeout_status.get(e["entry_sha256"])
                    != "aborted"]
        if launch_kind == "support_materialization" and not blocking:
            for aborted in prior_support:
                if aborted["freeze"].get("scientific_design_sha256") \
                        != entry["freeze"].get(
                            "scientific_design_sha256"):
                    raise InfrastructureError(
                        "an aborted-support retry must preserve the "
                        "scientific design (declaration/cohort, probe "
                        "rule, worker/request/cache identities); a "
                        "changed design is an outcome-informed "
                        "successor and needs its own reviewed path "
                        "(224_s F2)")
            if remaining < launch_max:
                raise InfrastructureError(
                    f"remaining {remaining} GPU-h cannot cover the "
                    f"initial support maximum {launch_max}")
        else:
            raise InfrastructureError(
                "no reserve on record — the no-reserve path admits "
                "only a support materialization whose predecessors "
                "(if any) are all ABORTED-closed design-preserving "
                f"attempts; the ledger shows {len(blocking)} prior "
                "support launch(es) that are open or completed "
                "(216_s F2, 222_s F1, 224_s F2)")
    else:
        validate_reserve(reserve)
        r_cycle = reserve["r_cycle_gpu_hours"]
        if launch_kind == "cycle_closure":
            if launch_max > r_cycle:
                raise InfrastructureError(
                    f"closure maximum {launch_max} exceeds the "
                    f"reserved R_cycle {r_cycle}")
            if remaining < launch_max:
                raise InfrastructureError(
                    f"remaining {remaining} GPU-h cannot cover the "
                    f"closure maximum {launch_max}")
        elif remaining < launch_max + r_cycle:
            raise InfrastructureError(
                f"inadmissible launch: remaining {remaining} GPU-h < "
                f"launch maximum {launch_max} + R_cycle {r_cycle} "
                "(211_f §10)")
    return _append(entry, expected_head_sha256, path)
