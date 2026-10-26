"""A transport that records what the surface asked of it, for the surface's tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from companion.io.surface import DeliveryError, Incoming


def msg(text: str, n: int = 99) -> Incoming:
    return Incoming(str(n), text, str(n))


@dataclass
class Fake:
    """`calls` holds "send <text>", "react <id> <emoji>" and "typing", in order. `script` is what
    `receive` queues: each message after its delay. `refuse` says whether the nth send fails."""

    script: list[tuple[float, Incoming]] = field(default_factory=list[tuple[float, Incoming]])
    refuse: Callable[[int], bool] = lambda n: False
    react_fails: bool = False
    calls: list[str] = field(default_factory=list[str])
    after: list[str | None] = field(default_factory=list[str | None])
    sends: int = 0

    @property
    def sent(self) -> list[str]:
        return [c.removeprefix("send ") for c in self.calls if c.startswith("send ")]

    @property
    def reactions(self) -> list[str]:
        return [c.removeprefix("react ") for c in self.calls if c.startswith("react ")]

    async def receive(self, inbox: asyncio.Queue[Incoming], after: str | None) -> None:
        self.after.append(after)
        for delay, m in self.script:
            await asyncio.sleep(delay)
            inbox.put_nowait(m)
        await asyncio.Event().wait()

    async def send(self, text: str) -> None:
        self.sends += 1
        if self.refuse(self.sends):
            msg = "send refused"
            raise DeliveryError(msg)
        self.calls.append(f"send {text}")

    async def react(self, message_id: str, emoji: str) -> None:
        if self.react_fails:
            msg = "reaction refused"
            raise DeliveryError(msg)
        self.calls.append(f"react {message_id} {emoji}")

    async def typing(self) -> None:
        self.calls.append("typing")
