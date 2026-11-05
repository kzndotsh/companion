"""What a turn hands to the chat: an emoji reaction, a reaction with a reply, or a reply with a
fixed message after it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Reaction:
    """Answer a message with an emoji reaction instead of text."""

    emoji: str


@dataclass(frozen=True, slots=True)
class ReactAndReply:
    """An emoji reaction on the user's message, then a normal reply."""

    reaction: Reaction
    text: str


@dataclass(frozen=True, slots=True)
class ThenSend:
    """A reply, then a fixed message of code's own sent after it: the crisis line on an urgent
    turn (ADR 0022). The second is never written by a model, and the reply is never edited."""

    reply: str | ReactAndReply
    then: str
