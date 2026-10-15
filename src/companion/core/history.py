"""What the talker sees of the past. Live and replay must use these same two rules."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.prompt.request import Message
from companion.core.types import Speaker, Utterance

HISTORY_LIMIT = 40


def to_messages(utterances: Sequence[Utterance]) -> list[Message]:
    return [
        Message("user" if u.speaker is Speaker.USER else "assistant", u.text) for u in utterances
    ]
