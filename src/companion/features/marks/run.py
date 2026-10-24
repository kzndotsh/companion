"""Offering one of its own marks on a turn (owner's choice, 2026-10-23): sent after the history,
where it is used (66 of 80 replies, 20 different marks); in the system block it was not. It does not
stop it copying theirs. A casual turn only; logged with the mark offered once the turn is stored."""

from __future__ import annotations

from companion.core.types import Speaker
from companion.features.marks.logic import OFFERED, note, offered, pick
from companion.loops.current import decide
from companion.loops.features import Feature, Moment, Offer, Offered


def mark_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    del found, so_far
    c, t = m.c, m.t
    if not c.marks or not m.casual or not offered(str(t.turn), t.text):
        return Offer()
    mine = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    mark = pick(str(t.turn), t.text, mine)
    if mark is None:
        return Offer()
    return Offer(tail=(note(mark),), after=(lambda: decide(c, t, OFFERED, {"mark": mark}),))


# One of its own emoticons now and then, never theirs (`COMPANION_MARKS`, on unless `off`).
MARKS = Feature("mark", note=mark_offer)
