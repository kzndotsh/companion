"""Their message for a turn, stored in exactly one place (the persist stage of a turn)."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from companion.core.types import Frame, Speaker, Utterance, UtteranceId
from companion.loops.turn import Turn

if TYPE_CHECKING:
    from companion.loops.fast import Conversation


def store_user(c: Conversation, t: Turn, channel: str, frame: Frame) -> Utterance:
    said = Utterance(
        UtteranceId(uuid.uuid4().hex),
        c.rel,
        t.session,
        t.turn,
        Speaker.USER,
        t.text,
        frame,
        channel,
        t.now,
    )
    c.store.append_utterance(said)
    return said


class TheirMessage:
    """Their message for this turn, stored exactly once: with the frame the turn resolved, or, if
    the turn fails before that, as real when the guard closes."""

    def __init__(self, c: Conversation, t: Turn, channel: str) -> None:
        self.c, self.t, self.channel = c, t, channel
        self.said: Utterance | None = None

    def store(self, frame: Frame) -> Utterance:
        if self.said is None:
            self.said = store_user(self.c, self.t, self.channel, frame)
        return self.said


@contextlib.asynccontextmanager
async def their_message(c: Conversation, t: Turn, channel: str) -> AsyncGenerator[TheirMessage]:
    """The one place their message is stored. A turn that fails at any stage still keeps it, as
    real, and the failure goes on up; before, an error in the look-ups or the card lost it."""
    keep = TheirMessage(c, t, channel)
    try:
        yield keep
    except BaseException:
        keep.store(Frame.REAL)
        raise
