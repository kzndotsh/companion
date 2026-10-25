"""Notes about what the next reply is likely to copy, built by code, never by the model.

The model sees its earlier replies and copies them: a few "Ha," openers in a row make the next one
likelier, and so does a phrase it keeps reaching for. When the last few replies share an opening
word or a run of words, the note says so plainly. It also copies their message back: after a
message with an emoji the reply used the same one 22 times in 49, and after an emoticon 14 times in
36, while it almost never copied a laugh or a stretched word (owner's flag of 2026-10-18), so a
message with one gets the echo note. Notes add context to the next request; they never touch a
reply. Nothing here knows any topic: it only counts what repeats.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from companion.core.types import Frame, Speaker, Utterance
from companion.prompts import get

WINDOW = 5
STREAK = 3
PHRASE_WINDOW = 6
PHRASE_MIN_REPLIES = {5: 2, 4: 2, 3: 3}  # a longer run repeated twice is already a habit
PHRASE_LENGTHS = (5, 4, 3)
MAX_PHRASES = 3
WORD_MIN_REPLIES = 3  # a single word in this many of its last replies is a pet word
WORD_MIN_CHARS = 4
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
# Everyday words any reply may use often; a pet word is a less common one it keeps reaching for.
_EVERYDAY_TEXT = (
    "little still down right want don't around back know think good okay yeah maybe more much "
    "even only again also gonna kind sounds sound make made feel feels sure well something "
    "thing things time today tonight night day kinda pretty probably actually honestly lol "
    "haha love nice cute fun better best every ever never always going come came look looks "
    "said says tell take keep need being doing getting where then over into through after "
    "before while still that's what's there's can't didn't won't i'd you'd we're they're"
)
_EVERYDAY_WORDS = frozenset(_EVERYDAY_TEXT.split())
EMOTICON = re.compile(
    r"(?<![\w/:])(?:[:;=][-']?[)(DPpOo3*/\\|\]\[]|\^[_.]?\^|[xX][Dd]\b|<3|T_T|uwu|owo|>_<|-_-)"
)
EMOJI = re.compile("[\U0001f000-\U0001faff\u2600-\u27bf\u2764\u2b50]")
_ECHO_NOTE = get("notes/habit-echo")


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


def pet_words(prior: Sequence[Utterance]) -> list[str]:
    """Single words it keeps reaching for: in several of its last few replies and in none of
    their messages in view, so a topic they brought up is not counted ("tiny" in 7 of 38 replies
    after one bit, owner's flag of 2026-10-25)."""
    mine = [u.text for u in prior if u.speaker is Speaker.COMPANION and u.frame is Frame.REAL][
        -PHRASE_WINDOW:
    ]
    theirs = {w for u in prior if u.speaker is Speaker.USER for w in _WORD.findall(u.text.lower())}
    seen = Counter(w for text in mine for w in set(_WORD.findall(text.lower())))
    return sorted(
        w
        for w, n in seen.items()
        if n >= WORD_MIN_REPLIES
        and len(w) >= WORD_MIN_CHARS
        and w not in _FUNCTION_WORDS
        and w not in _EVERYDAY_WORDS
        and w not in theirs
    )


def habit_note(prior: Sequence[Utterance], *, words: bool = False) -> str | None:
    """Everything worth telling the next turn about its own recent habits, or None. Single pet
    words are counted only when `words` is set (a casual turn): in intimate talk and scenes the
    same body words recur by nature."""
    notes = [opener_note(prior)]
    runs = repeated_phrases(prior)
    pets = [w for w in pet_words(prior) if not any(w in r for r in runs)] if words else []
    phrases = [*runs, *pets][:MAX_PHRASES]
    if phrases:
        quoted = ", ".join(f'"{p}"' for p in phrases)
        notes.append(get("notes/habit-phrases").render(phrases=quoted))
    joined = "\n".join(n for n in notes if n)
    return joined or None


def has_marks(text: str) -> bool:
    """Whether a message has an emoji or a text emoticon in it."""
    return bool(EMOTICON.search(text) or EMOJI.search(text))


def echo_note(user_text: str) -> str | None:
    """The note for a message the reply is likely to copy a symbol from, or None. It names nothing,
    so it cannot hand the model the thing to copy."""
    return _ECHO_NOTE.text if has_marks(user_text) else None
