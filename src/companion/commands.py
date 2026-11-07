"""Running a one-off command outside the bot: `run` opens the store and the judges' model and hands
them to a job (each feature's own is in its `cli.py`); running the memory pass and rebuilding memory
live here. What a command spends counts toward the day's spend."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from companion.characters import chosen, sheets_dir
from companion.compose import embedder, extractor, pass_options, spend_sink
from companion.core.spend import MeteredExtractor
from companion.core.types import RelationshipId
from companion.kit.services import Services
from companion.memory.memory_pass import memory_pass_from
from companion.memory.rebuild import rebuild
from companion.settings import Settings
from companion.store.sqlite.store import Store


@asynccontextmanager
async def _services(db: Path, relationship: str) -> AsyncGenerator[Services]:
    """What a one-off command needs: the store, the judges' model and the relationship. Closed
    after."""
    rel = RelationshipId(relationship)
    with Store(db) as store:
        async with httpx.AsyncClient() as client:
            sink = spend_sink(store, rel)
            judges = MeteredExtractor(extractor(client, Settings.from_env()), sink, "command")
            yield Services(store, judges, rel, client)


async def run(db: Path, relationship: str, job: Callable[[Services], Awaitable[str]]) -> str:
    """Open the store and the judges' model, run one command's job, and close them."""
    async with _services(db, relationship) as x:
        return await job(x)


async def memory_pass_now(db: Path, relationship: str, *, from_start: bool = False) -> str:
    """Drain the memory pass's backlog, one batch at a time, the pass the bot runs when it is idle
    (`compose.pass_options`). For `companion memory-pass`.

    `from_start` re-reads everything, for after the extraction prompt improves. Claims already
    recorded are skipped as already known, so it only adds what was missed.
    """
    lines: list[str] = []
    s = Settings.from_env()
    async with _services(db, relationship) as x:
        character = chosen(s.character, sheets_dir(db.parent))  # the data folder holds the db
        options = pass_options(
            s,
            x.judge,
            embedder(x.client, x.store, x.rel, s),
            character.sheet if character is not None else "",
        )
        start = None if from_start else x.store.pass_cursor(x.rel)
        while True:
            result = await memory_pass_from(x.store, x.judge, x.rel, start, options)
            if not result.ran:
                break
            start = result.upto
            lines.append(result.summary())
    return "\n".join(lines or ["nothing new to read"]) + "\n"


async def rebuild_now(db: Path, relationship: str) -> str:
    async with _services(db, relationship) as x:
        return await rebuild(x.store, x.judge, x.rel) + "\n"
