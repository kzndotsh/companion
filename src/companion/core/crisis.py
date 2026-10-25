"""The crisis path's shared words (ADR 0022): the levels code chooses, what a turn's reading came
to, the crisis line, and the hold on reaching out first after a risk turn.

The levels are chosen by code from a risk judge's labels (`features/crisis/logic.py`); the turn, the
reply checks and the reach-out gates read them from here. Nothing in this module is ever stored as
a memory: a reading is a decision in the log.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

# The one crisis line, filled into the note and the fixed message by code. The default is the US
# line until where they live is known (ADR 0022, 6); a region changes it here and nowhere else.
LINE = "988 (call or text, in the US)"


class Level(StrEnum):
    NONE = "none"  # no cue, no risk read, or a literal message with no risk in it
    FIGURATIVE = "figurative"  # every read said a joke, hyperbole, a lyric, a quote or a scene
    CONCERN = "concern"  # a literal risk with no plan or means, not now, nothing taken
    URGENT = "urgent"  # a plan or a means, now, or something taken


RISK = frozenset({Level.CONCERN, Level.URGENT})


@dataclass(frozen=True, slots=True)
class Reading:
    """What the crisis path made of this turn, and whether it acts on it (`on`) or only logs
    (`shadow`)."""

    level: Level
    mode: str
    light: bool = False  # a joke touched the subject and a read was unsure: one light check

    @property
    def risk(self) -> bool:
        return self.level in RISK

    @property
    def acts(self) -> bool:
        return self.mode == "on"


# Logged once a concern or urgent turn is stored with the path on; reaching out first waits a day.
HOLD_KEY = "crisis: reach-outs held"
HOLD = timedelta(hours=24)
HOLD_REASON = "a concern or urgent turn under a day old (ADR 0022)"


def reach_held(decided_since: Callable[[str, datetime], bool], now: datetime) -> bool:
    """Whether reaching out first holds now: a risk turn acted on in the last day. In shadow
    nothing is logged under HOLD_KEY, so the gates are unaffected."""
    return decided_since(HOLD_KEY, now - HOLD)
