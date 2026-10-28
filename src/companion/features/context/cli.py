"""`companion` commands of the context feature."""

from __future__ import annotations

from companion.core.clock import utc_now
from companion.features.context.run import write_missing
from companion.kit.services import Services


async def write_now(x: Services) -> str:
    """Write what they were talking about for every memory that wants it, for `memory context`."""
    done = await write_missing(x.store, x.judge, x.rel, utc_now(), limit=1000)
    return f"wrote {done.written} notes on what was being talked about, ${done.cost_usd:.4f}\n"
