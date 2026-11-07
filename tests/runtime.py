"""The runtime tests turn with: built by `compose.runtime` from `Settings`, with every switch off
except the four a turn needs to run at all, so a test sees only the feature it switches on. Name
what a test needs on top: `make_runtime(store, talker, PREFIX, REL, mood="on")`."""

from __future__ import annotations

from dataclasses import replace

from companion import compose
from companion import settings as sw
from companion.core.prompt.prefix import Prefix
from companion.core.talker import Talker
from companion.core.types import RelationshipId
from companion.kit.runtime import Runtime
from companion.settings import Settings
from companion.store.sqlite.store import Store

QUIET = Settings.from_env(
    {
        **{s.env: "off" for s in sw.SWITCHES},
        sw.LISTEN.env: "on",
        sw.RELEVANCE.env: "shadow",
        sw.REMINDERS.env: "on",
        sw.INITIATIVE.env: "shadow",
    }
)


def make_runtime(
    store: Store, talker: Talker, prefix: Prefix, rel: RelationshipId, **changes: object
) -> Runtime:
    """`QUIET` as a runtime, with no daily cap and no embedding model, and `changes` (any
    `Runtime` field) on top."""
    base = compose.runtime(QUIET, store, talker, prefix, rel)
    return replace(base, **{"daily_cap_usd": None, "embed_model": "", **changes})
