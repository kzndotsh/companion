"""Ask the small model whether a reply on a held turn is sexual (ADR 0017)."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import StructuredModel
from companion.core.turn.context import conversation_prompt
from companion.core.turn.floor import (
    BRUSH_OFF,
    EXPLICIT_LEAD,
    INTIMATE_CHECK,
    MINOR_CHECK,
)
from companion.core.types import Utterance
from companion.kit.ask import Read, ask, yes_no_judge

TIMEOUT_SECONDS = 3.0
INTIMATE = yes_no_judge(
    "floor-intimate",
    INTIMATE_CHECK,
    "intimate",
    timeout=TIMEOUT_SECONDS,
    unread="treated as intimate",
    trust_fallback=False,  # the floor never relies on the fallback model (ADR 0017)
    attempts=2,  # one late read threw away a good reply on a scene turn (2026-10-26)
    spend="floor",
)
MINOR = yes_no_judge(
    "floor-minor",
    MINOR_CHECK,
    "minor",
    timeout=4.0,
    unread="treated as a minor: the turn stays held",
    trust_fallback=False,
    attempts=2,
    spend="floor",
)


async def judge_intimate(extractor: StructuredModel, reply: str) -> bool | None:
    """Whether the reply is sexual, or None when it could not be read in time."""
    got = await ask(extractor, INTIMATE, f"COMPANION: {reply}")
    return None if got is None else got.value


ROUTE_SECONDS = 4.0  # a slow read routes the turn as it would have gone
EXPLICIT = yes_no_judge(
    "floor-explicit",
    EXPLICIT_LEAD,
    "explicit",
    timeout=ROUTE_SECONDS,
    unread="not explicit: intimacy starts on the everyday talker",
    spend="floor",
)
DECLINES = yes_no_judge(
    "route",
    BRUSH_OFF,
    "declines",
    timeout=ROUTE_SECONDS,
    unread="no push back: routed as before",
)


async def explicit_lead(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether their message itself is sexually explicit (`system/explicit-lead`)."""
    return await ask(extractor, EXPLICIT, conversation_prompt(prior, said, last=4, tags="colon"))


async def declines(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether their message pushes the flirting or the scene back, even jokingly
    (`system/brush-off`)."""
    return await ask(extractor, DECLINES, conversation_prompt(prior, said, last=6, tags="colon"))


async def confirm_minor(
    extractor: StructuredModel, prior: Sequence[Utterance], said: str
) -> Read[bool] | None:
    """Whether the text says or implies someone in the romantic or sexual content is under 18,
    asked only when the listening judge read the turn as age-coded (`system/minor-check`)."""
    return await ask(extractor, MINOR, conversation_prompt(prior, said, last=10, tags="colon"))
