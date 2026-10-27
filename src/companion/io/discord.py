"""Discord as a transport for `io/surface.py`. discord.py owns the gateway, its heartbeats and
reconnects, and the REST rate limits. Only direct messages from the one allowed user come in; guild
messages, anyone else's and the bot's own are ignored. It asks for the DM messages intent alone:
Discord sends the text of a DM to the bot without the privileged message content intent. Errors
name what failed and its status, never the token."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import NoReturn

import aiohttp
import discord

from companion.core.turn.quoted import Quoted
from companion.core.types import Speaker
from companion.io.discord_commands import command_tree, sync
from companion.io.surface import Commands, DeliveryError, Incoming

log = logging.getLogger("companion.discord")
TYPING_SECONDS = 2.0  # a typing indicator stuck behind a rate limit is skipped, never waited on
_FAILURES = (
    discord.DiscordException,
    aiohttp.ClientError,
    OSError,
    TimeoutError,
)


def _not_the_guilds_warning(record: logging.LogRecord) -> bool:
    """discord.py warns at every start that the guilds intent is off. It is off on purpose: this
    transport only takes direct messages, which need no guild state."""
    return not record.getMessage().startswith("Guilds intent seems to be disabled")


class DiscordError(DeliveryError):
    """A Discord call failed. The message names the call and the status, never the token."""


def _failed(call: str, err: BaseException) -> str:
    """What failed, by its status or the error's kind; never the error's own text."""
    status = getattr(err, "status", None)
    detail = f"status {status}" if isinstance(status, int) else type(err).__name__
    return f"discord {call} failed: {detail}"


class Discord:
    limit = 2000  # Discord refuses a longer message

    def __init__(self, client: discord.Client, allowed_user: int) -> None:
        self._client = client
        self._allowed = allowed_user
        self._dm: discord.DMChannel | None = None
        self._inbox: asyncio.Queue[Incoming] | None = None
        self._early: list[discord.Message] | None = None  # live messages while catching up
        self._last: int | None = None

    async def receive(self, inbox: asyncio.Queue[Incoming], after: str | None) -> None:
        """Connect to the gateway, queue the DMs missed since message `after`, then each new one.
        A message that comes in live while the missed ones are fetched waits its turn, and an id at
        or below the last one queued is never queued again, so each is answered at most once.
        Without `after`, as on a first start, nothing old is answered."""
        self._last = int(after) if after is not None else None
        self._early = []
        gateway = asyncio.create_task(self._client.connect())
        ready = asyncio.create_task(self._client.wait_until_ready())
        try:
            await asyncio.wait({gateway, ready}, return_when=asyncio.FIRST_COMPLETED)
            if not ready.done():
                await _gateway_closed(gateway, "before it was ready")
            log.info("discord: connected")
            if self._last is not None:
                await self._catch_up(inbox, self._last)
            for message in self._early:
                self._take(message, inbox)
            self._early, self._inbox = None, inbox
            await _gateway_closed(gateway, "")
        finally:
            self._early, self._inbox = None, None
            ready.cancel()
            gateway.cancel()

    async def _catch_up(self, inbox: asyncio.Queue[Incoming], after: int) -> None:
        try:
            dm = await self._channel()
            missed = dm.history(after=discord.Object(id=after), oldest_first=True, limit=None)
            async for message in missed:
                if self._accepts(message):
                    self._take(message, inbox)
        except _FAILURES as err:
            log.warning(
                "could not fetch the messages missed while down: %s", _failed("history", err)
            )

    async def on_ready(self) -> None:
        """discord.py calls this on every new gateway session. After the first, the connection
        dropped and could not resume, so the DMs sent in between were never delivered as events:
        fetch them like the ones missed while down. A resumed session replays them itself."""
        if self._inbox is None or self._last is None:
            return
        log.info("discord: a new session after a dropped connection; fetching what was missed")
        await self._catch_up(self._inbox, self._last)

    async def on_resumed(self) -> None:
        log.info("discord: connection resumed")

    async def on_disconnect(self) -> None:
        log.info("discord: disconnected; discord.py reconnects")

    async def on_message(self, message: discord.Message) -> None:
        """discord.py calls this for every message it sees."""
        if not self._accepts(message):
            return
        if self._inbox is not None:
            self._take(message, self._inbox)
        elif self._early is not None:
            self._early.append(message)

    def _accepts(self, message: discord.Message) -> bool:
        if message.channel.type is not discord.ChannelType.private:
            return False
        me = self._client.user
        if me is not None and message.author.id == me.id:
            return False
        if message.author.id != self._allowed:
            log.warning("ignored a message from a user who is not allowed")
            return False
        return bool(message.content)

    def _take(self, message: discord.Message, inbox: asyncio.Queue[Incoming]) -> None:
        if self._last is not None and message.id <= self._last:
            return
        self._last = message.id
        ref = message.reference
        replied = str(ref.message_id) if ref is not None and ref.message_id is not None else None
        inbox.put_nowait(
            Incoming(str(message.id), message.content, str(message.id), replied, self._quoted(ref))
        )

    def _quoted(self, ref: discord.MessageReference | None) -> Quoted | None:
        """The message they replied to, as Discord sent it with theirs. A forward, or a message
        deleted or not sent along, is None."""
        if ref is None or ref.type is not discord.MessageReferenceType.reply:
            return None
        replied = ref.resolved
        if replied is None or isinstance(replied, discord.DeletedReferencedMessage):
            return None
        if not replied.content:
            return None
        me = self._client.user
        mine = me is not None and replied.author.id == me.id
        return Quoted(replied.content, Speaker.COMPANION if mine else Speaker.USER)

    async def _channel(self) -> discord.DMChannel:
        if self._dm is None:
            user = await self._client.fetch_user(self._allowed)
            self._dm = await user.create_dm()
        return self._dm

    async def send(self, text: str) -> str:
        try:
            return str((await (await self._channel()).send(text)).id)
        except _FAILURES as err:
            raise DiscordError(_failed("send", err)) from None

    async def react(self, message_id: str, emoji: str) -> None:
        try:
            dm = await self._channel()
            await dm.get_partial_message(int(message_id)).add_reaction(emoji)
        except _FAILURES as err:
            raise DiscordError(_failed("reaction", err)) from None

    async def typing(self) -> None:
        """Shows for about ten seconds. A courtesy: failing to show it must never lose the reply."""
        try:
            async with asyncio.timeout(TYPING_SECONDS):
                await (await self._channel()).typing()
        except _FAILURES as err:
            log.warning("typing indicator skipped: %s", _failed("typing", err))


async def _gateway_closed(gateway: asyncio.Task[None], when: str) -> NoReturn:
    """Wait for the gateway to end and raise why, as a `DiscordError` that names no token."""
    try:
        await gateway
    except _FAILURES as err:
        raise DiscordError(_failed("gateway", err)) from None
    msg = f"discord gateway closed {when}".strip()
    raise DiscordError(msg)


@contextlib.asynccontextmanager
async def connected(
    token: str, allowed_user: int, commands: Commands | None = None
) -> AsyncGenerator[Discord]:
    """A logged-in Discord transport. Sending works from here on; the gateway connects when the
    surface starts receiving, and closes when it stops, while replies still in progress go out.
    `commands` become Discord slash commands (`io/discord_commands.py`), synced after login."""
    intents = discord.Intents.none()
    intents.dm_messages = True
    discord.VoiceClient.warn_nacl = discord.VoiceClient.warn_dave = False  # it never joins voice
    state = logging.getLogger("discord.state")
    if _not_the_guilds_warning not in state.filters:
        state.addFilter(_not_the_guilds_warning)
    client = discord.Client(intents=intents)
    transport = Discord(client, allowed_user)
    tree = command_tree(client, allowed_user, commands) if commands else None
    for handler in (
        transport.on_message,
        transport.on_ready,
        transport.on_resumed,
        transport.on_disconnect,
    ):
        client.event(handler)
    async with client:
        try:
            await client.login(token)
        except discord.LoginFailure:
            msg = "discord login failed: the bot token was refused"
            raise DiscordError(msg) from None
        except _FAILURES as err:
            raise DiscordError(_failed("login", err)) from None
        if tree is not None:
            await sync(tree)
        yield transport
