"""Every feature the turn and the memory pass run by declaration (`loops/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.features.episodes.run import EPISODES
from companion.features.guess.run import GUESS
from companion.features.lore.run import LORE
from companion.features.reminders.run import REMINDERS
from companion.features.topics.run import TOPICS
from companion.loops.context import CONTEXT
from companion.loops.features import Feature
from companion.loops.knowing import KNOWING
from companion.loops.names import NAMES
from companion.loops.relevance import RELEVANCE
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
