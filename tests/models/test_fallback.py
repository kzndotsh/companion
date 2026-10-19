from __future__ import annotations

import asyncio

import httpx
import pytest

from companion.core.extractor import Extraction, from_fallback
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json
from companion.models.fallback import RefusalFallback, TalkerFallback


class Refuses:
    def __init__(self, status: int) -> None:
        self.status = status

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(self.status, request=request)
        msg = "refused"
        raise httpx.HTTPStatusError(msg, request=request, response=response)


class Answers:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        return Extraction({"ok": True}, "second/model", 0.001, 5)


async def test_a_refused_call_goes_to_the_second_model_and_is_marked() -> None:
    got = await RefusalFallback(Refuses(403), Answers()).extract("s", "u", {})
    assert got.data == {"ok": True}
    assert from_fallback(got.model)


async def test_other_errors_are_raised_as_before() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        await RefusalFallback(Refuses(500), Answers()).extract("s", "u", {})


async def test_an_answer_from_the_first_model_is_not_marked() -> None:
    got = await RefusalFallback(Answers(), Refuses(403)).extract("s", "u", {})
    assert not from_fallback(got.model)


class _Talker:
    def __init__(self, name: str, *, delay: float = 0.0, fail: bool = False) -> None:
        self.name, self.delay, self.fail = name, delay, fail
        self.calls = 0
        self.cancelled = False

    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        self.calls += 1
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.fail:
            msg = f"{self.name} is down"
            raise RuntimeError(msg)
        return Reply(text=f"from {self.name}", model=self.name, latency_ms=1)


_REQ = TalkerRequest(
    prefix=build_prefix("You are steady and warm. " * 200),
    messages=(Message("user", "hi"),),
    card="",
)


async def test_a_quick_reply_never_asks_the_fallback() -> None:
    fallback = _Talker("deepseek")
    got = await TalkerFallback(_Talker("luna"), fallback, hedge_seconds=0.05).reply(_REQ)
    assert got.model == "luna"
    assert fallback.calls == 0


async def test_an_error_goes_to_the_fallback_at_once() -> None:
    got = await TalkerFallback(_Talker("luna", fail=True), _Talker("deepseek"), 5).reply(_REQ)
    assert got.model == "deepseek"  # the reply says which model wrote it


async def test_a_stall_asks_the_fallback_and_the_first_answer_wins() -> None:
    slow = _Talker("luna", delay=1.0)
    got = await TalkerFallback(slow, _Talker("deepseek", delay=0.01), hedge_seconds=0.05).reply(
        _REQ
    )
    assert got.model == "deepseek"
    assert slow.cancelled  # the slow one is stopped, not left running


async def test_a_stalled_talker_that_answers_first_still_wins() -> None:
    stalled = _Talker("luna", delay=0.1)
    fallback = _Talker("deepseek", delay=1.0)
    got = await TalkerFallback(stalled, fallback, hedge_seconds=0.05).reply(_REQ)
    assert got.model == "luna"
    assert fallback.cancelled


async def test_both_failing_raises_and_a_superseded_turn_cancels_both() -> None:
    with pytest.raises(RuntimeError):
        await TalkerFallback(_Talker("a", fail=True), _Talker("b", fail=True), 5).reply(_REQ)
    first, second = _Talker("luna", delay=1.0), _Talker("deepseek", delay=1.0)
    task = asyncio.ensure_future(TalkerFallback(first, second, hedge_seconds=0.02).reply(_REQ))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert first.cancelled
    assert second.cancelled
