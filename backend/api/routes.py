# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from dotenv import load_dotenv

load_dotenv()

from api.schemas import DreamInput, DreamResponse, Message, ChatInput
from core.analyzer.emotion_extractor import extract_emotions
from core.analyzer.dream_classifier import classify_dream
from core.composer.response_builder import build_response
from tts.voice_manager import synthesize_voice

app = FastAPI()


def _tts(text: str, voice: str):
    """Server-side synthesis; failures are non-fatal and return None."""
    try:
        return synthesize_voice(text, voice=voice)
    except Exception as e:
        print(f"TTS generation failed: {e}")
        return None


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

# Paths are anchored to this file so the app works from any working directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "frontend")
AUDIO_DIR = os.path.join(BACKEND_DIR, "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Serve UI (frontend folder sits next to backend)
try:
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")
except Exception as e:
    print(f"UI mount failed, frontend will not be served: {e}")

# Serve generated audio files
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Minimal in-memory session store (safe for development)
SESSION = {
    "dream_context": "",
    "history": []
}

# --- LLM (Groq cloud) ---
from llm.groq_llm import GroqLLM

# Prompts are always required - import them with error handling
try:
    from llm.prompt import SYSTEM_GUARDRAILS, CHAT_PROMPT, PRESENCE_PROMPT
except Exception as e:
    print(f"ERROR: Failed to load prompts from llm.prompt: {e}")
    raise RuntimeError("Critical: llm/prompt.py must be importable with SYSTEM_GUARDRAILS, CHAT_PROMPT, PRESENCE_PROMPT defined")

if os.getenv("GROQ_API_KEY"):
    llm = GroqLLM()
    print(f"GroqLLM ready (model={llm.model})")
else:
    llm = None
    print("Warning: GROQ_API_KEY not set; Echo will use fallback replies.")


@app.get("/llm-test")
def llm_test(prompt: str = "Respond briefly and calmly.", max_tokens: int = 60):
    """Smoke test: verify the Groq model actually generates text."""
    if llm is None:
        return {"ok": False, "error": "GROQ_API_KEY not set"}

    try:
        return {"ok": True, "response": llm.generate(prompt, max_tokens=max_tokens)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/")
def serve_ui():
    # index.html loads ./chat.css and ./chat.js, so it must be served from the /ui mount
    return RedirectResponse("/ui/")


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
    audio_path = _tts(base_text, voice)

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
    if llm is not None and presence_prompt:
        try:
            gen = llm.generate(presence_prompt, max_tokens=60)
            if gen:
                presence_text = sanitize_presence_reply(gen)
        except Exception:
            pass  # keep the deterministic fallback

    # Sanitize generated text
    try:
        from core.safeguards.dependency_filter import sanitize
        presence_text = sanitize(presence_text)
    except Exception:
        pass

    presence_audio = _tts(presence_text, voice)

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

    if llm is not None:
        try:
            reply = llm.generate(prompt, max_tokens=150)
        except Exception as e:
            print(f"llm.generate failed: {e}")
            reply = "Sorry, I couldn't generate a thoughtful reply right now."
    else:
        print("llm is not loaded; returning fallback reply")
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

    audio_path = _tts(reply, voice)
    if audio_path is None and str(voice).lower() == "she":
        raise HTTPException(status_code=500, detail="tts_unavailable_for_she")

    return DreamResponse(messages=[
        Message(id="c1", text=reply, tts=True, audio=audio_path)
    ])
