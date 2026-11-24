# -*- coding: utf-8 -*-
import json
import os

# Anchored to this file so templates resolve from any working directory
TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")


def build_response(category, emotions):
    with open(os.path.join(TEMPLATES, f"{category}.json"), encoding="utf-8") as f:
        template = json.load(f)

    response = (
        f"{template['opening']} "
        f"{template['body']} "
        f"{template['grounding']}"
    )

    return response
