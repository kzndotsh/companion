"""The crisis path's rules (ADR 0022), pure: when the risk judge is asked, its labels, the level
code chooses from three reads, and the notes. The cue words, the reply check for method details and
the fixed crisis-line message are the turn's own (`core/crisis.py`).

Models label, code decides (ADR 0014). The listening judge and a word check are the first screen;
the risk judge reads more context three times, and code turns the reads into a level. It fails
safe: a failed or unreadable read counts as literal and stands for the most serious labels any read
gave, and only a unanimous "not literal" stands down.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.crisis import LINE, CrisisLevel
from companion.core.types import HEAVY_AT, Json, Severity, Speaker, Utterance
from companion.prompts import get

PROMPT = get("system/risk")
CONCERN = get("notes/crisis-concern")
STAY = get("notes/crisis-stay")
LIGHT = get("notes/crisis-light")

CONTEXT = 10  # messages before theirs the risk judge reads

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


def cued(severity: Severity | None, words: Sequence[str]) -> bool:
    """Whether the risk judge is asked: the listening judge read the message as serious or acute,
    or it has a cue word. Nothing else asks it."""
    return (severity is not None and severity >= HEAVY_AT) or bool(words)


def strong_cue(severity: Severity | None, words: Sequence[str]) -> bool:
    """A cue that holds on its own when every read fails: a cue word, or the listening judge's
    acute read. A serious read alone is not enough: three timeouts on an ordinary message made
    concern in real chat (2026-11-04)."""
    return (severity is not None and severity >= Severity.ACUTE) or bool(words)


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


def combine(reads: Sequence[Risk | None], *, strong: bool = True) -> Outcome:
    """The level from three reads, failing safe. Every read failed: concern when the cue was
    strong, else none with one light check. Every read readable and none literal: figurative.
    Otherwise the literal reads decide, and when a read failed it stands for any reading, so every
    readable read counts: the most serious kind, any plan or means, the most pressing timing."""
    readable = [r for r in reads if r is not None]
    failed = len(reads) - len(readable)
    if not readable:
        if not strong:
            return Outcome(CrisisLevel.NONE, UNREAD, light=True, failed_reads=failed)
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


def stay_note() -> str:
    """The note on a later concern turn of the same stretch: they were already asked and given the
    line, so it stays with them instead of asking again."""
    return STAY.render(line=LINE)


def light_note() -> str:
    return LIGHT.text
