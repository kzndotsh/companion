"""What any talker model must do. Providers implement this; the loop depends only on it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from companion.core.prompt.request import TalkerRequest


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    model: str
    latency_ms: int
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


class Talker(Protocol):
    async def reply(self, request: TalkerRequest) -> Reply: ...
