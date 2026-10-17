"""Telegram long polling. Answers one allowed user and ignores everyone else."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from companion.core.ack import ReactAndReply, Reaction
from companion.core.pace import hold_seconds
from companion.models.wire import integer, obj, seq

log = logging.getLogger("companion.telegram")
TYPING_REFRESH_SECONDS = 4.0  # Telegram drops the typing indicator after about five


Handler = Callable[[str], Awaitable[str | Reaction | ReactAndReply]]
CommandHandler = Callable[[str], Awaitable[str | Reaction | ReactAndReply]]
Commands = dict[str, CommandHandler]
Undelivered = Callable[[str, str], Awaitable[None]]  # the reply text and why it did not arrive
LastHandled = Callable[[], int | None]  # the newest update id already handled, if any
MarkHandled = Callable[[int], None]


@dataclass(frozen=True, slots=True)
class Hooks:
    """What the daemon lets the Telegram layer tell it, and ask it. All optional."""

    on_undelivered: Undelivered | None = None
    last_handled: LastHandled | None = None
    mark_handled: MarkHandled | None = None


class TelegramError(RuntimeError):
    """A Telegram call failed. The message names the method and status, never the URL, because the
    URL contains the bot token and logs must not."""


class Telegram:
    def __init__(
        self,
        token: str,
        allowed_user: int,
        client: httpx.AsyncClient,
        hooks: Hooks = Hooks(),  # noqa: B008
        pace: float = 0.0,
    ) -> None:
        self._pace = pace
        self._base = f"https://api.telegram.org/bot{token}"
        self._allowed = allowed_user
        self._client = client
        self._hooks = hooks

    async def _call(self, method: str, **params: object) -> object:
        for attempt in range(2):
            try:
                resp = await self._client.post(f"{self._base}/{method}", json=params, timeout=45)
                resp.raise_for_status()
            except httpx.HTTPStatusError as err:
                status = err.response.status_code
                if status == 429 and attempt == 0:
                    await asyncio.sleep(_retry_after(err.response))
                    continue
                msg = f"telegram {method} failed with status {status}"
                raise TelegramError(msg) from None
            except httpx.HTTPError as err:
                msg = f"telegram {method} failed: {type(err).__name__}"
                raise TelegramError(msg) from None
            return resp.json()["result"]
        msg = f"telegram {method} failed"
        raise TelegramError(msg)

    async def send(self, chat_id: int, text: str) -> None:
        for attempt in range(2):
            try:
                await self._call("sendMessage", chat_id=chat_id, text=text)
            except TelegramError:
                if attempt == 1:
                    raise
                await asyncio.sleep(2.0)
            else:
                return

    async def react(self, chat_id: int, message_id: int, emoji: str) -> None:
        await self._call(
            "setMessageReaction",
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
        )

    async def _typing(self, chat_id: int) -> None:
        """The typing indicator is a courtesy. Failing to show it must never lose the reply."""
        try:
            await self._call("sendChatAction", chat_id=chat_id, action="typing")
        except TelegramError as err:
            log.warning("typing indicator skipped: %s", err)

    async def run(self, handle: Handler, commands: Commands | None = None) -> None:
        last = self._hooks.last_handled() if self._hooks.last_handled else None
        offset = last + 1 if last is not None else 0
        while True:
            try:
                updates = await self._call("getUpdates", offset=offset, timeout=30)
            except TelegramError as err:
                log.warning("poll failed, retrying: %s", err)
                await asyncio.sleep(3)
                continue
            offset = await self.process(seq(updates), offset, handle, commands or {})

    async def process(
        self, updates: list[object], offset: int, handle: Handler, commands: Commands
    ) -> int:
        """Handle each update once, in order, and return the next offset.

        Telegram only forgets an update when a later poll asks past it, so an update handled just
        before a restart comes back. The id is recorded before the turn runs, and an id at or below
        the recorded one is skipped: a message is answered at most once, never twice.
        """
        for update in updates:
            u = obj(update)
            update_id = integer(u.get("update_id"))
            if update_id < offset:
                continue
            offset = update_id + 1
            if self._hooks.mark_handled is not None:
                self._hooks.mark_handled(update_id)
            await self.handle_update(u, handle, commands)
        return offset

    async def handle_update(
        self, update: dict[str, object], handle: Handler, commands: Commands
    ) -> None:
        msg = obj(update.get("message"))
        text = msg.get("text")
        if not isinstance(text, str):
            return
        if integer(obj(msg.get("from")).get("id")) != self._allowed:
            log.warning("ignored a message from a user who is not allowed")
            return
        chat_id = integer(obj(msg.get("chat")).get("id"))
        message_id = integer(msg.get("message_id"))
        command = _command(text)
        if command is not None and command[0] not in commands:
            return  # unknown and /start commands never reach the model
        started = time.monotonic()
        try:
            if command is not None:
                reply = await commands[command[0]](command[1])
            else:
                await self._typing(chat_id)
                reply = await handle(text)
        except Exception:
            log.exception("turn failed")
            return
        wait = (text, started) if command is None else None
        try:
            await self._answer(chat_id, message_id, reply, wait)
        except TelegramError as err:
            log.warning("could not deliver the reply: %s", err)
            await self._report_undelivered(reply, str(err))

    async def _hold(self, chat_id: int, user_text: str, reply: str, started: float) -> None:
        """Wait like someone reading and typing, keeping the typing indicator alive while a text
        reply is on its way. The wait counts the time the model already took."""
        remaining = hold_seconds(
            user_text,
            reply,
            self._pace,
            time.monotonic() - started,
            random.uniform(0.8, 1.25),  # noqa: S311
        )
        while remaining > 0:
            if reply:
                await self._typing(chat_id)
            step = min(remaining, TYPING_REFRESH_SECONDS)
            await asyncio.sleep(step)
            remaining -= step

    async def _answer(
        self,
        chat_id: int,
        message_id: int,
        reply: str | Reaction | ReactAndReply,
        wait: tuple[str, float] | None = None,
    ) -> None:
        """Send the reply. `wait` is the user's text and when the turn started; leave it out for
        a command's reply, which goes at once."""

        async def hold(text: str) -> None:
            if wait is not None and self._pace > 0:
                await self._hold(chat_id, wait[0], text, wait[1])

        if isinstance(reply, ReactAndReply):
            try:
                await self.react(chat_id, message_id, reply.reaction.emoji)
            except TelegramError:
                log.warning("reaction refused; sending the reply without it")
            if reply.text:
                await hold(reply.text)
                await self.send(chat_id, reply.text)
        elif isinstance(reply, Reaction):
            await hold("")
            try:
                await self.react(chat_id, message_id, reply.emoji)
            except TelegramError:
                log.warning("reaction refused, falling back to text")
                await self.send(chat_id, "noted")
        elif reply:
            await hold(reply)
            await self.send(chat_id, reply)

    async def _report_undelivered(self, reply: str | Reaction | ReactAndReply, reason: str) -> None:
        """Tell the conversation a reply never arrived, so the model does not think it was seen."""
        text = reply.text if isinstance(reply, ReactAndReply) else reply
        if not isinstance(text, str) or not text or self._hooks.on_undelivered is None:
            return
        try:
            await self._hooks.on_undelivered(text, reason)
        except Exception:
            log.exception("could not record an undelivered reply")


def _retry_after(resp: httpx.Response) -> float:
    """How long Telegram asked us to wait, capped so a turn never stalls for long."""
    try:
        wait = float(resp.json()["parameters"]["retry_after"])
    except (ValueError, KeyError, TypeError):
        wait = 1.0
    return min(max(wait, 0.0), 5.0)


def _command(text: str) -> tuple[str, str] | None:
    """`/flag too long` -> ("flag", "too long"). `/flag@my_bot x` is the same command."""
    if not text.startswith("/"):
        return None
    head, _, arg = text[1:].partition(" ")
    return head.partition("@")[0].lower(), arg.strip()
