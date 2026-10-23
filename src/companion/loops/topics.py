"""Ask whether a small topic has run its course, with a time limit. A failure means no note."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.topics import JUDGE, SCHEMA, judge_prompt, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 3.0
SPENT = Judge(
    "topics", JUDGE, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no note", trust_fallback=False
)


async def judge_spent(extractor: Extractor, prior: Sequence[Utterance], said: str) -> bool:
    got = await ask(extractor, SPENT, judge_prompt(prior, said))
    return got is not None and got.value
