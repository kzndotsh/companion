"""How much energy a message is typed with: stretched words, exclamation marks, emoji and
emoticons. A pasted block (code, a table, terminal output) is not typing, and a message with a sad
or annoyed mark or word is not happy energy, so both count nothing. Counts
only; whether the energy is happy is decided elsewhere (ADR 0016 carries it over only on messages
the listening judge rated not serious)."""

from __future__ import annotations

import re

from companion.core.turn.habits import EMOJI, EMOTICON

_STRETCHED = re.compile(r"\b\w*([a-z])\1{2,}\w*\b", re.IGNORECASE)
_EXCLAIM = re.compile(r"!+")
_LOW = re.compile(
    r"(?<![\w/:])(?:[:;=][-']?[(\[/\\|]|:'\(|T_T|D:)"
    r"|[\U0001f622\U0001f61e\U0001f614\U0001f61f\U0001f621\U0001f620\U0001f480\U0001f629"
    r"\U0001f62b\U0001f623\U0001f641\u2639\U0001f616\U0001f494]"
    r"|\b(?:ugh+|sucks?|hate|awful|terrible|stressed|annoyed|exhausted)\b",
    re.IGNORECASE,
)
_PASTED_LINES = 4
_PASTED_CHARS = 400
_CAP = 2  # no single kind of mark counts more than this, so "!!!!!!!!" is not a whole mood


def texting_energy(text: str) -> int:
    """0 for a plain message, about 1 to 2 for a lively one, more for "omg YESSS!!! 😭"."""
    if text.count("\n") >= _PASTED_LINES or len(text) > _PASTED_CHARS or _LOW.search(text):
        return 0
    kinds = (
        len(_STRETCHED.findall(text)),
        len(_EXCLAIM.findall(text)),
        len(EMOJI.findall(text)),
        len(EMOTICON.findall(text)),
    )
    return sum(min(n, _CAP) for n in kinds)
