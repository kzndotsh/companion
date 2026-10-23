"""What a feature is, as the turn sees it: the parts it declares (design sketch, 2026-10-23).

A feature lists only the parts it has. Its look-up runs with the others before the reply, side by
side under the turn's deadline; its note reads what the look-up found and joins the notes, in the
order of `FEATURES` in `loops/notes.py`. Adding a feature is its module plus one line there: no
field on `Lookups`, no branch in `look`, no entry written by hand in `SOURCES`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from companion.core.extractor import Extractor
    from companion.core.types import Frame, RelationshipId
    from companion.loops.fast import Conversation
    from companion.loops.notes import Moment
    from companion.loops.turn import Heard, Turn
    from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Offer:
    """What one note source gives the turn: lines for the system block, and the writes it makes
    once the reply is stored (a cap used, a plan marked asked), so a failed turn uses none."""

    lines: tuple[str, ...] = ()
    after: tuple[Callable[[], None], ...] = ()
    tail: tuple[str, ...] = ()  # lines sent after the history, where they weigh most


type Look = Callable[[Conversation, Turn, Frame, Heard | None], Awaitable[object]]
# A note gets what the look-up found, or None when it found nothing.
type Note = Callable[[Moment, object], Offer]


class Spent(Protocol):
    @property
    def cost_usd(self) -> float: ...


# A step after a memory pass: it reads the store, may ask a model, and says what it cost.
type Step = Callable[[Store, Extractor, RelationshipId, datetime], Awaitable[Spent]]


@dataclass(frozen=True, slots=True)
class Feature:
    name: str  # its name in the notes' order and in the look-ups' log lines
    look: Look | None = None
    note: Note | None = None
    after_theirs: Step | None = None  # after a memory pass stored new memories of theirs
    after_own: Step | None = None  # after a memory pass stored new views of its own
