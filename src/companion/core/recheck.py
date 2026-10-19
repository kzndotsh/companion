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

SERIOUS = 2
EM_DASH = "—"
QUIP = "a joke bolted onto an ordinary message"


def eligible(*, severity: int | None, in_scene: bool, reply: str) -> bool:
    """Ordinary turns the listening judge read: not serious, not a scene, not an empty reply."""
    return severity is not None and severity < SERIOUS and not in_scene and bool(reply.strip())


def code_checks(reply: str) -> list[str]:
    """The checks plain code can make, as the reasons they failed."""
    return ["an em dash in a casual reply"] if EM_DASH in reply else []
