"""What the talker is asked. There is no `thinking` field: the talker never reasons.

Reasoning on a fast tier turned a 400 ms first token into 7 s in the speed audit. Leaving the
field out makes the mistake unrepresentable; the provider adapter always sends it disabled.
"""

from __future__ import annotations

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
    prefix: Prefix
    messages: tuple[Message, ...]


def build_request(
    prefix: Prefix,
    history: Sequence[Message],
    user_turn: str,
    volatile: str = "",
) -> TalkerRequest:
    """Volatile context (plates, moment, catalog) rides the final user message.

    The prefix and every earlier message stay byte-identical turn to turn, so the cache holds.
    """
    content = f"{volatile.rstrip()}\n\n{user_turn}" if volatile.strip() else user_turn
    return TalkerRequest(prefix=prefix, messages=(*history, Message("user", content)))
