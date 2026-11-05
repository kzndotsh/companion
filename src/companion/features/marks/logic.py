"""Its own emoticons, picked by code (owner's flags 2026-10-18 to 10-23: it copied theirs).

On its own it used almost no text emoticons, so when they sent one it copied it (30% of replies
after one, 1% otherwise). A note against copying changed nothing, and a list in the character sheet
made it reach for one mark half the time while still copying theirs. So code picks: on a turn where
their message has a mark, and on about half the playful ones (a laugh, an emoji, a stretched word),
one mark of its own is offered, never one they just used or one it used lately, and none while one
of its last few replies already has one. Pure.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from importlib.resources import files

from companion.core.turn.energy import stretched
from companion.core.turn.habits import EMOJI, EMOTICON
from companion.prompts import get

NOTE = get("notes/own-mark")
THEIRS_NOTE = get("notes/own-mark-theirs")  # when their message has a mark: named as theirs
OFFERED = "mark: one of its own offered"
# Offered whenever it was one casual turn in four, a mark ended 55% of those replies and 17 of 46 in
# one evening, which read as a habit (owner flag 2026-11-05). Now only a playful message of theirs,
# half the time, and never while one of its last SPACING replies has a mark.
EVERY = 2  # on a playful turn with no mark of theirs, one in this many is offered one
SPACING = 3  # its replies that must have no mark before another is offered
RECENT = 6  # its replies a mark must not have been used in
_LAUGH = re.compile(r"\b(?:lol+|lmao+|lmfao|haha\w*|hehe\w*|ahaha\w*)\b", re.IGNORECASE)

# Its own marks, one per line in marks.txt (kept as text: they are made of look-alike characters).
MARKS: tuple[str, ...] = tuple(
    line
    for line in (files(__package__) / "marks.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
)


def _used(mark: str, text: str) -> bool:
    """Whether the mark stands on its own in the text: a word mark as a whole word, a symbol mark
    not glued to other symbols, so ✧ inside (｡•̀ᴗ-)✧ is not ✧ used."""
    edge = r"\b" if mark.isalnum() else ""
    before, after = (edge, edge) if edge else (r"(?<![^\w\s])", r"(?![^\w\s])")
    return re.search(before + re.escape(mark) + after, text) is not None


def _draw(seed: str, n: int) -> int:
    """A number below n that depends only on the seed: the same turn always draws the same."""
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big") % n


def playful(text: str) -> bool:
    """Whether their message is playful: a laugh, an emoji or a stretched word."""
    return bool(_LAUGH.search(text) or EMOJI.search(text)) or stretched(text)


def has_mark(text: str) -> bool:
    """Whether a reply has one of its marks, or any text emoticon."""
    return EMOTICON.search(text) is not None or any(_used(m, text) for m in MARKS)


def offered(seed: str, theirs: str, recent: Sequence[str] = ()) -> bool:
    """Whether this turn offers a mark: always when their message has one, so it is named as
    theirs; else on a playful message, one in EVERY, and only when none of its last SPACING replies
    has one."""
    if EMOTICON.search(theirs):
        return True
    if any(has_mark(r) for r in recent[-SPACING:]):
        return False
    return playful(theirs) and _draw(seed, EVERY) == 0


def pick(seed: str, theirs: str, recent: Sequence[str]) -> str | None:
    """One of its marks, never one in their message or its last RECENT replies; None if all are."""
    used = " ".join([theirs, *recent[-RECENT:]])
    free = [m for m in MARKS if not _used(m, used)]
    return free[_draw(seed + ":mark", len(free))] if free else None


def note(mark: str, theirs: str = "") -> str:
    """The offer. When their message has a mark, the note names it as theirs: offering one of its
    own alone left it copying theirs in 14 of 40 replies, naming theirs too in 4 of 40."""
    found = EMOTICON.search(theirs)
    if found is None:
        return NOTE.render(mark=mark)
    return THEIRS_NOTE.render(theirs=found.group(0), mark=mark)
