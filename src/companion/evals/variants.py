"""Variant specs: `v10.md`, `v10.md+nocard`, `v10.md+h10` or `v10.md@provider/model`.

`+low`, `+medium` or `+high` turns the model's reasoning on at that effort. The bot has it off.
`+h10` keeps only the last 10 messages of history, the last one being what the user just typed.
`+len` adds the length note the bot adds to a short statement. `+listen` adds the listening note
the labels in a fixture's script would produce. `+as-mika` lays the character `mika` over the
persona, as `COMPANION_CHARACTER=mika` does for the bot. `+echo` adds the note against copying
their emoji or emoticon, on a message that has one. `+mood-cozy` adds the candidate mood line for
one state, and `+mood-cozy.playful` for two (ADR 0016), to measure a mood before it is built.
Flags combine: `v10.md+nocard+h10@provider/model`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EFFORTS = ("low", "medium", "high")
MOODS = ("cozy", "tender", "playful", "buzzing", "flat")
_HISTORY = re.compile(r"h(\d+)")


@dataclass(frozen=True, slots=True)
class Spec:
    persona: str
    keep_card: bool = True
    model: str | None = None
    history: int | None = None
    effort: str | None = None
    length: bool = False
    listen: bool = False
    character: str | None = None
    echo: bool = False
    mood: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return (
            self.persona
            + ("" if self.keep_card else "+nocard")
            + ("" if self.history is None else f"+h{self.history}")
            + ("" if self.effort is None else f"+{self.effort}")
            + ("+len" if self.length else "")
            + ("+listen" if self.listen else "")
            + (f"+as-{self.character}" if self.character else "")
            + ("+echo" if self.echo else "")
            + (f"+mood-{'.'.join(self.mood)}" if self.mood else "")
            + (f"@{self.model}" if self.model else "")
        )


def parse_spec(text: str) -> Spec:
    rest, _, model = text.partition("@")
    persona, *flags = rest.split("+")
    keep_card, history, effort, length, listen = True, None, None, False, False
    character: str | None = None
    echo = False
    mood: tuple[str, ...] = ()
    ok = persona.endswith(".md")
    for flag in flags:
        if flag == "nocard":
            keep_card = False
        elif flag == "len":
            length = True
        elif flag == "listen":
            listen = True
        elif flag == "echo":
            echo = True
        elif flag.startswith("mood-") and _moods(flag.removeprefix("mood-")):
            mood = tuple(flag.removeprefix("mood-").split("."))
        elif flag.startswith("as-") and len(flag) > len("as-"):
            character = flag.removeprefix("as-")
        elif flag in EFFORTS:
            effort = flag
        elif (m := _HISTORY.fullmatch(flag)) and int(m.group(1)) >= 1:
            history = int(m.group(1))
        else:
            ok = False
    if not ok:
        msg = (
            f"bad variant {text!r}: expected NAME.md with optional"
            " +nocard, +hN, +low/+medium/+high, +len, +listen, +echo, +mood-STATE,"
            " +as-CHARACTER and @model"
        )
        raise ValueError(msg)
    return Spec(
        persona, keep_card, model or None, history, effort, length, listen, character, echo, mood
    )


def _moods(text: str) -> bool:
    names = text.split(".")
    return 1 <= len(names) <= 2 and len(set(names)) == len(names) and set(names) <= set(MOODS)
