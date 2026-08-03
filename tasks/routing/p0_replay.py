"""P0 spine, Unit 1 — the authenticated C2 replay source and the
FROZEN compatibility projection (305_f §2; 302_s §3).

Two committed artifacts under `plans/conductor/p0/`:

- `pinned_mixture_v2.json` — the legacy B2 mixture record,
  materialized ONCE through the legacy builder and double-bound
  (file hash + the `135a72bf…` self-hash pin). Unit 2's schedule
  loader consumes THIS file, never the builder.
- `c2_compatibility_projection.json` — the expected canonical
  scientific projection of the C2 result, EXTRACTED from the
  authenticated archive and frozen BEFORE the Unit-3 evaluator
  exists. The Unit-3 evaluator (which never calls the legacy
  report builder and never reads this file's source report) must
  reproduce it exactly.

`verify_c2_replay_source()` is the Unit-1 authentication boundary:
ledger chain containing the C2 closeout, the closeout's complete
terminal inventory (verified BEFORE any replay), the reviewed
identity/environment anchors, the locked extension surface (with a
clean-clone restoration path), the frozen selection, the frozen
comparator, and the pinned-mixture artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tasks.conductor.types import InfrastructureError

from .charter import content_sha256

P0_DIR = Path("plans/conductor/p0")
PINNED_MIXTURE_PATH = P0_DIR / "pinned_mixture_v2.json"
PROJECTION_PATH = P0_DIR / "c2_compatibility_projection.json"

C2_EVIDENCE_DIR = Path("plans/conductor/evidence/unit_c2_v1")

# the authenticated replay-source pins (305_f §2; all verified
# against the committed archive at this freeze)
REPLAY_SOURCE = {
    "c2_closeout_entry_sha256":
        "2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558cf36174266fbe",
    "c2_actions_file_sha256":
        "8e705317676134df447b25a72532151c8068bb238a239facc266c1fb5525af34",
    "c2_report_file_sha256":
        "03152f0eaa7e83b34110dc6e53be550f0f761d6141861246a70f55f5587e3abe",
    "c2_schedule_file_sha256":
        "c2687919cd8a00768d9f5b148957f2c2013eb1b0a636f13ecb585d6bd5598b25",
    "c2_record_file_sha256":
        "cc42c16bd925282477746644e5959a5d5848c47e18308a8fc69a437fac8e27b6",
    "identity_manifest_sha256":
        "7b19aeb9a642478785db1aa0d24e9126cf6d6ad3358c46b6c6a44b4dd82514af",
    "attested_environment_sha256":
        "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
    "extension_surface_lock_sha256":
        "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
    "selection_record_sha256":
        "c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34",
    "selection_file_sha256":
        "e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724",
    "comparator_record_sha256":
        "9220c2c7a7efe890c60e5abbdcc3b84eecbbb971e75fa69e313e6d61888e5f1f",
    "pinned_mixture_record_sha256":
        "135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f",
}

# the canonical scientific fields the projection carries (302_s §3);
# identity fields expected to change under new source are EXCLUDED
_PROJECTION_REPORT_FIELDS = (
    "per_population_draws",
    "q1_gate", "q1_gate_pass_all_cells",
    "q1_counted_per_epoch_measured",
    "q2_blocks", "q2_cold_start_gate",
    "direct_specialist_control",
    "sentinel_block",
    "p0_size_derived",
    "strata",
    "zero_variance_groups", "zero_variance_fraction",
    "preregistered_decision",
)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore_extension_surface_if_absent() -> Path:
    """The clean-clone path (305_f §2): the canonical extension
    surface is reconstructed from committed evidence when absent —
    never depending on an earlier test having populated runs/."""
    from .support_run import restore_surface_evidence
    from .unit_c2_sample import UNIT_C2_CONFIG
    surface_dir = Path(UNIT_C2_CONFIG["extension_surface_dir"])
    if not (surface_dir / "surface_lock.json").exists():
        restore_surface_evidence(
            "plans/conductor/evidence/support_extension_v1/surface",
            surface_dir)
    return surface_dir


def verify_c2_replay_source(evidence_dir: str | Path | None = None,
                            ledger_path: str | Path | None = None
                            ) -> dict[str, Any]:
    """The Unit-1 authentication boundary (305_f §2). Verifies, in
    order: the ledger chain CONTAINS the C2 complete closeout with
    the frozen report/record bindings; the closeout's terminal
    inventory matches the evidence bytes EXACTLY (including the four
    pinned file hashes) BEFORE any replay; the identity/environment
    anchors; the locked extension surface (restored clean-clone if
    absent); the frozen selection; the frozen comparator; and the
    pinned-mixture artifact (file hash AND self-hash pin)."""
    from .dev_support import load_dev_surface
    from .ledger import LEDGER_PATH, ledger_head, verify_ledger_head
    from .p0_mixture_v2 import (
        EXPECTED_MIXTURE_V2_RECORD_SHA256,
        load_frozen_selection_v2,
    )
    from .unit_c2_sample import (
        UNIT_C2_CONFIG,
        load_extension_comparator,
    )
    evidence = Path(evidence_dir or C2_EVIDENCE_DIR)
    path = ledger_path or LEDGER_PATH
    pins = REPLAY_SOURCE

    # 1. the chain contains the C2 closeout, exactly once, complete
    entries = verify_ledger_head(ledger_head(path), path)
    matches = [e for e in entries if e.get("entry_sha256")
               == pins["c2_closeout_entry_sha256"]]
    if len(matches) != 1 \
            or matches[0].get("terminal_status") != "complete":
        raise InfrastructureError(
            "the C2 complete closeout is not present exactly once in "
            "the verified chain")
    closeout = matches[0]
    freeze = closeout.get("freeze", {})
    if freeze.get("exposure_report_file_sha256") != \
            pins["c2_report_file_sha256"] \
            or freeze.get("sample_record_file_sha256") != \
            pins["c2_record_file_sha256"]:
        raise InfrastructureError(
            "the C2 closeout does not bind the pinned report/record "
            "bytes")
    inventory = freeze.get("terminal_artifact_hashes")
    if not inventory:
        raise InfrastructureError(
            "the C2 closeout carries no terminal inventory")

    # 2. the evidence bytes ARE the closeout-bound inventory —
    # verified BEFORE any replay
    for name, pin_key in (
            ("actions.jsonl", "c2_actions_file_sha256"),
            ("exposure_report.json", "c2_report_file_sha256"),
            ("schedule.json", "c2_schedule_file_sha256"),
            ("sample_record.json", "c2_record_file_sha256")):
        digest = _sha_file(evidence / name)
        if digest != pins[pin_key]:
            raise InfrastructureError(
                f"{name}: evidence bytes do not match the pinned "
                f"hash (305_f §2)")
        if inventory.get(name) != digest:
            raise InfrastructureError(
                f"{name}: evidence bytes do not match the "
                "closeout-bound inventory")
    # every OTHER inventory file must match too where present
    for name, bound in inventory.items():
        member = evidence / name
        if member.exists() and _sha_file(member) != bound:
            raise InfrastructureError(
                f"{name}: evidence bytes diverge from the inventory")

    # 3. the anchors
    record = json.loads(
        (evidence / "sample_record.json").read_text("utf-8"))
    if record.get("identity_manifest_sha256") != \
            pins["identity_manifest_sha256"] \
            or record.get("attested_environment_sha256") != \
            pins["attested_environment_sha256"]:
        raise InfrastructureError(
            "the archived record does not carry the reviewed "
            "identity/environment anchors")

    # 4. the locked surface (clean-clone restore), selection,
    # comparator
    surface_dir = restore_extension_surface_if_absent()
    load_dev_surface(surface_dir, expected_lock_sha256=pins[
        "extension_surface_lock_sha256"])
    selection = load_frozen_selection_v2()
    if selection["record_sha256"] != pins["selection_record_sha256"]:
        raise InfrastructureError(
            "the frozen selection is not the pinned record")
    comparator = load_extension_comparator()
    if comparator["record_sha256"] != \
            pins["comparator_record_sha256"]:
        raise InfrastructureError(
            "the frozen comparator is not the pinned record")

    # 5. the pinned-mixture artifact (file + self-hash pin)
    mixture = load_pinned_mixture()
    if mixture["record_sha256"] != \
            EXPECTED_MIXTURE_V2_RECORD_SHA256:
        raise InfrastructureError(
            "the pinned-mixture artifact does not carry the pin")
    if UNIT_C2_CONFIG["mixture_record_sha256"] != \
            mixture["record_sha256"]:
        raise InfrastructureError(
            "the C2 config and the pinned artifact disagree")
    return {"verdict": "PASS",
            "closeout": pins["c2_closeout_entry_sha256"]}


# --- the pinned-mixture artifact -----------------------------------------------

def materialize_pinned_mixture(out_path: str | Path
                               = PINNED_MIXTURE_PATH
                               ) -> dict[str, Any]:
    """ONE-TIME materialization through the LEGACY builder from its
    authenticated inputs (302_s §4 step 1). Refuses to overwrite."""
    from .p0_mixture_v2 import (
        build_mixture_v2,
        load_frozen_selection_v2,
    )
    from .dev_support import load_dev_surface
    from .unit_c2_sample import UNIT_C2_CONFIG
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the pinned artifact is materialized "
            "exactly once")
    surface_dir = restore_extension_surface_if_absent()
    loaded = load_dev_surface(
        surface_dir,
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    mixture = build_mixture_v2(loaded, load_frozen_selection_v2())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(mixture, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return mixture


def load_pinned_mixture(path: str | Path = PINNED_MIXTURE_PATH
                        ) -> dict[str, Any]:
    """The strict artifact loader: self-hash must rehash AND equal
    the frozen pin. (Unit 2 builds the full schedule loader on top;
    this is the byte boundary.)"""
    from .p0_mixture_v2 import EXPECTED_MIXTURE_V2_RECORD_SHA256
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError(
            "pinned-mixture artifact does not rehash")
    if record["record_sha256"] != EXPECTED_MIXTURE_V2_RECORD_SHA256:
        raise InfrastructureError(
            "pinned-mixture artifact is not the frozen 135a72bf… "
            "candidate")
    return record


# --- the frozen compatibility projection ---------------------------------------

def extract_projection(evidence_dir: str | Path | None = None
                       ) -> dict[str, Any]:
    """EXTRACT the canonical scientific projection from the
    authenticated C2 archive (302_s §3). This extractor reads the
    LEGACY report — it exists to FREEZE the expected values before
    the Unit-3 evaluator is implemented; the evaluator itself never
    reads these sources. Identity fields expected to change under
    new source are excluded."""
    evidence = Path(evidence_dir or C2_EVIDENCE_DIR)
    report = json.loads(
        (evidence / "exposure_report.json").read_text("utf-8"))
    schedule = json.loads(
        (evidence / "schedule.json").read_text("utf-8"))
    record = json.loads(
        (evidence / "sample_record.json").read_text("utf-8"))
    valid = record["execution_telemetry"]["surface_reward_lookups"]
    total_completions = record["counters"]["sampled_completions"]
    projection = {
        "kind": "c2-compatibility-projection-v1",
        "source": {
            "closeout_entry_sha256":
                REPLAY_SOURCE["c2_closeout_entry_sha256"],
            "report_file_sha256":
                REPLAY_SOURCE["c2_report_file_sha256"],
            "schedule_file_sha256":
                REPLAY_SOURCE["c2_schedule_file_sha256"],
        },
        "epoch_rows": schedule[:157],
        "schedule_rows": schedule,
        "mixture_record_sha256": record["mixture_record_sha256"],
        "valid_completions": valid,
        "invalid_completions": total_completions - valid,
    }
    for field in _PROJECTION_REPORT_FIELDS:
        projection[field] = report[field]
    projection["projection_sha256"] = content_sha256(
        {k: v for k, v in projection.items()
         if k != "projection_sha256"})
    return projection


def freeze_projection(out_path: str | Path = PROJECTION_PATH
                      ) -> dict[str, Any]:
    """ONE-TIME freeze of the expected projection (refuses to
    overwrite): Unit 3's evaluator is compared against THESE bytes."""
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the projection is frozen exactly "
            "once")
    projection = extract_projection()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(projection, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return projection


def load_projection(path: str | Path = PROJECTION_PATH
                    ) -> dict[str, Any]:
    projection = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in projection.items()
            if k != "projection_sha256"}
    if content_sha256(body) != projection.get("projection_sha256"):
        raise InfrastructureError(
            "compatibility projection does not rehash")
    if projection.get("kind") != "c2-compatibility-projection-v1":
        raise InfrastructureError("unknown projection kind")
    return projection
