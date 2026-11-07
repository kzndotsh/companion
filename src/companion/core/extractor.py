"""What any structured-output model must do. The memory pass depends only on this."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Protocol

from companion.core.types import Json


@dataclass(frozen=True, slots=True)
class Extraction:
    data: Json
    model: str
    cost_usd: float
    latency_ms: int
    fallback: bool = False  # answered by the fallback model after the first refused (ADR 0017)


class StructuredModel(Protocol):
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction: ...


FALLBACK = " (fallback)"  # added to the model's name in a log when the fallback answered


def as_fallback(got: Extraction) -> Extraction:
    """An answer marked as the fallback model's: the flag the floor reads (it never trusts such an
    answer, ADR 0017), and the model's name with `FALLBACK` after it, as logs and rows show it."""
    return replace(got, model=got.model + FALLBACK, fallback=True)


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
