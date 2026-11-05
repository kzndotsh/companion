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
        date(2026, 11, 24),
        "would-sends that read right to the owner, none in quiet hours or mid-chat"
        " (A6, J27, J35 before live)",
    ),
    Shadow(
        "a nudge after they stepped away and stayed gone",
        "initiative",
        "companion initiative",
        date(2026, 11, 24),
        "drafts that do not read needy, at most two a day",
    ),
    Shadow(
        "reaching out for its own reasons: a thought, a time they keep, missing them (ADR 0021)",
        "initiative",
        "companion initiative",
        date(2026, 11, 10),
        "picks the owner marks as wanted, specific to them and not generic, landing at hours they"
        " start conversations, none needy, about the two of them, or right after a heavy chat"
        " (brainstorm and pick since 2026-11-03)",
    ),
    Shadow(
        "promises it made in its own replies, and each reply checked against them",
        "promises",
        "companion promises, the decision log (promise check)",
        date(2026, 11, 17),
        "would-redraws that read as real breaks to the owner, none on a reply that kept them,"
        " and breaks the owner flags (forgot) that the check also caught",
    ),
    Shadow(
        "how often it brings a thread up, learned from how they met the last ones (ADR 0023)",
        None,
        "the decision log (threads: how they met it, the learned pace)",
        date(2026, 11, 8),
        "whether the labels read right by eye and the pace it would have used beats the day's cap",
    ),
    Shadow(
        "what they said is coming, kept until it happens, and the note that says so (ADR 0024)",
        "now",
        "companion now",
        date(2026, 11, 8),
        "labels that read right on real messages and notes that would have stopped a time skip",
    ),
    Shadow(
        "its own history: stories of its past it made up in chat, checked against the sheet and"
        " kept as canon, and the ones it would show (ADR 0025)",
        "history",
        "companion history, the decision log",
        date(2026, 11, 9),
        "canon rulings that read right to the owner (nothing big or contradicting kept, the same"
        " story linked, not kept twice) and would-shows that fit the moment",
    ),
)


def overdue(today: date) -> list[Shadow]:
    return [s for s in SHADOWS if s.review_by < today]
