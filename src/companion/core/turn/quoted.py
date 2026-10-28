"""The message they used reply on, and the note that tells the talker which one it was.

A reply on Discord or Telegram points at an earlier message, but only their own words reach the
model, so it read every reply as an answer to its latest message. The transport reads the message
they replied to and the turn adds it to the system block, even when it is the latest one: a split
reply is several messages, and a reply picks one of them."""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.types import Speaker
from companion.prompts import get

NOTE = get("notes/replied-to")
MAX_CHARS = 500  # a long message is cut; the start says which one it was


@dataclass(frozen=True, slots=True)
class Quoted:
    """The message they replied to: its text and who sent it."""

    text: str
    speaker: Speaker


def quoted_note(quoted: Quoted | None) -> str | None:
    """The note for the message they replied to, or None when they replied to nothing."""
    if quoted is None or not quoted.text.strip():
        return None
    text = quoted.text.strip()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rstrip() + "…"
    who = "one of your messages" if quoted.speaker is Speaker.COMPANION else "one of their own"
    return NOTE.render(who=who, text="\n".join(f"> {line}" for line in text.splitlines()))
