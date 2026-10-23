from __future__ import annotations

import httpx
import pytest

from companion.lib import retry
from companion.lib.retry import retry_on_network_error


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fast(seconds: float) -> None:
        del seconds

    monkeypatch.setattr(retry.asyncio, "sleep", fast)


def _flaky(failures: int, error: Exception) -> tuple[list[int], object]:
    calls: list[int] = []

    async def call() -> str:
        calls.append(1)
        if len(calls) <= failures:
            raise error
        return "ok"

    return calls, call


async def test_a_dropped_connection_is_retried_until_it_works() -> None:
    calls, call = _flaky(2, httpx.ConnectError("down"))
    assert await retry_on_network_error(call) == "ok"  # type: ignore[arg-type]
    assert len(calls) == 3


async def test_it_gives_up_after_the_last_delay_and_raises() -> None:
    calls, call = _flaky(10, httpx.ConnectError("down"))
    with pytest.raises(httpx.ConnectError):
        await retry_on_network_error(call, (0.1, 0.1))  # type: ignore[arg-type]
    assert len(calls) == 3


async def test_a_real_error_is_never_retried() -> None:
    calls, call = _flaky(10, ValueError("the model said no"))
    with pytest.raises(ValueError, match="said no"):
        await retry_on_network_error(call)  # type: ignore[arg-type]
    assert len(calls) == 1


async def test_a_timeout_counts_as_a_network_error() -> None:
    calls, call = _flaky(1, httpx.ReadTimeout("slow"))
    assert await retry_on_network_error(call) == "ok"  # type: ignore[arg-type]
    assert len(calls) == 2
