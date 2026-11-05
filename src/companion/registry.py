"""Every feature the turn and the memory pass run by declaration (`kit/features.py`), in order:
their steps after a memory pass and once a turn is stored run in this order. Their notes go in the
order `ORDER` in `turn/notes.py` names."""

from __future__ import annotations

from companion.features.calendar.run import CALENDAR
from companion.features.crisis.run import CRISIS
from companion.features.curiosity.basics.run import BASICS
from companion.features.curiosity.guess.run import GUESS
from companion.features.curiosity.map.run import KNOWING
from companion.features.diction.marks.run import MARKS
from companion.features.diction.tics.run import TICS
from companion.features.episodes.run import EPISODES
from companion.features.flow.length.run import LENGTH
from companion.features.flow.questions.run import GAME, QUESTIONS
from companion.features.flow.topics.run import TOPICS
from companion.features.focus.run import FOCUS
from companion.features.history.run import HISTORY
from companion.features.intimate.run import SCENE
from companion.features.lore.run import LORE
from companion.features.mood.run import MOOD
from companion.features.now.run import NOW
from companion.features.promises.run import PROMISE_CHECK
from companion.features.recall.run import RECALL, RELEVANCE
from companion.features.reminders.run import REMINDERS
from companion.features.threads.run import OPENLOOPS
from companion.features.upkeep.context.run import CONTEXT
from companion.features.upkeep.sort.run import WORTH
from companion.kit.features import Feature

FEATURES: tuple[Feature, ...] = (
    KNOWING,
    BASICS,
    TICS,
    PROMISE_CHECK,
    MOOD,
    CONTEXT,
    WORTH,
    RECALL,
    RELEVANCE,
    FOCUS,
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
    HISTORY,
    SCENE,
    LENGTH,
    GAME,
    QUESTIONS,
)
