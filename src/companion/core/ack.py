"""Deciding whether a message needs a reply or only a reaction.

Two stages. A cheap code prefilter decides whether the question is worth asking: short, no
question mark, and the companion's last message did not ask anything. A small model then judges
the meaning from the last few messages. Code applies a threshold; the reason that gets logged is
rendered by code from the scores, never written by the model (ADR 0006).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Json, Speaker, Utterance

MAX_CHARS = 40
MAX_WORDS = 4
CONTEXT_MESSAGES = 4
# 0.70, not higher: on 15 hand-labelled messages the clear acknowledgements scored 0.70 to 0.90
# and the ones that needed a reply scored 0.60 or lower. Every judgement is logged to recalibrate.
REACT_THRESHOLD = 0.70
KINDS = ("ack", "answer", "emotional", "invitation", "other")
EMOJI = ("👍", "❤", "😁", "🔥", "🙏", "👌", "🤗", "🫡")


@dataclass(frozen=True, slots=True)
class Reaction:
    """Answer a message with an emoji reaction instead of text."""

    emoji: str


@dataclass(frozen=True, slots=True)
class Judgement:
    kind: str
    confidence: float
    emoji: str


SYSTEM = """You decide whether a chat message needs a reply. You see the last few messages of a \
conversation between a USER and their COMPANION, then the USER's newest message. Label the newest \
message:

- ack: it only acknowledges, agrees, thanks or signs off on what the companion just said, and adds \
nothing a reply could build on (ok, got it, thanks, lol, nice, a thumbs up).
- answer: it answers something, gives information, states a preference or a decision, even \
briefly (no, yeah, let's do it, i did).
- emotional: it carries a feeling that deserves a human reply, even if short (ugh, yeah..., \
i guess).
- invitation: it invites the companion to continue or react (so?, anyway, hmm).
- other: none of these.

Give your confidence from 0 to 1 that the label is right, and lower it when unsure. Also choose \
the emoji a friend would react with if no reply were needed: 👍 for ok or agree, ❤ for thanks \
or warmth, 😁 for laughing, 🔥 for excitement, 🙏 for gratitude, 👌 for fine, 🤗 for \
comfort, 🫡 for a sign-off."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "confidence": {"type": "number"},
        "emoji": {"type": "string", "enum": list(EMOJI)},
    },
    "required": ["kind", "confidence", "emoji"],
}


def schema_hash() -> str:
    return hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()


def inputs_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def ends_with_question(text: str) -> bool:
    return text.rstrip().endswith("?")


def is_candidate(text: str, history: Sequence[Utterance]) -> bool:
    """Worth asking the model: a short message that follows a statement, not a question."""
    if not history or history[-1].speaker is not Speaker.COMPANION:
        return False
    if ends_with_question(history[-1].text):
        return False
    if "?" in text or not text.strip() or len(text) > MAX_CHARS:
        return False
    return len(text.split()) <= MAX_WORDS


def build_prompt(history: Sequence[Utterance], text: str) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in history[-CONTEXT_MESSAGES:]
    ]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {text}"])


def parse(data: Json) -> Judgement | None:
    if not isinstance(data, dict):
        return None
    kind, conf, emoji = data.get("kind"), data.get("confidence"), data.get("emoji")
    if kind not in KINDS or emoji not in EMOJI or isinstance(conf, bool):
        return None
    if not isinstance(conf, int | float):
        return None
    return Judgement(str(kind), min(max(float(conf), 0.0), 1.0), str(emoji))


def reaction_for(j: Judgement) -> Reaction | None:
    """React only when sure it is an acknowledgement. Everything else gets a reply."""
    if j.kind == "ack" and j.confidence >= REACT_THRESHOLD:
        return Reaction(j.emoji)
    return None


def render_reason(j: Judgement, reacted: bool) -> str:
    """The logged reason, built from the scores. The model never writes it."""
    if reacted:
        return f"reacted {j.emoji} instead of replying: judged ack at {j.confidence:.2f}"
    return (
        f"replied: judged {j.kind} at {j.confidence:.2f}"
        f" (react needs ack at {REACT_THRESHOLD:.2f} or more)"
    )
