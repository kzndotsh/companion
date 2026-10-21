"""How many times a small model reads one question, and when its reads agree (ADR 0019).

Code acts on a model's label only where every read gives it; a failed read is never agreement.
Each feature keeps its own rule for what agreement means when reads differ (`core/worth.py`,
`core/lore.py`, `core/merging.py`); a plain "all the same" lives here.
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
