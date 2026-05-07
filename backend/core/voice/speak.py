# -*- coding: utf-8 -*-
"""Simple TTS router/stub.

This module provides a stable interface for server-side TTS:

    tts_audio = speak_text(text, voice="female")

It currently acts as a safe placeholder so backend code can call it without
failing; integrate a real TTS synthesizer here later.
"""

from typing import Optional

# Placeholder model names (replace with real TTS model handles)
FEMALE_VOICE_MODEL = "female_model"
MALE_VOICE_MODEL = "male_model"


def speak_text(text: str, voice: str = "female") -> Optional[bytes]:
    """Best-effort TTS synth.

    Returns raw audio bytes when available, otherwise None.
    This function never raises; callers should treat failures as non-fatal.
    """
    try:
        chosen = MALE_VOICE_MODEL if str(voice).lower() == "male" else FEMALE_VOICE_MODEL
        # TODO: wire real TTS synth here and return audio bytes
        # Example:
        # audio = synthesize_with_model(chosen, text)
        # return audio
        # For now, return None to indicate no server-side audio generated.
        return None
    except Exception:
        return None
