"""Parse `/flag [kind] note`. An unrecognised first word means the whole text is the note."""

from __future__ import annotations

from companion.core.types import FlagKind


def parse_flag(arg: str) -> tuple[FlagKind, str]:
    text = arg.strip()
    head, _, rest = text.partition(" ")
    try:
        return FlagKind(head.lower()), rest.strip()
    except ValueError:
        return FlagKind.OFF, text
