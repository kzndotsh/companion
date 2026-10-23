from __future__ import annotations

import asyncio

import pytest

from companion.core.extractor import FALLBACK, Extraction
from companion.core.types import Json
from companion.loops.ask import Judge, ask
from companion.prompts import get

PROMPT = get("system/brush-off")
SCHEMA: dict[str, Json] = {"type": "object", "properties": {"declines": {"type": "boolean"}}}


def _parse(data: Json) -> bool | None:
    value = data.get("declines") if isinstance(data, dict) else None
    return value if isinstance(value, bool) else None


def _judge(*, trust_fallback: bool = True, timeout: float = 1.0) -> Judge[bool]:
    return Judge(
        "test",
        PROMPT,
        SCHEMA,
        _parse,
        timeout=timeout,
        unread="nothing changes",
        trust_fallback=trust_fallback,
    )


class Fake:
    def __init__(self, data: Json, model: str = "m", *, delay: float = 0, fail: bool = False):
        self.data, self.model, self.delay, self.fail = data, model, delay, fail
        self.seen: list[tuple[str, str]] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del schema
        self.seen.append((system, user))
        await asyncio.sleep(self.delay)
        if self.fail:
            msg = "down"
            raise RuntimeError(msg)
        return Extraction(self.data, self.model, 0.001, 5)


async def test_a_read_carries_the_value_the_model_the_cost_and_the_prompt_version() -> None:
    fake = Fake({"declines": True})
    got = await ask(fake, _judge(), "their words")
    assert got is not None
    assert (got.value, got.model, got.cost_usd, got.ref) == (True, "m", 0.001, PROMPT.ref)
    assert fake.seen == [(PROMPT.text, "their words")]


@pytest.mark.parametrize(
    "fake",
    [
        Fake({"declines": True}, fail=True),
        Fake({"declines": True}, delay=1),
        Fake({"declines": "maybe"}),
    ],
    ids=["failed", "too slow", "unreadable"],
)
async def test_a_failed_slow_or_unreadable_read_is_none(
    fake: Fake, caplog: pytest.LogCaptureFixture
) -> None:
    assert await ask(fake, _judge(timeout=0.05), "x") is None
    assert "nothing changes" in caplog.text


async def test_a_fallback_answer_counts_only_where_it_is_trusted() -> None:
    fake = Fake({"declines": True}, model=f"m{FALLBACK}")
    assert await ask(fake, _judge(trust_fallback=False), "x") is None
    trusted = await ask(fake, _judge(), "x")
    assert trusted is not None
    assert trusted.value is True


async def test_a_failed_call_is_tried_again_up_to_its_attempts() -> None:
    class Flaky(Fake):
        async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
            self.fail = len(self.seen) == 0  # the first try fails, the second answers
            return await super().extract(system, user, schema)

    once = Judge("t", PROMPT, SCHEMA, _parse, timeout=1.0, unread="x")
    twice = Judge("t", PROMPT, SCHEMA, _parse, timeout=1.0, unread="x", attempts=2)
    assert await ask(Flaky({"declines": True}), once, "x") is None
    got = await ask(Flaky({"declines": True}), twice, "x")
    assert got is not None
    assert got.value is True
