# -*- coding: utf-8 -*-
"""symbol_mapper - small skeleton"""

SYMBOL_MAP = {}


def map_symbol(symbol: str) -> str:
    return SYMBOL_MAP.get(symbol, "")
