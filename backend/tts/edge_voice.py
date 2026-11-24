# -*- coding: utf-8 -*-
import asyncio
import os
import time
import uuid

import edge_tts

AUDIO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "audio"
)
os.makedirs(AUDIO_DIR, exist_ok=True)

ATTEMPTS = 3


def synthesize_edge(text: str, voice: str) -> str:
    """Synthesize `text` to an MP3 file via the edge-tts library and return web path.

    Uses the Python API (not the CLI) so it works without the console script on
    PATH, including on serverless hosts. Retries because the Microsoft endpoint
    drops connections and times out intermittently. Raises on final failure.
    """
    filename = f"{voice.lower().replace('/', '_')}_{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)
    last_error = None
    for attempt in range(ATTEMPTS):
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(out_path))
            return f"/audio/{filename}"
        except Exception as e:
            last_error = e
            # edge-tts streams to disk, so a failed attempt can leave a partial file
            if os.path.exists(out_path):
                os.remove(out_path)
            if attempt < ATTEMPTS - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error
