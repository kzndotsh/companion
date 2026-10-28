"""Running a one-off command outside the bot: `run` opens the store and the judges' model and hands
them to a job (each feature's own is in its `cli.py`); running the memory pass and rebuilding memory
live here. What a command spends counts toward the day's spend."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx

from companion.core.spend import MeteredExtractor, SpendEvent
from companion.core.types import RelationshipId
from companion.daemon import extractor, load_dotenv
from companion.kit.services import Services
from companion.memory.memory_pass import memory_pass_from
from companion.memory.rebuild import rebuild
from companion.store.sqlite.store import Store


@asynccontextmanager
async def _services(db: Path, relationship: str) -> AsyncGenerator[Services]:
    """What a one-off command needs: the store, the judges' model and the relationship. Closed
    after."""
    load_dotenv(Path(".env"))
    store = Store(db)
    rel = RelationshipId(relationship)

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    try:
        async with httpx.AsyncClient() as client:
            yield Services(store, MeteredExtractor(extractor(client), sink, "command"), rel)
    finally:
        store.close()


async def run(db: Path, relationship: str, job: Callable[[Services], Awaitable[str]]) -> str:
    """Open the store and the judges' model, run one command's job, and close them."""
    async with _services(db, relationship) as x:
        return await job(x)


async def memory_pass_now(db: Path, relationship: str, *, from_start: bool = False) -> str:
    """Drain the memory pass's backlog, one batch at a time. For `companion memory-pass`.

    `from_start` re-reads everything, for after the extraction prompt improves. Claims already
    recorded are skipped as duplicates, so it only adds what was missed.
    """
    lines: list[str] = []
    async with _services(db, relationship) as x:
        start = None if from_start else x.store.pass_cursor(x.rel)
        while True:
            result = await memory_pass_from(x.store, x.judge, x.rel, start)
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
