"""What every turn runs with: the store, the models and every switch the turn reads, for as long as
the bot runs. Plain data; the turn itself is run by `handle` in the stages above it."""

from __future__ import annotations

from dataclasses import dataclass, field

from companion.core.extractor import StructuredModel
from companion.core.prompt.prefix import Prefix
from companion.core.talker import Talker
from companion.core.types import RelationshipId
from companion.core.vectors import Embedder
from companion.loops.habits import HabitMemory
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Runtime:
    store: Store
    talker: Talker
    prefix: Prefix
    rel: RelationshipId
    judge: StructuredModel | None = None
    habits: HabitMemory = field(default_factory=HabitMemory)
    roleplay_talker: Talker | None = None  # replies while a pretend scene is in progress
    daily_cap_usd: float | None = None  # nothing paid runs once today's spend reaches this
    listen: bool = True  # ask how serious a message is before the reply
    mood: str = "off"  # off, shadow (worked out and logged, never shown) or on (ADR 0016)
    resample: bool = False  # draw one fresh reply when the first fails a check (core/recheck.py)
    route_intimate: bool = False  # intimate talk may go to the roleplay talker (ADR 0017)
    roleplay_prefix: Prefix | None = (
        None  # the roleplay talker's system prompt, with the sheet's scene section
    )
    embedder: Embedder | None = None  # the relevance look-up runs in shadow when set
    embed_model: str = ""
    lore: str = "off"  # on, shadow or off: its tastes nearest their message (ADR 0020)
    scene_reminder: str = ""  # the character's scene reminder, sent after the history in scenes
    relevance: str = "shadow"  # on (picks shown when a memory is near), shadow or off (ADR 0018)
    reminders: bool = True  # reminders they ask for are read and set (J50)
    initiative: bool = True  # reach-outs and the reads that only feed them (nudges' away read)
    calendar: bool = (
        False  # a note about the day: a holiday, a lead-up, their date (`features/calendar`)
    )
    marks: bool = False  # offer one of its own emoticons now and then (`features/marks`)
    episodes: str = "off"  # what they did together lately, when it bears: on, shadow or off (J12)
    crisis: str = "off"  # the crisis path: on, shadow (reads and logs only) or off (ADR 0022)
    now: str = (
        "off"  # what they said is coming, kept until it happens: on, shadow or off (ADR 0024)
    )
    history: str = "off"  # its own history: shadow logs the stories it would show (ADR 0025)
    scene_memory: str = "off"  # the intimate scene lane: on, shadow (logged only) or off (ADR 0026)
    serious_message: str = ""  # the sheet's `## Crisis message` section, sent by code
