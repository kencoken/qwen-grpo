"""Step-6 zero-effective-update grouped probe (211_f §5 as amended
by 248_s F1; the REGISTERED exposure measurement — 232_s/244_s:
Stage 5's six groups must NOT be used to estimate routing exposure
or size P0).

The signed cohort/sampling design, unchanged: the bound outcome-blind cohort
`7f31bd09…` (108 observations selected by the frozen first-probe
rule `0b616b88…` before any outcome existed), G=8, 4 groups per
observation — 432 groups, 3,456 completions — through the ACTUAL
training rollout path: the exact P0 trainer construction validated
by Step 5 (NF4 Qwen2.5-3B base, fp32 LoRA adapters at
checkpoint-zero, one group per optimizer step, the same tokenizer /
prompt / generation semantics), with ZERO model mutation.

Zero-update contract, AMENDED AND RE-FROZEN here (248_s F1 — this
deliberately amends the literal 211_f §5 "zero optimizer updates"
wording): 432 REAL trainer optimizer-step calls run at
`learning_rate = 0.0` and `beta = 0.0` — zero EFFECTIVE parameter
updates, with exact checkpoint-zero adapter equality PROVEN by
persisted hash maps; optimizer, scheduler and RNG state evolve,
which is the point — the probe exercises P0's real
between-generation training path rather than a rollout-only special
path.

Lifecycle identical to the validated Step-5 shape: four reviewed
launch hashes (freeze / static identity / attested environment /
ledger head), session preflight and prelaunch evidence persisted
BEFORE the irreversible admission, per-step deadline under the
charter's 3 GPU-hour probe ceiling, aborted closeouts with measured
cost and a content-hashed partial inventory, and an independent
archive verifier that rederives the report from the traces alone.

The probe's outputs are development data; its measured exposure
rates (through `telemetry.probe_report`, the reviewed boundary) are
EVIDENCE for the P0 design, never pass/fail thresholds (211_f §5).
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import InfrastructureError

from . import checkpoint as ckpt
from .charter import PROBE_CEILING_HOURS, content_sha256
from .dev_support import load_dev_surface
from .resume_validation import (
    attested_environment_sha256, make_validation_reward, read_trace,
    tensor_state_hashes,
)

PROBE_RULE_PATH = Path(
    "plans/conductor/routing_dev_support_prelaunch/probe_rule.json")

PROBE_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-grouped-probe-v1",
    # the Step-4 locked surface and its bound outcome-blind cohort
    "surface_lock_sha256": ("61c4e85a53683c9e2dbcbf15f60794935a76a"
                            "86d979a69412a97f44ea9f2562b"),
    "surface_dir": "runs/routing-dev/support-v1/surface",
    "probe_rule_sha256": ("0b616b8863bf73263c11c63cd8cc1572b880e658"
                          "6f15059bde642c2a397c9f7b"),
    "probe_cohort_sha256": ("7f31bd091aaa97664e71ecb86b17078861b4e2"
                            "8af284162ee6ac50338d661e3b"),
    # the exact P0 checkpoint-zero construction VALIDATED by Step 5
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "quantization": {"load_in_4bit": True, "quant_type": "nf4",
                     "double_quant": True, "compute_dtype": "bfloat16"},
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
             "adapter_dtype": "float32",
             "targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"]},
    # 244_s: sampling seeds, grouping semantics, generation config —
    # all frozen; lr/beta = 0 is the zero-update mechanism
    "grpo": {"beta": 0.0, "group_size": 8, "temperature": 1.0,
             "per_device_batch": 2, "grad_accum": 4,
             "learning_rate": 0.0, "warmup_steps": 0,
             "scheduler": "constant", "loss": "dapo",
             "optim": "adamw_torch", "bf16": True, "seed": 20260729},
    "policy_max_new_tokens": 128,
    "groups_per_observation": 4,
    "total_groups": 432,           # 108 observations × 4
    # 248_s F1: the AMENDED, re-frozen contract — not the literal
    # 211_f §5 wording: 432 real trainer optimizer-step calls at
    # learning rate zero; zero EFFECTIVE parameter updates and exact
    # checkpoint-zero adapter equality (optimizer/scheduler/RNG state
    # evolve, exercising P0's real between-generation training path).
    "zero_update_mechanism": ("432 real trainer optimizer-step calls "
                              "at learning_rate=0 and beta=0; zero "
                              "effective parameter updates; exact "
                              "checkpoint-zero adapter equality"),
    "full_determinism": True,
    "release_max_allocated_mib": 1024,
    "min_free_vram_mib": 20000,
    # the charter's probe ceiling (211_f §5), exact
    "ceiling_gpu_hours": PROBE_CEILING_HOURS,
    "run_root": "runs/routing-dev/probe-v1",
    "lineage": {
        "motivating_evidence":
            ("246_f Step-5 pass (closeout 1a8d41fd…); 231_f bound "
             "cohort 7f31bd09…; 211_f §5 / 232_s registered design"),
        "parent_entry_sha256":
            ("1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44"
             "fa8ea9b6a44a"),
        "outcome_informed": False,
    },
}

CONFIG_SHA256 = content_sha256(PROBE_CONFIG)


def tranche_freeze() -> dict[str, Any]:
    from .charter import lightweight_freeze
    return lightweight_freeze({
        "kind": "grouped_probe",
        "question": ("What exposure do REAL grouped G=8 rollouts "
                     "contain on the outcome-blind routing_dev "
                     "support — structured-action validity, family "
                     "routing, semantic reward variance, and actual "
                     "specialist co-sampling — versus the B "
                     "iid-singleton plug-ins?"),
        "motivation": "211_f §5 / §15 step 6; 232_s sequence item 4",
        "config": PROBE_CONFIG,
        "budget_gpu_hours": PROBE_CONFIG["ceiling_gpu_hours"],
    })


# --- frozen inputs (CPU-testable) ----------------------------------------------

def load_frozen_rule() -> dict[str, Any]:
    """The committed first-probe rule bytes, revalidated against the
    frozen hash."""
    from .cohorts import validate_probe_rule
    frozen = json.loads(PROBE_RULE_PATH.read_text("utf-8"))
    validate_probe_rule(frozen)
    if frozen["rule_sha256"] != PROBE_CONFIG["probe_rule_sha256"]:
        raise InfrastructureError(
            "committed probe rule is not the frozen one")
    return frozen


def load_locked_support(surface_dir: str | Path | None = None
                        ) -> dict[str, Any]:
    return load_dev_surface(
        surface_dir or PROBE_CONFIG["surface_dir"],
        expected_lock_sha256=PROBE_CONFIG["surface_lock_sha256"])


def bound_cohort(surface_dir: str | Path | None = None
                 ) -> dict[str, Any]:
    """Rederive the bound cohort from the frozen rule + locked
    surface and require it to BE the frozen binding (220_s F3
    discipline at the probe boundary)."""
    from .cohorts import bind_probe_cohort
    frozen = load_frozen_rule()
    surface_dir = Path(surface_dir or PROBE_CONFIG["surface_dir"])
    record = bind_probe_cohort(frozen, surface_dir,
                               PROBE_CONFIG["surface_lock_sha256"])
    if record["cohort_sha256"] != PROBE_CONFIG["probe_cohort_sha256"]:
        raise InfrastructureError(
            "rederived probe cohort is not the frozen binding")
    return record


def probe_schedule(loaded: Mapping[str, Any],
                   cohort: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One dataset row per GROUP: each bound observation, in bound
    order, repeated `groups_per_observation` times consecutively —
    432 rows, each consumed by exactly one optimizer step (= one
    generation of G=8)."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot
    per_observation = PROBE_CONFIG["groups_per_observation"]
    meta = {obs["observation_id"]: obs
            for obs in loaded["observations"]}
    system = prompt_fewshot()
    rows = []
    for oid in cohort["observation_ids"]:
        obs = meta[oid]
        latent = program.generate_latent(
            obs["cell_id"], "routing_dev", int(oid.split(":")[2]),
            DEFAULT_PROFILE).latent
        inst = program.render_instance(latent, obs["renderer_id"],
                                       oid.split(":")[5])
        if inst["render_instance_id"] != oid:
            raise InfrastructureError(
                f"regenerated instance != scheduled {oid}")
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(latent)]
        user = policy_messages(inst, steps)[1]
        row = {
            "prompt": [{"role": "system", "content": system},
                       dict(user)],
            "observation_id": oid,
            "cell_id": obs["cell_id"],
            "num_steps": len(steps),
            "positions": json.dumps(
                latent["reference_program"]["positions"]),
        }
        rows.extend(dict(row) for _ in range(per_observation))
    if len(rows) != PROBE_CONFIG["total_groups"]:
        raise InfrastructureError(
            f"schedule has {len(rows)} rows; the frozen design needs "
            f"{PROBE_CONFIG['total_groups']}")
    return rows


def static_identity_manifest(loaded: Mapping[str, Any],
                             cohort: Mapping[str, Any]
                             ) -> dict[str, Any]:
    from tasks.conductor.stage1 import prompt_fewshot
    from .charter import routing_execution_digest
    digest = routing_execution_digest("tasks/routing/probe_run.py")
    lock = loaded["lock"]
    manifest = {
        "kind": "routing-dev-probe-identity-v1",
        "routing_source_sha256": digest["routing_source_sha256"],
        "config_sha256": CONFIG_SHA256,
        "surface_manifest_sha256": lock["manifest_sha256"],
        "surface_lock_sha256": lock["lock_sha256"],
        "worker_pool_fingerprint": lock["worker_pool_fingerprint"],
        "cache_identity": lock["cache_identity"],
        "probe_rule_sha256": PROBE_CONFIG["probe_rule_sha256"],
        "probe_cohort_sha256": cohort["cohort_sha256"],
        "training_cohort_sha256": content_sha256(
            list(cohort["observation_ids"])),
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "seed": str(PROBE_CONFIG["grpo"]["seed"]),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


# --- report construction (CPU-testable) -----------------------------------------

def groups_from_trace(trace_rows: list[Mapping[str, Any]],
                      loaded: Mapping[str, Any],
                      c_fixed_record: Mapping[str, Any]
                      ) -> list[dict[str, Any]]:
    """Rebuild authenticated `group_stats` inputs from persisted
    trace rows. 248_s F2: NOTHING persisted is trusted — every
    completion text is re-parsed with the frozen
    `parse_routing_action`, its semantic assignment re-derived
    through the frozen positional mapping, and its reward re-derived
    from the locked surface; the stored action/assignment/reward
    must MATCH, and unequal parallel-array lengths refuse (no zip()
    truncation)."""
    from tasks.conductor import program
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import ActionSchemaError, \
        parse_routing_action
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from . import telemetry
    group_size = PROBE_CONFIG["grpo"]["group_size"]
    surface = loaded["surface"]
    meta = {obs["observation_id"]: obs
            for obs in loaded["observations"]}
    positions_cache: dict[str, list[str]] = {}
    groups = []
    for row in trace_rows:
        oid = row["observation_id"]
        if oid not in meta:
            raise InfrastructureError(
                f"trace row names foreign observation {oid}")
        arrays = (row["completions"], row["actions"],
                  row["assignments"], row["rewards"])
        if not all(len(a) == group_size for a in arrays):
            raise InfrastructureError(
                f"trace row {row.get('global_group_index')}: parallel "
                f"arrays are not all length {group_size} (248_s F2)")
        if oid not in positions_cache:
            obs = meta[oid]
            latent = program.generate_latent(
                obs["cell_id"], "routing_dev",
                int(oid.split(":")[2]), DEFAULT_PROFILE).latent
            positions_cache[oid] = \
                latent["reference_program"]["positions"]
        positions = positions_cache[oid]
        num_steps = len(positions)
        completions = []
        for text_, action, assignment, reward in zip(*arrays):
            try:
                json.loads(text_)
                parseable = True
            except (ValueError, UnicodeDecodeError):
                parseable = False
            try:
                reparsed = parse_routing_action(text_, num_steps)
            except ActionSchemaError:
                reparsed = None
            if reparsed is None:
                if action is not None or assignment is not None \
                        or reward != 0.0:
                    raise InfrastructureError(
                        f"{oid}: stored action/assignment/reward "
                        "disagree with the re-parse (malformed "
                        "completion recorded as valid; 248_s F2)")
                completions.append({"parseable": parseable,
                                    "valid": False,
                                    "assignment": None,
                                    "reward": 0.0})
                continue
            semantic = tuple(positional_to_semantic(reparsed,
                                                    positions))
            payoff = surface.get((oid, semantic))
            if payoff is None:
                raise InfrastructureError(
                    f"({oid}, {semantic}): no surface row")
            if action != list(reparsed) \
                    or assignment != list(semantic) \
                    or reward != float(payoff):
                raise InfrastructureError(
                    f"{oid}: stored action/assignment/reward "
                    f"({action}/{assignment}/{reward}) do not match "
                    f"the re-derivation ({list(reparsed)}/"
                    f"{list(semantic)}/{float(payoff)}) (248_s F2)")
            completions.append({"parseable": True, "valid": True,
                                "assignment": assignment,
                                "reward": reward})
        groups.append(telemetry.group_stats(
            {"observation_id": oid, "completions": completions},
            loaded=loaded, c_fixed_record=c_fixed_record))
    return groups


def load_c_fixed_record() -> dict[str, Any]:
    record = json.loads(Path(
        "plans/conductor/evidence/routing_dev_support_v1/"
        "c_fixed_dev.json").read_text("utf-8"))
    return record


def build_probe_report(run_root: str | Path) -> dict[str, Any]:
    """The report through the REVIEWED boundary
    (`telemetry.probe_report`): exact ids, multiplicities and group
    size against the frozen bound cohort + rule."""
    from . import telemetry
    run_root = Path(run_root)
    loaded = load_locked_support()
    cohort = bound_cohort()
    frozen_rule = load_frozen_rule()
    trace_rows = read_trace(run_root / "actions.jsonl")
    groups = groups_from_trace(trace_rows, loaded,
                               load_c_fixed_record())
    report = telemetry.probe_report(groups, loaded=loaded,
                                    bound_cohort=cohort,
                                    frozen_rule=frozen_rule)
    report["support_matrix"] = support_matrix(groups)
    return report


def support_matrix(groups: list[Mapping[str, Any]]) -> dict[str, int]:
    """248_s smaller item: the COMPLETE cell × renderer × direction
    grid, including zero-denominator combinations, so the later P0
    transport gate can mechanically reject unmeasured strata."""
    from tasks.conductor.types import CELL_IDS, RENDERER_IDS
    directions = ("w2_favoured", "w3_favoured", "tied", "no_pair")
    matrix = {f"{cell}|{renderer}|{direction}": 0
              for cell in CELL_IDS for renderer in RENDERER_IDS
              for direction in directions}
    for g in groups:
        key = f"{g['cell_id']}|{g['renderer_id']}|{g['direction']}"
        matrix[key] += 1
    return matrix


def _verify_probe_preflight(preflight: Mapping[str, Any]) -> None:
    """Preflight acceptance semantics against the PROBE's frozen
    floor (the 241_s pattern)."""
    if set(preflight) != {"free_mib", "total_mib", "floor_mib"}:
        raise InfrastructureError("preflight schema is not exact")
    for field in ("free_mib", "total_mib", "floor_mib"):
        value = preflight[field]
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 0:
            raise InfrastructureError(
                f"preflight {field} must be a non-negative int")
    if preflight["floor_mib"] != PROBE_CONFIG["min_free_vram_mib"]:
        raise InfrastructureError(
            "preflight floor is not the frozen one")
    if preflight["free_mib"] < preflight["floor_mib"]:
        raise InfrastructureError(
            "the archived preflight FAILED (free < floor)")
    if preflight["total_mib"] < preflight["free_mib"]:
        raise InfrastructureError("preflight total < free")


def verify_probe_run(run_root: str | Path,
                     expected_identity_sha256: str,
                     expected_environment_sha256: str
                     ) -> dict[str, Any]:
    """The independent archive verifier (248_s F3): from persisted
    bytes alone it rehashes and cross-binds the environment (self-
    hash + attested identity), the identity manifest, the preflight
    (values AND acceptance semantics), the bound cohort and the fully
    rederived 432-row schedule, the exact trace cardinality / order /
    observation ids / global indices, the record headers and frozen
    identities, the zero-mutation gate over the TWO PERSISTED hash
    maps, the design-derived counters, the complete execution-
    telemetry schema, and the exact rederivation of the persisted
    report.

    250_s P1 — external root of trust: internal coherence is not
    identity. A coherently relabelled archive (manifests altered,
    REHASHED, record pointers updated) is self-consistent, so the
    verifier REQUIRES the two REVIEWED launch identities and anchors
    both manifests and the record fields to them."""
    from .dev_support import validate_env_self_hash
    run_root = Path(run_root)
    record = json.loads(
        (run_root / "probe_record.json").read_text("utf-8"))
    if record["config_sha256"] != CONFIG_SHA256 \
            or record["tranche"] != PROBE_CONFIG["tranche"] \
            or record["freeze_sha256"] != \
            tranche_freeze()["freeze_sha256"]:
        raise InfrastructureError(
            "probe record does not match the frozen configuration")
    # environment: self-hash + attested binding
    archived_env = json.loads(
        (run_root / "environment_manifest.json").read_text("utf-8"))
    if validate_env_self_hash(archived_env) != \
            record["environment_manifest_sha256"]:
        raise InfrastructureError(
            "archived environment does not match the record")
    if attested_environment_sha256(archived_env) != \
            record["attested_environment_sha256"]:
        raise InfrastructureError(
            "archived environment does not match the attested binding")
    if record["attested_environment_sha256"] != \
            expected_environment_sha256:
        raise InfrastructureError(
            "archived environment is not the REVIEWED one (250_s P1: "
            "coherent relabelling refused by the external anchor)")
    # identity manifest: rehash + record binding + frozen fields
    identity_manifest = json.loads(
        (run_root / "identity_manifest.json").read_text("utf-8"))
    identity_body = {k: v for k, v in identity_manifest.items()
                     if k != "manifest_sha256"}
    if content_sha256(identity_body) != \
            identity_manifest["manifest_sha256"] \
            or identity_manifest["manifest_sha256"] != \
            record["identity_manifest_sha256"]:
        raise InfrastructureError(
            "archived identity manifest does not rehash or bind")
    if identity_manifest["manifest_sha256"] != expected_identity_sha256:
        raise InfrastructureError(
            "archived identity manifest is not the REVIEWED one "
            "(250_s P1: coherent relabelling refused by the external "
            "anchor)")
    if identity_manifest["config_sha256"] != CONFIG_SHA256 \
            or identity_manifest["probe_rule_sha256"] != \
            PROBE_CONFIG["probe_rule_sha256"] \
            or identity_manifest["probe_cohort_sha256"] != \
            PROBE_CONFIG["probe_cohort_sha256"] \
            or identity_manifest["surface_lock_sha256"] != \
            PROBE_CONFIG["surface_lock_sha256"]:
        raise InfrastructureError(
            "identity manifest fields do not match the frozen "
            "configuration")
    # preflight: hash + acceptance semantics
    preflight = json.loads(
        (run_root / "session_preflight.json").read_text("utf-8"))
    if content_sha256(preflight) != \
            record["session_preflight_sha256"] \
            or record["session_preflight"] != preflight:
        raise InfrastructureError(
            "archived preflight does not match the record")
    _verify_probe_preflight(preflight)
    # bound cohort: rehash + frozen binding; schedule: fully
    # rederived from the cohort
    archived_cohort = json.loads(
        (run_root / "bound_cohort.json").read_text("utf-8"))
    cohort_body = {k: v for k, v in archived_cohort.items()
                   if k != "cohort_sha256"}
    if content_sha256(cohort_body) != \
            archived_cohort["cohort_sha256"] \
            or archived_cohort["cohort_sha256"] != \
            PROBE_CONFIG["probe_cohort_sha256"] \
            or record["probe_cohort_sha256"] != \
            archived_cohort["cohort_sha256"]:
        raise InfrastructureError(
            "archived cohort does not rehash to the frozen binding")
    per_observation = PROBE_CONFIG["groups_per_observation"]
    expected_schedule = [oid
                         for oid in archived_cohort["observation_ids"]
                         for _ in range(per_observation)]
    schedule = json.loads(
        (run_root / "schedule.json").read_text("utf-8"))
    if schedule != expected_schedule:
        raise InfrastructureError(
            "archived schedule does not rederive from the bound "
            "cohort (248_s F3)")
    # traces: exact cardinality, order, ids, global indices
    trace_rows = read_trace(run_root / "actions.jsonl")
    total = PROBE_CONFIG["total_groups"]
    if len(trace_rows) != total:
        raise InfrastructureError(
            f"trace has {len(trace_rows)} groups; the design needs "
            f"{total}")
    for i, row in enumerate(trace_rows):
        if row["global_group_index"] != i \
                or row["observation_id"] != schedule[i]:
            raise InfrastructureError(
                f"trace row {i} violates the frozen schedule/order")
    # zero-mutation gate over the TWO PERSISTED maps
    zero_map = json.loads(
        (run_root / "checkpoint_zero_hashes.json").read_text("utf-8"))
    final_map = json.loads(
        (run_root / "checkpoint_final_hashes.json").read_text("utf-8"))
    if zero_map != final_map:
        differing = sorted(k for k in set(zero_map) | set(final_map)
                           if zero_map.get(k) != final_map.get(k))
        raise InfrastructureError(
            f"zero-mutation gate FAILS on the persisted maps "
            f"({differing[:3]}…)")
    if content_sha256(zero_map) != \
            record["checkpoint_zero_adapter_sha256"] \
            or content_sha256(final_map) != \
            record["final_adapter_sha256"]:
        raise InfrastructureError(
            "persisted hash maps do not match the record digests")
    # counters: design-derived
    group_size = PROBE_CONFIG["grpo"]["group_size"]
    expected_counters = {
        "generated_groups": total, "consumed_groups": total,
        "optimizer_updates": total,
        "sampled_completions": total * group_size}
    if record["counters"] != expected_counters:
        raise InfrastructureError(
            f"counters {record['counters']} != the design-derived "
            f"{expected_counters}")
    # execution telemetry: complete schema + rederivable parts
    # (250_s nonblocking tightening)
    telemetry_block = record["execution_telemetry"]
    if set(telemetry_block) != {
            "group_accounting", "surface_reward_lookups",
            "live_worker_calls", "worker_cache", "wall_seconds",
            "deadline_seconds", "peak_reserved_vram_mib",
            "session_preflight"}:
        raise InfrastructureError(
            "execution-telemetry schema is not exact")
    valid_completions = sum(
        1 for row in trace_rows for action in row["actions"]
        if action is not None)
    if telemetry_block["surface_reward_lookups"] != valid_completions:
        raise InfrastructureError(
            "surface-lookup count does not rederive from the traces")
    if telemetry_block["live_worker_calls"] != 0:
        raise InfrastructureError(
            "the probe performs no live worker calls")
    if telemetry_block["group_accounting"] != record["counters"]:
        raise InfrastructureError(
            "telemetry group accounting does not equal the counters")
    if telemetry_block["session_preflight"] != preflight:
        raise InfrastructureError(
            "telemetry preflight does not equal the archived one")
    if telemetry_block["deadline_seconds"] != \
            PROBE_CONFIG["ceiling_gpu_hours"] * 3600.0:
        raise InfrastructureError(
            "telemetry deadline is not the frozen ceiling")
    wall = telemetry_block["wall_seconds"]
    vram = telemetry_block["peak_reserved_vram_mib"]
    if not (isinstance(wall, (int, float)) and math.isfinite(wall)
            and wall >= 0):
        raise InfrastructureError(
            "telemetry wall_seconds must be finite and non-negative")
    if not (isinstance(vram, int) and vram >= 0):
        raise InfrastructureError(
            "telemetry peak VRAM must be a non-negative int")
    # the report itself: exact rederivation
    rederived = build_probe_report(run_root)
    persisted = json.loads(
        (run_root / "probe_report.json").read_text("utf-8"))
    if persisted != json.loads(json.dumps(rederived)):
        raise InfrastructureError(
            "persisted probe report does not rederive from the "
            "archived traces")
    return {"verdict": "PASS", "groups": total}


# --- the GPU run ----------------------------------------------------------------

def _build_probe_trainer(rows, reward, run_dir: Path,
                         extra_callbacks=()):
    """The exact P0 checkpoint-zero construction validated by Step 5
    (fp32 adapters), with the probe's frozen zero-update
    hyperparameters."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer

    import random

    import numpy
    config = PROBE_CONFIG
    grpo = config["grpo"]
    seed = grpo["seed"]
    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    processing_class = AutoTokenizer.from_pretrained(
        config["model_id"], revision=config["revision"])
    args = GRPOConfig(
        output_dir=str(run_dir), run_name=run_dir.name,
        seed=seed, num_generations=grpo["group_size"],
        max_completion_length=config["policy_max_new_tokens"],
        temperature=float(grpo["temperature"]),
        per_device_train_batch_size=grpo["per_device_batch"],
        gradient_accumulation_steps=grpo["grad_accum"],
        learning_rate=float(grpo["learning_rate"]),
        lr_scheduler_type=grpo["scheduler"],
        warmup_steps=grpo["warmup_steps"], beta=float(grpo["beta"]),
        max_steps=config["total_groups"], loss_type=grpo["loss"],
        shuffle_dataset=False, eval_strategy="no",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"],
        full_determinism=config["full_determinism"],
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": config["revision"],
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16)},
        optim=grpo["optim"], report_to="none", logging_steps=16,
        save_strategy="no")
    peft_config = LoraConfig(
        r=config["lora"]["r"], lora_alpha=config["lora"]["alpha"],
        lora_dropout=config["lora"]["dropout"],
        target_modules=list(config["lora"]["targets"]),
        task_type="CAUSAL_LM")
    trainer = GRPOTrainer(
        model=config["model_id"], args=args,
        train_dataset=Dataset.from_list(list(rows)),
        processing_class=processing_class, reward_funcs=[reward],
        peft_config=peft_config)
    adapter_dtype = getattr(torch, config["lora"]["adapter_dtype"])
    if adapter_dtype is not torch.float32:
        raise InfrastructureError(
            "the validated construction is float32 adapters only")
    for name, parameter in trainer.model.named_parameters():
        if "lora" in name:
            parameter.data = parameter.data.to(adapter_dtype)
    for callback in extra_callbacks:
        trainer.add_callback(callback)
    return trainer


