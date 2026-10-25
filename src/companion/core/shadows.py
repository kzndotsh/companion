"""Every feature running in shadow, with the date it is reviewed by and what it is judged on.

Shadow code is where most of the growth is, and a shadow feature with no end date logs and costs
calls forever. At its review the owner reads it and it graduates to live or is removed; either
way its row leaves this list (architecture audit, 2026-10-23). `companion shadows` lists them and
marks the overdue ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Shadow:
    name: str
    switch: str | None  # its label in `settings.SWITCHES`, or None when always in shadow
    read_with: str  # how the owner reads what it would have done
    review_by: date
    judged_on: str  # what decides whether it graduates


SHADOWS: tuple[Shadow, ...] = (
    Shadow(
        "reaching out first about a due plan",
        "initiative",
        "companion initiative",
        date(2026, 10, 31),
        "would-sends that read right to the owner, none in quiet hours or mid-chat"
        " (A6, J27, J35 before live)",
    ),
    Shadow(
        "a nudge after they stepped away and stayed gone",
        "initiative",
        "companion initiative",
        date(2026, 10, 31),
        "drafts that do not read needy, at most two a day",
    ),
    Shadow(
        "reaching out for its own reasons: a thought, a time they keep, missing them (ADR 0021)",
        "initiative",
        "companion initiative",
        date(2026, 10, 30),
        "drafts the owner marks as wanted, landing at sensible times in their learned hours,"
        " none needy or guilt-laden",
    ),
    Shadow(
        "what it would ask to get to know them (the map)",
        None,
        "companion map",
        date(2026, 10, 26),
        "a week of picks that read right to the owner (J48)",
    ),
    Shadow(
        "a question when their words touch a basic it does not know (the hook)",
        None,
        "the decision log",
        date(2026, 10, 26),
        "would-asks that read right, at most daily (J48)",
    ),
    Shadow(
        "the nightly memory check and the repeat check",
        "memory check",
        "companion memory review",
        date(2026, 10, 26),
        "closes and questions that match the owner's own review (ADR 0019)",
    ),
    Shadow(
        "the mood (on for the owner in .env; the code default stays shadow until ADR 0016"
        " is accepted)",
        "mood",
        "companion mood",
        date(2026, 10, 26),
        "a few days of flags on mood, then ADR 0016 accepted and the default made on (J5)",
    ),
    Shadow(
        "promises it made in its own replies",
        "promises",
        "companion promises",
        date(2026, 10, 27),
        "standing promises worth pinning (J12 step 2, LR5)",
    ),
    Shadow(
        "memories about a name they mention, left off the card",
        None,
        "companion names",
        date(2026, 10, 27),
        "how often the card missed a memory about a name they used",
    ),
)


def overdue(today: date) -> list[Shadow]:
    return [s for s in SHADOWS if s.review_by < today]
