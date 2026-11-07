"""Pure: what the focus look-up embeds, and how close each memory is to the moment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from companion.core.types import BeliefId
from companion.core.vectors import Vector, dot


def moment_texts(said: str, last_reply: str | None) -> list[str]:
    """Their message alone, and with the reply before it: a short message ("lol", "booop") means
    little alone, and the reply it answers says what it is about."""
    return [said, f"{last_reply}\n{said}"] if last_reply else [said]


def closeness(
    queries: Sequence[Vector], vectors: Mapping[BeliefId, Vector]
) -> dict[BeliefId, float]:
    """Each memory's closeness: its best cosine score against either query."""
    return {bid: max(dot(q, v) for q in queries) for bid, v in vectors.items()}
