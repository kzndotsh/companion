"""What the tics judge found after the last reply, held for the next few turns."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field


@dataclass(slots=True)
class TicMemory:
    """The tics found after the last reply, used for the next couple of turns.

    Found in the background after a reply is sent, so the check never delays a reply. A fast chat
    may not have the answer yet, and then the next turn simply goes without a note.
    """

    tics: list[str] = field(default_factory=list[str])
    age: int = 0
    pending: asyncio.Task[None] | None = None

    def fresh(self, turns: int) -> list[str]:
        """What was found, while it is fewer than `turns` turns old; each call is one turn."""
        found = self.tics if self.age < turns else []
        self.age += 1
        return found

    def start(self, run: Coroutine[object, object, list[str] | None]) -> None:
        if self.pending is not None and not self.pending.done():
            run.close()  # one check at a time
            return

        async def go() -> None:
            found = await run
            if found is not None:
                self.tics, self.age = found, 0

        self.pending = asyncio.ensure_future(go())
