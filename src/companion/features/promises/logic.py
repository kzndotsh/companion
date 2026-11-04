"""The promises the companion made in its own replies (J12).

A repair promise ("I won't call you that again") lived only in the 40 messages in view, and the
companion broke one a few hours after making it. A small model reads the companion's own messages in
each memory batch and labels promises; code keeps one only when its quote is in that message, it was
said for real (not in a pretend scene), it is not hedged and it looks forward. Recorded in shadow:
listed for the owner, never shown to the talker.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
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
                    "checkable": {"type": "boolean"},
                },
                "required": ["message", "quote", "claim", "kind", "avoid", "checkable"],
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
    checkable: bool = False  # it names something a later reply could keep or break


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
        message, quote, claim, kind, avoid = (fields[k] for k in fields)
        if all(isinstance(v, str) for v in fields.values()):
            out.append(
                Proposed(
                    str(message).strip(),
                    str(quote).strip(),
                    str(claim).strip(),
                    str(kind).strip(),
                    str(avoid).strip(),
                    # a word to stop using is always something a reply keeps or breaks
                    checkable=item.get("checkable") is True or bool(str(avoid).strip()),
                )
            )
    return out


def agreed(reads: Sequence[list[Proposed]]) -> tuple[list[Proposed], list[Proposed]]:
    """The promises every read found (the same message, quotes that overlap), checkable only when
    every read said so, and the ones only some found. Asked once, the reader took jokes and
    compliments for promises (2026-11-03)."""
    if not reads:
        return [], []

    def same(p: Proposed, q: Proposed) -> bool:
        a, b = p.quote.lower(), q.quote.lower()
        return p.message.strip("[] ") == q.message.strip("[] ") and (a in b or b in a)

    kept: list[Proposed] = []
    disputed: list[Proposed] = []
    for p in reads[0]:
        matches = [next((q for q in r if same(p, q)), None) for r in reads[1:]]
        if all(m is not None for m in matches):
            sure = p.checkable and all(m is not None and m.checkable for m in matches)
            kept.append(replace(p, checkable=sure))
        else:
            disputed.append(p)
    return kept, disputed


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
    if not p.checkable:
        return "nothing in it a later reply could keep or break"
    at = labels.index(label)
    near = " ".join(window[x].text for x in labels[max(0, at - NEAR) : at + 1]).lower()
    if p.avoid and (len(p.avoid.split()) > MAX_AVOID_WORDS or p.avoid.lower() not in near):
        return "the word to avoid is not in the exchange"
    return Promise(
        promise_id, u.relationship_id, u.id, p.quote, p.claim, Kind(p.kind), p.avoid, u.at
    )


# The check on a reply: a small judge reads its promises, the newest messages and the reply, and
# says which promise the reply breaks, if any, and which ones they released or ran out. A code check
# on a promised word got 13 of 32 edge cases right, the judge 30 (evals/CHANGELOG.md, 2026-11-03):
# a break is the same joke in other words as often as the word itself.
CHECK = get("system/promise-check")
RECENT = 6  # the newest messages the check reads, theirs last
CHECK_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "broken": {"type": "string"},
        "released": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "string"},
    },
    "required": ["broken", "released", "why"],
}


@dataclass(frozen=True, slots=True)
class Check:
    broken: str | None  # the label of the promise the reply breaks
    released: tuple[str, ...]  # labels of promises they released or that ran out
    why: str


def read_check(data: Json) -> Check | None:
    """The check's answer as labels, or None when it does not have the shape asked for."""
    if not isinstance(data, dict):
        return None
    broken, released, why = data.get("broken"), data.get("released"), data.get("why")
    if not isinstance(broken, str) or not isinstance(released, list):
        return None
    label = broken.strip().lower()
    return Check(
        None if label in ("", "none") else label,
        tuple(r.strip().lower() for r in released if isinstance(r, str)),
        why if isinstance(why, str) else "",
    )


def check_input(
    promises: Sequence[Promise], recent: Sequence[tuple[Speaker, str]], reply: str
) -> tuple[str, dict[str, Promise]]:
    """What the check reads, and each label it is shown under."""
    labels = {f"p{n}": p for n, p in enumerate(promises, 1)}
    lines = [
        "Promises:",
        *(f'- {label}: "{p.quote}"' for label, p in labels.items()),
        "Newest messages:",
        *(f"{'them' if who is Speaker.USER else 'companion'}: {text}" for who, text in recent),
        f"Reply: {reply}",
    ]
    return "\n".join(lines), labels
