"""What the small judges read of a conversation, and the hash a logged decision keeps of it."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from companion.core.types import Speaker, Utterance

# 8, not 4: with 4, a curt "thanks" after a hurt and a grudging forgiveness two exchanges back read
# as a plain ack every time (12/12) and got only an emoji; with 8 it got a reply 11/12. Past 8 the
# reads did not change (evals/CHANGELOG.md, 2026-11-02).
CONTEXT_MESSAGES = 8


def build_prompt(history: Sequence[Utterance], text: str) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in history[-CONTEXT_MESSAGES:]
    ]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {text}"])


def inputs_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()
