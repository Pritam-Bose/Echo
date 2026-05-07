# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import List, Optional


class Message(BaseModel):
    id: str
    text: str
    tts: bool = True
    audio: Optional[str] = None


class DreamResponse(BaseModel):
    messages: List[Message]


class DreamInput(BaseModel):
    dream: str
    voice: str


class ChatInput(BaseModel):
    message: str
    voice: str

