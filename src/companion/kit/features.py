"""What a feature is, as the turn sees it: the parts it declares (design sketch, 2026-10-23).

A feature lists only the parts it has. Its look-up runs with the others before the reply, side by
side under the turn's deadline; its note reads what the look-up found and joins the notes, in the
order of `ORDER` in `turn/notes.py`. Adding a feature is its module plus one line in `FEATURES`
(and a name in `ORDER` for a note): no field on `Lookups`, no branch in `look`, no entry written by
hand in `SOURCES`. The turn reaches a feature only through the parts it declares here.
"""

from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
    Collection,
    Coroutine,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from companion.core.reachout import PRECEDENCE, Held, Kind
from companion.core.switch import Mode, Switch
from companion.core.types import (
    Belief,
    BeliefId,
    Frame,
    Json,
    Severity,
    Utterance,
    UtteranceId,
    is_heavy,
)
from companion.kit.current import Heard, Turn, is_casual

if TYPE_CHECKING:
    from datetime import datetime, tzinfo

    from companion.core.card import Card
    from companion.core.extractor import StructuredModel
    from companion.core.turn.mentions import MentionCandidate
    from companion.core.types import RelationshipId
    from companion.core.vectors import Embedder
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


# Every hook reads the turn through one `Moment` (what is known by then: a look-up has no `looked`,
# `beliefs` or `on_card` yet), and gets besides it only what exists at its own stage.
LOOKS_TOGETHER_SECONDS = 9.0  # every look-up together; past it the reply goes without the late ones

type Look = Callable[[Moment], Awaitable[object]]
# Once the turn is stored: their message as kept, and the reply sent (None when it only reacted).
# The dispatcher runs the step beside the reply unless the feature says `must_finish`.
type AfterTurn = Callable[[Moment, Utterance, str | None], Coroutine[object, object, None]]
# A look-up in shadow: run beside the turn once the reply is out (`Moment.on_card` is the card it
# was sent); it logs what it would have done and never changes the reply. A failure is logged by
# `kit/beside.py`.
type Shadow = Callable[[Moment], Coroutine[object, object, None]]


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


class NoteName(StrEnum):
    """Every note's name, in one place: `ORDER` in `turn/notes.py`, a `Feature`'s name and the notes
    one reads through `reads` all use these, so a rename is one edit."""

    TICS = "tics"
    BASE = "base"
    LENGTH = "length"
    REPLIED_TO = "replied-to"
    LISTENING = "listening"
    RUDE = "rude"
    REPAIR = "repair"
    OWNED = "owned"
    RECALL = "recall"
    NOW = "now"
    RELEVANT = "relevant"
    RECENT = "recent"
    HOW_ARE_YOU = "how-are-you"
    MOOD = "mood"
    HOLD = "hold"
    BRUSH_OFF = "brush-off"
    NAME = "name"
    MEMORY_MAP = "memory map"
    GUESS = "guess"
    REMINDER = "reminder"
    CRISIS = "crisis"
    GAME = "game"
    MENTION = "mention"
    TOPIC = "topic"
    LORE = "lore"
    MARK = "mark"
    QUESTIONS = "questions"


# The earlier notes `has_room` reads, for a note to declare.
ROOM_READS = (NoteName.NAME, NoteName.HOW_ARE_YOU)


def has_room(m: Moment, so_far: Offered) -> bool:
    """A casual turn with no name asked, no how-are-you question and nothing held: room for a plan
    or a move on. Reads `ROOM_READS`."""
    return (
        m.casual
        and not so_far[NoteName.NAME].lines
        and not so_far[NoteName.HOW_ARE_YOU].lines
        and not m.held
    )


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
    """What a memory pass is set up with besides the store and the model: where each switch stands,
    the character's sheet, and the embedder. Built once (`compose.pass_options`) for the bot and for
    the commands that run a pass, so they run the same one."""

    switches: Mapping[Switch, str]  # each switch's position, by the row
    sheet: str = ""
    embedder: Embedder | None = None
    embed_model: str = ""
    judge: StructuredModel | None = None  # the model the pass reads with

    def mode(self, switch: Switch) -> Mode:
        return Mode(self.switches[switch])

    def on(self, switch: Switch) -> bool:
        """Whether a switch is anything but off."""
        return self.switches[switch] != Mode.OFF


