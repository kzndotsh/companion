"""The two question notes: one breaks a run of its own questions, one keeps a game of questions
they set up going.

The run: a question invites another. After one question reply 49% of the next ask again, after two
57%, and 11% of everyday replies follow three in a row (2026-10-24, 1,059 replies), until they asked
why it asks every turn.

The game: in a game they set up ("ask me anything", "ask something else") it answered each message
as if the talk could end there, and stopped (two flags of 2026-10-25). The note made it ask the next
question 12 times in 12 on both flagged turns, against 0 and 2 without.

Both are sent after the history, like the owned-it note (prompts/CHANGELOG.md)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime, timedelta

from companion.core.types import Speaker, Utterance
from companion.prompts import get

RUN_NOTE = get("notes/question-run")
RUN = 3  # its last replies that all asked something


def asked(reply: str) -> bool:
    """Whether a reply of its own asked them something."""
    return "?" in reply


def question_note(replies: Sequence[str]) -> str | None:
    """The note when each of its last RUN replies asked a question."""
    last = replies[-RUN:]
    if len(last) < RUN or not all(asked(r) for r in last):
        return None
    return RUN_NOTE.text


GAME_NOTE = get("notes/question-game")
GAP = timedelta(minutes=10)  # a pause this long between their messages ends the game
MESSAGES = 3  # the request must be among their last few messages, this one included
# Telling it to ask, not mentioning asking: "ask me anything", "or ask anything", "wanna ask me
# more", never "you ask questions every turn" or "I'm gonna ask something".
_ASKED = re.compile(
    r"(?:^|[.!?,;:]\s*|\b(?:or|and|so|ok|okay|now|then|wanna|want to|you can|go ahead and"
    r"|feel free to)\s+)ask\s+(?:me\s+)?(?:anything|something|another|a question|questions|more"
    r"|away|one)\b|\bkeep (?:asking|the questions)\b|\bquiz me\b|\b(?:20|twenty) questions\b",
    re.IGNORECASE,
)
_STOP = re.compile(
    r"\b(stop|enough|no more) (asking|questions|with the questions)\b|\bthat'?s enough\b",
    re.IGNORECASE,
)


def asking_game(prior: Sequence[Utterance], text: str, now: datetime) -> bool:
    """Whether they told it to ask them things in their last few messages, with no long pause
    since and without calling it off."""
    theirs = [u for u in prior if u.speaker is Speaker.USER][-(MESSAGES - 1) :]
    said = [(u.text, u.at) for u in theirs] + [(text, now)]
    later = now
    for message, at in reversed(said):
        if later - at > GAP or _STOP.search(message):
            return False
        if _ASKED.search(message):
            return True
        later = at
    return False


def game_note(prior: Sequence[Utterance], text: str, now: datetime) -> str | None:
    """The note while a game of questions is on, or None."""
    return GAME_NOTE.text if asking_game(prior, text, now) else None
