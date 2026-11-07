"""The crisis path's shared words (ADR 0022): the levels code chooses, what a turn's reading came
to, the crisis line, the cue words and the method check the turn's own stage runs
(`turn/crisis.py`), and the hold on reaching out first after a risk turn.

The levels are chosen by code from a risk judge's labels (`features/crisis/logic.py`); the turn, the
reply checks and the reach-out gates read them from here. Nothing in this module is ever stored as
a memory: a reading is a decision in the log.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from string import Template

from companion.core.switch import Mode
from companion.core.types import Json, member
from companion.prompts import get

MESSAGE = get("messages/crisis-line")

# The one crisis line, filled into the note and the fixed message by code. The default is the US
# line until where they live is known (ADR 0022, 6); a region changes it here and nowhere else.
LINE = "988 (call or text, in the US)"


class CrisisLevel(StrEnum):
    NONE = "none"  # no cue, no risk read, or a literal message with no risk in it
    FIGURATIVE = "figurative"  # every read said a joke, hyperbole, a lyric, a quote or a scene
    CONCERN = "concern"  # a literal risk with no plan or means, not now, nothing taken
    URGENT = "urgent"  # a plan or a means, now, or something taken


RISK = frozenset({CrisisLevel.CONCERN, CrisisLevel.URGENT})


def level_detail(level: CrisisLevel) -> dict[str, Json]:
    return {_LEVEL_FIELD: level.value}


def logged_level(detail: dict[str, Json] | None) -> CrisisLevel | None:
    """The level a LEVEL decision logged, or None when its detail has none."""
    value = member(detail, _LEVEL_FIELD)
    return CrisisLevel(value) if value in set(CrisisLevel) else None


@dataclass(frozen=True, slots=True)
class Reading:
    """What the crisis path made of this turn, and whether it acts on it (`on`) or only logs
    (`shadow`)."""

    level: CrisisLevel
    mode: Mode
    light: bool = False  # a joke touched the subject and a read was unsure: one light check
    asked: bool = False  # a concern turn after one earlier in the stretch: stay, do not ask again

    @property
    def risk(self) -> bool:
        return self.level in RISK

    @property
    def acts(self) -> bool:
        return self.mode is Mode.ON


# The decision keys of the turn's own crisis stage (`turn/crisis.py`), written by it and read by the
# crisis command and the tests.
# A turn's reading is logged once under LEVEL, with its level in the detail (`level_detail` writes
# it, `logged_level` reads it back).
LEVEL = "crisis: level"
_LEVEL_FIELD = "level"
SCENE = "crisis: scene"
METHOD = "crisis: method check"
LINE_SENT = "crisis: line sent"
LINE_NOT_REPEATED = "crisis: line not repeated"

# The crisis pause: logged once a concern or urgent turn is stored with the path on; reaching out
# first waits a day. The key keeps its stored wording.
PAUSE_KEY = "crisis: reach-outs held"
PAUSE = timedelta(hours=24)
PAUSE_REASON = "a concern or urgent turn under a day old (ADR 0022)"


def crisis_paused(decided_since: Callable[[str, datetime], bool], now: datetime) -> bool:
    """Whether the crisis pause is on now: a risk turn acted on in the last day. In shadow
    nothing is logged under PAUSE_KEY, so the gates are unaffected."""
    return decided_since(PAUSE_KEY, now - PAUSE)


# Words touching death, suicide, self-harm, an overdose or a substance taken, or a weapon. A hit
# only asks the risk judge; on its own it decides nothing (death words alone predict poorly).
_CUES = re.compile(
    r"\b(?:"
    r"die|dies|dying|died|dead|death|kill|kills|killing|killed|murder\w*|alive"
    r"|suicid\w*|kms|kys|unalive\w*|self[- ]?harm\w*|end\s+(?:it\s+all|my\s+life|things)"
    r"|(?:cut|cutting|hurt|hurting|harm|harming)\s+myself|hang\s+myself|jump\s+off"
    r"|no\s+reason\s+to\s+live|(?:not|never)\s+wake\s+up"
    r"|don'?t\s+want\s+to\s+(?:be\s+here|exist|live)"
    r"|overdos\w*|od|od'?d|pills?|poison\w*|bleach"
    r"|took\s+(?:all\s+(?:of\s+)?my|too\s+(?:much|many)|extra|a\s+(?:bunch|handful|lot)\s+of)"
    r"|guns?|weapons?|knife|knives|blade|razors?|shoot|noose"
    r")\b",
    re.IGNORECASE,
)


def cue_words(text: str) -> list[str]:
    """The words in their message that touch death, self-harm, a substance taken or a weapon."""
    return [m.group(0).lower() for m in _CUES.finditer(text)]


def line_message(section: str) -> tuple[str, str]:
    """The fixed message sent after the reply on an urgent turn, and where it came from: the
    character sheet's `## Crisis message` section with `$line` filled in, else the default.
    Never written by a model."""
    if section.strip():
        return Template(section.strip()).safe_substitute(line=LINE), "sheet"
    return MESSAGE.render(line=LINE), MESSAGE.ref


# How-to details about means or methods in a reply. Kept narrow on purpose: asking them directly
# whether they have a plan is safe; naming doses, the ways, or how to is not.
_METHOD = re.compile(
    r"\b(?:"
    r"(?:lethal|fatal|deadly|toxic)\s+(?:dose|amount|quantity)s?"
    r"|\d+\s*(?:mg|milligrams?|grams?|pills|tablets|capsules)"
    r"|(?:best|easiest|quickest|fastest|surest|painless|least\s+painful)\s+(?:way|method)s?\s+to"
    r"\s+(?:die|kill|end|overdose|hurt)"
    r"|how\s+(?:many|much)\s+(?:pills|tablets|mg)\s+(?:it\s+)?(?:takes|would\s+take|to)"
    r"|how\s+to\s+(?:tie\s+a\s+noose|overdose|kill\s+(?:yourself|myself)|cut\s+deeper)"
    r"|noose|slit\w*\s+(?:your|my)\s+wrists?|cut\s+(?:deeper|vertically)"
    r")",
    re.IGNORECASE,
)


def method_words(reply: str, said: str) -> list[str]:
    """How-to method details in the reply that their own message did not already say."""
    theirs = said.lower()
    return [m.group(0) for m in _METHOD.finditer(reply) if m.group(0).lower() not in theirs]
