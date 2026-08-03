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

    out("## 5. Sentinel — the COMPLETE signed obligation set "
        "(305_f §4)")
    out("")
    out("Every field of "
        "`contract.diagnostics.sentinel.fields_required`, with its "
        "C2 checkpoint-zero value where the frozen projection "
        "carries it (316_s: nothing omitted — deferred fields are "
        "named as deferred, never dropped):")
    out("")
    sentinel = projection["sentinel_block"]
    firsts_families = ("worker1", "reward1", "varying",
                      "q1_counted")
    out(_row("required field", "C2 checkpoint-zero value",
             "source"))
    out(_row("---", "---", "---"))
    for field in contract.diagnostics.sentinel.fields_required:
        if field in ("worker1_selections", "worker1_completions",
                     "reward1_completions", "reward_varying_groups",
                     "q1_counted_groups"):
            out(_row(f"`{field}`", sentinel[field],
                     "frozen projection"))
        elif field == "group_denominator":
            out(_row(f"`{field}`", sentinel["groups"],
                     "frozen projection (`groups`)"))
        elif field == "completion_denominator":
            out(_row(f"`{field}`",
                     "computed by `sentinel_checkpoint_block` "
                     "(the legacy C2 block does not persist it)",
                     "every P0 checkpoint"))
        elif field == "first_group_indices":
            out(_row(f"`{field}`", "; ".join(
                f"{family}="
                f"{sentinel[f'first_{family}_group_index']}"
                for family in firsts_families),
                "frozen projection"))
        elif field == "first_update_indices":
            out(_row(f"`{field}`", "; ".join(
                f"{family}="
                f"{sentinel[f'first_{family}_update_index']}"
                for family in firsts_families),
                "frozen projection"))
        elif field in ("checkpoint_trajectory",
                       "evaluation_trajectory"):
            out(_row(f"`{field}`",
                     "assembled across checkpoints by "
                     "`p0_launch.assemble_sentinel_trajectories`",
                     "instance at the P0 run"))
        else:
            raise InfrastructureError(
                f"unmapped required sentinel field {field!r} — the "
                "appendix must be complete (316_s P1)")
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

    out("## 8. Signed traceability matrix (316_s)")
    out("")
    out("The merge-gated mapping: requirement → contract field → "
        "enforcement → regression → artifact. Deferred obligations "
        "are NAMED with their owner, never dropped.")
    out("")
    out(_row("requirement", "field", "enforcement", "regression",
             "artifact"))
    out(_row("---", "---", "---", "---", "---"))
    matrix = (
        ("Q1 counted event (305_f §3)",
         f"`q1.event` (`{event.rule_id}`)",
         "`p0_estimands.q1_counted_event` (closed literals "
         "operative)",
         "`test_p0_estimand_rules` incl. the semantic-not-Q1 "
         "counterexample",
         "contract"),
        ("Q1 direct gate",
         "`q1.min_counted_groups_per_cell` = "
         f"{contract.q1.min_counted_groups_per_cell}; "
         "`q1.min_distinct_latents_among_counted` = "
         f"{contract.q1.min_distinct_latents_among_counted}",
         "`p0_estimands.evaluate_q1_gate`",
         "`test_p0_estimand_rules`; oracle `q1_gate` equality",
         "contract + projection"),
        ("Q1 population = bridge rows",
         "`scope.q1_direct_cells`; mixture `class_assignment`",
         "`derive_from_trace` population binding; "
         "`p0_schedule.population_of` (authenticated internal "
         "load)",
         "`test_p0_c2_replay_sensitivity` population substitution; "
         "310_s forged-mixture regression",
         "mixture"),
        ("Q2 marginal cold-start gate",
         f"`q2.marginal_*` (`{q2.marginal_rule_id}`)",
         "`marginal_target_selection` + "
         "`evaluate_q2_cold_start_gate` (structurally never "
         "conditional)",
         "`test_p0_estimand_rules` incl. the "
         "marginal-not-conditional counterexample",
         "contract"),
        ("Q2 eligibility",
         f"`q2.eligibility` (`{q2.eligibility.rule_id}`)",
         "`c2_eligible_completion` + `valid_assignment`",
         "313_s malformed-assignment regressions",
         "contract"),
        ("Q2 conditional choice",
         f"`q2.conditional_*` (`{q2.conditional_rule_id}`); zero "
         f"denominator = {q2.conditional_zero_denominator}",
         "`conditional_choice` (None, never 0.0)",
         "`test_p0_estimand_rules`",
         "contract"),
        ("Q2 contrasts",
         "`diagnostics.items`",
         "`group_contrasts` (cell-aware, valid assignments only)",
         "`test_p0_estimand_rules`",
         "contract"),
        ("Sentinel complete block (305_f §4)",
         "`diagnostics.sentinel.fields_required` (see §5)",
         "`sentinel_checkpoint_block` + `sentinel_legacy_view`",
         "`test_p0_sentinel_estimand` ([2]/[3]; population bound; "
         "forged index)",
         "contract + projection"),
        ("Schedule identity",
         f"`sizing.groups_per_epoch` = "
         f"{contract.sizing.groups_per_epoch}; mixture pins",
         "`p0_schedule` double bindings; `derive_from_trace` "
         "physical-position binding",
         "`test_p0_schedule_loader_reminders`; 313_s same-id swap",
         "mixture"),
        ("Exact C2 equivalence (303_f §3)",
         "every projection field",
         "`verify_c2_equivalence` (field-for-field + pin rehash)",
         "`test_p0_c2_replay_equivalence` under independence "
         "guards",
         "projection"),
        ("Sizing derivation",
         "`q1.sizing_counts`; `sizing.nominal_epochs` = "
         f"{contract.sizing.nominal_epochs}",
         "`p0_estimands.derive_sizing`; "
         "`_validate_against_projection`",
         "`test_p0_estimand_rules`; "
         "`test_p0_contract_cross_checks_the_projection`",
         "contract + projection"),
        ("Cap + launch (305_f §5)",
         f"`sizing.cap` (`{contract.sizing.cap.rule_id}`)",
         "`p0_cap.derive_launch_plan`; `require_launchable` "
         "(rederive-and-compare, type-sensitive)",
         "`test_p0_cap_arithmetic` (branches; legacy parity; "
         "forged plans)",
         "contract"),
        ("Launch-freeze persistence (all cap inputs + all three "
         "values)",
         "the `derive_launch_plan` record",
         "`p0_launch.build_p0_launch_freeze` (admits through "
         "`require_launchable`; typed `LaunchPlan` must round-trip "
         "to the record VERBATIM; stop branch unfreezable)",
         "`test_p0_launch_freeze_schema`",
         "P0LaunchFreeze schema (instance frozen post-merge, after "
         "val/cycle/beta)"),
        ("Checkpoint/evaluation trajectories",
         "`diagnostics.sentinel.fields_required` trajectories",
         "`p0_launch.assemble_sentinel_trajectories` (exact frozen "
         "index sets w/ mandatory checkpoint zero and final; "
         "semantic counter/denominator/first-index validation; "
         "deep-copied blocks; explicit infrastructure-abort "
         "prefix). The EXPECTED INDEX SETS themselves remain "
         "DEFERRED: frozen with the real P0LaunchFreeze instance "
         "(post-merge)",
         "`test_p0_sentinel_trajectories`",
         "P0 run record (instance at the P0 run)"),
        ("Dataset preparation (the first real consumer)",
         "`P0LaunchFreeze` (all fields; execution-manifest hash "
         "and terminal hashes excluded by the closed schema)",
         "`p0_launch.prepare_p0_dataset` (freeze under its "
         "REQUIRED reviewed hash; contract pin equality; plan "
         "REDERIVED; runtime BOUND to the canonical profile + the "
         "ACTUAL prompt; fresh `verify_c2_equivalence` + "
         "`verify_appendix`; strict schedule loader)",
         "`test_p0_first_consumer_prepare`",
         "dataset bundle (runtime; never an authorization)"),
        ("Launch admission (execution + precursor binding)",
         "precursor pins; `runtime.attested_environment_sha256`; "
         "the EXTERNAL execution-manifest argument (305_f §1); "
         "cadence/eval/telemetry identity",
         "**DEFERRED** to the post-merge unit constructing the "
         "real `P0LaunchFreeze` instance — the precursor "
         "artifacts do not exist yet, so their resolution cannot "
         "be genuinely enforced and is NOT marked complete "
         "(321_s)",
         "DEFERRED (post-merge)",
         "P0LaunchFreeze instance + admission record (future)"),
        ("Appendix divergence gate (303_f §8)",
         "this file",
         "`verify_appendix` (raw byte equality)",
         "`test_p0_traceability_appendix` (edited number; CRLF "
         "rewrite; diverging artifact)",
         "appendix"),
    )
    for row in matrix:
        out(_row(*row))
    out("")

    out("## 9. Supersession and lineage (references)")
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
    """The mechanical divergence gate, BYTE-exact (316_s P2): the
    committed RAW BYTES must equal the UTF-8 encoding of a fresh
    generation — a CRLF rewrite or any re-encoding refuses, not
    only textual edits."""
    committed = Path(path).read_bytes()
    generated = generate_traceability_appendix().encode("utf-8")
    if committed != generated:
        raise InfrastructureError(
            f"{path} diverges from the artifact-generated appendix "
            "— regenerate via freeze_appendix (never hand-edit)")
    return {"verdict": "PASS", "bytes": len(committed)}
