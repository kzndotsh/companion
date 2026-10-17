"""Ask the small model what the companion's recent replies keep repeating. Failure means nothing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass, field

from companion.core.extractor import Extractor
from companion.core.moves import FRESH_FOR, SCHEMA, SYSTEM, build_prompt, note_for, parse
from companion.core.spend import purpose

TIMEOUT_SECONDS = 6.0
log = logging.getLogger("companion.moves")


async def find_habits(
    extractor: Extractor, replies: Sequence[str]
) -> tuple[list[str], str, str] | None:
    """The habits, the model id and the prompt, or None if they could not be found in time."""
    prompt = build_prompt(replies)
    try:
        with purpose("habits"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("habit check failed or timed out; no note: %r", err)
        return None
    habits = parse(result.data)
    log.debug("habit judged %s in %dms, $%.5f", habits, result.latency_ms, result.cost_usd)
    return None if habits is None else (habits, result.model, prompt)


@dataclass(slots=True)
class HabitMemory:
    """The habits found after the last reply, used for the next couple of turns.

    Found in the background after a reply is sent, so the check never delays a reply. A fast chat
    may not have the answer yet, and then the next turn simply goes without a note.
    """

    habits: list[str] = field(default_factory=list[str])
    age: int = 0
    pending: asyncio.Task[None] | None = None

    def note(self) -> str | None:
        """The note for this turn, and age what was found so it is dropped after a few turns."""
        text = note_for(self.habits) if self.age < FRESH_FOR else None
        self.age += 1
        return text

    def start(self, run: Coroutine[object, object, list[str] | None]) -> None:
        if self.pending is not None and not self.pending.done():
            run.close()  # one check at a time
            return

        async def go() -> None:
            found = await run
            if found is not None:
                self.habits, self.age = found, 0

        self.pending = asyncio.ensure_future(go())
