# -*- coding: utf-8 -*-
"""Offline self-check for edge_voice retry behaviour.

Run from backend/:  ../.venv/Scripts/python.exe tts/test_edge_voice_retry.py
No network, no real TTS - edge_tts.Communicate is faked.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import edge_tts
from tts import edge_voice

AUDIO = edge_voice.AUDIO_DIR
_real_sleep = edge_voice.time.sleep
edge_voice.time.sleep = lambda s: None


class FakeCommunicate:
    def __init__(self, text, voice):
        self.voice = voice

    async def save(self, path):
        raise NotImplementedError


def reset(n):
    state = {"calls": 0}

    class C(FakeCommunicate):
        async def save(self, path):
            state["calls"] += 1
            open(path, "wb").write(b"partial")
            if state["calls"] <= n:
                raise OSError("connection dropped")
            open(path, "wb").write(b"real-audio")

    edge_tts.Communicate = C
    edge_voice.edge_tts = edge_tts
    return state


try:
    # succeeds on the third attempt, within the ATTEMPTS budget
    assert edge_voice.ATTEMPTS == 3, edge_voice.ATTEMPTS
    state = reset(2)
    path = edge_voice.synthesize_edge("hello", "en-US-JennyNeural")
    assert state["calls"] == 3, state["calls"]
    assert path.startswith("/audio/") and path.endswith(".mp3"), path
    with open(os.path.join(AUDIO, os.path.basename(path)), "rb") as f:
        assert f.read() == b"real-audio"
    os.remove(os.path.join(AUDIO, os.path.basename(path)))

    # exhausts every attempt -> raises, and leaves no partial file behind
    state = reset(99)
    try:
        edge_voice.synthesize_edge("hello", "en-IN-PrabhatNeural")
        raise AssertionError("expected the final error to be raised")
    except OSError:
        pass
    assert state["calls"] == 3, state["calls"]
    partials = [
        f for f in os.listdir(AUDIO)
        if os.path.getsize(os.path.join(AUDIO, f)) == len(b"partial")
        and open(os.path.join(AUDIO, f), "rb").read() == b"partial"
    ]
    assert not partials, partials

    print("edge_voice retry self-check OK")
finally:
    edge_voice.time.sleep = _real_sleep
