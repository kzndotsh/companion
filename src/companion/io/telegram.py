"""Telegram long polling. Answers one allowed user and ignores everyone else."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx

from companion.models.wire import integer, obj, seq

log = logging.getLogger("companion.telegram")

Handler = Callable[[str], Awaitable[str]]


class Telegram:
    def __init__(self, token: str, allowed_user: int, client: httpx.AsyncClient) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._allowed = allowed_user
        self._client = client

    async def _call(self, method: str, **params: object) -> object:
        resp = await self._client.post(f"{self._base}/{method}", json=params, timeout=45)
        resp.raise_for_status()
        return resp.json()["result"]

    async def send(self, chat_id: int, text: str) -> None:
        await self._call("sendMessage", chat_id=chat_id, text=text)

    async def run(self, handle: Handler) -> None:
        offset = 0
        while True:
            try:
                updates = await self._call("getUpdates", offset=offset, timeout=30)
            except httpx.HTTPError:
                log.exception("poll failed, retrying")
                await asyncio.sleep(3)
                continue
            for update in seq(updates):
                u = obj(update)
                offset = integer(u.get("update_id")) + 1
                await self._one(u, handle)

    async def _one(self, update: dict[str, object], handle: Handler) -> None:
        msg = obj(update.get("message"))
        text = msg.get("text")
        if not isinstance(text, str):
            return
        if integer(obj(msg.get("from")).get("id")) != self._allowed:
            log.warning("ignored a message from a user who is not allowed")
            return
        chat_id = integer(obj(msg.get("chat")).get("id"))
        try:
            await self._call("sendChatAction", chat_id=chat_id, action="typing")
            reply = await handle(text)
        except Exception:
            log.exception("turn failed")
            return
        if reply:
            await self.send(chat_id, reply)
