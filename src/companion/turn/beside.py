"""What runs beside a turn and never changes the reply: shadow look-ups, each logged, a failure
logged too (the shadow stage of a turn)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.types import Frame
from companion.loops.current import Heard, Turn
from companion.registry import FEATURES

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


_BESIDE: set[asyncio.Task[None]] = set()  # shadow look-ups still running, kept from collection


def beside(job: Coroutine[object, object, None]) -> None:
    """Run a shadow look-up beside the turn, kept from collection until it ends. A failure is
    logged, never raised and never silent."""
    task = asyncio.get_running_loop().create_task(job)
    _BESIDE.add(task)

    def done(finished: asyncio.Task[None]) -> None:
        _BESIDE.discard(finished)
        if not finished.cancelled() and finished.exception() is not None:
            log.warning("shadow look-up failed: %r", finished.exception())

    task.add_done_callback(done)


def shadows(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, card: Card) -> None:
    """What runs in shadow on a turn and never changes the reply: each feature's shadow look-up."""
    for feature in FEATURES:
        if feature.shadow is not None:
            beside(feature.shadow(c, t, in_scene, heard, card))
