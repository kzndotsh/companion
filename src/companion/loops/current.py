"""The turn being answered now: its facts, its debug marks, recording its decisions, and whether
it is an ordinary moment. Shared by the stages and every feature."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.turn.goodbye import leaving
from companion.core.turn.listening import Judgement as ListenJudgement
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
