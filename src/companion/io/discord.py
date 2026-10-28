"""Discord as a transport for `io/delivery.py`. discord.py owns the gateway, its heartbeats and
reconnects, and the REST rate limits. Only direct messages from the one allowed user come in; guild
messages, anyone else's and the bot's own are ignored. It asks for the DM messages intent alone:
Discord sends the text of a DM to the bot without the privileged message content intent. Errors
name what failed and its status, never the token.

`/flag`, `/fav` and `/mode` are also Discord's own slash commands, with Flag this and Favorite this
on a message's Apps menu: typed as text, a command name another app also uses brings up that app's
command. They run the same handlers as the text commands (`daemon.chat_commands`), answer only the
allowed user, and answer privately, never as part of the chat."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any, NoReturn

import aiohttp
import discord
from discord import app_commands

from companion.core.turn.ack import ReactAndReply, Reaction
from companion.core.turn.quoted import Quoted
from companion.core.types import Speaker
from companion.io.delivery import Commands, DeliveryError, Incoming

log = logging.getLogger("companion.discord")
TYPING_SECONDS = 2.0  # a typing indicator stuck behind a rate limit is skipped, never waited on
NOTE_CHARS = 500  # a note on a mark is a line or two
NOT_YOURS = "these commands are only for the person this bot talks to"
FAILED = "that didn't work, try again in a bit"
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


def said(answer: str | Reaction | ReactAndReply) -> str:
    """A command's answer as the text of a private reply: a reaction becomes its emoji."""
    if isinstance(answer, Reaction):
        return answer.emoji
    if isinstance(answer, ReactAndReply):
        return f"{answer.reaction.emoji} {answer.text}"
    return answer or "done"


async def run_command(commands: Commands, name: str, note: str, message_id: str | None) -> str:
    """Run one command by name. A failure is logged and answered, never raised to discord.py."""
    try:
        return said(await commands[name](note, message_id))
    except Exception:
        log.exception("command /%s failed", name)
        return FAILED


@dataclass(frozen=True, slots=True)
class _Marks:
    """Who may use the commands, and what they run."""

    allowed: int
    commands: Commands

    async def answer(
        self, interaction: discord.Interaction, name: str, note: str, message_id: str | None
    ) -> None:
        if interaction.user.id != self.allowed:
            await interaction.response.send_message(NOT_YOURS, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)  # /flag may ask a judge
        reply = await run_command(self.commands, name, note[:NOTE_CHARS], message_id)
        await interaction.followup.send(reply, ephemeral=True)


@dataclass(frozen=True, slots=True)
class _Menu:
    """A mark on a message's Apps menu: the command it runs, its name there, the note's prompt."""

    command: str
    title: str
    label: str


class _Note(discord.ui.Modal):
    """The optional note for a mark made from a message's Apps menu."""

    def __init__(self, marks: _Marks, menu: _Menu, message_id: str) -> None:
        super().__init__(title=menu.title)
        self.note: discord.ui.TextInput[_Note] = discord.ui.TextInput(
            label=menu.label,
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=NOTE_CHARS,
        )
        self.add_item(self.note)
        self._marks, self._command, self._id = marks, menu.command, message_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._marks.answer(interaction, self._command, self.note.value, self._id)


def command_tree(
    client: discord.Client, allowed: int, commands: Commands
) -> app_commands.CommandTree:
    """The commands, usable in a DM with the bot, whether it was added to a server or to an
    account. Discord learns of them when the tree is synced after login."""
    tree = app_commands.CommandTree(client)
    marks = _Marks(allowed, commands)
    where = app_commands.AppCommandContext(guild=False, dm_channel=True, private_channel=False)
    installs = app_commands.AppInstallationType(guild=True, user=True)

    def mark(name: str, description: str) -> app_commands.Command[Any, ..., None]:
        @app_commands.describe(note="what about it, in a few words (optional)")
        async def run(interaction: discord.Interaction, note: str = "") -> None:
            await marks.answer(interaction, name, note, None)

        return app_commands.Command(
            name=name,
            description=description,
            callback=run,
            allowed_contexts=where,
            allowed_installs=installs,
        )

    async def mode(interaction: discord.Interaction) -> None:
        await marks.answer(interaction, "mode", "", None)

    def on_message(menu: _Menu) -> app_commands.ContextMenu:
        async def run(interaction: discord.Interaction, message: discord.Message) -> None:
            if interaction.user.id != allowed:
                await interaction.response.send_message(NOT_YOURS, ephemeral=True)
                return
            await interaction.response.send_modal(_Note(marks, menu, str(message.id)))

        return app_commands.ContextMenu(
            name=menu.title, callback=run, allowed_contexts=where, allowed_installs=installs
        )

    tree.add_command(mark("flag", "Mark the last reply as off"))
    tree.add_command(mark("fav", "Mark the last reply as one you loved"))
    tree.add_command(
        app_commands.Command(
            name="mode",
            description="Which model is talking now",
            callback=mode,
            allowed_contexts=where,
            allowed_installs=installs,
        )
    )
    tree.add_command(on_message(_Menu("flag", "Flag this", "What feels off? (optional)")))
    tree.add_command(on_message(_Menu("fav", "Favorite this", "What did you love? (optional)")))
    return tree


@dataclass(frozen=True, slots=True)
class Synced:
    """Where the fingerprint of the commands last synced is kept. Discord rate limits its command
    endpoint without saying how, and day-long lockouts are reported, so it is told only of a
    change, never at every start."""

    last: Callable[[], str | None]
    mark: Callable[[str], None]


def fingerprint(tree: app_commands.CommandTree, application_id: int | None) -> str:
    """Everything a sync sends, for this application, as one hash."""
    sent = [c.to_dict(tree) for c in tree.get_commands()]
    payload = json.dumps([application_id, sent], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


async def sync(tree: app_commands.CommandTree, synced: Synced | None = None) -> None:
    """Tell Discord the commands when they changed. On a failure the old ones stay and the text
    commands still work, and the next start tries again."""
    now = fingerprint(tree, tree.client.application_id)
    if synced is not None and synced.last() == now:
        log.debug("discord: commands unchanged; not synced")
        return
    try:
        sent = await tree.sync()
    except (discord.DiscordException, OSError) as err:
        status = getattr(err, "status", None)
        log.warning("discord: slash commands not synced (%s)", status or type(err).__name__)
        return
    if synced is not None:
        synced.mark(now)
    log.info("discord: %d commands synced", len(sent))


@contextlib.asynccontextmanager
async def connected(
    token: str, allowed_user: int, commands: Commands | None = None, synced: Synced | None = None
) -> AsyncGenerator[Discord]:
    """A logged-in Discord transport. Sending works from here on; the gateway connects when the
    delivery starts receiving, and closes when it stops, while replies still in progress go out.
    `commands` become Discord slash commands, synced after login when they changed."""
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
            await sync(tree, synced)
        yield transport
