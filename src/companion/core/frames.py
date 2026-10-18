"""Which frame a message is in: real, play, story, hypothetical, or out of character.

A frame is set on every utterance when it is stored. Utterances never change after that, and the
belief rules already refuse a sincere fact from a play, story or hypothetical frame, so getting the
frame right at the door is what keeps pretend out of what the companion believes about a person.

"Play" means pretend or fiction, where what is said is not literally true or about real life. A game
of honest questions is not play: the answers are real and should be remembered. A cheap check for
cues decides whether a model is asked at all, and a scene already in progress is assumed to
continue, so most messages never reach a model.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Belief, Frame, Json, Provenance, Speaker, Utterance
from companion.prompts import get

NON_REAL = frozenset({Frame.PLAY, Frame.STORY, Frame.HYPOTHETICAL})
MIN_CONFIDENCE = 0.7
CONTEXT_MESSAGES = 4

_CUES = re.compile(
    r"\b(pretend\w*|imagine|role-?\s?play\w*|let'?s play|play a game|play along|what if"
    r"|what would you do if|act as|in this scene|story)\b|\*[^*\n]{2,}\*",
    re.IGNORECASE,
)

PROMPT = get("system/frames")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "frame": {"type": "string", "enum": [f.value for f in Frame]},
        "confidence": {"type": "number"},
    },
    "required": ["frame", "confidence"],
}


@dataclass(frozen=True, slots=True)
class Judgement:
    frame: Frame
    confidence: float


def has_cue(text: str) -> bool:
    return _CUES.search(text) is not None


def scene_frame(history: Sequence[Utterance]) -> Frame:
    """The frame the conversation was in at the user's last message. Out of character ends it."""
    for u in reversed(history):
        if u.speaker is Speaker.USER:
            return u.frame if u.frame in NON_REAL else Frame.REAL
    return Frame.REAL


def needs_judge(text: str, history: Sequence[Utterance]) -> bool:
    return has_cue(text) or scene_frame(history) is not Frame.REAL


def companion_frame(user_frame: Frame) -> Frame:
    """The companion plays along inside a scene. Stepping out, or real talk, is real."""
    return user_frame if user_frame in NON_REAL else Frame.REAL


_SCENE_NOTES = {
    Frame.PLAY: get("notes/scene-play"),
    Frame.STORY: get("notes/scene-story"),
    Frame.HYPOTHETICAL: get("notes/scene-hypothetical"),
}


def scene_note(frame: Frame) -> str | None:
    """A line for the reply when the last turn was inside a scene. It does not wait for a judge."""
    note = _SCENE_NOTES.get(frame)
    return note.text if note else None


def build_prompt(history: Sequence[Utterance], text: str) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in history[-CONTEXT_MESSAGES:]
    ]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {text}"])


def parse(data: Json) -> Judgement | None:
    if not isinstance(data, dict):
        return None
    raw, conf = data.get("frame"), data.get("confidence")
    if not isinstance(raw, str) or isinstance(conf, bool) or not isinstance(conf, int | float):
        return None
    try:
        frame = Frame(raw)
    except ValueError:
        return None
    return Judgement(frame, min(max(float(conf), 0.0), 1.0))


def resolve(judgement: Judgement | None, fallback: Frame = Frame.REAL) -> Frame:
    """The frame to store. Unsure, missing or low confidence means the fallback."""
    if judgement is None or judgement.confidence < MIN_CONFIDENCE:
        return fallback
    return judgement.frame


def render_reason(judgement: Judgement | None, stored: Frame) -> str:
    """The logged reason, built from the scores. The model never writes it."""
    if judgement is None:
        return f"stored as {stored.value}: no judgement was made in time"
    if judgement.confidence < MIN_CONFIDENCE:
        return (
            f"stored as {stored.value}: judged {judgement.frame.value} at "
            f"{judgement.confidence:.2f}, below {MIN_CONFIDENCE:.2f}"
        )
    return f"stored as {stored.value}: judged at {judgement.confidence:.2f}"


def is_assertable(belief: Belief) -> bool:
    """Whether a belief about the user may be stated as fact.

    A belief from a play, story or hypothetical frame, or one said as a joke or in pretend, is kept
    as a record of what happened. It is never shown to the companion as something true.
    """
    return belief.frame is Frame.REAL and belief.provenance in {
        Provenance.STATED,
        Provenance.INFERRED,
        Provenance.THIRD_PARTY,
    }
