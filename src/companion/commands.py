"""The one-off commands that run a model outside the bot (`companion callbacks`, `memory group`,
`reflect` and the rest): each opens the store and the judges' model, does one job, and says what it
did and what it cost. What it spends counts toward the day's spend."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from companion.core.clock import local_zone, utc_now
from companion.core.extractor import Extractor
from companion.core.spend import MeteredExtractor, SpendEvent
from companion.core.types import RelationshipId
from companion.daemon import extractor, load_dotenv
from companion.features.callbacks.logic import report
from companion.features.callbacks.run import check_new
from companion.features.context.run import write_missing
from companion.features.episodes.run import write_closed
from companion.features.invented.logic import report as invented_report
from companion.features.invented.run import check_new as check_invented
from companion.features.knowing.run import label_new
from companion.features.lore.run import label_views
from companion.features.merging import run as merging
from companion.features.names.run import read_names
from companion.features.worth.run import label
from companion.loops.rebuild import rebuild
from companion.loops.slow import reflect_from
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class _Services:
    store: Store
    judge: Extractor  # metered: what a command spends counts toward the day's spend
    rel: RelationshipId


@asynccontextmanager
async def _services(db: Path, relationship: str) -> AsyncGenerator[_Services]:
    """What a one-off command needs: the store, the judges' model and the relationship. Closed
    after."""
    load_dotenv(Path(".env"))
    store = Store(db)
    rel = RelationshipId(relationship)

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    try:
        async with httpx.AsyncClient() as client:
            yield _Services(store, MeteredExtractor(extractor(client), sink, "command"), rel)
    finally:
        store.close()


async def callbacks_now(db: Path, relationship: str, days: int, cap_usd: float) -> str:
    """Judge recent replies for callbacks, then report. For `companion callbacks`."""
    start = utc_now() - timedelta(days=days)
    async with _services(db, relationship) as x:
        judged, spent = await check_new(x.store, x.judge, x.rel, start, cap_usd)
        verdicts = x.store.callback_checks_since(x.rel, start)
        replies = {t: x.store.reply_text(x.rel, t) for t, c in verdicts if c.callback}
    shown = [(replies[t], c) for t, c in verdicts if c.callback][-8:]
    head = f"judged {judged} new replies for ${spent:.4f}\n"
    return head + report([c for _, c in verdicts], days, shown)


async def invented_now(
    db: Path, relationship: str, days: int, cap_usd: float, dump: Path | None = None
) -> str:
    """Judge recent replies for made-up facts about the user, then report (G42)."""
    start = utc_now() - timedelta(days=days)
    async with _services(db, relationship) as x:
        judged, spent = await check_invented(x.store, x.judge, x.rel, start, cap_usd)
        checks = x.store.invented_since(x.rel, start)
        if dump is not None:
            dump.write_text(
                json.dumps(x.store.invented_candidates(x.rel, start), ensure_ascii=False, indent=1)
            )
    return f"judged {judged} new replies for ${spent:.4f}\n" + invented_report(checks, days)


async def label_now(db: Path, relationship: str) -> str:
    """Label memories that have no label yet, for `companion map --label`."""
    async with _services(db, relationship) as x:
        done = await label_new(x.store, x.judge, x.rel, utc_now(), batches=10)
    return f"labelled {done.labelled}, {done.left} left, ${done.cost_usd:.4f}\n"


async def group_now(db: Path, relationship: str) -> str:
    """Propose merges across every day and the whole store, for `companion memory group`."""
    async with _services(db, relationship) as x:
        done = await merging.everything(x.store, x.judge, x.rel, utc_now(), local_zone())
    return f"proposed {done.groups} merges, ${done.cost_usd:.4f}; answer them in memory review\n"


async def context_now(db: Path, relationship: str) -> str:
    """Write what they were talking about for every memory that wants it, for `memory context`."""
    async with _services(db, relationship) as x:
        done = await write_missing(x.store, x.judge, x.rel, utc_now(), limit=1000)
    return f"wrote {done.written} notes on what was being talked about, ${done.cost_usd:.4f}\n"


async def worth_now(db: Path, relationship: str) -> str:
    """Label every memory kept before the rule; each change becomes a question, `memory label`."""
    async with _services(db, relationship) as x:
        done = await label(x.store, x.judge, x.rel, utc_now(), act_since=None, limit=1000)
    return (
        f"labelled {done.labelled}, {done.questions} questions for memory review,"
        f" ${done.cost_usd:.4f}\n"
    )


async def episodes_now(db: Path, relationship: str) -> str:
    """Write a record of every finished stretch of chat that has none, for `companion episodes`."""
    async with _services(db, relationship) as x:
        done = await write_closed(x.store, x.judge, x.rel, utc_now())
    return f"wrote {done.written} episodes, ${done.cost_usd:.4f}\n"


async def lore_now(db: Path, relationship: str, *, again: bool = False) -> str:
    """Label its views that have no kind yet (or all of them, `again`), for `companion lore`."""
    async with _services(db, relationship) as x:
        done = await label_views(x.store, x.judge, x.rel, utc_now(), batches=10, again=again)
    return f"labelled {done.labelled}, {done.left} left, ${done.cost_usd:.4f}\n"


async def names_now(db: Path, relationship: str) -> str:
    """List the names in memories not read yet, for `companion names --read`."""
    async with _services(db, relationship) as x:
        done = await read_names(x.store, x.judge, x.rel, utc_now(), batches=10)
    return (
        f"read {done.read} memories, {done.names} names, {done.left} left, ${done.cost_usd:.4f}\n"
    )


async def reflect_now(db: Path, relationship: str, *, from_start: bool = False) -> str:
    """Drain the slow loop's backlog, one batch at a time. For `companion reflect`.

    `from_start` re-reads everything, for after the extraction prompt improves. Claims already
    recorded are skipped as duplicates, so it only adds what was missed.
    """
    lines: list[str] = []
    async with _services(db, relationship) as x:
        start = None if from_start else x.store.reflect_cursor(x.rel)
        while True:
            result = await reflect_from(x.store, x.judge, x.rel, start)
            if not result.ran:
                break
            start = result.upto
            lines.append(
                f"+{result.accepted} beliefs, {result.confirmed} confirmed, "
                f"{result.rejected} rejected, {result.duplicates} duplicates; "
                f"views +{result.views_accepted}, {result.views_confirmed} confirmed, "
                f"{result.views_rejected} rejected; ${result.cost_usd:.5f}"
            )
    return "\n".join(lines or ["nothing new to read"]) + "\n"


async def rebuild_now(db: Path, relationship: str) -> str:
    async with _services(db, relationship) as x:
        return await rebuild(x.store, x.judge, x.rel) + "\n"
