"""`companion` commands of the worth feature."""

from __future__ import annotations

from companion.core.clock import utc_now
from companion.features.worth.run import label
from companion.kit.services import Services


async def label_now(x: Services) -> str:
    """Label every memory kept before the rule; each change becomes a question, `memory label`."""
    done = await label(x.store, x.judge, x.rel, utc_now(), act_since=None, limit=1000)
    return (
        f"labelled {done.labelled}, {done.questions} questions for memory review,"
        f" ${done.cost_usd:.4f}\n"
    )
