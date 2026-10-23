"""A memory shown with the conversation around its quote: the window and how it is written for a
model. Shared by the features that read a memory in its moment (context notes, memory labels)."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.types import Belief, Speaker, Utterance

BEFORE, AFTER = 6, 1  # messages around the quote that a memory is read with


def build_prompt(b: Belief, around: Sequence[Utterance]) -> str:
    lines = [f"{'USER' if u.speaker is Speaker.USER else 'COMPANION'}: {u.text}" for u in around]
    return "\n".join(
        [f"Memory: {b.claim}", f'Their words: "{b.evidence[0].quote}"', "", "Conversation:", *lines]
    )
