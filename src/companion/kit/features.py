"""What a feature is, as the turn sees it: the parts it declares (design sketch, 2026-10-23).

A feature lists only the parts it has. Its look-up runs with the others before the reply, side by
side under the turn's deadline; its note reads what the look-up found and joins the notes, in the
order of `ORDER` in `turn/notes.py`. Adding a feature is its module plus one line in `FEATURES`
(and a name in `ORDER` for a note): no field on `Lookups`, no branch in `look`, no entry written by
hand in `SOURCES`. The turn reaches a feature only through the parts it declares here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection, Coroutine, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from companion.core.reachout import PRECEDENCE, Held, Kind
from companion.core.switch import Mode, Switch
from companion.core.types import Belief, BeliefId, Frame, Utterance
from companion.kit.current import Heard, Turn, is_casual

if TYPE_CHECKING:
    from datetime import datetime, tzinfo

    from companion.core.card import Card
    from companion.core.extractor import StructuredModel
    from companion.core.turn.mentions import MentionCandidate
    from companion.core.types import RelationshipId
    from companion.kit.jobs import Job
    from companion.kit.runtime import Runtime
    from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Offer:
    """What one note source gives the turn: lines for the system block, and the writes it makes
    once the reply is stored (a cap used, a plan marked asked), so a failed turn uses none."""

    lines: tuple[str, ...] = ()
    after: tuple[Callable[[], None], ...] = ()
    tail: tuple[str, ...] = ()  # lines sent after the history, where they weigh most
    asks: bool = False  # its lines ask them something, so the question-run note stays out


@dataclass(frozen=True, slots=True)
class CardLane:
    """What a feature does to this turn's request on top of the everyday card: memories left off it,
    a card sent instead of it, text pinned after the history, and the writes made once the turn is
    stored."""

    hidden: frozenset[BeliefId] = frozenset()  # left off the everyday card
    text: str | None = None  # sent instead of the everyday card ("" sends no card at all)
    pinned: str = ""  # sent after the history, where it weighs most
    after: tuple[Callable[[], None], ...] = ()


type Look = Callable[[Runtime, Turn, Frame, Heard | None], Awaitable[object]]
# Once the turn is stored: their message as kept, and the reply sent (None when it only reacted).
# A step that should not hold up the reply starts its own task and returns.
type AfterTurn = Callable[[Runtime, Turn, Utterance, str | None], Awaitable[None]]
# A look-up in shadow: run beside the turn once the reply is out, with the card it was sent; it logs
# what it would have done and never changes the reply. A failure is logged by `turn/beside.py`.
type Shadow = Callable[[Runtime, Turn, Frame, Heard | None, Card], Coroutine[object, object, None]]


# A feature's part in the request's card, given the card built so far (`turn/assemble.py`).
class Lane(Protocol):
    def __call__(
        self, c: Runtime, t: Turn, looked: Lookups, *, roleplay: bool, card: Card
    ) -> CardLane: ...


# A note gets what its look-up found (None when it found nothing) and what earlier notes offered.
type Note = Callable[[Moment, object, Offered], Offer]
# What a feature would bring up on its own this turn, its best only, chosen across features by one
# picker (`turn/mention.py`); it gets what its look-up found. No gating, no cap, no write.
type Mention = Callable[[Moment, object], MentionCandidate | None]


class Offered(Mapping[str, Offer]):
    """What the notes before this one offered. A note reads an earlier one by name only if it
    declared it in `reads` (`turn/notes.py` checks at load that each comes earlier in `ORDER`); an
    undeclared name raises. What any earlier note asks is read through `asking`."""

    def __init__(self, offers: Mapping[str, Offer], reads: Collection[str] | None = None) -> None:
        self.asking = any(o.asks and (o.lines or o.tail) for o in offers.values())
        names = offers.keys() if reads is None else reads
        self._named = {n: offers[n] for n in names}

    asking: bool  # whether any earlier note asks them something

    def __getitem__(self, name: str) -> Offer:
        try:
            return self._named[name]
        except KeyError:
            msg = f"a note read {name!r} without declaring it in `reads`"
            raise KeyError(msg) from None

    def __iter__(self) -> Iterator[str]:
        return iter(self._named)

    def __len__(self) -> int:
        return len(self._named)


# The earlier notes `has_room` reads, for a note to declare.
ROOM_READS = ("name", "how-are-you")


def has_room(m: Moment, so_far: Offered) -> bool:
    """A casual turn with no name asked, no how-are-you question and nothing held: room for a plan
    or a move on. Reads `ROOM_READS`."""
    return m.casual and not so_far["name"].lines and not so_far["how-are-you"].lines and not m.held


def asking(so_far: Offered) -> bool:
    """Whether a note offered so far asks them something this turn (its offer says `asks`)."""
    return so_far.asking


class Spent(Protocol):
    @property
    def cost_usd(self) -> float: ...


# A step after a memory pass: it reads the store, may ask a model, and says what it cost.
type Step = Callable[[Store, StructuredModel, RelationshipId, datetime], Awaitable[Spent]]


@dataclass(frozen=True, slots=True)
class Passing:
    """What a memory pass is set up with besides the store and the model: where each switch stands
    and the character's sheet. Built once (`compose.pass_options`) for the bot and for the commands
    that run a pass, so they run the same one."""

    modes: Mapping[Switch, Mode]
    sheet: str = ""

    def mode(self, switch: Switch) -> Mode:
        return self.modes[switch]


# A step every pass runs, set up from `Passing`; None when its switch is off.
type PassStep = Callable[[Passing], Step | None]


@dataclass(frozen=True, slots=True)
class NightStep:
    """One part of the night's memory work (`memory/nightly.py`), run on its own so one failing does
    not skip the rest. With a `switch`, it is left out while that switch is off."""

    name: str  # in the log line that says it failed
    run: Callable[[Runtime, StructuredModel], Awaitable[None]]
    switch: Switch | None = None


@dataclass(frozen=True, slots=True)
class Outlet:
    """Where the bot sends its own messages while it runs: the platform's send, and its name."""

    send: Callable[[str], Awaitable[object]]
    platform: str


