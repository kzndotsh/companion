"""Whether a reply bolted a joke onto its reaction (J45).

Wording does not stop it: on five real flagged turns about 45% of replies still add a quip whatever
the persona says (`evals/CHANGELOG.md`, 2026-10-19). So a small model labels the reply, and code
decides to draw one fresh reply instead (ADR 0014). Nothing is edited: code only chooses which
whole reply goes out, and the discarded one is kept in the decision detail.
"""

from __future__ import annotations

from companion.core.types import Json
from companion.prompts import get

PROMPT = get("system/quip")
SYSTEM = PROMPT.text
SERIOUS = 2  # a serious turn is never resampled: it has its own care, and a retry is not that

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"added_joke": {"type": "boolean"}},
    "required": ["added_joke"],
}


def build_prompt(their_text: str, reply: str) -> str:
    return f"USER: {their_text}\nCOMPANION: {reply}"


def parse(data: Json) -> bool | None:
    if not isinstance(data, dict):
        return None
    value = data.get("added_joke")
    return value if isinstance(value, bool) else None


def eligible(*, severity: int | None, in_scene: bool, reply: str) -> bool:
    """Only ordinary turns the listening judge read: not serious, not a scene, not an empty
    reply."""
    return severity is not None and severity < SERIOUS and not in_scene and bool(reply.strip())
