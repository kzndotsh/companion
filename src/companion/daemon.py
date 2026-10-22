"""Wires the pieces together and runs the Telegram surface. Settings come from `settings.py`;
keys and tokens are read here, where the clients are made."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from companion import backups, characters, logsetup, prompts
from companion.characters import Character
from companion.core.ack import ReactAndReply, Reaction
from companion.core.callbacks import report
from companion.core.clock import local_zone, utc_now
from companion.core.extractor import Extractor
from companion.core.flags import parse_flag
from companion.core.invented import report as invented_report
from companion.core.prompt.prefix import build_prefix
from companion.core.relevance import Embedder
from companion.core.spend import MeteredEmbedder, MeteredExtractor, MeteredTalker, SpendEvent
from companion.core.talker import Talker
from companion.core.types import Favorite, FavoriteId, Flag, FlagId, RelationshipId, SessionId
from companion.io.telegram import Commands, Hooks, Telegram
from companion.loops import merging
from companion.loops.callbacks import check_new
from companion.loops.consolidate import SameCheck, nightly
from companion.loops.context import write_missing
from companion.loops.curate import rebuild, retire_implicated_views
from companion.loops.episodes import write_closed
from companion.loops.fast import Conversation
from companion.loops.invented import check_new as check_invented
from companion.loops.knowing import label_new
from companion.loops.lore import label_views
from companion.loops.names import read_names
from companion.loops.nudges import tick_nudge
from companion.loops.openloops import Ticker, drafter, tick
from companion.loops.reminders import deliver_due
from companion.loops.slow import reflect_from, reflect_once
from companion.loops.spendcap import over_cap
from companion.loops.views import views_implicated
from companion.loops.worth import expire_routine, label
from companion.models import anthropic, embeddings, openrouter
from companion.models.fallback import RefusalFallback, TalkerFallback
from companion.models.retry import retry_on_network_error
from companion.settings import Settings
from companion.store.sqlite.store import Store

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

    async def undelivered(text: str, reason: str) -> None:
        if store.mark_undelivered(rel, text, reason, datetime.now(UTC)) is not None:
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
        logging.getLogger("companion").info("favorite on turn %s: %s", turn[:8], arg.strip())
        return Reaction(FAVORITE_REACTION)

    return {"flag": flag, "fav": favorite, "favorite": favorite}


INITIATIVE_TICK_SECONDS = 900


NIGHTLY_HOUR = 4  # local time, when they are least likely to be chatting


async def _nightly_memory(store: Store, judge: Extractor, rel: RelationshipId, s: Settings) -> None:
    """The memory check once a night (ADR 0019). A failure is logged and tried the next night."""
    if not s.on("memory check"):
        return
    while True:
        now = utc_now().astimezone(local_zone())
        nxt = now.replace(hour=NIGHTLY_HOUR, minute=0, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        await asyncio.sleep((nxt - now).total_seconds())
        if over_cap(store, rel, s.daily_cap, datetime.now(UTC)) is not None:
            continue
        try:
            await nightly(store, judge, rel, utc_now(), local_zone(), mode=s.mode("memory check"))
            await merging.recent(store, judge, rel, utc_now(), local_zone())
            expire_routine(store, rel, utc_now())
            await write_closed(store, judge, rel, utc_now())
        except Exception:
            logging.getLogger("companion.consolidate").exception("memory check failed")


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
    log_file = logsetup.configure(data_dir / "logs")
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
                result = await retry_on_network_error(
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

        async def handle(text: str) -> str | Reaction | ReactAndReply:
            reply = await convo.handle(SESSION, text, "telegram")
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
            await tg.run(handle, _commands(store, rel, reflector))
        finally:
            for task in background:
                task.cancel()


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
