"""Wires the pieces together and runs the Telegram surface. The only module that reads the env."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
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
from companion.core.pace import DEFAULT_PACE, PACES, pace_factor
from companion.core.prompt.prefix import build_prefix
from companion.core.relevance import Embedder
from companion.core.spend import MeteredEmbedder, MeteredExtractor, MeteredTalker, SpendEvent
from companion.core.talker import Talker
from companion.core.types import Favorite, FavoriteId, Flag, FlagId, RelationshipId, SessionId
from companion.io.telegram import Commands, Hooks, Telegram
from companion.loops.callbacks import check_new
from companion.loops.curate import rebuild, retire_implicated_views
from companion.loops.fast import Conversation
from companion.loops.knowing import label_new
from companion.loops.openloops import Ticker, drafter, tick
from companion.loops.slow import reflect_from, reflect_once
from companion.loops.spendcap import over_cap
from companion.loops.views import views_implicated
from companion.models import anthropic, embeddings, openrouter
from companion.models.fallback import RefusalFallback, TalkerFallback
from companion.models.retry import retry_on_network_error
from companion.store.sqlite.store import Store

FLAG_REACTION = "✍"
FAVORITE_REACTION = "❤"
FALLBACK_MODEL = "deepseek/deepseek-v4.1-flash"  # asked only when the first model refuses
REFLECT_MODEL = "anthropic/claude-haiku-5.5"
ROLEPLAY_MODEL = "deepseek/deepseek-v4.1-flash"
UPDATE_KEY = "telegram.last_update_id"
DEFAULT_DAILY_CAP_USD = 10.0
REFLECT_IDLE_SECONDS = 90
REFLECT_RETRY_DELAYS = (30.0, 120.0)  # a dropped connection, not a model error
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


def _talker(client: httpx.AsyncClient) -> Talker:
    model = os.environ.get("COMPANION_MODEL")
    if key := os.environ.get("OPENROUTER_API_KEY"):
        return openrouter.OpenRouterTalker(key, client, model or openrouter.DEFAULT_MODEL)
    key = _need("ANTHROPIC_API_KEY")
    return anthropic.AnthropicTalker(key, client, model or anthropic.DEFAULT_MODEL)


def daily_cap() -> float | None:
    """The daily spend cap in dollars from COMPANION_DAILY_CAP_USD, or None when it is switched off.

    Unset means the default. "off", "none" or "0" turn the cap off."""
    raw = os.environ.get("COMPANION_DAILY_CAP_USD", "").strip().lower()
    if raw in ("off", "none", "0", "0.0"):
        return None
    try:
        value = float(raw) if raw else DEFAULT_DAILY_CAP_USD
    except ValueError:
        return DEFAULT_DAILY_CAP_USD
    return value if value > 0 else None


def pace_name() -> str:
    """The reply pace from COMPANION_PACE: off, quick, natural or slow. Unset means natural."""
    raw = os.environ.get("COMPANION_PACE", "").strip().lower()
    return raw if raw in PACES else DEFAULT_PACE


def initiative_mode() -> str:
    """COMPANION_INITIATIVE: `shadow` (the default) records what it would reach out about and sends
    nothing, `off` turns it off. There is no live mode yet."""
    raw = os.environ.get("COMPANION_INITIATIVE", "").strip().lower()
    return "off" if raw in ("off", "0", "no", "false") else "shadow"


def listen_on() -> bool:
    """Whether each message is read for how serious it is before the reply: COMPANION_LISTEN, on
    unless off."""
    return os.environ.get("COMPANION_LISTEN", "").strip().lower() not in ("off", "0", "no", "false")


def mood_mode() -> str:
    """COMPANION_MOOD (ADR 0016): `shadow` (the default) works the mood out and logs it without
    showing it to the model, `on` adds the mood line, `off` does neither."""
    raw = os.environ.get("COMPANION_MOOD", "").strip().lower()
    return raw if raw in ("off", "on") else "shadow"


def resample_on() -> bool:
    """Whether a reply that fails a check is drawn once more: COMPANION_RESAMPLE, on unless off."""
    return os.environ.get("COMPANION_RESAMPLE", "").strip().lower() not in (
        "off",
        "0",
        "no",
        "false",
    )


def route_intimate_on() -> bool:
    """COMPANION_ROUTE_INTIMATE (ADR 0017): `on` lets intimate talk go to the roleplay talker, above
    the floor in code; anything else keeps it on the everyday talker."""
    return os.environ.get("COMPANION_ROUTE_INTIMATE", "").strip().lower() in (
        "on",
        "1",
        "yes",
        "true",
    )


def relevance_on() -> bool:
    """Whether the relevance look-up runs in shadow (`core/relevance.py`): COMPANION_RELEVANCE,
    shadow unless off. It never reaches the talker yet."""
    return os.environ.get("COMPANION_RELEVANCE", "").strip().lower() not in (
        "off",
        "0",
        "no",
        "false",
    )


def split_on() -> bool:
    """Whether long replies may be sent as several messages: COMPANION_SPLIT, on unless off."""
    return os.environ.get("COMPANION_SPLIT", "").strip().lower() not in ("off", "0", "no", "false")


def pace_setting() -> float:
    return pace_factor(pace_name())


def cap_text(cap: float | None) -> str:
    return "off" if cap is None else f"${cap:.2f}"


def startup_line(
    rel: RelationshipId,
    prefix_sha: str,
    scene: Talker | None,
    character: Character | None = None,
) -> str:
    """The line that says what is running: persona, prefix hash and which models talk."""
    if model := os.environ.get("COMPANION_MODEL"):
        everyday = model
    elif os.environ.get("OPENROUTER_API_KEY"):
        everyday = openrouter.DEFAULT_MODEL
    else:
        everyday = anthropic.DEFAULT_MODEL
    roleplay = (
        "the same model"
        if scene is None
        else os.environ.get("COMPANION_ROLEPLAY_MODEL", ROLEPLAY_MODEL)
    )
    persona = prompts.get("system/persona").version
    return (
        f"up as {rel} | persona {persona} (prefix {prefix_sha[:12]})"
        f" | character {character.ref if character else 'none'} | prompts {prompts.set_hash()}"
        f" | everyday {everyday}"
        f" | roleplay {roleplay} | daily cap {cap_text(daily_cap())} | pace {pace_name()}"
        f" | split {'on' if split_on() else 'off'} | listen {'on' if listen_on() else 'off'}"
        f" | initiative {initiative_mode()} | mood {mood_mode()}"
        f" | resample {'on' if resample_on() else 'off'}"
        f" | intimate {'may route' if route_intimate_on() else 'stays'}"
        f" | relevance {'shadow' if relevance_on() else 'off'}"
        f" | talker fallback {talker_fallback() or 'off'}"
    )


def _roleplay_talker(client: httpx.AsyncClient) -> Talker | None:
    """The model for pretend scenes and, when allowed, intimate talk (ADR 0017). Set
    COMPANION_ROLEPLAY_MODEL to `none` to use the everyday model for those too. Needs OpenRouter."""
    model = os.environ.get("COMPANION_ROLEPLAY_MODEL", ROLEPLAY_MODEL)
    key = os.environ.get("OPENROUTER_API_KEY")
    if model.lower() == "none" or not key:
        return None
    return openrouter.OpenRouterTalker(key, client, model)


def talker_fallback() -> str | None:
    """The model that answers when the everyday talker fails or stalls (J21):
    COMPANION_TALKER_FALLBACK, by default the roleplay model; `none` turns it off. The roleplay
    talker falls back to the everyday model. Needs OpenRouter."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        return None
    model = os.environ.get("COMPANION_TALKER_FALLBACK", "").strip()
    if model.lower() == "none":
        return None
    return model or os.environ.get("COMPANION_ROLEPLAY_MODEL", ROLEPLAY_MODEL)


