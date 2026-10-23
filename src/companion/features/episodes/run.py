"""Writing a record of each stretch of chat once it is over (J12, shadow: nothing reaches the talker
yet). Run nightly and by `companion episodes --write`."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from companion.core.clock import named_zone
from companion.core.types import Frame, Json, Speaker
from companion.features.episodes.logic import GAP_BACK as EPISODE_GAP
from companion.features.episodes.logic import NOTE as EPISODES_NOTE
from companion.features.episodes.logic import Told, period
from companion.features.episodes.logic import note as episodes_note
from companion.features.episodes.logic import recent as recent_times
from companion.loops.features import Feature, Offer, Offered
from companion.loops.turn import Heard, Turn, decide, mark

if TYPE_CHECKING:
    from companion.loops.fast import Conversation
    from companion.loops.notes import Moment

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import DecisionKind, RelationshipId, TurnId
from companion.features.episodes.logic import (
    GAP,
    PROMPT,
    SCHEMA,
    Kind,
    facts,
    firsts,
    kind,
    parse,
    stretches,
    top_severity,
    transcript,
)
from companion.features.episodes.store import Episode
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.episodes")
FAR = datetime(9999, 1, 1, tzinfo=UTC)
WHOLE = 1_000_000


@dataclass(frozen=True, slots=True)
class Written:
    written: int = 0
    cost_usd: float = 0.0


def _severities(store: Store, rel: RelationshipId) -> dict[TurnId, int]:
    out: dict[TurnId, int] = {}
    for d in store.decisions_of_kind(rel, DecisionKind.POLICY):
        if not d.has_key("listening") or not d.detail:
            continue
        labels = d.detail.get("labels")
        value = labels.get("severity") if isinstance(labels, dict) else None
        if isinstance(value, int):
            out[d.turn_id] = value
    return out


async def write_closed(
    store: Store, extractor: Extractor, rel: RelationshipId, now: datetime
) -> Written:
    """A record for every stretch that has ended (no message for GAP) and has none yet."""
    said = store.history_before(rel, FAR, WHOLE)
    done = store.episodes(rel)
    have = {e.first_id for e in done if e.prompt == PROMPT.ref}  # older prompts are written again
    seen = {Kind(e.kind) for e in done}
    severity = _severities(store, rel)
    written, cost = 0, 0.0
    for s in stretches(said):
        found = kind(s, severity)
        new_firsts = firsts(found, seen)
        seen.add(found)
        if s.said[0].id in have or now - s.said[-1].at < GAP:
            continue
        try:
            with purpose("episodes"):
                got = await extractor.extract(
                    PROMPT.text, f"{facts(s, found)}\n\nMessages:\n{transcript(s)}", SCHEMA
                )
        except Exception as err:
            log.warning("episode line failed; it is written next time: %r", err)
            continue
        cost += got.cost_usd
        gist = parse(got.data)
        if gist is None:
            continue
        store.add_episode(
            rel,
            Episode(
                uuid.uuid4().hex,
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


EPISODE_SECONDS = 8.0  # writing a just-ended stretch before the reply; slower means it is left out
EPISODES_SHOWN = "episodes: what the two of them did recently, shown"


async def recent_for_turn(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[Told, ...]:
    """What the two of them did recently, when their words point at a time or they come back after
    a gap (J12, J49). A stretch not yet recorded is written first. Logged; shown only when on."""
    del heard
    if c.episodes == "off" or c.judge is None or in_scene is not Frame.REAL:
        return ()
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    last = theirs[-1].at if theirs else None
    zone = named_zone()
    pointed = period(t.text, t.now, zone) is not None
    back = last is not None and t.now - last >= EPISODE_GAP
    if not (pointed or back):
        return ()
    mark(t, "recent times")
    try:
        await asyncio.wait_for(write_closed(c.store, c.judge, c.rel, t.now), EPISODE_SECONDS)
    except Exception as err:  # what is already recorded is still shown
        log.warning("writing episodes before the reply failed: %r", err)
    ends = [(e.start_at, e.end_at, e.gist) for e in c.store.episodes(c.rel)]
    told = recent_times(ends, t.text, last, t.now, zone)
    if told:
        detail: dict[str, Json] = {
            "mode": c.episodes,
            "why": "pointed at a time" if pointed else "back after a gap",
            "shown": [f"{x.when}: {x.gist}" for x in told],
            "note": EPISODES_NOTE.ref,
        }
        shadow = "" if c.episodes == "on" else " (shadow, not sent)"
        decide(c, t, EPISODES_SHOWN, detail, reason=EPISODES_SHOWN + shadow)
    return tuple(told) if c.episodes == "on" else ()


def recent_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    del m, so_far
    text = episodes_note(cast("tuple[Told, ...]", found or ()))
    return Offer((text,) if text else ())


EPISODES = Feature("recent", look=recent_for_turn, note=recent_offer)
