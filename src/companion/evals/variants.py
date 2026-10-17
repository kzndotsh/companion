"""Variant specs: `v10.md`, `v10.md+nocard`, `v10.md+h10` or `v10.md@provider/model`.

`+low`, `+medium` or `+high` turns the model's reasoning on at that effort. The bot has it off.
`+h10` keeps only the last 10 messages of history, the last one being what the user just typed.
Flags combine: `v10.md+nocard+h10@provider/model`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EFFORTS = ("low", "medium", "high")
_HISTORY = re.compile(r"h(\d+)")


@dataclass(frozen=True, slots=True)
class Spec:
    persona: str
    keep_card: bool = True
    model: str | None = None
    history: int | None = None
    effort: str | None = None

    @property
    def label(self) -> str:
        return (
            self.persona
            + ("" if self.keep_card else "+nocard")
            + ("" if self.history is None else f"+h{self.history}")
            + ("" if self.effort is None else f"+{self.effort}")
            + (f"@{self.model}" if self.model else "")
        )


def parse_spec(text: str) -> Spec:
    rest, _, model = text.partition("@")
    persona, *flags = rest.split("+")
    keep_card, history, effort = True, None, None
    ok = persona.endswith(".md")
    for flag in flags:
        if flag == "nocard":
            keep_card = False
        elif flag in EFFORTS:
            effort = flag
        elif (m := _HISTORY.fullmatch(flag)) and int(m.group(1)) >= 1:
            history = int(m.group(1))
        else:
            ok = False
    if not ok:
        msg = (
            f"bad variant {text!r}: expected NAME.md with optional"
            " +nocard, +hN, +low/+medium/+high and @model"
        )
        raise ValueError(msg)
    return Spec(persona, keep_card, model or None, history, effort)