# A step every pass runs, set up from `Passing`; None when its switch is off.
type PassStep = Callable[[Passing], Step | None]

# Writes a decision of the pass: its reason and detail. The pass records it under its own run.
type Log = Callable[[str, dict[str, Json]], None]

# A reader of the companion's own messages in the open-loop batch: the cost, or None when its call
# failed so the batch is read again. It rides the loop batch and its bookmark (`Feature.own_loop`).
type OwnReader = Callable[
    [
        Store,
        StructuredModel,
        Mapping[str, Utterance],
        set[UtteranceId],
        tuple[datetime, tzinfo],
        Log,
    ],
    Awaitable[float | None],
]
type OwnLoopSetup = Callable[[Passing], OwnReader | None]

# The open-loop read of a pass: their messages from its own bookmark, with the readers of the
# companion's own messages that ride the same batch. A failed call leaves the bookmark, so the
# batch is read again.
type Loops = Callable[
    [Store, StructuredModel, RelationshipId, tuple[datetime, tzinfo], Log], Awaitable[Spent]
]
type LoopSetup = Callable[[Passing, Sequence[OwnReader]], Loops | None]


class MemoryWrite(Protocol):
    """What a feature does as the pass writes a memory of theirs: `repeat` before it is stored (the
    older memory it repeats, whose evidence it becomes, or None), `stored` once it is."""

    async def repeat(
        self, store: Store, rel: RelationshipId, made: Belief, now: datetime, log: Log
    ) -> Belief | None: ...

    def stored(self, store: Store, rel: RelationshipId, made: Belief, now: datetime) -> None: ...


type WriteSetup = Callable[[Passing], MemoryWrite | None]


