"""What each stage of the turn hands the next, and cancelling what a stage left running."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

from companion.core.crisis import Reading
from companion.core.frames import Judgement as FrameJudgement
from companion.core.talker import Reply, Talker
from companion.core.turn.ack import Reaction
from companion.core.turn.react import ToneRead
from companion.core.types import Frame
from companion.kit.current import Heard


@dataclass(frozen=True, slots=True)
class Listened:
    """The listen stage: a reaction to send instead of a reply, or what the listening judge heard
    (None when it could not read the message)."""

    reaction: Reaction | None
    heard: Heard | None


@dataclass(frozen=True, slots=True)
class Routed:
    """The route stage: the talker that answers, whether the floor held the turn, the reading the
    route used (in a scene, its own), and whether they pushed the flirting back."""

    talker: Talker
    held: bool
    read: Heard | None
    brushed: bool
    heard: Heard | None  # the listening judge's read of their message
    in_scene: Frame
    crisis: Reading | None = None  # the crisis path's reading (ADR 0022), set after the look-ups


@dataclass(frozen=True, slots=True)
class Answered:
    """The talk stage: the checked reply, and the frame and reaction readings made beside it."""

    reply: Reply
    framed: tuple[FrameJudgement, str, str] | None
    felt: tuple[ToneRead, str, str] | None
    in_scene: Frame


async def stop(*tasks: asyncio.Future[Any] | None) -> None:
    """Cancel whatever a stage still has running beside it."""
    for task in tasks:
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
