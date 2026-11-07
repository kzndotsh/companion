"""The question notes as features: the game while they keep asking for questions, and the run
breaker when its last replies all asked one."""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core.types import HEAVY_AT, Frame, Speaker
from companion.features.flow.questions.logic import game_note, question_note
from companion.kit.features import Feature, Offer, Offered, asking

if TYPE_CHECKING:
    from companion.kit.features import Moment


def game_offer(m: Moment, _: object, __: Offered) -> Offer:
    """When they asked it to keep asking them things, a note after the history to ask the next
    one: outside a scene, not on a serious turn and not on one the crisis path reads as a risk."""
    serious = m.risk or (m.heard is not None and m.heard[0].severity >= HEAVY_AT)
    if m.in_scene is not Frame.REAL or serious:
        return Offer()
    note = game_note(m.t.prior, m.t.text, m.t.now)
    return Offer(tail=(note,) if note else (), asks=True)


def run_offer(m: Moment, _: object, so_far: Offered) -> Offer:
    """When its last replies were all questions, a note to ask nothing this time: outside a scene,
    not on a serious turn, and not when another note asks them something. After the history."""
    serious = m.heard is not None and m.heard[0].severity >= HEAVY_AT
    if m.in_scene is not Frame.REAL or serious or asking(so_far):
        return Offer()
    replies = [u.text for u in m.t.prior if u.speaker is Speaker.COMPANION]
    note = question_note(replies)
    return Offer(tail=(note,) if note else ())


GAME = Feature("game", note=game_offer)
QUESTIONS = Feature("questions", note=run_offer)
