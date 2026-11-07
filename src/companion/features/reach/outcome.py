"""How each reach-out landed (ADR 0021, card A6, issue 123). Pure.

One record per reach-out of any kind (its own reasons, a plan, a nudge), once their answer is in
or two days passed without one. In shadow nothing was sent, so a shadow record shows only when they
came back on their own: the base rate a live one is compared with. How they took it, and a request
to stop, are read only for a live one. A stop holds every reach-out until the owner turns it back
on.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from statistics import median

from companion.core.reachout import Kind
from companion.core.types import Json
from companion.features.reach.gate import ANSWER_SPAN, Answer, answer
from companion.prompts import get

OUTCOME = "reach out: outcome"
STOPPED = "reach out: stopped"
RESUMED = "reach out: resumed"
UNANSWERED_AFTER = timedelta(hours=48)  # no answer in this long is unanswered
LANDED = get("system/reach-landed")


class Landed(StrEnum):
    """How they took a live reach-out, read from their first answer."""

    PICKED_UP = "picked_up"
    BRUSHED_OFF = "brushed_off"
    IGNORED = "ignored"
    STOP = "asked_to_stop"


LANDED_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"landed": {"type": "string", "enum": [m.value for m in Landed]}},
    "required": ["landed"],
    "additionalProperties": False,
}


def parse_landed(data: Json) -> Landed | None:
    got = data.get("landed") if isinstance(data, dict) else None
    return next((m for m in Landed if m.value == got), None)


def landed_prompt(sent: str, theirs: str) -> str:
    return f"COMPANION: {sent}\nUSER: {theirs}"


@dataclass(frozen=True, slots=True)
class Sent:
    """One reach-out of any kind: sent (live) or would have been (shadow)."""

    id: str
    kind: Kind
    live: bool
    text: str
    at: datetime


@dataclass(frozen=True, slots=True)
class Outcome:
    sent: Sent
    got: Answer | None  # None: unanswered
    reply: str  # their words in the answer, empty when unanswered

    def detail(self, landed: Landed | None) -> dict[str, Json]:
        """The record. `landed` is None for a shadow one (never read) or a failed read."""
        got = self.got
        return {
            "reach_out": self.sent.id,
            "kind": self.sent.kind.value,
            "mode": "live" if self.sent.live else "shadow",
            "base_rate": not self.sent.live,
            "sent_at": self.sent.at.isoformat(),
            "answered": got is not None,
            "after_hours": None if got is None else round(got.after.total_seconds() / 3600, 2),
            "words": 0 if got is None else got.words,
            "landed": landed.value if landed else None if not self.sent.live else "not read",
        }


def outcome(sent: Sent, theirs: Sequence[tuple[datetime, str]], now: datetime) -> Outcome | None:
    """How it landed as of `now`, or None while still open: their answer is still coming in, or two
    days have not yet passed without one. An answer after two days counts as unanswered."""
    got = answer(sent.at, [t for t in theirs if t[0] <= now])
    if got is None or got.after > UNANSWERED_AFTER:
        return Outcome(sent, None, "") if now - sent.at >= UNANSWERED_AFTER else None
    first = sent.at + got.after
    if now < first + ANSWER_SPAN:
        return None
    reply = " ".join(text for at, text in sorted(theirs) if first <= at <= first + ANSWER_SPAN)
    return Outcome(sent, got, reply)


def stopped(stops: Sequence[datetime], resumes: Sequence[datetime]) -> bool:
    """Whether a request to stop stands: one came after the owner last turned it back on."""
    last = max(stops, default=None)
    return last is not None and last > max(resumes, default=last - timedelta(seconds=1))


def summary(records: Sequence[dict[str, Json]]) -> list[str]:
    """How the reach-outs landed, by kind and mode, from their records: how many were answered, the
    median hours to an answer, and for live ones how they took them."""
    groups: dict[tuple[str, str], list[dict[str, Json]]] = {}
    for r in records:
        groups.setdefault((str(r.get("kind")), str(r.get("mode"))), []).append(r)
    out: list[str] = []
    for (kind, mode), rs in sorted(groups.items()):
        hours = [h for r in rs if isinstance(h := r.get("after_hours"), int | float)]
        answered = sum(r.get("answered") is True for r in rs)
        mid = f", median {median(hours):.1f}h" if hours else ""
        line = f"  {kind:16} {mode:6} {answered} of {len(rs)} answered{mid}"
        if mode == "live":
            took = Counter(str(r.get("landed")) for r in rs if r.get("answered") is True)
            line += "".join(f", {n} {k}" for k, n in sorted(took.items()))
        out.append(line)
    return out
