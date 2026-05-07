# -*- coding: utf-8 -*-
"""Voice manager - Edge TTS routing for 'she' and 'he'.

Hard routing rules:
- she -> Jenny (Edge TTS voice en-US-JennyNeural)
- he  -> Male Edge TTS voice (en-IN-PrabhatNeural)
- No browser fallback, no mixing of voices
"""

from typing import Optional
from tts.edge_voice import synthesize_edge

FEMALE_VOICE = "en-US-JennyNeural"
MALE_VOICE = "en-IN-PrabhatNeural"


def synthesize_voice(text: str, voice: str) -> Optional[str]:
    """Synthesize `text` according to the hard rules above.

    Returns a web path ('/ui/audio/...') on success, or None on failure.
    Exceptions are caught and result in None so callers can decide how to handle failures.
    """
    v = str(voice).lower()
    try:
        if v == "she":
            print("Jenny: generating female voice")
            return synthesize_edge(text, FEMALE_VOICE)
        if v == "he":
            print("Male TTS: generating male voice")
            return synthesize_edge(text, MALE_VOICE)
        return None
    except Exception as e:
        print("TTS failed:", e)
        return None

