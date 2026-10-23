"""Every feature the turn and the memory pass run by declaration (`loops/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.features.basics.run import BASICS
from companion.features.context.run import CONTEXT
from companion.features.episodes.run import EPISODES
from companion.features.guess.run import GUESS
from companion.features.hooks.run import HOOKS
from companion.features.knowing.run import KNOWING
from companion.features.lore.run import LORE
from companion.features.mood.run import MOOD
from companion.features.moves.run import MOVES
from companion.features.names.run import NAMES
from companion.features.nudges.run import NUDGES
from companion.features.openloops.run import OPENLOOPS
from companion.features.relevance.run import RELEVANCE
from companion.features.reminders.run import REMINDERS
from companion.features.topics.run import TOPICS
from companion.features.worth.run import WORTH
from companion.loops.features import Feature

FEATURES: tuple[Feature, ...] = (
    KNOWING,
    BASICS,
    MOVES,
    MOOD,
    NAMES,
    CONTEXT,
    WORTH,
    RELEVANCE,
    EPISODES,
    TOPICS,
    GUESS,
    OPENLOOPS,
    LORE,
    REMINDERS,
    NUDGES,
    HOOKS,
)
