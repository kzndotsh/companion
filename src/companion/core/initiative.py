"""Whether to reach out now, and about what. Pure: the same inputs give the same answer.

Every answer carries a reason rendered here from the numbers, never written by a model (ADR 0003,
0006). Holding is a normal answer and is never counted as being ignored. This is the gate that
sits in front of any spend: nothing is drafted or sent unless it says to.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, tzinfo

from companion.core.openloops import SENSITIVE, LoopState, OpenLoop


@dataclass(frozen=True, slots=True)
class Caps:
    quiet_start: time = time(23, 0)
    quiet_end: time = time(8, 0)
    max_per_day: int = 1
    min_gap_hours: float = 20.0
    user_quiet_minutes: int = 90
    expire_days: float = 2.0
    backoff_hours: float = 72.0  # after one reach-out went unanswered
    max_unanswered: int = 2  # after this many in a row, wait for them to write first


@dataclass(frozen=True, slots=True)
class Situation:
    now: datetime
    tz: tzinfo
    last_message_at: datetime | None  # anyone's newest message
    in_scene: bool
    sent_today: int
    last_reach_out_at: datetime | None
    unanswered: int = 0  # sent reach-outs since their last message


@dataclass(frozen=True, slots=True)
class Verdict:
    send: bool
    reason: str
    loop: OpenLoop | None = None
    expired: tuple[OpenLoop, ...] = field(default_factory=tuple)


def in_quiet_hours(now: datetime, tz: tzinfo, caps: Caps) -> bool:
    t = now.astimezone(tz).time()
    if caps.quiet_start <= caps.quiet_end:
        return caps.quiet_start <= t < caps.quiet_end
    return t >= caps.quiet_start or t < caps.quiet_end


def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


def _clock(t: time) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


def evaluate(loops: Sequence[OpenLoop], sit: Situation, caps: Caps = Caps()) -> Verdict:  # noqa: B008
    """Pick the loop to ask about, or hold with the reason."""
    live = [lp for lp in loops if lp.state is LoopState.OPEN]
    horizon = timedelta(days=caps.expire_days)
    expired = tuple(lp for lp in live if sit.now > lp.follow_up_at + horizon)
    due = sorted(
        (
            lp
            for lp in live
            if lp not in expired and lp.follow_up_at <= sit.now and lp.sensitivity < SENSITIVE
        ),
        key=lambda lp: lp.follow_up_at,
    )
    if not due:
        return Verdict(False, "nothing is due", None, expired)
    pick = due[0]
    reason = _hold_reason(sit, caps)
    if reason is not None:
        return Verdict(False, reason, pick, expired)
    since = _hours(sit.now - pick.follow_up_at)
    return Verdict(True, f"due {since:.0f}h ago and nothing holds it: {pick.claim}", pick, expired)


def _hold_reason(sit: Situation, caps: Caps) -> str | None:
    """The first thing that holds a reach-out back, in order, or None."""
    gap = None if sit.last_reach_out_at is None else _hours(sit.now - sit.last_reach_out_at)
    quiet = (
        None
        if sit.last_message_at is None
        else (sit.now - sit.last_message_at).total_seconds() / 60
    )
    checks: tuple[tuple[bool, Callable[[], str]], ...] = (
        (
            in_quiet_hours(sit.now, sit.tz, caps),
            lambda: f"quiet hours, {_clock(caps.quiet_start)} to {_clock(caps.quiet_end)}",
        ),
        (sit.in_scene, lambda: "a pretend scene is in progress"),
        (
            sit.sent_today >= caps.max_per_day,
            lambda: f"already reached out today ({sit.sent_today} of {caps.max_per_day})",
        ),
        (
            sit.unanswered >= caps.max_unanswered,
            lambda: (
                f"the last {sit.unanswered} reach-outs went unanswered;"
                " waits for them to write first"
            ),
        ),
        (
            gap is not None and sit.unanswered > 0 and gap < caps.backoff_hours,
            lambda: (
                f"the last reach-out went unanswered; waits {caps.backoff_hours:.0f}h"
                f" before another ({gap or 0:.0f}h so far)"
            ),
        ),
        (
            gap is not None and gap < caps.min_gap_hours,
            lambda: (
                f"last reach-out was {gap or 0:.0f}h ago,"
                f" under the {caps.min_gap_hours:.0f}h minimum"
            ),
        ),
        (
            quiet is not None and quiet < caps.user_quiet_minutes,
            lambda: (
                f"the chat was active {quiet or 0:.0f} minutes ago, under {caps.user_quiet_minutes}"
            ),
        ),
    )
    return next((reason() for held, reason in checks if held), None)
