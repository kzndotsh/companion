"""What every turn runs with: the store, the models and every switch the turn reads, for as long as
the bot runs. Plain data; the turn itself is run by `handle` in the stages above it."""

from __future__ import annotations

from dataclasses import dataclass, field

from companion.core.extractor import StructuredModel
from companion.core.prompt.prefix import Prefix
from companion.core.talker import Talker
from companion.core.types import RelationshipId
from companion.core.vectors import Embedder
from companion.kit.tics import TicMemory
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True, kw_only=True)
class Runtime:
    """Built only by `compose.runtime`, so every switch has Settings' value: a field here has no
    default of its own."""

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
    listen: bool  # ask how serious a message is before the reply
    mood: str  # off, shadow (worked out and logged, never shown) or on (ADR 0016)
    redraw: bool  # draw one fresh reply when the first fails a check (core/reply_gate.py)
    route_intimate: bool  # intimate talk may go to the roleplay talker (ADR 0017)
    lore: str  # on, shadow or off: its tastes nearest their message (ADR 0020)
    focus: str  # on or off: the card ranked by closeness to the moment
    relevance: str  # on (picks shown when a memory is near), shadow or off (ADR 0018)
    reminders: bool  # reminders they ask for are read and set (J50)
    initiative: bool  # reach-outs and the reads that only feed them (nudges' away read)
    calendar: bool  # a note about the day: a holiday, a lead-up, their date (`features/calendar`)
    own_marks: bool  # one of its own emoticons now and then (`features/diction/marks`)
    episodes: str  # what they did together lately, when it bears: on, shadow or off (J12)
    crisis: str  # the crisis path: on, shadow (reads and logs only) or off (ADR 0022)
    now: str  # what they said is coming, kept until it happens: on, shadow or off (ADR 0024)
    history: str  # its own history: shadow logs the stories it would show (ADR 0025)
    intimate_memory: str  # the intimate memory lane: on, shadow or off (ADR 0026)
    promises: str  # its promises: shadow checks each reply and logs what it would redraw
