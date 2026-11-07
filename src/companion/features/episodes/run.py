"""Writing a record of each episode of chat once it is over (J12, shadow: nothing reaches the talker
yet). Run nightly and by `companion episodes --write`."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from companion.core import switch
from companion.core.clock import local_zone, utc_now
from companion.core.episode import EPISODE_GAP
from companion.core.ids import new_id
from companion.core.switch import Mode
from companion.core.turn.listening import LISTENING_KEY, logged_severity
from companion.core.types import Frame, Json, Severity, Speaker
from companion.features.episodes.logic import GAP_BACK, Told, period
from companion.features.episodes.logic import NOTE as EPISODES_NOTE
from companion.features.episodes.logic import note as episodes_note
from companion.features.episodes.logic import recent as recent_times
from companion.features.episodes.store import Episodes
from companion.kit.current import Heard, Turn, decide, mark
from companion.kit.features import Feature, NightStep, Offer, Offered

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime

import logging
from dataclasses import dataclass
from datetime import datetime

from companion.core.episode import Episode
from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId, TurnId
from companion.features.episodes.logic import (
    PROMPT,
    SCHEMA,
    Kind,
    cut,
    facts,
    firsts,
    kind,
    parse,
    top_severity,
    transcript,
)
from companion.kit.ask import Judge, ask
from companion.kit.embed import bounded
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.episodes")
GIST_WRITER = Judge(
    "episodes",
    PROMPT,
    SCHEMA,
    parse,
    timeout=60.0,  # one ended episode's messages a call
    unread="the episode is written next time",
)


@dataclass(frozen=True, slots=True)
class Written:
    written: int = 0
    cost_usd: float = 0.0


def _severities(store: Store, rel: RelationshipId) -> dict[TurnId, Severity]:
    out: dict[TurnId, Severity] = {}
    for d in store.decisions_with_key(rel, LISTENING_KEY):
        value = logged_severity(d.detail)
        if value is not None:
            out[d.turn_id] = value
    return out


async def write_closed(
    store: Store, extractor: StructuredModel, rel: RelationshipId, now: datetime
) -> Written:
    """A record for every episode that has ended (no message for EPISODE_GAP) and has none yet."""
    said = store.whole_history(rel)
    done = store.episodes(rel)
    have = {e.first_id for e in done if e.prompt == PROMPT.ref}  # older prompts are written again
    seen = {Kind(e.kind) for e in done}
    severity = _severities(store, rel)
    written, cost = 0, 0.0
    for s in cut(said):
        found = kind(s, severity)
        new_firsts = firsts(found, seen)
        seen.add(found)
        if s.said[0].id in have or now - s.said[-1].at < EPISODE_GAP:
            continue
        got = await ask(extractor, GIST_WRITER, f"{facts(s, found)}\n\nMessages:\n{transcript(s)}")
        if got is None:
            continue
        cost += got.cost_usd
        gist = got.value
        store.part(Episodes).add(
            rel,
            Episode(
                new_id(),
                s.said[0].id,
                s.said[-1].id,
                s.said[0].at,
                s.said[-1].at,
                len(s.said),
                found.value,
                round(s.scene_share, 3),
                top_severity(s, severity),
                tuple(new_firsts),
                gist,
                PROMPT.ref,
                now,
            ),
        )
        written += 1
    return Written(written, cost)


EPISODE_SECONDS = 8.0  # writing a just-ended episode before the reply; slower means it is left out
EPISODES_SHOWN = "episodes: what the two of them did recently, shown"


async def recent_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[Told, ...]:
    """What the two of them did recently, when their words point at a time or they come back after
    a gap (J12, J49). An episode not yet recorded is written first. Logged; shown only when on."""
    del heard
    if c.mode(switch.EPISODES) is Mode.OFF or c.judge is None or in_scene is not Frame.REAL:
        return ()
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    last = theirs[-1].at if theirs else None
    zone = local_zone()
    pointed = period(t.text, t.now, zone) is not None
    back = last is not None and t.now - last >= GAP_BACK
    if not (pointed or back):
        return ()
    mark(t, "recent times")
    await bounded(  # what is already recorded is still shown
        write_closed(c.store, c.judge, c.rel, t.now),
        deadline=EPISODE_SECONDS,
        what="writing episodes before the reply",
        unread="what is already recorded is shown",
    )
    ends = [(e.start_at, e.end_at, e.gist) for e in c.store.episodes(c.rel)]
    told = recent_times(ends, t.text, last, t.now, zone)
    if told:
        detail: dict[str, Json] = {
            "mode": c.mode(switch.EPISODES),
            "why": "pointed at a time" if pointed else "back after a gap",
            "shown": [f"{x.when}: {x.gist}" for x in told],
            "note": EPISODES_NOTE.ref,
        }
        shadow = "" if c.mode(switch.EPISODES) is Mode.ON else " (shadow, not sent)"
        decide(c, t, EPISODES_SHOWN, detail, reason=EPISODES_SHOWN + shadow)
    return tuple(told) if c.mode(switch.EPISODES) is Mode.ON else ()


def recent_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    del m, so_far
    text = episodes_note(cast("tuple[Told, ...]", found or ()))
    return Offer((text,) if text else ())


async def write_step(c: Runtime, judge: StructuredModel) -> None:
    await write_closed(c.store, judge, c.rel, utc_now())


EPISODES = Feature(
    "recent",
    look=recent_for_turn,
    note=recent_offer,
    nightly=NightStep("episodes", write_step),
)
