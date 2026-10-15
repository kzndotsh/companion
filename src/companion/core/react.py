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

from companion.core.ack import Reaction
from companion.core.types import Json

# On 24 hand-labelled messages the model scored plain ones 0.80 to 0.95 and humour 0.50 to 0.70, so
# a bar of 0.80 missed jokes that deserved a laugh. Every judgement is logged to recalibrate.
MIN_CONFIDENCE = 0.65
# At least this many of the user's messages since the last reaction, so a reaction is occasional.
MIN_GAP = 3
TONES = ("funny", "sweet", "impressive", "exciting", "sad", "plain")
EMOJI = ("😁", "🤣", "❤", "🥰", "😍", "🔥", "🤯", "👏", "🎉", "🤗", "😢", "💯", "👀")

SYSTEM = """You decide whether a friend would put an emoji reaction on a chat message, on top \
of replying to it. You see the last few messages of a conversation between a USER and their \
COMPANION, then the USER's newest message. Say what the newest message is like:

- funny: a joke, a silly or teasing line, something that would make a friend laugh.
- sweet: affectionate, tender, kind, flirty or complimentary toward the companion.
- impressive: good news, an achievement, something they are proud of.
- exciting: excitement, a big plan, something thrilling.
- sad: grief, fear, loneliness, bad news or anything vulnerable, where a reaction would feel \
flippant.
- plain: anything else, including questions, information, opinions, requests and ordinary talk.

Most messages are plain. Pick plain unless the tone is obvious. Give your confidence from 0 to 1 \
that the tone is right. Also choose the emoji a friend would react with: 😁 or 🤣 for funny, ❤ 🥰 \
or 😍 for sweet, 👏 🎉 or 💯 for impressive, 🔥 or 🤯 for exciting, 🤗 or 😢 for sad, 👀 for \
something intriguing."""

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
class Judgement:
    tone: str
    confidence: float
    emoji: str


@dataclass(frozen=True, slots=True)
class Decision:
    reaction: Reaction | None
    reason: str


def parse(data: Json) -> Judgement | None:
    if not isinstance(data, dict):
        return None
    tone, conf, emoji = data.get("tone"), data.get("confidence"), data.get("emoji")
    if tone not in TONES or emoji not in EMOJI or isinstance(conf, bool):
        return None
    if not isinstance(conf, int | float):
        return None
    return Judgement(str(tone), min(max(float(conf), 0.0), 1.0), str(emoji))


def decide(j: Judgement, since_last: int | None) -> Decision:
    """React alongside the reply only when the tone is clear, sure, and not soon after the last."""
    if j.tone == "plain":
        return Decision(None, f"no reaction: judged plain at {j.confidence:.2f}")
    if j.tone == "sad":
        return Decision(None, f"no reaction: judged sad at {j.confidence:.2f}, too heavy for one")
    if j.confidence < MIN_CONFIDENCE:
        return Decision(
            None,
            f"no reaction: judged {j.tone} at {j.confidence:.2f} (needs {MIN_CONFIDENCE:.2f})",
        )
    if since_last is not None and since_last < MIN_GAP:
        return Decision(
            None,
            f"no reaction: judged {j.tone} at {j.confidence:.2f}, but the last reaction was "
            f"{since_last} messages ago (needs {MIN_GAP})",
        )
    return Decision(
        Reaction(j.emoji),
        f"reacted {j.emoji} alongside the reply: judged {j.tone} at {j.confidence:.2f}",
    )
