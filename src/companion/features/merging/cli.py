"""`companion` commands of the merging feature."""

from __future__ import annotations

from companion.core.clock import local_zone, utc_now
from companion.features.merging import run as merging
from companion.loops.services import Services


async def group_now(x: Services) -> str:
    """Propose merges across every day and the whole store, for `companion memory group`."""
    done = await merging.everything(x.store, x.judge, x.rel, utc_now(), local_zone())
    return f"proposed {done.groups} merges, ${done.cost_usd:.4f}; answer them in memory review\n"
