"""How they want to be referred to, pinned in every turn's card.

How someone wants to be referred to has to be used on every turn without being raised as a topic,
so it cannot compete with recent memories for a place on the card, where it can be crowded out.
They state it themselves, it is stored as a setting, and code puts it first in the card. A model
never infers it.
"""

from __future__ import annotations

from companion.prompts import get

KEY = "address"
NOTE = get("notes/address")


def address_note(value: str | None) -> str | None:
    """The pinned line, or None when nothing is set."""
    text = (value or "").strip()
    return NOTE.render(address=text) if text else None
