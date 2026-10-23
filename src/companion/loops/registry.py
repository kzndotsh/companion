"""Every feature the turn and the memory pass run by declaration (`loops/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.loops.context import CONTEXT
from companion.loops.features import Feature
from companion.loops.knowing import KNOWING
from companion.loops.lore import LORE
from companion.loops.names import NAMES
from companion.loops.reminders import REMINDERS
from companion.loops.worth import WORTH

FEATURES: tuple[Feature, ...] = (KNOWING, NAMES, CONTEXT, WORTH, LORE, REMINDERS)
