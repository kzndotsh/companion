"""Wires the pieces together and runs the Telegram surface. Settings come from `settings.py`;
keys and tokens are read here, where the clients are made."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from companion import backups, characters, prompts
from companion.characters import Character
from companion.core.ack import ReactAndReply, Reaction
from companion.core.clock import local_zone, utc_now
from companion.core.extractor import Extractor
from companion.core.flags import parse_flag
from companion.core.prompt.prefix import build_prefix
from companion.core.spend import MeteredEmbedder, MeteredExtractor, MeteredTalker, SpendEvent
from companion.core.talker import Talker
from companion.core.types import Favorite, FavoriteId, Flag, FlagId, RelationshipId, SessionId
from companion.core.vectors import Embedder
from companion.features.consolidate.run import SameCheck
from companion.features.nudges.run import tick_nudge
from companion.features.openloops.run import Ticker, drafter, tick
from companion.features.reminders.run import deliver_due
from companion.io.telegram import Commands, Hooks, Telegram
from companion.lib import logs, retry
from companion.loops import curate
from companion.loops.conversation import Conversation
from companion.loops.spendcap import over_cap
from companion.memory.nightly import missed, night
from companion.memory.slow import reflect_once
from companion.memory.views import views_implicated
from companion.models import anthropic, embeddings, openrouter
from companion.models.fallback import RefusalFallback, TalkerFallback
from companion.settings import Settings
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

FLAG_REACTION = "✍"
FAVORITE_REACTION = "❤"
FALLBACK_MODEL = "deepseek/deepseek-v4.1-flash"  # asked only when the first model refuses
REFLECT_MODEL = "anthropic/claude-haiku-5.5"
UPDATE_KEY = "telegram.last_update_id"
REFLECT_IDLE_SECONDS = 90
REFLECT_RETRY_DELAYS = (30.0, 120.0)  # a dropped connection, not a model error
REMINDER_TICK_SECONDS = 60
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
    """The judges' and the memory pass's model, with a second model for calls the first refuses."""
    key = _need("OPENROUTER_API_KEY")
    first = openrouter.OpenRouterExtractor(
        key, client, os.environ.get("COMPANION_REFLECT_MODEL", REFLECT_MODEL)
    )
    second = os.environ.get("COMPANION_FALLBACK_MODEL", FALLBACK_MODEL)
    if second.lower() == "none":
        return first
    return RefusalFallback(first, openrouter.OpenRouterExtractor(key, client, second))


def _talker(client: httpx.AsyncClient, s: Settings) -> Talker:
    if s.openrouter:
        return openrouter.OpenRouterTalker(_need("OPENROUTER_API_KEY"), client, s.everyday_model)
    return anthropic.AnthropicTalker(_need("ANTHROPIC_API_KEY"), client, s.everyday_model)


def startup_line(
    rel: RelationshipId,
    prefix_sha: str,
    character: Character | None = None,
    settings: Settings | None = None,
) -> str:
    """The line that says what is running: persona, prefix hash, models and every setting, printed
    from the same values the bot is configured with."""
    s = settings or Settings.from_env()
    persona = prompts.get("system/persona").version
    return " | ".join(
        [
            f"up as {rel}",
            f"persona {persona} (prefix {prefix_sha[:12]})",
            f"character {character.ref if character else 'none'}",
            f"prompts {prompts.set_hash()}",
            f"everyday {s.everyday_model}",
            *s.fragments(),
        ]
    )


ROLEPLAY_MAX_TOKENS = 700  # scene replies run longer; 400 cut some off mid-sentence


def _roleplay_talker(client: httpx.AsyncClient, s: Settings) -> Talker | None:
    """The model for pretend scenes and, when allowed, intimate talk (ADR 0017). Set
    COMPANION_ROLEPLAY_MODEL to `none` to use the everyday model for those too. Needs OpenRouter."""
    if s.roleplay_model is None:
        return None
    return openrouter.OpenRouterTalker(
        _need("OPENROUTER_API_KEY"), client, s.roleplay_model, max_tokens=ROLEPLAY_MAX_TOKENS
    )


def _with_fallback(client: httpx.AsyncClient, talker: Talker, fallback: str | None) -> Talker:
    if fallback is None:
        return talker
    return TalkerFallback(
        talker, openrouter.OpenRouterTalker(_need("OPENROUTER_API_KEY"), client, fallback)
    )


def _metered_models(
    client: httpx.AsyncClient, store: Store, rel: RelationshipId, s: Settings
) -> tuple[Talker, Talker | None, Extractor, Extractor]:
    """The talkers and extractors, each reporting what its calls cost to the spend ledger. Each
    talker has a fallback: the everyday one the fallback model, the roleplay one the everyday
    model."""

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    scene = _roleplay_talker(client, s)
    shared = extractor(client)
    fallback = s.talker_fallback
    talker = _with_fallback(client, _talker(client, s), fallback)
    roleplay = (
        _with_fallback(client, scene, s.everyday_model if fallback else None) if scene else None
    )
    return (
        MeteredTalker(talker, sink, "talker"),
        MeteredTalker(roleplay, sink, "roleplay talker") if roleplay is not None else None,
        MeteredExtractor(shared, sink, "judge"),
        MeteredExtractor(shared, sink, "memory"),
    )


def _embedder(
    client: httpx.AsyncClient, store: Store, rel: RelationshipId, s: Settings
) -> Embedder | None:
    """The embedding model for the relevance look-up and its tastes, metered, or None when both
    are off."""
    if not s.openrouter or (not s.on("relevance") and not s.on("lore")):
        return None

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    key = _need("OPENROUTER_API_KEY")
    return MeteredEmbedder(embeddings.OpenRouterEmbedder(key, client, s.embed_model), sink)


def _hooks(store: Store, rel: RelationshipId) -> Hooks:
    """What the Telegram layer reports back: undelivered replies, and which updates were handled."""

    async def undelivered(text: str, reason: str, delivered: str) -> None:
        now = datetime.now(UTC)
        if delivered:
            if store.mark_partly_delivered(rel, text, delivered, reason, now) is not None:
                logging.getLogger("companion").warning(
                    "a reply was cut off; only what arrived is kept"
                )
        elif store.mark_undelivered(rel, text, reason, now) is not None:
            logging.getLogger("companion").warning("a reply never arrived and is not remembered")

    def last_handled() -> int | None:
        saved = store.setting(rel, UPDATE_KEY)
        return int(saved) if saved is not None else None

    def mark_handled(update_id: int) -> None:
        store.set_setting(rel, UPDATE_KEY, str(update_id), datetime.now(UTC))

    return Hooks(undelivered, last_handled, mark_handled)


def _commands(store: Store, rel: RelationshipId, reflector: Extractor) -> Commands:
    """The slash commands, `/flag` and `/fav`, which answer with a reaction."""

    async def flag(arg: str) -> str | Reaction | ReactAndReply:
        turn = store.latest_turn(rel)
        if turn is None:
            return "nothing to flag yet"
        kind, note = parse_flag(arg)
        store.add_flag(Flag(FlagId(uuid.uuid4().hex), rel, turn, kind, note, datetime.now(UTC)))
        logging.getLogger("companion").info("flag on turn %s (%s): %s", turn[:8], kind, note)
        implicated = await views_implicated(store, reflector, rel, turn, note)
        logging.getLogger("companion").debug("flag implicates %d view(s)", len(implicated))
        for claim in curate.retire_implicated_views(store, implicated):
            logging.getLogger("companion").info("flag retired a view: %s", claim)
        return Reaction(FLAG_REACTION)

    async def favorite(arg: str) -> str | Reaction | ReactAndReply:
        turn = store.latest_turn(rel)
        if turn is None:
            return "nothing to favorite yet"
        store.add_favorite(
            Favorite(FavoriteId(uuid.uuid4().hex), rel, turn, arg.strip(), datetime.now(UTC))
        )
        logging.getLogger("companion").info("favorite on turn %s: %s", turn[:8], arg.strip())
        return Reaction(FAVORITE_REACTION)

    return {"flag": flag, "fav": favorite, "favorite": favorite}


INITIATIVE_TICK_SECONDS = 900


NIGHTLY_HOUR = 4  # local time, when they are least likely to be chatting
CATCH_UP = timedelta(minutes=5)  # after a start, a missed night runs this much later


async def _nightly_memory(store: Store, judge: Extractor, rel: RelationshipId, s: Settings) -> None:
    """The night's memory work once a night (ADR 0019, `memory/nightly.py`), each step on its own. A
    night missed while the bot was down is made up CATCH_UP after it starts."""
    if not s.on("memory check"):
        return

    async def run() -> None:
        if over_cap(store, rel, s.daily_cap, datetime.now(UTC)) is not None:
            return
        failed = await night(store, judge, rel, local_zone(), mode=s.mode("memory check"))
        if failed:
            logging.getLogger("companion.nightly").warning("nightly: %s failed", ", ".join(failed))

    if missed(store, rel, utc_now()):
        await asyncio.sleep(CATCH_UP.total_seconds())
        await run()
    while True:
        now = utc_now().astimezone(local_zone())
        nxt = now.replace(hour=NIGHTLY_HOUR, minute=0, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        await asyncio.sleep((nxt - now).total_seconds())
        await run()


async def _daily_backups(data_dir: Path, db: Path) -> None:
    """A snapshot once a day while the bot runs, besides the one at every start."""
    while True:
        await asyncio.sleep(backups.EVERY_SECONDS)
        await asyncio.to_thread(backups.back_up_quietly, data_dir, db, "daily", utc_now())


def _start_initiative(
    store: Store, rel: RelationshipId, judge: Extractor, s: Settings
) -> asyncio.Task[None] | None:
    """The timer that looks at open loops. In shadow mode it records and sends nothing."""
    if not s.on("initiative"):
        return None
    ticker, draft = Ticker(), drafter(judge)
    log = logging.getLogger("companion.initiative")

    async def loop() -> None:
        while True:
            await asyncio.sleep(INITIATIVE_TICK_SECONDS)
            if over_cap(store, rel, s.daily_cap, datetime.now(UTC)) is not None:
                continue
            try:
                await tick(store, rel, utc_now(), local_zone(), draft, ticker)
                await tick_nudge(store, rel, utc_now(), local_zone(), judge)
            except Exception:
                log.exception("initiative tick failed; will try again next time")

    return asyncio.create_task(loop())


def _start_reminders(
    convo: Conversation, tg: Telegram, user: int, s: Settings
) -> asyncio.Task[None] | None:
    """The timer that sends reminders when they fall due (J50)."""
    if not s.on("reminders"):
        return None
    started, log = utc_now(), logging.getLogger("companion.reminders")

    async def send(text: str) -> None:
        await tg.send(user, text)

    async def loop() -> None:
        while True:
            await asyncio.sleep(REMINDER_TICK_SECONDS)
            try:
                await deliver_due(convo, send, SESSION, utc_now(), started)
            except Exception:
                log.exception("reminder tick failed; will try again next time")

    return asyncio.create_task(loop())


async def run(data_dir: Path) -> None:
    load_dotenv(Path(".env"))
    s = Settings.from_env()
    log_file = logs.configure(data_dir / "logs")
    token, user = _need("TELEGRAM_BOT_TOKEN"), int(_need("TELEGRAM_USER_ID"))
    rel = RelationshipId(f"telegram-{user}")
    db = data_dir / f"{rel}.sqlite"
    backups.back_up_quietly(data_dir, db, "start", utc_now())  # before any migration runs
    store = Store(db)
    character = characters.chosen(data_dir / "characters")
    prefix = build_prefix(characters.system_prompt(prompts.get("system/persona").raw, character))
    roleplay_prefix = build_prefix(
        characters.system_prompt(prompts.get("system/persona").raw, character, roleplay=True)
    )
    async with httpx.AsyncClient() as client:
        talker, scene, judge, reflector = _metered_models(client, store, rel, s)
        convo = Conversation(
            store,
            talker,
            prefix,
            rel,
            judge=judge,
            roleplay_talker=scene,
            daily_cap_usd=s.daily_cap,
            listen=s.on("listen"),
            mood=s.mode("mood"),
            resample=s.on("resample"),
            route_intimate=s.on("intimate"),
            roleplay_prefix=roleplay_prefix,
            scene_reminder=character.scene_reminder if character is not None else "",
            embedder=_embedder(client, store, rel, s),
            embed_model=s.embed_model,
            lore=s.mode("lore"),
            relevance=s.mode("relevance"),
            reminders=s.on("reminders"),
            episodes=s.mode("episodes"),
        )
        same = (
            SameCheck(reflector, convo.embedder, convo.embed_model, s.mode("memory check"))
            if convo.embedder is not None and s.on("memory check")
            else None
        )
        pending: list[asyncio.Task[None]] = []

        async def reflect_after_idle() -> None:
            await asyncio.sleep(REFLECT_IDLE_SECONDS)
            logging.getLogger("companion.slow").debug(
                "idle for %ds; reading what has not been read", REFLECT_IDLE_SECONDS
            )
            if over_cap(store, rel, s.daily_cap, datetime.now(UTC)) is not None:
                logging.getLogger("companion.slow").warning("daily spend cap reached; no reflect")
                return
            try:
                result = await retry.retry_on_network_error(
                    lambda: reflect_once(
                        store, reflector, rel, same=same, promises=s.on("promises")
                    ),
                    REFLECT_RETRY_DELAYS,
                    "reflect",
                )
            except httpx.TransportError as err:
                logging.getLogger("companion.slow").warning(
                    "reflect could not reach the model (%s); it will run after the next message",
                    type(err).__name__,
                )
                return
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

        tg = Telegram(
            token, user, client, _hooks(store, rel), pace=s.pace_factor, split=s.on("split")
        )

        async def answer(text: str) -> str | Reaction | ReactAndReply:
            reply = await handle(convo, SESSION, text, "telegram")
            schedule_reflect()
            return reply

        logging.getLogger("companion").info(startup_line(rel, prefix.sha256, character, s))
        logging.getLogger("companion").info("full log: %s", log_file)
        background = [
            task
            for task in (
                _start_initiative(store, rel, judge, s),
                _start_reminders(convo, tg, user, s),
                asyncio.create_task(_daily_backups(data_dir, db)),
                asyncio.create_task(_nightly_memory(store, reflector, rel, s)),
            )
            if task is not None
        ]
        try:
            await tg.run(answer, _commands(store, rel, reflector))
        finally:
            for task in background:
                task.cancel()
