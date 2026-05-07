# -*- coding: utf-8 -*-
"""Jenny TTS helper.

Attempts to synthesize audio using the following methods (in order):
1. edge-tts (recommended, no Azure creds required; uses Microsoft online voices)
2. Azure Cognitive Services Speech SDK (if AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are set)

If neither is available, this module raises RuntimeError so the caller can act accordingly.
"""

import os
import asyncio

VOICE_NAME = "en-US-JennyNeural"


async def _edge_speak(text: str, output_path: str):
    try:
        from edge_tts import Communicate
    except Exception as e:
        raise RuntimeError("edge-tts is not installed") from e

    comm = Communicate(text, VOICE_NAME)
    # `save` method will write to file
    await comm.save(output_path)


def synthesize_jenny(text: str, output_path: str):
    """Synthesize `text` to `output_path` using Jenny voice.

    Raises RuntimeError if synthesis is not possible.
    """
    # Try edge-tts first
    try:
        print(f"Jenny: attempting edge-tts synthesis to {output_path}")
        asyncio.run(_edge_speak(text, output_path))
        if os.path.exists(output_path):
            print(f"Jenny: wrote file {output_path}")
            return
    except Exception as e:
        print(f"Jenny: edge-tts failed: {e}")

    # Try Azure Speech SDK as fallback
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if key and region:
        try:
            from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig
            print("Jenny: attempting Azure Speech SDK synthesis")
            speech_config = SpeechConfig(subscription=key, region=region)
            speech_config.set_speech_synthesis_voice_name(VOICE_NAME)
            audio_cfg = AudioConfig(filename=output_path)
            synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_cfg)
            result = synthesizer.speak_text_async(text).get()
            if result.reason.name == "SynthesizingAudioCompleted":
                print(f"Jenny: Azure wrote file {output_path}")
                return
            else:
                print(f"Jenny: Azure failed with reason {result.reason}")
        except Exception as e:
            print(f"Jenny: azure sdk failed: {e}")

    raise RuntimeError("No available Jenny TTS backend (install edge-tts or configure Azure Speech)")