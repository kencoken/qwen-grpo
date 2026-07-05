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
| `rewards.py` | The verifier: answer extraction + the two reward functions |
| `test_rewards.py` | Unit tests for the verifier — run these before burning GPU-hours |
| `data.py` | GSM8K → (prompt, answer) datasets; the swap point for other tasks |
| `train.py` | Config + TRL `GRPOTrainer` wiring; every knob commented |
| `eval.py` | Greedy pass@1 on GSM8K test, before/after training |
| `filter_data.py` | One-off difficulty filter: keep problems the model sometimes solves |

## Usage

```bash
uv sync
uv run pytest                      # verify the verifier (no GPU)
uv run python data.py              # print one rendered example

# Stage 0: smoke test (~15 min, 1.5B bf16 + LoRA)
uv run python train.py

# Stage 1: the real run (7B QLoRA, overnight)
uv run python filter_data.py       # one-off, ~1-2 h: build difficulty-filtered set
uv run python eval.py              # baseline accuracy on test
uv run python train.py --model Qwen/Qwen2.5-7B-Instruct --load_in_4bit true \
    --max_completion_length 512 --max_steps 300 --dataset filtered \
    --run_name stage1-7b-g8-t1.0
uv run python eval.py --adapter runs/stage1-7b-g8-t1.0   # after
```

Any `Config` field in `train.py` is a `--flag value` override. Metrics go to
the `qwen-grpo` W&B project (`wandb login` once first).

## Deliberately left out (extension points)

vLLM generation (fits 1.5B/3B in colocate mode — the Stage-2 sweep speedup),
SFT warm start, multi-GPU, MATH500/`math_verify`, the Countdown task,
Conductor/worker machinery. Each has a marked home: tasks in `data.py` +
`rewards.py`, everything else in `train.py`'s config.
