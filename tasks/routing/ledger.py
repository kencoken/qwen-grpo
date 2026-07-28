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
    "closes_entry_sha256",
})
_ENTRY_KINDS = (
    "support_materialization", "resume_validation", "grouped_probe",
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
    "support_materialization", "resume_validation", "grouped_probe",
    "engineering_smoke", "standalone_evaluation", "training_run",
    "engineering_resume", "adaptive_continuation", "fork",
    "cycle_closure",
})
_COHORT_SELECTIONS = ("outcome_blind", "outcome_conditioned")

_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


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
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) \
            or budget < 0:
        raise InfrastructureError(
            f"budget_allocated_gpu_hours must be >= 0, got {budget!r}")
    if not isinstance(entry["outcome_informed"], bool):
        raise InfrastructureError("outcome_informed must be a bool")
    selection = entry.get("cohort_selection")
    if selection is not None and selection not in _COHORT_SELECTIONS:
        raise InfrastructureError(
            f"cohort_selection must be one of {_COHORT_SELECTIONS}")
    if entry["kind"] == "reserve_update":
        validate_reserve(entry.get("reserve"))
    if entry["kind"] == "closeout":
        if not entry.get("closes_entry_sha256"):
            raise InfrastructureError(
                "a closeout must name the launch entry it closes")
        consumed = entry.get("budget_consumed_gpu_hours")
        if not isinstance(consumed, (int, float)) \
                or isinstance(consumed, bool) or consumed < 0:
            raise InfrastructureError(
                "a closeout must record the measured "
                "budget_consumed_gpu_hours")
    else:
        if entry.get("closes_entry_sha256") is not None:
            raise InfrastructureError(
                "only closeout entries may reference a launch to close")
        if entry.get("budget_consumed_gpu_hours") is not None:
            raise InfrastructureError(
                "measured consumption is recorded by a linked closeout "
                "entry, never on the launch itself (214_s P1)")


def validate_reserve(reserve: Any) -> None:
    """212_f reminder 1: a reserve carries its full numerical basis,
    not just the number."""
    if not isinstance(reserve, Mapping):
        raise InfrastructureError("reserve_update entry carries no "
                                  "reserve record")
    required = {"status", "r_cycle_gpu_hours", "assumed_cohort_size",
                "evaluation_multiplier",
                "measured_seconds_per_observation", "rounding"}
    missing = required - set(reserve)
    if missing:
        raise InfrastructureError(
            f"reserve record missing numerical basis {sorted(missing)} "
            "(212_f reminder 1)")
    if reserve["status"] not in ("provisional", "final"):
        raise InfrastructureError(
            f"reserve status {reserve['status']!r} must be provisional "
            "or final")
    value = reserve["r_cycle_gpu_hours"]
    if not isinstance(value, (int, float)) or isinstance(value, bool) \
            or value <= 0:
        raise InfrastructureError(
            f"r_cycle_gpu_hours must be > 0, got {value!r}")


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
                        path: str | Path = LEDGER_PATH,
                        expected_head_sha256: str | None = ...,
                        ) -> dict[str, Any]:
    """Verify the existing chain, then append — never rewrite. The
    entry is validated, chained to the last recorded hash, self-hashed
    and written as a new fenced block. Pass `expected_head_sha256`
    (the externally committed head, None for an empty ledger) to also
    detect suffix deletion before appending; a closeout must name a
    recorded, not-yet-closed launch entry."""
    path = Path(path)
    if expected_head_sha256 is ...:
        existing = read_ledger(path)
    else:
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


def check_launch_admissible(*, remaining_gpu_hours: float,
                            launch_max_gpu_hours: float,
                            reserve: Mapping[str, Any] | None,
                            closure: bool = False,
                            initial_support: bool = False) -> None:
    """211_f §10 as corrected by 210_s issue 4 and 214_s P1. Ordinary
    pre-closure launches keep the reserve intact; closure consumes it;
    the INITIAL support materialization — the run whose measured
    timing CREATES the provisional reserve — is admissible against the
    bare envelope, exactly once, before any reserve exists."""
    if not isinstance(launch_max_gpu_hours, (int, float)) \
            or isinstance(launch_max_gpu_hours, bool) \
            or launch_max_gpu_hours <= 0:
        raise InfrastructureError(
            f"launch maximum must be > 0, got {launch_max_gpu_hours!r}")
    if initial_support:
        if reserve is not None:
            raise InfrastructureError(
                "the initial-support admission path applies only "
                "BEFORE a reserve exists; use the ordinary rule")
        if remaining_gpu_hours < launch_max_gpu_hours:
            raise InfrastructureError(
                f"remaining {remaining_gpu_hours} GPU-h cannot cover "
                f"the initial support maximum {launch_max_gpu_hours}")
        return
    if reserve is None:
        raise InfrastructureError(
            "no reserve on record — only the initial support "
            "materialization may launch without one "
            "(initial_support=True; 214_s P1)")
    validate_reserve(reserve)
    r_cycle = reserve["r_cycle_gpu_hours"]
    if closure:
        if launch_max_gpu_hours > r_cycle:
            raise InfrastructureError(
                f"closure maximum {launch_max_gpu_hours} exceeds the "
                f"reserved R_cycle {r_cycle}")
        if remaining_gpu_hours < launch_max_gpu_hours:
            raise InfrastructureError(
                f"remaining {remaining_gpu_hours} GPU-h cannot cover "
                f"the closure maximum {launch_max_gpu_hours}")
        return
    if remaining_gpu_hours < launch_max_gpu_hours + r_cycle:
        raise InfrastructureError(
            f"inadmissible launch: remaining {remaining_gpu_hours} "
            f"GPU-h < launch maximum {launch_max_gpu_hours} + R_cycle "
            f"{r_cycle} (211_f §10)")
