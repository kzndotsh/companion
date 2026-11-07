"""What every turn runs with: the store, the models and every switch the turn reads, for as long as
the bot runs. Plain data; the turn itself is run by `handle` in the stages above it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from companion.core.extractor import StructuredModel
from companion.core.prompt.prefix import Prefix
from companion.core.switch import Mode, Switch
from companion.core.talker import Talker
from companion.core.types import RelationshipId
from companion.core.vectors import Embedder
from companion.kit.tics import TicMemory
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True, kw_only=True)
class Runtime:
    """Built only by `compose.runtime`, so every switch has Settings' value, and none has a field of
    its own: a switch is read as `c.mode(MOOD)` or `c.on(MOOD)`."""

    store: Store
    talker: Talker
    prefix: Prefix
    rel: RelationshipId
    judge: StructuredModel | None = None
    tics: TicMemory = field(default_factory=TicMemory)
    roleplay_talker: Talker | None = None  # replies while a pretend scene is in progress
    roleplay_prefix: Prefix | None = (
        None  # the roleplay talker's system prompt, with the sheet's scene section
    )
    embedder: Embedder | None = None  # the relevance look-up runs in shadow when set
    embed_model: str = ""
    scene_reminder: str = ""  # the character's scene reminder, sent after the history in scenes
    serious_message: str = ""  # the sheet's `## Crisis message` section, sent by code
    daily_cap_usd: float | None  # nothing paid runs once today's spend reaches this
    modes: Mapping[Switch, Mode]  # where each on, shadow or off switch stands (`core/switch.py`)

    def mode(self, switch: Switch) -> Mode:
        """Where a switch stands: on, shadow or off."""
        return self.modes[switch]

    def on(self, switch: Switch) -> bool:
        """Whether a switch is anything but off."""
        return self.modes[switch] is not Mode.OFF
