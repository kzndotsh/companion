"""How they want to be referred to, pinned in every turn's card.

How someone wants to be referred to has to be used on every turn without being raised as a topic,
so it cannot compete with recent memories for a place on the card, where it can be crowded out.
They state it themselves, it is stored as a setting, and code puts it first in the card. A model
never infers it.
"""

from __future__ import annotations

import re

from companion.core.types import Belief, Subject
from companion.prompts import get

KEY = "address"
NOTE = get("notes/address")


def address_note(value: str | None) -> str | None:
    """The pinned line, or None when nothing is set."""
    text = (value or "").strip()
    return NOTE.render(address=text) if text else None


_NAMED = re.compile(
    r"\buser'?s? (?:first |real )?name is\b|\buser (?:is called|goes by|is named)\b"
    r"|\b(?:wants?|likes?|prefers?) (?:to be|being) called\b",
    re.IGNORECASE,
)


def names_them(b: Belief) -> bool:
    """Whether a belief about them says what they are called: one of the basics a scene keeps."""
    return b.subject is Subject.USER and _NAMED.search(b.claim) is not None
