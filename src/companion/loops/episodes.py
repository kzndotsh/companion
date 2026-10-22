"""Writing a record of each stretch of chat once it is over (J12, shadow: nothing reaches the talker
yet). Run nightly and by `companion episodes --write`."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from companion.core.episodes import (
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
from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import DecisionKind, RelationshipId, TurnId
from companion.store.sqlite.episodes import Episode
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
