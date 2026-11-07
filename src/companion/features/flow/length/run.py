"""The length note as a feature: the one target for this turn, logged with the reason code wrote."""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.features.flow.length.logic import LengthTarget, length_target
from companion.kit.current import decide
from companion.kit.features import Feature, NoteName, Offer, Offered

if TYPE_CHECKING:
    from companion.kit.features import Moment


def target(m: Moment) -> LengthTarget | None:
    """The one length target for this turn, logged with the reason code wrote for it. None on a
    turn the crisis path reads as a risk (ADR 0022)."""
    c, t = m.c, m.t
    severity = m.severity
    size = (
        None
        if m.risk
        else length_target(t.text, severity=severity, in_scene=m.pretend, seed=str(t.turn))
    )
    reason = f"length: under about {size.words} words, {size.why}" if size else "length: no cap"
    if m.risk:
        reason = "length: no cap, the crisis path read a risk"
    decide(
        c, t, "length", {"words": size.words if size else None, "severity": severity}, reason=reason
    )
    return size


def length_offer(m: Moment, _: object, __: Offered) -> Offer:
    size = target(m)
    return Offer((size.note,) if size else ())


LENGTH = Feature(NoteName.LENGTH, note=length_offer)
