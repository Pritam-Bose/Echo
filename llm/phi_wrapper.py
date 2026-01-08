# -*- coding: utf-8 -*-
"""Simple, dedicated GGUF loader using llama.cpp (recommended for local .gguf models).

This file intentionally focuses on the llama_cpp backend since your model is a
GGUF file and is not compatible with the HuggingFace/transformers ecosystem.
"""
import os

try:
    from llama_cpp import Llama
    _HAS_LLAMA_CPP = True
except Exception:
    Llama = None
    _HAS_LLAMA_CPP = False

import multiprocessing


class PhiMini:
    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: int | None = None, n_batch: int = 128):
        if not os.path.exists(model_path):
            raise RuntimeError(f"GGUF model file not found: {model_path}")

        if not _HAS_LLAMA_CPP:
            raise RuntimeError(
                "llama_cpp is not available. Install with: pip install llama-cpp-python"
            )

        # Cap threads to 4 by default for low-memory machines
        if n_threads is None:
            n_threads = max(1, min(4, multiprocessing.cpu_count()))

        # Use llama.cpp Llama wrapper
        print(f"Loading GGUF model from {model_path} (threads={n_threads}, n_ctx={n_ctx})...")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=n_batch,
            verbose=False,
        )
        print(f"Loaded GGUF model — threads={n_threads} n_ctx={n_ctx}")

    def generate(self, prompt: str, max_tokens: int = 180):
        print("=== PHI-3 GENERATE CALLED ===")

        # Enforce strict generation limits to avoid OOM on low-memory machines
        max_tokens = min(max_tokens, 180)

        # Wrap the user's prompt into an instruction-style format expected by Phi-3-instruct models
        wrapped_prompt = f"""### Instruction:
You are Echo.
Echo does not explain, advise, reassure, or motivate.
Echo reflects what the user is feeling in a quiet, human way.
Speak like a person sitting beside the user. Use at most 2–3 short sentences. No advice, no therapy language.

### Input:
{prompt}

### Response:
"""

        output = self.llm(
            wrapped_prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
        )

        choices = output.get("choices") or []
        text = ""
        if choices:
            text = choices[0].get("text", "")

        # If the model returns an empty string, try once more with a slightly higher temperature
        if not text:
            print("=== PHI-3 GENERATE RETRY ===")
            retry_out = self.llm(
                wrapped_prompt,
                max_tokens=max_tokens,
                temperature=0.85,
                top_p=0.9,
            )
            retry_choices = retry_out.get("choices") or []
            if retry_choices:
                text = retry_choices[0].get("text", "")

        if not text:
            return "[Echo paused, taking a moment.]"

        # Strip instruction leakage (remove prompt markers if accidentally echoed)
        for marker in ["### Instruction:", "### Input:", "### Response:"]:
            if marker in text:
                text = text.split(marker)[0]

        # Hard-cap by sentences (2–3 short sentences)
        text = text.strip()
        if not text:
            return "[Echo paused, taking a moment.]"

        sentences = [s.strip() for s in text.split(".") if s.strip()]
        text = ". ".join(sentences[:3])
        if text and not text.endswith((".", "!", "?")):
            text += "."

        return text
