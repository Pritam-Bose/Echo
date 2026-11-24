# -*- coding: utf-8 -*-
import asyncio
import os
import uuid

import edge_tts

AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


def synthesize_edge(text: str, voice: str) -> str:
    """Synthesize `text` to an MP3 file via the edge-tts library and return web path.

    Uses the Python API (not the CLI) so it works without the console script on
    PATH, including on serverless hosts. Raises on failure.
    """
    filename = f"{voice.lower().replace('/', '_')}_{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)
    asyncio.run(edge_tts.Communicate(text, voice).save(out_path))
    return f"/audio/{filename}"
