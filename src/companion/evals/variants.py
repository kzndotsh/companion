"""Variant specs: `v10.md`, `v10.md+nocard`, `v10.md+h10` or `v10.md@provider/model`.

A sample is what the person would receive: the turn's own notes and reply checks
(`evals/sample.py`). `+raw` keeps the model's first reply, with no checks and no redraws.
`+note=PATH@card` adds that file's text to the notes in the system block, and `+note=PATH@tail`
sends it after the history, to try a note before it is built. `+nocard` drops the memory block.
`+h10` keeps only the last 10 messages of history, the last one being what the user just typed.
`+low`, `+medium` or `+high` turns the model's reasoning on at that effort; the bot has it off.
`+as-mika` lays the character `mika` over the persona, as `COMPANION_CHARACTER=mika` does for the
bot. `+roleplay` builds the roleplay talker's prompt and answers as in a pretend scene: with
`+as-CHARACTER`, its sheet section and scene reminder too. `+cardN` and `+histN` rebuild a recorded
turn (`evals/rebuild.py`). Flags combine, with `@model` last: `v10.md+nocard+h10@provider/model`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

EFFORTS = ("low", "medium", "high")
_HISTORY = re.compile(r"h(\d+)")
_CARD = re.compile(r"card(\d+)")
_HIST = re.compile(r"hist(\d+)")
_NOTE = re.compile(r"note=([^@]+)@(card|tail)")
_LAST_NOTE = re.compile(r"(note=[^@]+@(?:card|tail))(?:@(.+))?")
ALL = 10_000  # +cardall: every memory in force at the time

type Place = Literal["card", "tail"]


@dataclass(frozen=True, slots=True)
class Spec:
    persona: str
    keep_card: bool = True
    model: str | None = None
    history: int | None = None
    effort: str | None = None
    character: str | None = None
    roleplay: bool = False
    card: int | None = None  # rebuild a recorded turn's card with this many memories (+cardN)
    long_history: int | None = None  # rebuild a recorded turn with this many messages (+histN)
    raw: bool = False  # the model's first reply, without the turn's checks and redraws
    notes: tuple[tuple[str, Place], ...] = ()  # (file, where): a note tried before it is built

    @property
    def label(self) -> str:
        return (
            self.persona
            + ("" if self.keep_card else "+nocard")
            + ("" if self.history is None else f"+h{self.history}")
            + ("" if self.effort is None else f"+{self.effort}")
            + (f"+as-{self.character}" if self.character else "")
            + ("+roleplay" if self.roleplay else "")
            + ("" if self.card is None else f"+card{'all' if self.card >= ALL else self.card}")
            + ("" if self.long_history is None else f"+hist{self.long_history}")
            + ("+raw" if self.raw else "")
            + "".join(f"+note={path}@{where}" for path, where in self.notes)
            + (f"@{self.model}" if self.model else "")
        )


def _split(text: str) -> tuple[list[str], str]:
    """The persona and flags, and the model after the last `@` that is not a note's place."""
    *flags, last = text.split("+")
    if found := _LAST_NOTE.fullmatch(last):
        return [*flags, found.group(1)], found.group(2) or ""
    last, _, model = last.partition("@")
    return [*flags, last], model


def parse_spec(text: str) -> Spec:
    (persona, *flags), model = _split(text)
    history: int | None = None
    effort: str | None = None
    character: str | None = None
    card: int | None = None
    long_history: int | None = None
    notes: list[tuple[str, Place]] = []
    on: set[str] = set()
    ok = persona.endswith(".md")
    for flag in flags:
        if flag in ("nocard", "roleplay", "raw"):
            on.add(flag)
        elif m := _NOTE.fullmatch(flag):
            notes.append((m.group(1), "card" if m.group(2) == "card" else "tail"))
        elif flag.startswith("as-") and len(flag) > len("as-"):
            character = flag.removeprefix("as-")
        elif flag in EFFORTS:
            effort = flag
        elif (m := _HISTORY.fullmatch(flag)) and int(m.group(1)) >= 1:
            history = int(m.group(1))
        elif flag == "cardall":
            card = ALL
        elif (m := _CARD.fullmatch(flag)) and int(m.group(1)) >= 1:
            card = int(m.group(1))
        elif (m := _HIST.fullmatch(flag)) and int(m.group(1)) >= 1:
            long_history = int(m.group(1))
        else:
            ok = False
    if not ok:
        msg = (
            f"bad variant {text!r}: expected NAME.md with optional +nocard, +hN, +low, +medium,"
            " +high, +as-CHARACTER, +roleplay, +cardN or +cardall, +histN, +raw,"
            " +note=PATH@card or +note=PATH@tail, and @model"
        )
        raise ValueError(msg)
    return Spec(
        persona,
        keep_card="nocard" not in on,
        model=model or None,
        history=history,
        effort=effort,
        character=character,
        roleplay="roleplay" in on,
        card=card,
        long_history=long_history,
        raw="raw" in on,
        notes=tuple(notes),
    )