def execute_probe(*, expected_freeze_sha256: str,
                  expected_identity_sha256: str,
                  expected_environment_sha256: str,
                  expected_head_sha256: str,
                  ledger_path: str | Path | None = None,
                  _environment_builder=None) -> dict[str, Any]:
    """The Step-6 run, in the validated Step-5 lifecycle shape."""
    from .ledger import LEDGER_PATH, admit_and_append_launch, \
        append_ledger_entry
    from .resume_validation import _DeadlineCallback
    from .support_run import _hash_directory, _sha_file
    ledger_path = ledger_path or LEDGER_PATH
    config = PROBE_CONFIG
    frozen = tranche_freeze()
    if frozen["freeze_sha256"] != expected_freeze_sha256:
        raise InfrastructureError(
            "the reconstructed freeze is not the reviewed one")
    # 248_s smaller item: the launch head IS the frozen lineage
    # parent — the reviewed head cannot be substituted at the command
    # line
    if expected_head_sha256 != \
            config["lineage"]["parent_entry_sha256"]:
        raise InfrastructureError(
            "expected_head_sha256 must equal the lineage parent "
            "frozen in PROBE_CONFIG (248_s)")
    if _environment_builder is None:
        from tasks.conductor.stage1_manifest import \
            build_stage1_env_manifest
        environment = build_stage1_env_manifest()
    else:
        environment = _environment_builder()
    from .dev_support import validate_environment_manifest_binding
    env_sha = validate_environment_manifest_binding(environment)
    if attested_environment_sha256(environment) != \
            expected_environment_sha256:
        raise InfrastructureError(
            "the live environment is not the reviewed one")
    loaded = load_locked_support()
    cohort = bound_cohort()
    rows = probe_schedule(loaded, cohort)
    identity_manifest = static_identity_manifest(loaded, cohort)
    if identity_manifest["manifest_sha256"] != expected_identity_sha256:
        raise InfrastructureError(
            "the execution identity is not the reviewed one")
    preflight = _probe_preflight()
    preflight_sha = content_sha256(preflight)
    run_root = Path(config["run_root"])
    if run_root.exists():
        raise InfrastructureError(
            f"{run_root} exists; the probe runs exactly once")
    run_root.mkdir(parents=True)
    for name, payload in (
            ("environment_manifest.json", environment),
            ("identity_manifest.json", identity_manifest),
            ("session_preflight.json", preflight),
            ("schedule.json",
             [row["observation_id"] for row in rows]),
            ("bound_cohort.json", dict(cohort))):
        (run_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    lineage = config["lineage"]
    entry = {
        "kind": "grouped_probe",
        "question": frozen["question"],
        "motivating_evidence": lineage["motivating_evidence"],
        "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                   "config_sha256": CONFIG_SHA256,
                   "identity_manifest_sha256":
                       identity_manifest["manifest_sha256"],
                   "environment_manifest_sha256": env_sha,
                   "attested_environment_sha256":
                       expected_environment_sha256,
                   "session_preflight_sha256": preflight_sha,
                   "probe_rule_sha256":
                       config["probe_rule_sha256"],
                   "probe_cohort_sha256":
                       config["probe_cohort_sha256"]},
        "parent": lineage["parent_entry_sha256"],
        "budget_allocated_gpu_hours": config["ceiling_gpu_hours"],
        "outcome_informed": lineage["outcome_informed"],
        "cohort_selection": "outcome_blind",
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started + config["ceiling_gpu_hours"] * 3600.0

    try:
        accountant = ckpt.GroupAccountant()
        trace_path = run_root / "actions.jsonl"
        reward = make_validation_reward(
            loaded["surface"], accountant, trace_path,
            config["grpo"]["group_size"])
        trainer = _build_probe_trainer(
            rows, reward, run_root / "trainer",
            [_DeadlineCallback(deadline).callback,
             _ConsumeCallback(accountant).callback])
        zero_map = tensor_state_hashes(
            {k: v for k, v in trainer.model.state_dict().items()
             if "lora" in k})
        (run_root / "checkpoint_zero_hashes.json").write_text(
            json.dumps(zero_map, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        trainer.train()
        final_map = tensor_state_hashes(
            {k: v for k, v in trainer.model.state_dict().items()
             if "lora" in k})
        # 248_s F3: BOTH maps persist so the verifier proves the gate
        # from the archive, not from record digests
        (run_root / "checkpoint_final_hashes.json").write_text(
            json.dumps(final_map, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        import torch as _torch
        peak_reserved_mib = (
            round(_torch.cuda.max_memory_reserved() / 2 ** 20)
            if _torch.cuda.is_available() else 0)
        from .resume_validation import _release_trainer
        holder = {"trainer": trainer}
        del trainer
        _release_trainer(holder)
        # the zero-EFFECTIVE-update gate: PROVEN, not assumed
        if final_map != zero_map:
            raise InfrastructureError(
                "the probe MUTATED the model — zero-effective-update "
                "gate fails; this is an infrastructure abort")
        counters = accountant.authorize_checkpoint()
        total = config["total_groups"]
        expected_counters = {
            "generated_groups": total, "consumed_groups": total,
            "optimizer_updates": total,
            "sampled_completions":
                total * config["grpo"]["group_size"]}
        if counters != expected_counters:
            raise InfrastructureError(
                f"counters {counters} != the frozen design "
                f"{expected_counters}")
        trace_rows = read_trace(trace_path)
        for i, row in enumerate(trace_rows):
            if row["observation_id"] != rows[i]["observation_id"] \
                    or row["global_group_index"] != i:
                raise InfrastructureError(
                    f"trace group {i} does not match the frozen "
                    "schedule")
        report = build_probe_report(run_root)
        # 248_s F4: the charter's execution-telemetry block — cache
        # and live-worker categories are structurally zero because
        # reward comes from the locked payoff surface
        valid_completions = sum(
            1 for row in trace_rows for action in row["actions"]
            if action is not None)
        execution_telemetry = {
            "group_accounting": dict(counters),
            "surface_reward_lookups": valid_completions,
            "live_worker_calls": 0,
            "worker_cache": ("not-applicable: rewards derive from "
                            "the locked payoff surface; no worker "
                            "executes during the probe"),
            "wall_seconds": round(time.monotonic() - started, 1),
            "deadline_seconds":
                config["ceiling_gpu_hours"] * 3600.0,
            "peak_reserved_vram_mib": peak_reserved_mib,
            "session_preflight": preflight,
        }
        record = {
            "tranche": config["tranche"],
            "freeze_sha256": frozen["freeze_sha256"],
            "config_sha256": CONFIG_SHA256,
            "identity_manifest_sha256":
                identity_manifest["manifest_sha256"],
            "environment_manifest_sha256": env_sha,
            "attested_environment_sha256":
                expected_environment_sha256,
            "session_preflight": preflight,
            "session_preflight_sha256": preflight_sha,
            "checkpoint_zero_adapter_sha256":
                content_sha256(zero_map),
            "final_adapter_sha256": content_sha256(final_map),
            "counters": counters,
            "probe_cohort_sha256": cohort["cohort_sha256"],
            "execution_telemetry": execution_telemetry,
        }
        for name, payload in (("probe_report.json", report),
                              ("probe_record.json", record)):
            path = run_root / name
            path.write_text(json.dumps(payload, indent=1,
                                       sort_keys=True) + "\n",
                            encoding="utf-8")
        verify_probe_run(run_root,
                         expected_identity_sha256,
                         expected_environment_sha256)
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": frozen["question"],
             "motivating_evidence": "grouped probe ABORTED",
             "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                        "partial_artifact_hashes": (
                            _hash_directory(run_root)
                            if run_root.exists() else
                            {"(nothing written)": "-"})},
             "parent": head, "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": measured,
             "closes_entry_sha256": head,
             "terminal_status": "aborted",
             "interpretation": f"{type(error).__name__}: {error}",
             "outcome_informed": False,
             "outcome_pointer": str(run_root)},
            head, ledger_path)
        raise

    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": frozen["question"],
         "motivating_evidence": "grouped probe complete",
         "freeze": {
             "freeze_sha256": frozen["freeze_sha256"],
             "probe_report_file_sha256":
                 _sha_file(run_root / "probe_report.json"),
             "probe_record_file_sha256":
                 _sha_file(run_root / "probe_record.json"),
             "terminal_artifact_hashes": _hash_directory(run_root),
         },
         "parent": head, "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": False,
         "outcome_pointer": str(run_root / "probe_report.json")},
        head, ledger_path)
    return {"tranche": config["tranche"],
            "measured_gpu_hours": measured,
            "launch_entry_sha256": head,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"],
            "report": str(run_root / "probe_report.json")}


class _ConsumeCallback:
    def __init__(self, accountant) -> None:
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def on_optimizer_step(self, args, state, control, **kw):
                accountant.record_update(consumed_groups=1)
        self.callback = _Callback()


def _probe_preflight() -> dict[str, Any]:
    """The probe's session preflight against ITS frozen floor."""
    import subprocess
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True).stdout.strip()
    free_mib, total_mib = (int(x.strip()) for x in out.split(","))
    floor = PROBE_CONFIG["min_free_vram_mib"]
    record = {"free_mib": free_mib, "total_mib": total_mib,
              "floor_mib": floor}
    if free_mib < floor:
        raise InfrastructureError(
            f"session preflight: {free_mib} MiB free < {floor} MiB "
            "floor — resolve (ollama?) before admission")
    return record
