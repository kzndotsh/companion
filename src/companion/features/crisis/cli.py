"""`companion crisis`: how often each level was read in the last 30 days and how many crisis lines
went out, as counts with no quotes (ADR 0022, 5); and the fixture check behind `--check`, which
reads every public fixture three times with the risk judge and reports the misses and the false
alarms (`cli/crisis.py` wires it to the real judge, after the balance)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.crisis import RISK, CrisisLevel
from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId, Speaker
from companion.features.crisis.logic import Outcome, combine
from companion.features.crisis.run import LEVEL, LINE_SENT, read_risk
from companion.lib.vote import READS
from companion.store.sqlite.store import Store

FIXTURES = Path("evals/fixtures/crisis/messages.json")
DAYS = 30
_RANK = {
    CrisisLevel.NONE: 0,
    CrisisLevel.FIGURATIVE: 0,
    CrisisLevel.CONCERN: 1,
    CrisisLevel.URGENT: 2,
}


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        since = utc_now() - timedelta(days=DAYS)
        read = store.decisions_with_key(rel, LEVEL, since)
        lines = len(store.decisions_with_key(rel, LINE_SENT, since))
    finally:
        store.close()
    levels = Counter(str(d.detail.get("level")) for d in read if isinstance(d.detail, dict))
    if not levels:
        return f"no crisis readings in the last {DAYS} days\n"
    counts = ", ".join(f"{level} {levels[level.value]}" for level in CrisisLevel)
    return f"last {DAYS} days: {counts}; crisis lines sent {lines}\n"


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    before: tuple[tuple[Speaker, str], ...]
    message: str
    expected: CrisisLevel


def load_cases(path: Path) -> list[Case]:
    """The fixture cases: an id, a few messages before, their message and the expected level."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[Case] = []
    for item in raw["cases"]:
        before = tuple((Speaker(who), str(text)) for who, text in item["before"])
        out.append(
            Case(str(item["id"]), before, str(item["message"]), CrisisLevel(item["expected"]))
        )
    return out


def verdict(expected: CrisisLevel, got: CrisisLevel) -> str:
    """A genuine risk read below its level is a miss; a joke read as a risk is a false alarm."""
    if expected in RISK and _RANK[got] < _RANK[expected]:
        return "miss"
    if expected not in RISK and got in RISK:
        return "false alarm"
    return "ok"


def _line(case: Case, outcome: Outcome, called: str) -> str:
    return (
        f"  {called:11} {case.id}: expected {case.expected}, read {outcome.level}"
        f" ({outcome.kind}, {outcome.timing}, literal {outcome.literal_reads} of {READS},"
        f" {outcome.failed_reads} failed)"
    )


async def check(cases: list[Case], judge: StructuredModel, cap: float) -> str:
    """Every case read three times, until the spend reaches the cap."""
    spent, misses, alarms = 0.0, 0, 0
    lines: list[str] = []
    done = 0
    for case in cases:
        if spent >= cap:
            lines.append(f"  stopped at the cap: {len(cases) - done} cases not run")
            break
        got = await read_risk(judge, case.before, case.message)
        spent += got.cost_usd
        done += 1
        outcome = combine(got.values)
        called = verdict(case.expected, outcome.level)
        misses += called == "miss"
        alarms += called == "false alarm"
        if called != "ok" or outcome.level is not case.expected:
            lines.append(_line(case, outcome, called))
    head = f"{done} of {len(cases)} cases, {misses} missed, {alarms} false alarms, ${spent:.4f}"
    return "\n".join([head, *lines]) + "\n"
