# -*- coding: utf-8 -*-
def extract_emotions(text: str) -> list:
    emotions = []

    keywords = {
        "loss": ["lost", "gone", "disappeared", "khoya", "chole geche"],
        "peace": ["calm", "shaant", "peace", "shanto"],
        "longing": ["cry", "miss", "want back", "chesta", "khujlam"],
        "fear": ["jungle", "dark", "chase", "bhoy"]
    }

    for emotion, words in keywords.items():
        if any(w in text.lower() for w in words):
            emotions.append(emotion)

    return emotions or ["neutral"]
