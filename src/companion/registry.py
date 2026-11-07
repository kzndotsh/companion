"""Every feature the turn, the memory pass, the night and the timers run by declaration
(`kit/features.py`), in order: their steps after a memory pass and once a turn is stored, and the
night's steps, run in this order. Their notes go in the order `ORDER` in `turn/notes.py` names, and
the initiative tick's steps in `Kind` order (`core/reachout.py`)."""

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
from companion.features.nudges.run import NUDGES
from companion.features.promises.run import PROMISE_CHECK
from companion.features.reach.run import REACH
from companion.features.recall.run import RECALL, RELEVANCE
from companion.features.reminders.run import REMINDERS
from companion.features.threads.run import OPENLOOPS
from companion.features.upkeep.context.run import CONTEXT
from companion.features.upkeep.merging.run import MERGING
from companion.features.upkeep.reread.run import REREAD
from companion.features.upkeep.sort.run import WORTH
from companion.kit.features import Feature

FEATURES: tuple[Feature, ...] = (
    KNOWING,
    BASICS,
    TICS,
    PROMISE_CHECK,
    MOOD,
    CONTEXT,
    REREAD,
    MERGING,
    WORTH,
    RECALL,
    RELEVANCE,
    FOCUS,
    EPISODES,
    TOPICS,
    GUESS,
    OPENLOOPS,
    NUDGES,
    REACH,
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
