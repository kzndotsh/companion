"""Sending one reply as two or three messages, the way people text.

The model writes one reply and the ledger keeps it as one reply, so what it reads next turn is
never its own splitting habit. Only the delivery is cut, at sentence boundaries, so no sentence is
broken and no word changes. Whether to split and where are decided from two random numbers the io
layer supplies, which keeps this function pure and the test exact. A fixed rule would be as
mechanical as no rule, so only some eligible replies are split.
"""

from __future__ import annotations

import itertools
import re

MIN_WORDS = 25
THREE_PART_WORDS = 60
SPLIT_CHANCE = 0.65
MIN_PART_WORDS = 3
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_ACTION = re.compile(r"\*[^*\n]{2,}\*")
_LIST_LINE = re.compile(r"^\s*(?:[-•]|\d+[.)])\s", re.MULTILINE)
_SPEECH = re.compile(r"[\"“”]")  # quoted speech: roleplay, which reads wrong cut apart


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(text.strip()) if s]


def eligible(text: str) -> bool:
    """Long enough, more than one sentence, and plain: no paragraphs, lists, asterisk actions or
    quoted speech."""
    if "\n" in text or _ACTION.search(text) or _LIST_LINE.search(text) or _SPEECH.search(text):
        return False
    return len(text.split()) >= MIN_WORDS and len(sentences(text)) >= 2


def _words(sentence: str) -> int:
    return len(sentence.split())


def _boundaries(parts: list[str]) -> list[int]:
    """Indexes i where the reply may be cut between sentence i-1 and sentence i. Never right after
    a question, so a question is never left hanging at the end of a message that is not the last,
    and never leaving fewer than MIN_PART_WORDS on either side."""
    total = sum(_words(s) for s in parts)
    out: list[int] = []
    before = 0
    for i in range(1, len(parts)):
        before += _words(parts[i - 1])
        if parts[i - 1].rstrip().endswith("?"):
            continue
        if before >= MIN_PART_WORDS and total - before >= MIN_PART_WORDS:
            out.append(i)
    return out


def _closest(candidates: list[int], target: float, parts: list[str], pick: float) -> int:
    """The candidate cut nearest a target word count, chosen among the two nearest by `pick`."""
    running = [0]
    for s in parts:
        running.append(running[-1] + _words(s))
    ranked = sorted(candidates, key=lambda i: abs(running[i] - target))
    return ranked[min(int(pick * 2), len(ranked) - 1)]


def split_reply(text: str, roll: float, pick: float) -> list[str]:
    """The reply as the messages to send, in order. One message unless it is eligible and `roll`
    (0 to 1) falls under SPLIT_CHANCE. `pick` (0 to 1) varies which boundary is used."""
    if not eligible(text) or roll >= SPLIT_CHANCE:
        return [text]
    parts = sentences(text)
    cuts = _boundaries(parts)
    if not cuts:
        return [text]
    total = sum(_words(s) for s in parts)
    chosen = [_closest(cuts, total / 2, parts, pick)]
    if total >= THREE_PART_WORDS and len(parts) >= 3:
        left = [c for c in cuts if c < chosen[0]]
        right = [c for c in cuts if c > chosen[0]]
        if left and right:
            first = _closest(left, total / 3, parts, pick)
            second = _closest(right, 2 * total / 3, parts, pick)
            chosen = [first, second]
    chosen.sort()
    bounds = [0, *chosen, len(parts)]
    return [" ".join(parts[a:b]) for a, b in itertools.pairwise(bounds)]
