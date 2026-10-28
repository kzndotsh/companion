"""The mood line for the system block (ADR 0016), worked out from the effects their messages added,
and the effects this message adds, written once the turn is stored. Logged in shadow too."""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core.clock import local_zone
from companion.core.types import Frame, Speaker
from companion.features.mood.logic import PARAMS_VERSION as MOOD_PARAMS
from companion.features.mood.logic import WINDOW as MOOD_WINDOW
from companion.features.mood.logic import Effect as MoodEffect
from companion.features.mood.logic import (
    Said,
    chat_minutes,
    effects_for,
    held_because,
    inputs_for,
    mood_at,
)
from companion.features.mood.logic import line as mood_line
from companion.features.mood.logic import reason as mood_reason
from companion.kit.current import Heard, Turn, decide
from companion.kit.features import Feature, Moment, Offer, Offered

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime


def _mood(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[str | None, list[MoodEffect]]:
    """The mood line for the system block when the mood is on, and what this message adds to it.
    The decision is logged in shadow mode too, so the replay and the live log can be compared."""
    if c.mood == "off":
        return None, []
    zone = local_zone()
    severity = heard[0].severity if heard is not None else None
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    earlier = c.store.said_since(c.rel, theirs[-1].at)[:1] if theirs else []
    minutes = chat_minutes([u.at for u in t.prior], t.now, zone)
    said = Said(t.turn, t.now, t.text, severity, None)
    added = effects_for(inputs_for(said, earlier[0].tone if earlier else None, minutes))
    stored = c.store.mood_effects_since(c.rel, t.now - MOOD_WINDOW)
    before, after = mood_at(stored, t.now, zone), mood_at([*stored, *added], t.now, zone)
    held = held_because(severity=severity, text=t.text, in_scene=in_scene is not Frame.REAL)
    shown, why = mood_line(after, held=held), mood_reason(after, held=held)
    decide(
        c,
        t,
        "mood",
        {
            "mode": c.mood,
            "params": MOOD_PARAMS,
            "before": {s.value: round(v, 3) for s, v in before.strengths.items()},
            "after": {s.value: round(v, 3) for s, v in after.strengths.items()},
            "added": [[e.source.value, round(e.amount, 3)] for e in added],
            "line": shown,
        },
        reason=f"{why} [{c.mood}]",
    )
    return (shown if c.mood == "on" else None), added


def mood_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    del found, so_far
    shown, added = _mood(m.c, m.t, m.in_scene, m.heard)
    c = m.c
    after = (lambda: c.store.add_mood_effects(c.rel, added),) if added else ()
    return Offer((shown,) if shown else (), after)


# A mood that carries: only what they did moves it, and it shows in the system block when on.
MOOD = Feature("mood", note=mood_offer)
