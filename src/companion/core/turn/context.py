"""What the small judges read of a conversation, and the hashes a logged decision keeps of it."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from companion.core.types import Json, Speaker, Utterance

# 8, not 4: with 4, a curt "thanks" after a hurt and a grudging forgiveness two exchanges back read
# as a plain ack every time (12/12) and got only an emoji; with 8 it got a reply 11/12. Past 8 the
# reads did not change (evals/CHANGELOG.md, 2026-11-02).
CONTEXT_MESSAGES = 8

# How a line names its speaker: `[USER] text` or `USER: text`. Each judge's prompt was measured in
# one of the two, so each keeps its own.
type Tags = Literal["bracket", "colon"]


def transcript_prompt(
    before: Sequence[tuple[Speaker, str]],
    said: str,
    *,
    tags: Tags = "bracket",
    preamble: Sequence[str] = (),
) -> str:
    """The one shape a small judge reads a conversation in: the lines before, then their newest
    message. `preamble` lines come first."""
    lines = [
        f"[{_name(who)}] {text}" if tags == "bracket" else f"{_name(who)}: {text}"
        for who, text in before
    ]
    return "\n".join([*preamble, "Conversation:", *lines, "", f"Newest USER message: {said}"])


def conversation_prompt(
    history: Sequence[Utterance],
    said: str,
    *,
    last: int = CONTEXT_MESSAGES,
    tags: Tags = "bracket",
    preamble: Sequence[str] = (),
) -> str:
    """`transcript_prompt` over the last `last` messages of a history."""
    before = [(u.speaker, u.text) for u in history[-last:]]
    return transcript_prompt(before, said, tags=tags, preamble=preamble)


def _name(who: Speaker) -> str:
    return "USER" if who is Speaker.USER else "COMPANION"


def inputs_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def schema_hash(schema: Json) -> str:
    return hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Scored[T]:
    """A small judge's read, the model that made it and the prompt text it read: what the turn
    keeps of a judge whose decision is logged later, once the turn knows what it did with it."""

    read: T
    model: str
    prompt: str
    fallback: bool = False  # the fallback model answered: the floor does not trust such a read

    def detail(self, ref: str, *, schema: Json | None = None, **rest: Json) -> dict[str, Json]:
        """The standard detail of a judge's logged decision: who read it, which prompt version, the
        hash of its input (and of its schema when that is kept), then what it found (`rest`)."""
        out: dict[str, Json] = {"scorer": self.model, "prompt": ref}
        if schema is not None:
            out["schema_hash"] = schema_hash(schema)
        out["inputs_hash"] = inputs_hash(self.prompt)
        return out | rest
