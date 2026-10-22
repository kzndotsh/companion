"""The times they spent together (J12): the conversation cut into stretches, each with the facts
code can work out and one line about it.

Facts about them are memories and their plans are open loops; what the two of them did together had
no record, so the morning after a long pretend scene "still drained from last night" meant nothing.
A stretch ends at a gap of GAP or more, or where the talk turns from everyday to a pretend scene (or
back) for at least SWITCH messages. Code works out when, how long, how much was a scene, the most
serious moment and the firsts; a small model only writes the line, never the facts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from companion.core.types import Frame, Json, Speaker, TurnId, Utterance
from companion.prompts import get

PROMPT = get("system/episode-gist")
GAP = timedelta(hours=2)
SWITCH = 20  # a change of frame starts a new stretch only when it lasts this many messages
SERIOUS = 2
LINES = 40  # messages shown to the writer: the start and the end of a long stretch
CUT = 220  # characters kept of each message

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"gist": {"type": "string"}},
    "required": ["gist"],
}


class Kind(StrEnum):
    EVERYDAY = "everyday"
    SCENE = "scene"
    HEAVY = "heavy"


@dataclass(frozen=True, slots=True)
class Stretch:
    said: tuple[Utterance, ...]

    @property
    def scene_share(self) -> float:
        return sum(u.frame is Frame.PLAY for u in self.said) / len(self.said)


def _scene(u: Utterance) -> bool:
    return u.frame is Frame.PLAY


def stretches(said: Sequence[Utterance]) -> list[Stretch]:
    """The conversation cut at gaps, then where it turns into or out of a scene for long enough."""
    by_gap: list[list[Utterance]] = []
    for u in said:
        if by_gap and u.at - by_gap[-1][-1].at < GAP:
            by_gap[-1].append(u)
        else:
            by_gap.append([u])
    return [Stretch(tuple(run)) for part in by_gap for run in _by_frame(part)]


def _by_frame(part: list[Utterance]) -> list[list[Utterance]]:
    """Runs of scene and everyday messages, a run shorter than SWITCH folded into the one before
    it (or after it, at the start), then neighbours of the same kind joined."""
    runs: list[list[Utterance]] = []
    for u in part:
        if runs and _scene(runs[-1][-1]) == _scene(u):
            runs[-1].append(u)
        else:
            runs.append([u])
    kept: list[list[Utterance]] = []
    for run in runs:
        if kept and (len(run) < SWITCH or len(kept[-1]) < SWITCH):
            kept[-1].extend(run)
        else:
            kept.append(run)
    joined: list[list[Utterance]] = []
    for run in kept:
        if joined and _majority(joined[-1]) == _majority(run):
            joined[-1].extend(run)
        else:
            joined.append(run)
    return joined


def _majority(run: list[Utterance]) -> bool:
    return 2 * sum(_scene(u) for u in run) >= len(run)


def kind(s: Stretch, severity: Mapping[TurnId, int]) -> Kind:
    if top_severity(s, severity) >= SERIOUS:
        return Kind.HEAVY
    return Kind.SCENE if s.scene_share >= 0.5 else Kind.EVERYDAY


def top_severity(s: Stretch, severity: Mapping[TurnId, int]) -> int:
    return max((severity.get(u.turn_id, 0) for u in s.said if u.speaker is Speaker.USER), default=0)


def firsts(found: Kind, seen: set[Kind]) -> list[str]:
    """What this stretch is the first of, given the kinds already seen."""
    names = {Kind.SCENE: "first pretend scene", Kind.HEAVY: "first heavy talk"}
    return [names[found]] if found in names and found not in seen else []


def transcript(s: Stretch) -> str:
    """The stretch as the writer sees it: all of a short one, the start and end of a long one."""
    said = list(s.said)
    if len(said) > LINES:
        head = LINES // 3
        said = [*said[:head], *said[-(LINES - head) :]]
    lines = [
        f"{'USER' if u.speaker is Speaker.USER else 'COMPANION'}"
        f"{' (pretend)' if u.frame is Frame.PLAY else ''}: {' '.join(u.text.split())[:CUT]}"
        for u in said
    ]
    return "\n".join(lines)


def facts(s: Stretch, found: Kind) -> str:
    minutes = int((s.said[-1].at - s.said[0].at).total_seconds() // 60)
    return (
        f"Length: {minutes} minutes, {len(s.said)} messages."
        f" Kind: {found.value}, {s.scene_share:.0%} pretend."
    )


MAX_WORDS = 35  # a longer line is not a summary; it is not stored


def parse(data: Json) -> str | None:
    raw = data.get("gist") if isinstance(data, dict) else None
    if not isinstance(raw, str) or not raw.strip() or len(raw.split()) > MAX_WORDS:
        return None
    return " ".join(raw.split())
