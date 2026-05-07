# -*- coding: utf-8 -*-
import os
import uuid
import subprocess

AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


def synthesize_edge(text: str, voice: str) -> str:
    """Synthesize `text` to a WAV file using the edge-tts CLI and return web path.

    This runs the `edge-tts` command which must be installed in the current
    virtualenv (`pip install edge-tts`). It raises subprocess.CalledProcessError
    on failure.
    """
    filename = f"{voice.lower().replace('/', '_')}_{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)

    cmd = [
        "edge-tts",
        "--voice", voice,
        "--text", text,
        "--write-media", out_path
    ]

    # Run and raise on error
    subprocess.run(cmd, check=True)
    return f"/audio/{filename}"
