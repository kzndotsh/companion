"""The one thing the companion brings up on its own when they write, chosen across every feature
that would (ADR 0023): a plan of theirs, a day. One gate (a casual turn, nothing else asking them
something), one choice by rank with one a day across sources, one decision once the turn is stored,
and how they met it read from their next message, for the pace learned in shadow.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.turn.mentions import (
    CHECKED_IN,
    MET_PROMPT,
    MET_SCHEMA,
    PACE,
    PACE_LOOKBACK,
    WINDOW,
    MentionCandidate,
    Rank,
    choose,
    met_prompt,
    pace,
    pace_holds,
    parse_met,
)
from companion.core.types import Json, Speaker, Utterance
from companion.features.calendar.logic import OFFERED as CALENDAR_OFFERED
from companion.features.threads.run import LOOP_OFFERED
from companion.kit.ask import Judge, ask
from companion.kit.current import Turn, decide
from companion.kit.features import Moment, Offer, Offered, asking, has_room
from companion.registry import FEATURES

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

MET = "threads: how they met it"
PACE_SOONER = "threads: the learned pace would bring one up now (shadow)"
MET_JUDGE = Judge("thread-met", MET_PROMPT, MET_SCHEMA, parse_met, timeout=8.0, unread="no label")
# The decision key each feature's mentions are logged under, by feature name. Checked when the
# module loads, so a feature that mentions things cannot be left out of the day's count.
KEYS = {"loop": LOOP_OFFERED, "calendar": CALENDAR_OFFERED}


def _check_keys() -> None:
    mentions = {f.name for f in FEATURES if f.mention is not None}
    if mentions != set(KEYS):
        msg = f"mentions: features {sorted(mentions)} but keys for {sorted(KEYS)}"
        raise RuntimeError(msg)


_check_keys()


def _offers(c: Runtime, since: datetime) -> list[tuple[datetime, Rank]]:
    """What was brought up since a time, with its rank; one from before ranks were logged counts as
    the lowest, so it holds back only a lead-up."""
    out: list[tuple[datetime, Rank]] = []
    for key in KEYS.values():
        for d in c.store.decisions_with_key(c.rel, key, since):
            rank = (d.detail or {}).get("rank")
            out.append((d.at, Rank(rank) if isinstance(rank, int) else Rank.LEAD_UP))
    return out


def _pace(c: Runtime, now: datetime, offered: list[datetime]) -> tuple[dict[str, Json], bool]:
    """What the learned pace says now (shadow): its wait, the answers it was learned from, and
    whether it would bring one up. Check-ins count with the rest."""
    mets = [
        m
        for d in c.store.decisions_with_key(c.rel, MET, now - PACE_LOOKBACK)
        if (m := parse_met(d.detail or {})) is not None
    ]
    wait = pace(mets)
    checked_in = [d.at for d in c.store.decisions_with_key(c.rel, CHECKED_IN, now - PACE[-1])]
    held = pace_holds(wait, [*offered, *checked_in], now)
    detail: dict[str, Json] = {
        "wait_hours": wait.total_seconds() / 3600,
        "answers": [m.value for m in mets[-5:]],
        "held": held,
    }
    return detail, held is None


def mention_note(m: Moment, so_far: Offered) -> Offer:
    """On a casual turn where no earlier note asks them something, the best of what the features
    would bring up, unless something as good or better was brought up in the last day. Logged once
    the turn is stored, with what the learned pace would have done (shadow); when the day's count
    holds a mention the pace would have allowed, that is logged once a day."""
    if not has_room(m, so_far) or asking(so_far):
        return Offer()
    found = [
        cand
        for f in FEATURES
        if f.mention is not None and (cand := f.mention(m, m.looked.found.get(f.name)))
    ]
    if not found:
        return Offer()
    c, t = m.c, m.t
    offers = _offers(c, t.now - PACE[-1])
    paced, would = _pace(c, t.now, [at for at, _ in offers])
    pick = choose(found, [rank for at, rank in offers if t.now - at < WINDOW])
    if pick is None:
        if not would or c.store.decided_since(c.rel, PACE_SOONER, t.now - WINDOW):
            return Offer()
        best = min(found, key=lambda cand: cand.rank)
        sooner = paced | {"about": best.about, "rank": int(best.rank)}
        return Offer(after=(lambda: decide(c, t, PACE_SOONER, sooner),))
    return _offer(c, t, pick, paced)


def _offer(c: Runtime, t: Turn, pick: MentionCandidate, paced: dict[str, Json]) -> Offer:
    detail: dict[str, Json] = {
        **pick.detail,
        "rank": int(pick.rank),
        "about": pick.about,
        "pace": paced,
    }

    def stored() -> None:
        decide(c, t, pick.key, detail, reason=pick.reason)
        if pick.write is not None:
            pick.write()

    line = (pick.line,)
    return Offer(() if pick.tail else line, (stored,), tail=line if pick.tail else (), asks=True)


async def read_met(c: Runtime, t: Turn, said: Utterance, sent: str | None) -> None:
    """Once the turn is stored: when its last message brought something up (a mention or a
    check-in), read how their message met it, once, for the learned pace."""
    del said, sent
    last = next((u for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), None)
    if c.judge is None or last is None:
        return
    keys = (*KEYS.values(), CHECKED_IN)
    offered = next(
        (
            d
            for d in c.store.decisions_for_turn(c.rel, last.turn_id)
            if any(d.has_key(k) for k in keys)
        ),
        None,
    )
    if offered is None or c.store.decided_since(c.rel, MET, offered.at):
        return
    found = offered.detail or {}
    about = str(found.get("about") or found.get("claim") or "how they are after a heavy talk")
    got = await ask(c.judge, MET_JUDGE, met_prompt(about, last.text, t.text))
    met = got.value.value if got is not None else None
    detail: dict[str, Json] = {
        "about": about,
        "loop_id": found.get("loop_id"),
        "met": met,
        "prompt": MET_PROMPT.ref,
    }
    decide(c, t, MET, detail, reason=f"{MET}: {met or 'not read'}, about {about}")
