# qwen-grpo

Minimal GRPO training on GSM8K with TRL, sized for a single RTX 4090 (24 GB).
Built for **learning how GRPO behaves**, not for benchmark numbers — flat,
heavily-commented scripts in the spirit of microgpt. See [stages.md](stages.md)
for the full exploration roadmap.

The model is trained to answer in

```
<think> ... reasoning ... </think>
<answer> 42 </answer>
```

with reward **+0.2** for correct format and **+1.0** for the exact answer.

## Files

| File | Purpose |
|---|---|
| `experiment_log.md` | Lab notebook: one entry per experiment + backlog of ideas |
| `tasks/` | One module per task = its data + its verifier (contract in `tasks/__init__.py`) |
| `rewards.py` | Shared reward machinery: the `<think>/<answer>` format contract |
| `test_*.py` | Verifier tests, one file per task — run before burning GPU-hours |
| `train.py` | Config + TRL `GRPOTrainer` wiring; every knob commented |
| `eval.py` | Greedy pass@1 on GSM8K test, before/after training |
| `filter_data.py` | One-off difficulty filter: keep problems the model sometimes solves |

## Usage

```bash
uv sync
uv run pytest                      # verify the verifiers (no GPU)
uv run python -m tasks.gsm8k       # print one rendered example

# Stage 0: smoke test (~15 min, 1.5B bf16 + LoRA)
uv run python train.py

# Phase C: countdown (difficulty dial = --num_numbers 3..6; W&B project
# qwen-grpo-countdown)
uv run python train.py --task countdown --model Qwen/Qwen2.5-3B-Instruct \
    --num_numbers 4 --run_name c1-D2-s0
uv run python eval.py --task countdown --model Qwen/Qwen2.5-3B-Instruct \
    --num_numbers 4 --n 500

# Stage 1: the real run (7B QLoRA, overnight)
uv run python filter_data.py       # one-off, ~1-2 h: build difficulty-filtered set
uv run python eval.py              # baseline accuracy on test
uv run python train.py --model Qwen/Qwen2.5-7B-Instruct --load_in_4bit true \
    --max_completion_length 512 --max_steps 300 --dataset filtered \
    --run_name stage1-7b-g8-t1.0
uv run python eval.py --adapter runs/stage1-7b-g8-t1.0   # after
uv run python eval.py --num_samples 8 --temperature 1.0  # pass@8 / maj@8
```

Any `Config` field in `train.py` is a `--flag value` override. Metrics go to
the `qwen-grpo` W&B project (`wandb login` once first).

## Deliberately left out (extension points)

vLLM generation (fits 1.5B/3B in colocate mode — the Stage-2 sweep speedup),
SFT warm start, multi-GPU, MATH500/`math_verify`, the Countdown task,
Conductor/worker machinery. Each has a marked home: tasks in `data.py` +
`rewards.py`, everything else in `train.py`'s config.

The toy Conductor environment (Stage 0A, CPU-only) lives in
`tasks/conductor/` — see `conductor_cell_specs.md` (frozen v0.8) and
`conductor_log.md`.
