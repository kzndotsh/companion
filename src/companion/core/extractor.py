"""What any structured-output model must do. The slow loop depends only on this."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
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


FALLBACK = (
    " (fallback)"  # added to Extraction.model when a refused call was answered by the fallback
)


def from_fallback(model: str) -> bool:
    """Whether an answer came from the fallback model after the first refused. The floor never
    trusts such an answer (ADR 0017)."""
    return model.endswith(FALLBACK)


_judge: ContextVar[str | None] = ContextVar("judge", default=None)


@contextmanager
def judging(name: str) -> Generator[None]:
    """Name the judge the calls inside this block ask. Only `ask` and `read_times` set it, so an
    extractor that routes by judge (`models/fallback.py` `ByJudge`) moves only their calls."""
    token = _judge.set(name)
    try:
        yield
    finally:
        _judge.reset(token)


def current_judge() -> str | None:
    """The judge being asked, or None outside `ask` and `read_times`."""
    return _judge.get()
