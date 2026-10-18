"""A note about the companion's own recent habits, built from the ledger, never from the model.

The model sees its earlier replies and copies them: a few "Ha," openers in a row make the next one
likelier, and so does a phrase it keeps reaching for. When the last few replies share an opening
word or a run of words, the note says so plainly. It adds context to the next request; it never
touches a reply. Nothing here knows any topic: it only counts what the replies repeat.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from companion.core.types import Speaker, Utterance
from companion.prompts import get

WINDOW = 5
STREAK = 3
PHRASE_WINDOW = 6
PHRASE_MIN_REPLIES = {5: 2, 4: 2, 3: 3}  # a longer run repeated twice is already a habit
PHRASE_LENGTHS = (5, 4, 3)
MAX_PHRASES = 3
_FIRST_WORD = re.compile(r"\W*(\w+)")
_WORD = re.compile(r"[a-z0-9']+")
# Everyday function words. A habit is a run that starts and ends on a real word.
_FUNCTION_TEXT = (
    "a an the and or but so if then than that this these those it its it's i i'm i'll "
    "i've me my mine you you're you'll you've your yours we us our they them their he she "
    "his her to of in on at by for with from as is are was were be been am do does did "
    "have has had not no yes just like what how when why who which there here too very "
    "really can could would should will about up out all any some"
)
_FUNCTION_WORDS = frozenset(_FUNCTION_TEXT.split())


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
    return get("notes/habit-opener").render(n=n, total=len(firsts), word=word)


def repeated_phrases(prior: Sequence[Utterance]) -> list[str]:
    """Runs of words that turn up in several of the last few replies, longest first."""
    replies = [_WORD.findall(u.text.lower()) for u in prior if u.speaker is Speaker.COMPANION][
        -PHRASE_WINDOW:
    ]
    found: list[tuple[int, int, str]] = []
    for n in PHRASE_LENGTHS:
        seen: Counter[tuple[str, ...]] = Counter()
        for words in replies:
            seen.update({tuple(words[i : i + n]) for i in range(len(words) - n + 1)})
        for gram, count in seen.items():
            if (
                count < PHRASE_MIN_REPLIES[n]
                or gram[0] in _FUNCTION_WORDS
                or gram[-1] in _FUNCTION_WORDS
            ):
                continue
            text = " ".join(gram)
            if any(text in longer for _, _, longer in found):
                continue
            found.append((count, n, text))
    found.sort(key=lambda f: (-f[0], -f[1], f[2]))
    return [text for _, _, text in found[:MAX_PHRASES]]


def habit_note(prior: Sequence[Utterance]) -> str | None:
    """Everything worth telling the next turn about its own recent habits, or None."""
    notes = [opener_note(prior)]
    phrases = repeated_phrases(prior)
    if phrases:
        quoted = ", ".join(f'"{p}"' for p in phrases)
        notes.append(get("notes/habit-phrases").render(phrases=quoted))
    joined = "\n".join(n for n in notes if n)
    return joined or None
