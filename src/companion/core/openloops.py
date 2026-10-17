"""Open loops: things they said about their near future that a friend would ask about later.

"Going to the vet tomorrow", "I keep putting off a haircut". Each one is recorded with the exact
words it came from and a time to follow up, and nothing is asked about before that time. The model
only labels what it read (how long the thing lasts, roughly when, how sensitive); code decides
whether to keep it and when to follow up, and drops anything minute-scale, sensitive, not said by
them for real, or not found word for word in their message.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta, tzinfo
from enum import StrEnum

from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.types import Frame, Json, RelationshipId, Speaker, Utterance, UtteranceId

SENSITIVE = 2
FOLLOW_UP_HOUR = 10
UNDATED_DAYS = 3
MAX_PAST_DAYS = 3
MAX_CLAIM_CHARS = 160
SCALES = ("minutes", "hours", "days", "unknown")
SAME_DAY_SCALES = ("minutes", "hours")
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_SAME_DAY = ("today", "tonight", "this evening", "this afternoon", "later", "now", "this morning")


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


@dataclass(frozen=True, slots=True)
class RawLoop:
    ref: str
    quote: str
    claim: str
    when: str
    scale: str
    sensitivity: int


SYSTEM = """You read a chat between a USER and their COMPANION. List the things the USER said \
about their own near future or an unresolved situation that a caring friend would plausibly ask \
about later: a plan, an appointment, a deadline, something they are waiting on, something \
they keep putting off. For each give:
- ref: the label of the USER message it came from.
- quote: an exact quote from that USER message.
- claim: the thing, in a few words.
- when: when it happens, as they said it ("tomorrow", "friday", "next week"), or an empty string.
- scale: "minutes" if it is about to happen within the hour or is a passing action (getting a \
snack, taking a shower), "hours" if it is later today, "days" if it is days or more away or an \
ongoing situation, "unknown" if you cannot tell.
- sensitivity: 0 to 3. Use 2 or 3 for health, mental health or therapy, relationships, money, \
grief, sexuality or family conflict.
Do not list general facts, preferences, passing moods or states ("busy day", "tired"), things \
about the chat itself or the COMPANION, or anything the COMPANION said. If there is nothing, \
return an empty list."""

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
                },
                "required": ["ref", "quote", "claim", "when", "scale", "sensitivity"],
            },
        }
    },
    "required": ["loops"],
}


def _raw(item: Json) -> RawLoop | None:
    if not isinstance(item, dict):
        return None
    text = {k: item.get(k) for k in ("ref", "quote", "claim", "when", "scale")}
    level = item.get("sensitivity")
    if not all(isinstance(v, str) for v in text.values()):
        return None
    if isinstance(level, bool) or not isinstance(level, int):
        return None
    return RawLoop(
        str(text["ref"]),
        str(text["quote"]),
        " ".join(str(text["claim"]).split()),
        str(text["when"]).strip().lower(),
        str(text["scale"]),
        level,
    )


def parse(data: Json) -> list[RawLoop] | None:
    """The labelled items, or None if the answer was malformed."""
    items = data.get("loops") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out = [_raw(item) for item in items]
    return None if any(r is None for r in out) else [r for r in out if r is not None]


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
    if any(w in when for w in _SAME_DAY):
        return 0
    dated = _calendar_offset(when, said)
    if dated is not None:
        return dated
    fixed = next((days for phrase, days in _FIXED_OFFSETS if phrase in when), None)
    if fixed is not None:
        return fixed
    named = [*enumerate(_WEEKDAYS), (5, "weekend")]
    return next((_days_until(i, said) for i, name in named if name in when), None)


def follow_up_time(when: str, scale: str, said_at: datetime, tz: tzinfo) -> datetime:
    """The morning after the thing happens, or a few days on when nothing says when."""
    said = said_at.astimezone(tz)
    offset = _event_offset(when, said)
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
        (raw.scale in SAME_DAY_SCALES, "minute-scale or same-day, not worth asking about later"),
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
    when = follow_up_time(raw.when, raw.scale, source.at, made.tz) if source else None
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
    )


def normalise(claim: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", claim.lower()).strip()
