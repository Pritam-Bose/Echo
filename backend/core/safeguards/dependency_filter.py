# -*- coding: utf-8 -*-
from backend.core.safeguards.forbidden_phrases import FORBIDDEN

def sanitize(text: str) -> str:
    lower = text.lower()
    for phrase in FORBIDDEN:
        if phrase in lower:
            return "Let's pause here. This experience is about understanding, not attachment."
    return text
