"""P0 spine, Unit 4 — the GENERATED freeze tables (303_f §8; §9
step 4).

`generate_traceability_appendix()` renders the committed appendix
markdown ENTIRELY from the authenticated frozen artifacts (the
contract under its reviewed pin, the projection under both pins,
the pinned mixture, the replay-source constants). No number in the
appendix is hand-transcribed. The committed file is byte-checked
against a fresh generation in the test suite, making prose/number
divergence MECHANICALLY DETECTABLE for generated numerical fields
(303_f §8 — detectable, not "structurally impossible"; independent
invariants and human review remain in force)."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import InfrastructureError

from .p0_contract import (
    CONTRACT_PATH,
    CONTRACT_SHA256,
    load_p0_science_contract,
)
from .p0_replay import (
    PINNED_MIXTURE_FILE_SHA256,
    PINNED_MIXTURE_PATH,
    PROJECTION_FILE_SHA256,
    PROJECTION_PATH,
    PROJECTION_SHA256,
    REPLAY_SOURCE,
    load_pinned_mixture,
    load_projection,
)

APPENDIX_PATH = Path("plans/conductor/p0/p0_traceability_appendix.md")


def _row(*cells: Any) -> str:
    # pipe characters inside CELL CONTENT (e.g. the direction keys)
    # are escaped so the table structure survives rendering
    return "| " + " | ".join(
        str(cell).replace("|", "\\|") if str(cell) != "---"
        else "---" for cell in cells) + " |"


def _ints(values) -> str:
    return ", ".join(str(v) for v in values)


def generate_traceability_appendix() -> str:
    contract = load_p0_science_contract()
    projection = load_projection()
    mixture = load_pinned_mixture()
    pins = contract.input_pins
    lines: list[str] = []
    out = lines.append

    out("# P0 traceability appendix (GENERATED)")
    out("")
    out("**GENERATED FILE — do not edit.** Every value below is "
        "rendered from the authenticated frozen artifacts by "
        "`tasks/routing/p0_tables.py`; the committed bytes are "
        "compared against a fresh generation in the test suite, so "
        "an edited number diverges mechanically (303_f §8).")
    out("")

    out("## 1. Identities")
    out("")
    out(_row("artifact", "semantic sha256", "file sha256"))
    out(_row("---", "---", "---"))
    contract_file = hashlib.sha256(
        Path(CONTRACT_PATH).read_bytes()).hexdigest()
    out(_row("P0ScienceContract (`p0_science_contract.json`)",
             f"`{CONTRACT_SHA256}`", f"`{contract_file}`"))
    out(_row("compatibility projection "
             "(`c2_compatibility_projection.json`)",
             f"`{PROJECTION_SHA256}`",
             f"`{PROJECTION_FILE_SHA256}`"))
    out(_row("pinned mixture (`pinned_mixture_v2.json`)",
             f"`{mixture['record_sha256']}`",
             f"`{PINNED_MIXTURE_FILE_SHA256}`"))
    out("")
    out("Replay-source pins (Unit 1, all verified against the "
        "committed C2 evidence):")
    out("")
    out(_row("pin", "sha256"))
    out(_row("---", "---"))
    for name in sorted(REPLAY_SOURCE):
        out(_row(f"`{name}`", f"`{REPLAY_SOURCE[name]}`"))
    out("")

    out("## 2. Active scope (301_f)")
    out("")
    scope = contract.scope
    out(_row("field", "value"))
    out(_row("---", "---"))
    out(_row("Q1 direct cells", _ints(scope.q1_direct_cells)))
    out(_row("Q2", scope.q2_description))
    out(_row("Q3", scope.q3))
    out(_row("sentinel cell", scope.sentinel_cell))
    out(_row("sentinel observation ids",
             " / ".join(f"`{oid}`"
                        for oid in scope.sentinel_observation_ids)))
    out(_row("sentinel excluded from",
             _ints(scope.sentinel_excluded_from)))
    out(_row("sentinel training-exposed",
             scope.sentinel_training_exposed))
    out("")

    out("## 3. Q1 (rule `%s`, event `%s`)"
        % (contract.q1.version, contract.q1.event.rule_id))
    out("")
    event = contract.q1.event
    out("Counted event: a reward-%s completion of %s family "
        "correctness AND a reward-%s completion of %s family "
        "correctness, valid completions only, in the same group."
        % (event.high_reward, event.high_family_correctness,
           event.low_reward, event.low_family_correctness))
    out("")
    out("Gate: >= %d counted groups AND >= %d distinct latents per "
        "cell." % (contract.q1.min_counted_groups_per_cell,
                   contract.q1.min_distinct_latents_among_counted))
    out("")
    out(_row("cell", "C2 counted groups "
             f"(over {contract.q1.sizing_epochs} epochs)",
             "measured per-epoch rate", "bridge draws",
             "distinct latents", "pass"))
    out(_row("---", "---", "---", "---", "---", "---"))
    for cell, count in contract.q1.sizing_counts:
        gate = projection["q1_gate"][cell]
        out(_row(cell, count,
                 projection["q1_counted_per_epoch_measured"][cell],
                 gate["bridge_draws"],
                 _ints(gate["distinct_latents"]), gate["pass"]))
    out("")

    out("## 4. Q2 (rule `%s`) — the four separated quantities"
        % contract.q2.version)
    out("")
    q2 = contract.q2
    out("1. **Marginal** (`%s`): target selections over VALID "
        "completions regardless of upstream correctness; gate >= "
        "%d selections from >= %d distinct latents per direction."
        % (q2.marginal_rule_id, q2.marginal_min_target_selections,
           q2.marginal_min_distinct_latents))
    out("2. **Eligibility** (`%s`): %s non-Code routing, Code "
        "choice in %s, malformed %s."
        % (q2.eligibility.rule_id, q2.eligibility.non_code_routing,
           tuple(q2.eligibility.code_worker_in),
           q2.eligibility.malformed_completions))
    out("3. **Conditional** (`%s`): %s / %s; zero denominator = %s "
        "(never 0.0) — the P0 learning estimand."
        % (q2.conditional_rule_id, q2.conditional_numerator,
           q2.conditional_denominator,
           q2.conditional_zero_denominator))
    out("4. **Contrasts**: direct (both family-correct variants in "
        "one group) and semantic (reward levels 1 and 0.5 "
        "co-present).")
    out("")
    out(_row("direction", "target worker",
             "C2 marginal selections (baseline)",
             "distinct latents", "conditional baseline "
             "(optimal/eligible)", "gate pass"))
    out(_row("---", "---", "---", "---", "---", "---"))
    conditional = {b.direction: b for b in q2.conditional_baselines}
    marginal = dict(q2.marginal_baselines)
    for direction, worker in q2.per_direction_targets:
        gate = projection["q2_cold_start_gate"]["per_direction"][
            direction]
        baseline = conditional[direction]
        out(_row(direction, worker, marginal[direction],
                 len(gate["distinct_latents"]),
                 f"{baseline.numerator}/{baseline.denominator}",
                 gate["pass"]))
    out("")
    out("The asymmetric starting conditions (301_f) are carried as "
        "context: the conditional baselines above are materially "
        "different between directions.")
    out("")

    out("## 5. Sentinel (C2 checkpoint-zero block)")
    out("")
    sentinel = projection["sentinel_block"]
    out(_row("field", "value"))
    out(_row("---", "---"))
    for field in ("groups", "worker1_selections",
                  "worker1_completions", "reward1_completions",
                  "reward_varying_groups", "q1_counted_groups",
                  "first_worker1_group_index",
                  "first_worker1_update_index"):
        out(_row(f"`{field}`", sentinel[field]))
    out("")

    out("## 6. Sizing and the cap (rule `%s`)"
        % contract.sizing.cap.rule_id)
    out("")
    sizing = contract.sizing
    derived = projection["p0_size_derived"]
    out(_row("field", "value"))
    out(_row("---", "---"))
    out(_row("target Q1 counted groups per sizing cell",
             sizing.target_q1_counted_groups_per_sizing_cell))
    out(_row("groups per epoch", sizing.groups_per_epoch))
    out(_row("nominal epochs (C2-derived)", sizing.nominal_epochs))
    out(_row("derived groups", derived["derived_groups"]))
    out(_row("minimum cell", derived["min_cell"]))
    out(_row("operational ceiling (hours)",
             sizing.operational_ceiling_hours))
    out(_row("launch rule", f"`{sizing.cap.launch_epochs}` "
             "(launch = min(nominal, capacity))"))
    out(_row("capacity <= 0", f"`{sizing.cap.capacity_zero_action}`"))
    out(_row("capacity < nominal",
             f"`{sizing.cap.under_target_action}`"))
    out(_row("capacity >= nominal",
             f"`{sizing.cap.spare_capacity_action}`"))
    out(_row("registered capacity inputs",
             " / ".join(f"`{name}`"
                        for name in sizing.cap.capacity_inputs)))
    out("")

    out("## 7. C2 measured results (from the frozen projection)")
    out("")
    out(_row("population", "draws"))
    out(_row("---", "---"))
    for population, draws in sorted(
            projection["per_population_draws"].items()):
        out(_row(population, draws))
    out("")
    out(_row("quantity", "value"))
    out(_row("---", "---"))
    out(_row("valid completions", projection["valid_completions"]))
    out(_row("invalid completions",
             projection["invalid_completions"]))
    out(_row("zero-variance groups",
             projection["zero_variance_groups"]))
    out(_row("zero-variance fraction",
             projection["zero_variance_fraction"]))
    out(_row("Q1 gate (all cells)",
             projection["q1_gate_pass_all_cells"]))
    out(_row("Q2 cold-start gate",
             projection["q2_cold_start_gate"]["pass"]))
    out(_row("preregistered decision",
             f"**{projection['preregistered_decision']}**"))
    out("")

    out("## 8. Supersession and lineage (references)")
    out("")
    out("- Formal Q3 is out of scope (269_s; closed in 301_f); Q2 "
        "is authorized to be TRAINED, not shown learned (300_s/"
        "301_f).")
    out("- math_atomic is the training-exposed sentinel (283_s "
        "route; 290_f signed wrap-up; erratum 289_f) — excluded "
        "from gates, sizing, authorization, and headline Q1.")
    out("- The Unit-B mixture (274_f) is superseded by the B2 "
        "mixture (291_f-295_f); the C1 exposure sample (281_f) is "
        "superseded as the sizing basis by C2 (296_f-299_f, closed "
        "300_s/301_f).")
    out("- The spine artifacts derive from the signed plan chain "
        "287_f -> 303_f (rev2) -> 305_f (rev3); units 306_f/308_f, "
        "309_f/311_f, 312_f/314_f.")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def freeze_appendix(out_path: str | Path = APPENDIX_PATH) -> str:
    """Write the generated appendix. Regeneration is idempotent
    while the artifacts are frozen; the byte-equality test is the
    divergence gate."""
    out_path = Path(out_path)
    text = generate_traceability_appendix()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return text


def verify_appendix(path: str | Path = APPENDIX_PATH) -> dict[str, Any]:
    """The mechanical divergence gate: the committed appendix bytes
    must equal a fresh generation from the authenticated
    artifacts."""
    committed = Path(path).read_text("utf-8")
    generated = generate_traceability_appendix()
    if committed != generated:
        raise InfrastructureError(
            f"{path} diverges from the artifact-generated appendix "
            "— regenerate via freeze_appendix (never hand-edit)")
    return {"verdict": "PASS", "bytes": len(committed)}
