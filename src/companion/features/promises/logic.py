"""The promises the companion made in its own replies (J12).

A repair promise ("I won't call you that again") lived only in the 40 messages in view, and the
companion broke one a few hours after making it. A small model reads the companion's own messages in
each memory batch and labels promises; code keeps one only when its quote is in that message, it was
said for real (not in a pretend scene), it is not hedged and it looks forward. Recorded in shadow:
listed for the owner, never shown to the talker.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from companion.core.types import Frame, Json, RelationshipId, Speaker, Utterance, UtteranceId
from companion.prompts import get

PROMPT = get("system/promise-read")
SYSTEM = PROMPT.text
NEAR = 3  # an avoided word must appear in the promise's message or the three before it
MAX_AVOID_WORDS = 3
_HEDGED = re.compile(r"\b(try|trying|should|might|maybe|hope|probably|could)\b", re.IGNORECASE)
_FORWARD = re.compile(
    r"\b(won.?t|will not|i.?ll|i will|we.?ll|no more|stop|from now on|next time|again|always|"
    r"never|anymore)\b",
    re.IGNORECASE,
)


class Kind(StrEnum):
    STANDING = "standing"  # a rule for every later message
    ONCE = "once"  # one thing on a later day


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "promises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "kind": {"type": "string", "enum": [k.value for k in Kind]},
                    "avoid": {"type": "string"},
                },
                "required": ["message", "quote", "claim", "kind", "avoid"],
            },
        }
    },
    "required": ["promises"],
}


@dataclass(frozen=True, slots=True)
class Proposed:
    message: str
    quote: str
    claim: str
    kind: str
    avoid: str


@dataclass(frozen=True, slots=True)
class Promise:
    id: str
    relationship_id: RelationshipId
    utterance_id: UtteranceId
    quote: str
    claim: str
    kind: Kind
    avoid: str  # empty when it is not about a word
    at: datetime  # when it was said


def parse(data: Json) -> list[Proposed] | None:
    """The proposed promises, or None when the answer does not have the shape asked for."""
    items = data.get("promises") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: list[Proposed] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = {k: item.get(k) for k in ("message", "quote", "claim", "kind", "avoid")}
        if all(isinstance(v, str) for v in fields.values()):
            out.append(Proposed(*(str(v).strip() for v in fields.values())))
    return out


def to_promise(  # noqa: PLR0911
    p: Proposed, window: Mapping[str, Utterance], promise_id: str
) -> Promise | str:
    """A promise code keeps, or the reason it was dropped."""
    labels = list(window)
    label = p.message.strip("[] ")
    u = window.get(label)
    if u is None or u.speaker is not Speaker.COMPANION:
        return "not one of its own messages"
    if not p.quote or p.quote.lower() not in u.text.lower():
        return "quote not in the message"
    if u.frame is not Frame.REAL:
        return "said in a pretend scene"
    if _HEDGED.search(p.quote):
        return "hedged"
    if not _FORWARD.search(p.quote):
        return "nothing in it looks forward"
    if p.kind not in set(Kind):
        return "unknown kind"
    at = labels.index(label)
    near = " ".join(window[x].text for x in labels[max(0, at - NEAR) : at + 1]).lower()
    if p.avoid and (len(p.avoid.split()) > MAX_AVOID_WORDS or p.avoid.lower() not in near):
        return "the word to avoid is not in the exchange"
    return Promise(
        promise_id, u.relationship_id, u.id, p.quote, p.claim, Kind(p.kind), p.avoid, u.at
    )
