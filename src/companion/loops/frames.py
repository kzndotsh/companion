"""Ask the small model which frame a message is in. Any failure means no judgement."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.frames import PROMPT, SCHEMA, Judgement, build_prompt, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.5
FRAME = Judge("frame", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="storing as real")


def schema_hash() -> str:
    return hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()


def inputs_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


async def judge_frame(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, FRAME, prompt)
    return None if got is None else (got.value, got.model, prompt)
