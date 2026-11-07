"""The runtime tests turn with: built by `compose.runtime` from `Settings`, with every switch off
except the four a turn needs to run at all, so a test sees only the feature it switches on. Name
what a test needs on top: `make_runtime(store, talker, PREFIX, REL, mood="on")`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from companion import compose
from companion.core import switch as sw
from companion.core.prompt.prefix import Prefix
from companion.core.switch import Position, Switch
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

_BY_NAME = {name.lower(): v for name, v in vars(sw).items() if isinstance(v, Switch)}


def make_runtime(
    store: Store, talker: Talker, prefix: Prefix, rel: RelationshipId, **changes: object
) -> Runtime:
    """`QUIET` as a runtime, with no daily cap and no embedding model, and `changes` on top: a
    `Runtime` field, or a switch by its name in `core/switch.py` with its mode (`mood="on"`, or a
    bool for one that is on or off). A name that is neither stops the test."""
    base = compose.runtime(QUIET, store, talker, prefix, rel)
    fields = {k: v for k, v in changes.items() if k not in _BY_NAME}
    positions: Mapping[Switch, Position] = {
        **base.positions,
        **{_BY_NAME[k]: _mode(v) for k, v in changes.items() if k in _BY_NAME},
    }
    return replace(
        base, positions=positions, **{"daily_cap_usd": None, "embed_model": "", **fields}
    )


def _mode(value: object) -> Position:
    if isinstance(value, bool):
        return Position.ON if value else Position.OFF
    return Position(str(value))
