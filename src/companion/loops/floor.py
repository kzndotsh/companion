"""Ask the small model whether a reply on a held turn is sexual (ADR 0017)."""

from __future__ import annotations

from companion.core.extractor import Extractor
from companion.core.floor import INTIMATE_CHECK, INTIMATE_SCHEMA, parse_intimate
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 3.0
INTIMATE = Judge(
    "floor",
    INTIMATE_CHECK,
    INTIMATE_SCHEMA,
    parse_intimate,
    timeout=TIMEOUT_SECONDS,
    unread="treated as intimate",
    trust_fallback=False,  # the floor never relies on the fallback model (ADR 0017)
)


async def judge_intimate(extractor: Extractor, reply: str) -> bool | None:
    """Whether the reply is sexual, or None when it could not be read in time."""
    got = await ask(extractor, INTIMATE, f"COMPANION: {reply}")
    return None if got is None else got.value
