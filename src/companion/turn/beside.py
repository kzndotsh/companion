"""What runs beside a turn and never changes the reply: shadow look-ups, each logged, a failure
logged too (the shadow stage of a turn)."""

from __future__ import annotations

from companion.kit.beside import beside
from companion.kit.features import Moment
from companion.registry import FEATURES


def shadows(m: Moment) -> None:
    """What runs in shadow on a turn and never changes the reply: each feature's shadow look-up."""
    for feature in FEATURES:
        if feature.shadow is not None and feature.can_read(m.c):
            beside(feature.shadow(m))
