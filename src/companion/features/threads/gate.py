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
from datetime import datetime, timedelta, tzinfo

from companion.core.reachout import Caps
from companion.features.threads.logic import SENSITIVE, Thread, ThreadKind, ThreadState


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
    caps: Caps = Caps(),  # noqa: B008
) -> Verdict:
    """Pick the loop to ask about, or hold with the shared gate's reason."""
    live = [lp for lp in loops if lp.state is ThreadState.OPEN]
    horizon = timedelta(days=caps.expire_days)
    expired = tuple(lp for lp in live if _past(lp, now, tz, horizon))
    due = sorted(
        (
            lp
            for lp in live
            if lp not in expired
            and not lp.note_only
            and lp.follow_up_at <= now
            and lp.sensitivity < SENSITIVE
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


def _past(loop: Thread, now: datetime, tz: tzinfo, horizon: timedelta) -> bool:
    """A follow-up keeps for a couple of days; a celebration or encouragement for its day only."""
    if loop.kind is ThreadKind.FOLLOW_UP:
        return now > loop.follow_up_at + horizon
    return now.astimezone(tz).date() > loop.follow_up_at.astimezone(tz).date()
