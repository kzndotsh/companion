"""Asking the same question several times and acting only when every answer agrees.

A failed or unreadable answer (None) is never agreement. A caller with its own rule for answers
that differ keeps that rule itself; a plain "all the same" lives here.
"""

from __future__ import annotations

from collections.abc import Iterable

READS = 3


def unanimous[T](reads: Iterable[T | None]) -> T | None:
    """The value every one of the READS reads gave, else None."""
    found = list(reads)
    first = found[0] if found else None
    return (
        first
        if first is not None and len(found) == READS and all(r == first for r in found)
        else None
    )
