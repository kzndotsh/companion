"""Whether it may reach out now for its own reasons (ADR 0021). Pure: the same inputs give the
same answer, and the first hold that applies is the reason, rendered here from the numbers.

Kept from ADR 0015: quiet hours (now learned), a scene in progress, an active chat, the spend cap
before any paid call, and the draft last. Added: never a second while the last is unanswered, at
least six hours between its own, and the share of conversations it starts held under the dial,
which steps down one level after a reach-out answered late or briefly, until they start one.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from enum import StrEnum

from companion.core.rhythm import NEW_CONVERSATION, WINDOW, Rhythm
from companion.core.types import Json
from companion.features.reach.logic import TARGET, Dial, step_down

ACTIVE_MINUTES = 90
MIN_GAP = timedelta(hours=6)
BRIEF_WORDS = 3  # an answer this short, all told, is brief
ANSWER_SPAN = timedelta(minutes=10)  # their words in this long after the first count as the answer


class Hold(StrEnum):
    OFF = "the dial is off"
    QUIET = "quiet hours"
    SCENE = "a scene in progress"
    ACTIVE = "an active chat"
    UNANSWERED = "the last one is unanswered"
    GAP = "too soon after its last"
    SHARE = "its share is at the dial"
    CAP = "the spend cap"
    NOTHING = "nothing to reach out about"


@dataclass(frozen=True, slots=True)
class Share:
    mine: int  # conversations it started in the window, a shadow would-send counted as one
    total: int

    @property
    def value(self) -> float:
        return self.mine / self.total if self.total else 0.0


def firsts(events: Sequence[tuple[datetime, bool]], now: datetime) -> list[tuple[datetime, bool]]:
    """The first message of each conversation in the last two weeks, from (time, it was mine)."""
    seen = sorted(e for e in events if now - WINDOW <= e[0] <= now)
    return [e for i, e in enumerate(seen) if i == 0 or e[0] - seen[i - 1][0] >= NEW_CONVERSATION]


def share(events: Sequence[tuple[datetime, bool]], now: datetime) -> Share:
    """Who started each conversation in the last two weeks, a shadow would-send counted as sent."""
    started = firsts(events, now)
    return Share(sum(mine for _, mine in started), len(started))


@dataclass(frozen=True, slots=True)
class Answer:
    """How they answered its last reach-out: their first message after it, and its words."""

    after: timedelta
    words: int


def answer(last_own: datetime, theirs: Sequence[tuple[datetime, str]]) -> Answer | None:
    after = sorted(t for t in theirs if t[0] > last_own)
    if not after:
        return None
    first = after[0][0]
    words = sum(len(text.split()) for at, text in after if at - first <= ANSWER_SPAN)
    return Answer(first - last_own, words)


def pace(got: Answer | None, rhythm: Rhythm, they_started_since: bool) -> str | None:
    """Why the dial is a step lower now, or None. Lowered after an answer that came later than
    their usual pause, or was a few words, until they start a conversation themselves."""
    if got is None or they_started_since:
        return None
    hours = got.after.total_seconds() / 3600
    if hours > rhythm.pause:
        return f"its last was answered after {hours:.1f}h, past their usual {rhythm.pause:.1f}h"
    if got.words <= BRIEF_WORDS:
        return f"its last was answered in {got.words} words"
    return None


@dataclass(frozen=True, slots=True)
class Situation:
    now: datetime
    tz: tzinfo
    rhythm: Rhythm
    dial: Dial  # as set
    paced: str | None  # why it is a step lower, if it is
    last_message_at: datetime | None  # anyone's newest message
    in_scene: bool
    last_own: datetime | None  # its newest reach-out of any kind, shadow or live
    unanswered: bool  # they have not written since it
    share: Share
    capped: bool  # the daily spend cap is reached

    @property
    def effective(self) -> Dial:
        return step_down(self.dial) if self.paced else self.dial

    def detail(self) -> dict[str, Json]:
        return {
            "rhythm": self.rhythm.detail(),
            "dial": self.dial.value,
            "effective_dial": self.effective.value,
            "paced": self.paced,
            "share": f"{self.share.mine}/{self.share.total}",
            "target": round(TARGET[self.effective], 3),
        }


def hold(sit: Situation) -> tuple[Hold, str] | None:
    """The first thing that holds a reach-out back, in order, with its reason, or None."""
    now, local = sit.now, sit.now.astimezone(sit.tz)
    active = None if sit.last_message_at is None else (now - sit.last_message_at).total_seconds()
    gap = None if sit.last_own is None else now - sit.last_own
    target = TARGET[sit.effective]
    checks: tuple[tuple[bool, Hold, Callable[[], str]], ...] = (
        (sit.dial is Dial.OFF, Hold.OFF, lambda: "COMPANION_REACH is off"),
        (
            local.hour in sit.rhythm.quiet,
            Hold.QUIET,
            lambda: f"{local.hour}:00 is one of their quiet hours",
        ),
        (sit.in_scene, Hold.SCENE, lambda: "a pretend scene is in progress"),
        (
            active is not None and active < ACTIVE_MINUTES * 60,
            Hold.ACTIVE,
            lambda: f"the chat was active {(active or 0) / 60:.0f} minutes ago",
        ),
        (
            sit.unanswered,
            Hold.UNANSWERED,
            lambda: "they have not written since its last reach-out; it waits for them",
        ),
        (
            gap is not None and gap < MIN_GAP,
            Hold.GAP,
            lambda: f"its last was {(gap or MIN_GAP).total_seconds() / 3600:.1f}h ago, under 6h",
        ),
        (
            sit.effective is Dial.OFF or sit.share.value >= target,
            Hold.SHARE,
            lambda: (
                f"it started {sit.share.mine} of {sit.share.total} conversations,"
                f" at or over {sit.effective.value} ({target:.2f})"
                + (f"; dial a step down: {sit.paced}" if sit.paced else "")
            ),
        ),
        (sit.capped, Hold.CAP, lambda: "the daily spend cap is reached"),
    )
    return next(((h, why()) for held, h, why in checks if held), None)
