from __future__ import annotations

import httpx
import pytest

from companion.models.credits import Credits, charged_since, credits


def _client(used: list[float]) -> httpx.AsyncClient:
    """A fake OpenRouter that reports each figure in turn, then repeats the last."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        assert request.url.path == "/api/v1/credits"
        figure = used[min(calls, len(used) - 1)]
        calls += 1
        return httpx.Response(200, json={"data": {"total_credits": 15, "total_usage": figure}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_credits_reads_balance() -> None:
    async with _client([14.9]) as client:
        got = await credits("k", client)
    assert got == Credits(bought=15, used=14.9)
    assert got is not None
    assert got.balance == pytest.approx(0.1)


async def test_charged_waits_for_the_meter_to_settle() -> None:
    async with _client([14.90, 14.93, 14.95, 14.95]) as client:
        before = await credits("k", client)
        assert before is not None
        charged = await charged_since("k", client, before, settle=0)
    assert charged == pytest.approx(0.05)


async def test_unreadable_meter_is_none_not_an_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "no"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await credits("k", client) is None
        assert await charged_since("k", client, Credits(15, 1), settle=0) is None
