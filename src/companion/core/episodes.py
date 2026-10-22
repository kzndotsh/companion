"""The times they spent together (J12): the conversation cut into stretches, each with the facts
code can work out and one line about it.

Facts about them are memories and their plans are open loops; what the two of them did together had
no record, so the morning after a long pretend scene "still drained from last night" meant nothing.
A stretch ends at a gap of GAP or more, or where the talk turns from everyday to a pretend scene (or
back) for at least SWITCH messages. Code works out when, how long, how much was a scene, the most
serious moment and the firsts; a small model only writes the line, never the facts.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum

from companion.core.types import Frame, Json, Speaker, TurnId, Utterance
from companion.prompts import get

PROMPT = get("system/episode-gist")
GAP = timedelta(hours=2)
SWITCH = 20  # a change of frame starts a new stretch only when it lasts this many messages
SERIOUS = 2
LINES = 40  # messages shown to the writer: the start and the end of a long stretch
CUT = 220  # characters kept of each message

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"gist": {"type": "string"}},
    "required": ["gist"],
}


class Kind(StrEnum):
    EVERYDAY = "everyday"
    SCENE = "scene"
    HEAVY = "heavy"


@dataclass(frozen=True, slots=True)
class Stretch:
    said: tuple[Utterance, ...]

    @property
    def scene_share(self) -> float:
        return sum(u.frame is Frame.PLAY for u in self.said) / len(self.said)


def _scene(u: Utterance) -> bool:
    return u.frame is Frame.PLAY


def stretches(said: Sequence[Utterance]) -> list[Stretch]:
    """The conversation cut at gaps, then where it turns into or out of a scene for long enough."""
    by_gap: list[list[Utterance]] = []
    for u in said:
        if by_gap and u.at - by_gap[-1][-1].at < GAP:
            by_gap[-1].append(u)
        else:
            by_gap.append([u])
    return [Stretch(tuple(run)) for part in by_gap for run in _by_frame(part)]


def _by_frame(part: list[Utterance]) -> list[list[Utterance]]:
    """Runs of scene and everyday messages, a run shorter than SWITCH folded into the one before
    it (or after it, at the start), then neighbours of the same kind joined."""
    runs: list[list[Utterance]] = []
    for u in part:
        if runs and _scene(runs[-1][-1]) == _scene(u):
            runs[-1].append(u)
        else:
            runs.append([u])
    kept: list[list[Utterance]] = []
    for run in runs:
        if kept and (len(run) < SWITCH or len(kept[-1]) < SWITCH):
            kept[-1].extend(run)
        else:
            kept.append(run)
    joined: list[list[Utterance]] = []
    for run in kept:
        if joined and _majority(joined[-1]) == _majority(run):
            joined[-1].extend(run)
        else:
            joined.append(run)
    return joined


def _majority(run: list[Utterance]) -> bool:
    return 2 * sum(_scene(u) for u in run) >= len(run)


def kind(s: Stretch, severity: Mapping[TurnId, int]) -> Kind:
    if top_severity(s, severity) >= SERIOUS:
        return Kind.HEAVY
    return Kind.SCENE if s.scene_share >= 0.5 else Kind.EVERYDAY


def top_severity(s: Stretch, severity: Mapping[TurnId, int]) -> int:
    return max((severity.get(u.turn_id, 0) for u in s.said if u.speaker is Speaker.USER), default=0)


def firsts(found: Kind, seen: set[Kind]) -> list[str]:
    """What this stretch is the first of, given the kinds already seen."""
    names = {Kind.SCENE: "first pretend scene", Kind.HEAVY: "first heavy talk"}
    return [names[found]] if found in names and found not in seen else []


def transcript(s: Stretch) -> str:
    """The stretch as the writer sees it: all of a short one, the start and end of a long one."""
    said = list(s.said)
    if len(said) > LINES:
        head = LINES // 3
        said = [*said[:head], *said[-(LINES - head) :]]
    lines = [
        f"{'USER' if u.speaker is Speaker.USER else 'COMPANION'}"
        f"{' (pretend)' if u.frame is Frame.PLAY else ''}: {' '.join(u.text.split())[:CUT]}"
        for u in said
    ]
    return "\n".join(lines)


def facts(s: Stretch, found: Kind) -> str:
    minutes = int((s.said[-1].at - s.said[0].at).total_seconds() // 60)
    return (
        f"Length: {minutes} minutes, {len(s.said)} messages."
        f" Kind: {found.value}, {s.scene_share:.0%} pretend."
    )


MAX_WORDS = 35  # a longer line is not a summary; it is not stored


def parse(data: Json) -> str | None:
    raw = data.get("gist") if isinstance(data, dict) else None
    if not isinstance(raw, str) or not raw.strip() or len(raw.split()) > MAX_WORDS:
        return None
    return " ".join(raw.split())


# When their message points at a time, the stretch of the clock it means. Before MORNING, "today"
# still means the day that is ending and "last night" means this night.
MORNING = 7
_LAST_NIGHT = re.compile(r"\blast night\b|\bthis night\b", re.IGNORECASE)
_YESTERDAY = re.compile(r"\byesterday\b", re.IGNORECASE)
_TODAY = re.compile(
    r"\btoday\b|\bthis morning\b|\bearlier\b|\btonight\b|\b(long|intense|rough|good|crazy|weird|"
    r"busy|hard|great|wild) day\b|\bwhat a day\b",
    re.IGNORECASE,
)


def period(said: str, now: datetime, tz: tzinfo) -> tuple[datetime, datetime] | None:
    """The span of time their words point at, or None."""
    local = now.astimezone(tz)
    day = local.date() if local.hour >= MORNING else local.date() - timedelta(days=1)
    start = datetime.combine(day, time(MORNING), tzinfo=tz)
    if _LAST_NIGHT.search(said):
        night = start if local.hour < MORNING else start - timedelta(days=1)
        return night + timedelta(hours=11), night + timedelta(days=1)  # 18:00 to 07:00
    if _YESTERDAY.search(said):
        return start - timedelta(days=1), start
    if _TODAY.search(said):
        return start, now
    return None


def when_said(end: datetime, now: datetime, tz: tzinfo) -> str:
    """How long ago a stretch was, the way a person says it. A day runs from MORNING to MORNING, so
    at 3 a.m. the evening just gone is still tonight."""
    e, n = end.astimezone(tz), now.astimezone(tz)

    def day_of(t: datetime) -> date:
        return t.date() if t.hour >= MORNING else t.date() - timedelta(days=1)

    evening = e.hour >= 18 or e.hour < MORNING
    days = (day_of(n) - day_of(e)).days
    if days == 0:
        return "earlier tonight" if evening else "earlier today"
    if days == 1:
        return "last night" if evening else "yesterday"
    return f"on {e:%A}"


GAP_BACK = timedelta(hours=3)  # back after this long: one line about the last time
SHOWN = 3
NOTE = get("notes/recent-times")


@dataclass(frozen=True, slots=True)
class Told:
    """A recorded stretch as the talker is shown it."""

    when: str
    gist: str


def recent(
    ends: Sequence[tuple[datetime, datetime, str]],
    said: str,
    last_theirs: datetime | None,
    now: datetime,
    tz: tzinfo,
) -> list[Told]:
    """Which recorded stretches (start, end, line) to show on this turn: those in the time their
    words point at, else the last one when they come back after GAP_BACK; none otherwise."""
    done = [e for e in ends if e[1] < now]
    span = period(said, now, tz)
    if span is not None:
        picked = [e for e in done if e[1] > span[0] and e[0] < span[1]][-SHOWN:]
    elif last_theirs is not None and now - last_theirs >= GAP_BACK and done:
        picked = done[-1:]
    else:
        picked = []
    return [Told(when_said(end, now, tz), line) for _, end, line in picked]


def note(told: Sequence[Told]) -> str | None:
    if not told:
        return None
    return NOTE.render(items="\n".join(f"- {t.when}: {t.gist}" for t in told))
