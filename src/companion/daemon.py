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

from companion import logsetup
from companion.core.ack import ReactAndReply, Reaction
from companion.core.clock import local_zone, utc_now
from companion.core.extractor import Extractor
from companion.core.flags import parse_flag
from companion.core.pace import DEFAULT_PACE, PACES, pace_factor
from companion.core.prompt.prefix import build_prefix
from companion.core.spend import MeteredExtractor, MeteredTalker, SpendEvent
from companion.core.talker import Talker
from companion.core.types import Favorite, FavoriteId, Flag, FlagId, RelationshipId, SessionId
from companion.io.telegram import Commands, Hooks, Telegram
from companion.loops.curate import rebuild, retire_implicated_views
from companion.loops.fast import Conversation
from companion.loops.openloops import Ticker, drafter, tick
from companion.loops.slow import reflect_from, reflect_once
from companion.loops.spendcap import over_cap
from companion.loops.views import views_implicated
from companion.models import anthropic, openrouter
from companion.models.retry import retry_on_network_error
from companion.store.sqlite.store import Store

PERSONA = "v26.md"
FLAG_REACTION = "✍"
FAVORITE_REACTION = "❤"
REFLECT_MODEL = "anthropic/claude-haiku-5.5"
SCENE_MODEL = "deepseek/deepseek-v4-flash"
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


def split_on() -> bool:
    """Whether long replies may be sent as several messages: COMPANION_SPLIT, on unless off."""
    return os.environ.get("COMPANION_SPLIT", "").strip().lower() not in ("off", "0", "no", "false")


def pace_setting() -> float:
    return pace_factor(pace_name())


def cap_text(cap: float | None) -> str:
    return "off" if cap is None else f"${cap:.2f}"


def startup_line(rel: RelationshipId, prefix_sha: str, scene: Talker | None) -> str:
    """The line that says what is running: persona, prefix hash and which models talk."""
    if model := os.environ.get("COMPANION_MODEL"):
        everyday = model
    elif os.environ.get("OPENROUTER_API_KEY"):
        everyday = openrouter.DEFAULT_MODEL
    else:
        everyday = anthropic.DEFAULT_MODEL
    scenes = (
        "the same model" if scene is None else os.environ.get("COMPANION_SCENE_MODEL", SCENE_MODEL)
    )
    persona = PERSONA.removesuffix(".md")
    return (
        f"up as {rel} | persona {persona} (prefix {prefix_sha[:12]}) | everyday {everyday}"
        f" | scenes {scenes} | daily cap {cap_text(daily_cap())} | pace {pace_name()}"
        f" | split {'on' if split_on() else 'off'} | initiative {initiative_mode()}"
    )


def _scene_talker(client: httpx.AsyncClient) -> Talker | None:
    """The model that answers while a pretend scene is in progress. Set COMPANION_SCENE_MODEL to
    `none` to use the everyday model for scenes too. Scenes need OpenRouter."""
    model = os.environ.get("COMPANION_SCENE_MODEL", SCENE_MODEL)
    key = os.environ.get("OPENROUTER_API_KEY")
    if model.lower() == "none" or not key:
        return None
    return openrouter.OpenRouterTalker(key, client, model)


def _metered_models(
    client: httpx.AsyncClient, store: Store, rel: RelationshipId
) -> tuple[Talker, Talker | None, Extractor, Extractor]:
    """The talkers and extractors, each reporting what its calls cost to the spend ledger."""

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, datetime.now(UTC))

    scene = _scene_talker(client)
    shared = extractor(client)
    return (
        MeteredTalker(_talker(client), sink, "talker"),
        MeteredTalker(scene, sink, "scene talker") if scene is not None else None,
        MeteredExtractor(shared, sink, "judge"),
        MeteredExtractor(shared, sink, "memory"),
    )


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
    store = Store(data_dir / f"{rel}.sqlite")
    persona = resources.files("companion.persona").joinpath(PERSONA).read_text(encoding="utf-8")
    prefix = build_prefix(persona)
    async with httpx.AsyncClient() as client:
        talker, scene, judge, reflector = _metered_models(client, store, rel)
        convo = Conversation(
            store, talker, prefix, rel, judge=judge, scene_talker=scene, daily_cap_usd=daily_cap()
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

        logging.getLogger("companion").info(startup_line(rel, prefix.sha256, convo.scene_talker))
        logging.getLogger("companion").info("full log: %s", log_file)
        initiative = _start_initiative(store, rel, judge)
        try:
            await tg.run(handle, _commands(store, rel, reflector))
        finally:
            if initiative is not None:
                initiative.cancel()


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
