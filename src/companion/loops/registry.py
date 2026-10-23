"""Every feature the turn and the memory pass run by declaration (`loops/features.py`), in order:
their notes go in this order, and so do their steps after a memory pass."""

from __future__ import annotations

from companion.loops.features import Feature
from companion.loops.lore import LORE
from companion.loops.reminders import REMINDERS

FEATURES: tuple[Feature, ...] = (LORE, REMINDERS)
