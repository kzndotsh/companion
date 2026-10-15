"""Wires the pieces together and runs the Telegram surface. The only module that reads the env."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import httpx

from companion.core.flags import parse_flag
from companion.core.prompt.prefix import build_prefix
from companion.core.talker import Talker
from companion.core.types import Flag, FlagId, RelationshipId, SessionId
from companion.io.telegram import Telegram
from companion.loops.fast import Conversation
from companion.models import anthropic, openrouter
from companion.store.sqlite.store import Store

PERSONA = "v2.md"
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


def _talker(client: httpx.AsyncClient) -> Talker:
    model = os.environ.get("COMPANION_MODEL")
    if key := os.environ.get("OPENROUTER_API_KEY"):
        return openrouter.OpenRouterTalker(key, client, model or openrouter.DEFAULT_MODEL)
    key = _need("ANTHROPIC_API_KEY")
    return anthropic.AnthropicTalker(key, client, model or anthropic.DEFAULT_MODEL)


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
        convo = Conversation(store, talker, prefix, rel)
        tg = Telegram(token, user, client)

        async def handle(text: str) -> str:
            return await convo.handle(SESSION, text, "telegram")

        async def flag(arg: str) -> str:
            turn = store.latest_turn(rel)
            if turn is None:
                return "nothing to flag yet"
            kind, note = parse_flag(arg)
            store.add_flag(Flag(FlagId(uuid.uuid4().hex), rel, turn, kind, note, datetime.now(UTC)))
            return "noted"

        logging.getLogger("companion").info("up as %s, prefix %s", rel, prefix.sha256[:12])
        await tg.run(handle, {"flag": flag})
