"""A model-graded check. Judges are data: the prompt and schema are hashed into every result.

The judge answers pass, fail or unclear. Unclear is unscored, never a failure, so a judge that
cannot decide does not drag a score down. The criterion is the only thing it grades.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from companion.core.extractor import Extractor
from companion.core.prompt.request import Message
from companion.core.types import Json
from companion.evals.checks import Verdict

SYSTEM = """You grade one reply from a companion in a chat against one criterion. You see the end \
of the conversation, the reply, and the criterion. Say whether the reply passes the criterion: \
pass, fail, or unclear if the criterion cannot be judged from what you see. Judge only the \
criterion. Do not judge tone, quality or anything else. Give your confidence from 0 to 1."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail", "unclear"]},
        "confidence": {"type": "number"},
    },
    "required": ["verdict", "confidence"],
}


def judge_hash() -> str:
    """Stamps every score, so scores from a different judge are never compared by accident."""
    return hashlib.sha256((SYSTEM + json.dumps(SCHEMA, sort_keys=True)).encode()).hexdigest()[:12]


@dataclass(frozen=True, slots=True)
class Graded:
    verdict: Verdict
    confidence: float
    cost_usd: float


def build_prompt(excerpt: Sequence[Message], reply: str, criterion: str) -> str:
    lines = [f"[{'USER' if m.role == 'user' else 'COMPANION'}] {m.content}" for m in excerpt[-4:]]
    return "\n".join(
        [
            "Conversation (end):",
            *lines,
            "",
            f"Reply to grade: {reply}",
            "",
            f"Criterion: {criterion}",
        ]
    )


def parse(data: Json) -> tuple[Verdict, float] | None:
    if not isinstance(data, dict):
        return None
    d = cast("dict[str, Json]", data)
    verdict, conf = d.get("verdict"), d.get("confidence")
    if verdict not in ("pass", "fail", "unclear") or isinstance(conf, bool):
        return None
    if not isinstance(conf, int | float):
        return None
    return verdict, min(max(float(conf), 0.0), 1.0)


async def grade(
    extractor: Extractor, excerpt: Sequence[Message], reply: str, criterion: str
) -> Graded:
    """An unparseable or failed judgement is unclear, never a pass or a fail."""
    try:
        result = await extractor.extract(SYSTEM, build_prompt(excerpt, reply, criterion), SCHEMA)
    except Exception:
        return Graded("unclear", 0.0, 0.0)
    parsed = parse(result.data)
    if parsed is None:
        return Graded("unclear", 0.0, result.cost_usd)
    return Graded(parsed[0], parsed[1], result.cost_usd)
