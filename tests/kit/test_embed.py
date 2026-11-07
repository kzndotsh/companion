from __future__ import annotations

import asyncio
from collections.abc import Sequence

from companion.core.spend import MeteredEmbedder, SpendEvent
from companion.core.vectors import Embedded
from companion.kit.embed import bounded, embed_within


class Fake:
    def __init__(self, *, delay: float = 0, fail: bool = False) -> None:
        self.delay, self.fail = delay, fail

    async def embed(self, texts: Sequence[str]) -> Embedded:
        await asyncio.sleep(self.delay)
        if self.fail:
            msg = "down"
            raise RuntimeError(msg)
        return Embedded(tuple((1.0,) for _ in texts), "m", 0.001)


async def test_an_embedding_in_time_is_returned_and_tagged_for_spend() -> None:
    events: list[SpendEvent] = []
    got = await embed_within(
        MeteredEmbedder(Fake(), events.append), ["a"], spend="lore", deadline=1.0, unread="x"
    )
    assert got is not None
    assert [e.purpose for e in events] == ["lore"]


async def test_a_failed_or_slow_embedding_is_none() -> None:
    for fake in (Fake(fail=True), Fake(delay=1)):
        got = await embed_within(fake, ["a"], spend="lore", deadline=0.01, unread="nothing shown")
        assert got is None


async def test_any_look_up_can_be_bounded() -> None:
    async def work() -> int:
        return 3

    assert await bounded(work(), deadline=1.0, what="w", unread="u") == 3
