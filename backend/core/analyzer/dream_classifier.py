# -*- coding: utf-8 -*-
def classify_dream(emotions: list) -> str:
    if "loss" in emotions:
        return "loss"
    if "fear" in emotions:
        return "fear"
    if "peace" in emotions:
        return "romantic"
    return "neutral"
