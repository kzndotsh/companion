"""The callback score: did a reply bring up a memory on its own, and did that land.

Users of companion apps value one thing above the rest: the companion bringing up something minor
from days ago, unprompted, correctly and at a fitting moment. Research on memory in agents measures
recall questions, not this, and treats over-use (irrelevant, repeated, flattering) as its own
failure; a wrong callback hurts more than a missed one. So each reply is read by a judge beside the
memories its card held, and the report puts precision first: of the callbacks it made, how many were
accurate, fitting and not forced. Word overlap cannot find callbacks (on 570 real turns it found 6,
all false matches).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from companion.core.types import Json
from companion.prompts import get

PROMPT = get("system/callback-judge")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "callback": {"type": "boolean"},
        "memories": {"type": "array", "items": {"type": "string"}},
        "accurate": {"type": "boolean"},
        "fitting": {"type": "boolean"},
        "forced": {"type": "boolean"},
    },
    "required": ["callback", "memories", "accurate", "fitting", "forced"],
}


@dataclass(frozen=True, slots=True)
class Check:
    callback: bool
    memories: tuple[str, ...]  # the claims it brought up
    accurate: bool
    fitting: bool
    forced: bool

    @property
    def landed(self) -> bool:
        return self.callback and self.accurate and self.fitting and not self.forced


def label(memories: Sequence[str]) -> dict[str, str]:
    return {f"m{i}": claim for i, claim in enumerate(memories, start=1)}


def build_prompt(recent: Sequence[tuple[str, str]], labelled: Mapping[str, str], reply: str) -> str:
    talk = [f"[{'USER' if who == 'user' else 'COMPANION'}] {text}" for who, text in recent]
    known = [f"[{k}] {claim}" for k, claim in labelled.items()]
    return "\n".join(
        ["Recent messages:", *talk, "", "Its memories:", *known, "", f"The reply: {reply}"]
    )


def parse(data: Json, labelled: Mapping[str, str]) -> Check | None:
    if not isinstance(data, dict):
        return None
    flags = [data.get(k) for k in ("callback", "accurate", "fitting", "forced")]
    raw = data.get("memories")
    if not all(isinstance(f, bool) for f in flags) or not isinstance(raw, list):
        return None
    callback, accurate, fitting, forced = (bool(f) for f in flags)
    named = [labelled.get(str(x).strip().strip("[]")) for x in raw]
    claims = tuple(c for c in named if c is not None)
    if callback and not claims:
        return None  # a callback with no memory it can name is not one we can check
    return Check(callback, claims, accurate, fitting, forced)


def report(checks: Sequence[Check], days: int, examples: Sequence[tuple[str, Check]] = ()) -> str:
    """Precision first: how many callbacks landed, how many were wrong, forced or out of place."""
    made = [c for c in checks if c.callback]
    landed = sum(c.landed for c in made)
    wrong = sum(not c.accurate for c in made)
    off = sum(c.accurate and (not c.fitting or c.forced) for c in made)
    lines = [f"last {days} days: {len(checks)} replies checked, {len(made)} callbacks"]
    if made:
        lines.append(
            f"  landed {landed} of {len(made)} | wrong {wrong} | forced or out of place {off}"
        )
    for reply, c in examples:
        verdict = "landed" if c.landed else "wrong" if not c.accurate else "forced/out of place"
        lines.append(f"  - {verdict}: {reply[:100]!r}  <= {c.memories[0][:80]}")
    return "\n".join(lines) + "\n"
