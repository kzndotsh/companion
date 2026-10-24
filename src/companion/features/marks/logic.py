"""Its own emoticons, picked by code (owner's flags 2026-10-18 to 10-23: it copied theirs).

On its own it used almost no text emoticons, so when they sent one it copied it (30% of replies
after one, 1% otherwise). A note against copying changed nothing, and a list in the character sheet
made it reach for one mark half the time while still copying theirs. So code picks: on a turn where
their message has a mark, and on about one casual turn in four, one mark of its own is offered,
never one they just used or one it used lately. Pure.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from importlib.resources import files

from companion.core.turn.habits import EMOTICON
from companion.prompts import get

NOTE = get("notes/own-mark")
OFFERED = "mark: one of its own offered"
EVERY = 4  # on a casual turn with no mark of theirs, one in this many is offered one
RECENT = 6  # its replies a mark must not have been used in

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


def offered(seed: str, theirs: str) -> bool:
    """Whether this turn offers a mark: always when their message has one, else one in EVERY."""
    return bool(EMOTICON.search(theirs)) or _draw(seed, EVERY) == 0


def pick(seed: str, theirs: str, recent: Sequence[str]) -> str | None:
    """One of its marks, never one in their message or its last RECENT replies; None if all are."""
    used = " ".join([theirs, *recent[-RECENT:]])
    free = [m for m in MARKS if not _used(m, used)]
    return free[_draw(seed + ":mark", len(free))] if free else None


def note(mark: str) -> str:
    return NOTE.render(mark=mark)
