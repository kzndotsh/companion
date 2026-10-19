"""What OpenRouter says the account has bought and used. The eval runner reads it before and after a
run, so the reported spend is what was charged, not what the responses claimed."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from companion.models.wire import number, obj

log = logging.getLogger("companion.openrouter")
URL = "https://openrouter.ai/api/v1/credits"
SETTLE_SECONDS = 5.0
TRIES = 18  # about a minute and a half
CAUGHT_UP = 0.8


@dataclass(frozen=True, slots=True)
class Credits:
    bought: float
    used: float

    @property
    def balance(self) -> float:
        return self.bought - self.used


async def credits(key: str, client: httpx.AsyncClient) -> Credits | None:
    """None when OpenRouter cannot be read; a run never fails over the meter."""
    try:
        resp = await client.get(URL, headers={"Authorization": f"Bearer {key}"}, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError as err:
        log.warning("openrouter credits unreadable: %s", type(err).__name__)
        return None
    data = obj(obj(resp.json()).get("data"))
    return Credits(bought=number(data.get("total_credits")), used=number(data.get("total_usage")))


async def charged_since(
    key: str,
    client: httpx.AsyncClient,
    before: Credits,
    expected: float,
    *,
    settle: float = SETTLE_SECONDS,
) -> float | None:
    """What the account was charged since `before`. The meter can sit still for a while before it
    catches up, so a steady reading counts only once it has reached most of what the replies said
    they cost; past the time limit the last reading is returned as it is."""
    last: float | None = None
    for _ in range(TRIES):
        await asyncio.sleep(settle)
        now = await credits(key, client)
        if now is None:
            return last
        charged = now.used - before.used
        caught_up = charged >= expected * CAUGHT_UP
        if caught_up and last is not None and abs(charged - last) < 1e-9:
            return charged
        last = charged
    return last


__all__ = ["Credits", "charged_since", "credits"]
