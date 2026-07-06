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
from collections import Counter
from math import comb

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

from data import load_gsm8k
from rewards import extract_answer, is_formatted


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
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--num_samples", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--no_wandb", action="store_true")
    args = parser.parse_args()
    assert args.num_samples == 1 or args.temperature > 0, \
        "k>1 identical greedy samples would be pointless; set --temperature"

    dataset = load_gsm8k("test", n=args.n)
    llm, lora = load_model(args.model, args.adapter)
    completions = batch_generate(
        llm, dataset["prompt"], max_new_tokens=args.max_new_tokens,
        temperature=args.temperature, num_return=args.num_samples, lora=lora,
    )

    n = args.num_samples
    extracted = [[extract_answer(c) for c in group] for group in completions]
    golds = dataset["answer"]
    corrects = [sum(e == g for e in ex) for ex, g in zip(extracted, golds)]

    def pass_at(k):
        # standard unbiased estimator from n samples with c correct:
        # P(at least one correct in a size-k draw) = 1 - C(n-c,k)/C(n,k)
        return sum(1 - comb(n - c, k) / comb(n, k) for c in corrects) / len(golds)

    def maj_at(k):
        # plurality vote over the first k samples (deterministic; a None
        # answer is a candidate that simply never matches gold)
        return sum(Counter(ex[:k]).most_common(1)[0][0] == g
                   for ex, g in zip(extracted, golds)) / len(golds)

    format_rate = sum(is_formatted(c) for gr in completions for c in gr) / (len(golds) * n)

    name = args.adapter or args.model
    print(f"\n{name} on {args.n} GSM8K test problems "
          f"(n={n}, temp={args.temperature}):")
    ks = [2**i for i in range(n.bit_length()) if 2**i <= n]
    metrics = {"eval/format_rate": format_rate}
    for k in ks:
        line = f"  pass@{k:<3} {pass_at(k):.3f}"
        metrics[f"eval/pass@{k}"] = pass_at(k)
        if k > 1:
            line += f"   maj@{k:<3} {maj_at(k):.3f}"
            metrics[f"eval/maj@{k}"] = maj_at(k)
        print(line)
    print(f"  format compliance {format_rate:.3f}")
    print(f"\nsample completion:\n{completions[0][0]}")

    if not args.no_wandb:
        import wandb

        run = wandb.init(
            project="qwen-grpo",
            name=f"eval-{name.split('/')[-1]}-k{n}-t{args.temperature}",
            job_type="eval",
        )
        run.log(metrics)
        run.finish()


if __name__ == "__main__":
    main()
