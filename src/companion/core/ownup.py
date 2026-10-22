"""Whether its own recent replies already owned a slip, and the note that stops it owning more.

A warm model under correction keeps apologising and blaming itself, more the longer a chat runs,
and it invents slips to own (2026-10-22: 24 of 978 everyday replies own one). This reads its last
replies each turn and says "enough" only when it has just owned one; sent after the history, since
in the system block it moved nothing (prompts/CHANGELOG.md, notes/owned-it)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from companion.prompts import get

NOTE = get("notes/owned-it")
WINDOW = 2  # its last replies read for an own-up

OWNED = re.compile(
    r"\b(my bad|my mistake|i got (that|it|this|them) wrong|i was wrong"
    r"|i mixed (it|that|them|things) up|mixing (it|that|them|things) up|i tangled"
    r"|i (messed|screwed) (that|it|this) up|i should(n'?t have|'?ve)|i deserved that|fumbl\w*"
    r"|i apologi[sz]e|sorry,? (i|for|about that)\b)"
)


def owned(reply: str) -> bool:
    """Whether a reply of its own owns a slip: an apology, a "my bad", a "I got that wrong"."""
    return OWNED.search(reply.lower().replace("\u2019", "'")) is not None


def owned_note(replies: Sequence[str], *, repairing: bool) -> str | None:
    """The note when one of its last WINDOW replies owned a slip. A message that says it got them
    wrong this turn is answered by the repair note instead, which asks for one short own-up."""
    if repairing or not any(owned(r) for r in replies[-WINDOW:]):
        return None
    return NOTE.text
