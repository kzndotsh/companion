"""Which thread to reach out about now, if any. Pure: the same inputs give the same answer.

Whether anything may reach out at all is the shared gate's question (`features/reach/gate.py`,
asked by the daemon, ADR 0023): learned quiet hours, a scene, an active chat, the last one
unanswered, the gap since the last of any kind, the share dial. This picks the due thread and
reports the ones past their horizon; a hold from the shared gate holds it with that reason. Every
reason is rendered here or there from the numbers, never written by a model (ADR 0003, 0006).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, tzinfo

from companion.core.sensitivity import GUARDED_AT
from companion.features.threads.logic import (
    FOLLOW_UP_KEEPS,
    REACH_KEEPS,
    Thread,
    ThreadKind,
    ThreadState,
)


@dataclass(frozen=True, slots=True)
class Verdict:
    send: bool
    reason: str
    loop: Thread | None = None
    expired: tuple[Thread, ...] = field(default_factory=tuple)


def evaluate(
    loops: Sequence[Thread],
    now: datetime,
    tz: tzinfo,
    held: str | None,
) -> Verdict:
    """Pick the loop to ask about, or hold with the shared gate's reason."""
    live = [lp for lp in loops if lp.state is ThreadState.OPEN]
    expired = tuple(lp for lp in live if _past(lp, now, tz))
    due = sorted(
        (
            lp
            for lp in live
            if lp not in expired
            and not lp.note_only
            and lp.follow_up_at <= now
            and not _reach_over(lp, now)
            and lp.sensitivity < GUARDED_AT
        ),
        key=lambda lp: lp.follow_up_at,
    )
    if not due:
        return Verdict(False, "nothing is due", None, expired)
    pick = due[0]
    if held is not None:
        return Verdict(False, held, pick, expired)
    since = (now - pick.follow_up_at).total_seconds() / 3600
    return Verdict(True, f"due {since:.0f}h ago and nothing holds it: {pick.claim}", pick, expired)


def _reach_over(loop: Thread, now: datetime) -> bool:
    """A follow-up is reached out about for `REACH_KEEPS` after it falls due, then only the note
    brings it up. A celebration or encouragement keeps its day, as `_past` says."""
    return loop.kind is ThreadKind.FOLLOW_UP and now > loop.follow_up_at + REACH_KEEPS


def _past(loop: Thread, now: datetime, tz: tzinfo) -> bool:
    """Past its horizon: a follow-up after `FOLLOW_UP_KEEPS`; a celebration or
    encouragement once its day is over."""
    if loop.kind is ThreadKind.FOLLOW_UP:
        return now > loop.follow_up_at + FOLLOW_UP_KEEPS
    return now.astimezone(tz).date() > loop.follow_up_at.astimezone(tz).date()
