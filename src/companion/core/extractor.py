"""What any structured-output model must do. The slow loop depends only on this."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from companion.core.types import Json


@dataclass(frozen=True, slots=True)
class Extraction:
    data: Json
    model: str
    cost_usd: float
    latency_ms: int


class Extractor(Protocol):
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction: ...
