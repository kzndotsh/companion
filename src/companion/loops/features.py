"""What a feature is, as the turn sees it: the parts it declares (design sketch, 2026-10-23).

A feature lists only the parts it has. Its look-up runs with the others before the reply, side by
side under the turn's deadline; its note reads what the look-up found and joins the notes, in the
order of `ORDER` in `turn/notes.py`. Adding a feature is its module plus one line there: no
field on `Lookups`, no branch in `look`, no entry written by hand in `SOURCES`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from companion.core.types import Belief, BeliefId, Frame, Utterance
from companion.loops.current import Heard, Turn, is_casual
from companion.loops.recall import Recalled

if TYPE_CHECKING:
    from datetime import datetime

    from companion.core.card import Card
    from companion.core.extractor import Extractor
    from companion.core.types import RelationshipId
    from companion.loops.conversation import Conversation
    from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Offer:
    """What one note source gives the turn: lines for the system block, and the writes it makes
    once the reply is stored (a cap used, a plan marked asked), so a failed turn uses none."""

    lines: tuple[str, ...] = ()
    after: tuple[Callable[[], None], ...] = ()
    tail: tuple[str, ...] = ()  # lines sent after the history, where they weigh most


type Look = Callable[[Conversation, Turn, Frame, Heard | None], Awaitable[object]]
# Once the turn is stored: their message as kept, and the reply sent (None when it only reacted).
# A step that should not hold up the reply starts its own task and returns.
type AfterTurn = Callable[[Conversation, Turn, Utterance, str | None], Awaitable[None]]
# A look-up in shadow: run beside the turn once the reply is out, with the card it was sent; it logs
# what it would have done and never changes the reply. A failure is logged by `turn/beside.py`.
type Shadow = Callable[
    [Conversation, Turn, Frame, Heard | None, Card], Coroutine[object, object, None]
]
Offered = Mapping[str, Offer]  # what the notes before this one offered, by name

# A note gets what its look-up found (None when it found nothing) and what earlier notes offered.
type Note = Callable[[Moment, object, Offered], Offer]


def quiet(m: Moment, so_far: Offered) -> bool:
    """A casual turn with no name asked, no check-in and nothing held: room for a plan or a
    move on."""
    return m.casual and not so_far["name"].lines and not so_far["check-in"].lines and not m.held


# Notes that ask them something themselves: with one of these the turn's question is the point.
ASKING = ("check-in", "name", "loop", "crisis", "game", "calendar")


def asking(so_far: Offered) -> bool:
    """Whether a note offered so far asks them something this turn."""
    return any(o.lines or o.tail for n in ASKING if (o := so_far.get(n)) is not None)


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
    shadow: Shadow | None = None
    after_turn: AfterTurn | None = None


@dataclass(frozen=True, slots=True)
class Lookups:
    """What a reply waits for besides the judges: a recall, whether a topic is spent, a guess."""

    recalled: Recalled | None = None
    found: Mapping[str, object] = field(default_factory=dict[str, object])  # by feature name


@dataclass(frozen=True, slots=True)
class Moment:
    """What every note reads about the turn being answered."""

    c: Conversation
    t: Turn
    in_scene: Frame
    heard: Heard | None
    looked: Lookups
    held: bool  # the floor held this turn (ADR 0017)
    beliefs: Sequence[Belief]  # the memories that may be stated as true
    on_card: frozenset[BeliefId] = frozenset()  # what the card already shows this turn
    brushed: bool = False  # they pushed the flirting or the scene back (`system/brush-off`)
    risk: bool = False  # the crisis path acts on a concern or urgent reading (ADR 0022)

    @property
    def casual(self) -> bool:
        """Never on a turn the crisis path reads as a risk, whatever the listening judge said."""
        return not self.risk and is_casual(self.t, self.in_scene, self.heard)
