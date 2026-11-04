"""What runs beside a turn and never changes the reply: shadow look-ups, each logged, a failure
logged too (the shadow stage of a turn)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.types import Frame
from companion.kit.beside import beside
from companion.kit.current import Heard, Turn
from companion.registry import FEATURES

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime


def shadows(c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card) -> None:
    """What runs in shadow on a turn and never changes the reply: each feature's shadow look-up."""
    for feature in FEATURES:
        if feature.shadow is not None:
            beside(feature.shadow(c, t, in_scene, heard, card))
