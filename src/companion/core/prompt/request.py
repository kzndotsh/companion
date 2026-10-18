"""What the talker is asked. There is no `thinking` field: the talker never reasons.

Reasoning on a fast tier turned a 400 ms first token into 7 s in the speed audit. Leaving the
field out makes the mistake unrepresentable; the provider adapter always sends it disabled.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from companion.core.prompt.prefix import Prefix

Role = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class TalkerRequest:
    """`card` is the memory block. It is sent as a system block after the persona, not inside a
    user message, so the model reads it as background knowledge and not as something just said."""

    prefix: Prefix
    messages: tuple[Message, ...]
    card: str = ""


def build_request(
    prefix: Prefix,
    history: Sequence[Message],
    user_turn: str,
    volatile: str = "",
    card: str = "",
) -> TalkerRequest:
    """`volatile` rides the final user message. Live turns pass it empty and put the clock, the
    memory card and the notes in `card`, the system block; replays of turns recorded before that
    still carry their old volatile text.

    The prefix and every earlier message stay byte-identical turn to turn, so the cache holds
    for as long as the card does not change.
    """
    content = f"{volatile.rstrip()}\n\n{user_turn}" if volatile.strip() else user_turn
    return TalkerRequest(prefix=prefix, messages=(*history, Message("user", content)), card=card)


def request_sha256(request: TalkerRequest) -> str:
    """Identity of exactly what was sent: the prefix hash plus every message, in order."""
    body: dict[str, object] = {
        "prefix": request.prefix.sha256,
        "messages": [[m.role, m.content] for m in request.messages],
    }
    if request.card:
        body["card"] = request.card  # absent when empty, so turns recorded before it still match
    payload = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
