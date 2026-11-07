"""The crisis path in a turn (ADR 0022): the risk judge read three times when the first screen
cues it, one decision with the reads and the level, and, when `COMPANION_CRISIS=on`, the note after
the history. In shadow it reads and logs what it would do, and nothing the talker is sent changes.

The scene rule, the method check on the reply and the fixed crisis-line message are the turn's own
(`turn/crisis.py`); reaching out first reads the hold from `core/crisis.py`. A reading is never
stored as a memory.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core import switch
from companion.core.crisis import (
    PAUSE_KEY,
    PAUSE_REASON,
    RISK,
    CrisisLevel,
    Reading,
    cue_words,
)
from companion.core.episode import EPISODE_GAP
from companion.core.extractor import StructuredModel
from companion.core.switch import Mode
from companion.core.types import Frame, Json, Speaker
from companion.features.crisis.logic import (
    PROMPT,
    SCHEMA,
    Outcome,
    Risk,
    combine,
    concern_note,
    cued,
    light_note,
    parse,
    render_reason,
    risk_prompt,
    said_before,
    stay_note,
    strong_cue,
)
from companion.kit.current import Heard, Turn, decide, mark
from companion.kit.features import Feature, Offer, Offered
from companion.kit.reads import Reads, read_times

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.crisis")
NAME = "crisis"
TIMEOUT_SECONDS = 6.0  # each read; under the turn's 9 s look-up deadline
LEVEL = "crisis: level"
LIGHT_KEY = "crisis: checked lightly"
LIGHT_EVERY = timedelta(days=1)


async def read_risk(
    extractor: StructuredModel, before: Sequence[tuple[Speaker, str]], said: str
) -> Reads[Risk]:
    """The risk judge's three reads of their message; a failed or unreadable read is None."""
    return await read_times(
        extractor,
        PROMPT.text,
        risk_prompt(before, said),
        SCHEMA,
        parse,
        spend="crisis",
        timeout=TIMEOUT_SECONDS,
    )


def would_do(reading: Reading) -> list[str]:
    """What the path does at this level when on, in words for the log."""
    if reading.risk:
        note = "the stay-with-them note" if reading.asked else "the concern note"
        done = [f"add {note} after the history with no length cap"]
        if reading.level is CrisisLevel.URGENT:
            done.append("send the crisis line after the reply")
        return [*done, "check the reply for method details", "hold reaching out first for a day"]
    return ["add one light check"] if reading.light else []


async def assess(c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None) -> Reading | None:
    """The level of this turn, logged once. The risk judge is asked only when the listening judge
    read the message as serious or acute, or a cue word is in it."""
    del in_scene
    if c.mode(switch.CRISIS) is Mode.OFF or c.judge is None:
        return None
    severity = heard.read.severity if heard is not None else None
    words = cue_words(t.text)
    detail: dict[str, Json] = {
        "mode": c.mode(switch.CRISIS),
        "cue": {"severity": severity, "words": list[Json](words)},
    }
    outcome = Outcome(CrisisLevel.NONE)
    if cued(severity, words):
        mark(t, "risk judge")
        got = await read_risk(c.judge, said_before(t.prior), t.text)
        outcome = combine(got.values, strong=strong_cue(severity, words))
        detail |= {
            "reads": [r.detail() if r is not None else None for r in got.values],
            "scorer": got.model,
            "prompt": PROMPT.ref,
        }
    light = outcome.light and not c.store.decided_since(c.rel, LIGHT_KEY, t.now - LIGHT_EVERY)
    asked = outcome.level is CrisisLevel.CONCERN and _risk_in_stretch(c, t)
    reading = Reading(outcome.level, c.mode(switch.CRISIS), light, asked)
    done = would_do(reading)
    detail |= {
        "level": outcome.level.value,
        "kind": outcome.kind,
        "timing": outcome.timing,
        "plan_or_means": outcome.plan_or_means,
        "light": light,
        "would": list[Json](done),
    }
    decide(c, t, LEVEL, detail, reason=render_reason(outcome, c.mode(switch.CRISIS), done))
    return reading


def _risk_in_stretch(c: Runtime, t: Turn) -> bool:
    """Whether a turn under EPISODE_GAP ago read concern or urgent: the same hard stretch, where
    they were already asked and given the line. In real chat concern fired five times in 18
    minutes (2026-11-04)."""
    for d in c.store.decisions_with_key(c.rel, LEVEL, t.now - EPISODE_GAP):
        if (d.detail or {}).get("level") in RISK:
            return True
    return False


def crisis_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """When on: the concern note after the history on a concern or urgent turn, and the hold on
    reaching out once the turn is stored; or one light check, at most once a day."""
    del so_far
    if not isinstance(found, Reading) or not found.acts:
        return Offer()
    c, t = m.c, m.t
    if found.risk:
        return Offer(
            tail=(stay_note() if found.asked else concern_note(),),
            after=(lambda: decide(c, t, PAUSE_KEY, reason=f"{PAUSE_KEY}: {PAUSE_REASON}"),),
            asks=True,
        )
    if found.light:
        return Offer(tail=(light_note(),), after=(lambda: decide(c, t, LIGHT_KEY),), asks=True)
    return Offer()


# Reads every turn for risk (ADR 0022), `COMPANION_CRISIS`: shadow by default, on or off.
CRISIS = Feature(NAME, look=assess, note=crisis_offer)
