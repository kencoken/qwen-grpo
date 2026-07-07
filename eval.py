"""Eval on GSM8K test: greedy pass@1 (the before/after headline number) or
sampled pass@k / maj@k (the sharpening-vs-capability diagnostic).

  uv run python eval.py                                    # base 7B, greedy
  uv run python eval.py --adapter runs/stage1-7b-g8-t1.0   # after training
  uv run python eval.py --num_samples 8 --temperature 1.0  # pass@8 / maj@8

Also home to the shared batch-generation helper used by filter_data.py.
Generation here runs on vLLM: offline scripts have the GPU to themselves (no
optimizer/gradients/activations), so a bf16 7B fits alongside vLLM's paged KV
cache and runs ~10x faster than HF generate. Training-time generation inside
TRL stays HF `generate` — a second bf16 weight copy does NOT fit next to 7B
QLoRA training state, and TRL can't sync LoRA into a quantized engine.
"""

import argparse
import json
import os
from collections import Counter
from math import comb

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

from rewards import answer_block, is_formatted
from tasks import TASKS


def load_model(model_id, adapter=None):
    """Returns (llm, lora_request-or-None). The adapter is a local path to a
    saved PEFT LoRA (vLLM merges it at request time, quantization-free)."""
    llm = LLM(
        model=model_id,
        dtype="bfloat16",
        enable_lora=adapter is not None,
        max_lora_rank=64,
    )
    lora = LoRARequest("adapter", 1, adapter) if adapter is not None else None
    return llm, lora


def batch_generate(llm, prompts, max_new_tokens=512, temperature=0.0,
                   num_return=1, lora=None):
    """prompts: list of chat-message lists (vLLM applies the chat template).
    Returns one list of `num_return` completion strings per prompt.
    temperature=0 -> greedy."""
    params = SamplingParams(
        n=num_return, temperature=temperature, max_tokens=max_new_tokens
    )
    outputs = llm.chat(list(prompts), params, lora_request=lora)
    return [[o.text for o in out.outputs] for out in outputs]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--task", default="gsm8k", choices=sorted(TASKS))
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--num_numbers", type=int, default=4)  # countdown dial
    parser.add_argument("--eval_seed", type=int, default=0)
    parser.add_argument("--num_samples", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--wandb_project", default="")
    parser.add_argument("--tag", default="", help="suffix for the results file, "
                        "e.g. nn3 to keep calibration dials apart")
    parser.add_argument("--no_wandb", action="store_true")
    args = parser.parse_args()
    assert args.num_samples == 1 or args.temperature > 0, \
        "k>1 identical greedy samples would be pointless; set --temperature"

    task = TASKS[args.task]
    dataset = task.load_eval(n=args.n, num_numbers=args.num_numbers,
                             seed=args.eval_seed)
    llm, lora = load_model(args.model, args.adapter)
    completions = batch_generate(
        llm, dataset["prompt"], max_new_tokens=args.max_new_tokens,
        temperature=args.temperature, num_return=args.num_samples, lora=lora,
    )

    # meta = every non-prompt column; the task verifier knows what it needs
    meta_cols = [c for c in dataset.column_names if c != "prompt"]
    metas = [{c: dataset[c][i] for c in meta_cols} for i in range(len(dataset))]
    n = args.num_samples
    n_problems = len(dataset)
    corrects = [sum(task.verify(c, **meta) for c in group)
                for group, meta in zip(completions, metas)]
    # displayable answer per completion: the canonical form if the task has
    # one, else the raw <answer> block
    display = task.canonical or (lambda t: (answer_block(t) or "").strip())
    extracted = [[display(c) for c in group] for group in completions]

    def pass_at(k):
        # standard unbiased estimator from n samples with c correct:
        # P(at least one correct in a size-k draw) = 1 - C(n-c,k)/C(n,k)
        return sum(1 - comb(n - c, k) / comb(n, k) for c in corrects) / n_problems

    def maj_at(k):
        # plurality vote over the first k samples — only meaningful when the
        # task has a canonical answer to vote on (gsm8k yes, countdown no)
        return sum(Counter(ex[:k]).most_common(1)[0][0] == meta["answer"]
                   for ex, meta in zip(extracted, metas)) / n_problems

    format_rate = sum(is_formatted(c) for gr in completions for c in gr) / (n_problems * n)

    name = args.adapter or args.model
    print(f"\n{name} on {args.n} {args.task} problems "
          f"(n={n}, temp={args.temperature}):")
    ks = [2**i for i in range(n.bit_length()) if 2**i <= n]
    metrics = {"eval/format_rate": format_rate}
    for k in ks:
        line = f"  pass@{k:<3} {pass_at(k):.3f}"
        metrics[f"eval/pass@{k}"] = pass_at(k)
        if k > 1 and task.canonical is not None:
            line += f"   maj@{k:<3} {maj_at(k):.3f}"
            metrics[f"eval/maj@{k}"] = maj_at(k)
        print(line)
    print(f"  format compliance {format_rate:.3f}")
    print(f"\nsample completion:\n{completions[0][0]}")

    # Per-problem outcomes -> data/evals/. Aggregates hide everything that
    # matters for comparing runs: paired tests (McNemar) and difficulty-slice
    # analyses need to know WHICH problems each model got right.
    os.makedirs("data/evals", exist_ok=True)
    tag = f"-{args.tag}" if args.tag else ""
    out_path = f"data/evals/{name.split('/')[-1]}{tag}-k{n}-t{args.temperature}.json"
    with open(out_path, "w") as f:
        json.dump({
            "model": args.model, "adapter": args.adapter, "task": args.task,
            "k": n, "temperature": args.temperature,
            "results": [
                {"i": i, "meta": meta, "extracted": ex,
                 "n_correct": c, "n_formatted": sum(is_formatted(x) for x in gr)}
                for i, (meta, ex, c, gr) in enumerate(
                    zip(metas, extracted, corrects, completions))
            ],
        }, f)
    print(f"per-problem results -> {out_path}")

    if not args.no_wandb:
        import wandb

        run = wandb.init(
            project=args.wandb_project or (
                "qwen-grpo" if args.task == "gsm8k" else f"qwen-grpo-{args.task}"
            ),
            name=f"eval-{name.split('/')[-1]}-k{n}-t{args.temperature}",
            job_type="eval",
        )
        run.log(metrics)
        run.finish()


if __name__ == "__main__":
    main()
