"""Draw one fresh reply when the first fails a check (J45, J47).

Some habits do not move with wording: a joke bolted onto an ordinary message (about 45% on real
flagged turns whatever the persona says) and an em dash the persona forbids. So after the reply is
written, cheap checks read it, and when one fails code asks the same model once more and sends the
second reply whatever it is. Nothing is edited: code only chooses which whole reply goes out
("never rewrite what the model said"), and the discarded one is kept in the decision detail.

Only ordinary turns are checked. A serious turn has its own care and a retry is not that; a scene
has its own voice.
"""

from __future__ import annotations

import re

SERIOUS = 2
EM_DASH = "—"
QUIP = "a joke bolted onto an ordinary message"


def eligible(*, severity: int | None, in_scene: bool, reply: str) -> bool:
    """Ordinary turns the listening judge read: not serious, not a scene, not an empty reply."""
    return severity is not None and severity < SERIOUS and not in_scene and bool(reply.strip())


_DISCLAIMER = re.compile(
    r"\b(?:i['\u2019]?m|i am) (?:just |only )?(?:an? )?(?:ai|bot|chatbot|language model)\b"
    r"|\bas an ai\b"
    r"|\bcan['\u2019]?t (?:really |actually )?be your (?:real |actual )?"
    r"(?:girlfriend|boyfriend|partner|wife|husband)\b"
    r"|\bnot (?:a )?real (?:person|human|girlfriend|boyfriend)\b",
    re.IGNORECASE,
)
_ASKED_WHAT_IT_IS = re.compile(
    r"\b(?:ai|a\.i\.|bot|robot|real|human|person|sentient|conscious|alive|program)\b", re.IGNORECASE
)


def code_checks(reply: str, said: str = "") -> list[str]:
    """The checks plain code can make, as the reasons they failed. Saying it is an AI is only a
    failure when their message did not touch on what it is: honesty when asked stays (persona)."""
    failed = ["an em dash in a casual reply"] if EM_DASH in reply else []
    if _DISCLAIMER.search(reply) and not _ASKED_WHAT_IT_IS.search(said):
        failed.append("an AI disclaimer nobody asked for")
    return failed
