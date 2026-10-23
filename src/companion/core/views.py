"""Which of the companion's own views reach the card.

A view is a claim about itself made by the thing it describes. Left alone that is a self-confirming
mirror: whatever the model does by default, it would record, restate and then be held to. So views
are split by what they are about, and only the low-stakes kind can install itself.

- An **idea** or taste about the world (kind `preference`) can become part of the card on its own,
  once it is *settled* (expressed on two different days), and a check has found no conflict with
  what the user has said they want.
- A view about **how it treats the user** (kind `promise`) or a description **of itself** (kind
  `trait`) never installs itself. Those come from the authored core, or from the user.
- The user can always **approve** any view, and can retire any view. Approval beats the kind rule.

A view stored more firmly than it was said (every quote hedged, "probably", "maybe", the claim not)
is overstated: it never installs itself, and the owner sees the mark before approving it.

Three modes, set per relationship: `auto` (the default), `review` (only approved views), `off`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from companion.core.types import Belief, BeliefId, BeliefKind, Subject

SETTLED_DAYS = 2
MAX_VIEWS = 8
AUTO_KINDS = frozenset({BeliefKind.PREFERENCE})
# How it softens a view when it says it. A claim that keeps any of these, or "can", "may", "often"
# or "some", keeps the softness (2026-10-23: 8 of 11 hedged quotes were stored without one).
HEDGE = re.compile(
    r"\b(?:probably|maybe|might|perhaps|possibly|i guess|kind of|kinda|sort of|sometimes|usually"
    r"|mostly|not always)\b",
    re.IGNORECASE,
)
SOFT = re.compile(rf"{HEDGE.pattern}|\b(?:can|may|often|some)\b", re.IGNORECASE)


class ViewMode(StrEnum):
    AUTO = "auto"
    REVIEW = "review"
    OFF = "off"


DEFAULT_MODE = ViewMode.AUTO


def parse_mode(value: str | None) -> ViewMode:
    try:
        return ViewMode(value) if value else DEFAULT_MODE
    except ValueError:
        return DEFAULT_MODE


def is_settled(belief: Belief, days: Mapping[BeliefId, int]) -> bool:
    return (
        belief.subject is Subject.SELF
        and belief.kind is not BeliefKind.EVENT
        and days.get(belief.id, 1) >= SETTLED_DAYS
    )


def overstated(belief: Belief) -> str | None:
    """The hedge its words had and its claim lost, or None: every quote hedged, the claim not."""
    found = [HEDGE.search(e.quote) for e in belief.evidence]
    if not found or any(m is None for m in found) or SOFT.search(belief.claim):
        return None
    first = found[0]
    return first.group(0).lower() if first is not None else None


@dataclass(frozen=True, slots=True)
class Gates:
    """Why a view can or cannot install itself. Logged, so the rule can be checked against use."""

    kind_allowed: bool
    settled: bool
    checked: bool
    conflicts: bool
    hedged: bool = False  # stored more firmly than it was said

    @property
    def eligible(self) -> bool:
        return (
            self.kind_allowed
            and self.settled
            and self.checked
            and not self.conflicts
            and not self.hedged
        )


def gates(belief: Belief, days: Mapping[BeliefId, int], checks: Mapping[BeliefId, bool]) -> Gates:
    return Gates(
        kind_allowed=belief.kind in AUTO_KINDS,
        settled=is_settled(belief, days),
        checked=belief.id in checks,
        conflicts=checks.get(belief.id, False),
        hedged=overstated(belief) is not None,
    )


@dataclass(frozen=True, slots=True)
class ViewState:
    """Everything that decides which views are carried, gathered once per turn."""

    mode: ViewMode
    approved: frozenset[BeliefId]
    days: Mapping[BeliefId, int]
    checks: Mapping[BeliefId, bool]
    support: Mapping[BeliefId, datetime]


def why(belief: Belief, state: ViewState) -> str:
    if belief.id in state.approved:
        return "in the card as a view of its own that the user approved"
    n = state.days.get(belief.id, 1)
    return (
        f"in the card as a view of its own: an idea, expressed on {n} days, "
        "with no conflict with what the user asked for"
    )


def card_views(
    beliefs: Sequence[Belief], state: ViewState, limit: int = MAX_VIEWS
) -> tuple[Belief, ...]:
    """The views to carry this turn, most recently restated first. Nothing else gets through."""
    if state.mode is ViewMode.OFF:
        return ()
    auto = state.mode is ViewMode.AUTO
    chosen = [
        b
        for b in beliefs
        if b.subject is Subject.SELF
        and (b.id in state.approved or (auto and gates(b, state.days, state.checks).eligible))
    ]
    chosen.sort(key=lambda b: state.support.get(b.id, b.valid_from), reverse=True)
    return tuple(chosen[:limit])
