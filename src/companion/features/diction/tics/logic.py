"""Tics: what its own replies keep repeating, and the notes that tell the next reply. Built by code
from counts and from a judge's labels, never written by the model, and they never touch a reply.

Counted by code: the model sees its earlier replies and copies them. A few "Ha," openers in a row
make the next one likelier, and so does a phrase or a single word it keeps reaching for. When the
last few replies share an opening word or a run of words, the note says so plainly. Nothing here
knows any topic: it only counts what repeats.

Read by a judge: counting misses most of it (a pet name, an action in asterisks followed by a quoted
line, the same gesture in new words). A small model reads the last few replies and names what
repeats; its text is bounded in length and count, and the decision to ask is logged with the scorer,
never rendered as a reason by the model (ADR 0006)."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from companion.core.types import Frame, Json, Speaker, Utterance
from companion.prompts import get

OPENER_WINDOW = 5
STREAK = 3
PHRASE_WINDOW = 6
PHRASE_MIN_REPLIES = {5: 2, 4: 2, 3: 3}  # a longer run repeated twice is already a habit
PHRASE_LENGTHS = (5, 4, 3)
MAX_PHRASES = 3
WORD_MIN_REPLIES = 3  # a single word in this many of its last replies is a pet word
WORD_MIN_CHARS = 4
_FIRST_WORD = re.compile(r"\W*(\w+)")
# A capitalised word that does not start a sentence: a name or a title in lower-case replies.
_NAMED = re.compile(r"(?<![.!?]\s)(?<!^)(?<![.!?])\b([A-Z][\w']*)")
_PRONOUN_I = frozenset({"i", "i'm", "i'll", "i've", "i'd"})
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


def opener_note(prior: Sequence[Utterance]) -> str | None:
    """The note for the next turn, or None when no opening word is overused."""
    firsts = [
        m.group(1).lower()
        for u in prior
        if u.speaker is Speaker.COMPANION and (m := _FIRST_WORD.match(u.text))
    ][-OPENER_WINDOW:]
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


def names(texts: Sequence[str]) -> set[str]:
    """Words written as a name or a title (capitalised mid-sentence), lower-cased. A title it
    brought up and they went on talking about is the topic, not a pet word ("sing", "street" for a
    film it suggested, owner's flag of 2026-11-05)."""
    return {m.group(1).lower() for text in texts for m in _NAMED.finditer(text)} - _PRONOUN_I


def pet_words(prior: Sequence[Utterance]) -> list[str]:
    """Single words it keeps reaching for: in several of its last few replies, in none of their
    messages in view, so a topic they brought up is not counted ("tiny" in 7 of 38 replies after one
    bit, owner's flag of 2026-10-25), and never a name or a title."""
    mine = [u.text for u in prior if u.speaker is Speaker.COMPANION and u.frame is Frame.REAL][
        -PHRASE_WINDOW:
    ]
    theirs = {w for u in prior if u.speaker is Speaker.USER for w in _WORD.findall(u.text.lower())}
    named = names(mine)
    seen = Counter(w for text in mine for w in set(_WORD.findall(text.lower())))
    return sorted(
        w
        for w, n in seen.items()
        if n >= WORD_MIN_REPLIES
        and len(w) >= WORD_MIN_CHARS
        and w not in _FUNCTION_WORDS
        and w not in _EVERYDAY_WORDS
        and w not in theirs
        and w not in named
    )


def tic_note(prior: Sequence[Utterance], *, words: bool = False) -> str | None:
    """Everything worth telling the next turn about its own recent tics, or None. Single pet
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


# The judge.
WINDOW = 6
MIN_REPLIES = 4
# A habit counts only if the model says it appears in at least this many of the replies it read.
MIN_SEEN_IN = 3
MAX_HABITS = 3
MAX_HABIT_CHARS = 90
# A habit found on one turn is only used for the next two, so a stale one does not linger.
FRESH_FOR = 2

PROMPT = get("system/habits")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "habits": {
            "type": "array",
            "maxItems": MAX_HABITS,
            "items": {
                "type": "object",
                "properties": {
                    "habit": {"type": "string", "maxLength": MAX_HABIT_CHARS},
                    "replies": {"type": "integer"},
                },
                "required": ["habit", "replies"],
            },
        }
    },
    "required": ["habits"],
}


def replies_to_read(prior: Sequence[Utterance], latest: str) -> list[str]:
    """The companion's last few replies, oldest first, ending with the one just sent. None when
    there are too few to judge."""
    mine = [u.text for u in prior if u.speaker is Speaker.COMPANION][-(WINDOW - 1) :]
    replies = [*mine, latest]
    return replies if len(replies) >= MIN_REPLIES else []


def build_prompt(replies: Sequence[str]) -> str:
    return "\n".join(f"[reply {i}] {text}" for i, text in enumerate(replies, start=1))


def parse(data: Json) -> list[str] | None:
    """The habits named, cleaned and bounded, or None if the answer was malformed. A habit the
    model saw in fewer than MIN_SEEN_IN replies is dropped, so weak or invented ones never count."""
    raw = data.get("habits") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    habits: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        text, seen = item.get("habit"), item.get("replies")
        if not isinstance(text, str) or isinstance(seen, bool) or not isinstance(seen, int):
            return None
        cleaned = " ".join(text.split())[:MAX_HABIT_CHARS]
        if cleaned and seen >= MIN_SEEN_IN:
            habits.append(cleaned)
    return habits[:MAX_HABITS]


def note_for(habits: Sequence[str]) -> str | None:
    if not habits:
        return None
    return get("notes/habit-moves").render(habits="; ".join(habits))
