"""Wires the pieces together and runs on the platform `COMPANION_PLATFORM` names, Telegram or
Discord. Either way it is one relationship and one database. Settings come from `settings.py` and
the pieces are built by `compose.py`; the platform's own token is read here."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator

import httpx

from companion import backups, characters, compose, prompts
from companion.background import jobs
from companion.chat_commands import chat_commands
from companion.compose import models, need
from companion.core import switch as sw
from companion.core.clock import utc_now
from companion.core.prompt.prefix import build_prefix
from companion.core.turn.reply import ReactAndReply, Reaction, ThenSend
from companion.core.types import RelationshipId
from companion.io import discord
from companion.io.delivery import Commands, Delivery, Hooks, Incoming
from companion.io.stop import until_stopped
from companion.io.telegram import Telegram
from companion.kit.ask import check_routes
from companion.kit.features import Outlet
from companion.kit.jobs import keep_running
from companion.lib import logs
from companion.memory.idle import IdlePass
from companion.paths import Paths
from companion.settings import Settings
from companion.startup import startup_lines
from companion.store.sqlite.store import FIRST_RELATIONSHIP, Store, relationship_in
from companion.turn.fast import handle

UPDATE_KEY = "telegram.last_update_id"
DISCORD_KEY = "discord.last_message_id"
COMMANDS_KEY = "discord.commands_synced"  # the fingerprint of the slash commands Discord has


def delivery_hooks(store: Store, rel: RelationshipId, key: str, platform: str) -> Hooks:
    """What delivery reports back: undelivered replies, which messages were handled, kept under
    the store setting `key`, and the id of each message that carried a reply, kept with its turn."""

    async def undelivered(text: str, reason: str, delivered: str) -> None:
        now = utc_now()
        if delivered:
            if store.mark_partly_delivered(rel, text, delivered, reason, now) is not None:
                logging.getLogger("companion").warning(
                    "a reply was cut off; only what arrived is kept"
                )
        elif store.mark_undelivered(rel, text, reason, now) is not None:
            logging.getLogger("companion").warning("a reply never arrived and is not remembered")

    def last_handled() -> str | None:
        return store.setting(rel, key)

    def mark_handled(cursor: str) -> None:
        store.set_setting(rel, key, cursor, utc_now())

    def sent(message_id: str) -> None:
        turn = store.latest_turn(rel)  # the reply going out was stored as the latest turn
        if turn is not None:
            store.record_message(rel, platform, message_id, turn, utc_now(), sent=True)

    return Hooks(undelivered, last_handled, mark_handled, sent)


@contextlib.asynccontextmanager
async def _delivery(
    s: Settings, client: httpx.AsyncClient, store: Store, rel: RelationshipId, commands: Commands
) -> AsyncGenerator[Delivery]:
    """Delivery on the platform `COMPANION_PLATFORM` names, ready to send, with its own resume
    point. On Discord the commands are slash commands too."""
    if s.value(sw.PLATFORM) == "discord":
        token, user = need("DISCORD_BOT_TOKEN"), int(need("DISCORD_USER_ID"))
        synced = discord.Synced(
            lambda: store.setting(rel, COMMANDS_KEY),
            lambda value: store.set_setting(rel, COMMANDS_KEY, value, utc_now()),
        )
        async with discord.connected(token, user, commands, synced) as transport:
            hooks = delivery_hooks(store, rel, DISCORD_KEY, "discord")
            yield Delivery(transport, hooks, s.pace_factor, s.on(sw.SPLIT))
        return
    telegram = Telegram(need("TELEGRAM_BOT_TOKEN"), int(need("TELEGRAM_USER_ID")), client)
    hooks = delivery_hooks(store, rel, UPDATE_KEY, "telegram")
    yield Delivery(telegram, hooks, s.pace_factor, s.on(sw.SPLIT))


async def run(paths: Paths) -> None:
    s = Settings.from_env()
    check_routes(s.judge_routes)
    log_file = logs.configure(paths.logs)
    rel = relationship_in(paths.db) or FIRST_RELATIONSHIP
    into = paths.backups(s.backup_dir)
    backups.back_up_quietly(paths, "start", utc_now(), into)  # before any migration runs
    character = characters.chosen(s.character, characters.sheets_dir(paths.data))
    persona = prompts.get("system/persona").raw
    prefix = build_prefix(characters.system_prompt(persona, character))
    roleplay_prefix = build_prefix(characters.system_prompt(persona, character, roleplay=True))
    with Store(paths.db) as store:
        async with contextlib.AsyncExitStack() as stack:
            client = await stack.enter_async_context(httpx.AsyncClient())
            m = models(client, store, rel, s)
            runtime = compose.runtime(
                s,
                store,
                m.talker,
                prefix,
                rel,
                judge=m.judge,
                memory=m.memory,
                roleplay_talker=m.roleplay,
                roleplay_prefix=roleplay_prefix,
                embedder=m.embedder,
                scene_reminder=character.scene_reminder if character is not None else "",
                serious_message=character.serious if character is not None else "",
            )
            idle = IdlePass(
                store,
                m.memory,
                rel,
                compose.pass_options(
                    s, m.memory, m.embedder, character.sheet if character is not None else ""
                ),
                s.daily_cap,
            )
            commands = chat_commands(store, rel, m.memory, s)
            delivery = await stack.enter_async_context(_delivery(s, client, store, rel, commands))

            async def answer(msg: Incoming) -> str | Reaction | ReactAndReply | ThenSend:
                reply = await handle(
                    runtime,
                    msg.text,
                    s.value(sw.PLATFORM),
                    quoted=msg.quoted,
                    message_id=msg.id,
                )
                idle.schedule()
                return reply

            logging.getLogger("companion").info(
                "\n".join(startup_lines(paths.db.stem, prefix.sha256, character, s))
            )
            logging.getLogger("companion").info("full log: %s", log_file)
            outlet = Outlet(delivery.transport.send, s.value(sw.PLATFORM))
            background = [
                asyncio.create_task(keep_running(runtime, job))
                for job in jobs(runtime, outlet, paths, into)
            ]
            try:
                await until_stopped(lambda stop: delivery.run(answer, commands, stop))
            finally:
                for task in background:
                    task.cancel()
                idle.cancel()  # a memory pass waiting to run stops too
