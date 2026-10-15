"""Variant specs: `v10.md`, `v10.md+nocard`, or `v10.md@provider/model`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Spec:
    persona: str
    keep_card: bool = True
    model: str | None = None

    @property
    def label(self) -> str:
        return (
            self.persona
            + ("" if self.keep_card else "+nocard")
            + (f"@{self.model}" if self.model else "")
        )


def parse_spec(text: str) -> Spec:
    rest, _, model = text.partition("@")
    persona, plus, flag = rest.partition("+")
    if not persona.endswith(".md") or (plus and flag != "nocard"):
        msg = f"bad variant {text!r}: expected NAME.md, NAME.md+nocard or NAME.md@model"
        raise ValueError(msg)
    return Spec(persona, keep_card=not plus, model=model or None)
