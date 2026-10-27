"""Answering one person over a chat surface, whichever it is. Telegram (`io/telegram.py`) and
Discord (`io/discord.py`) are transports: each brings in the allowed user's messages and carries out
a send, a reaction or a typing indicator. Everything about how a reply goes out is here, once: one
message answered at a time, a newer plain message replacing an answer in progress, the reading pause
and the typing, splitting, reactions, code's own message after the reply, and what never arrived."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from companion.core.turn.ack import ReactAndReply, Reaction, ThenSend
from companion.core.turn.quoted import Quoted
from companion.io.pace import hold_seconds, read_seconds
from companion.io.split import fit, split_reply
from companion.io.stop import cancel_when, next_message

log = logging.getLogger("companion.surface")
TYPING_REFRESH_SECONDS = 4.0  # both surfaces drop the typing indicator after five to ten seconds

Reply = str | Reaction | ReactAndReply | ThenSend
# The command's argument, and the id of the message it was sent as a reply to, if any.
CommandHandler = Callable[[str, str | None], Awaitable[str | Reaction | ReactAndReply]]
Commands = dict[str, CommandHandler]
# The reply text, why it did not all arrive, and the parts that did ("" when none did).
Undelivered = Callable[[str, str, str], Awaitable[None]]
LastHandled = Callable[[], str | None]  # the cursor of the newest message already handled, if any
MarkHandled = Callable[[str], None]
Sent = Callable[[str], None]  # the id of a message that carried part of a turn's reply


class DeliveryError(RuntimeError):
    """A send or a reaction failed. The message names what failed, never a token."""


@dataclass(frozen=True, slots=True)
class Incoming:
    """A message from the allowed user. `id` is what a reaction points at; `cursor` is where the
    transport resumes after a restart (Telegram's update id, Discord's message id); `replied_to`
    is the id of the message they replied to, if they did, and `quoted` its text and sender."""

    id: str
    text: str
    cursor: str
    replied_to: str | None = None
    quoted: Quoted | None = None


Handler = Callable[[Incoming], Awaitable[Reply]]


class Transport(Protocol):
    """One chat surface, talking to the one allowed user."""

    @property
    def limit(self) -> int:
        """The longest message it accepts, in characters."""
        ...

    async def receive(self, inbox: asyncio.Queue[Incoming], after: str | None) -> None:
        """Queue each new message from the allowed user, those after cursor `after` first, until
        cancelled. Messages from anyone else, or that are not text, never reach the queue."""
        ...

    async def send(self, text: str) -> str:
        """Send one message and return its id. Raises DeliveryError."""
        ...

    async def react(self, message_id: str, emoji: str) -> None:
        """React to one of their messages. Raises DeliveryError."""
        ...

    async def typing(self) -> None:
        """Show the typing indicator. A courtesy: it never raises and never waits on a limit."""
        ...


@dataclass(frozen=True, slots=True)
class Hooks:
    """What the daemon lets the surface tell it, and ask it. All optional."""

    on_undelivered: Undelivered | None = None
    last_handled: LastHandled | None = None
    mark_handled: MarkHandled | None = None
    on_sent: Sent | None = None


@dataclass(slots=True)
class _Delivery:
    """The messages of one reply that have actually gone out, so a cut-off reply is remembered as
    what the user saw."""

    sent: list[str] = field(default_factory=list[str])
    of_turn: bool = False  # a turn's reply, whose message ids are kept, not a command's answer


@dataclass(frozen=True, slots=True)
class _Wait:
    """Their message, when the turn started, and the one random factor for this reply's timing."""

    text: str
    started: float
    jitter: float


