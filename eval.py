"""Greedy pass@1 on GSM8K test — the before/after check for a training run.

  uv run python eval.py                                   # base 7B baseline
  uv run python eval.py --adapter runs/stage1-7b-g8-t1.0  # after training

Also home to the shared batch-generation helper used by filter_data.py.
Inference here is plain bf16 (a 7B fits in ~15 GB when there's no training
state next to it) — faster than the 4-bit weights we train with.
"""

import argparse

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from data import load_gsm8k
from rewards import extract_answer, is_formatted


def load_model(model_id, adapter=None):
    tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map="cuda",
    )
    if adapter is not None:
        # LoRA trained on the 4-bit base applies cleanly to the bf16 base:
        # adapters attach by module name, not by quantization scheme.
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter)
    return model.eval(), tokenizer


@torch.no_grad()
def batch_generate(
    model, tokenizer, prompts,
    max_new_tokens=512, temperature=0.0, num_return=1, batch_size=16,
):
    """prompts: list of chat-message lists. Returns one list of `num_return`
    completion strings per prompt. temperature=0 -> greedy."""
    results = []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i : i + batch_size]
        texts = tokenizer.apply_chat_template(
            chunk, tokenize=False, add_generation_prompt=True
        )
        batch = tokenizer(texts, return_tensors="pt", padding=True).to(model.device)
        sampling = (
            {"do_sample": True, "temperature": temperature, "top_p": 1.0}
            if temperature > 0
            else {"do_sample": False}
        )
        out = model.generate(
            **batch,
            max_new_tokens=max_new_tokens,
            num_return_sequences=num_return,
            pad_token_id=tokenizer.pad_token_id,
            **sampling,
        )
        completions = tokenizer.batch_decode(
            out[:, batch["input_ids"].shape[1] :], skip_special_tokens=True
        )
        for j in range(len(chunk)):
            results.append(completions[j * num_return : (j + 1) * num_return])
        print(f"  generated {len(results)}/{len(prompts)}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--no_wandb", action="store_true")
    args = parser.parse_args()

    dataset = load_gsm8k("test", n=args.n)
    model, tokenizer = load_model(args.model, args.adapter)
    completions = batch_generate(
        model, tokenizer, dataset["prompt"],
        max_new_tokens=args.max_new_tokens, batch_size=args.batch_size,
    )

    correct = [
        extract_answer(c[0]) == gold
        for c, gold in zip(completions, dataset["answer"])
    ]
    formatted = [is_formatted(c[0]) for c in completions]
    accuracy, format_rate = sum(correct) / len(correct), sum(formatted) / len(formatted)

    name = args.adapter or args.model
    print(f"\n{name} on {args.n} GSM8K test problems (greedy):")
    print(f"  accuracy          {accuracy:.3f}")
    print(f"  format compliance {format_rate:.3f}")
    print(f"\nsample completion:\n{completions[0][0]}")

    if not args.no_wandb:
        import wandb

        run = wandb.init(
            project="qwen-grpo", name=f"eval-{name.split('/')[-1]}", job_type="eval"
        )
        run.log({"eval/accuracy": accuracy, "eval/format_rate": format_rate})
        run.finish()


if __name__ == "__main__":
    main()
