"""Read their answer when the companion asked what to call them (J48)."""

from __future__ import annotations

from companion.core.extractor import Extractor
from companion.core.turn.basics import NAME_CAPTURE, NAME_SCHEMA, parse_name
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 3.0


async def judge_name(extractor: Extractor, asked: str, said: str) -> str | None:
    """The name they gave in reply, or None."""
    judge = Judge(
        "basics",
        NAME_CAPTURE,
        NAME_SCHEMA,
        lambda data: parse_name(data, said),
        timeout=TIMEOUT_SECONDS,
        unread="no name stored",
    )
    got = await ask(extractor, judge, f"COMPANION: {asked}\nUSER: {said}")
    return None if got is None else got.value