class Surface:
    def __init__(
        self,
        transport: Transport,
        hooks: Hooks | None = None,
        pace: float = 0.0,
        split: bool = False,
    ) -> None:
        self.transport = transport
        self._hooks = hooks or Hooks()
        self._pace = pace
        self._split = split

    async def run(
        self, handle: Handler, commands: Commands | None = None, stop: asyncio.Event | None = None
    ) -> None:
        """Receive in the background and answer one message at a time. A new plain message that
        arrives while the previous one is still being answered replaces that answer, so a burst of
        messages gets one reply that has seen all of them. When `stop` is set it takes nothing
        more, answers what it already has, the reply in progress included, and returns: a restart
        stopped it mid-turn and lost a message that had been received (2026-10-25). A transport
        that fails stops the run with its error."""
        last = self._hooks.last_handled() if self._hooks.last_handled else None
        queue: asyncio.Queue[Incoming] = asyncio.Queue()
        receiver = asyncio.create_task(self.transport.receive(queue, last))
        stopping = stop or asyncio.Event()
        halt = asyncio.create_task(cancel_when(stopping, receiver))
        waiting: list[Incoming] = []
        try:
            while True:
                msg = waiting.pop(0) if waiting else await next_message(queue, stopping, receiver)
                if msg is None:
                    log.info("stopping: every message received has been answered")
                    return
                await self._serve(msg, queue, waiting, handle, commands or {})
        finally:
            receiver.cancel()
            halt.cancel()

    async def _serve(
        self,
        msg: Incoming,
        queue: asyncio.Queue[Incoming],
        waiting: list[Incoming],
        handle: Handler,
        commands: Commands,
    ) -> None:
        """Answer a message. If another plain message arrives before the answer is out and this
        one was a plain message too, drop the answer and answer the new one, which sees both."""
        current = msg
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
            if _command(current.text) is not None or _command(newer.text) is not None:
                waiting.append(newer)
                await turn
                return
            log.info("a newer message arrived before the answer went out; answering both together")
            turn.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await turn
            current = newer

    async def _handle_one(self, msg: Incoming, handle: Handler, commands: Commands) -> None:
        """Record the message as handled before its turn runs, so it is answered at most once."""
        if self._hooks.mark_handled is not None:
            self._hooks.mark_handled(msg.cursor)
        await self.reply_to(msg, handle, commands)

    async def reply_to(self, msg: Incoming, handle: Handler, commands: Commands) -> None:
        """Run the turn for one message and deliver what it returns. Never raises but on a
        cancel."""
        command = _command(msg.text)
        log.debug(
            "message %s in: %d chars%s",
            msg.id,
            len(msg.text),
            f", command /{command[0]}" if command else "",
        )
        if command is not None and command[0] not in commands:
            return  # unknown and /start commands never reach the model
        started = time.monotonic()
        jitter = random.uniform(0.8, 1.25)  # noqa: S311
        typist: asyncio.Task[None] | None = None
        try:
            if command is not None:
                reply: Reply = await commands[command[0]](command[1], msg.replied_to)
            else:
                read = read_seconds(msg.text, self._pace, jitter)
                typist = asyncio.create_task(self._type_after(read))
                reply = await handle(msg)
        except asyncio.CancelledError:
            log.info("message %s superseded while the reply was being written", msg.id)
            raise
        except Exception:
            log.exception("turn failed")
            return
        finally:
            if typist is not None:
                typist.cancel()
        wait = _Wait(msg.text, started, jitter) if command is None else None
        delivery = _Delivery(of_turn=command is None)
        try:
            await self._answer(msg.id, reply, wait, delivery)
        except asyncio.CancelledError:
            log.info("message %s superseded; %d part(s) had gone out", msg.id, len(delivery.sent))
            await self._report_undelivered(reply, "superseded by a newer message", delivery.sent)
            raise
        except DeliveryError as err:
            log.warning("could not deliver the reply: %s", err)
            await self._report_undelivered(reply, str(err))
        else:
            log.info(
                "message %s answered %.1fs after it arrived (%s)",
                msg.id,
                time.monotonic() - started,
                _kind(reply),
            )

    async def _type_after(self, delay: float) -> None:
        """Show typing once the reading pause is over, and keep it up while the reply is written.
        A reply written within the pause shows none, as someone still reading would not."""
        await asyncio.sleep(delay)
        while True:
            await self.transport.typing()
            await asyncio.sleep(TYPING_REFRESH_SECONDS)

    async def _hold(self, reply: str, wait: _Wait, *, reading: bool = True) -> None:
        """Wait like someone reading and then typing: no indicator for what is left of the reading
        pause, then the typing indicator kept alive while a text reply is on its way. The wait
        counts the time already spent since `wait.started`."""
        elapsed = time.monotonic() - wait.started
        user_text = wait.text if reading else ""
        remaining = hold_seconds(user_text, reply, self._pace, elapsed, wait.jitter, reading)
        if remaining > 0:
            log.info("holding %.1fs before sending (%d words)", remaining, len(reply.split()))
        quiet = max(0.0, read_seconds(user_text, self._pace, wait.jitter) - elapsed)
        quiet = min(quiet, remaining) if reading else 0.0
        if quiet > 0:
            await asyncio.sleep(quiet)
            remaining -= quiet
        while remaining > 0:
            if reply:
                await self.transport.typing()
            step = min(remaining, TYPING_REFRESH_SECONDS)
            await asyncio.sleep(step)
            remaining -= step

    async def _send_parts(
        self, text: str, hold: Callable[..., Awaitable[None]] | None, delivery: _Delivery
    ) -> None:
        """Send a reply, cut into a few messages when it is long enough, each after its own
        typing time. A part that fails after an earlier one arrived stops the rest and is logged;
        the user has already seen the start, so only the parts that arrived are remembered."""
        parts = split_reply(text, random.random(), random.random()) if self._split else [text]  # noqa: S311
        parts = [piece for part in parts for piece in fit(part, self.transport.limit)]
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
                sent = await self.transport.send(part)
                delivery.sent.append(part)
                if delivery.of_turn and self._hooks.on_sent is not None:
                    self._hooks.on_sent(sent)
            except DeliveryError as err:
                if n == 0:
                    raise
                log.warning(
                    "part %d of %d failed to send; the rest were not sent", n + 1, len(parts)
                )
                await self._report_undelivered(text, str(err), delivery.sent)
                return

    async def _answer(
        self,
        message_id: str,
        reply: Reply,
        wait: _Wait | None = None,
        delivery: _Delivery | None = None,
    ) -> None:
        """Send the reply. `wait` is the user's text, when the turn started and its jitter; leave it
        out for a command's reply, which goes at once."""
        delivery = delivery or _Delivery()

        async def hold(text: str, *, first: bool = True) -> None:
            if wait is None or self._pace <= 0:
                return
            if first:
                await self._hold(text, wait)
            else:
                later = _Wait("", time.monotonic(), wait.jitter)
                await self._hold(text, later, reading=False)

        if isinstance(reply, ThenSend):
            try:
                await self._answer(message_id, reply.reply, wait, delivery)
            finally:
                await self._send_then(reply.then)
        elif isinstance(reply, ReactAndReply):
            try:
                await self.transport.react(message_id, reply.reaction.emoji)
            except DeliveryError:
                log.warning("reaction refused; sending the reply without it")
            if reply.text:
                await self._send_parts(reply.text, hold, delivery)
        elif isinstance(reply, Reaction):
            await hold("")
            try:
                await self.transport.react(message_id, reply.emoji)
            except DeliveryError:
                log.warning("reaction refused, falling back to text")
                await self.transport.send("noted")
        elif reply:
            await self._send_parts(reply, hold if wait is not None else None, delivery)

    async def _send_then(self, text: str) -> None:
        """Code's own message after the reply (the crisis line, ADR 0022), sent whatever became of
        the reply. A failure is logged and reported, never raised."""
        try:
            await self.transport.send(text)
        except DeliveryError as err:
            log.warning("could not deliver the message after the reply: %s", err)
            await self._report_undelivered(text, str(err))

    async def _report_undelivered(
        self, reply: Reply, reason: str, sent: Sequence[str] = ()
    ) -> None:
        """Tell the conversation a reply, or the rest of it, never arrived, so the model does not
        think it was seen. `sent` is the parts that did; a reply sent whole is not reported."""
        reply = reply.reply if isinstance(reply, ThenSend) else reply
        text = reply.text if isinstance(reply, ReactAndReply) else reply
        if not isinstance(text, str) or not text or self._hooks.on_undelivered is None:
            return
        delivered = " ".join(p.strip() for p in sent)
        if sent and delivered == " ".join(text.split()):
            return  # all of it arrived
        try:
            await self._hooks.on_undelivered(text, reason, delivered)
        except Exception:
            log.exception("could not record an undelivered reply")


def _kind(reply: Reply) -> str:
    if isinstance(reply, ThenSend):
        return f"{_kind(reply.reply)}, then code's own message"
    if isinstance(reply, ReactAndReply):
        return f"reaction {reply.reaction.emoji} then {len(reply.text.split())} words"
    if isinstance(reply, Reaction):
        return f"reaction {reply.emoji}"
    return f"{len(reply.split())} words"


def _command(text: str) -> tuple[str, str] | None:
    """`/flag too long` -> ("flag", "too long"). `/flag@my_bot x` is the same command."""
    if not text.startswith("/"):
        return None
    head, _, arg = text[1:].partition(" ")
    return head.partition("@")[0].lower(), arg.strip()
