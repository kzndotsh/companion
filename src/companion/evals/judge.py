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

from companion.core.extractor import StructuredModel
from companion.core.prompt.request import Message
from companion.core.types import Json
from companion.evals.checks import Verdict
from companion.prompts import get

PROMPT = get("system/judge")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail", "unclear"]},
        "confidence": {"type": "number"},
    },
    "required": ["verdict", "confidence"],
}


EMPATHY_PROMPT = get("system/judge-empathy")
EMPATHY_SYSTEM = EMPATHY_PROMPT.text

EMPATHY_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "reaction": {"type": "integer", "enum": [0, 1, 2]},
        "interpretation": {"type": "integer", "enum": [0, 1, 2]},
        "exploration": {"type": "integer", "enum": [0, 1, 2]},
        "support": {"type": "integer", "enum": [0, 1, 2]},
    },
    "required": ["reaction", "interpretation", "exploration", "support"],
}


def judge_hash() -> str:
    """Stamps every score, so scores from a different judge are never compared by accident."""
    material = SYSTEM + json.dumps(SCHEMA, sort_keys=True)
    material += EMPATHY_SYSTEM + json.dumps(EMPATHY_SCHEMA, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()[:12]


@dataclass(frozen=True, slots=True)
class Graded:
    verdict: Verdict
    confidence: float
    cost_usd: float


def build_prompt(excerpt: Sequence[Message], reply: str, criterion: str) -> str:
    lines = [
        f"[{'USER' if m.role == 'user' else 'COMPANION'}] {m.content}"
        for m in [m for m in excerpt if m.role != "system"][-4:]
    ]
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
    extractor: StructuredModel, excerpt: Sequence[Message], reply: str, criterion: str
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


EMPATHY_PARTS = ("reaction", "interpretation", "exploration", "support")


def empathy_scores(data: Json) -> dict[str, int] | None:
    """The four scores, or None if the answer is unreadable."""
    if not isinstance(data, dict):
        return None
    scores = {k: data.get(k) for k in EMPATHY_PARTS}
    if any(isinstance(v, bool) or v not in (0, 1, 2) for v in scores.values()):
        return None
    return {k: int(v) for k, v in scores.items()}  # type: ignore[arg-type]


def empathy_verdict(data: Json) -> Verdict:
    """Pass needs a reaction and something beyond the words they said: a strong interpretation, an
    exploration, or support. A reaction plus a restatement fails. Unreadable is unclear."""
    scores = empathy_scores(data)
    if scores is None:
        return "unclear"
    substance = (
        scores["interpretation"] >= 2 or scores["exploration"] >= 1 or scores["support"] >= 1
    )
    return "pass" if scores["reaction"] >= 1 and substance else "fail"


async def grade_empathy(
    extractor: StructuredModel, excerpt: Sequence[Message], reply: str
) -> Graded:
    """Score a reply 0 to 2 on reaction, interpretation, exploration and support."""
    lines = [
        f"[{'USER' if m.role == 'user' else 'COMPANION'}] {m.content}"
        for m in [m for m in excerpt if m.role != "system"][-4:]
    ]
    prompt = "\n".join(["Conversation (end):", *lines, "", f"Reply to grade: {reply}"])
    try:
        result = await extractor.extract(EMPATHY_SYSTEM, prompt, EMPATHY_SCHEMA)
    except Exception:
        return Graded("unclear", 0.0, 0.0)
    return Graded(empathy_verdict(result.data), 1.0, result.cost_usd)
