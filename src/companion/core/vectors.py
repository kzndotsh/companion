"""Vectors for meaning: an embedder, unit vectors, and the memories nearest a message. Shared by
every feature that searches by meaning."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from companion.core.types import Belief, BeliefId

Vector = tuple[float, ...]
SHORTLIST = 15  # how many nearest memories a search returns by default


@dataclass(frozen=True, slots=True)
class Embedded:
    vectors: tuple[Vector, ...]
    model: str
    cost_usd: float


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> Embedded: ...


def unit(v: Sequence[float]) -> Vector:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return tuple(x / norm for x in v)


def dot(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def nearest(
    query: Vector, beliefs: Sequence[Belief], vectors: Mapping[BeliefId, Vector], k: int = SHORTLIST
) -> list[tuple[Belief, float]]:
    """The k memories whose embedding is closest to the query, closest first. A memory with no
    embedding yet is left out."""
    scored = [(b, dot(query, vectors[b.id])) for b in beliefs if b.id in vectors]
    return sorted(scored, key=lambda x: -x[1])[:k]
