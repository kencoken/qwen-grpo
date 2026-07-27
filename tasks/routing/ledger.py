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
})
_ENTRY_KINDS = (
    "support_materialization", "resume_validation", "grouped_probe",
    "engineering_smoke", "standalone_evaluation", "training_run",
    "engineering_resume", "adaptive_continuation", "fork",
    "reserve_update", "cycle_closure", "cycle_synthesis",
)
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


def append_ledger_entry(entry: Mapping[str, Any],
                        path: str | Path = LEDGER_PATH
                        ) -> dict[str, Any]:
    """Verify the existing chain, then append — never rewrite. The
    entry is validated, chained to the last recorded hash, self-hashed
    and written as a new fenced block."""
    path = Path(path)
    existing = read_ledger(path)
    validate_entry(entry)
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
    """Consumed = sum of recorded consumption (falling back to the
    allocation for entries not yet closed out — a launch is charged
    its maximum until its measured cost is recorded)."""
    consumed = 0.0
    reserve = None
    for entry in entries:
        if entry["kind"] in ("reserve_update", "cycle_synthesis"):
            if entry["kind"] == "reserve_update":
                reserve = entry["reserve"]
            continue
        recorded = entry.get("budget_consumed_gpu_hours")
        if recorded is not None:
            if not isinstance(recorded, (int, float)) \
                    or isinstance(recorded, bool) or recorded < 0:
                raise InfrastructureError(
                    f"bad budget_consumed_gpu_hours {recorded!r}")
            consumed += recorded
        else:
            consumed += entry["budget_allocated_gpu_hours"]
    return {"envelope_gpu_hours": envelope_gpu_hours,
            "consumed_gpu_hours": consumed,
            "remaining_gpu_hours": envelope_gpu_hours - consumed,
            "reserve": reserve}


def check_launch_admissible(*, remaining_gpu_hours: float,
                            launch_max_gpu_hours: float,
                            reserve: Mapping[str, Any] | None,
                            closure: bool = False) -> None:
    """211_f §10 as corrected by 210_s issue 4. Ordinary pre-closure
    launches keep the reserve intact; closure consumes it. No reserve
    on record refuses BOTH paths — the provisional reserve exists from
    the support-materialization review onward."""
    if not isinstance(launch_max_gpu_hours, (int, float)) \
            or isinstance(launch_max_gpu_hours, bool) \
            or launch_max_gpu_hours <= 0:
        raise InfrastructureError(
            f"launch maximum must be > 0, got {launch_max_gpu_hours!r}")
    if reserve is None:
        raise InfrastructureError(
            "no reserve on record — set the provisional R_cycle at the "
            "support-materialization review before any launch "
            "(211_f §10)")
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
