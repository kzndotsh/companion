"""Ask the small model whether a reply on a held turn is sexual (ADR 0017)."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import StructuredModel
from companion.core.turn.floor import (
    BRUSH_OFF,
    BRUSH_SCHEMA,
    EXPLICIT_LEAD,
    EXPLICIT_SCHEMA,
    INTIMATE_CHECK,
    INTIMATE_SCHEMA,
    MINOR_CHECK,
    MINOR_SCHEMA,
    parse_declines,
    parse_explicit,
    parse_intimate,
    parse_minor,
)
from companion.core.types import Utterance
from companion.loops.ask import Judge, Read, ask

TIMEOUT_SECONDS = 3.0
INTIMATE = Judge(
    "floor",
    INTIMATE_CHECK,
    INTIMATE_SCHEMA,
    parse_intimate,
    timeout=TIMEOUT_SECONDS,
    unread="treated as intimate",
    trust_fallback=False,  # the floor never relies on the fallback model (ADR 0017)
    attempts=2,  # one late read threw away a good reply on a scene turn (2026-10-26)
)
MINOR = Judge(
    "floor",
    MINOR_CHECK,
    MINOR_SCHEMA,
    parse_minor,
    timeout=4.0,
    unread="treated as a minor: the turn stays held",
    trust_fallback=False,
    attempts=2,
)


async def judge_intimate(extractor: StructuredModel, reply: str) -> bool | None:
    """Whether the reply is sexual, or None when it could not be read in time."""
    got = await ask(extractor, INTIMATE, f"COMPANION: {reply}")
    return None if got is None else got.value


ROUTE_SECONDS = 4.0  # a slow read routes the turn as it would have gone
EXPLICIT = Judge(
    "floor",
    EXPLICIT_LEAD,
    EXPLICIT_SCHEMA,
    parse_explicit,
    timeout=ROUTE_SECONDS,
    unread="not explicit: intimacy starts on the everyday talker",
)
DECLINES = Judge(
    "route",
    BRUSH_OFF,
    BRUSH_SCHEMA,
    parse_declines,
    timeout=ROUTE_SECONDS,
    unread="no push back: routed as before",
)


def _conversation(prior: Sequence[Utterance], said: str, last: int) -> str:
    lines = [f"{u.speaker.value.upper()}: {u.text}" for u in prior[-last:]]
    return "\n".join(["Conversation:", *lines, "", f"Newest USER message: {said}"])


async def explicit_lead(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether their message itself is sexually explicit (`system/explicit-lead`)."""
    return await ask(extractor, EXPLICIT, _conversation(prior, said, 4))


async def declines(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether their message pushes the flirting or the scene back, even jokingly
    (`system/brush-off`)."""
    return await ask(extractor, DECLINES, _conversation(prior, said, 6))


async def confirm_minor(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether the text says or implies someone in the romantic or sexual content is under 18,
    asked only when the listening judge read the turn as age-coded (`system/minor-check`)."""
    return await ask(extractor, MINOR, _conversation(prior, said, 10))
