"""Whether a reply bolted a joke onto its reaction (J45), or leans on a canned generic reaction.

Wording does not stop it: on five real flagged turns about 45% of replies still add a quip whatever
the persona says (`evals/CHANGELOG.md`, 2026-10-19). So a small model labels the reply, and code
decides to draw one fresh reply instead (ADR 0014). Nothing is edited: code only chooses which
whole reply goes out, and the discarded one is kept in the decision detail. The same call says
whether the reaction is generic ("that sounds so good", "X is always the best part"): about one
reply in six had such a line, and on 200 hand-labelled replies the judge was right 88% of the times
it said so (2026-10-24, `evals/CHANGELOG.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.types import Json
from companion.prompts import get

PROMPT = get("system/quip")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"added_joke": {"type": "boolean"}, "generic": {"type": "boolean"}},
    "required": ["added_joke", "generic"],
}


@dataclass(frozen=True, slots=True)
class Verdict:
    joke: bool  # a joke bolted onto an ordinary message
    generic: bool  # a canned reaction that could sit under many messages


def build_prompt(their_text: str, reply: str) -> str:
    return f"USER: {their_text}\nCOMPANION: {reply}"


def parse(data: Json) -> Verdict | None:
    if not isinstance(data, dict):
        return None
    joke, generic = data.get("added_joke"), data.get("generic")
    if not isinstance(joke, bool) or not isinstance(generic, bool):
        return None
    return Verdict(joke, generic)
