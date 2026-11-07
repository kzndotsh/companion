"""What the tics judge found after the last reply, held for the next few turns."""

from __future__ import annotations

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
    running: bool = False

    def fresh(self, turns: int) -> list[str]:
        """What was found, while it is fewer than `turns` turns old; each call is one turn."""
        found = self.tics if self.age < turns else []
        self.age += 1
        return found

    async def run(self, check: Coroutine[object, object, list[str] | None]) -> None:
        """Keep what the check finds. One check at a time: asked while one is running, it is not
        awaited."""
        if self.running:
            check.close()
            return
        self.running = True
        try:
            found = await check
        finally:
            self.running = False
        if found is not None:
            self.tics, self.age = found, 0
