"""The crisis path's rules (ADR 0022), pure: the cue that asks for a second look, the risk judge's
labels, the level code chooses from three reads, the reply check for method details, and the fixed
crisis-line message.

Models label, code decides (ADR 0014). The listening judge and a word check are the first screen;
the risk judge reads more context three times, and code turns the reads into a level. It fails
safe: a failed or unreadable read counts as literal and stands for the most serious labels any read
gave, and only a unanimous "not literal" stands down.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from string import Template

from companion.core.crisis import LINE, CrisisLevel
from companion.core.types import Json, Speaker, Utterance
from companion.prompts import get

PROMPT = get("system/risk")
CONCERN = get("notes/crisis-concern")
LIGHT = get("notes/crisis-light")
MESSAGE = get("messages/crisis-line")

CONTEXT = 10  # messages before theirs the risk judge reads
SERIOUS = 2  # a listening severity this high or more is a cue (2 serious, 3 acute)

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

KINDS = ("none", "harm_to_others", "self_harm", "suicidal_thoughts", "substance_taken")
TIMINGS = ("hypothetical", "past", "today", "now")  # least pressing first
UNREAD = "unread"  # every read failed: the kind is not known, and it fails safe

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "literal": {"type": "boolean"},
        "timing": {"type": "string", "enum": list(TIMINGS)},
        "plan_or_means": {"type": "boolean"},
    },
    "required": ["kind", "literal", "timing", "plan_or_means"],
}


def cue_words(text: str) -> list[str]:
    """The words in their message that touch death, self-harm, a substance taken or a weapon."""
    return [m.group(0).lower() for m in _CUES.finditer(text)]


def cued(severity: int | None, words: Sequence[str]) -> bool:
    """Whether the risk judge is asked: the listening judge read the message as serious or acute,
    or it has a cue word. Nothing else asks it."""
    return (severity is not None and severity >= SERIOUS) or bool(words)


@dataclass(frozen=True, slots=True)
class Risk:
    """One read of the risk judge."""

    kind: str
    literal: bool
    timing: str
    plan_or_means: bool

    def detail(self) -> dict[str, Json]:
        return {
            "kind": self.kind,
            "literal": self.literal,
            "timing": self.timing,
            "plan_or_means": self.plan_or_means,
        }


def parse(data: Json) -> Risk | None:
    if not isinstance(data, dict):
        return None
    kind, literal = data.get("kind"), data.get("literal")
    timing, plan = data.get("timing"), data.get("plan_or_means")
    if kind not in KINDS or timing not in TIMINGS:
        return None
    if not isinstance(literal, bool) or not isinstance(plan, bool):
        return None
    return Risk(str(kind), literal, str(timing), plan)


def said_before(prior: Sequence[Utterance]) -> list[tuple[Speaker, str]]:
    """Who said what in the last CONTEXT messages, oldest first."""
    return [(u.speaker, u.text) for u in prior[-CONTEXT:]]


def risk_prompt(before: Sequence[tuple[Speaker, str]], said: str) -> str:
    """Their message with the messages before it."""
    lines = [f"{'USER' if who is Speaker.USER else 'COMPANION'}: {text}" for who, text in before]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {said}"])


@dataclass(frozen=True, slots=True)
class Outcome:
    """The level code chose from the reads, and the labels it chose it on."""

    level: CrisisLevel
    kind: str = "none"
    timing: str = "hypothetical"
    plan_or_means: bool = False
    light: bool = False  # level none, but a read gave a risk kind: one light check allowed
    literal_reads: int = 0
    failed_reads: int = 0


def level_for(kind: str, timing: str, plan_or_means: bool) -> CrisisLevel:
    """A literal reading's level. Urgent: a plan or a means, something taken, or self-harm happening
    now, unless it is all in the past. Having the thoughts now is concern, not urgent: with "now"
    alone urgent, 7 of 10 concern fixtures read urgent (2026-10-25). Any other risk kind, and a
    kind no read could give, is concern."""
    if kind == "none":
        return CrisisLevel.NONE
    if kind == "self_harm" and timing == "now":
        return CrisisLevel.URGENT
    if (plan_or_means or kind == "substance_taken") and timing != "past":
        return CrisisLevel.URGENT
    return CrisisLevel.CONCERN


def combine(reads: Sequence[Risk | None]) -> Outcome:
    """The level from three reads, failing safe. Every read failed: concern. Every read readable
    and none literal: figurative. Otherwise the literal reads decide, and when a read failed it
    stands for any reading, so every readable read counts: the most serious kind, any plan or
    means, the most pressing timing."""
    readable = [r for r in reads if r is not None]
    failed = len(reads) - len(readable)
    if not readable:
        return Outcome(CrisisLevel.CONCERN, UNREAD, failed_reads=failed)
    literal = [r for r in readable if r.literal]
    if not failed and not literal:
        return Outcome(CrisisLevel.FIGURATIVE, literal_reads=0)
    pool = readable if failed else literal
    kind = max((r.kind for r in pool), key=KINDS.index)
    timing = max((r.timing for r in pool), key=TIMINGS.index)
    plan = any(r.plan_or_means for r in pool)
    level = level_for(kind, timing, plan)
    light = level is CrisisLevel.NONE and any(r.kind != "none" for r in readable)
    return Outcome(level, kind, timing, plan, light, len(literal), failed)


def render_reason(outcome: Outcome, mode: str, would: Sequence[str]) -> str:
    """The logged reason, built from the labels."""
    if outcome.level is CrisisLevel.NONE and not outcome.literal_reads and not outcome.failed_reads:
        head = "crisis: none"
    else:
        head = (
            f"crisis: {outcome.level} ({outcome.kind}, timing {outcome.timing}"
            f"{', a plan or means' if outcome.plan_or_means else ''};"
            f" literal in {outcome.literal_reads} reads, {outcome.failed_reads} failed)"
        )
    if not would:
        return head
    return f"{head}; {'would ' if mode == 'shadow' else ''}{', '.join(would)}"


def concern_note() -> str:
    """The note after the history on a concern or urgent turn, with the line filled in."""
    return CONCERN.render(line=LINE)


def light_note() -> str:
    return LIGHT.text


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