def _with_fallback(client: httpx.AsyncClient, talker: Talker, fallback: str | None) -> Talker:
    key = os.environ.get("OPENROUTER_API_KEY")
    if fallback is None or fallback.lower() == "none" or not key:
        return talker
    return TalkerFallback(talker, openrouter.OpenRouterTalker(key, client, fallback))


def _metered_models(
    client: httpx.AsyncClient, store: Store, rel: RelationshipId
) -> tuple[Talker, Talker | None, Extractor, Extractor]:
    """The talkers and extractors, each reporting what its calls cost to the spend ledger. Each
    talker has a fallback: the everyday one the fallback model, the roleplay one the everyday
    model."""

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    scene = _roleplay_talker(client)
    shared = extractor(client)
    fallback = talker_fallback()
    everyday = os.environ.get("COMPANION_MODEL") or openrouter.DEFAULT_MODEL
    talker = _with_fallback(client, _talker(client), fallback)
    roleplay = _with_fallback(client, scene, everyday if fallback else None) if scene else None
    return (
        MeteredTalker(talker, sink, "talker"),
        MeteredTalker(roleplay, sink, "roleplay talker") if roleplay is not None else None,
        MeteredExtractor(shared, sink, "judge"),
        MeteredExtractor(shared, sink, "memory"),
    )


