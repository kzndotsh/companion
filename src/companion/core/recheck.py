"""Draw one fresh reply when the first fails a check (J45, J47).

Some habits do not move with wording: a joke bolted onto an ordinary message (about 45% on real
flagged turns whatever the persona says) and an em dash the persona forbids. So after the reply is
written, cheap checks read it, and when one fails code asks the same model once more and sends the
second reply whatever it is. Nothing is edited: code only chooses which whole reply goes out
("never rewrite what the model said"), and the discarded one is kept in the decision detail.

Ordinary turns get every check. A serious turn and a scene get only the code checks: the joke judge
is for ordinary chat, while an em dash or a stock line is as wrong in a hard moment as a light one.
"""

from __future__ import annotations

import re

SERIOUS = 2
EM_DASH = "—"
DASHED = "an em dash"  # the reason a reply with one fails
QUIP = "a joke bolted onto an ordinary message"
GENERIC = "a canned generic reaction"


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


# The system block's clock line or one of its tags, copied into a reply (seen 2026-10-19:
# "[right now it is Thursday 13:11]" at the end of a reply).
_COPIED_CARD = re.compile(
    r"\bright now it is (?:mon|tues|wednes|thurs|fri|satur|sun)day\b|</?(?:clock|notes)>",
    re.IGNORECASE,
)


# A stock line: an evaluation, then ", especially when/with/the ..." or ", even when ..." ("that
# sounds exhausting, especially when ..."; flagged 2026-10-20 and 10-22). The first version caught
# only "that sounds X, especially when" (13 of 1,048 replies) and let the same move through in
# other words; this one catches 38 (3.6%), nearly all that move. "Even if" and "especially piano"
# are left.
_ESPECIALLY = re.compile(
    r",\s*(?:especially\s+(?:when|while|if|since|with|after|because|on|the|that|this|for)"
    r"|even\s+when)\b",
    re.IGNORECASE,
)


# A screenwriter's stage direction ("*a beat, and I grin*"), not how a person writes (2026-10-21).
_A_BEAT = re.compile(r"\ba beat\b(?!\s+(?:drop|to|of|from|in)\b)", re.IGNORECASE)


# Markdown that shows raw in Telegram: **bold**, or a *Title* in italics (owner flag 2026-10-21). An
# action in asterisks ("*leans in*") starts lower-case and is how a scene or a flirt is written.
_MARKDOWN = re.compile(r"\*\*[^*\n]+\*\*|(?<![\w*])\*(?!I\b)[A-Z][^*\n]{0,60}\*(?![\w*])")
MARKDOWN = "markdown that shows raw in a chat"


def code_checks(reply: str, said: str = "", *, scene: bool = False) -> list[str]:
    """The checks plain code can make, as the reasons they failed. Saying it is an AI is only a
    failure when their message did not touch on what it is: honesty when asked stays (persona).
    Markdown is only checked outside a scene."""
    failed = [DASHED] if EM_DASH in reply else []
    if _DISCLAIMER.search(reply) and not _ASKED_WHAT_IT_IS.search(said):
        failed.append("an AI disclaimer nobody asked for")
    if _COPIED_CARD.search(reply):
        failed.append("the clock line or a tag copied from the system block")
    if _ESPECIALLY.search(reply):
        failed.append("the stock 'X, especially when' line")
    if _A_BEAT.search(reply):
        failed.append("the stage direction 'a beat'")
    if not scene and _MARKDOWN.search(reply):
        failed.append(MARKDOWN)
    return failed
