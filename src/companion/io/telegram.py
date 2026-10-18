"""Telegram long polling. Answers one allowed user and ignores everyone else."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from companion.core.ack import ReactAndReply, Reaction
from companion.core.pace import hold_seconds
from companion.core.split import split_reply
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


@dataclass(slots=True)
class _Delivery:
    """How many messages of one reply have actually gone out, so a cancelled reply is only called
    undelivered when the user saw none of it."""

    sent: int = 0


class TelegramError(RuntimeError):
    """A Telegram call failed. The message names the method and status, never the URL, because the
    URL contains the bot token and logs must not."""


class Telegram:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        token: str,
        allowed_user: int,
        client: httpx.AsyncClient,
        hooks: Hooks = Hooks(),  # noqa: B008
        pace: float = 0.0,
        split: bool = False,
    ) -> None:
        self._pace = pace
        self._split = split
        self._base = f"https://api.telegram.org/bot{token}"
        self._allowed = allowed_user
        self._client = client
        self._hooks = hooks

    async def _call(self, method: str, **params: object) -> object:
        for attempt in range(2):
            began = time.perf_counter()
            try:
                resp = await self._client.post(f"{self._base}/{method}", json=params, timeout=45)
                resp.raise_for_status()
            except httpx.HTTPStatusError as err:
                status = err.response.status_code
                if status == 429 and attempt == 0:
                    wait = _retry_after(err.response)
                    log.warning(
                        "telegram %s rate limited; waiting %.1fs and retrying", method, wait
                    )
                    await asyncio.sleep(wait)
                    continue
                log.warning("telegram %s status %d: %s", method, status, err.response.text[:300])
                msg = f"telegram {method} failed with status {status}"
                raise TelegramError(msg) from None
            except httpx.HTTPError as err:
                msg = f"telegram {method} failed: {type(err).__name__}"
                raise TelegramError(msg) from None
            if method != "getUpdates":
                log.debug("telegram %s ok in %dms", method, (time.perf_counter() - began) * 1000)
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
        """Poll in the background and serve one update at a time. A new plain message that arrives
        while the previous one is still being answered replaces that answer, so a burst of
        messages gets one reply that has seen all of them."""
        last = self._hooks.last_handled() if self._hooks.last_handled else None
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        poller = asyncio.create_task(self._poll(queue, last + 1 if last is not None else 0))
        waiting: list[dict[str, object]] = []
        try:
            while True:
                update = waiting.pop(0) if waiting else await queue.get()
                await self._serve(update, queue, waiting, handle, commands or {})
        finally:
            poller.cancel()

    async def _poll(self, queue: asyncio.Queue[dict[str, object]], offset: int) -> None:
        """Fetch updates for ever and queue them. The offset moves past an update as soon as it is
        queued, so a restart can lose a message that was queued but not yet answered."""
        failures = 0
        while True:
            try:
                updates = await self._call("getUpdates", offset=offset, timeout=30)
            except TelegramError as err:
                failures += 1
                log.warning("poll failed, retrying: %s", err)
                await asyncio.sleep(3)
                continue
            if failures:
                log.info("poll recovered after %d failed attempt(s)", failures)
                failures = 0
            if seq(updates):
                log.debug("poll: %d update(s), offset %d", len(seq(updates)), offset)
            for update in seq(updates):
                u = obj(update)
                update_id = integer(u.get("update_id"))
                if update_id >= offset:
                    offset = update_id + 1
                    queue.put_nowait(u)

    def _plain_text(self, update: dict[str, object]) -> str | None:
        """The text of a message from the allowed user that is not a command, else None."""
        msg = obj(update.get("message"))
        text = msg.get("text")
        if not isinstance(text, str) or integer(obj(msg.get("from")).get("id")) != self._allowed:
            return None
        return None if _command(text) is not None else text

    async def _serve(
        self,
        update: dict[str, object],
        queue: asyncio.Queue[dict[str, object]],
        waiting: list[dict[str, object]],
        handle: Handler,
        commands: Commands,
    ) -> None:
        """Answer an update. If another plain message arrives before the answer is out and this
        one was a plain message too, drop the answer and answer the new one, which sees both."""
        current = update
        while True:
            turn = asyncio.create_task(self._handle_one(current, handle, commands))
            arrival = asyncio.create_task(queue.get())
            await asyncio.wait({turn, arrival}, return_when=asyncio.FIRST_COMPLETED)
            if turn.done():
                if arrival.done():
                    waiting.append(arrival.result())
                else:
                    arrival.cancel()
                await turn
                return
            newer = arrival.result()
            if self._plain_text(current) is None or self._plain_text(newer) is None:
                waiting.append(newer)
                await turn
                return
            log.info("a newer message arrived before the answer went out; answering both together")
            turn.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await turn
            current = newer

    async def _handle_one(
        self, update: dict[str, object], handle: Handler, commands: Commands
    ) -> None:
        update_id = integer(update.get("update_id"))
        if self._hooks.mark_handled is not None:
            self._hooks.mark_handled(update_id)
        await self.handle_update(update, handle, commands)

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
        log.debug(
            "message %d in: %d chars%s",
            message_id,
            len(text),
            f", command /{command[0]}" if command else "",
        )
        if command is not None and command[0] not in commands:
            return  # unknown and /start commands never reach the model
        started = time.monotonic()
        try:
            if command is not None:
                reply = await commands[command[0]](command[1])
            else:
                await self._typing(chat_id)
                reply = await handle(text)
        except asyncio.CancelledError:
            log.info("message %d superseded while the reply was being written", message_id)
            raise
        except Exception:
            log.exception("turn failed")
            return
        wait = (text, started) if command is None else None
        delivery = _Delivery()
        try:
            await self._answer(chat_id, message_id, reply, wait, delivery)
        except asyncio.CancelledError:
            log.info("message %d superseded; %d part(s) had gone out", message_id, delivery.sent)
            if delivery.sent == 0:
                await self._report_undelivered(reply, "superseded by a newer message")
            raise
        except TelegramError as err:
            log.warning("could not deliver the reply: %s", err)
            await self._report_undelivered(reply, str(err))
        else:
            log.info(
                "message %d answered %.1fs after it arrived (%s)",
                message_id,
                time.monotonic() - started,
                _kind(reply),
            )

    async def _hold(
        self, chat_id: int, user_text: str, reply: str, started: float, *, reading: bool = True
    ) -> None:
        """Wait like someone reading and typing, keeping the typing indicator alive while a text
        reply is on its way. The wait counts the time already spent since `started`."""
        remaining = hold_seconds(
            user_text,
            reply,
            self._pace,
            time.monotonic() - started,
            random.uniform(0.8, 1.25),  # noqa: S311
            reading,
        )
        if remaining > 0:
            log.info("holding %.1fs before sending (%d words)", remaining, len(reply.split()))
        while remaining > 0:
            if reply:
                await self._typing(chat_id)
            step = min(remaining, TYPING_REFRESH_SECONDS)
            await asyncio.sleep(step)
            remaining -= step

    async def _send_parts(
        self,
        chat_id: int,
        text: str,
        hold: Callable[..., Awaitable[None]] | None,
        delivery: _Delivery,
    ) -> None:
        """Send a reply, cut into a few messages when it is long enough, each after its own
        typing time. A part that fails after an earlier one arrived stops the rest and is logged;
        the user has already seen the start, so the reply is not reported as undelivered."""
        parts = split_reply(text, random.random(), random.random()) if self._split else [text]  # noqa: S311
        if len(parts) > 1:
            log.info(
                "splitting into %d messages (%s words)",
                len(parts),
                "+".join(str(len(p.split())) for p in parts),
            )
        for n, part in enumerate(parts):
            if hold is not None:
                await hold(part, first=n == 0)
            try:
                await self.send(chat_id, part)
                delivery.sent += 1
            except TelegramError:
                if n == 0:
                    raise
                log.warning(
                    "part %d of %d failed to send; the rest were not sent", n + 1, len(parts)
                )
                return

    async def _answer(
        self,
        chat_id: int,
        message_id: int,
        reply: str | Reaction | ReactAndReply,
        wait: tuple[str, float] | None = None,
        delivery: _Delivery | None = None,
    ) -> None:
        """Send the reply. `wait` is the user's text and when the turn started; leave it out for
        a command's reply, which goes at once."""
        delivery = delivery or _Delivery()

        async def hold(text: str, *, first: bool = True) -> None:
            if wait is None or self._pace <= 0:
                return
            if first:
                await self._hold(chat_id, wait[0], text, wait[1])
            else:
                await self._hold(chat_id, "", text, time.monotonic(), reading=False)

        if isinstance(reply, ReactAndReply):
            try:
                await self.react(chat_id, message_id, reply.reaction.emoji)
            except TelegramError:
                log.warning("reaction refused; sending the reply without it")
            if reply.text:
                await self._send_parts(chat_id, reply.text, hold, delivery)
        elif isinstance(reply, Reaction):
            await hold("")
            try:
                await self.react(chat_id, message_id, reply.emoji)
            except TelegramError:
                log.warning("reaction refused, falling back to text")
                await self.send(chat_id, "noted")
        elif reply:
            await self._send_parts(chat_id, reply, hold if wait is not None else None, delivery)

    async def _report_undelivered(self, reply: str | Reaction | ReactAndReply, reason: str) -> None:
        """Tell the conversation a reply never arrived, so the model does not think it was seen."""
        text = reply.text if isinstance(reply, ReactAndReply) else reply
        if not isinstance(text, str) or not text or self._hooks.on_undelivered is None:
            return
        try:
            await self._hooks.on_undelivered(text, reason)
        except Exception:
            log.exception("could not record an undelivered reply")


def _kind(reply: str | Reaction | ReactAndReply) -> str:
    if isinstance(reply, ReactAndReply):
        return f"reaction {reply.reaction.emoji} then {len(reply.text.split())} words"
    if isinstance(reply, Reaction):
        return f"reaction {reply.emoji}"
    return f"{len(reply.split())} words"


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
