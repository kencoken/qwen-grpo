"""NF4 worker pool — Stage 0B (plan rev6 §8; spec §1.5–1.7, §1.10).

Three frozen 1.5B endpoints (spec §1.6): Lookup = Qwen2.5-1.5B-Instruct,
Math = Qwen2.5-Math-1.5B-Instruct, Code = Qwen2.5-Coder-1.5B-Instruct, all
NF4-quantized, greedy decoding, per-worker token caps and inference
microbatch caps from the runtime profile.

Tokenizers load eagerly at pool construction: the chat template is a
cache-key component (§1.10), so its bytes must be pinned before any
fingerprint is computed. Models load lazily on first generation for their
endpoint and stay resident (three 1.5B NF4 models fit one 24 GB card).

The pool never parses artifacts and never sees tools: it maps canonical
rendered request bytes to raw completions plus the §1.6 backend telemetry
(`finish_reason`, generated-token count, `generation_hit_token_cap`).
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from .prompts import PromptBundle, WORKER_ENDPOINT_SET, resolve_prompts
from .types import ENDPOINT_NAMES, InfrastructureError


@dataclass(frozen=True)
class Generation:
    """Raw completion + backend telemetry for one worker call (§1.6)."""
    completion: str
    finish_reason: str            # "eos" | "length"
    generated_tokens: int
    generation_hit_token_cap: bool


class WorkerPool:
    """Real HF/bitsandbytes backend. Tests substitute fakes implementing
    `chat_template_sha`, `render_request`, `generate`, `close`."""

    def __init__(self, profile: Mapping[str, Any],
                 device: str = "cuda",
                 prompts: PromptBundle | None = None) -> None:
        from .runtime import validate_runtime_profile
        validate_runtime_profile(profile)
        if profile["decoding"]["stopping"] != "eos":
            raise InfrastructureError(
                f"unsupported stopping rule {profile['decoding']['stopping']!r}")
        # Own the configuration (plan 81_f §6.2): caller mutation after
        # construction must not change generation behavior.
        self._profile = copy.deepcopy(dict(profile))
        # Bind the resolved prompt strings now (81_f §5.2): rendering never
        # re-reads module globals, so the hashes recorded from this bundle
        # describe exactly what every request contained.
        self._prompts = prompts if prompts is not None else resolve_prompts()
        if {name for name, _ in self._prompts.prompts} != WORKER_ENDPOINT_SET:
            raise InfrastructureError(
                f"prompt bundle {self._prompts.revision!r} must cover "
                f"exactly {sorted(WORKER_ENDPOINT_SET)}")
        self._device = device
        self._tokenizers: dict[str, Any] = {}
        self._models: dict[str, Any] = {}
        for name in sorted(set(ENDPOINT_NAMES.values())):
            self._tokenizers[name] = self._load_tokenizer(name)

    def _load_tokenizer(self, endpoint_name: str) -> Any:
        from transformers import AutoTokenizer
        worker = self._profile["workers"][endpoint_name]
        tokenizer = AutoTokenizer.from_pretrained(
            worker["model_id"], revision=worker["revision"])
        if not getattr(tokenizer, "chat_template", None):
            raise InfrastructureError(
                f"{worker['model_id']} has no chat template; the canonical "
                "rendered request is defined over one (§1.5)")
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "left"
        return tokenizer

    # --- fingerprint inputs -------------------------------------------------

    def chat_template_sha(self, endpoint_name: str) -> str:
        template = self._tokenizers[endpoint_name].chat_template
        return hashlib.sha256(template.encode("utf-8")).hexdigest()

    def system_prompt(self, endpoint_name: str) -> str:
        """The exact system prompt this pool renders for the endpoint —
        the provenance source for prompt hashes in fingerprints/manifests."""
        return self._prompts.text(endpoint_name)

    def tokenizer_facts(self, endpoint_name: str) -> dict[str, Any]:
        """Actual tokenizer-level facts used at render/decode time (81_f
        §6.3). The model generation-config eos set is only known after the
        lazy model load and is validated at decode, not recorded here."""
        tokenizer = self._tokenizers[endpoint_name]
        return {
            "pad_token_id": tokenizer.pad_token_id,
            "padding_side": tokenizer.padding_side,
            "eos_token_id": tokenizer.eos_token_id,
        }

    # --- canonical rendered request (§1.5, cache-key component) -------------

    def render_request(self, endpoint_name: str, user_message: str) -> bytes:
        """Chat template over (system, user); system prompt comes from the
        bundle bound at construction. Returned bytes are the cache-key
        request component and the byte-stability test target."""
        tokenizer = self._tokenizers[endpoint_name]
        text = tokenizer.apply_chat_template(
            [{"role": "system", "content": self.system_prompt(endpoint_name)},
             {"role": "user", "content": user_message}],
            tokenize=False, add_generation_prompt=True)
        return text.encode("utf-8")

    # --- generation ---------------------------------------------------------

    def _load_model(self, endpoint_name: str) -> Any:
        if endpoint_name not in self._models:
            import torch
            from transformers import (AutoModelForCausalLM,
                                      BitsAndBytesConfig)
            worker = self._profile["workers"][endpoint_name]
            nf4 = self._profile["nf4"]
            if nf4 != {"load_in_4bit": "true", "quant_type": "nf4",
                       "double_quant": "true", "compute_dtype": "bfloat16"}:
                raise InfrastructureError(
                    f"unsupported nf4 config {nf4!r}")
            self._models[endpoint_name] = AutoModelForCausalLM.from_pretrained(
                worker["model_id"], revision=worker["revision"],
                dtype=torch.bfloat16,
                quantization_config=BitsAndBytesConfig(
                    load_in_4bit=True, bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.bfloat16),
                device_map=self._device).eval()
        return self._models[endpoint_name]

    def generate(self, endpoint_name: str,
                 requests: list[bytes]) -> list[Generation]:
        """Greedy batched generation under the endpoint's token cap,
        microbatched at the profile's per-worker cap. Returns one
        Generation per request, in order."""
        import torch
        tokenizer = self._tokenizers[endpoint_name]
        model = self._load_model(endpoint_name)
        worker = self._profile["workers"][endpoint_name]
        cap = worker["max_new_tokens"]
        microbatch = worker["microbatch"]
        results: list[Generation] = []
        for start in range(0, len(requests), microbatch):
            chunk = [req.decode("utf-8")
                     for req in requests[start:start + microbatch]]
            batch = tokenizer(chunk, return_tensors="pt", padding=True,
                              add_special_tokens=False).to(model.device)
            with torch.no_grad():
                output = model.generate(
                    **batch, max_new_tokens=cap, do_sample=False,
                    pad_token_id=tokenizer.pad_token_id)
            # `generate` stops at the model's generation-config eos set
            # (Qwen2.5 lists both <|im_end|> and <|endoftext|>); decoding
            # must recognize the same set, not just tokenizer.eos_token_id.
            eos = model.generation_config.eos_token_id
            eos_ids = frozenset([eos] if isinstance(eos, int) else eos or [])
            new_tokens = output[:, batch["input_ids"].shape[1]:]
            for row in new_tokens:
                results.append(self._decode_row(tokenizer, row, eos_ids))
        if len(results) != len(requests):
            raise InfrastructureError(
                f"generated {len(results)} completions for "
                f"{len(requests)} requests")
        return results

    @staticmethod
    def _decode_row(tokenizer: Any, row: Any,
                    eos_ids: frozenset[int]) -> Generation:
        token_ids = row.tolist()
        stop_positions = [i for i, tok in enumerate(token_ids)
                          if tok in eos_ids]
        if stop_positions:
            token_ids = token_ids[:stop_positions[0]]
            finish_reason = "eos"
        else:
            # Right-side padding cannot occur before eos with left-padded
            # inputs, so a row without eos ran to the cap.
            finish_reason = "length"
        completion = tokenizer.decode(token_ids, skip_special_tokens=True)
        generated = len(token_ids) + (1 if finish_reason == "eos" else 0)
        return Generation(
            completion=completion, finish_reason=finish_reason,
            generated_tokens=generated,
            generation_hit_token_cap=finish_reason == "length")

    def close(self) -> None:
        self._models.clear()
        self._tokenizers.clear()