type Jobs = Callable[[Runtime, Outlet], Sequence[Job]]  # background work, as data (`kit/jobs.py`)


@dataclass(slots=True)
class Round:
    """One tick of the timer that reaches out first (ADR 0021), as the steps that can take it see
    it. A step takes the tick by setting `first` to its kind, which the later steps respect."""

    now: datetime
    tz: tzinfo
    held: Held | None = None  # what holds every reach-out now (the shared gate), set by its step
    first: Kind | None = None  # the reach-out an earlier step took this tick


@dataclass(frozen=True, slots=True)
class Move:
    """A feature's step in the initiative tick. `kind` is the reach-out it can take, and the steps
    run in `Kind` order (`core/reachout.py`: a plan, then a nudge, then its own reasons); None runs
    before them all, for the shared gate."""

    kind: Kind | None
    run: Callable[[Round], Awaitable[None]]

    @property
    def rank(self) -> int:
        return -1 if self.kind is None else PRECEDENCE.index(self.kind)


# What a feature adds to the initiative tick, built once at the start (it keeps what it must).
type Reaching = Callable[[Runtime], Sequence[Move]]


@dataclass(frozen=True, slots=True)
class Feature:
    name: str  # its name in the notes' order and in the look-ups' log lines
    look: Look | None = None
    note: Note | None = None
    after_theirs: Step | None = None  # after a memory pass stored new memories of theirs
    after_own: Step | None = None  # after a memory pass stored new views of its own
    after_pass: PassStep | None = None  # after every memory pass, whatever it stored
    nightly: NightStep | None = None  # its part of the night's memory work, in registry order
    reaching: Reaching | None = None  # its steps in the initiative tick
    jobs: Jobs | None = None  # background work of its own, started with the bot
    shadow: Shadow | None = None
    after_turn: AfterTurn | None = None
    mention: Mention | None = None  # what it would bring up on its own this turn (ADR 0023)
    lane: Lane | None = None  # what it does to the request's card (the scene card, memories hidden)
    reads: tuple[str, ...] = ()  # earlier notes its note reads by name; they must come before it
    # Its look-up gets the route's read in a scene, where the listening judge does not run.
    scene_read: bool = False


@dataclass(frozen=True, slots=True)
class Lookups:
    """What a reply waits for besides the judges: what each feature's look-up found."""

    found: Mapping[str, object] = field(default_factory=dict[str, object])  # by feature name

    def find[T](self, kind: type[T]) -> T | None:
        """What the look-ups found that is a `kind`, for a consumer that cannot name the feature
        that found it. A type no look-up returns gives None; one two look-ups return is an error."""
        hits = [v for v in self.found.values() if isinstance(v, kind)]
        if len(hits) > 1:
            msg = f"{len(hits)} look-ups found a {kind.__name__}; ask by feature"
            raise LookupError(msg)
        return hits[0] if hits else None


@dataclass(frozen=True, slots=True)
class Moment:
    """What every note reads about the turn being answered."""

    c: Runtime
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