@dataclass(frozen=True, slots=True)
class PassParts:
    """What the features add to one memory pass, set up once from `Passing`: the open-loop reads
    (with the own-message readers riding their batch), the checks on each memory of theirs as it is
    written, and the steps after."""

    steps: tuple[Step, ...] = ()
    loops: tuple[Loops, ...] = ()
    writes: tuple[MemoryWrite, ...] = ()

    @classmethod
    def of(cls, features: Iterable[Feature], p: Passing) -> PassParts:
        features = tuple(features)
        own = [r for f in features if f.own_loop and (r := f.own_loop(p))]
        steps = [step for f in features if f.after_pass and (step := f.after_pass(p))]
        loops = [read for f in features if f.loops and (read := f.loops(p, own))]
        writes = [check for f in features if f.memory_write and (check := f.memory_write(p))]
        return cls(tuple(steps), tuple(loops), tuple(writes))


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
    """The parts a feature has, and the policy the dispatchers apply to all of them, so no hook
    checks it again: its `switch` (off leaves out its look-up, note, shadow look-up, mention, lane
    and step after the turn; the steps after a memory pass, the night, reaching and jobs keep their
    own), whether it needs a judge, and whether its step after the turn must finish before the
    reply goes out."""

    name: str  # its name in the notes' order and in the look-ups' log lines
    look: Look | None = None
    note: Note | None = None
    after_theirs: Step | None = None  # after a memory pass stored new memories of theirs
    after_own: Step | None = None  # after a memory pass stored new views of its own
    after_pass: PassStep | None = None  # after every memory pass, whatever it stored
    loops: LoopSetup | None = None  # the open-loop read of a pass, with the readers `own_loop` adds
    own_loop: OwnLoopSetup | None = None  # reads its own messages in the open-loop batch
    memory_write: WriteSetup | None = None  # as the pass writes a memory of theirs
    nightly: NightStep | None = None  # its part of the night's memory work, in registry order
    reaching: Reaching | None = None  # its steps in the initiative tick
    jobs: Jobs | None = None  # background work of its own, started with the bot
    shadow: Shadow | None = None
    after_turn: AfterTurn | None = None
    mention: Mention | None = None  # what it would bring up on its own this turn (ADR 0023)
    mention_key: str | None = None  # the decision key its brought-up offers are logged under
    lane: Lane | None = None  # what it does to the request's card (the scene card, memories hidden)
    reads: tuple[str, ...] = ()  # earlier notes its note reads by name; they must come before it
    # Its look-up gets the route's read in a scene, where the listening judge does not run.
    scene_read: bool = False
    # The longest its look-up waits on its models in all, under `LOOKS_TOGETHER_SECONDS`: one that
    # waits longer is cut off at the shared deadline, so its own limit would be dead. Checked at
    # load (`turn/notes.py`); a look-up must state it.
    look_seconds: float | None = None
    switch: Switch | None = None  # while it is off, the hooks the docstring names are left out
    # Its look-up, shadow look-up and step after the turn read a judge, and are left out of a
    # runtime that has none (a note, a mention and a lane never are).
    needs_judge: bool = False
    # Its step after the turn is waited for before the reply goes out: it writes what the next
    # message reads. Any other step runs beside the reply and never holds it up.
    must_finish: bool = False

    def live(self, c: Runtime) -> bool:
        """Whether its switch leaves it on, or it has none."""
        return self.switch is None or c.mode(self.switch) is not Mode.OFF

    def offer(self, m: Moment, found: object, so_far: Offered) -> Offer:
        """Its note's offer, none while it is switched off."""
        assert self.note is not None
        return self.note(m, found, so_far) if self.live(m.c) else Offer()

    def can_read(self, c: Runtime) -> bool:
        """Whether its look-up, shadow look-up or step after the turn runs: live, and a judge
        where it needs one."""
        return self.live(c) and not (self.needs_judge and c.judge is None)


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
    """The turn being answered, as every hook reads it: the facts about it worked out once, here.
    Built when the turn is routed and filled in as it goes (`looked` after the look-ups; `risk`,
    `beliefs` and `on_card` once the card is built), so what a hook sees depends on its stage."""

    c: Runtime
    t: Turn
    in_scene: Frame
    heard: Heard | None
    looked: Lookups = field(default_factory=Lookups)
    held: bool = False  # the floor held this turn (ADR 0017)
    beliefs: Sequence[Belief] = ()  # the memories that may be stated as true
    on_card: frozenset[BeliefId] = frozenset()  # what the card already shows this turn
    brushed: bool = False  # they pushed the flirting or the scene back (`system/brush-off`)
    risk: bool = False  # the crisis path acts on a concern or urgent reading (ADR 0022); a
    # look-up cannot see it, since the crisis look-up is one of them

    @property
    def judge(self) -> StructuredModel:
        """The judges' model, for a hook of a feature that `needs_judge`: the dispatcher leaves it
        out of a runtime with none, so there is always one."""
        if self.c.judge is None:
            msg = "a hook that needs a judge ran without one"
            raise RuntimeError(msg)
        return self.c.judge

    @property
    def severity(self) -> Severity | None:
        """What the listening judge read, None when it could not read the message."""
        return self.heard.read.severity if self.heard is not None else None

    @property
    def heavy(self) -> bool:
        """Serious or acute; an unread turn is not (it gets what an ordinary one does)."""
        return is_heavy(self.severity, unread=False)

    @property
    def unread_or_heavy(self) -> bool:
        """The turn is serious or acute, or could not be read: for what must not run on a turn that
        may be heavy."""
        return is_heavy(self.severity, unread=True)

    @property
    def sharing(self) -> bool:
        """They are telling it something, not only chatting (everyday weight or more)."""
        return self.severity is not None and self.severity >= Severity.EVERYDAY

    @property
    def pretend(self) -> bool:
        """The turn is in a pretend scene (not real)."""
        return self.in_scene is not Frame.REAL

    @property
    def casual(self) -> bool:
        """Never on a turn the crisis path reads as a risk, whatever the listening judge said."""
        return not self.risk and is_casual(self.t, self.in_scene, self.heard)
