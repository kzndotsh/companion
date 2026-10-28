"""Every feature the turn and the memory pass run by declaration (`kit/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.features.basics.run import BASICS
from companion.features.calendar.run import CALENDAR
from companion.features.context.run import CONTEXT
from companion.features.crisis.run import CRISIS
from companion.features.episodes.run import EPISODES
from companion.features.guess.run import GUESS
from companion.features.history.run import HISTORY
from companion.features.hooks.run import HOOKS
from companion.features.knowing.run import KNOWING
from companion.features.lore.run import LORE
from companion.features.marks.run import MARKS
from companion.features.mood.run import MOOD
from companion.features.moves.run import MOVES
from companion.features.names.run import NAMES
from companion.features.now.run import NOW
from companion.features.relevance.run import RELEVANCE
from companion.features.reminders.run import REMINDERS
from companion.features.scene_memory.run import SCENE
from companion.features.threads.run import OPENLOOPS
from companion.features.topics.run import TOPICS
from companion.features.worth.run import WORTH
from companion.kit.features import Feature

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
    MARKS,
    REMINDERS,
    CRISIS,
    NOW,
    CALENDAR,
    HOOKS,
    HISTORY,
    SCENE,
)
