"""Every feature the turn and the memory pass run by declaration (`loops/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.features.reminders.run import REMINDERS
from companion.loops.context import CONTEXT
from companion.loops.episodes import EPISODES
from companion.loops.features import Feature
from companion.loops.guess import GUESS
from companion.loops.knowing import KNOWING
from companion.loops.lore import LORE
from companion.loops.names import NAMES
from companion.loops.relevance import RELEVANCE
from companion.loops.topics import TOPICS
from companion.loops.worth import WORTH

FEATURES: tuple[Feature, ...] = (
    KNOWING,
    NAMES,
    CONTEXT,
    WORTH,
    RELEVANCE,
    EPISODES,
    TOPICS,
    GUESS,
    LORE,
    REMINDERS,
)
