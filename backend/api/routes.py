# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.schemas import DreamInput, DreamResponse, Message, ChatInput
from core.analyzer.emotion_extractor import extract_emotions
from core.analyzer.dream_classifier import classify_dream
from core.composer.response_builder import build_response

app = FastAPI()

from threading import Lock
MODEL_LOCK = Lock()


def sanitize_presence_reply(text: str) -> str:
    """Post-process a model-generated presence reply to ensure it's concise,
    non-analytical, and reflects the feeling in a short, human way."""
    if not text:
        return ""
    t = text.strip()

    # Remove common hedges/prefixes
    prefixes = [
        "It sounds like",
        "It seems",
        "It might",
        "It may",
        "It could be",
        "This might be",
        "This seems",
        "Your dream seems",
        "Your dream might be",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].lstrip(" ,:.")
            break

    # Remove invitation phrases that ask for more sharing
    removals = [
        "I'm here to listen if you want to share more about how it made you feel",
        "I'm here to listen if you want to share more",
        "If you like, tell me more",
        "If you want to share more",
    ]
    for r in removals:
        t = t.replace(r, "")

    # Split into sentences and filter out analytical/therapy-y sentences
    raw_sentences = [s.strip() for s in t.split(".") if s.strip()]

    # Blacklist words that indicate analysis or therapeutic framing
    blacklist = ["dream", "reflect", "subconscious", "represent", "analysis", "interpret", "therap"]
    good_sentences = [s for s in raw_sentences if not any(b in s.lower() for b in blacklist)]

    # If the model's output is too analytical, fall back to a neutral, reflective default
    if not good_sentences:
        return "I hear you — that felt like something that mattered."

    t = ". ".join(good_sentences[:2])
    if t and not t.endswith((".", "?", "!")):
        t += "."

    # Normalize start
    if t and not t[0].isupper():
        t = t[0].upper() + t[1:]
    if t and not t.startswith(("That", "You", "It", "This")):
        t = "That " + t[0].lower() + t[1:]

    return t

# Serve UI (Local only, expects frontend folder to be next to backend)
try:
    app.mount("/ui", StaticFiles(directory="../frontend"), name="ui")
except:
    pass

# Serve generated audio files
app.mount("/audio", StaticFiles(directory="static/audio"), name="audio")

# Minimal in-memory session store (safe for development)
SESSION = {
    "dream_context": "",
    "history": []
}

# --- Phi-3 model (optional) ---
# Import and initialize once, but keep failure-safe so server runs without model
PhiMini = None
try:
    from llm.phi_wrapper import PhiMini
except Exception as e:
    print(f"Warning: PhiMini loader failed: {e}")
    PhiMini = None

# Prompts are always required - import them with error handling
try:
    from llm.prompt import SYSTEM_GUARDRAILS, CHAT_PROMPT, PRESENCE_PROMPT
except Exception as e:
    print(f"ERROR: Failed to load prompts from llm.prompt: {e}")
    raise RuntimeError("Critical: llm/prompt.py must be importable with SYSTEM_GUARDRAILS, CHAT_PROMPT, PRESENCE_PROMPT defined")

phi = None
if PhiMini is not None and os.getenv("PHI_ENABLED", "1") == "1":
    # Use the local GGUF file directly (recommended for your setup)
    model_path = "models/Phi-3-mini-4k-instruct.Q4_0.gguf"
    try:
        phi = PhiMini(model_path)
        print(f"PhiMini loaded from {model_path}")
    except Exception as e:
        phi = None
        try:
            print(f"PhiMini loader: failed to initialize with {model_path}: {e}")
        except Exception:
            pass


@app.get("/phi-test")
def phi_test(prompt: str = "Respond briefly and calmly. Response:", max_tokens: int = 60):
    """Quick test endpoint to verify the model is actually generating text.

    If the model isn't loaded, returns an error message instead of raising.
    """
    if phi is None:
        return {"ok": False, "error": "Model is not loaded"}

    try:
        gen = phi.generate(prompt, max_tokens=max_tokens)
        return {"ok": True, "response": gen}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/")
def serve_ui():
    try:
        return FileResponse(os.path.join("..", "frontend", "index.html"))
    except:
        return {"message": "Echo Backend API is running."}


@app.get('/debug/jenny_test')
def debug_jenny():
    """Attempt to synthesize a short Jenny phrase and return the file path or error."""
    try:
        from tts.voice_manager import synthesize_voice
        p = synthesize_voice("I am here. Just listening.", voice='she')
        return {"ok": True, "audio": p}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/dream", response_model=DreamResponse)
