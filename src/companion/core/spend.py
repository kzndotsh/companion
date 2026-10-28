"""Counting what the paid calls cost, without the callers knowing.

A talker or an extractor is wrapped once, in the daemon, and every call that comes back with a
cost is reported to a sink. The purpose ("talker", "ack", "memory") says what the call was for. A
talker has a fixed one. An extractor is shared by several judges, so each judge names itself with
`purpose(...)` and the wrapper reads it. A call that was cancelled or failed before answering has
no cost to report, which is a known gap, not an error.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from companion.core.extractor import Extraction, StructuredModel
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply, Talker
from companion.core.types import Json
from companion.core.vectors import Embedded, Embedder


@dataclass(frozen=True, slots=True)
class SpendEvent:
    purpose: str
    model: str
    cost_usd: float
    input_tokens: int = 0


Sink = Callable[[SpendEvent], None]
_purpose: ContextVar[str | None] = ContextVar("spend_purpose", default=None)


@contextmanager
def purpose(name: str) -> Generator[None]:
    """Name what the calls inside this block are for."""
    token = _purpose.set(name)
    try:
        yield
    finally:
        _purpose.reset(token)


class MeteredTalker:
    def __init__(self, inner: Talker, sink: Sink, purpose_name: str = "talker") -> None:
        self._inner = inner
        self._sink = sink
        self._purpose = purpose_name

    async def reply(self, request: TalkerRequest) -> Reply:
        reply = await self._inner.reply(request)
        self._sink(SpendEvent(self._purpose, reply.model, reply.cost_usd, reply.input_tokens))
        return reply


class MeteredExtractor:
    def __init__(self, inner: StructuredModel, sink: Sink, default_purpose: str = "judge") -> None:
        self._inner = inner
        self._sink = sink
        self._default = default_purpose

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        result = await self._inner.extract(system, user, schema)
        self._sink(SpendEvent(_purpose.get() or self._default, result.model, result.cost_usd))
        return result


class MeteredEmbedder:
    def __init__(self, inner: Embedder, sink: Sink, purpose_name: str = "relevance") -> None:
        self._inner = inner
        self._sink = sink
        self._purpose = purpose_name

    async def embed(self, texts: Sequence[str]) -> Embedded:
        result = await self._inner.embed(texts)
        self._sink(SpendEvent(_purpose.get() or self._purpose, result.model, result.cost_usd))
        return result
