"""Whether its last replies were a run of questions, and the note that breaks the run.

A question invites another: after one question reply 49% of the next ask again, after two 57%, and
11% of everyday replies follow three in a row (2026-10-24, 1,059 replies), until they asked why it
asks every turn. Sent after the history, like the owned-it note (prompts/CHANGELOG.md)."""

from __future__ import annotations

from collections.abc import Sequence

from companion.prompts import get

NOTE = get("notes/question-run")
RUN = 3  # its last replies that all asked something


def asked(reply: str) -> bool:
    """Whether a reply of its own asked them something."""
    return "?" in reply


def question_note(replies: Sequence[str]) -> str | None:
    """The note when each of its last RUN replies asked a question."""
    last = replies[-RUN:]
    if len(last) < RUN or not all(asked(r) for r in last):
        return None
    return NOTE.text