def analyze_dream(data: DreamInput):
    dream_text = data.dream
    voice = data.voice

    emotions = extract_emotions(dream_text)
    category = classify_dream(emotions)

    # Message 1 — template based (deterministic)
    base_text = build_response(category, emotions)

    # Store dream context and reset history
    SESSION["dream_context"] = base_text
    SESSION["history"] = []

    messages = []

    # Message 1 — neutral grounding (template)
    # Synthesize server-side audio for the message (backend is authoritative)
    audio_path = None
    try:
        from tts.voice_manager import synthesize_voice
        audio_path = synthesize_voice(base_text, voice=voice)
    except Exception as e:
        print(f"TTS generation failed for m1: {e}")
        audio_path = None

    messages.append(
        Message(
            id="m1",
            text=base_text,
            tts=True,
            audio=audio_path
        )
    )
    print(f"Dream MESSAGE m1 audio (voice={voice}): {audio_path}")

    # Message 2 — presence reply (short, human, non-analytical)
    presence_text = "I hear you — that felt like something that mattered."

    # Build presence prompt if available
    presence_prompt = None
    if PRESENCE_PROMPT:
        presence_prompt = PRESENCE_PROMPT.format(dream=dream_text)

    # Generate presence reply with phi if available (guarded)
    if phi is not None and presence_prompt:
        # Try to acquire model lock to avoid concurrent heavy runs
        if not MODEL_LOCK.acquire(blocking=False):
            # Model busy — skip model generation and keep deterministic presence_text (no busy message)
            pass
        else:
            try:
                gen = phi.generate(presence_prompt, max_tokens=60)
                if gen:
                    presence_text = sanitize_presence_reply(gen)
            except Exception:
                # keep fallback
                pass
            finally:
                MODEL_LOCK.release()

    # Sanitize generated text
    try:
        from core.safeguards.dependency_filter import sanitize
        presence_text = sanitize(presence_text)
    except Exception:
        pass

    # Synthesize presence reply audio as well; non-fatal if synthesis fails
    presence_audio = None
    try:
        from tts.voice_manager import synthesize_voice
        presence_audio = synthesize_voice(presence_text, voice=voice)
    except Exception as e:
        print(f"TTS generation failed for presence reply: {e}")
        presence_audio = None

    messages.append(
        Message(
            id="m2",
            text=presence_text,
            tts=True,
            audio=presence_audio
        )
    )
    print(f"Dream MESSAGE m2 audio (voice={voice}): {presence_audio}")

    return DreamResponse(messages=messages)


@app.get('/debug/male_test')
def debug_male():
    """Attempt to synthesize a short male phrase and return the file path or error."""
    try:
        from tts.voice_manager import synthesize_voice
        p = synthesize_voice("This is a male voice test.", voice='he')
        return {"ok": True, "audio": p}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/chat", response_model=DreamResponse)
def chat(data: ChatInput):
    user_msg = data.message
    # Respect client's voice selection (no silent defaulting)
    voice = data.voice

    # Add user message to session history
    SESSION["history"].append(f"User: {user_msg}")

    # Build compact context (dream + recent history)
    context = (
        "Dream:\n"
        + SESSION.get("dream_context", "")
        + "\n\nConversation so far:\n"
        + "\n".join(SESSION["history"][-6:])
    )

    # Build prompt
    prompt = ""
    if SYSTEM_GUARDRAILS:
        prompt += SYSTEM_GUARDRAILS
    
    if not CHAT_PROMPT:
        raise RuntimeError("CHAT_PROMPT is not loaded. Check llm/prompt.py import.")
    
    prompt += CHAT_PROMPT.format(context=context, message=user_msg)

    # Generate with phi if available (guarded)
    if phi is not None:
        # Acquire model lock to prevent overlapping heavy runs
        if not MODEL_LOCK.acquire(blocking=False):
            print("Model busy; rejecting overlapping request")
            # Don't append placeholder messages in the UI — return 429 so frontend can hide loader and let user retry
            raise HTTPException(status_code=429, detail="model_busy")
        else:
            try:
                reply = phi.generate(prompt, max_tokens=150)
            except Exception as e:
                print(f"phi.generate failed: {e}")
                reply = "Sorry, I couldn't generate a thoughtful reply right now."
            finally:
                MODEL_LOCK.release()
    else:
        print("phi is not loaded; returning fallback reply")
        reply = (
            "This thought seems connected to the feeling you described earlier. "
            "Notice how it relates to the same emotional pattern, without needing to resolve it immediately."
        )

    # Sanitize and append assistant reply to history
    try:
        from core.safeguards.dependency_filter import sanitize
        reply = sanitize(reply)
    except Exception:
        pass

    SESSION["history"].append(f"Echo: {reply}")

    # Synthesize server-side audio (Jenny required for 'she')
    audio_path = None
    try:
        from tts.voice_manager import synthesize_voice
        audio_path = synthesize_voice(reply, voice=voice)
    except Exception as e:
        # If the user specifically requested 'she' and synthesis failed, respond with 500
        if str(voice).lower() == "she":
            print(f"Jenny TTS failed: {e}")
            raise HTTPException(status_code=500, detail="tts_unavailable_for_she")
        audio_path = None

    return DreamResponse(messages=[
        Message(id="c1", text=reply, tts=True, audio=audio_path)
    ])
