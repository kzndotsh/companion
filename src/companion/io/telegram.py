"""Telegram as a transport for `io/surface.py`: long polling, update ids, the Bot API's calls and
its "too many requests" waits. Takes text messages from the one allowed user in their private chat
and ignores everyone else. Errors never carry the URL, which holds the bot token."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from companion.io.surface import DeliveryError, Incoming
from companion.models.wire import integer, obj, seq

log = logging.getLogger("companion.telegram")
# How long one call may wait in all on Telegram's "too many requests" before giving up. Each wait is
# the full time Telegram asks for: asking again sooner is refused and can lengthen the block.
RATE_LIMIT_BUDGET_SECONDS = 60.0


class TelegramError(DeliveryError):
    """A Telegram call failed. The message names the method and status, never the URL, because the
    URL contains the bot token and logs must not."""


class RateLimited(TelegramError):
    """Telegram kept saying "too many requests" past the wait budget."""


class Telegram:
    limit = 4096  # the Bot API refuses a longer message

    def __init__(self, token: str, allowed_user: int, client: httpx.AsyncClient) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._allowed = allowed_user
        self._client = client

    async def _call(
        self, method: str, *, budget: float = RATE_LIMIT_BUDGET_SECONDS, **params: object
    ) -> object:
        waited = 0.0
        while True:
            began = time.perf_counter()
            try:
                resp = await self._client.post(f"{self._base}/{method}", json=params, timeout=45)
                resp.raise_for_status()
            except httpx.HTTPStatusError as err:
                status = err.response.status_code
                wait = _retry_after(err.response) if status == 429 else None
                if wait is not None and waited + wait <= budget:
                    log.warning(
                        "telegram %s rate limited; waiting the %.1fs asked and retrying",
                        method,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    waited += wait
                    continue
                log.warning("telegram %s status %d: %s", method, status, err.response.text[:300])
                msg = f"telegram {method} failed with status {status}"
                raise (RateLimited if wait is not None else TelegramError)(msg) from None
            except httpx.HTTPError as err:
                msg = f"telegram {method} failed: {type(err).__name__}"
                raise TelegramError(msg) from None
            if method != "getUpdates":
                log.debug("telegram %s ok in %dms", method, (time.perf_counter() - began) * 1000)
            return resp.json()["result"]

    async def send(self, text: str) -> None:
        for attempt in range(2):
            try:
                await self._call("sendMessage", chat_id=self._allowed, text=text)
            except RateLimited:
                raise  # it already waited out its budget; another try would only wait again
            except TelegramError:
                if attempt == 1:
                    raise
                await asyncio.sleep(2.0)
            else:
                return

    async def react(self, message_id: str, emoji: str) -> None:
        await self._call(
            "setMessageReaction",
            chat_id=self._allowed,
            message_id=int(message_id),
            reaction=[{"type": "emoji", "emoji": emoji}],
        )

    async def typing(self) -> None:
        """The typing indicator is a courtesy. Failing to show it must never lose the reply."""
        try:
            await self._call("sendChatAction", budget=0.0, chat_id=self._allowed, action="typing")
        except TelegramError as err:
            log.warning("typing indicator skipped: %s", err)

    async def receive(self, inbox: asyncio.Queue[Incoming], after: str | None) -> None:
        """Fetch updates for ever and queue the allowed user's messages. The offset moves past an
        update as soon as it is queued, so a restart can lose a message that was queued but not yet
        answered. Telegram only forgets an update when a later poll asks past it, so one handled
        just before a restart comes back; starting past `after` skips it."""
        offset = int(after) + 1 if after is not None else 0
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
            messages, offset = self.read(seq(updates), offset)
            for msg in messages:
                inbox.put_nowait(msg)

    def read(self, updates: list[object], offset: int) -> tuple[list[Incoming], int]:
        """The allowed user's text messages in private chat among `updates`, each once and in
        order, and the next offset. An update below `offset` was already taken."""
        out: list[Incoming] = []
        for update in updates:
            u = obj(update)
            update_id = integer(u.get("update_id"))
            if update_id < offset:
                continue
            offset = update_id + 1
            msg = obj(u.get("message"))
            text = msg.get("text")
            if not isinstance(text, str):
                continue
            if integer(obj(msg.get("from")).get("id")) != self._allowed:
                log.warning("ignored a message from a user who is not allowed")
                continue
            if integer(obj(msg.get("chat")).get("id")) != self._allowed:
                log.warning("ignored a message outside their private chat")
                continue
            out.append(Incoming(str(integer(msg.get("message_id"))), text, str(update_id)))
        return out, offset


def _retry_after(resp: httpx.Response) -> float:
    """How long Telegram asked us to wait, in full. A missing or unreadable value means a second."""
    try:
        wait = float(resp.json()["parameters"]["retry_after"])
    except (ValueError, KeyError, TypeError):
        wait = 1.0
    return max(wait, 0.0)
