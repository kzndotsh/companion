"""The two reaction judges' pure parts: what each reads, its schema, and the rule code applies to
its scores.

The instead judge decides a reaction in place of a reply. A cheap code prefilter decides whether the
question is worth asking: short, no question mark, no stretched word, the companion's last message
did not ask anything, and their message before this one was not judged serious (a bare "thanks"
after something heavy deserves words, not an emoji). A small model then judges the meaning from the
last few messages. Code applies a threshold.

The alongside judge decides a reaction as well as a reply, the way a friend might heart a sweet
message and then answer it. A small model says what the message feels like and which emoji fits.
Code decides whether to react: the tone must be clear, the model confident, and the last reaction
not too recent, so a reaction stays occasional and keeps meaning something.

The reason that gets logged is rendered by code from the scores, never written by the model
(ADR 0006).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.turn.energy import stretched
from companion.core.turn.reply import Reaction
from companion.core.types import Json, Speaker, Utterance, unit_interval
from companion.prompts import get

MAX_CHARS = 40
MAX_WORDS = 4
# 0.70, not higher: on 15 hand-labelled messages the clear acknowledgements scored 0.70 to 0.90
# and the ones that needed a reply scored 0.60 or lower. Every judgement is logged to recalibrate.
INSTEAD_THRESHOLD = 0.70
KINDS = ("ack", "answer", "emotional", "invitation", "other")
INSTEAD_EMOJI = ("👍", "❤", "😘", "🥹", "😁", "💀", "😭", "🔥", "🙏", "👌", "🤗", "🫡")

# On 24 hand-labelled messages the model scored plain ones 0.80 to 0.95 and humour 0.50 to 0.70, so
# a bar of 0.80 missed jokes that deserved a laugh. Every judgement is logged to recalibrate.
MIN_CONFIDENCE = 0.65
# At least this many of the user's messages since the last reaction, so a reaction is occasional.
MIN_GAP = 3
TONES = ("funny", "sweet", "impressive", "exciting", "sad", "plain")
ALONGSIDE_EMOJI = (
    "😁",
    "🤣",
    "💀",
    "😭",
    "🤪",
    "😅",
    "❤",
    "🥰",
    "😍",
    "🥹",
    "🥺",
    "😘",
    "🫠",
    "😇",
    "😈",
    "🥵",
    "😜",
    "🫣",
    "👏",
    "🎉",
    "💯",
    "😎",
    "🔥",
    "🤯",
    "🥳",
    "🤗",
    "😢",
    "👀",
)

INSTEAD_PROMPT = get("system/ack")
INSTEAD_SYSTEM = INSTEAD_PROMPT.text
ALONGSIDE_PROMPT = get("system/react")
ALONGSIDE_SYSTEM = ALONGSIDE_PROMPT.text

INSTEAD_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "confidence": {"type": "number"},
        "emoji": {"type": "string", "enum": list(INSTEAD_EMOJI)},
    },
    "required": ["kind", "confidence", "emoji"],
}
ALONGSIDE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "tone": {"type": "string", "enum": list(TONES)},
        "confidence": {"type": "number"},
        "emoji": {"type": "string", "enum": list(ALONGSIDE_EMOJI)},
    },
    "required": ["tone", "confidence", "emoji"],
}


@dataclass(frozen=True, slots=True)
class InsteadRead:
    kind: str
    confidence: float
    emoji: str


@dataclass(frozen=True, slots=True)
class ToneRead:
    tone: str
    confidence: float
    emoji: str


@dataclass(frozen=True, slots=True)
class ReactionPick:
    reaction: Reaction | None
    reason: str


def ends_with_question(text: str) -> bool:
    return text.rstrip().endswith("?")


def is_candidate(text: str, history: Sequence[Utterance], *, after_serious: bool = False) -> bool:
    """Worth asking the instead judge: a short message that follows a statement, not a question,
    not a stretched word, and not right after a serious message of theirs."""
    if after_serious or not history or history[-1].speaker is not Speaker.COMPANION:
        return False
    if ends_with_question(history[-1].text):
        return False
    if "?" in text or not text.strip() or len(text) > MAX_CHARS or stretched(text):
        return False
    return len(text.split()) <= MAX_WORDS


def parse_instead(data: Json) -> InsteadRead | None:
    if not isinstance(data, dict):
        return None
    kind, conf, emoji = data.get("kind"), data.get("confidence"), data.get("emoji")
    confidence = unit_interval(conf)
    if kind not in KINDS or emoji not in INSTEAD_EMOJI or confidence is None:
        return None
    return InsteadRead(str(kind), confidence, str(emoji))


def reaction_instead(j: InsteadRead) -> Reaction | None:
    """React only when sure it is an acknowledgement. Everything else gets a reply."""
    if j.kind == "ack" and j.confidence >= INSTEAD_THRESHOLD:
        return Reaction(j.emoji)
    return None


def render_reason(j: InsteadRead, reacted: bool) -> str:
    """The logged reason, built from the scores. The model never writes it."""
    if reacted:
        return f"reacted {j.emoji} instead of replying: judged ack at {j.confidence:.2f}"
    return (
        f"replied: judged {j.kind} at {j.confidence:.2f}"
        f" (react needs ack at {INSTEAD_THRESHOLD:.2f} or more)"
    )


def parse_tone(data: Json) -> ToneRead | None:
    if not isinstance(data, dict):
        return None
    tone, conf, emoji = data.get("tone"), data.get("confidence"), data.get("emoji")
    confidence = unit_interval(conf)
    if tone not in TONES or emoji not in ALONGSIDE_EMOJI or confidence is None:
        return None
    return ToneRead(str(tone), confidence, str(emoji))


def reaction_alongside(j: ToneRead, since_last: int | None) -> ReactionPick:
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
