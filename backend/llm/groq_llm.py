# -*- coding: utf-8 -*-
"""Groq cloud inference (OpenAI-compatible chat completions).

Replaces the local Phi-3 GGUF so Echo can deploy anywhere without shipping a
2 GB model file. Credentials come from the environment, never from code.
"""
import json
import os
import urllib.request

API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM = (
    "You are Echo.\n"
    "Echo does not explain, advise, reassure, or motivate.\n"
    "Echo reflects what the user is feeling in a quiet, human way.\n"
    "Speak like a person sitting beside the user. Use at most 2-3 short sentences. "
    "No advice, no therapy language."
)

FALLBACK = "[Echo paused, taking a moment.]"


class GroqLLM:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    def generate(self, prompt: str, max_tokens: int = 180) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": min(max_tokens, 180),
            "temperature": 0.7,
            "top_p": 0.9,
        }).encode()
        req = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json",
                # Groq's edge rejects requests with no browser-like User-Agent
                "User-Agent": "echo-backend/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as res:
            choices = json.load(res).get("choices") or []

        text = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        if not text:
            return FALLBACK

        # Hard-cap by sentences (2-3 short sentences), same behaviour as before
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        text = ". ".join(sentences[:3])
        if text and not text.endswith((".", "!", "?")):
            text += "."
        return text or FALLBACK
