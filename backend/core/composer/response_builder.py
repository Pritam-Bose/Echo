# -*- coding: utf-8 -*-
import json

def build_response(category, emotions):
    with open(f"backend/core/templates/{category}.json") as f:
        template = json.load(f)

    response = (
        f"{template['opening']} "
        f"{template['body']} "
        f"{template['grounding']}"
    )

    return response