def _embedder(client: httpx.AsyncClient, store: Store, rel: RelationshipId) -> Embedder | None:
    """The embedding model for the relevance look-up, metered, or None when it is off."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key or not relevance_on():
        return None

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    model = os.environ.get("COMPANION_EMBED_MODEL", embeddings.DEFAULT_MODEL)
    return MeteredEmbedder(embeddings.OpenRouterEmbedder(key, client, model), sink)


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


async def _daily_backups(data_dir: Path, db: Path) -> None:
    """A snapshot once a day while the bot runs, besides the one at every start."""
    while True:
        await asyncio.sleep(backups.EVERY_SECONDS)
        await asyncio.to_thread(backups.back_up_quietly, data_dir, db, "daily", utc_now())


def _start_initiative(
    store: Store, rel: RelationshipId, judge: Extractor
) -> asyncio.Task[None] | None:
    """The timer that looks at open loops. In shadow mode it records and sends nothing."""
    if initiative_mode() == "off":
        return None
    ticker, draft = Ticker(), drafter(judge)
    log = logging.getLogger("companion.initiative")

    async def loop() -> None:
        while True:
            await asyncio.sleep(INITIATIVE_TICK_SECONDS)
            if over_cap(store, rel, daily_cap(), datetime.now(UTC)) is not None:
                continue
            try:
                await tick(store, rel, utc_now(), local_zone(), draft, ticker)
            except Exception:
                log.exception("initiative tick failed; will try again next time")

    return asyncio.create_task(loop())


async def run(data_dir: Path) -> None:
    load_dotenv(Path(".env"))
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
        talker, scene, judge, reflector = _metered_models(client, store, rel)
        convo = Conversation(
            store,
            talker,
            prefix,
            rel,
            judge=judge,
            roleplay_talker=scene,
            daily_cap_usd=daily_cap(),
            listen=listen_on(),
            mood=mood_mode(),
            resample=resample_on(),
            route_intimate=route_intimate_on(),
            roleplay_prefix=roleplay_prefix,
            embedder=_embedder(client, store, rel),
            embed_model=os.environ.get("COMPANION_EMBED_MODEL", embeddings.DEFAULT_MODEL),
        )
        pending: list[asyncio.Task[None]] = []

        async def reflect_after_idle() -> None:
            await asyncio.sleep(REFLECT_IDLE_SECONDS)
            logging.getLogger("companion.slow").debug(
                "idle for %ds; reading what has not been read", REFLECT_IDLE_SECONDS
            )
            if over_cap(store, rel, daily_cap(), datetime.now(UTC)) is not None:
                logging.getLogger("companion.slow").warning("daily spend cap reached; no reflect")
                return
            try:
                result = await retry_on_network_error(
                    lambda: reflect_once(store, reflector, rel), REFLECT_RETRY_DELAYS, "reflect"
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
            token, user, client, _hooks(store, rel), pace=pace_setting(), split=split_on()
        )

        async def handle(text: str) -> str | Reaction | ReactAndReply:
            reply = await convo.handle(SESSION, text, "telegram")
            schedule_reflect()
            return reply

        logging.getLogger("companion").info(
            startup_line(rel, prefix.sha256, convo.roleplay_talker, character)
        )
        logging.getLogger("companion").info("full log: %s", log_file)
        initiative = _start_initiative(store, rel, judge)
        daily = asyncio.create_task(_daily_backups(data_dir, db))
        try:
            await tg.run(handle, _commands(store, rel, reflector))
        finally:
            daily.cancel()
            if initiative is not None:
                initiative.cancel()


async def callbacks_now(db: Path, relationship: str, days: int, cap_usd: float) -> str:
    """Judge recent replies for callbacks, then report. For `companion callbacks`."""
    load_dotenv(Path(".env"))
    store = Store(db)
    rel = RelationshipId(relationship)
    start = utc_now() - timedelta(days=days)
    try:
        async with httpx.AsyncClient() as client:
            judged, spent = await check_new(store, extractor(client), rel, start, cap_usd)
        verdicts = store.callback_checks_since(rel, start)
        replies = {t: store.reply_text(rel, t) for t, c in verdicts if c.callback}
    finally:
        store.close()
    shown = [(replies[t], c) for t, c in verdicts if c.callback][-8:]
    head = f"judged {judged} new replies for ${spent:.4f}\n"
    return head + report([c for _, c in verdicts], days, shown)


async def label_now(db: Path, relationship: str) -> str:
    """Label memories that have no label yet, for `companion map --label`."""
    load_dotenv(Path(".env"))
    store = Store(db)
    try:
        async with httpx.AsyncClient() as client:
            done = await label_new(
                store, extractor(client), RelationshipId(relationship), utc_now(), batches=10
            )
    finally:
        store.close()
    return f"labelled {done.labelled}, {done.left} left, ${done.cost_usd:.4f}\n"


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
