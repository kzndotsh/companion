"""The state card: what the companion carries into every turn about the person.

Beliefs are split two ways. By sensitivity: ordinary ones are usable in conversation, sensitive ones
are held, so the companion knows them and does not ask again but does not raise them unprompted.
By freshness (see `freshness.py`): aging ones are marked as possibly changed, and stale ones leave
the main card. A few stale ordinary ones go in a separate "may be out of date" block so the
companion can check naturally. Stale sensitive ones are left out entirely.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, tzinfo

from companion.core.clock import local_zone
from companion.core.freshness import Freshness, status, when_phrase
from companion.core.quoted import wants_context
from companion.core.types import Belief, BeliefId, BeliefKind
from companion.core.vectors import Vector, dot

HOLD_AT = 2
MAX_ITEMS = 15
MAX_OLDER = 3
# A one-day moment of daily life (a spill, a meal, a long shower: an event the memory map labels
# daily life at surface depth) stops being shown a week after it was last mentioned. It stays in
# memory and the look-ups still find it; it just stops taking one of the card's places. Other
# events, such as starting a project or getting a job, are history and stay.
EVENT_SHOWN_DAYS = 7
# What they said in the last few hours goes first after their boundaries and its promises: a meal
# named three hours earlier was crowded off a full card, since events sort last (flag 2026-10-25).
RECENT = timedelta(hours=12)
RECENT_SLOTS = 8  # with 4, a busy evening's newer memories still pushed the meal off
RULES = frozenset({BeliefKind.BOUNDARY, BeliefKind.PROMISE})  # always first, whatever is recent
# With a focus, the places after their boundaries and its promises go to the memories closest to the
# moment, not to the same kinds every turn: on 150 audited turns blind judges preferred that list
# 131 to 8 (evals/CHANGELOG.md, 2026-11-02).
FOCUS_SAME = 0.90  # a memory this close to one already chosen says the same thing
FOCUS_HELD = 0.40  # a held memory only this close, and only when they are sharing
FOCUS_PERSONAL = 0.35  # a mildly personal one (sensitivity 1) only this close
KIND_ORDER = {
    kind: i
    for i, kind in enumerate(
        [
            BeliefKind.BOUNDARY,
            BeliefKind.PROMISE,
            BeliefKind.TELL,
            BeliefKind.TRAIT,
            BeliefKind.STATE,
            BeliefKind.THREAD,
            BeliefKind.PREFERENCE,
            BeliefKind.EVENT,
        ]
    )
}


@dataclass(frozen=True, slots=True)
class Aged:
    last_supported: datetime
    status: Freshness


@dataclass(frozen=True, slots=True)
class Focus:
    """How close each memory is to the moment, from the focus look-up, and the vectors that tell
    two memories that say the same thing apart."""

    closeness: Mapping[BeliefId, float]
    vectors: Mapping[BeliefId, Vector]


@dataclass(frozen=True, slots=True)
class Card:
    usable: tuple[Belief, ...]
    held: tuple[Belief, ...]
    older: tuple[Belief, ...]
    dropped: tuple[Belief, ...]
    aged: Mapping[BeliefId, Aged]
    now: datetime
    views: tuple[Belief, ...] = ()
    crowded: tuple[Belief, ...] = ()  # current, but past the card's size
    kept_back: tuple[Belief, ...] = ()  # sensitive, left out on a casual turn
    contexts: Mapping[BeliefId, str] = field(default_factory=dict[BeliefId, str])  # J51

    @property
    def empty(self) -> bool:
        return not (self.usable or self.held or self.older or self.views)


def build_card(  # noqa: PLR0913
    beliefs: Sequence[Belief],
    support: Mapping[BeliefId, datetime],
    now: datetime,
    max_items: int = MAX_ITEMS,
    views: Sequence[Belief] = (),
    *,
    show_held: bool = True,
    everyday: Collection[BeliefId] = (),
    contexts: Mapping[BeliefId, str] | None = None,
    focus: Focus | None = None,
) -> Card:
    """`support` is each belief's freshest evidence time, falling back to valid_from.

    With `show_held` off (a casual turn) sensitive beliefs are left out entirely and their places go
    to ordinary ones: in view, a model links them to unrelated banter and raises them unasked.
    With a `focus` the rest of the card is the memories closest to the moment, not the newest of
    each kind (`_focused`)."""
    aged = {
        b.id: Aged(
            (last := support.get(b.id, b.valid_from)),
            status(b.kind, last, now),
        )
        for b in beliefs
    }
    faded = [
        b
        for b in beliefs
        if (b.id in everyday and _faded(b, aged[b.id].last_supported, now))
        or _dated_past(b, aged[b.id].last_supported, now)
        or day_over(b, now)
    ]
    current = [b for b in beliefs if aged[b.id].status is not Freshness.STALE and b not in faded]
    kept_back = [] if show_held else [b for b in current if b.sensitivity >= HOLD_AT]
    current = [b for b in current if b not in kept_back]
    stale = sorted(
        (b for b in beliefs if aged[b.id].status is Freshness.STALE),
        key=lambda b: -aged[b.id].last_supported.timestamp(),
    )
    by_kind = sorted(
        current, key=lambda b: (KIND_ORDER[b.kind], -aged[b.id].last_supported.timestamp())
    )
    rules = [b for b in by_kind if b.kind in RULES]
    newest = sorted(current, key=lambda b: -aged[b.id].last_supported.timestamp())
    recent = [b for b in newest if b not in rules and now - aged[b.id].last_supported <= RECENT][
        :RECENT_SLOTS
    ]
    if focus is None:
        ordered = [*rules, *recent, *(b for b in by_kind if b not in rules and b not in recent)]
        ranked, crowded = ordered[:max_items], ordered[max_items:]
    else:  # a place nothing close enough fills stays empty
        rest = [b for b in current if b not in rules]
        room = max_items - len(rules)
        ranked = [*rules, *_focused(rest, focus, room, sharing=show_held)][:max_items]
        crowded = [b for b in by_kind if b not in ranked]
    older_pool = [b for b in stale if b.sensitivity < HOLD_AT]
    older = tuple(older_pool[:MAX_OLDER])
    return Card(
        usable=tuple(b for b in ranked if b.sensitivity < HOLD_AT),
        held=tuple(b for b in ranked if b.sensitivity >= HOLD_AT),
        older=older,
        dropped=tuple(b for b in [*stale, *faded] if b not in older),
        aged=aged,
        now=now,
        views=tuple(views),
        crowded=tuple(crowded),
        kept_back=tuple(kept_back),
        contexts={k: v for k, v in (contexts or {}).items() if k in aged},
    )


def _focused(beliefs: Sequence[Belief], focus: Focus, room: int, *, sharing: bool) -> list[Belief]:
    """The closest memories first, at most `room`: a held one only when they are sharing and it is
    close, a mildly personal one only when it is close, and none that says what one already chosen
    says. A memory with no vector is not ranked."""
    chosen: list[Belief] = []
    for b in sorted(
        (b for b in beliefs if b.id in focus.closeness and b.id in focus.vectors),
        key=lambda b: -focus.closeness[b.id],
    ):
        if len(chosen) >= room:
            break
        near = focus.closeness[b.id]
        if b.sensitivity >= HOLD_AT and (not sharing or near < FOCUS_HELD):
            continue
        if b.sensitivity == 1 and near < FOCUS_PERSONAL:
            continue
        if any(dot(focus.vectors[b.id], focus.vectors[x.id]) > FOCUS_SAME for x in chosen):
            continue
        chosen.append(b)
    return chosen


_ON_A_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def _dated_past(b: Belief, last: datetime, now: datetime) -> bool:
    """A personal happening on a given day ("On 2026-10-21 they had an appointment"), past its week
    on the card. It stays in memory, and the look-ups still find it. Events told without a date are
    their history, and an ordinary dated one (a project started) is a milestone; both stay."""
    return (
        b.kind is BeliefKind.EVENT
        and b.sensitivity >= 1
        and _ON_A_DATE.search(b.claim) is not None
        and now - last > timedelta(days=EVENT_SHOWN_DAYS)
    )


# A plan, a state or a moment bound to one day: "plans to apply to jobs that day", "had just woken
# up on", "expects it back on". Shown as current days later, it read as still true (2026-11-02).
_ONE_DAY = re.compile(
    r"\b(that day|the same day|today|tonight|that night|had just|just woke|about to|planned to"
    r"|plans to|expects?|expecting|wanted to be reminded)\b",
    re.IGNORECASE,
)
DAY_GRACE = 1  # shown on its day and the day after ("last night you said"), then left off


def day_over(b: Belief, now: datetime) -> bool:
    """A memory bound to the days it names, once the last of them is more than `DAY_GRACE` days
    past in the local zone. It stays in memory; only the card leaves it off. Rules never end so."""
    if b.kind in RULES or not _ONE_DAY.search(b.claim):
        return False
    named = [date.fromisoformat(d) for d in _ON_A_DATE.findall(b.claim)]
    return bool(named) and (now.astimezone(local_zone()).date() - max(named)).days > DAY_GRACE


def faded(b: Belief, last: datetime, now: datetime) -> bool:
    """Whether a memory labelled a one-day moment of daily life is past its week on the card."""
    return _faded(b, last, now)


def _faded(b: Belief, last: datetime, now: datetime) -> bool:
    return (
        b.kind is BeliefKind.EVENT
        and b.sensitivity == 0
        and now - last > timedelta(days=EVENT_SHOWN_DAYS)
    )


def _line(b: Belief, card: Card) -> str:
    a = card.aged[b.id]
    when = when_phrase(a.last_supported, card.now)
    note = "; may have changed" if a.status is Freshness.AGING else ""
    said = card.contexts.get(b.id) if wants_context(b) else None
    about = f"; said {said}" if said else ""
    return f"- {b.claim} (mentioned {when}{about}{note})"


def render(card: Card, tz: tzinfo = UTC) -> str:
    """Plain text for the volatile part of the user message. Empty when there is nothing.

    `tz` is kept so callers need not change; ages are relative, so no zone is needed to print them.
    """
    del tz
    parts: list[str] = []
    if card.usable:
        parts.append(
            "[What you remember about them. Use it naturally, never recite it:\n"
            + "\n".join(_line(b, card) for b in card.usable)
            + "]"
        )
    if card.held:
        parts.append(
            "[Also known, but only touch it if they bring it up:\n"
            + "\n".join(_line(b, card) for b in card.held)
            + "]"
        )
    if card.older:
        parts.append(
            "[Older, and may be out of date. Do not assume these still hold. If it comes up, "
            "check lightly:\n" + "\n".join(_line(b, card) for b in card.older) + "]"
        )
    if card.views:
        parts.append(
            "[Views of your own that you have expressed. Hold to them "
            "unless they give you a real reason to change your mind. If you do change your mind, "
            "say so plainly:\n" + "\n".join(f"- {b.claim}" for b in card.views) + "]"
        )
    return "\n".join(parts)


# How a stored card is read back: the user's memory blocks and one memory per line.
_LINE = re.compile(r"^- (.+?)(?: \(mentioned [^)]*\))?$")
_USER_BLOCKS = ("[What you remember", "[Also known", "[Older")


def memories_from_card(card: str) -> list[str]:
    """The memories about the user that a stored card held, without the companion's own views."""
    out: list[str] = []
    keep = False
    for line in card.splitlines():
        if line.startswith("["):
            keep = line.startswith(_USER_BLOCKS)
            continue
        m = _LINE.match(line.rstrip("]"))
        if keep and m:
            out.append(m.group(1))
    return out
