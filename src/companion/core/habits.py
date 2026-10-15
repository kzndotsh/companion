"""A note about the companion's own recent habits, built from the ledger, never from the model.

The model sees its earlier replies and copies them: a few "Ha," openers in a row make the next one
likelier. When the last few replies share an opening word, the note says so plainly. It adds
context to the next request; it never touches a reply.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from companion.core.types import Speaker, Utterance

WINDOW = 5
STREAK = 3
_FIRST_WORD = re.compile(r"\W*(\w+)")


def opener_note(prior: Sequence[Utterance]) -> str | None:
    """The note for the next turn, or None when no opening word is overused."""
    firsts = [
        m.group(1).lower()
        for u in prior
        if u.speaker is Speaker.COMPANION and (m := _FIRST_WORD.match(u.text))
    ][-WINDOW:]
    if not firsts:
        return None
    word, n = Counter(firsts).most_common(1)[0]
    if n < STREAK:
        return None
    return (
        f'[{n} of your last {len(firsts)} replies began with "{word}". Begin this one differently.]'
    )
