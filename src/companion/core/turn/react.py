"""Reacting to a message and replying to it too.

The ack judge handles the case where a reaction replaces a reply. This is the other case: a message
that deserves a reply and also a reaction, the way a friend might heart a sweet message and then
answer it. A small model says what the message feels like and which emoji fits. Code decides
whether to react: the tone must be clear, the model confident, and the last reaction not too
recent, so a reaction stays occasional and keeps meaning something. The logged reason is rendered
by code from the scores, never written by the model (ADR 0006).
"""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.turn.ack import Reaction
from companion.core.types import Json
from companion.prompts import get

# On 24 hand-labelled messages the model scored plain ones 0.80 to 0.95 and humour 0.50 to 0.70, so
# a bar of 0.80 missed jokes that deserved a laugh. Every judgement is logged to recalibrate.
MIN_CONFIDENCE = 0.65
# At least this many of the user's messages since the last reaction, so a reaction is occasional.
MIN_GAP = 3
TONES = ("funny", "sweet", "impressive", "exciting", "sad", "plain")
EMOJI = ("😁", "🤣", "❤", "🥰", "😍", "🔥", "🤯", "👏", "🎉", "🤗", "😢", "💯", "👀")

PROMPT = get("system/react")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "tone": {"type": "string", "enum": list(TONES)},
        "confidence": {"type": "number"},
        "emoji": {"type": "string", "enum": list(EMOJI)},
    },
    "required": ["tone", "confidence", "emoji"],
}


@dataclass(frozen=True, slots=True)
class ToneRead:
    tone: str
    confidence: float
    emoji: str


@dataclass(frozen=True, slots=True)
class ReactionPick:
    reaction: Reaction | None
    reason: str


def parse(data: Json) -> ToneRead | None:
    if not isinstance(data, dict):
        return None
    tone, conf, emoji = data.get("tone"), data.get("confidence"), data.get("emoji")
    if tone not in TONES or emoji not in EMOJI or isinstance(conf, bool):
        return None
    if not isinstance(conf, int | float):
        return None
    return ToneRead(str(tone), min(max(float(conf), 0.0), 1.0), str(emoji))


def decide(j: ToneRead, since_last: int | None) -> ReactionPick:
    """React alongside the reply only when the tone is clear, sure, and not soon after the last."""
    if j.tone == "plain":
        return ReactionPick(None, f"no reaction: judged plain at {j.confidence:.2f}")
    if j.tone == "sad":
        return ReactionPick(
            None, f"no reaction: judged sad at {j.confidence:.2f}, too heavy for one"
        )
    if j.confidence < MIN_CONFIDENCE:
        return ReactionPick(
            None,
            f"no reaction: judged {j.tone} at {j.confidence:.2f} (needs {MIN_CONFIDENCE:.2f})",
        )
    if since_last is not None and since_last < MIN_GAP:
        return ReactionPick(
            None,
            f"no reaction: judged {j.tone} at {j.confidence:.2f}, but the last reaction was "
            f"{since_last} messages ago (needs {MIN_GAP})",
        )
    return ReactionPick(
        Reaction(j.emoji),
        f"reacted {j.emoji} alongside the reply: judged {j.tone} at {j.confidence:.2f}",
    )
