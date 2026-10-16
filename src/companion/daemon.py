"""Wires the pieces together and runs the Telegram surface. The only module that reads the env."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import httpx

from companion.core.ack import ReactAndReply, Reaction
from companion.core.extractor import Extractor
from companion.core.flags import parse_flag
from companion.core.prompt.prefix import build_prefix
from companion.core.talker import Talker
from companion.core.types import Favorite, FavoriteId, Flag, FlagId, RelationshipId, SessionId
from companion.io.telegram import Telegram
from companion.loops.curate import rebuild, retire_implicated_views
from companion.loops.fast import Conversation
from companion.loops.slow import reflect_from, reflect_once
from companion.loops.views import views_implicated
from companion.models import anthropic, openrouter
from companion.store.sqlite.store import Store

PERSONA = "v17.md"
FLAG_REACTION = "✍"
FAVORITE_REACTION = "❤"
REFLECT_MODEL = "anthropic/claude-haiku-5.5"
SCENE_MODEL = "deepseek/deepseek-v4-flash"
REFLECT_IDLE_SECONDS = 90
SESSION = SessionId("main")  # one continuous conversation per relationship, see ADR 0005


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        msg = f"{name} is not set (put it in .env)"
        raise SystemExit(msg)
    return value


def extractor(client: httpx.AsyncClient) -> Extractor:
    key = _need("OPENROUTER_API_KEY")
    return openrouter.OpenRouterExtractor(
        key, client, os.environ.get("COMPANION_REFLECT_MODEL", REFLECT_MODEL)
    )


def _talker(client: httpx.AsyncClient) -> Talker:
    model = os.environ.get("COMPANION_MODEL")
    if key := os.environ.get("OPENROUTER_API_KEY"):
        return openrouter.OpenRouterTalker(key, client, model or openrouter.DEFAULT_MODEL)
    key = _need("ANTHROPIC_API_KEY")
    return anthropic.AnthropicTalker(key, client, model or anthropic.DEFAULT_MODEL)


def _scene_talker(client: httpx.AsyncClient) -> Talker | None:
    """The model that answers while a pretend scene is in progress. Set COMPANION_SCENE_MODEL to
    `none` to use the everyday model for scenes too. Scenes need OpenRouter."""
    model = os.environ.get("COMPANION_SCENE_MODEL", SCENE_MODEL)
    key = os.environ.get("OPENROUTER_API_KEY")
    if model.lower() == "none" or not key:
        return None
    return openrouter.OpenRouterTalker(key, client, model)


async def run(data_dir: Path) -> None:
    logging.basicConfig(level=logging.INFO)
    # httpx logs full request URLs at INFO, and Telegram puts the bot token in the URL.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv(Path(".env"))
    token, user = _need("TELEGRAM_BOT_TOKEN"), int(_need("TELEGRAM_USER_ID"))
    rel = RelationshipId(f"telegram-{user}")
    store = Store(data_dir / f"{rel}.sqlite")
    persona = resources.files("companion.persona").joinpath(PERSONA).read_text(encoding="utf-8")
    prefix = build_prefix(persona)
    async with httpx.AsyncClient() as client:
        talker = _talker(client)
        reflector = extractor(client)
        convo = Conversation(
            store, talker, prefix, rel, judge=reflector, scene_talker=_scene_talker(client)
        )
        pending: list[asyncio.Task[None]] = []

        async def reflect_after_idle() -> None:
            await asyncio.sleep(REFLECT_IDLE_SECONDS)
            try:
                result = await reflect_once(store, reflector, rel)
            except Exception:
                logging.getLogger("companion.slow").exception("reflect failed, will retry")
                return
            if result.ran:
                logging.getLogger("companion.slow").info(
                    "reflect: +%d beliefs, %d confirmed, %d rejected, %d duplicates;"
                    " views +%d, %d confirmed, %d rejected, %d checked (%d conflict); $%.5f",
                    result.accepted,
                    result.confirmed,
                    result.rejected,
                    result.duplicates,
                    result.views_accepted,
                    result.views_confirmed,
                    result.views_rejected,
                    result.views_checked,
                    result.views_conflicts,
                    result.cost_usd,
                )

        def schedule_reflect() -> None:
            for task in pending:
                task.cancel()
            pending[:] = [asyncio.create_task(reflect_after_idle())]

        async def undelivered(text: str, reason: str) -> None:
            if store.mark_undelivered(rel, text, reason, datetime.now(UTC)) is not None:
                logging.getLogger("companion").warning(
                    "a reply never arrived and is not remembered"
                )

        tg = Telegram(token, user, client, on_undelivered=undelivered)

        async def handle(text: str) -> str | Reaction | ReactAndReply:
            reply = await convo.handle(SESSION, text, "telegram")
            schedule_reflect()
            return reply

        async def flag(arg: str) -> str | Reaction | ReactAndReply:
            turn = store.latest_turn(rel)
            if turn is None:
                return "nothing to flag yet"
            kind, note = parse_flag(arg)
            store.add_flag(Flag(FlagId(uuid.uuid4().hex), rel, turn, kind, note, datetime.now(UTC)))
            implicated = await views_implicated(store, reflector, rel, turn, note)
            for claim in retire_implicated_views(store, implicated):
                logging.getLogger("companion").info("flag retired a view: %s", claim)
            return Reaction(FLAG_REACTION)

        async def favorite(arg: str) -> str | Reaction | ReactAndReply:
            turn = store.latest_turn(rel)
            if turn is None:
                return "nothing to favorite yet"
            store.add_favorite(
                Favorite(FavoriteId(uuid.uuid4().hex), rel, turn, arg.strip(), datetime.now(UTC))
            )
            return Reaction(FAVORITE_REACTION)

        logging.getLogger("companion").info(
            "up as %s, prefix %s, scenes by %s",
            rel,
            prefix.sha256[:12],
            "the everyday model"
            if convo.scene_talker is None
            else os.environ.get("COMPANION_SCENE_MODEL", SCENE_MODEL),
        )
        await tg.run(handle, {"flag": flag, "fav": favorite, "favorite": favorite})


async def reflect_now(db: Path, relationship: str, *, from_start: bool = False) -> str:
    """Drain the slow loop's backlog, one batch at a time. For `companion reflect`.

    `from_start` re-reads everything, for after the extraction prompt improves. Claims already
    recorded are skipped as duplicates, so it only adds what was missed.
    """
    load_dotenv(Path(".env"))
    store = Store(db)
    rel = RelationshipId(relationship)
    lines: list[str] = []
    try:
        async with httpx.AsyncClient() as client:
            reflector = extractor(client)
            start = None if from_start else store.reflect_cursor(rel)
            while True:
                result = await reflect_from(store, reflector, rel, start)
                if not result.ran:
                    break
                start = result.upto
                lines.append(
                    f"+{result.accepted} beliefs, {result.confirmed} confirmed, "
                    f"{result.rejected} rejected, {result.duplicates} duplicates; "
                    f"views +{result.views_accepted}, {result.views_confirmed} confirmed, "
                    f"{result.views_rejected} rejected; ${result.cost_usd:.5f}"
                )
    finally:
        store.close()
    return "\n".join(lines or ["nothing new to read"]) + "\n"


async def rebuild_now(db: Path, relationship: str) -> str:
    load_dotenv(Path(".env"))
    store = Store(db)
    try:
        async with httpx.AsyncClient() as client:
            return await rebuild(store, extractor(client), RelationshipId(relationship)) + "\n"
    finally:
        store.close()
