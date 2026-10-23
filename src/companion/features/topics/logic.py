"""Moving on when a small topic has run its course (owner flag 2026-10-19).

A topic kept alive only by minimal replies ("honey mustard", "hehe true") is withering, and people
end it by starting a new one, usually linked to the old (conversation analysis calls it topic
attrition; a bridging line is how people most often change topic). The companion instead kept
asking about smaller details of the same thing. The listening judge labels the moment; code decides
whether to act and what to move on to, and says so in one line.
"""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.types import Json, Speaker, Utterance
from companion.prompts import Prompt, get

JUDGE = get("system/topic-spent")
SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"spent": {"type": "boolean"}},
    "required": ["spent"],
}
SHORT_WORDS = 5
CONTEXT = 8
NOTE = get("notes/topic-spent")
MOVES = {
    "loop": get("notes/topic-move-loop"),
    "day": get("notes/topic-move-day"),
    "evening": get("notes/topic-move-evening"),
    "night": get("notes/topic-move-night"),
}
EVERY_TURNS = 10  # at most once in this many of their messages
SPENT = "topic: run its course, moving on"
DAY_FROM, EVENING_FROM, NIGHT_FROM, NIGHT_UNTIL = 5, 17, 22, 5


def likely(prior: Sequence[Utterance], said: str) -> bool:
    """Whether to ask the judge at all: a short answer with no question of theirs, right after the
    companion asked something. Most turns are not, and make no call."""
    replies = [u.text for u in prior if u.speaker is Speaker.COMPANION]
    return (
        len(said.split()) <= SHORT_WORDS
        and "?" not in said
        and bool(replies)
        and "?" in replies[-1]
    )


def judge_prompt(prior: Sequence[Utterance], said: str) -> str:
    lines = [
        f"[{'USER' if u.speaker is Speaker.USER else 'COMPANION'}] {u.text}"
        for u in prior[-CONTEXT:]
    ]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {said}"])


def parse(data: Json) -> bool:
    return isinstance(data, dict) and data.get("spent") is True


def move_for(local_hour: int, *, loop_offered: bool) -> Prompt:
    """What to move on to: a plan of theirs offered this turn, else their day or evening by the
    clock, and late at night something of its own rather than another question."""
    if loop_offered:
        return MOVES["loop"]
    if local_hour >= NIGHT_FROM or local_hour < NIGHT_UNTIL:
        return MOVES["night"]
    return MOVES["evening"] if local_hour >= EVENING_FROM else MOVES["day"]


def topic_note(
    *, spent: bool, casual: bool, moved_recently: bool, local_hour: int, loop_offered: bool
) -> tuple[str, Prompt] | None:
    """The note and the move it names, or None: only on a casual turn, not twice close together."""
    if not spent or not casual or moved_recently:
        return None
    move = move_for(local_hour, loop_offered=loop_offered)
    return NOTE.render(move=move.text), move
