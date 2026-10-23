"""The turn being answered: its facts, its debug marks, recording its decisions, and whether it
is an ordinary moment. Shared by the turn loop and its notes."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from companion.core.frames import Judgement as FrameJudgement
from companion.core.talker import Reply, Talker
from companion.core.turn.ack import Reaction
from companion.core.turn.goodbye import leaving
from companion.core.turn.listening import Judgement as ListenJudgement
from companion.core.turn.react import Judgement as ReactJudgement
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    SessionId,
    TraceId,
    TurnId,
    Utterance,
)
from companion.loops.record import Recorder

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


@dataclass(frozen=True, slots=True)
class Turn:
    session: SessionId
    turn: TurnId
    now: datetime
    prior: list[Utterance]
    text: str
    started: float = field(default_factory=time.perf_counter)


def mark(t: Turn, what: str) -> None:
    """One DEBUG line per stage of a turn, with the milliseconds since the turn began."""
    log.debug("turn %s +%dms %s", t.turn[:8], (time.perf_counter() - t.started) * 1000, what)


def recorder(c: Conversation, t: Turn) -> Recorder:
    return Recorder(c.store, c.rel, t.session, t.turn, TraceId(t.turn), t.now)


def decide(  # noqa: PLR0913
    c: Conversation,
    t: Turn,
    key: str,
    detail: dict[str, Json] | None = None,
    *,
    reason: str | None = None,
    kind: DecisionKind = DecisionKind.POLICY,
    at: datetime | None = None,
) -> None:
    """Record one of this turn's decisions (`loops/record.py`)."""
    recorder(c, t).decide(key, detail, reason=reason, kind=kind, at=at)


def is_casual(t: Turn, in_scene: Frame, heard: Heard | None) -> bool:
    """An ordinary moment: read as not serious, not in a scene, not a goodbye."""
    return (
        heard is not None
        and heard[0].severity == 0
        and in_scene is Frame.REAL
        and not leaving(t.text)
    )


Heard = tuple[ListenJudgement, str, str]


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


@dataclass(frozen=True, slots=True)
class Answered:
    """The talk stage: the checked reply, and the frame and reaction readings made beside it."""

    reply: Reply
    framed: tuple[FrameJudgement, str, str] | None
    felt: tuple[ReactJudgement, str, str] | None
    in_scene: Frame


async def stop(*tasks: asyncio.Future[Any] | None) -> None:
    """Cancel whatever a stage still has running beside it."""
    for task in tasks:
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
