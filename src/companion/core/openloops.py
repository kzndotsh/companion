"""Open loops: things they said about their near future that a friend would ask about later.

"Going to the vet tomorrow", "I keep putting off a haircut". Each one is recorded with the exact
words it came from and a time to follow up, and nothing is asked about before that time. The model
only labels what it read (how long the thing lasts, roughly when, how sensitive); code decides
whether to keep it and when to follow up, and drops anything minute-scale, sensitive, not said by
them for real, or not found word for word in their message.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta, tzinfo
from enum import StrEnum

from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.types import Frame, Json, RelationshipId, Speaker, Utterance, UtteranceId
from companion.prompts import get

SENSITIVE = 2
FOLLOW_UP_HOUR = 10
CELEBRATE_TIME = time(10)
ENCOURAGE_TIME = time(8, 30)  # just after quiet hours, before most things start
UNDATED_DAYS = 3
MAX_PAST_DAYS = 3
MAX_CLAIM_CHARS = 160
SCALES = ("minutes", "hours", "days", "unknown")
SAME_DAY_SCALES = ("minutes", "hours")
NOTE_DELAY = timedelta(hours=3)  # a same-day plan is asked about when they write a few hours on
NOTE_KEEPS = timedelta(days=3)  # a follow-up note is offered for this long after it falls due
MAX_OFFERS = 2  # offered as a note at most twice, then let go
CERTAINTIES = ("firm", "maybe", "wish")
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# Whole words only: "now" must not match "know" or "snow", and "later this week" is not today.
_SAME_DAY = re.compile(
    r"\b(?:today|tonight|this evening|this afternoon|this morning|now"
    r"|later(?! (?:this|next|in) ))\b"
)


class LoopKind(StrEnum):
    """What the thing is, which decides when and how to reach out."""

    FOLLOW_UP = "follow_up"  # asked about the morning after: how did it go
    CELEBRATE = "celebrate"  # marked on the day: happy birthday
    ENCOURAGE = "encourage"  # a word the morning of: cheering them on


class LoopState(StrEnum):
    OPEN = "open"
    ASKED = "asked"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    DROPPED = "dropped"


@dataclass(frozen=True, slots=True)
class OpenLoop:
    id: str
    relationship_id: RelationshipId
    claim: str
    quote: str
    source_utterance_id: UtteranceId
    follow_up_at: datetime
    sensitivity: int
    created_at: datetime
    state: LoopState = LoopState.OPEN
    kind: LoopKind = LoopKind.FOLLOW_UP
    note_only: bool = False  # same-day: only ever a note when they next write, never a reach-out


@dataclass(frozen=True, slots=True)
class RawLoop:
    ref: str
    quote: str
    claim: str
    when: str
    scale: str
    sensitivity: int
    certainty: str = "firm"
    about_companion: bool = False
    kind: str = LoopKind.FOLLOW_UP


@dataclass(frozen=True, slots=True)
class RawResolution:
    loop: str  # the label the prompt gave the open loop, "L1"
    ref: str
    quote: str


PROMPT = get("system/openloops")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "loops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "when": {"type": "string"},
                    "scale": {"type": "string", "enum": list(SCALES)},
                    "sensitivity": {"type": "integer"},
                    "certainty": {"type": "string", "enum": list(CERTAINTIES)},
                    "about_companion": {"type": "boolean"},
                    "kind": {"type": "string", "enum": [k.value for k in LoopKind]},
                },
                "required": [
                    "ref",
                    "quote",
                    "claim",
                    "when",
                    "scale",
                    "sensitivity",
                    "certainty",
                    "about_companion",
                    "kind",
                ],
            },
        },
        "resolved": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "loop": {"type": "string"},
                    "ref": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["loop", "ref", "quote"],
            },
        },
    },
    "required": ["loops", "resolved"],
}


def _raw(item: Json) -> RawLoop | None:
    if not isinstance(item, dict):
        return None
    keys = ("ref", "quote", "claim", "when", "scale", "certainty", "kind")
    text = {k: item.get(k) for k in keys}
    level, about = item.get("sensitivity"), item.get("about_companion")
    if not all(isinstance(v, str) for v in text.values()):
        return None
    if isinstance(level, bool) or not isinstance(level, int) or not isinstance(about, bool):
        return None
    return RawLoop(
        str(text["ref"]),
        str(text["quote"]),
        " ".join(str(text["claim"]).split()),
        str(text["when"]).strip().lower(),
        str(text["scale"]),
        level,
        str(text["certainty"]).strip().lower(),
        about,
        str(text["kind"]).strip().lower(),
    )


def parse(data: Json) -> list[RawLoop] | None:
    """The labelled items, or None if the answer was malformed."""
    items = data.get("loops") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out = [_raw(item) for item in items]
    return None if any(r is None for r in out) else [r for r in out if r is not None]


def parse_resolved(data: Json) -> list[RawResolution]:
    """The loops their new messages settle. Malformed items are skipped: a missed resolution only
    means the loop stays open, and the gate still never asks before its time."""
    items = data.get("resolved") if isinstance(data, dict) else None
    out: list[RawResolution] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        loop, ref, quote = item.get("loop"), item.get("ref"), item.get("quote")
        if isinstance(loop, str) and isinstance(ref, str) and isinstance(quote, str):
            out.append(RawResolution(loop.strip(), ref.strip(), quote))
    return out


def loop_labels(loops: Sequence[OpenLoop]) -> dict[str, OpenLoop]:
    """Short labels for the loops still waiting, so the model can point at one."""
    waiting = [lp for lp in loops if lp.state in {LoopState.OPEN, LoopState.ASKED}]
    return {f"L{i}": lp for i, lp in enumerate(waiting, start=1)}


def render_open_loops(labels: Mapping[str, OpenLoop]) -> str:
    """The section of the prompt that lists the loops still waiting."""
    if not labels:
        return ""
    lines = [f"[{label}] {lp.claim} (they said: {lp.quote!r})" for label, lp in labels.items()]
    return "\n".join(["", "Open loops:", *lines])


def to_resolution(
    raw: RawResolution, labels: Mapping[str, OpenLoop], index: Mapping[str, Utterance]
) -> tuple[OpenLoop, str] | str:
    """The loop to close and the quote that settles it, or the reason it must not be closed."""
    loop = labels.get(raw.loop)
    if loop is None:
        return f"no open loop labelled {raw.loop!r}"
    source = index.get(raw.ref)
    if source is None or source.speaker is not Speaker.USER or source.frame is not Frame.REAL:
        return "not settled by something they said for real"
    if not _holds(source, raw.quote):
        return "the quote is not in their message"
    return loop, evidence_from(source, raw.quote).quote


def _days_until(weekday: int, said: datetime) -> int:
    ahead = (weekday - said.weekday()) % 7
    return ahead or 7


_FIXED_OFFSETS = (("tomorrow", 1), ("next week", 7), ("next month", 30))
_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_DATE = re.compile(
    r"\b(" + "|".join(m[:3] for m in _MONTHS) + r")[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b"
)


def _calendar_offset(when: str, said: datetime) -> int | None:
    """Days until a date written out ("december 4th"), the next time it comes round."""
    m = _DATE.search(when)
    if m is None:
        return None
    month = next(i for i, name in enumerate(_MONTHS, start=1) if name.startswith(m.group(1)))
    try:
        date = said.date().replace(month=month, day=int(m.group(2)))
    except ValueError:
        return None
    if date < said.date():
        date = date.replace(year=date.year + 1)
    return (date - said.date()).days


def _event_offset(when: str, said: datetime) -> int | None:
    """How many days after they spoke the thing happens, or None when `when` does not say."""
    if _SAME_DAY.search(when):
        return 0
    dated = _calendar_offset(when, said)
    if dated is not None:
        return dated
    fixed = next((days for phrase, days in _FIXED_OFFSETS if phrase in when), None)
    if fixed is not None:
        return fixed
    named = [*enumerate(_WEEKDAYS), (5, "weekend")]
    return next((_days_until(i, said) for i, name in named if name in when), None)


def follow_up_time(
    when: str, scale: str, said_at: datetime, tz: tzinfo, kind: str = LoopKind.FOLLOW_UP
) -> datetime | None:
    """When to reach out. A follow-up is the morning after the thing happens, or a few days on when
    nothing says when. A celebration is the morning of the day and encouragement early that morning;
    both need a day after today, so None when there is none."""
    said = said_at.astimezone(tz)
    offset = _event_offset(when, said)
    if kind in {LoopKind.CELEBRATE, LoopKind.ENCOURAGE}:
        if not offset:
            return None
        at = CELEBRATE_TIME if kind == LoopKind.CELEBRATE else ENCOURAGE_TIME
        return datetime.combine(said.date() + timedelta(days=offset), at, tzinfo=tz)
    if offset is None:
        offset = 0 if scale == "hours" else UNDATED_DAYS - 1
    day = said.date() + timedelta(days=offset + 1)
    return datetime.combine(day, time(FOLLOW_UP_HOUR), tzinfo=tz)


def _source(raw: RawLoop, index: Mapping[str, Utterance]) -> Utterance | None:
    cited = index.get(raw.ref)
    if cited is not None:
        return cited
    holders = [u for u in index.values() if u.speaker is Speaker.USER and _holds(u, raw.quote)]
    return holders[0] if len(holders) == 1 else None


def _holds(u: Utterance, quote: str) -> bool:
    try:
        evidence_from(u, quote)
    except QuoteNotFoundError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class Making:
    """What a loop is made with: whose, when now is, their zone, and where ids come from."""

    rel: RelationshipId
    now: datetime
    tz: tzinfo
    new_id: Callable[[], str]


def _why_not(
    raw: RawLoop, source: Utterance | None, when: datetime | None, now: datetime
) -> str | None:
    checks = (
        (
            source is None,
            "cited message not found and no single message of theirs holds the quote",
        ),
        (
            source is not None
            and (source.speaker is not Speaker.USER or source.frame is not Frame.REAL),
            "not something they said for real",
        ),
        (source is not None and not _holds(source, raw.quote), "the quote is not in their message"),
        (raw.scale == "minutes", "minute-scale, not worth asking about later"),
        (raw.about_companion, "about the companion or this chat, not their life"),
        (raw.certainty != "firm", f"not a firm plan ({raw.certainty}), a friend would not ask"),
        (raw.kind not in set(LoopKind), f"unknown kind {raw.kind!r}"),
        (
            source is not None and when is None,
            "a celebration or encouragement needs a day after today to land on",
        ),
        (raw.sensitivity >= SENSITIVE, "sensitive, never raised on its own"),
        (not raw.claim or len(raw.claim) > MAX_CLAIM_CHARS, "no usable claim"),
        (
            when is not None and when < now - timedelta(days=MAX_PAST_DAYS),
            "the follow-up time had already passed days ago",
        ),
    )
    return next((message for failed, message in checks if failed), None)


def to_loop(raw: RawLoop, index: Mapping[str, Utterance], made: Making) -> OpenLoop | str:
    """The loop to record, or the reason it must not be."""
    source = _source(raw, index)
    same_day = raw.scale in SAME_DAY_SCALES
    if source is None:
        when = None
    elif same_day:
        when = source.at + NOTE_DELAY
    else:
        when = follow_up_time(raw.when, raw.scale, source.at, made.tz, raw.kind)
    problem = _why_not(raw, source, when, made.now)
    if problem is not None or source is None or when is None:
        return problem or "no source"
    return OpenLoop(
        id=made.new_id(),
        relationship_id=made.rel,
        claim=raw.claim,
        quote=evidence_from(source, raw.quote).quote,
        source_utterance_id=source.id,
        follow_up_at=when,
        sensitivity=max(raw.sensitivity, 0),
        created_at=made.now,
        kind=LoopKind.FOLLOW_UP if same_day else LoopKind(raw.kind),
        note_only=same_day,
    )


_KIND_ORDER = {LoopKind.CELEBRATE: 0, LoopKind.ENCOURAGE: 1, LoopKind.FOLLOW_UP: 2}


def _note_due(loop: OpenLoop, now: datetime, tz: tzinfo) -> bool:
    """A follow-up from its time for a few days; a celebration or encouragement on its day only."""
    if loop.kind is LoopKind.FOLLOW_UP:
        return loop.follow_up_at <= now <= loop.follow_up_at + NOTE_KEEPS
    return loop.follow_up_at.astimezone(tz).date() == now.astimezone(tz).date()


def pick_note(
    loops: Sequence[OpenLoop], offers: Mapping[str, int], now: datetime, tz: tzinfo
) -> OpenLoop | None:
    """The one loop to bring up as a note when they write (J15), or None. Open, or already offered
    once as a note and still unsettled; never sensitive; due now. A celebration beats an
    encouragement beats a follow-up, then the most recently due."""

    def offerable(lp: OpenLoop) -> bool:
        n = offers.get(lp.id, 0)
        state_ok = lp.state is LoopState.OPEN or (lp.state is LoopState.ASKED and n > 0)
        return state_ok and n < MAX_OFFERS and lp.sensitivity < SENSITIVE and _note_due(lp, now, tz)

    due = [lp for lp in loops if offerable(lp)]
    due.sort(key=lambda lp: (_KIND_ORDER[lp.kind], -lp.follow_up_at.timestamp()))
    return due[0] if due else None


_NOTES = {
    LoopKind.FOLLOW_UP: get("notes/loop-follow-up"),
    LoopKind.CELEBRATE: get("notes/loop-celebrate"),
    LoopKind.ENCOURAGE: get("notes/loop-encourage"),
}


def loop_note(loop: OpenLoop) -> str:
    return _NOTES[loop.kind].render(claim=loop.claim)


def loop_note_ref(loop: OpenLoop) -> str:
    return _NOTES[loop.kind].ref


def normalise(claim: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", claim.lower()).strip()
