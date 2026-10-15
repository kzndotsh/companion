"""Does the provider actually serve cached prompt tokens for our request shape?

Run on purpose: `uv run pytest -m live tests/live -s`. Costs a few cents.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, build_request
from companion.daemon import load_dotenv
from companion.models.openrouter import OpenRouterTalker

pytestmark = pytest.mark.live

HISTORY = [Message("user", "morning"), Message("assistant", "hey"), Message("user", "tired")]


async def _usage(persona_words: int) -> tuple[int, int, int]:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    prefix = build_prefix("You are a steady, warm companion who texts briefly. " * persona_words)
    async with httpx.AsyncClient() as client:
        talker = OpenRouterTalker(key, client, max_tokens=8)
        await talker.reply(build_request(prefix, [*HISTORY, Message("assistant", "ok")], "hi"))
        second = await talker.reply(
            build_request(prefix, [*HISTORY, Message("assistant", "ok")], "hello again")
        )
    return second.input_tokens, second.cache_read_tokens, second.cache_write_tokens


# Measured 2026-10-15 on anthropic/claude-haiku-4.5 via OpenRouter, pinned to Anthropic:
# a ~2.8k-token prompt is never cached and a ~6.6k-token prompt is. The floor sits between.
@pytest.mark.parametrize(("words", "cached"), [(250, False), (600, True)])
async def test_cache_floor(words: int, cached: bool) -> None:
    total, read, write = await _usage(words)
    detail = f"prompt ~{total} tokens: cache_read={read} cache_write={write}"
    assert (read > 0) is cached, detail
